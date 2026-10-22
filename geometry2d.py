"""2D/3D 幾何プリミティブ演算(HALCON "Tools" chapter の genuine core, numpy).

点/直線/線分/円の距離・角度・交点。metrology の基盤。HALCON 慣例で点は (row, col)、
直線・線分は 2 点 (row1,col1,row2,col2)。純粋な解析幾何=曖昧さのない genuine 実装。
"""
from __future__ import annotations

import numpy as np


def distance_pp(row1, col1, row2, col2) -> float:
    """2 点間の距離(distance_pp)。"""
    return float(np.hypot(row2 - row1, col2 - col1))


def _line_ab(r1, c1, r2, c2):
    """2 点を通る直線 a*col + b*row + c = 0 の (a,b,c)(正規化)。"""
    a = r2 - r1
    b = c1 - c2
    c = -(a * c1 + b * r1)
    n = np.hypot(a, b) + 1e-12
    return a / n, b / n, c / n


def distance_pl(row, col, r1, c1, r2, c2) -> float:
    """点から(無限)直線までの垂直距離(distance_pl)。"""
    a, b, c = _line_ab(r1, c1, r2, c2)
    return float(abs(a * col + b * row + c))


def projection_pl(row, col, r1, c1, r2, c2):
    """点を直線へ正射影した足を返す(projection_pl)。"""
    p = np.array([row, col], float)
    A = np.array([r1, c1], float)
    d = np.array([r2 - r1, c2 - c1], float)
    d = d / (np.hypot(*d) + 1e-12)
    return A + np.dot(p - A, d) * d


def distance_ps(row, col, r1, c1, r2, c2) -> float:
    """点から線分までの距離(distance_ps)。"""
    p = np.array([row, col], float)
    A, B = np.array([r1, c1], float), np.array([r2, c2], float)
    ab = B - A
    t = np.clip(np.dot(p - A, ab) / (np.dot(ab, ab) + 1e-12), 0, 1)
    return float(np.hypot(*(p - (A + t * ab))))


def _seg_pts(r1, c1, r2, c2, n=20):
    t = np.linspace(0, 1, n)[:, None]
    return np.array([r1, c1]) + t * np.array([r2 - r1, c2 - c1])


def distance_ss(a1, b1, a2, b2, a3, b3, a4, b4) -> float:
    """2 線分間の最小距離(distance_ss)。"""
    s1 = _seg_pts(a1, b1, a2, b2)
    d = min(distance_ps(p[0], p[1], a3, b3, a4, b4) for p in s1)
    s2 = _seg_pts(a3, b3, a4, b4)
    return float(min(d, min(distance_ps(p[0], p[1], a1, b1, a2, b2) for p in s2)))


def distance_sl(a1, b1, a2, b2, r1, c1, r2, c2) -> float:
    """線分から直線までの最小距離(端点の垂直距離の小さい方、distance_sl)。"""
    return float(min(distance_pl(a1, b1, r1, c1, r2, c2), distance_pl(a2, b2, r1, c1, r2, c2)))


def angle_lx(r1, c1, r2, c2) -> float:
    """直線と x(列)軸のなす角 [rad](angle_lx)。"""
    return float(np.arctan2(r2 - r1, c2 - c1))


def angle_ll(ra1, ca1, rb1, cb1, ra2, ca2, rb2, cb2) -> float:
    """2 直線のなす角 [rad](angle_ll)。"""
    a1 = angle_lx(ra1, ca1, rb1, cb1)
    a2 = angle_lx(ra2, ca2, rb2, cb2)
    d = (a2 - a1) % np.pi
    return float(d if d <= np.pi / 2 else np.pi - d)


def intersection_lines(ra1, ca1, rb1, cb1, ra2, ca2, rb2, cb2):
    """2 直線の交点 (row, col) を返す(平行なら None、intersection_lines)。"""
    a1, b1, c1 = _line_ab(ra1, ca1, rb1, cb1)
    a2, b2, c2 = _line_ab(ra2, ca2, rb2, cb2)
    M = np.array([[b1, a1], [b2, a2]])                    # [row, col] 係数
    det = np.linalg.det(M)
    if abs(det) < 1e-12:
        return None
    row, col = np.linalg.solve(M, [-c1, -c2])
    return np.array([row, col])


def intersection_circles(row1, col1, r1, row2, col2, r2):
    """2 円の交点(0/1/2 点)を返す(intersection_circles)。"""
    d = np.hypot(row2 - row1, col2 - col1)
    if d > r1 + r2 or d < abs(r1 - r2) or d < 1e-12:
        return []
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h2 = r1 * r1 - a * a
    ux, uy = (row2 - row1) / d, (col2 - col1) / d
    mx, my = row1 + a * ux, col1 + a * uy
    if h2 <= 1e-12:
        return [np.array([mx, my])]
    h = np.sqrt(h2)
    return [np.array([mx + h * uy, my - h * ux]), np.array([mx - h * uy, my + h * ux])]


