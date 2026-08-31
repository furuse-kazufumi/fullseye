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
    "volume_downsample",
    "vol_reduce_domain", "vol_bounding_box", "vol_crop_domain", "vol_uncrop",
    "vol_boundary", "vol_boundary_points",
    "VOLOPS", "MAX_VOXELS", "MAX_EIGEN_VOXELS",
]

#: The public 3-D analysis operators, by name (introspection / facade wiring).
VOLOPS = [
    "vol_frangi", "vol_sato", "vol_hessian_blobness",
    "vol_distance_transform", "vol_label", "vol_region_props",
    "vol_gradient_magnitude", "vol_local_maxima", "vol_watershed",
    "volume_downsample",
    "vol_reduce_domain", "vol_bounding_box", "vol_crop_domain", "vol_uncrop",
    "vol_boundary", "vol_boundary_points",
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


def _check_voxels(v: np.ndarray, cap: int, op: str, cap_name: str) -> None:
    if v.size > cap:
        raise ValueError("%s: a %d-voxel volume (shape %r) exceeds the %d cap "
                         "(volops.%s) — crop to an ROI or downsample first"
                         % (op, v.size, v.shape, cap, cap_name))


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


def _structure_floor(v: np.ndarray) -> float:
    """An absolute Hessian-strength threshold below which a volume is treated as
    structureless. A flat / constant volume yields only floating-point dust
    (~1e-16) in its second derivatives; normalising that to ``[0, 1]`` would
    manufacture a spurious full-range vesselness. This floor (scaled to the
    volume's own intensity range) sits far above the dust and far below any real
    ridge, so the enhancement filters honestly return zeros on a flat volume."""
    scale = float(v.max() - v.min())
    return 1e-8 * (scale if scale > 0.0 else 1.0)


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
    ``[[a, d, e], [d, b, f], [e, f, c]]``.

    The volume is demeaned first. The Hessian is a second-order (DC-invariant)
    operator analytically, but the *truncated* discrete Gaussian second-derivative
    kernel does not sum to exactly zero, so a constant input leaks a small
    intensity-proportional residual; demeaning makes a globally-constant volume
    exactly zero and removes that artefact without touching real structure."""
    vol = vol - float(vol.mean())
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
    _check_voxels(v, MAX_EIGEN_VOXELS, "vol_frangi", "MAX_EIGEN_VOXELS")
    a2 = 2.0 * float(alpha) ** 2
    b2 = 2.0 * float(beta) ** 2
    tol = _structure_floor(v)
    out = np.zeros_like(v)
    smax = 0.0
    for sigma in _iter_scales(scales):
        e1, e2, e3 = _eigvalsh_sym3(*_hessian_components(v, sigma))
        l1, l2, l3 = _abs_sorted_eigs(e1, e2, e3)
        al2, al3 = np.abs(l2), np.abs(l3)
        S = np.sqrt(l1 * l1 + l2 * l2 + l3 * l3)
        smax = max(smax, float(S.max()))
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
    if smax <= tol:                          # no real structure — do not amplify dust
        return np.zeros_like(v)
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
    _check_voxels(v, MAX_EIGEN_VOXELS, "vol_sato", "MAX_EIGEN_VOXELS")
    tol = _structure_floor(v)
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
    if float(out.max()) <= tol:                # no real structure — do not amplify dust
        return np.zeros_like(v)
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
    _check_voxels(v, MAX_EIGEN_VOXELS, "vol_hessian_blobness", "MAX_EIGEN_VOXELS")
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
    _check_voxels(m, MAX_VOXELS, "vol_distance_transform", "MAX_VOXELS")
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
    _check_voxels(m, MAX_VOXELS, "vol_label", "MAX_VOXELS")
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
    _check_voxels(v, MAX_VOXELS, "vol_gradient_magnitude", "MAX_VOXELS")
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
    _check_voxels(v, MAX_VOXELS, "vol_local_maxima", "MAX_VOXELS")
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
    _check_voxels(v, MAX_VOXELS, "vol_watershed", "MAX_VOXELS")
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


def volume_downsample(vol, factor, mode="mean"):
    """Block-pool a ``(D, H, W)`` volume by an integer *factor* per axis (data 間引き).

    Large CT / laminography / simulation volumes must be thinned before the
    heavier 3-D operators (Frangi/Sato are capped at ~256**3 voxels, see
    ``MAX_EIGEN_VOXELS``). This is the volume analogue of the point-cloud
    ``voxel_grid_downsample`` and the mesh ``decimate_qem`` — the third leg of
    Fullseye's *間引き* (decimation) family, one per 3-D data sort.

    Parameters
    ----------
    vol : array_like, shape (D, H, W)
        Input volume (coerced to float64; NaN/Inf rejected).
    factor : int or (fz, fy, fx)
        Block size per axis, each ``>= 1``. The output shape is
        ``(D//fz, H//fy, W//fx)``; a trailing partial block that cannot fill a
        full factor is dropped (deterministic, no edge bias).
    mode : {'mean', 'max', 'stride'}
        * ``'mean'`` — average-pool. Band-limits before subsampling (the
          anti-aliasing choice); the right default for grey CT / MRI.
        * ``'max'``  — max-pool. Preserves thin bright structures (bone, vessel,
          defect voxels) that averaging would wash out.
        * ``'stride'`` — plain subsample ``vol[::fz, ::fy, ::fx]`` (fastest,
          but aliases — no pre-filter).

    Returns
    -------
    ndarray, shape (D//fz, H//fy, W//fx), float64
        The downsampled volume. Spacing scales by the same factor: an input
        spacing ``(sz, sy, sx)`` mm becomes ``(sz*fz, sy*fy, sx*fx)`` mm.

    Raises
    ------
    ValueError
        Non-3-D input, a factor component ``< 1`` or larger than its axis, or an
        unknown *mode* (fail-closed).
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_VOXELS, "volume_downsample", "MAX_VOXELS")
    if mode not in ("mean", "max", "stride"):
        raise ValueError("mode must be 'mean', 'max' or 'stride', got %r" % (mode,))
    f = np.atleast_1d(np.asarray(factor))
    if f.size == 1:
        f = np.repeat(f, 3)
    if f.size != 3:
        raise ValueError("factor must be an int or a length-3 (fz, fy, fx), got %r"
                         % (factor,))
    try:
        fz, fy, fx = (int(x) for x in f)
    except (TypeError, ValueError):
        raise ValueError("factor components must be integers, got %r" % (factor,)) from None
    if min(fz, fy, fx) < 1:
        raise ValueError("factor components must be >= 1, got (%d, %d, %d)" % (fz, fy, fx))
    D, H, W = v.shape
    if fz > D or fy > H or fx > W:
        raise ValueError("factor (%d, %d, %d) exceeds volume shape %r"
                         % (fz, fy, fx, v.shape))
    if fz == fy == fx == 1:
        return v.copy()
    if mode == "stride":
        return np.ascontiguousarray(v[::fz, ::fy, ::fx])
    d, h, w = D // fz, H // fy, W // fx
    vt = v[:d * fz, :h * fy, :w * fx].reshape(d, fz, h, fy, w, fx)
    out = vt.mean(axis=(1, 3, 5)) if mode == "mean" else vt.max(axis=(1, 3, 5))
    return np.ascontiguousarray(out)


# --------------------------------------------------------------------------- #
# domain (processing region) — the voxel version of HALCON's domain concept    #
# --------------------------------------------------------------------------- #
def vol_reduce_domain(vol, domain):
    """Restrict a volume to a *domain* mask (HALCON ``reduce_domain``, voxel-wise).

    Every voxel outside the foreground of *domain* is set to ``0`` — the same
    "outside the domain is undefined -> 0" convention the 2-D ``it_crop_domain``
    op uses (a plain numpy array cannot carry a separate domain channel, so the
    restriction is materialised). A non-``{0, 1}`` *domain* is thresholded at
    ``> 0.5``. Use it to silence everything a downstream operator must not see
    (metal artefacts, the scanner bed, a neighbouring part); combine with
    :func:`vol_crop_domain` when you also want the *memory* of the volume
    reduced, not just its values.

    Returns a ``(D, H, W)`` float64 volume of the same shape.
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_VOXELS, "vol_reduce_domain", "MAX_VOXELS")
    m = _as_binary(domain, "domain")
    if m.shape != v.shape:
        raise ValueError("domain shape %r must match the volume shape %r"
                         % (m.shape, v.shape))
    return np.ascontiguousarray(np.where(m, v, 0.0), dtype=np.float64)


def vol_bounding_box(domain, margin=0):
    """Tight axis-aligned bounding box of a mask's foreground, in voxel indices.

    Returns ``(z0, y0, x0, z1, y1, x1)`` with **exclusive** upper bounds, i.e.
    ``vol[z0:z1, y0:y1, x0:x1]`` is the smallest sub-volume containing every
    foreground voxel. *margin* (an int ``>= 0``) grows the box by that many
    voxels per side, clipped to the volume — headroom for operators with a
    spatial footprint (a Gaussian of sigma s needs ~``3*s`` voxels of context).
    A non-``{0, 1}`` input is thresholded at ``> 0.5``.

    An **empty** mask raises ``ValueError`` (fail-closed): there is no box, and
    silently returning the full volume would defeat the point of cropping.
    """
    m = _as_binary(domain, "domain")
    _check_voxels(m, MAX_VOXELS, "vol_bounding_box", "MAX_VOXELS")
    if int(margin) != margin or int(margin) < 0:
        raise ValueError("margin must be a non-negative integer, got %r" % (margin,))
    mg = int(margin)
    if not m.any():
        raise ValueError("domain is empty (no foreground voxel) — a bounding box "
                         "is undefined; check the threshold/segmentation upstream")
    lo, hi = [], []
    for ax in range(3):
        prof = np.any(m, axis=tuple(i for i in range(3) if i != ax))
        idx = np.flatnonzero(prof)
        lo.append(max(0, int(idx[0]) - mg))
        hi.append(min(m.shape[ax], int(idx[-1]) + 1 + mg))
    return (lo[0], lo[1], lo[2], hi[0], hi[1], hi[2])


def vol_crop_domain(vol, domain=None, margin=0):
    """Crop a volume to the tight bounding box of a domain (HALCON ``crop_domain``).

    **This is the memory lever of the domain family**: a 512**3 CT scan whose
    part of interest fits in 128**3 costs 64x less memory and compute once
    cropped — and the Hessian operators (:func:`vol_frangi` / :func:`vol_sato`),
    capped at ``MAX_EIGEN_VOXELS``, often become *possible* only after this
    step. Gray values inside the box are kept verbatim (the box, not the mask,
    defines the crop — pair with :func:`vol_reduce_domain` first if voxels
    outside the mask but inside the box must read 0).

    *domain* defaults to the volume's own **non-zero support** (``vol != 0`` —
    a gray volume is cropped to wherever it has any signal; note this differs
    from the ``> 0.5`` convention used when an explicit binary *domain* is
    passed). *margin* is forwarded to :func:`vol_bounding_box`.

    Returns ``(cropped, offset)`` — the ``(d, h, w)`` float64 sub-volume and the
    ``(z0, y0, x0)`` voxel offset of its origin in the input frame. Keep the
    offset: :func:`vol_uncrop` maps results back, and
    :func:`vol_boundary_points` accepts it as *origin* so point coordinates stay
    in the uncropped frame. An empty domain raises ``ValueError`` (fail-closed).
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_VOXELS, "vol_crop_domain", "MAX_VOXELS")
    dom = (v != 0.0) if domain is None else domain
    if domain is not None and _as_binary(dom, "domain").shape != v.shape:
        raise ValueError("domain shape must match the volume shape %r" % (v.shape,))
    z0, y0, x0, z1, y1, x1 = vol_bounding_box(dom, margin=margin)
    part = np.ascontiguousarray(v[z0:z1, y0:y1, x0:x1], dtype=np.float64)
    return part, (z0, y0, x0)


