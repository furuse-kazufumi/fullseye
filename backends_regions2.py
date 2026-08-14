"""Binary-region geometry operators (registry tier, prefix ``r2_``).

Genuine computational-geometry / connected-component operators over binary region
masks, each implementing the algorithm named by a real, previously-uncovered HALCON
operator.  Every op is a module-level ``fn(v, a, b)`` so tests call it directly; the
tier is assembled by :func:`build`, which the caller wires into the op registry.

Region contract: input/return is a 2-D float64 mask (0/1) in [0,1]; feature ops
return a finite scalar float.  All fns are exception-safe (fail-soft on empty / const
/ tiny / malformed input — never raise) and deterministic (any rng is seeded).

Genuine algorithms
------------------
* ``inner_circle``        - largest inscribed circle via the Euclidean distance
                            transform (center = arg-max distance-to-background,
                            radius = that distance), rasterised as a disk mask.
* ``inner_rectangle1``    - largest axis-aligned all-foreground rectangle via the
                            maximal-rectangle-in-a-binary-matrix stack algorithm.
* ``smallest_rectangle1`` - axis-aligned bounding box of the region.
* ``smallest_circle``     - minimum enclosing circle (Welzl on the convex hull).
* ``smallest_rectangle2`` - minimum-area oriented bounding rectangle (rotating
                            calipers over the convex hull).
* ``sort_region``         - keep the k-th largest connected component (k from ``a``).
* ``union1``              - union of all connected components into one mask.
* ``partition_rectangle`` - split the region bbox into a grid; keep overlapping cells.
* ``runlength_features``  - mean horizontal run length (region -> feature).
* ``split_skeleton_lines``- thin to a skeleton, then break it at junction pixels.

``contlength`` (boundary length) is intentionally NOT implemented here: it is already
covered elsewhere in the registry (``backends_auto``).  See :data:`SKIPPED`.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

try:  # skimage is used only to thin regions for split_skeleton_lines; degrade gracefully
    from skimage.morphology import skeletonize as _sk_skeletonize
except ImportError:  # pragma: no cover - environment without skimage
    _sk_skeletonize = None

# HALCON operators deliberately skipped in this tier (with the honest reason).
SKIPPED = {
    "contlength": "boundary length already covered in backends_auto (region_feat perimeter)",
}


# --------------------------------------------------------------------------- #
# small shared helpers
# --------------------------------------------------------------------------- #
def _as_mask(v) -> np.ndarray:
    """Coerce any region-ish input to a 2-D boolean foreground mask (fail-soft)."""
    a = np.asarray(v, dtype=np.float64)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    elif a.ndim > 2:
        a = a.reshape(a.shape[0], -1)
    return np.isfinite(a) & (a > 0.5)


def _clip01(a: np.ndarray) -> np.ndarray:
    return np.clip(np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)


def _knob(x: float) -> float:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not np.isfinite(x):
        return 0.5
    return min(1.0, max(0.0, x))


def _disk(shape, cy: float, cx: float, r: float) -> np.ndarray:
    h, w = shape
    yy, xx = np.ogrid[:h, :w]
    r = max(0.0, float(r))
    return ((yy - cy) ** 2 + (xx - cx) ** 2) <= (r * r)


def _convex_hull_xy(pts_xy: np.ndarray) -> np.ndarray:
    """Andrew's monotone chain. ``pts_xy`` = Nx2 (x, y); returns CCW hull vertices."""
    pts = np.unique(pts_xy.astype(np.float64), axis=0)
    if len(pts) <= 2:
        return pts
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in pts[::-1]:
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = np.array(lower[:-1] + upper[:-1], dtype=np.float64)
    return hull if len(hull) >= 1 else pts


# --- minimum enclosing circle (Welzl) --------------------------------------- #
def _circle_2(p, q):
    cx, cy = (p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0
    r = 0.5 * float(np.hypot(p[0] - q[0], p[1] - q[1]))
    return (cx, cy, r)


def _circle_3(p, q, s):
    ax, ay = p
    bx, by = q
    cx_, cy_ = s
    d = 2.0 * (ax * (by - cy_) + bx * (cy_ - ay) + cx_ * (ay - by))
    if abs(d) < 1e-12:  # collinear -> degenerate; caller falls back
        return None
    ux = ((ax * ax + ay * ay) * (by - cy_) + (bx * bx + by * by) * (cy_ - ay)
          + (cx_ * cx_ + cy_ * cy_) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx_ - bx) + (bx * bx + by * by) * (ax - cx_)
          + (cx_ * cx_ + cy_ * cy_) * (bx - ax)) / d
    r = float(np.hypot(ux - ax, uy - ay))
    return (ux, uy, r)


