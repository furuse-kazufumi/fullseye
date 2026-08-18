"""幾何ツール: 交点・Plücker 直線・Hough・直線当てはめ(HALCON "Tools" chapter genuine, numpy).

点/線分/円/直線の解析幾何、Plücker 座標、方向つき Hough 変換。純粋な幾何式。
点/直線は (row, col) 座標。直線は (r0,c0,r1,c1) の 2 端点で表す。
"""
from __future__ import annotations

import numpy as np


def _p(x):
    return np.asarray(x, dtype=np.float64)


# ── 交点 ─────────────────────────────────────────────────────────────────────── #
def intersection_lines(l1, l2):
    """2 直線(各 2 点)の交点 (row, col) を返す(intersection_lines)。平行なら None。"""
    r1, c1, r2, c2 = l1; r3, c3, r4, c4 = l2
    d = (c1 - c2) * (r3 - r4) - (r1 - r2) * (c3 - c4)
    if abs(d) < 1e-12:
        return None
    a = c1 * r2 - r1 * c2; b = c3 * r4 - r3 * c4
    col = (a * (c3 - c4) - (c1 - c2) * b) / d
    row = (a * (r3 - r4) - (r1 - r2) * b) / d
    return np.array([row, col])


def intersection_line_circle(line, center, radius):
    """直線と円の交点を返す(0/1/2 点)(intersection_line_circle)。"""
    r1, c1, r2, c2 = line; cr, cc = center
    d = _p([r2 - r1, c2 - c1]); f = _p([r1 - cr, c1 - cc])
    a = d @ d; b = 2 * (f @ d); cq = f @ f - radius ** 2
    disc = b * b - 4 * a * cq
    if disc < 0:
        return []
    sq = np.sqrt(disc)
    ts = [(-b - sq) / (2 * a), (-b + sq) / (2 * a)]
    return [np.array([r1, c1]) + t * d for t in dict.fromkeys(ts)]


def intersection_segment_line(seg, line):
    """線分と直線の交点(線分内のみ)(intersection_segment_line)。"""
    pt = intersection_lines(seg, line)
    if pt is None:
        return None
    r1, c1, r2, c2 = seg
    t_num = (pt[0] - r1) * (r2 - r1) + (pt[1] - c1) * (c2 - c1)
    t_den = (r2 - r1) ** 2 + (c2 - c1) ** 2 + 1e-12
    t = t_num / t_den
    return pt if -1e-9 <= t <= 1 + 1e-9 else None


def intersection_segments(s1, s2):
    """2 線分の交点(両線分内のみ)(intersection_segments)。"""
    pt = intersection_segment_line(s1, s2)
    if pt is None:
        return None
    return pt if intersection_segment_line(s2, s1) is not None else None


def intersection_segment_circle(seg, center, radius):
    """線分と円の交点(線分内のみ)(intersection_segment_circle)。"""
    r1, c1, r2, c2 = seg
    out = []
    for pt in intersection_line_circle(seg, center, radius):
        t = ((pt[0] - r1) * (r2 - r1) + (pt[1] - c1) * (c2 - c1)) / \
            ((r2 - r1) ** 2 + (c2 - c1) ** 2 + 1e-12)
        if -1e-9 <= t <= 1 + 1e-9:
            out.append(pt)
    return out


# ── 直線特徴 ─────────────────────────────────────────────────────────────────── #
def line_orientation(r1, c1, r2, c2):
    """線分の向き(ラジアン、-pi/2..pi/2、line_orientation)。"""
    return float(np.arctan2(r2 - r1, c2 - c1))


def line_position(r1, c1, r2, c2):
    """線分の中点・長さ・向き(line_position)。"""
    return {"row": (r1 + r2) / 2, "column": (c1 + c2) / 2,
            "length": float(np.hypot(r2 - r1, c2 - c1)),
            "phi": line_orientation(r1, c1, r2, c2)}


# ── Plücker 直線座標 ─────────────────────────────────────────────────────────── #
def points_to_pluecker_line(p1, p2):
    """3D 2 点から直線の Plücker 座標 (方向 d, モーメント m) を返す(points_to_pluecker_line)。"""
    p1 = _p(p1).ravel(); p2 = _p(p2).ravel()
    d = p2 - p1
    m = np.cross(p1, p2)
    return {"direction": d, "moment": m}


def point_direction_to_pluecker_line(point, direction):
    """3D 点と方向から Plücker 座標を返す(point_direction_to_pluecker_line)。"""
    p = _p(point).ravel(); d = _p(direction).ravel()
    return {"direction": d, "moment": np.cross(p, d)}


def pluecker_line_to_point_direction(pluecker):
    """Plücker 座標から直線上の 1 点と方向を復元(pluecker_line_to_point_direction)。"""
    d = _p(pluecker["direction"]); m = _p(pluecker["moment"])
    point = np.cross(d, m) / (d @ d + 1e-12)
    return {"point": point, "direction": d}


def pluecker_line_to_points(pluecker, t0=0.0, t1=1.0):
    """Plücker 直線上の 2 点を返す(pluecker_line_to_points)。"""
    pd = pluecker_line_to_point_direction(pluecker)
    p, d = pd["point"], pd["direction"]
    return np.array([p + t0 * d, p + t1 * d])


def distance_point_pluecker_line(point, pluecker):
    """3D 点と Plücker 直線の距離(distance_point_pluecker_line)。"""
    pd = pluecker_line_to_point_direction(pluecker)
    p0, d = pd["point"], pd["direction"]
    v = _p(point).ravel() - p0
    return float(np.linalg.norm(np.cross(v, d)) / (np.linalg.norm(d) + 1e-12))


# ── 方向つき Hough 変換 ──────────────────────────────────────────────────────── #
def hough_line_trans_dir(edge_mask, dir_row, dir_col, n_angle=180, n_rho=None):
    """勾配方向を使う方向つき Hough 直線変換(hough_line_trans_dir)。
    edge_mask: bool 2D、dir_row/dir_col: 各エッジ点の勾配方向成分。"""
    m = np.asarray(edge_mask, bool)
    ys, xs = np.where(m)
    theta_g = np.arctan2(dir_row[m], dir_col[m])          # 勾配 = 法線方向
    H, W = m.shape
    rho_max = np.hypot(H, W)
    nr = int(n_rho) if n_rho else int(2 * rho_max)
    acc = np.zeros((nr, int(n_angle)))
    for y, x, tg in zip(ys, xs, theta_g):
        ang = tg % np.pi
        ai = int(ang / np.pi * n_angle) % n_angle
        rho = x * np.cos(ang) + y * np.sin(ang)
        ri = int((rho + rho_max) / (2 * rho_max) * (nr - 1))
        acc[ri, ai] += 1
    return acc


def hough_lines_dir(edge_mask, dir_row, dir_col, n_angle=180, thresh=None):
    """方向つき Hough のピークから直線 (rho, angle) を検出(hough_lines_dir)。"""
    acc = hough_line_trans_dir(edge_mask, dir_row, dir_col, n_angle)
    H, W = np.asarray(edge_mask, bool).shape
    rho_max = np.hypot(H, W)
    thr = thresh if thresh is not None else 0.5 * acc.max()
    peaks = np.argwhere(acc >= thr)
    nr = acc.shape[0]
    lines = []
    for ri, ai in peaks:
        rho = ri / (nr - 1) * 2 * rho_max - rho_max
        angle = ai / n_angle * np.pi
        lines.append((float(rho), float(angle), float(acc[ri, ai])))
    lines.sort(key=lambda t: -t[2])
    return lines