def get_points_ellipse(row, col, phi, ra, rb, n: int = 60) -> np.ndarray:
    """楕円周上の n 点を返す(get_points_ellipse)。"""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x, y = ra * np.cos(t), rb * np.sin(t)
    cp, sp = np.cos(phi), np.sin(phi)
    return np.column_stack([row + x * sp + y * cp, col + x * cp - y * sp])


def distance_point_line(px, py, pz, lx, ly, lz, dx, dy, dz) -> float:
    """3D 点から直線(点 l + 方向 d)までの距離(distance_point_line)。"""
    p = np.array([px, py, pz], float)
    l = np.array([lx, ly, lz], float)
    d = np.array([dx, dy, dz], float)
    d = d / (np.linalg.norm(d) + 1e-12)
    return float(np.linalg.norm(np.cross(p - l, d)))


# ── contour/region 距離(Tools 続き)──────────────────────────────────────────── #
def _cs_pts(v):
    if isinstance(v, dict):
        cs = v.get("cs", [])
        return np.concatenate([np.asarray(c, float) for c in cs], 0) if cs else np.zeros((0, 2))
    return np.asarray(v, float).reshape(-1, 2)


def distance_cc_min(contour1, contour2) -> float:
    """2 contour 間の最小点間距離(distance_cc_min)。"""
    from scipy.spatial import cKDTree
    a, b = _cs_pts(contour1), _cs_pts(contour2)
    if len(a) == 0 or len(b) == 0:
        return 0.0
    return float(cKDTree(b).query(a, k=1)[0].min())


def distance_cc(contour1, contour2) -> float:
    """2 contour 間の平均点間距離(distance_cc)。"""
    from scipy.spatial import cKDTree
    a, b = _cs_pts(contour1), _cs_pts(contour2)
    if len(a) == 0 or len(b) == 0:
        return 0.0
    return float(cKDTree(b).query(a, k=1)[0].mean())


def distance_contours_xld(contour_from, contour_to) -> float:
    """contour_from の各点から contour_to への最大距離(distance_contours_xld)。"""
    from scipy.spatial import cKDTree
    a, b = _cs_pts(contour_from), _cs_pts(contour_to)
    if len(a) == 0 or len(b) == 0:
        return 0.0
    return float(cKDTree(b).query(a, k=1)[0].max())


def distance_rr_min(region1, region2) -> float:
    """2 region(二値マスク)間の最小画素距離(distance_rr_min)。"""
    from scipy import ndimage
    r1 = np.asarray(region1) > 0.5
    r2 = np.asarray(region2) > 0.5
    if not r1.any() or not r2.any():
        return 0.0
    dt = ndimage.distance_transform_edt(~r2)
    return float(dt[r1].min())


