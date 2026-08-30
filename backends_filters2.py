"""Classical single-image image->image filters HALCON has but imgevolve did not
yet cover (registry cluster ``filters2``, name prefix ``f2_``).

Every operator here implements the GENUINE algorithm named by its HALCON operator
(the ``Op.halcon`` field is the real, previously-uncovered MVTec operator name):

  f2_shock            shock_filter        Osher-Rudin morphological shock filter
  f2_gray_skeleton    gray_skeleton       thinning of a gray image (bright-region
                                          skeleton lifted back to gray values)
  f2_lut_trans        lut_trans           gray-value look-up-table transform
  f2_topographic      topographic_sketch  Haralick topographic primal sketch
                                          (peak/pit/ridge/ravine/saddle/flat/hillside
                                          from gradient + Hessian eigenvalue signs)
  f2_expand_domain    expand_domain_gray  grow the non-zero domain and fill the new
                                          border pixels from the nearest valid gray
  f2_symmetry         symmetry            local reflective symmetry of gray values
                                          along a row (low response = symmetric)
  f2_gauss_pyramid    gen_gauss_pyramid   one Gauss-pyramid level (down- then
                                          up-sampled back to the original HxW)
  f2_gray_inside      gray_inside         lowest gray value on any path to the border
                                          == grayscale hole-fill (reconstruction by
                                          erosion), a controls the fill depth
  f2_bit_slice        bit_slice           extract one bit-plane of the 8-bit image

Contract: ``fn(v, a, b)`` takes a 2-D float64 image in [0,1] plus two evolution
knobs a,b in [0,1] and returns a 2-D float64 image in [0,1]. Deterministic,
finite, and fail-soft (never raises on the canonical battery).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

try:  # skimage is a repo-wide dependency; guard so import never hard-fails.
    from skimage import morphology as _skmorph
except Exception:  # noqa: BLE001  # pragma: no cover - skimage is present in this env
    _skmorph = None


# --------------------------------------------------------------------------- #
# small helpers                                                               #
# --------------------------------------------------------------------------- #
def _img(v):
    """Coerce input to a finite 2-D float64 image in [0,1] (fail-soft)."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:                       # accidental colour -> luma
        x = x.mean(axis=-1)
    elif x.ndim != 2:
        x = np.atleast_2d(x).astype(np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


def _shift_cols(x, d):
    """result[:, j] = x[:, j - d] with the border replicated (edge-clamped)."""
    if d == 0:
        return x
    W = x.shape[1]
    if d > 0:
        d = min(d, W)
        pad = np.repeat(x[:, :1], d, axis=1)
        return np.concatenate([pad, x[:, :W - d]], axis=1)
    d = min(-d, W)
    pad = np.repeat(x[:, -1:], d, axis=1)
    return np.concatenate([x[:, d:], pad], axis=1)


def _fit(x, H, W):
    """Crop/pad x to exactly (H, W) (zoom can be off by one pixel)."""
    x = np.asarray(x, np.float64)
    h, w = x.shape[:2]
    if h < H:
        x = np.pad(x, ((0, H - h), (0, 0)), mode="edge")
    if w < W:
        x = np.pad(x, ((0, 0), (0, W - w)), mode="edge")
    return x[:H, :W]


# --------------------------------------------------------------------------- #
# operators (module-level so tests can call them directly)                    #
# --------------------------------------------------------------------------- #
def f2_shock(v, a, b):
    """Osher-Rudin shock filter: I_t = -sign(Lap I)*|grad I|, morphological form.

    Each step dilates where the Laplacian is negative (bright/convex side of an
    edge) and erodes where it is positive (dark/concave side); the two flows
    collide at the zero-crossing, forming a shock that sharpens blurred edges.
    ``a`` sets the number of iterations; ``b`` is ignored.
    """
    x = _img(v)
    if x.size < 4:
        return x
    steps = 1 + int(round(float(a) * 9))          # 1..10
    for _ in range(steps):
        lap = ndimage.laplace(x)
        dil = ndimage.grey_dilation(x, size=3, mode="nearest")
        ero = ndimage.grey_erosion(x, size=3, mode="nearest")
        x = np.where(lap < 0, dil, np.where(lap > 0, ero, x))
    return np.clip(x, 0.0, 1.0)


def f2_gray_skeleton(v, a, b):
    """Thinning of a gray-value image: skeletonise the bright region (threshold
    set by ``a``) and lift the 1-px medial ridge back to the original gray
    values. ``b`` is ignored."""
    x = _img(v)
    if _skmorph is None:
        return x
    thr = 0.15 + 0.60 * float(a)                  # bright-region threshold
    mask = x > thr
    if not mask.any():
        return np.zeros_like(x)
    sk = _skmorph.skeletonize(mask)
    return np.clip(x * sk.astype(np.float64), 0.0, 1.0)


def f2_lut_trans(v, a, b):
    """Transform the image through a monotone (gamma-free) gray-value look-up
    table. The 256-entry table is a contrast sigmoid whose gain is set by ``a``
    and pivot by ``b``, endpoint-normalised to span [0,1]; the image is then a
    genuine table lookup on its 8-bit-quantised value."""
    x = _img(v)
    gain = 1.0 + 12.0 * float(a)
    pivot = 0.15 + 0.70 * float(b)
    t = np.linspace(0.0, 1.0, 256)
    raw = 1.0 / (1.0 + np.exp(-gain * (t - pivot)))
    lo, hi = float(raw[0]), float(raw[-1])
    lut = (raw - lo) / (hi - lo) if (hi - lo) > 1e-9 else t   # monotone, spans [0,1]
    idx = np.clip(np.round(x * 255.0), 0, 255).astype(np.intp)
    return np.clip(lut[idx], 0.0, 1.0)


def f2_topographic(v, a, b):
    """Haralick topographic primal sketch: classify every pixel from its gradient
    magnitude and the two Hessian eigenvalue signs into peak / pit / ridge /
    ravine / saddle / flat / hillside and emit the class as a gray code.

    ``a`` sets the derivative smoothing scale; ``b`` sets the "flat gradient"
    tolerance. Codes: flat=0.0, pit=0.14, ravine=0.30, saddle=0.45,
    hillside=0.55, ridge=0.75, peak=1.0.
    """
    x = _img(v)
    if x.size < 4:
        return np.zeros_like(x)
    sigma = 0.6 + 2.5 * float(a)
    xs = ndimage.gaussian_filter(x, sigma)
    gy, gx = np.gradient(xs)
    gmag = np.hypot(gx, gy)
    # np.gradient(arr) -> [d/d(axis0=row=y), d/d(axis1=col=x)], so the SECOND unpacked
    # element is the d/dx component. hyx must be d/dx(gy) (the cross term), not d/dy(gy).
    hyy, hyx = np.gradient(gy)      # hyy = d/dy(gy) = d2/dy2, hyx = d/dx(gy) = d2/dxdy
    hxy, hxx = np.gradient(gx)      # hxy = d/dy(gx) = d2/dydx, hxx = d/dx(gx) = d2/dx2
    off = 0.5 * (hxy + hyx)         # symmetric off-diagonal (avg of the two mixed-partial estimates)
    tr = hxx + hyy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - (hxx * hyy - off * off), 0.0))
    l1 = tr / 2.0 + disc            # larger eigenvalue
    l2 = tr / 2.0 - disc            # smaller eigenvalue
    gt = (0.02 + 0.08 * float(b)) * (float(gmag.max()) + 1e-12)
    emax = float(np.maximum(np.abs(l1), np.abs(l2)).max()) + 1e-12
    et = 0.05 * emax
    flat_g = gmag < gt
    code = np.full(x.shape, 0.55)                       # hillside default
    # non-flat-gradient ridges/ravines
    code[(~flat_g) & (l2 < -et)] = 0.75                 # ridge
    code[(~flat_g) & (l1 > et)] = 0.30                  # ravine
    # flat-gradient (critical) points
    code[flat_g & (np.abs(l1) <= et) & (np.abs(l2) <= et)] = 0.0   # flat
    code[flat_g & (l1 > et) & (l2 < -et)] = 0.45        # saddle
    code[flat_g & (l1 < -et) & (l2 < -et)] = 1.0        # peak
    code[flat_g & (l1 > et) & (l2 > et)] = 0.14         # pit
    # degenerate critical lines (2026-08-30 review): the crest of a straight ridge is
    # translation-invariant, so gmag == 0 there with only ONE significant eigenvalue —
    # Haralick classes it ridge/ravine, but no flat-case matched and it fell through
    # to the hillside default.
    code[flat_g & (np.abs(l1) <= et) & (l2 < -et)] = 0.75   # ridge crest
    code[flat_g & (np.abs(l2) <= et) & (l1 > et)] = 0.30    # ravine trough
    return np.clip(code, 0.0, 1.0)


