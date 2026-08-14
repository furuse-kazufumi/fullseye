"""3-D volume image-analysis operators (numpy + scipy.ndimage; skimage optional).

The *analysis* side of the ``volume`` sort. :mod:`volio` widened Fullseye's ingest
to the volumetric world (DICOM / NIfTI / NRRD / MetaImage), turning each study into
the plain ``(D, H, W)`` float64 array the ``vol_*`` ops in :mod:`ops` already speak.
Those built-in ops cover *filtering* (gaussian / median / erode / dilate),
thresholding, projection (MIP / slice) and a blob count — but the only
*segmentation* primitive was a global threshold. This module makes a CT / MRI /
industrial-laminography volume genuinely **analysable**: vessel / tube enhancement,
a spacing-aware Euclidean distance transform, 3-D connected components with a
selectable 6/18/26 neighbourhood, quantitative per-region shape descriptors, a 3-D
gradient, peak detection, and (optionally) a marker watershed.

HALCON has **no voxel image type at all** — its operators act on 2-D images and XLD
contours. Everything here is therefore native ground the evolvable 2-D operator set
cannot reach, and it is deliberately kept *out* of the evolution op registry
(:mod:`ops`): these are plain module functions surfaced through the ``fullseye``
facade (exactly like :mod:`stereo` / :mod:`terrain` / :mod:`pointcloud`), so the
numpy core and the evolutionary search stay untouched.

Frame convention (shared with :mod:`volio`): a volume is a ``(D, H, W)`` float64
array indexed ``[z, y, x]``; ``spacing`` is ``(sz, sy, sx)`` in millimetres, lined
up with those axes, exactly as :class:`volio.VolumeMeta` reports it (a
``VolumeMeta`` may itself be passed wherever ``spacing`` is accepted).

Provenance (public papers, cited per function):

  * **Frangi** vesselness — A. F. Frangi, W. J. Niessen, K. L. Vincken, M. A.
    Viergever, "Multiscale vessel enhancement filtering", MICCAI 1998, LNCS 1496,
    130-137.
  * **Sato** tubeness — Y. Sato *et al.*, "Three-dimensional multi-scale line
    filter for segmentation and visualization of curvilinear structures in medical
    images", Medical Image Analysis 2(2):143-168, 1998.
  * **Exact Euclidean distance transform** — P. F. Felzenszwalb & D. P.
    Huttenlocher, "Distance Transforms of Sampled Functions", Theory of Computing
    8(19):415-428, 2012 (the algorithm behind ``scipy.ndimage.distance_transform_edt``).
  * **Wadell sphericity** — H. Wadell, "Volume, Shape, and Roundness of Quartz
    Particles", J. Geology 43(3):250-280, 1935.
  * The symmetric-3x3 eigenvalue closed form is the standard trigonometric
    (Cardano) solution used by most vesselness implementations.

Honest limitations (nothing here claims more than a real test in
``tests/test_volops.py`` proves):

  * **Frangi / Sato are scale-dependent.** A tubular structure is enhanced only
    when some ``scale`` in the set is comparable to its radius (the Hessian is
    built from a Gaussian of standard deviation ``sigma = scale`` and
    gamma-normalised by ``sigma**2``). Pick ``scales`` to bracket the *radii* of
    the features you want, in voxels — too small and a thick vessel reads as a
    slab, too large and a thin one is smoothed away. Neither is a substitute for
    the other: Frangi suppresses plate- and blob-like structure explicitly; Sato
    is the simpler two-eigenvalue line measure.
  * **Eigenvalue sign convention.** With eigenvalues ordered by magnitude
    ``|l1| <= |l2| <= |l3|``, a *bright* tube on a dark background has
    ``l2, l3 < 0`` (the default, ``black_ridges=False``); a *dark* tube on a
    bright background has ``l2, l3 > 0`` (``black_ridges=True``). Passing the
    wrong polarity yields an all-zero response, not a wrong-but-plausible one.
  * **Surface area / sphericity from a voxel grid are discretisation-sensitive
    and approximate.** Counting exposed voxel faces *overestimates* a curved
    surface by up to the staircase factor (~1.5x for a sphere), which drives the
    reported sphericity below 1; the optional marching-cubes surface (``skimage``)
    is markedly closer to the truth. Both are approximations — treat sphericity as
    a shape *index*, not a certified measurement.
  * **Memory.** The Hessian eigenvalue ops (Frangi / Sato / blobness) build a
    handful of full-volume temporaries and are capped at ``MAX_EIGEN_VOXELS``
    (~256**3). A full 512**3 CT is refused: take a region of interest or
    downsample first (3-D Frangi at that size costs several GB in *any*
    implementation).
  * A "binary" input (distance transform / labelling) that is not already ``{0,
    1}`` is thresholded at ``> 0.5`` — the same convention as ``ops.vol_count`` /
    ``ops.vol_threshold`` — rather than being rejected. This is documented, not
    silent.

Fail-closed on untrusted input: every entry point requires a 3-D ``(D, H, W)``
array, coerces to float64, rejects NaN / Inf where it would corrupt the result,
and caps the voxel count *before* any heavy allocation. A malformed input raises
``ValueError`` naming the problem.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = [
    "vol_frangi", "vol_sato", "vol_hessian_blobness",
    "vol_distance_transform", "vol_label", "vol_region_props",
    "vol_gradient_magnitude", "vol_local_maxima", "vol_watershed",
    "VOLOPS", "MAX_VOXELS", "MAX_EIGEN_VOXELS",
]

#: The public 3-D analysis operators, by name (introspection / facade wiring).
VOLOPS = [
    "vol_frangi", "vol_sato", "vol_hessian_blobness",
    "vol_distance_transform", "vol_label", "vol_region_props",
    "vol_gradient_magnitude", "vol_local_maxima", "vol_watershed",
]

#: Refuse a volume larger than this for the *cheap* N-D ops (label / EDT /
#: gradient / region-props / peaks). ~134 M voxels = 1 GiB as float64.
MAX_VOXELS = 1 << 27
#: Refuse a volume larger than this for the Hessian-eigenvalue ops (Frangi / Sato
#: / blobness), which allocate several full-volume temporaries. ~16.7 M voxels
#: (~256**3). A larger volume must be cropped to an ROI or downsampled first.
MAX_EIGEN_VOXELS = 1 << 24


# --------------------------------------------------------------------------- #
# fail-closed input helpers                                                    #
# --------------------------------------------------------------------------- #
def _require_volume(vol, name: str = "vol", check_finite: bool = True) -> np.ndarray:
    """Coerce to a contiguous ``(D, H, W)`` float64 array or raise ``ValueError``.

    Rejects anything that is not exactly 3-D, and (by default) any NaN / Inf —
    a poisoned voxel would propagate through every derivative and corrupt the
    whole downstream result silently."""
    v = np.ascontiguousarray(vol, dtype=np.float64)
    if v.ndim != 3:
        raise ValueError("%s must be a 3-D (D, H, W) volume, got a %d-D array of shape %r"
                         % (name, v.ndim, tuple(np.shape(vol))))
    if check_finite and not np.isfinite(v).all():
        n = int((~np.isfinite(v)).sum())
        raise ValueError("%s has %d non-finite voxel(s) (NaN/Inf) — refusing "
                         "(the 3-D operators would propagate them)" % (name, n))
    return v


def _check_voxels(v: np.ndarray, cap: int, op: str) -> None:
    if v.size > cap:
        raise ValueError("%s: a %d-voxel volume (shape %r) exceeds the %d cap "
                         "(volops.%s) — crop to an ROI or downsample first"
                         % (op, v.size, v.shape, cap,
                            "MAX_EIGEN_VOXELS" if cap == MAX_EIGEN_VOXELS else "MAX_VOXELS"))


def _as_binary(vol, name: str = "vol_binary") -> np.ndarray:
    """A 3-D mask as a bool array. A non-``{0, 1}`` volume is thresholded at
    ``> 0.5`` (documented convention, matching ``ops.vol_count``)."""
    v = _require_volume(vol, name)
    return v > 0.5


def _spacing_tuple(spacing, name: str = "spacing"):
    """Normalise a spacing argument to ``(sz, sy, sx)`` floats, or ``None``.

    Accepts a 3-tuple *or* a :class:`volio.VolumeMeta` (whose ``spacing_mm`` is
    already ``(sz, sy, sx)``)."""
    if spacing is None:
        return None
    if hasattr(spacing, "spacing_mm"):
        spacing = spacing.spacing_mm
    try:
        sp = tuple(float(s) for s in spacing)
    except (TypeError, ValueError):
        raise ValueError("%s must be a length-3 (sz, sy, sx) sequence or a "
                         "VolumeMeta, got %r" % (name, spacing)) from None
    if len(sp) != 3 or any(not np.isfinite(s) or s <= 0.0 for s in sp):
        raise ValueError("%s must be 3 positive finite values (sz, sy, sx), got %r"
                         % (name, sp))
    return sp


def _norm01(x: np.ndarray) -> np.ndarray:
    """Scale a non-negative response to ``[0, 1]`` (all-zero stays all-zero)."""
    m = float(x.max()) if x.size else 0.0
    if m <= 0.0:
        return np.zeros_like(x)
    return x / m


# --------------------------------------------------------------------------- #
# Hessian + symmetric-3x3 eigenvalues (shared by Frangi / Sato / blobness)     #
# --------------------------------------------------------------------------- #
def _hessian_components(vol: np.ndarray, sigma: float):
    """The six independent entries of the gamma-normalised Hessian at ``sigma``.

    Second derivatives of the Gaussian-smoothed volume via
    ``scipy.ndimage.gaussian_filter`` (``order`` selects the derivative per axis,
    axis 0=z, 1=y, 2=x), scaled by ``sigma**2`` for scale invariance (Lindeberg's
    gamma-normalisation with gamma=1). Returns ``(a, b, c, d, e, f)`` = the
    ``(zz, yy, xx, zy, zx, yx)`` entries of the symmetric matrix
    ``[[a, d, e], [d, b, f], [e, f, c]]``."""
    s = float(sigma)
    g = s * s
    hzz = ndimage.gaussian_filter(vol, s, order=(2, 0, 0)) * g
    hyy = ndimage.gaussian_filter(vol, s, order=(0, 2, 0)) * g
    hxx = ndimage.gaussian_filter(vol, s, order=(0, 0, 2)) * g
    hzy = ndimage.gaussian_filter(vol, s, order=(1, 1, 0)) * g
    hzx = ndimage.gaussian_filter(vol, s, order=(1, 0, 1)) * g
    hyx = ndimage.gaussian_filter(vol, s, order=(0, 1, 1)) * g
    return hzz, hyy, hxx, hzy, hzx, hyx


def _eigvalsh_sym3(a, b, c, d, e, f):
    """Eigenvalues of a field of symmetric 3x3 matrices, in **algebraic** order
    ``e1 >= e2 >= e3`` (element-wise).

    Closed-form trigonometric (Cardano) solution — avoids materialising an
    ``(N, 3, 3)`` stack, so peak memory stays O(N). ``a, b, c`` are the diagonal
    and ``d, e, f`` the off-diagonals ``(M01, M02, M12)``."""
    q = (a + b + c) / 3.0
    p1 = d * d + e * e + f * f
    aq, bq, cq = a - q, b - q, c - q
    p2 = aq * aq + bq * bq + cq * cq + 2.0 * p1
    p = np.sqrt(p2 / 6.0)
    det = aq * bq * cq - aq * f * f - bq * e * e - cq * d * d + 2.0 * d * e * f
    with np.errstate(divide="ignore", invalid="ignore"):
        r = det / (2.0 * p ** 3)
    r = np.clip(np.nan_to_num(r, nan=0.0, posinf=1.0, neginf=-1.0), -1.0, 1.0)
    phi = np.arccos(r) / 3.0
    e1 = q + 2.0 * p * np.cos(phi)
    e3 = q + 2.0 * p * np.cos(phi + 2.0 * np.pi / 3.0)
    e2 = 3.0 * q - e1 - e3               # trace = e1 + e2 + e3
    flat = p > 0.0                       # p == 0  =>  matrix is q*I (all equal)
    e1 = np.where(flat, e1, q)
    e2 = np.where(flat, e2, q)
    e3 = np.where(flat, e3, q)
    return e1, e2, e3


def _abs_sorted_eigs(e1, e2, e3):
    """Re-order per-voxel eigenvalues by magnitude: ``|l1| <= |l2| <= |l3|``."""
    E = np.stack([e1, e2, e3], axis=-1)
    order = np.argsort(np.abs(E), axis=-1)
    Es = np.take_along_axis(E, order, axis=-1)
    return Es[..., 0], Es[..., 1], Es[..., 2]


def _iter_scales(scales, name="scales"):
    try:
        sc = [float(s) for s in np.atleast_1d(scales)]
    except (TypeError, ValueError):
        raise ValueError("%s must be a sequence of positive scale(s), got %r"
                         % (name, scales)) from None
    if not sc or any(not np.isfinite(s) or s <= 0.0 for s in sc):
        raise ValueError("%s must be positive finite value(s), got %r" % (name, scales))
    return sc


# --------------------------------------------------------------------------- #
# vesselness / tubeness / blobness                                            #
# --------------------------------------------------------------------------- #
def vol_frangi(vol, scales=(1, 2, 3), alpha=0.5, beta=0.5, c=None,
               black_ridges=False):
    """3-D Frangi vesselness — multiscale tubular-structure enhancement.

    For every ``sigma`` in *scales* the gamma-normalised Hessian is formed, its
    three eigenvalues ``|l1| <= |l2| <= |l3|`` are taken, and the Frangi response

        V = (1 - exp(-Ra**2 / 2 alpha**2)) * exp(-Rb**2 / 2 beta**2)
              * (1 - exp(-S**2 / 2 c**2))

    is evaluated, where ``Ra = |l2|/|l3|`` (plate vs. line), ``Rb = |l1|/sqrt|l2 l3|``
    (blob deviation) and ``S = sqrt(l1**2 + l2**2 + l3**2)`` (structure strength).
    The response is set to 0 where the contrast polarity is wrong (bright tube:
    ``l2 > 0`` or ``l3 > 0``; ``black_ridges=True`` flips this). The maximum over
    scales is taken and the volume is normalised to ``[0, 1]``.

    Parameters
    ----------
    scales : sequence of float — Gaussian sigmas, in **voxels**, to bracket the
        vessel *radii* of interest (see the module "scale-dependent" limitation).
    alpha, beta : sensitivities of the plate- and blob-suppression terms (Frangi's
        defaults 0.5).
    c : half the maximum Hessian norm ``S`` at each scale when ``None`` (Frangi's
        adaptive suggestion); otherwise a fixed structure-strength scale.
    black_ridges : ``False`` (default) enhances *bright* tubes on a dark
        background; ``True`` enhances *dark* tubes on a bright background.

    Returns a ``(D, H, W)`` float64 volume in ``[0, 1]``. Reference: Frangi et al.,
    MICCAI 1998.
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_EIGEN_VOXELS, "vol_frangi")
    a2 = 2.0 * float(alpha) ** 2
    b2 = 2.0 * float(beta) ** 2
    out = np.zeros_like(v)
    for sigma in _iter_scales(scales):
        e1, e2, e3 = _eigvalsh_sym3(*_hessian_components(v, sigma))
        l1, l2, l3 = _abs_sorted_eigs(e1, e2, e3)
        al2, al3 = np.abs(l2), np.abs(l3)
        S = np.sqrt(l1 * l1 + l2 * l2 + l3 * l3)
        cc = 0.5 * float(S.max()) if c is None else float(c)
        if cc <= 0.0:
            cc = 1.0
        with np.errstate(divide="ignore", invalid="ignore"):
            Ra = np.where(al3 > 0, al2 / al3, 0.0)
            Rb = np.where((al2 * al3) > 0, np.abs(l1) / np.sqrt(al2 * al3), 0.0)
        resp = ((1.0 - np.exp(-(Ra * Ra) / a2))
                * np.exp(-(Rb * Rb) / b2)
                * (1.0 - np.exp(-(S * S) / (2.0 * cc * cc))))
        if black_ridges:
            resp[(l2 < 0) | (l3 < 0)] = 0.0
        else:
            resp[(l2 > 0) | (l3 > 0)] = 0.0
        resp = np.nan_to_num(resp, nan=0.0, posinf=0.0, neginf=0.0)
        out = np.maximum(out, resp)
    return _norm01(out)


