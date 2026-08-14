"""Sub-pixel critical-point extraction (image -> contour point sets).

HALCON has a family of operators that locate the *critical points* of a gray-value
surface with sub-pixel precision: `local_max_sub_pix`, `local_min_sub_pix`,
`saddle_points_sub_pix`, `critical_points_sub_pix`, plus the region operators
`plateaus` (connected flat regions) and `lowlands`/`lowlands_center` (basin
centres). This module implements those genuinely and exposes them as `sp_*` ops
whose out_sort is CONTOUR — a dict ``{"shape": (H, W), "cs": [Nx2 (row, col)]}``.
Each detected point is returned as its own single-point (1x2) sub-contour so the
downstream ``count_contours`` feature reports the number of critical points.

Method (genuine, deterministic):
  * A discrete extremum is a pixel strictly greater (max) / less (min) than all 8
    of its neighbours.  Its position is refined to sub-pixel by fitting a 2-D
    quadratic  z = a0 + a1 x + a2 y + a3 x^2 + a4 y^2 + a5 xy  to the 3x3
    neighbourhood (least squares — a fixed pseudo-inverse), then solving
    grad z = 0  ->  offset = -H^{-1} g  (with a separable 1-D parabola fallback
    when the fitted Hessian is degenerate).
  * A saddle is a pixel whose 3x3 quadratic fit has an indefinite Hessian
    (det H < 0, i.e. mixed-sign eigenvalues) and whose critical offset falls
    inside the pixel cell (|dx|,|dy| <= 0.5).
  * `plateaus` = connected components of (quantised-)equal gray value; centroids
    returned as points.  `lowlands_center` = those flat components that are
    *regional minima* (every neighbouring pixel outside the component is strictly
    higher); basin centroids returned as points.

Knob ``a`` controls the detection threshold / minimum prominence (peak depth for
extrema, basin depth for lowlands, minimum area for plateaus); ``b`` is unused.
Same contract as the other backend modules: ``build()`` returns typed ``Op``
wrappers, each exception-safe and finite.
"""
from __future__ import annotations

import numpy as np

# --------------------------------------------------------------------------- #
# Fixed 3x3 quadratic-fit pseudo-inverse.                                      #
# Basis [1, x, y, x^2, y^2, x*y] over the 9 offsets (dy, dx) in {-1,0,1}^2,    #
# row-major (dy outer, dx inner) so index 4 == the centre (0, 0).             #
# --------------------------------------------------------------------------- #
_OFFS = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
_X = np.array([[1.0, dx, dy, dx * dx, dy * dy, dx * dy] for (dy, dx) in _OFFS])
_MINV = np.linalg.pinv(_X)  # (6, 9): coeffs = _MINV @ zvals