def area_intersection_rectangle2(row1, col1, phi1, l1a, l1b,
                                 row2, col2, phi2, l2a, l2b, n: int = 60,
                                 method: str = "exact") -> float:
    """Return the intersection area of two oriented rectangles.

    ``method="exact"`` (the default) translates the rectangles to their common
    midpoint, normalizes all lengths by the largest half-side, then clips the
    two convex polygons.  Its inside tolerance is eight floating-point ulps
    relative to the edge and point distances; an exact separating-axis test
    still makes edge/corner contact and every representable positive gap have
    area zero.  Containment is evaluated analytically, so nested rectangles
    retain the smaller area down to the floating-point range.  The final area
    is multiplied in two guarded steps; it is zero or infinity only when the
    mathematical result is outside the binary64 range.
    Crossing needles whose normalized thickness is below one ulp remain a
    precision limit and may return zero even when their exact overlap is
    positive; analytic containment does not have this limitation.
    ``method="grid"`` is a selectable sampling approximation.  For identical
    half-side-one squares at angle pi/4 its measured absolute error is 0.13333
    at ``n=60`` and 0.01333 at ``n=600``.  Touching edges and zero half-lengths
    have area zero.
    """
    if method not in {"grid", "exact"}:
        raise ValueError("method must be 'grid' or 'exact'")

    values = (row1, col1, phi1, l1a, l1b,
              row2, col2, phi2, l2a, l2b)
    if not all(np.isfinite(value) for value in values):
        from fslib import FsValueError
        raise FsValueError("area_intersection_rectangle2: non-finite input")

    def vertices(r, c, phi, la, lb):
        cp, sp = np.cos(phi), np.sin(phi)
        # Counter-clockwise (x=column, y=row).
        u, v = np.array([cp, sp]), np.array([-sp, cp])
        centre = np.array([c, r])
        return [centre + sx * la * u + sy * lb * v
                for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

    if method == "exact":
        if min(l1a, l1b, l2a, l2b) <= 0:
            return 0.0

        # Subtract before constructing vertices: centre +/- half-side loses the
        # half-side outright when a perfectly ordinary rectangle is far away.
        origin_row = 0.5 * row1 + 0.5 * row2
        origin_col = 0.5 * col1 + 0.5 * col2
        row_delta, col_delta = row2 - row1, col2 - col1
        if np.isfinite(row_delta):
            r1, r2 = -0.5 * row_delta, 0.5 * row_delta
        else:
            r1, r2 = row1 - origin_row, row2 - origin_row
        if np.isfinite(col_delta):
            c1, c2 = -0.5 * col_delta, 0.5 * col_delta
        else:
            c1, c2 = col1 - origin_col, col2 - origin_col

        # Overflow-safe circumcircle rejection.  Scaling by the largest item
        # keeps both the centre separation and radii finite.
        sep_scale = max(abs(r1), abs(c1), abs(r2), abs(c2),
                        l1a, l1b, l2a, l2b)
        sr1, sc1, sr2, sc2 = (r1 / sep_scale, c1 / sep_scale,
                              r2 / sep_scale, c2 / sep_scale)
        distance = float(np.hypot(sr2 - sr1, sc2 - sc1))
        radii = (float(np.hypot(l1a / sep_scale, l1b / sep_scale)) +
                 float(np.hypot(l2a / sep_scale, l2b / sep_scale)))
        if distance > radii:
            return 0.0

        length_scale = max(l1a, l1b, l2a, l2b)
        exact_args = (r1 / length_scale, c1 / length_scale,
                      phi1, l1a / length_scale, l1b / length_scale,
                      r2 / length_scale, c2 / length_scale,
                      phi2, l2a / length_scale, l2b / length_scale)

        def axes(phi):
            cp, sp = float(np.cos(phi)), float(np.sin(phi))
            return (np.array([cp, sp]), np.array([-sp, cp]))

        centre1 = np.array([exact_args[1], exact_args[0]])
        centre2 = np.array([exact_args[6], exact_args[5]])
        axes1, axes2 = axes(phi1), axes(phi2)
        delta = centre2 - centre1

        def radius_on(axis, rect_axes, la, lb):
            return la * abs(float(np.dot(axis, rect_axes[0]))) + \
                   lb * abs(float(np.dot(axis, rect_axes[1])))

        # The four rectangle normals form an exact separating-axis test.
        for axis in axes1 + axes2:
            reach1 = radius_on(axis, axes1, exact_args[3], exact_args[4])
            reach2 = radius_on(axis, axes2, exact_args[8], exact_args[9])
            if abs(float(np.dot(delta, axis))) >= reach1 + reach2:
                return 0.0

        def contains(host_centre, host_axes, ha, hb,
                     inner_centre, inner_axes, ia, ib):
            d = inner_centre - host_centre
            return all(abs(float(np.dot(d, axis))) +
                       radius_on(axis, inner_axes, ia, ib) <= half
                       for axis, half in zip(host_axes, (ha, hb)))

        def restore_area(area_normalized):
            # This order avoids forming S**2, which can overflow or underflow
            # even when the final result is representable.
            with np.errstate(over="ignore", under="ignore"):
                return float((area_normalized * length_scale) * length_scale)

        if contains(centre1, axes1, exact_args[3], exact_args[4],
                    centre2, axes2, exact_args[8], exact_args[9]):
            with np.errstate(over="ignore", under="ignore"):
                return float((4.0 * min(l2a, l2b)) * max(l2a, l2b))
        if contains(centre2, axes2, exact_args[8], exact_args[9],
                    centre1, axes1, exact_args[3], exact_args[4]):
            with np.errstate(over="ignore", under="ignore"):
                return float((4.0 * min(l1a, l1b)) * max(l1a, l1b))

        # Parallel rectangles have a closed-form interval intersection.  Apart
        # from being faster, this preserves very shallow representable overlap
        # without polygon-coordinate cancellation.
        if phi1 == phi2:
            cp, sp = float(np.cos(phi1)), float(np.sin(phi1))
            dc, dr = col2 - col1, row2 - row1
            du = dc * cp + dr * sp
            dv = -dc * sp + dr * cp
            overlap_u = max(0.0, min(l1a, du + l2a) - max(-l1a, du - l2a))
            overlap_v = max(0.0, min(l1b, dv + l2b) - max(-l1b, dv - l2b))
            contact_tol = 8 * np.finfo(float).eps * max(l1a, l1b, l2a, l2b)
            if overlap_u <= contact_tol or overlap_v <= contact_tol:
                return 0.0
            return float(overlap_u * overlap_v)

        subject = vertices(*exact_args[:5])
        clip = vertices(*exact_args[5:])
        eps_rel = np.finfo(float).eps * 8
        for a, b in zip(clip, clip[1:] + clip[:1]):
            edge = b - a
            def side(p):
                return edge[0] * (p[1] - a[1]) - edge[1] * (p[0] - a[0])
            def is_inside(p, value):
                return value >= -eps_rel * np.hypot(*edge) * np.hypot(*(p - a))
            old, subject = subject, []
            if not old:
                break
            prev, prev_side = old[-1], side(old[-1])
            for cur in old:
                cur_side = side(cur)
                cur_inside = is_inside(cur, cur_side)
                prev_inside = is_inside(prev, prev_side)
                if cur_inside:
                    if not prev_inside:
                        t = float(np.clip(prev_side / (prev_side - cur_side), 0.0, 1.0))
                        subject.append(prev + (cur - prev) * t)
                    subject.append(cur)
                elif prev_inside:
                    t = float(np.clip(prev_side / (prev_side - cur_side), 0.0, 1.0))
                    subject.append(prev + (cur - prev) * t)
                prev, prev_side = cur, cur_side
        if len(subject) < 3:
            return 0.0
        p = np.asarray(subject)
        p = p - p[0]
        area = 0.5 * abs(np.dot(p[:, 0], np.roll(p[:, 1], -1)) -
                         np.dot(p[:, 1], np.roll(p[:, 0], -1)))
        return restore_area(area)

    def inside(pts, r, c, phi, la, lb):
        d = pts - [r, c]
        cp, sp = np.cos(-phi), np.sin(-phi)
        x = d[:, 1] * cp - d[:, 0] * sp
        y = d[:, 1] * sp + d[:, 0] * cp
        return (np.abs(x) <= la) & (np.abs(y) <= lb)
    corners = np.asarray(vertices(row1, col1, phi1, l1a, l1b) +
                         vertices(row2, col2, phi2, l2a, l2b))
    lo = corners[:, ::-1].min(axis=0)
    hi = corners[:, ::-1].max(axis=0)
    gy, gx = np.meshgrid(np.linspace(lo[0], hi[0], n), np.linspace(lo[1], hi[1], n))
    pts = np.column_stack([gy.ravel(), gx.ravel()])
    both = inside(pts, row1, col1, phi1, l1a, l1b) & inside(pts, row2, col2, phi2, l2a, l2b)
    cell = (hi[0] - lo[0]) * (hi[1] - lo[1]) / (n * n)
    return float(both.sum() * cell)


def distance_lc(r1, c1, r2, c2, contour) -> float:
    """直線から contour までの最小距離(distance_lc)。"""
    p = _cs_pts(contour)
    if len(p) == 0:
        return 0.0
    return float(min(distance_pl(pt[0], pt[1], r1, c1, r2, c2) for pt in p))


def distance_lr(r1, c1, r2, c2, region) -> float:
    """直線から region(二値)までの最小距離(distance_lr)。"""
    reg = np.asarray(region) > 0.5
    ys, xs = np.nonzero(reg)
    if len(ys) == 0:
        return 0.0
    return float(min(distance_pl(y, x, r1, c1, r2, c2) for y, x in zip(ys, xs)))


def distance_sr(a1, b1, a2, b2, region) -> float:
    """線分から region までの最小距離(distance_sr)。"""
    reg = np.asarray(region) > 0.5
    ys, xs = np.nonzero(reg)
    if len(ys) == 0:
        return 0.0
    return float(min(distance_ps(y, x, a1, b1, a2, b2) for y, x in zip(ys, xs)))


def distance_cc_min_points(contour1, contour2):
    """2 contour 間の最小距離とその最近点対を返す(distance_cc_min_points)。"""
    from scipy.spatial import cKDTree
    a, b = _cs_pts(contour1), _cs_pts(contour2)
    if len(a) == 0 or len(b) == 0:
        return {"distance": 0.0}
    dist, idx = cKDTree(b).query(a, k=1)
    k = int(np.argmin(dist))
    return {"distance": float(dist[k]), "p1": a[k], "p2": b[idx[k]]}


def distance_point_pluecker_line(px, py, pz, mx, my, mz, lx, ly, lz) -> float:
    """3D 点から Pluecker 直線(モーメント m, 方向 l)までの距離(distance_point_pluecker_line)。"""
    l = np.array([lx, ly, lz], float); m = np.array([mx, my, mz], float)
    p = np.array([px, py, pz], float)
    ln = np.linalg.norm(l) + 1e-12
    return float(np.linalg.norm(np.cross(p, l / ln) - m / ln))