def vol_sato(vol, scales=(1, 2, 3), black_ridges=False):
    """3-D Sato tubeness — the simpler two-eigenvalue line filter.

    Per scale, from eigenvalues in algebraic order ``e1 >= e2 >= e3`` a bright
    curvilinear (tube) structure has ``e2, e3 < 0`` and the tubeness is
    ``sqrt(e2 * e3)`` there (0 elsewhere); ``black_ridges=True`` uses the two most
    *positive* eigenvalues for dark tubes. The maximum over scales is normalised
    to ``[0, 1]``.

    Cheaper and less selective than :func:`vol_frangi` (it does not explicitly
    suppress plate- or blob-like structure), but a robust, well-cited tube
    detector. Reference: Sato et al., Medical Image Analysis 1998.
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_EIGEN_VOXELS, "vol_sato")
    out = np.zeros_like(v)
    for sigma in _iter_scales(scales):
        e1, e2, e3 = _eigvalsh_sym3(*_hessian_components(v, sigma))
        if black_ridges:                       # dark tube: two most positive eigenvalues
            lo, hi = e2, e1
            resp = np.where((lo > 0) & (hi > 0), np.sqrt(np.maximum(lo * hi, 0.0)), 0.0)
        else:                                  # bright tube: two most negative eigenvalues
            lo, hi = e3, e2
            resp = np.where((lo < 0) & (hi < 0), np.sqrt(np.maximum(lo * hi, 0.0)), 0.0)
        out = np.maximum(out, resp)
    return _norm01(out)


def vol_hessian_blobness(vol, scale, black_ridges=False):
    """Blob-like (spherical) response from the Hessian eigenvalues at one *scale*.

    A bright blob has all three eigenvalues negative and comparable in magnitude;
    the response is the geometric mean of their magnitudes,
    ``(|l1| |l2| |l3|)**(1/3)``, gated to voxels where the three share the sign of
    a blob of the requested polarity (all negative for bright, all positive for
    dark). Normalised to ``[0, 1]``. Complements the line filters — a Frangi-style
    ``Rb`` term rejects blobs, this one keeps them. Reference: the second-order
    (Hessian) blob measure, cf. Frangi et al. 1998 / Lindeberg scale-space blobs.
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_EIGEN_VOXELS, "vol_hessian_blobness")
    sigma = _iter_scales(scale, "scale")[0]
    e1, e2, e3 = _eigvalsh_sym3(*_hessian_components(v, sigma))
    if black_ridges:
        same = (e1 > 0) & (e2 > 0) & (e3 > 0)
    else:
        same = (e1 < 0) & (e2 < 0) & (e3 < 0)
    mag = np.cbrt(np.abs(e1) * np.abs(e2) * np.abs(e3))
    resp = np.where(same, mag, 0.0)
    return _norm01(resp)


