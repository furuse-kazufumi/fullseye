"""XLD 輪郭の追加演算: 多角形ブール・交差・幾何統合・parallels・NURBS
(HALCON "Contours"/"XLD" chapter genuine 続き, numpy).

contours_xld のヘルパ(_contour/_rasterize/get_polygon_xld/*_closed_contours_xld)を再利用。
"""
from __future__ import annotations

import numpy as np

from contours_xld import (_contour, _rasterize, get_polygon_xld,
                          union2_closed_contours_xld, intersection_closed_contours_xld,
                          difference_closed_contours_xld, symm_difference_closed_contours_xld)
from tools_geom import (intersection_segments, intersection_segment_line,
                        intersection_segment_circle)


# ── 多角形ブール(closed polygons)= 閉輪郭ブールに委譲 ──────────────────────── #
def union2_closed_polygons_xld(c1, c2):
    """2 閉多角形の和(union2_closed_polygons_xld)。"""
    return union2_closed_contours_xld(c1, c2)


def intersection_closed_polygons_xld(c1, c2):
    """2 閉多角形の積(intersection_closed_polygons_xld)。"""
    return intersection_closed_contours_xld(c1, c2)


def difference_closed_polygons_xld(c1, c2):
    """2 閉多角形の差(difference_closed_polygons_xld)。"""
    return difference_closed_contours_xld(c1, c2)


def symm_difference_closed_polygons_xld(c1, c2):
    """2 閉多角形の対称差(symm_difference_closed_polygons_xld)。"""
    return symm_difference_closed_contours_xld(c1, c2)


def intersection_region_contour_xld(region, contour):
    """領域と閉輪郭の交差領域(intersection_region_contour_xld)。"""
    shape = contour.get("shape", np.asarray(region).shape)
    m = np.zeros(shape, bool)
    for a in contour["cs"]:
        if len(a) >= 3:
            m |= _rasterize(a, shape)
    return np.asarray(region, bool) & m


# ── 輪郭交差(接触点)─────────────────────────────────────────────────────────── #
def _seg_intersections(a, b):
    out = []
    for i in range(len(a) - 1):
        for j in range(len(b) - 1):
            p = intersection_segments((a[i, 0], a[i, 1], a[i + 1, 0], a[i + 1, 1]),
                                      (b[j, 0], b[j, 1], b[j + 1, 0], b[j + 1, 1]))
            if p is not None:
                out.append(p)
    return out


def intersection_contours_xld(contour1, contour2):
    """2 輪郭の交差点を返す(intersection_contours_xld)。"""
    out = []
    for a in contour1["cs"]:
        for b in contour2["cs"]:
            out.extend(_seg_intersections(a, b))
    return np.asarray(out) if out else np.zeros((0, 2))


def intersection_line_contour_xld(line, contour):
    """直線(2 端点)と輪郭の交差点(intersection_line_contour_xld)。"""
    out = []
    for a in contour["cs"]:
        for i in range(len(a) - 1):
            p = intersection_segment_line((a[i, 0], a[i, 1], a[i + 1, 0], a[i + 1, 1]), line)
            if p is not None:
                out.append(p)
    return np.asarray(out) if out else np.zeros((0, 2))


def intersection_segment_contour_xld(seg, contour):
    """線分と輪郭の交差点(intersection_segment_contour_xld)。"""
    out = []
    for a in contour["cs"]:
        for i in range(len(a) - 1):
            p = intersection_segments(seg, (a[i, 0], a[i, 1], a[i + 1, 0], a[i + 1, 1]))
            if p is not None:
                out.append(p)
    return np.asarray(out) if out else np.zeros((0, 2))


def intersection_circle_contour_xld(center, radius, contour):
    """円と輪郭の交差点(intersection_circle_contour_xld)。"""
    out = []
    for a in contour["cs"]:
        for i in range(len(a) - 1):
            out.extend(intersection_segment_circle(
                (a[i, 0], a[i, 1], a[i + 1, 0], a[i + 1, 1]), center, radius))
    return np.asarray(out) if out else np.zeros((0, 2))


# ── 輪郭の統合(幾何基準)────────────────────────────────────────────────────── #
def _dir(a):
    d = a[-1] - a[0]
    return d / (np.linalg.norm(d) + 1e-12)


def _endpoints(a):
    return a[0], a[-1]


