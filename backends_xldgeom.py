"""XLD contour geometry tier — point-set / polyline operators (registry shape).

Adds a batch of genuine HALCON *XLD* geometry operators that consume the typed
``contour`` sort and produce either a scalar ``feature`` (moments, area,
eccentricity, orientation, axis ratio, bbox ratio, regression residual) or a
transformed ``contour`` (length clipping, Douglas-Peucker polygon simplification,
central-window cropping).

Contour data model (as threaded by the registry)::

    {"shape": (H, W), "cs": [ Nx2 float64 arrays of (row, col) points, ... ]}

Every operator is a real numerical algorithm — the covariance / moment
computations follow the standard 2-D central-moment definitions, the polygon
area is the shoelace formula, the polyline simplification is genuine
Ramer-Douglas-Peucker recursion. `build()` returns the Op list; each op is a
module-level function so its semantics can be exercised directly by tests.

Honesty note: three ops (xg_clip_contours = length-band filter, xg_crop_contours
= central-window point crop, xg_regress_contours = TLS perpendicular-residual RMS)
are genuine algorithms but do NOT reproduce the real HALCON `clip_contours_xld` /
`crop_contours_xld` / `regress_contours_xld` semantics (rectangle-clip / region-crop
/ regression-polyline), so they carry NO `halcon` name — they add op capability, not
a coverage claim (feedback_no_false_reporting). The other seven (`gen_polygons_xld`,
`moments_points_xld`, `area_center_points_xld`, `eccentricity_points_xld`,
`orientation_points_xld`, `elliptic_axis_points_xld`, `height_width_ratio_xld`) are
faithful genuine analogs and keep their names. (`moments_points_xld` /
`area_center_points_xld` reduce their multi-value HALCON output to the single scalar
the feature sort allows — the same convention as the existing `moments_xld` /
`area_center_xld` core ops.)

    py -3.11 backends_xldgeom.py    # self-report: ops + functional gate

stdlib + numpy only. Deterministic. Fail-soft on empty/degenerate contours.
"""
from __future__ import annotations

import math

import numpy as np

CATEGORY = "xldgeom"


# --------------------------------------------------------------------------- #
# contour-dict access helpers (fail-soft: never raise on odd input)
# --------------------------------------------------------------------------- #
def _cs(v):
    """Return the list of valid Nx2 float64 point arrays in a contour dict."""
    if not isinstance(v, dict):
        return []
    raw = v.get("cs") or []
    out = []
    for c in raw:
        try:
            arr = np.asarray(c, np.float64)
        except (ValueError, TypeError):
            continue  # non-numeric element -> skip (fail-soft contract)
        if arr.ndim == 2 and arr.shape[0] > 0 and arr.shape[1] == 2 and np.all(np.isfinite(arr)):
            out.append(arr)
    return out


def _shape(v):
    """Return (H, W) from a contour dict, or (0, 0) if absent/malformed."""
    if isinstance(v, dict):
        s = v.get("shape")
        try:
            if s is not None and len(s) == 2:
                return int(s[0]), int(s[1])
        except (TypeError, ValueError):
            pass
    return 0, 0


def _allpts(cs):
    """Concatenate every contour's points into one (N, 2) array (or empty)."""
    if not cs:
        return np.zeros((0, 2), np.float64)
    return np.concatenate(cs, axis=0)


def _pca(pts):
    """Population covariance eigen-decomposition of an (N,2) (row,col) point set.

    Returns (w, V) with ``w`` ascending eigenvalues (w[0] <= w[1]) and ``V`` the
    matching eigenvector columns in (row, col) space, or ``None`` if < 2 points.
    """
    if len(pts) < 2:
        return None
    c = pts - pts.mean(axis=0)
    cov = (c.T @ c) / len(pts)
    w, vecs = np.linalg.eigh(cov)  # ascending eigenvalues
    return w, vecs


def _plen(c):
    """Open-polyline length of an (N,2) point array."""
    if len(c) < 2:
        return 0.0
    d = np.diff(c, axis=0)
    return float(np.sum(np.hypot(d[:, 0], d[:, 1])))


def _fin(x, default=0.0):
    """Coerce to a finite np.float64 scalar."""
    xf = float(x)
    return np.float64(xf if math.isfinite(xf) else default)