# --------------------------------------------------------------------------- #
# distance transform / connected components                                   #
# --------------------------------------------------------------------------- #
def vol_distance_transform(vol_binary, spacing=None):
    """Exact Euclidean distance transform of a binary volume.

    Each foreground (non-zero) voxel is labelled with its Euclidean distance to
    the nearest background voxel, via ``scipy.ndimage.distance_transform_edt``.
    Pass *spacing* ``(sz, sy, sx)`` (e.g. ``VolumeMeta.spacing_mm``, or the
    ``VolumeMeta`` itself) to make the distance **anisotropy-aware** — millimetres
    rather than voxels; otherwise unit spacing is assumed. A non-``{0, 1}`` input
    is thresholded at ``> 0.5``.

    Returns a ``(D, H, W)`` float64 distance field (0 on the background).
    Reference: Felzenszwalb & Huttenlocher, Theory of Computing 2012.
    """
    m = _as_binary(vol_binary)
    _check_voxels(m, MAX_VOXELS, "vol_distance_transform")
    sp = _spacing_tuple(spacing)
    dt = ndimage.distance_transform_edt(m, sampling=sp)
    return np.ascontiguousarray(dt, dtype=np.float64)


def vol_label(vol_binary, connectivity=26):
    """3-D connected-component labelling with a selectable neighbourhood.

    *connectivity* chooses the structuring element: ``6`` (face neighbours only),
    ``18`` (faces + edges), or ``26`` (faces + edges + corners — the default,
    ``ndimage.generate_binary_structure(3, 3)``). A non-``{0, 1}`` input is
    thresholded at ``> 0.5``.

    Returns ``(labels, n)`` — an ``int32`` volume whose voxels are ``0``
    (background) or a component id in ``1..n``, and the component count ``n``.
    The neighbourhood genuinely matters: two blobs meeting only at a corner are
    *two* components under 6-connectivity but *one* under 26.
    """
    rank = {6: 1, 18: 2, 26: 3}.get(int(connectivity))
    if rank is None:
        raise ValueError("connectivity must be 6, 18 or 26 (3-D neighbourhoods), got %r"
                         % (connectivity,))
    m = _as_binary(vol_binary)
    _check_voxels(m, MAX_VOXELS, "vol_label")
    structure = ndimage.generate_binary_structure(3, rank)
    labels, n = ndimage.label(m, structure=structure)
    return labels.astype(np.int32, copy=False), int(n)


