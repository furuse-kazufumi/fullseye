"""Stereo depth building blocks (numpy + scipy only).

Dense two-frame stereo by fronto-parallel block matching — the first piece of a
perception stack that turns two views into depth, and depth into a terrain
heightmap / point cloud for locomotion and grasping. It builds on the same
windowed normalized-correlation idea as the (now-correct) NCC template operator,
and on the geometric-transform ops used for rectification.

Convention: `left` and `right` are **rectified** grayscale images of equal shape
with horizontal epipolar lines, and a scene feature at left column ``c`` appears
in the right image at column ``c - d`` for disparity ``d >= 0`` (nearer surfaces
-> larger ``d``). Depth follows ``Z = focal * baseline / d``.

Reference: Scharstein & Szeliski, "A Taxonomy and Evaluation of Dense Two-Frame
Stereo Correspondence Algorithms", IJCV 2002 (public literature — reimplemented,
not derived from any product).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["disparity_map", "disparity_subpixel", "lr_consistency",
           "depth_from_disparity", "reproject_to_points",
           "census_transform", "disparity_census", "disparity_sgm",
           "speckle_filter", "fill_disparity", "disparity_confidence"]


def _shift_right_cols(R: np.ndarray, d: int) -> np.ndarray:
    """Return ``Rd`` with ``Rd[y, x] = R[y, x - d]`` (edge-replicated on the left)."""
    if d == 0:
        return R
    Rd = np.empty_like(R)
    Rd[:, d:] = R[:, :-d]
    Rd[:, :d] = R[:, :1]
    return Rd


def _cost_volume(L: np.ndarray, R: np.ndarray, max_disp: int, block: int,
                 method: str) -> np.ndarray:
    """Per-disparity matching cost volume ``vol[d, y, x]`` (lower = better).

    The same windowed SAD/SSD/(1-NCC) cost the winner-take-all matcher argmin's
    over — sharing it lets the sub-pixel refiner read the cost curvature."""
    H, W = L.shape
    k = int(block)

    def box(a):
        return ndimage.uniform_filter(a, k, mode="nearest")

    D = int(max_disp)
    vol = np.empty((D + 1, H, W), np.float64)
    if method == "ncc":
        lz = L - box(L)
        el = box(lz * lz)
    for d in range(0, D + 1):
        Rd = _shift_right_cols(R, d)
        if method == "sad":
            vol[d] = box(np.abs(L - Rd))
        elif method == "ssd":
            vol[d] = box((L - Rd) ** 2)
        elif method == "ncc":
            rz = Rd - box(Rd)
            den = np.sqrt(np.maximum(el * box(rz * rz), 1e-12))
            vol[d] = 1.0 - box(lz * rz) / den          # 1 - NCC: 0 = perfect match
        else:
            raise ValueError("method must be sad|ssd|ncc, got %r" % method)
    return vol


def disparity_map(left, right, max_disp: int = 16, block: int = 7,
                  method: str = "sad", reference: str = "left") -> np.ndarray:
    """Dense disparity by winner-take-all block matching.

    Parameters
    ----------
    left, right : (H, W) float arrays in [0, 1], rectified, same shape.
    max_disp    : largest disparity searched (0..max_disp inclusive).
    block       : matching window side (odd).
    method      : 'sad' (default), 'ssd', or 'ncc' (zero-mean normalized).
    reference   : 'left' (default) indexes the map by left-image columns; 'right'
                  indexes it by right-image columns (the map needed for a
                  left-right consistency check — see :func:`lr_consistency`).

    Returns the per-pixel disparity (float, 0..max_disp). Border columns that
    never have full overlap are left at their best in-range match.
    """
    L = np.asarray(left, np.float64)
    R = np.asarray(right, np.float64)
    if L.shape != R.shape or L.ndim != 2:
        raise ValueError("left/right must be equal-shape 2-D arrays")
    if reference == "right":
        # right-referenced disparity via the standard mirror identity:
        # flip both, swap roles, run the left matcher, flip the result back.
        d = disparity_map(R[:, ::-1], L[:, ::-1], max_disp, block, method, "left")
        return d[:, ::-1]
    if reference != "left":
        raise ValueError("reference must be 'left' or 'right', got %r" % reference)
    return _cost_volume(L, R, max_disp, block, method).argmin(0).astype(np.float64)


def disparity_subpixel(left, right, max_disp: int = 16, block: int = 7,
                       method: str = "ssd") -> np.ndarray:
    """Disparity refined to sub-pixel precision by a parabola fit.

    Fits ``a·x² + b·x + c`` through the winning cost and its two neighbours and
    takes the parabola's vertex, so a surface whose true disparity is 5.4 reads
    ~5.4 instead of snapping to the integer 5. 'ssd'/'ncc' give a smoother cost
    curve than 'sad' and refine more accurately. Pixels whose winner sits at the
    search-range border keep their integer disparity."""
    L = np.asarray(left, np.float64)
    R = np.asarray(right, np.float64)
    if L.shape != R.shape or L.ndim != 2:
        raise ValueError("left/right must be equal-shape 2-D arrays")
    vol = _cost_volume(L, R, max_disp, block, method)
    D = vol.shape[0]
    d = vol.argmin(0)
    dm = np.clip(d - 1, 0, D - 1)[None]
    dp = np.clip(d + 1, 0, D - 1)[None]
    c0 = np.take_along_axis(vol, d[None], 0)[0]
    cm = np.take_along_axis(vol, dm, 0)[0]
    cp = np.take_along_axis(vol, dp, 0)[0]
    denom = cm - 2.0 * c0 + cp                      # >0 at a convex minimum
    offset = np.where(denom > 1e-12, 0.5 * (cm - cp) / denom, 0.0)
    offset = np.clip(offset, -0.5, 0.5)
    interior = (d > 0) & (d < D - 1)
    return d.astype(np.float64) + np.where(interior, offset, 0.0)


def lr_consistency(disp_left, disp_right, max_diff: float = 1.0):
    """Left-right consistency mask (True = disparity is trustworthy).

    A correct left disparity ``dL`` at column ``x`` should be echoed by the
    right-referenced map at the matched column ``x - dL``. Where the two disagree
    by more than *max_diff* the pixel is an occlusion or a mismatch and should be
    dropped. Pass the ``reference='left'`` and ``reference='right'`` disparity
    maps of the same pair."""
    dL = np.asarray(disp_left, np.float64)
    dR = np.asarray(disp_right, np.float64)
    if dL.shape != dR.shape or dL.ndim != 2:
        raise ValueError("disparity maps must be equal-shape 2-D arrays")
    W = dL.shape[1]
    xx = np.arange(W)[None, :]
    xr_raw = np.round(xx - dL).astype(int)
    # a matched column outside [0, W) has no correspondence to check -> not
    # trustworthy (clamping it to column 0 would fabricate an agreement on the
    # left overlap-free margin, which is exactly what this check must reject).
    valid = (xr_raw >= 0) & (xr_raw < W)
    xr = np.clip(xr_raw, 0, W - 1)
    dR_at = np.take_along_axis(dR, xr, axis=1)
    return valid & (np.abs(dL - dR_at) <= float(max_diff))


def depth_from_disparity(disp, focal: float = 1.0, baseline: float = 1.0,
                         min_disp: float = 1e-6) -> np.ndarray:
    """Metric depth ``Z = focal * baseline / disparity``.

    Pixels with ``disparity <= min_disp`` (no measurable parallax -> infinitely
    far / unmatched) are returned as ``inf``.
    """
    d = np.asarray(disp, np.float64)
    z = np.full_like(d, np.inf)
    m = d > min_disp
    z[m] = float(focal) * float(baseline) / d[m]
    return z


def reproject_to_points(depth, fx: float = 1.0, fy: float = 1.0,
                        cx: float | None = None, cy: float | None = None):
    """Back-project a depth map to a camera-frame point cloud (N, 3) of finite
    points. Pinhole model: X = (u-cx)*Z/fx, Y = (v-cy)*Z/fy, Z = depth."""
    Z = np.asarray(depth, np.float64)
    H, W = Z.shape
    cx = (W - 1) / 2.0 if cx is None else cx
    cy = (H - 1) / 2.0 if cy is None else cy
    v, u = np.mgrid[0:H, 0:W]
    finite = np.isfinite(Z)
    zz = Z[finite]
    xx = (u[finite] - cx) * zz / float(fx)
    yy = (v[finite] - cy) * zz / float(fy)
    return np.stack([xx, yy, zz], axis=1)


# --- census / illumination-robust matching ---------------------------------- #
def _popcount64(x: np.ndarray) -> np.ndarray:
    """Vectorized population count for a uint64 array (SWAR bit-twiddling)."""
    x = x.astype(np.uint64)
    m1 = np.uint64(0x5555555555555555)
    m2 = np.uint64(0x3333333333333333)
    m4 = np.uint64(0x0F0F0F0F0F0F0F0F)
    h01 = np.uint64(0x0101010101010101)
    x = x - ((x >> np.uint64(1)) & m1)
    x = (x & m2) + ((x >> np.uint64(2)) & m2)
    x = (x + (x >> np.uint64(4))) & m4
    return (x * h01) >> np.uint64(56)


def census_transform(img, window: int = 5) -> np.ndarray:
    """Census transform: encode each pixel by which of its neighbours it exceeds
    (Zabih & Woodfill, ECCV 1994).

    Returns a ``uint64`` code per pixel (window must be odd, ``window^2 - 1 <= 64``
    neighbours -> window <= 7). Because the code depends only on the *ordering* of
    intensities, it is invariant to any monotonic photometric change (gain +
    offset, vignetting) — which is exactly why census-based matching survives the
    left/right exposure differences that break raw SAD/SSD."""
    a = np.asarray(img, np.float64)
    if a.ndim != 2:
        raise ValueError("img must be 2-D")
    w = int(window)
    if w % 2 == 0 or w < 3:
        raise ValueError("window must be odd and >= 3")
    if w * w - 1 > 64:
        raise ValueError("window too large: %d neighbours exceed 64 bits" % (w * w - 1))
    pad = w // 2
    P = np.pad(a, pad, mode="edge")
    H, W = a.shape
    code = np.zeros((H, W), np.uint64)
    k = 0
    for dy in range(w):
        for dx in range(w):
            if dy == pad and dx == pad:
                continue
            neigh = P[dy:dy + H, dx:dx + W]
            bit = (a > neigh).astype(np.uint64) << np.uint64(k)
            code |= bit
            k += 1
    return code


def _census_cost_volume(Lc: np.ndarray, Rc: np.ndarray, D: int) -> np.ndarray:
    """Per-disparity Hamming-distance cost volume ``vol[d, y, x]`` of two census
    images (lower = better match)."""
    H, W = Lc.shape
    vol = np.empty((D + 1, H, W), np.float64)
    for d in range(D + 1):
        Rd = _shift_right_cols(Rc, d)
        vol[d] = _popcount64(Lc ^ Rd).astype(np.float64)
    return vol


def disparity_census(left, right, max_disp: int = 16, window: int = 5) -> np.ndarray:
    """Dense disparity by census + Hamming winner-take-all.

    Illumination-robust alternative to :func:`disparity_map`: matches the census
    codes (intensity *orderings*) instead of raw intensities, so a global gain /
    exposure difference between the two views no longer biases the match. Returns
    the per-pixel disparity (float, 0..max_disp), left-referenced."""
    L = np.asarray(left, np.float64)
    R = np.asarray(right, np.float64)
    if L.shape != R.shape or L.ndim != 2:
        raise ValueError("left/right must be equal-shape 2-D arrays")
    Lc = census_transform(L, window)
    Rc = census_transform(R, window)
    return _census_cost_volume(Lc, Rc, int(max_disp)).argmin(0).astype(np.float64)


def _sgm_penalty(prev: np.ndarray, P1: float, P2: float) -> np.ndarray:
    """One SGM aggregation step for a line of pixels: ``prev`` is (M, D) previous
    path costs, returns the penalized term (M, D) already offset by ``min_d prev``."""
    mn = prev.min(1, keepdims=True)
    left = np.full_like(prev, np.inf)
    left[:, 1:] = prev[:, :-1] + P1
    right = np.full_like(prev, np.inf)
    right[:, :-1] = prev[:, 1:] + P1
    term = np.minimum(np.minimum(prev, left), np.minimum(right, mn + P2))
    return term - mn


def _aggregate_dir(C: np.ndarray, sy: int, sx: int, P1: float, P2: float) -> np.ndarray:
    """Aggregate the (H, W, D) cost volume along one cardinal path (sy, sx)."""
    H, W, _ = C.shape
    L = C.copy()
    if sx != 0:                                    # horizontal scan, vectorize over rows
        xs = range(1, W) if sx > 0 else range(W - 2, -1, -1)
        for x in xs:
            L[:, x, :] = C[:, x, :] + _sgm_penalty(L[:, x - sx, :], P1, P2)
    else:                                          # vertical scan, vectorize over cols
        ys = range(1, H) if sy > 0 else range(H - 2, -1, -1)
        for y in ys:
            L[y, :, :] = C[y, :, :] + _sgm_penalty(L[y - sy, :, :], P1, P2)
    return L


def disparity_sgm(left, right, max_disp: int = 16, window: int = 5,
                  P1: float = 5.0, P2: float = 50.0, paths: int = 4) -> np.ndarray:
    """Semi-Global Matching disparity (Hirschmüller, CVPR 2005 / PAMI 2008).

    Aggregates a census matching cost along several 1-D paths under a smoothness
    penalty (``P1`` for a +/-1 disparity step, ``P2`` for larger jumps), then takes
    the winner. The path aggregation approximates a 2-D smoothness prior, so the
    result has far fewer isolated mismatches than the raw winner-take-all
    :func:`disparity_census` / :func:`disparity_map` — the standard high-quality
    passive-stereo method. ``paths`` is 2 (horizontal only) or 4 (cardinal, the
    default 4-path variant). Returns per-pixel disparity (float), left-referenced."""
    L = np.asarray(left, np.float64)
    R = np.asarray(right, np.float64)
    if L.shape != R.shape or L.ndim != 2:
        raise ValueError("left/right must be equal-shape 2-D arrays")
    if paths not in (2, 4):
        raise ValueError("paths must be 2 or 4")
    D = int(max_disp)
    vol = _census_cost_volume(census_transform(L, window),
                              census_transform(R, window), D)
    C = np.moveaxis(vol, 0, -1)                    # (H, W, D)
    dirs = [(0, 1), (0, -1)] + ([(1, 0), (-1, 0)] if paths == 4 else [])
    S = np.zeros_like(C)
    for sy, sx in dirs:
        S += _aggregate_dir(C, sy, sx, float(P1), float(P2))
    return S.argmin(-1).astype(np.float64)


# --- disparity post-processing ---------------------------------------------- #
def speckle_filter(disp, max_diff: float = 1.0, min_size: int = 50):
    """Remove small speckle regions from a disparity map (Hirschmüller 2008 / the
    OpenCV ``filterSpeckles`` idea).

    Connects 4-neighbour pixels whose disparities differ by <= *max_diff* into
    regions and invalidates (sets to ``NaN``) any region with fewer than *min_size*
    pixels — the isolated mismatches a stereo matcher sprays into textureless or
    occluded areas. Returns ``(cleaned_disp, valid_mask)``."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components

    d = np.asarray(disp, np.float64)
    if d.ndim != 2:
        raise ValueError("disp must be 2-D")
    H, W = d.shape
    n = H * W
    ids = np.arange(n).reshape(H, W)
    edges_r, edges_c = [], []
    hor = np.abs(d[:, 1:] - d[:, :-1]) <= max_diff
    edges_r.append(ids[:, :-1][hor]); edges_c.append(ids[:, 1:][hor])
    ver = np.abs(d[1:, :] - d[:-1, :]) <= max_diff
    edges_r.append(ids[:-1, :][ver]); edges_c.append(ids[1:, :][ver])
    r = np.concatenate(edges_r) if edges_r else np.zeros(0, int)
    c = np.concatenate(edges_c) if edges_c else np.zeros(0, int)
    graph = csr_matrix((np.ones(r.size + c.size),
                        (np.concatenate([r, c]), np.concatenate([c, r]))), shape=(n, n))
    ncomp, labels = connected_components(graph, directed=False)
    sizes = np.bincount(labels, minlength=ncomp)
    valid = (sizes[labels] >= min_size).reshape(H, W)
    out = d.copy()
    out[~valid] = np.nan
    return out, valid