def f2_expand_domain(v, a, b):
    """Expand the domain of the image (the non-zero region) outward by a margin
    and set the new pixels to the nearest existing gray value. ``a`` sets the
    margin width (1..7 px); ``b`` is ignored."""
    x = _img(v)
    width = 1 + int(round(float(a) * 6))          # 1..7
    valid = x > 0.0
    if not valid.any() or valid.all():
        return x
    dist, (iy, ix) = ndimage.distance_transform_edt(~valid, return_indices=True)
    out = x.copy()
    grow = (~valid) & (dist <= width)
    out[grow] = x[iy[grow], ix[grow]]
    return np.clip(out, 0.0, 1.0)


def f2_symmetry(v, a, b):
    """Local reflective symmetry of gray values along a row. For each pixel the
    weighted asymmetry sum_d (1/d)|I(i,j-d) - I(i,j+d)| over d=1..r is measured;
    a low response means the neighbourhood is left-right symmetric about that
    column. ``a`` sets the radius r (1..6); ``b`` is ignored. Output is the
    asymmetry response normalised to [0,1]."""
    x = _img(v)
    r = 1 + int(round(float(a) * 5))              # 1..6
    asym = np.zeros_like(x)
    wsum = 0.0
    for d in range(1, r + 1):
        w = 1.0 / d
        asym += w * np.abs(_shift_cols(x, d) - _shift_cols(x, -d))
        wsum += w
    if wsum > 0:
        asym /= wsum
    m = float(asym.max())
    return np.clip(asym / m, 0.0, 1.0) if m > 1e-8 else np.zeros_like(x)