def _face_surface_area(mask: np.ndarray, spacing) -> float:
    """Surface area by counting exposed voxel faces (a border face counts as
    exposed). Face perpendicular to z has area ``sy*sx``, and so on. This
    *overestimates* a curved surface (staircase artefact) — see the module note."""
    sz, sy, sx = spacing
    mm = np.pad(mask, 1)                      # False border => border faces are exposed
    core = mm[1:-1, 1:-1, 1:-1]
    ez = (np.count_nonzero(core & ~mm[0:-2, 1:-1, 1:-1])
          + np.count_nonzero(core & ~mm[2:, 1:-1, 1:-1]))
    ey = (np.count_nonzero(core & ~mm[1:-1, 0:-2, 1:-1])
          + np.count_nonzero(core & ~mm[1:-1, 2:, 1:-1]))
    ex = (np.count_nonzero(core & ~mm[1:-1, 1:-1, 0:-2])
          + np.count_nonzero(core & ~mm[1:-1, 1:-1, 2:]))
    return float(ez * (sy * sx) + ey * (sz * sx) + ex * (sz * sy))


def _mc_surface_area(mask: np.ndarray, spacing) -> float:
    """Marching-cubes surface area (needs ``scikit-image``). Padded by one voxel
    so a region touching the volume border is still closed."""
    from skimage import measure                # lazy: optional dependency
    padded = np.pad(mask.astype(np.float64), 1)
    verts, faces, _n, _v = measure.marching_cubes(padded, level=0.5, spacing=spacing)
    return float(measure.mesh_surface_area(verts, faces))