def vol_uncrop(part, offset, shape, fill=0.0):
    """Paste a cropped sub-volume back into the full frame (inverse of
    :func:`vol_crop_domain`).

    *part* is placed at voxel *offset* ``(z0, y0, x0)`` inside a new
    ``(D, H, W)`` float64 volume of the given *shape*, everything else set to
    *fill* (the 2-D ``full_domain`` restoration, made explicit — the cropped
    result must land at exactly the coordinates it came from). The part must fit
    entirely inside *shape* at *offset*; anything else raises ``ValueError``
    rather than silently clipping data.
    """
    p = _require_volume(part, "part")
    try:
        off = tuple(int(o) for o in offset)
        shp = tuple(int(s) for s in shape)
    except (TypeError, ValueError):
        raise ValueError("offset and shape must be length-3 integer sequences, "
                         "got offset=%r shape=%r" % (offset, shape)) from None
    if len(off) != 3 or len(shp) != 3:
        raise ValueError("offset and shape must have length 3, got offset=%r "
                         "shape=%r" % (offset, shape))
    if any(s < 1 for s in shp):
        raise ValueError("shape must be positive, got %r" % (shape,))
    # plain-int product: np.prod would overflow int64 on absurd shapes and slip
    # past the cap as a negative number, crashing later in the allocation
    if shp[0] * shp[1] * shp[2] > MAX_VOXELS:
        raise ValueError("vol_uncrop: target shape %r exceeds the %d-voxel cap "
                         "(volops.MAX_VOXELS)" % (shp, MAX_VOXELS))
    if any(o < 0 for o in off) or any(o + p.shape[i] > shp[i] for i, o in enumerate(off)):
        raise ValueError("part of shape %r at offset %r does not fit inside %r "
                         "— refusing to clip data" % (p.shape, off, shp))
    out = np.full(shp, float(fill), dtype=np.float64)
    out[off[0]:off[0] + p.shape[0],
        off[1]:off[1] + p.shape[1],
        off[2]:off[2] + p.shape[2]] = p
    return out