def f2_gauss_pyramid(v, a, b):
    """Return one level of the image's Gauss pyramid, down-sampled by 2 ``level``
    times (blur + decimate) and then up-sampled back to the original HxW so the
    result is a band-limited (low-pass) version at reduced resolution. ``a``
    selects the level (1..4); ``b`` is ignored."""
    x = _img(v)
    H, W = x.shape
    level = 1 + int(round(float(a) * 3))          # 1..4
    cur = x
    for _ in range(level):
        cur = ndimage.gaussian_filter(cur, 1.0)
        cur = cur[::2, ::2]
        if min(cur.shape) < 2:
            break
    zy, zx = H / cur.shape[0], W / cur.shape[1]
    up = ndimage.zoom(cur, (zy, zx), order=1) if (zy != 1.0 or zx != 1.0) else cur
    return np.clip(_fit(up, H, W), 0.0, 1.0)


def f2_gray_inside(v, a, b):
    """Grayscale hole-fill: for each pixel, the lowest gray value attainable on
    any path to the image border == morphological reconstruction of the image by
    erosion from a border-anchored marker. Dark basins enclosed by brighter walls
    are raised toward the wall height; regions connected to the border stay dark.
    ``a`` sets the maximum fill depth h (0 = none, 1 = full); ``b`` is ignored."""
    x = _img(v)
    if _skmorph is None or x.size < 4:
        return x
    h = 0.02 + 0.98 * float(a)
    marker = np.minimum(x + h, 1.0)
    marker[0, :] = x[0, :]
    marker[-1, :] = x[-1, :]
    marker[:, 0] = x[:, 0]
    marker[:, -1] = x[:, -1]
    marker = np.maximum(marker, x)                # reconstruction needs seed >= mask
    rec = _skmorph.reconstruction(marker, x, method="erosion")
    return np.clip(rec, 0.0, 1.0)


def f2_bit_slice(v, a, b):
    """Extract one bit-plane of the image after 8-bit quantisation. ``a`` selects
    the plane (0 = LSB .. 7 = MSB); ``b`` is ignored. Returns a {0,1} image."""
    x = _img(v)
    q = np.clip(np.round(x * 255.0), 0, 255).astype(np.uint8)
    plane = int(round(float(a) * 7))              # 0..7
    return ((q >> plane) & 1).astype(np.float64)


# --------------------------------------------------------------------------- #
# registry hook                                                               #
# --------------------------------------------------------------------------- #
def _safe(fn):
    """Wrap so a fn never raises on odd input; degrade to a clipped copy."""
    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:  # noqa: BLE001  # fail-soft: an op must never raise
            out = None
        if out is None:
            return _img(v)
        arr = np.asarray(out, np.float64)
        arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
        return np.clip(arr, 0.0, 1.0)
    return w


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    defs = [
        ("f2_shock", "edges", "shock_filter", f2_shock),
        ("f2_gray_skeleton", "morphology", "gray_skeleton", f2_gray_skeleton),
        ("f2_lut_trans", "gray", "lut_trans", f2_lut_trans),
        ("f2_topographic", "edges", "topographic_sketch", f2_topographic),
        ("f2_expand_domain", "gray", "expand_domain_gray", f2_expand_domain),
        ("f2_symmetry", "texture", "symmetry", f2_symmetry),
        ("f2_gauss_pyramid", "smoothing", "gen_gauss_pyramid", f2_gauss_pyramid),
        ("f2_gray_inside", "morphology", "gray_inside", f2_gray_inside),
        ("f2_bit_slice", "gray", "bit_slice", f2_bit_slice),
    ]
    return [Op(name, cat, hal, IMAGE, IMAGE, _safe(fn)) for (name, cat, hal, fn) in defs]