def _in_circle(c, p, eps=1e-7):
    return np.hypot(p[0] - c[0], p[1] - c[1]) <= c[2] + eps


def _trivial(pts):
    if not pts:
        return (0.0, 0.0, 0.0)
    if len(pts) == 1:
        return (pts[0][0], pts[0][1], 0.0)
    if len(pts) == 2:
        return _circle_2(pts[0], pts[1])
    c = _circle_3(pts[0], pts[1], pts[2])
    if c is not None:
        return c
    # collinear triple: enclosing circle = diameter of the farthest pair
    best = _circle_2(pts[0], pts[1])
    for i in range(3):
        for j in range(i + 1, 3):
            cc = _circle_2(pts[i], pts[j])
            if cc[2] > best[2]:
                best = cc
    return best


def _welzl(P, R):
    if not P or len(R) == 3:
        return _trivial(R)
    p = P[-1]
    d = _welzl(P[:-1], R)
    if _in_circle(d, p):
        return d
    return _welzl(P[:-1], R + [p])


def _min_enclosing_circle(points_yx: np.ndarray):
    """Minimum enclosing circle of (row, col) points. Returns (cy, cx, r)."""
    pts = np.asarray(points_yx, dtype=np.float64)
    if len(pts) == 0:
        return (0.0, 0.0, 0.0)
    xy = np.column_stack([pts[:, 1], pts[:, 0]])          # (x, y)
    hull = _convex_hull_xy(xy)
    if len(hull) == 1:
        return (float(hull[0][1]), float(hull[0][0]), 0.0)
    P = [tuple(p) for p in hull]
    rng = np.random.default_rng(0)
    rng.shuffle(P)                                        # deterministic shuffle
    cx, cy, r = _welzl(P, [])
    return (float(cy), float(cx), float(r))               # back to (row, col, r)


# --- minimum-area oriented rectangle (rotating calipers) -------------------- #
def _min_area_rect(points_yx: np.ndarray):
    """Min-area oriented bbox of (row,col) points.

    Returns (cy, cx, long_len, short_len, angle) where ``angle`` (radians) is the
    orientation of the LONG side in image (x=col, y=row) coordinates.
    """
    pts = np.asarray(points_yx, dtype=np.float64)
    if len(pts) == 0:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    xy = np.column_stack([pts[:, 1], pts[:, 0]])          # (x, y)
    hull = _convex_hull_xy(xy)
    if len(hull) <= 1:
        return (float(pts[0, 0]), float(pts[0, 1]), 0.0, 0.0, 0.0)
    if len(hull) == 2:
        d = hull[1] - hull[0]
        c = hull.mean(0)
        return (float(c[1]), float(c[0]), float(np.hypot(*d)), 0.0,
                float(np.arctan2(d[1], d[0])))

    best = None
    n = len(hull)
    for i in range(n):
        edge = hull[(i + 1) % n] - hull[i]
        L = float(np.hypot(edge[0], edge[1]))
        if L < 1e-12:
            continue
        ux, uy = edge[0] / L, edge[1] / L                 # edge dir
        vx, vy = -uy, ux                                  # perpendicular
        pu = hull[:, 0] * ux + hull[:, 1] * uy
        pv = hull[:, 0] * vx + hull[:, 1] * vy
        umin, umax = pu.min(), pu.max()
        vmin, vmax = pv.min(), pv.max()
        area = (umax - umin) * (vmax - vmin)
        if best is None or area < best[0]:
            cu, cv = (umin + umax) / 2.0, (vmin + vmax) / 2.0
            cx = cu * ux + cv * vx
            cy = cu * uy + cv * vy
            best = (area, cx, cy, umax - umin, vmax - vmin,
                    float(np.arctan2(uy, ux)))
    if best is None:                                      # fully degenerate
        c = hull.mean(0)
        return (float(c[1]), float(c[0]), 0.0, 0.0, 0.0)
    _, cx, cy, ext_u, ext_v, ang_u = best
    if ext_u >= ext_v:
        long_len, short_len, angle = ext_u, ext_v, ang_u
    else:
        long_len, short_len, angle = ext_v, ext_u, ang_u + np.pi / 2.0
    return (float(cy), float(cx), float(long_len), float(short_len), float(angle))