# --------------------------------------------------------------------------- #
# contour -> feature
# --------------------------------------------------------------------------- #
def xg_moments(v, a, b):
    """Normalized 2nd central moment of the point set: mu20 + mu02.

    Each ``mu`` is the per-point mean of the squared centred coordinate
    (HALCON's moments_points_xld normalizes central moments by point count).
    The trace mu20+mu02 is a single rotation-invariant scalar.
    """
    pts = _allpts(_cs(v))
    if len(pts) < 1:
        return np.float64(0.0)
    c = pts - pts.mean(axis=0)
    mu = np.mean(c ** 2, axis=0)  # [mu02 (rows), mu20 (cols)]
    return _fin(mu[0] + mu[1])


def xg_area_center(v, a, b):
    """Polygon area of the contour(s) via the shoelace formula (summed abs)."""
    total = 0.0
    for c in _cs(v):
        if len(c) >= 3:
            y = c[:, 0]
            x = c[:, 1]
            total += 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)))
    return _fin(total)


def xg_eccentricity(v, a, b):
    """Eccentricity sqrt(1 - lambda_min/lambda_max) from the point covariance."""
    r = _pca(_allpts(_cs(v)))
    if r is None:
        return np.float64(0.0)
    w, _ = r
    lo, hi = float(w[0]), float(w[1])
    if hi <= 1e-12:
        return np.float64(0.0)
    e = math.sqrt(max(0.0, 1.0 - lo / hi))
    return _fin(min(1.0, e))


def xg_orientation(v, a, b):
    """Principal-axis orientation in degrees, folded to [0,180) and /180 scaled.

    Angle is measured from the +x (column) axis; multiply the result by 180 to
    recover degrees. Line orientation is defined mod 180, so a line at theta and
    theta+180 map to the same value.
    """
    r = _pca(_allpts(_cs(v)))
    if r is None:
        return np.float64(0.0)
    _, vecs = r
    vy, vx = float(vecs[0, 1]), float(vecs[1, 1])  # major-axis eigenvector (row,col)
    ang = math.degrees(math.atan2(vy, vx)) % 180.0
    return _fin(ang / 180.0)


def xg_elliptic_axis(v, a, b):
    """Major/minor axis ratio sqrt(lambda_max/lambda_min) of the point set."""
    r = _pca(_allpts(_cs(v)))
    if r is None:
        return np.float64(1.0)
    w, _ = r
    lo, hi = float(w[0]), float(w[1])
    if lo <= 1e-12:
        return np.float64(1e6 if hi > 1e-12 else 1.0)
    return _fin(min(1e6, math.sqrt(hi / lo)), default=1.0)


def xg_height_width_ratio(v, a, b):
    """Axis-aligned bounding-box height/width ratio of the point set."""
    pts = _allpts(_cs(v))
    if len(pts) < 1:
        return np.float64(0.0)
    h = float(np.ptp(pts[:, 0]))
    w = float(np.ptp(pts[:, 1]))
    if w < 1e-12:
        return np.float64(1e6 if h > 1e-12 else 0.0)
    return _fin(min(1e6, h / w))


def xg_regress_contours(v, a, b):
    """Total-least-squares line residual RMS = sqrt(minor covariance eigenvalue).

    The perpendicular (orthogonal-regression) residual variance of a point set
    equals its smallest covariance eigenvalue; its square root is the RMS
    perpendicular distance to the best-fit line.
    """
    r = _pca(_allpts(_cs(v)))
    if r is None:
        return np.float64(0.0)
    w, _ = r
    return _fin(math.sqrt(max(0.0, float(w[0]))))


# --------------------------------------------------------------------------- #
# contour -> contour
# --------------------------------------------------------------------------- #
def xg_clip_contours(v, a, b):
    """Drop contours whose polyline length is below a * max-length (a in [0,1])."""
    cs = _cs(v)
    shape = _shape(v)
    if not cs:
        return {"shape": shape, "cs": []}
    lens = [_plen(c) for c in cs]
    lmax = max(lens)
    if lmax <= 1e-12:
        return {"shape": shape, "cs": [c.copy() for c in cs]}
    lo = float(np.clip(a, 0.0, 1.0)) * lmax
    out = [c.copy() for c, length in zip(cs, lens) if length >= lo]
    return {"shape": shape, "cs": out}