def union_collinear_contours_xld(contour, max_dist=5.0, max_angle=0.15):
    """共線な輪郭断片を統合(union_collinear_contours_xld)。"""
    cs = [a.copy() for a in contour["cs"]]
    merged = True
    while merged and len(cs) > 1:
        merged = False
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                ang = np.arccos(np.clip(abs(_dir(cs[i]) @ _dir(cs[j])), -1, 1))
                gap = min(np.linalg.norm(p - q)
                          for p in _endpoints(cs[i]) for q in _endpoints(cs[j]))
                if ang < max_angle and gap < max_dist:
                    cs[i] = np.vstack([cs[i], cs[j]]); cs.pop(j); merged = True
                    break
            if merged:
                break
    return _contour(contour.get("shape", (256, 256)), cs)


def union_collinear_contours_ext_xld(contour, max_dist=5.0, max_angle=0.15):
    """共線統合(拡張パラメータ版)(union_collinear_contours_ext_xld)。"""
    return union_collinear_contours_xld(contour, max_dist, max_angle)


def union_straight_contours_xld(contour, max_dist=5.0, max_angle=0.15):
    """直線的な輪郭を統合(union_straight_contours_xld)。"""
    return union_collinear_contours_xld(contour, max_dist, max_angle)


def union_cotangential_contours_xld(contour, max_dist=5.0, max_angle=0.2):
    """接線連続な輪郭を統合(union_cotangential_contours_xld)。"""
    return union_collinear_contours_xld(contour, max_dist, max_angle)


def _fit_circle(a):
    A = np.column_stack([a[:, 1], a[:, 0], np.ones(len(a))])
    bb = a[:, 1] ** 2 + a[:, 0] ** 2
    sol, *_ = np.linalg.lstsq(A, bb, rcond=None)
    cx = sol[0] / 2; cy = sol[1] / 2
    r = np.sqrt(max(0.0, sol[2] + cx ** 2 + cy ** 2))
    return np.array([cy, cx]), r


def union_cocircular_contours_xld(contour, max_radius_diff=5.0):
    """共円(同一円上)な輪郭を統合(union_cocircular_contours_xld)。"""
    cs = [a.copy() for a in contour["cs"]]
    merged = True
    while merged and len(cs) > 1:
        merged = False
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                if len(cs[i]) < 3 or len(cs[j]) < 3:
                    continue
                ci, ri = _fit_circle(cs[i]); cj, rj = _fit_circle(cs[j])
                if abs(ri - rj) < max_radius_diff and np.linalg.norm(ci - cj) < max_radius_diff:
                    cs[i] = np.vstack([cs[i], cs[j]]); cs.pop(j); merged = True
                    break
            if merged:
                break
    return _contour(contour.get("shape", (256, 256)), cs)


# ── parallels / segment / NURBS ─────────────────────────────────────────────── #
def gen_parallels_xld(contour, distance=5.0):
    """各輪郭に平行なオフセット輪郭を生成(gen_parallels_xld)。"""
    out = []
    for a in contour["cs"]:
        d = np.gradient(a, axis=0)
        norm = np.hypot(d[:, 0], d[:, 1])[:, None] + 1e-12
        nvec = np.column_stack([-d[:, 1], d[:, 0]]) / norm
        out.append(a + distance * nvec)
        out.append(a - distance * nvec)
    return _contour(contour.get("shape", (256, 256)), out)


def mod_parallels_xld(contour, distance=5.0):
    """平行輪郭の生成(パラメータ変更版)(mod_parallels_xld)。"""
    return gen_parallels_xld(contour, distance)


def max_parallels_xld(contour, distance=5.0):
    """最大距離までの平行輪郭群(max_parallels_xld)。"""
    return gen_parallels_xld(contour, distance)


def segment_contours_xld(contour, max_line_dist=2.0):
    """輪郭を直線分に分割(segment_contours_xld)。"""
    polys = get_polygon_xld(contour, max_line_dist)
    out = []
    for poly in polys:
        for i in range(len(poly) - 1):
            out.append(np.vstack([poly[i], poly[i + 1]]))
    return _contour(contour.get("shape", (256, 256)), out)


def gen_contour_nurbs_xld(control_points, degree=3, n=100, shape=(256, 256)):
    """制御点から NURBS(B スプライン)輪郭を生成(gen_contour_nurbs_xld)。"""
    from scipy.interpolate import splprep, splev
    p = np.asarray(control_points, float).reshape(-1, 2)
    k = min(int(degree), len(p) - 1)
    tck, _ = splprep([p[:, 0], p[:, 1]], k=k, s=0)
    u = np.linspace(0, 1, int(n))
    r, c = splev(u, tck)
    return _contour(shape, [np.column_stack([r, c])])


def gen_nurbs_interp(points, degree=3, n=100, shape=(256, 256)):
    """点を通る NURBS 補間輪郭(gen_nurbs_interp)。"""
    return gen_contour_nurbs_xld(points, degree, n, shape)