def _oriented_rect_mask(shape, cy, cx, long_len, short_len, angle):
    h, w = shape
    yy, xx = np.ogrid[:h, :w]
    ux, uy = np.cos(angle), np.sin(angle)                 # long axis (x, y)
    dx = xx - cx
    dy = yy - cy
    pu = dx * ux + dy * uy
    pv = -dx * uy + dy * ux
    hu = long_len / 2.0 + 0.5
    hv = short_len / 2.0 + 0.5
    return (np.abs(pu) <= hu) & (np.abs(pv) <= hv)


def _max_all_ones_rect(m: np.ndarray):
    """Largest axis-aligned all-True rectangle. Returns (top, left, bottom, right)."""
    h, w = m.shape
    if not m.any():
        return None
    height = np.zeros(w, dtype=np.int64)
    best = None                                           # (area, top, left, bottom, right)
    for r in range(h):
        height = np.where(m[r], height + 1, 0)
        stack = []                                        # (start_col, bar_height)
        for i in range(w + 1):
            cur = int(height[i]) if i < w else 0
            start = i
            while stack and stack[-1][1] > cur:
                idx, hgt = stack.pop()
                area = hgt * (i - idx)
                if hgt > 0 and (best is None or area > best[0]):
                    best = (area, r - hgt + 1, idx, r, i - 1)
                start = idx
            stack.append((start, cur))
    if best is None:
        return None
    return (best[1], best[2], best[3], best[4])


# --------------------------------------------------------------------------- #
# operators
# --------------------------------------------------------------------------- #
def r2_inner_circle(v, a, b):
    """Largest inscribed circle drawn as a mask (a scales drawn radius; a=0.5=exact)."""
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    if not m.any():
        return out
    dt = ndimage.distance_transform_edt(m)
    cy, cx = np.unravel_index(int(np.argmax(dt)), dt.shape)
    r0 = float(dt[cy, cx])                                # genuine inradius
    r = r0 * (0.6 + 0.8 * _knob(a))                       # a in [0,1] -> [0.6,1.4]*inradius
    out[_disk(m.shape, cy, cx, r)] = 1.0
    return _clip01(out)


def r2_inner_rectangle1(v, a, b):
    """Largest axis-aligned inscribed rectangle (a shrinks the drawn rect; a=0=exact)."""
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    rect = _max_all_ones_rect(m)
    if rect is None:
        return out
    top, left, bottom, right = rect
    hh = bottom - top + 1
    ww = right - left + 1
    f = 0.3 * _knob(a)                                    # inward shrink fraction per side
    dt = int(round(hh * f / 2.0))
    dl = int(round(ww * f / 2.0))
    t2, b2 = top + dt, bottom - dt
    l2, r2 = left + dl, right - dl
    if b2 < t2:
        t2 = b2 = (top + bottom) // 2
    if r2 < l2:
        l2 = r2 = (left + right) // 2
    out[t2:b2 + 1, l2:r2 + 1] = 1.0
    return _clip01(out)


def r2_smallest_rectangle1(v, a, b):
    """Axis-aligned bounding box (smallest_rectangle1)."""
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    ys, xs = np.where(m)
    if ys.size == 0:
        return out
    out[ys.min():ys.max() + 1, xs.min():xs.max() + 1] = 1.0
    return _clip01(out)


def r2_smallest_circle(v, a, b):
    """Minimum enclosing circle as a mask (Welzl); a inflates radius (>=0)."""
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    ys, xs = np.where(m)
    if ys.size == 0:
        return out
    cy, cx, r = _min_enclosing_circle(np.column_stack([ys, xs]))
    r_draw = (r + 0.75) * (1.0 + 0.4 * _knob(a))          # >= r so all pixels enclosed
    out[_disk(m.shape, cy, cx, r_draw)] = 1.0
    return _clip01(out)


def r2_smallest_rectangle2(v, a, b):
    """Minimum-area ORIENTED bounding rectangle as a mask (rotating calipers)."""
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    ys, xs = np.where(m)
    if ys.size == 0:
        return out
    cy, cx, ll, ss, ang = _min_area_rect(np.column_stack([ys, xs]))
    ll = ll * (1.0 + 0.3 * _knob(a))                      # a mildly inflates the long side
    out[_oriented_rect_mask(m.shape, cy, cx, ll, ss, ang)] = 1.0
    return _clip01(out)


def r2_sort_region(v, a, b):
    """Keep the k-th largest connected component; k = round(a*(n-1))."""
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    lab, n = ndimage.label(m)
    if n == 0:
        return out
    sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
    order = np.argsort(sizes)[::-1]                       # descending by area
    k = int(round(_knob(a) * (n - 1)))
    k = min(n - 1, max(0, k))
    out[lab == (int(order[k]) + 1)] = 1.0
    return _clip01(out)