def fill_disparity(disp, valid=None) -> np.ndarray:
    """Fill invalid disparities by row-wise interpolation, biased to the background.

    For each invalid pixel takes the nearer of its left/right valid neighbours in
    the same row and keeps the *smaller* disparity (the farther, background surface)
    — the standard hole-filling for occlusion gaps left by an L/R consistency check
    or :func:`speckle_filter`. ``valid`` is the trust mask (default: finite &
    positive). Rows with no valid pixel stay ``NaN``. Returns the filled map."""
    d = np.asarray(disp, np.float64).copy()
    if valid is None:
        valid = np.isfinite(d) & (d > 0)
    else:
        valid = np.asarray(valid, bool)
    H, W = d.shape
    cols = np.arange(W)[None, :]
    # forward fill: index of last valid pixel at or before each column (-1 if none)
    fidx = np.where(valid, cols, -1)
    fidx = np.maximum.accumulate(fidx, axis=1)
    # backward fill: index of next valid pixel at or after each column (W if none)
    bidx = np.where(valid, cols, W)
    bidx = np.minimum.accumulate(bidx[:, ::-1], axis=1)[:, ::-1]
    rows = np.arange(H)[:, None]
    fval = np.where(fidx >= 0, d[rows, np.clip(fidx, 0, W - 1)], np.nan)
    bval = np.where(bidx < W, d[rows, np.clip(bidx, 0, W - 1)], np.nan)
    filled = np.fmin(fval, bval)                   # smaller = background; ignores NaN
    out = np.where(valid, d, filled)
    return out


def disparity_confidence(left, right, max_disp: int = 16, block: int = 7,
                         method: str = "ssd") -> np.ndarray:
    """Per-pixel matching confidence in [0, 1] from the cost curve (PKRN-style).

    Compares the best matching cost ``c1`` with the second-best ``c2``:
    ``conf = 1 - c1 / c2``. A sharp, unambiguous minimum (well-textured pixel) gives
    ``conf -> 1``; a flat cost curve (textureless / repetitive region where the
    disparity is untrustworthy) gives ``conf -> 0``. Use it to gate depth before
    building a cloud. Returns (H, W)."""
    L = np.asarray(left, np.float64)
    R = np.asarray(right, np.float64)
    if L.shape != R.shape or L.ndim != 2:
        raise ValueError("left/right must be equal-shape 2-D arrays")
    vol = _cost_volume(L, R, int(max_disp), int(block), method)
    part = np.sort(vol, axis=0)                    # ascending cost per pixel
    c1 = part[0]
    c2 = part[1] if part.shape[0] > 1 else part[0]
    conf = 1.0 - c1 / np.where(c2 < 1e-12, 1e-12, c2)
    return np.clip(conf, 0.0, 1.0)