def _as_image(v):
    """Coerce input to a 2-D float64 image in [0, 1]; None if not usable."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:
        x = x.mean(-1)
    if x.ndim != 2 or x.size == 0:
        return None
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


def _points_dict(shape, pts):
    """Wrap (row, col) points as CONTOUR dict — one 1x2 sub-contour per point."""
    cs = []
    H, W = shape
    for r, c in pts:
        r = float(np.clip(r, 0.0, H - 1))
        c = float(np.clip(c, 0.0, W - 1))
        if np.isfinite(r) and np.isfinite(c):
            cs.append(np.array([[r, c]], np.float64))
    return {"shape": (int(shape[0]), int(shape[1])), "cs": cs}


def _fit_grid(v):
    """Fit the 3x3 quadratic at every interior pixel.

    Returns (S, coeffs) where S is (9, M) the stacked neighbourhood values and
    coeffs is (6, M) the fitted coefficients, for the interior grid of shape
    (H-2, W-2).  None when there is no interior.
    """
    H, W = v.shape
    if H < 3 or W < 3:
        return None
    cols = []
    for (dy, dx) in _OFFS:
        cols.append(v[1 + dy:H - 1 + dy, 1 + dx:W - 1 + dx].ravel())
    S = np.stack(cols, 0)          # (9, M)
    coeffs = _MINV @ S             # (6, M)
    return S, coeffs


def _offsets(coeffs):
    """Sub-pixel offset (dx, dy) of the fitted quadratic's critical point.

    dx is along columns, dy along rows.  Uses -H^{-1} g; where the Hessian is
    (near-)singular the offset is left at 0 (caller may substitute a separable
    estimate).  Also returns det(H) and the flag of which offsets are safe.
    """
    c1, c2, c3, c4, c5 = coeffs[1], coeffs[2], coeffs[3], coeffs[4], coeffs[5]
    det = 4.0 * c3 * c4 - c5 * c5
    safe = np.abs(det) > 1e-9
    dx = np.zeros_like(det)
    dy = np.zeros_like(det)
    d = np.where(safe, det, 1.0)
    dx = np.where(safe, -(2.0 * c4 * c1 - c5 * c2) / d, 0.0)
    dy = np.where(safe, -(-c5 * c1 + 2.0 * c3 * c2) / d, 0.0)
    return dx, dy, det, safe


def _sep_offsets(S):
    """Separable 1-D parabola offsets from the 3x3 cross (fallback for extrema).

    S index map: 1=up(dy-1), 7=down(dy+1), 3=left(dx-1), 5=right(dx+1), 4=centre.
    """
    left, right, cen = S[3], S[5], S[4]
    up, down = S[1], S[7]
    denx = left - 2.0 * cen + right
    deny = up - 2.0 * cen + down
    dx = np.where(np.abs(denx) > 1e-12, 0.5 * (left - right) / np.where(np.abs(denx) > 1e-12, denx, 1.0), 0.0)
    dy = np.where(np.abs(deny) > 1e-12, 0.5 * (up - down) / np.where(np.abs(deny) > 1e-12, deny, 1.0), 0.0)
    return np.clip(dx, -0.5, 0.5), np.clip(dy, -0.5, 0.5)


def _extrema(v, a, want_max):
    """Sub-pixel local maxima (want_max) or minima points."""
    img = _as_image(v)
    if img is None:
        return _points_dict((1, 1), [])
    fit = _fit_grid(img)
    if fit is None:
        return _points_dict(img.shape, [])
    S, coeffs = fit
    Wi = img.shape[1] - 2
    cen = S[4]
    others = np.delete(S, 4, axis=0)      # (8, M)
    if want_max:
        is_ext = cen > others.max(0)
        prom = cen - S.min(0)             # depth below the deepest neighbour
    else:
        is_ext = cen < others.min(0)
        prom = S.max(0) - cen
    thr = 0.01 + 0.30 * float(np.clip(a, 0.0, 1.0))
    keep = is_ext & (prom >= thr) & np.isfinite(prom)

    dxq, dyq, _det, safe = _offsets(coeffs)
    dxs, dys = _sep_offsets(S)
    # Prefer the full-3x3 quadratic offset when it is well-posed and stays in the
    # cell; otherwise fall back to the separable 1-D parabola.
    use_q = safe & (np.abs(dxq) <= 1.0) & (np.abs(dyq) <= 1.0)
    dx = np.where(use_q, dxq, dxs)
    dy = np.where(use_q, dyq, dys)
    dx = np.clip(dx, -1.0, 1.0)
    dy = np.clip(dy, -1.0, 1.0)

    idx = np.where(keep)[0]
    rows = (idx // Wi) + 1
    cols = (idx % Wi) + 1
    pts = [(rows[k] + dy[idx[k]], cols[k] + dx[idx[k]]) for k in range(idx.size)]
    return _points_dict(img.shape, pts)


def _saddles(v, a):
    """Sub-pixel saddle points: indefinite Hessian, critical point inside cell."""
    img = _as_image(v)
    if img is None:
        return _points_dict((1, 1), [])
    fit = _fit_grid(img)
    if fit is None:
        return _points_dict(img.shape, [])
    _, coeffs = fit
    Wi = img.shape[1] - 2
    dx, dy, det, safe = _offsets(coeffs)
    # Saddle prominence = the smaller |principal curvature| (both axes must
    # genuinely curve); scale-robust unlike raw |det|.
    strength = np.minimum(np.abs(2.0 * coeffs[3]), np.abs(2.0 * coeffs[4]))
    thr = 1e-4 + 0.02 * float(np.clip(a, 0.0, 1.0))
    keep = safe & (det < 0.0) & (np.abs(dx) <= 0.5) & (np.abs(dy) <= 0.5) & (strength >= thr)
    idx = np.where(keep)[0]
    rows = (idx // Wi) + 1
    cols = (idx % Wi) + 1
    pts = [(rows[k] + dy[idx[k]], cols[k] + dx[idx[k]]) for k in range(idx.size)]
    return _points_dict(img.shape, pts)


def _critical(v, a):
    """Union of sub-pixel maxima, minima and saddle points (points only)."""
    img = _as_image(v)
    if img is None:
        return _points_dict((1, 1), [])
    mx = _extrema(img, a, True)
    mn = _extrema(img, a, False)
    sd = _saddles(img, a)
    cs = mx["cs"] + mn["cs"] + sd["cs"]
    return {"shape": mx["shape"], "cs": cs}


# --------------------------------------------------------------------------- #
# Flat-region components (plateaus) and regional-minima basins (lowlands).     #
# --------------------------------------------------------------------------- #
def _flat_components(v, q):
    """Label connected components of equal quantised gray value (4-connectivity).

    Returns an int label image (same shape).  Union-find over the equality graph:
    two 4-neighbours join iff they share the same quantised level.  Bounded by
    the number of equal adjacencies (≈0 for noisy images, all edges for flats).
    """
    H, W = v.shape
    q = max(float(q), 1e-9)
    L = np.round(v / q).astype(np.int64)
    n = H * W
    parent = np.arange(n)

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    idx = np.arange(n).reshape(H, W)
    eqh = np.where(L[:, 1:] == L[:, :-1])
    for y, x in zip(eqh[0], eqh[1]):
        union(int(idx[y, x]), int(idx[y, x + 1]))
    eqv = np.where(L[1:, :] == L[:-1, :])
    for y, x in zip(eqv[0], eqv[1]):
        union(int(idx[y, x]), int(idx[y + 1, x]))

    roots = np.array([find(i) for i in range(n)]).reshape(H, W)
    return roots


def _plateaus(v, a, b):
    """Connected flat regions -> their centroid points."""
    img = _as_image(v)
    if img is None:
        return _points_dict((1, 1), [])
    H, W = img.shape
    if H * W > 200_000:                       # fail-soft guard on huge inputs
        return _points_dict(img.shape, [])
    aa = float(np.clip(a, 0.0, 1.0))
    q = 1e-6 + 0.05 * aa                       # flatness tolerance grows with a
    min_area = 2 + int(round(aa * 6))          # min plateau area grows with a
    roots = _flat_components(img, q)
    labels, counts = np.unique(roots, return_counts=True)
    yy, xx = np.mgrid[0:H, 0:W]
    pts = []
    for lab, cnt in zip(labels, counts):
        if cnt < min_area:
            continue
        m = roots == lab
        pts.append((float(yy[m].mean()), float(xx[m].mean())))
    return _points_dict(img.shape, pts)


def _lowlands_center(v, a, b):
    """Regional-minima basins -> their centroid points."""
    img = _as_image(v)
    if img is None:
        return _points_dict((1, 1), [])
    H, W = img.shape
    if H * W > 200_000:
        return _points_dict(img.shape, [])
    aa = float(np.clip(a, 0.0, 1.0))
    q = 1e-6 + 0.05 * aa
    min_depth = 0.01 + 0.40 * aa               # basin depth threshold grows with a
    roots = _flat_components(img, q)
    labels = np.unique(roots)
    yy, xx = np.mgrid[0:H, 0:W]
    pts = []
    for lab in labels:
        m = roots == lab
        val = float(img[m].mean())
        # 4-connected outer boundary of this component.
        up = np.zeros_like(m); up[:-1, :] = m[1:, :]
        dn = np.zeros_like(m); dn[1:, :] = m[:-1, :]
        lf = np.zeros_like(m); lf[:, :-1] = m[:, 1:]
        rt = np.zeros_like(m); rt[:, 1:] = m[:, :-1]
        border = (up | dn | lf | rt) & (~m)
        if border.any():
            depth = float(img[border].min()) - val
            is_min = img[border].min() > val + 1e-9   # every neighbour strictly higher
        else:
            depth = np.inf                             # no surroundings (e.g. const image)
            is_min = True
        if is_min and depth >= min_depth:
            pts.append((float(yy[m].mean()), float(xx[m].mean())))
    return _points_dict(img.shape, pts)


# --------------------------------------------------------------------------- #
# Module-level op functions (so tests can call them directly).                #
# --------------------------------------------------------------------------- #
def sp_local_max_sub_pix(v, a, b):
    return _extrema(v, a, True)


def sp_local_min_sub_pix(v, a, b):
    return _extrema(v, a, False)


def sp_saddle_points_sub_pix(v, a, b):
    return _saddles(v, a)


def sp_critical_points_sub_pix(v, a, b):
    return _critical(v, a)


def sp_plateaus(v, a, b):
    return _plateaus(v, a, b)


def sp_lowlands_center(v, a, b):
    return _lowlands_center(v, a, b)


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Return the sub-pixel critical-point ops (image -> contour point sets)."""
    def _safe(fn):
        def w(v, a, b):
            try:
                out = fn(v, a, b)
            except Exception:
                out = None
            if isinstance(out, dict) and "cs" in out and "shape" in out:
                return out
            # Fail-soft: an empty point set with a best-effort shape.
            try:
                x = _as_image(v)
                shp = x.shape if x is not None else (1, 1)
            except Exception:
                shp = (1, 1)
            return {"shape": (int(shp[0]), int(shp[1])), "cs": []}
        return w

    return [
        # halcon "" — local_max_sub_pix is already covered by a core op; genuine
        # alternate impl, not new coverage (no double-claim).
        Op("sp_local_max_sub_pix", "subpix", "", IMAGE, CONTOUR, _safe(sp_local_max_sub_pix)),
        Op("sp_local_min_sub_pix", "subpix", "local_min_sub_pix", IMAGE, CONTOUR, _safe(sp_local_min_sub_pix)),
        Op("sp_saddle_points_sub_pix", "subpix", "saddle_points_sub_pix", IMAGE, CONTOUR, _safe(sp_saddle_points_sub_pix)),
        Op("sp_critical_points_sub_pix", "subpix", "critical_points_sub_pix", IMAGE, CONTOUR, _safe(sp_critical_points_sub_pix)),
        Op("sp_plateaus", "subpix", "plateaus", IMAGE, CONTOUR, _safe(sp_plateaus)),
        Op("sp_lowlands_center", "subpix", "lowlands_center", IMAGE, CONTOUR, _safe(sp_lowlands_center)),
    ]