def _max_perp(pts, i, j):
    """Farthest interior point index and its perpendicular distance to seg i-j."""
    if j <= i + 1:
        return -1.0, i
    p = pts[i]
    seg = pts[j] - p
    seg_len = math.hypot(seg[0], seg[1])
    w = pts[i + 1:j] - p
    if seg_len < 1e-12:
        d = np.hypot(w[:, 0], w[:, 1])
    else:
        d = np.abs(seg[0] * w[:, 1] - seg[1] * w[:, 0]) / seg_len
    k = int(np.argmax(d))
    return float(d[k]), i + 1 + k


def _dp(pts, eps):
    """Ramer-Douglas-Peucker simplification of an (N,2) polyline."""
    n = len(pts)
    if n < 3:
        return pts.copy()
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        d, idx = _max_perp(pts, i, j)
        if d > eps:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    return pts[keep].copy()


def xg_gen_polygons(v, a, b):
    """Douglas-Peucker polyline simplification; eps = a * contour bbox diagonal."""
    cs = _cs(v)
    shape = _shape(v)
    out = []
    for c in cs:
        if len(c) < 3:
            out.append(c.copy())
            continue
        diag = math.hypot(float(np.ptp(c[:, 0])), float(np.ptp(c[:, 1])))
        eps = float(np.clip(a, 0.0, 1.0)) * diag
        out.append(_dp(c, eps))
    return {"shape": shape, "cs": out}


def xg_crop_contours(v, a, b):
    """Keep only contour points inside the central a-fraction window of the shape."""
    cs = _cs(v)
    H, W = _shape(v)
    if H <= 0 or W <= 0:
        pts = _allpts(cs)
        if len(pts) == 0:
            return {"shape": (H, W), "cs": []}
        H = int(math.ceil(float(pts[:, 0].max()))) + 1
        W = int(math.ceil(float(pts[:, 1].max()))) + 1
    half = float(np.clip(a, 0.0, 1.0)) / 2.0
    r_lo, r_hi = (0.5 - half) * H, (0.5 + half) * H
    c_lo, c_hi = (0.5 - half) * W, (0.5 + half) * W
    out = []
    for c in cs:
        m = (c[:, 0] >= r_lo) & (c[:, 0] <= r_hi) & (c[:, 1] >= c_lo) & (c[:, 1] <= c_hi)
        if m.any():
            out.append(c[m].copy())
    return {"shape": (H, W), "cs": out}


# --------------------------------------------------------------------------- #
# registry wiring
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Return the XLD contour-geometry Op list (all in_sort=CONTOUR)."""
    defs = [
        ("xg_moments", "moments_points_xld", CONTOUR, FEATURE, xg_moments),
        ("xg_area_center", "area_center_points_xld", CONTOUR, FEATURE, xg_area_center),
        ("xg_eccentricity", "eccentricity_points_xld", CONTOUR, FEATURE, xg_eccentricity),
        ("xg_orientation", "orientation_points_xld", CONTOUR, FEATURE, xg_orientation),
        ("xg_elliptic_axis", "elliptic_axis_points_xld", CONTOUR, FEATURE, xg_elliptic_axis),
        ("xg_height_width_ratio", "height_width_ratio_xld", CONTOUR, FEATURE, xg_height_width_ratio),
        # These three reuse XLD-family NAMES but implement different semantics than
        # the real HALCON operators (length-band filter / central-window crop /
        # TLS residual RMS vs HALCON's rectangle-clip / region-crop /
        # regression-polyline). They are genuine ops but must NOT claim those
        # HALCON names as coverage (feedback_no_false_reporting) — halcon left "".
        ("xg_regress_contours", "", CONTOUR, FEATURE, xg_regress_contours),
        ("xg_clip_contours", "", CONTOUR, CONTOUR, xg_clip_contours),
        ("xg_gen_polygons", "gen_polygons_xld", CONTOUR, CONTOUR, xg_gen_polygons),
        ("xg_crop_contours", "", CONTOUR, CONTOUR, xg_crop_contours),
    ]
    return [Op(name, CATEGORY, halcon, isort, osort, fn) for (name, halcon, isort, osort, fn) in defs]


if __name__ == "__main__":
    class _Op:
        def __init__(self, *a):
            self.name, self.category, self.halcon = a[0], a[1], a[2]
            self.in_sort, self.out_sort, self.fn = a[3], a[4], a[5]

    ops = build(_Op, "image", "region", "feature", "contour", lambda x: x, lambda v: v > 0.5)
    print(f"xldgeom tier: {len(ops)} ops")
    for op in ops:
        print(f"  {op.name:<24} -> {op.out_sort:<7}  ({op.halcon})")