def _surface_area(mask: np.ndarray, spacing, surface: str) -> float:
    sp = (1.0, 1.0, 1.0) if spacing is None else spacing
    if surface == "faces":
        return _face_surface_area(mask, sp)
    if surface in ("auto", "marching"):
        try:
            return _mc_surface_area(mask, sp)
        except ImportError:
            if surface == "marching":
                raise ImportError("surface='marching' needs scikit-image — "
                                  "`pip install scikit-image` (or use surface='faces')")
            return _face_surface_area(mask, sp)
    raise ValueError("surface must be 'auto', 'marching' or 'faces', got %r" % (surface,))


def _sphericity(volume: float, area: float) -> float:
    """Wadell sphericity: ``pi**(1/3) (6V)**(2/3) / A`` (1 for a perfect sphere,
    dimensionless and scale-free). Discretisation-sensitive — see module note."""
    if area <= 0.0:
        return 0.0
    return float((np.pi ** (1.0 / 3.0)) * ((6.0 * volume) ** (2.0 / 3.0)) / area)


def vol_region_props(labels, spacing=None, surface="auto"):
    """Per-component quantitative descriptors from a label volume.

    *labels* is the ``int`` volume returned by :func:`vol_label` (or any integer
    labelling; voxels ``<= 0`` are background). Pass *spacing* ``(sz, sy, sx)`` (or
    a :class:`volio.VolumeMeta`) to report physical volume in mm**3 and physical
    surface area in mm**2. *surface* selects the surface-area estimator:
    ``"auto"`` (marching cubes when ``scikit-image`` is importable, else exposed
    faces), ``"marching"`` (require marching cubes), or ``"faces"`` (always the
    face count).

    Returns a ``list[dict]`` (one per label ``1..n``, in ascending label order),
    each with:

    ``label`` id · ``voxel_count`` · ``volume`` (voxels, or mm**3 with spacing) ·
    ``centroid`` ``(z, y, x)`` in voxel-index coordinates · ``bbox``
    ``(z0, z1, y0, y1, x0, x1)`` with **exclusive** upper bounds (slice ``stop``) ·
    ``surface_area`` (voxel-face units, or mm**2 with spacing) · ``sphericity``
    (Wadell, ~1 for a sphere, lower for a slab; approximate — see module note).
    """
    L = np.asarray(labels)
    if L.ndim != 3:
        raise ValueError("labels must be a 3-D (D, H, W) label volume, got a %d-D array"
                         % L.ndim)
    if L.size > MAX_VOXELS:
        raise ValueError("vol_region_props: %d-voxel label volume exceeds the %d cap "
                         "(volops.MAX_VOXELS)" % (L.size, MAX_VOXELS))
    L = L.astype(np.int64, copy=False)
    sp = _spacing_tuple(spacing)
    voxvol = 1.0 if sp is None else float(sp[0] * sp[1] * sp[2])
    slices = ndimage.find_objects(L)
    props = []
    for i, sl in enumerate(slices, start=1):
        if sl is None:
            continue
        sub = (L[sl] == i)
        cnt = int(sub.sum())
        if cnt == 0:
            continue
        offset = np.array([s.start for s in sl], dtype=np.float64)
        centroid = tuple(float(x) for x in (np.argwhere(sub).mean(axis=0) + offset))
        area = _surface_area(sub, sp, surface)
        volume = cnt * voxvol
        props.append({
            "label": int(i),
            "voxel_count": cnt,
            "volume": float(volume),
            "centroid": centroid,
            "bbox": (int(sl[0].start), int(sl[0].stop),
                     int(sl[1].start), int(sl[1].stop),
                     int(sl[2].start), int(sl[2].stop)),
            "surface_area": float(area),
            "sphericity": _sphericity(volume, area),
        })
    return props