# --------------------------------------------------------------------------- #
# boundary — the voxel version of the 2-D region_boundary                      #
# --------------------------------------------------------------------------- #
def _boundary_structure(connectivity, op: str):
    rank = {6: 1, 18: 2, 26: 3}.get(int(connectivity))
    if rank is None:
        raise ValueError("%s: connectivity must be 6, 18 or 26 (3-D "
                         "neighbourhoods), got %r" % (op, connectivity))
    return ndimage.generate_binary_structure(3, rank)


def vol_boundary(vol_binary, connectivity=6, side="inner"):
    """Boundary shell of a binary volume (the 3-D ``region_boundary``).

    ``side='inner'`` keeps the foreground voxels that touch background:
    ``mask & ~erode(mask)``. ``side='outer'`` keeps the background voxels that
    touch foreground: ``dilate(mask) & ~mask``. *connectivity* (6/18/26) decides
    which neighbours count as "touching" — 6 uses face neighbours only (the
    thinnest shell); 26 also counts a diagonal background contact, so shells at
    convex corners come out thicker. The volume border counts as background
    for the *inner* shell (a mask reaching the border has a boundary there —
    the same convention as the surface-area estimate in
    :func:`vol_region_props`); the *outer* shell can only occupy voxels that
    exist, so a mask filling the whole volume has an empty outer boundary.

    A solid region's interior drops out entirely: the shell of a solid ball of
    radius ``r`` voxels is roughly a ``3/r`` fraction of it (surface over
    volume), so the saving grows with size — which is exactly why boundary
    representations (and :func:`vol_boundary_points`) are the memory-frugal way
    to hand a shape to the point-cloud / metrology operators.

    Returns a ``(D, H, W)`` float64 ``{0, 1}`` volume (chainable into
    :func:`vol_label`, :func:`vol_boundary_points`, ...).
    """
    if side not in ("inner", "outer"):
        raise ValueError("side must be 'inner' or 'outer', got %r" % (side,))
    m = _as_binary(vol_binary)
    _check_voxels(m, MAX_VOXELS, "vol_boundary", "MAX_VOXELS")
    st = _boundary_structure(connectivity, "vol_boundary")
    if side == "inner":
        shell = m & ~ndimage.binary_erosion(m, structure=st, border_value=0)
    else:
        shell = ndimage.binary_dilation(m, structure=st) & ~m
    return np.ascontiguousarray(shell, dtype=np.float64)


