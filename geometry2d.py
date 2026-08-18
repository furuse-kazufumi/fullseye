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
                                 row2, col2, phi2, l2a, l2b, n: int = 60) -> float:
    """2 つの有向矩形の交差面積(モンテカルロ近似、area_intersection_rectangle2)。"""
    def inside(pts, r, c, phi, la, lb):
        d = pts - [r, c]
        cp, sp = np.cos(-phi), np.sin(-phi)
        x = d[:, 1] * cp - d[:, 0] * sp
        y = d[:, 1] * sp + d[:, 0] * cp
        return (np.abs(x) <= la) & (np.abs(y) <= lb)
    lo = np.array([min(row1, row2) - max(l1a, l1b, l2a, l2b), min(col1, col2) - max(l1a, l1b, l2a, l2b)])
    hi = np.array([max(row1, row2) + max(l1a, l1b, l2a, l2b), max(col1, col2) + max(l1a, l1b, l2a, l2b)])
    gy, gx = np.meshgrid(np.linspace(lo[0], hi[0], n), np.linspace(lo[1], hi[1], n))
    pts = np.column_stack([gy.ravel(), gx.ravel()])
    both = inside(pts, row1, col1, phi1, l1a, l1b) & inside(pts, row2, col2, phi2, l2a, l2b)
    cell = (hi[0] - lo[0]) * (hi[1] - lo[1]) / (n * n)
    return float(both.sum() * cell)