# --------------------------------------------------------------------------- #
# gradient / peaks / watershed                                                #
# --------------------------------------------------------------------------- #
def vol_gradient_magnitude(vol):
    """3-D Sobel gradient magnitude ``sqrt(gz**2 + gy**2 + gx**2)``.

    Each ``g*`` is a ``scipy.ndimage.sobel`` derivative along one axis. The
    response localises at intensity boundaries (a step edge lights up on the
    interface and is ~0 in flat regions). Returns a ``(D, H, W)`` float64 volume.
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_VOXELS, "vol_gradient_magnitude")
    gz = ndimage.sobel(v, axis=0)
    gy = ndimage.sobel(v, axis=1)
    gx = ndimage.sobel(v, axis=2)
    return np.sqrt(gz * gz + gy * gy + gx * gx)


def vol_local_maxima(vol, min_distance, threshold=None):
    """3-D local-maxima (peak) detection.

    A voxel is a peak if it equals the maximum over a cubic neighbourhood of
    half-width ``min_distance`` (side ``2*min_distance + 1``) **and** that
    neighbourhood is not flat (its max strictly exceeds its min, so a constant
    region yields no peaks). Pass *threshold* to additionally require
    ``vol >= threshold`` (drop weak peaks in noise).

    Returns an ``(N, 3)`` int array of ``(z, y, x)`` peak coordinates. Uses only
    ``scipy.ndimage.maximum_filter`` / ``minimum_filter`` (no skimage).
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_VOXELS, "vol_local_maxima")
    md = int(min_distance)
    if md < 1:
        raise ValueError("min_distance must be a positive integer, got %r" % (min_distance,))
    size = 2 * md + 1
    mx = ndimage.maximum_filter(v, size=size, mode="nearest")
    mn = ndimage.minimum_filter(v, size=size, mode="nearest")
    peaks = (v == mx) & (mx > mn)
    if threshold is not None:
        peaks &= v >= float(threshold)
    return np.argwhere(peaks).astype(np.int64)


def vol_watershed(vol, markers, mask=None):
    """Marker-controlled 3-D watershed segmentation (**optional — scikit-image**).

    Floods the volume from the labelled *markers* (an int volume, ``0`` = unset),
    optionally restricted to *mask*. Delegates to
    ``skimage.segmentation.watershed`` — treat *vol* as a landscape (e.g. a
    gradient magnitude, or the negated distance transform for splitting touching
    blobs). Returns an ``int32`` ``(D, H, W)`` label volume.

    Raises ``ImportError`` with a clear ``pip install scikit-image`` message when
    the optional dependency is absent; the rest of this module needs only
    numpy + scipy.
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_VOXELS, "vol_watershed")
    mk = np.asarray(markers)
    if mk.shape != v.shape:
        raise ValueError("markers must match the volume shape %r, got %r"
                         % (v.shape, mk.shape))
    try:
        from skimage.segmentation import watershed      # lazy: optional dependency
    except ImportError:
        raise ImportError("vol_watershed needs scikit-image — "
                          "`pip install scikit-image`") from None
    msk = None if mask is None else (_require_volume(mask, "mask", check_finite=False) > 0.5)
    labels = watershed(v, markers=mk.astype(np.int32), mask=msk)
    return labels.astype(np.int32, copy=False)