def r2_union1(v, a, b):
    """Union of all connected components into a single mask (OR of labels)."""
    m = _as_mask(v)
    lab, _ = ndimage.label(m)
    return _clip01((lab > 0).astype(np.float64))


def r2_partition_rectangle(v, a, b):
    """Split the region bbox into an NxN grid; keep cells overlapping the region."""
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    ys, xs = np.where(m)
    if ys.size == 0:
        return out
    top, bottom = int(ys.min()), int(ys.max())
    left, right = int(xs.min()), int(xs.max())
    ncell = 2 + int(_knob(a) * 4)                          # a in [0,1] -> 2..6 divisions
    rb = np.linspace(top, bottom + 1, ncell + 1).astype(int)
    cb = np.linspace(left, right + 1, ncell + 1).astype(int)
    for i in range(ncell):
        for j in range(ncell):
            r0, r1 = rb[i], rb[i + 1]
            c0, c1 = cb[j], cb[j + 1]
            if r1 <= r0 or c1 <= c0:
                continue
            if m[r0:r1, c0:c1].any():
                out[r0:r1, c0:c1] = 1.0
    return _clip01(out)


def r2_runlength_features(v, a, b):
    """Region -> feature: mean length of horizontal foreground runs."""
    m = _as_mask(v)
    if not m.any():
        return np.float64(0.0)
    lengths = []
    for row in m:
        if not row.any():
            continue
        # run boundaries via diff on a zero-padded row
        padded = np.concatenate(([0], row.view(np.int8), [0]))
        d = np.diff(padded)
        starts = np.where(d == 1)[0]
        ends = np.where(d == -1)[0]
        lengths.extend((ends - starts).tolist())
    if not lengths:
        return np.float64(0.0)
    return np.float64(float(np.mean(lengths)))


def r2_split_skeleton_lines(v, a, b):
    """Thin the region to a skeleton, then break it at junctions (>=3 neighbours).

    ``a`` drops resulting segments shorter than ``a*8`` pixels (a=0 keeps all).
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    if not m.any():
        return out
    skel = _sk_skeletonize(m) if _sk_skeletonize is not None else m
    skel = np.asarray(skel, dtype=bool)
    if not skel.any():
        return out
    # 8-neighbour foreground count (exclude self)
    kernel = np.ones((3, 3), dtype=np.int64)
    neigh = ndimage.convolve(skel.astype(np.int64), kernel, mode="constant") - skel
    junction = skel & (neigh >= 3)
    segments = skel & ~junction
    min_len = int(_knob(a) * 8)
    if min_len > 0:
        lab, n = ndimage.label(segments)                  # 4-connectivity
        if n > 0:
            sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
            keep = np.zeros_like(segments)
            for i, s in enumerate(sizes, 1):
                if s >= min_len:
                    keep |= (lab == i)
            segments = keep
    out[segments] = 1.0
    return _clip01(out)


# --------------------------------------------------------------------------- #
# registry assembly
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Return the r2_ binary-region operator tier."""
    cat = "region"
    defs = [
        ("r2_inner_circle", "inner_circle", REGION, REGION, r2_inner_circle),
        ("r2_inner_rectangle1", "inner_rectangle1", REGION, REGION, r2_inner_rectangle1),
        # halcon "" — smallest_rectangle1 is already covered by a core op; this is a
        # genuine alternate impl, not new coverage (no double-claim).
        ("r2_smallest_rectangle1", "", REGION, REGION, r2_smallest_rectangle1),
        ("r2_smallest_circle", "smallest_circle", REGION, REGION, r2_smallest_circle),
        ("r2_smallest_rectangle2", "smallest_rectangle2", REGION, REGION, r2_smallest_rectangle2),
        ("r2_sort_region", "sort_region", REGION, REGION, r2_sort_region),
        ("r2_union1", "union1", REGION, REGION, r2_union1),
        ("r2_partition_rectangle", "partition_rectangle", REGION, REGION, r2_partition_rectangle),
        ("r2_runlength_features", "runlength_features", REGION, FEATURE, r2_runlength_features),
        ("r2_split_skeleton_lines", "split_skeleton_lines", REGION, REGION, r2_split_skeleton_lines),
    ]
    return [Op(name, cat, halcon, isort, osort, fn)
            for (name, halcon, isort, osort, fn) in defs]
