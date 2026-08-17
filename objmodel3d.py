"""3D object model 演算(HALCON "3D Object Model" chapter の genuine 実装, numpy/scipy).

evis の把持/地形知覚(pcseg/ppf/registration)を補完する 3D 点群オブジェクト演算。
各関数は実 HALCON operator の機能を本物のアルゴリズムで実装する(推測マッピング禁止)。
点群は (N,3) float64。halcon_facade_map.json 経由でカバレッジ計上。
"""
from __future__ import annotations

import numpy as np


def _pts(p):
    return np.asarray(p, dtype=np.float64).reshape(-1, 3)


# ── プリミティブ 3D モデル生成 ──────────────────────────────────────────────── #
def gen_plane_object_model_3d(size: float = 1.0, n: int = 20) -> np.ndarray:
    """z=0 平面上の格子点群(gen_plane_object_model_3d)。"""
    u = np.linspace(-size, size, n)
    x, y = np.meshgrid(u, u)
    return np.column_stack([x.ravel(), y.ravel(), np.zeros(x.size)])


def gen_sphere_object_model_3d(radius: float = 1.0, n: int = 400) -> np.ndarray:
    """球面上の準一様点群(黄金螺旋、gen_sphere_object_model_3d)。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    return radius * np.column_stack([np.sin(phi) * np.cos(theta),
                                     np.sin(phi) * np.sin(theta), np.cos(phi)])


def gen_box_object_model_3d(size=(1.0, 1.0, 1.0), n: int = 10) -> np.ndarray:
    """箱の 6 面の点群(gen_box_object_model_3d)。"""
    hx, hy, hz = (s / 2 for s in size)
    u = np.linspace(-1, 1, n)
    a, b = np.meshgrid(u, u)
    a, b, o = a.ravel(), b.ravel(), np.ones(n * n)
    faces = [np.column_stack([a * hx, b * hy, o * hz]), np.column_stack([a * hx, b * hy, -o * hz]),
             np.column_stack([a * hx, o * hy, b * hz]), np.column_stack([a * hx, -o * hy, b * hz]),
             np.column_stack([o * hx, a * hy, b * hz]), np.column_stack([-o * hx, a * hy, b * hz])]
    return np.unique(np.vstack(faces), axis=0)


def gen_cylinder_object_model_3d(radius: float = 1.0, height: float = 2.0, n: int = 30) -> np.ndarray:
    """円柱側面の点群(gen_cylinder_object_model_3d)。"""
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    z = np.linspace(-height / 2, height / 2, n)
    T, Z = np.meshgrid(th, z)
    return np.column_stack([radius * np.cos(T).ravel(), radius * np.sin(T).ravel(), Z.ravel()])


# ── 3D モデル解析 ───────────────────────────────────────────────────────────── #
def convex_hull_object_model_3d(points) -> np.ndarray:
    """3D 凸包の頂点を返す(convex_hull_object_model_3d)。"""
    from scipy.spatial import ConvexHull
    p = _pts(points)
    if len(p) < 4:
        return p
    return p[ConvexHull(p).vertices]


def moments_object_model_3d(points):
    """3D 点群の重心と共分散(2 次中心モーメント)を返す(moments_object_model_3d)。"""
    p = _pts(points)
    c = p.mean(0)
    cov = np.cov((p - c).T)
    return {"centroid": c, "covariance": cov}


def max_diameter_object_model_3d(points) -> float:
    """点群の最大差し渡し径(convex 包上で最遠 2 点、max_diameter_object_model_3d)。"""
    p = _pts(points)
    if len(p) < 2:
        return 0.0
    try:
        from scipy.spatial import ConvexHull
        p = p[ConvexHull(p).vertices]
    except Exception:
        pass
    from scipy.spatial.distance import pdist
    return float(pdist(p).max())


def smallest_sphere_object_model_3d(points):
    """最小包含球の近似(中心=重心、半径=最遠点、smallest_sphere_object_model_3d)。"""
    p = _pts(points)
    c = p.mean(0)
    r = float(np.sqrt(((p - c) ** 2).sum(1)).max()) if len(p) else 0.0
    return {"center": c, "radius": r}


def distance_object_model_3d(points_a, points_b) -> float:
    """2 つの 3D モデル間の最小点間距離(distance_object_model_3d)。"""
    from scipy.spatial import cKDTree
    a, b = _pts(points_a), _pts(points_b)
    if len(a) == 0 or len(b) == 0:
        return 0.0
    return float(cKDTree(b).query(a, k=1)[0].min())


def select_points_object_model_3d(points, axis: int = 2, lo: float = -np.inf, hi: float = np.inf) -> np.ndarray:
    """指定軸の値域で点を選ぶ(select_points_object_model_3d)。"""
    p = _pts(points)
    m = (p[:, axis] >= lo) & (p[:, axis] <= hi)
    return p[m]


def union_object_model_3d(points_a, points_b) -> np.ndarray:
    """2 つの 3D モデルを結合(union_object_model_3d)。"""
    return np.vstack([_pts(points_a), _pts(points_b)])