def vol_boundary_points(vol_binary, spacing=None, connectivity=6, origin=(0, 0, 0)):
    """Boundary shell as an ``(N, 3)`` point cloud in ``(z, y, x)`` order.

    The bridge from the voxel world to the point-cloud world at minimal memory:
    only the *surface* voxels of the mask become points (inner boundary, see
    :func:`vol_boundary`), so a solid object of a million voxels typically
    yields a few tens of thousands of points — ready for ``fit_sphere3`` /
    ``smallest_box3`` / ``register_fpfh`` and friends without ever materialising
    the full grid as points.

    Coordinates are ``(index + origin) * spacing`` per axis: pass *spacing*
    ``(sz, sy, sx)`` (or a :class:`volio.VolumeMeta`) for physical millimetre
    coordinates, and pass the offset returned by :func:`vol_crop_domain` as
    *origin* so points from a cropped volume land in the uncropped frame. An
    empty mask returns an empty ``(0, 3)`` array (a valid question with a valid
    empty answer — unlike a crop, which needs a box to exist).

    Returns an ``(N, 3)`` float64 array, rows ordered z-major (deterministic).
    """
    shell = vol_boundary(vol_binary, connectivity=connectivity, side="inner")
    sp = _spacing_tuple(spacing) or (1.0, 1.0, 1.0)
    try:
        org = tuple(float(o) for o in origin)
    except (TypeError, ValueError):
        raise ValueError("origin must be a length-3 (z0, y0, x0) sequence, "
                         "got %r" % (origin,)) from None
    if len(org) != 3:
        raise ValueError("origin must have length 3, got %r" % (origin,))
    idx = np.argwhere(shell > 0.5).astype(np.float64)
    if idx.size == 0:
        return np.zeros((0, 3), dtype=np.float64)
    return np.ascontiguousarray((idx + np.asarray(org)) * np.asarray(sp))
