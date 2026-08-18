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


def smooth_object_model_3d(points, k: int = 8) -> np.ndarray:
    """各点を k 近傍の重心へ移動して平滑化(smooth_object_model_3d)。"""
    from scipy.spatial import cKDTree
    p = _pts(points)
    if len(p) <= k:
        return p
    _, idx = cKDTree(p).query(p, k=k)
    return p[idx].mean(axis=1)


def edges_object_model_3d(points, k: int = 12, thresh: float = 0.08) -> np.ndarray:
    """局所曲率が高い点=3D エッジを抽出(edges_object_model_3d)。近傍 PCA の平面性で判定。"""
    from scipy.spatial import cKDTree
    p = _pts(points)
    if len(p) <= k:
        return p
    _, idx = cKDTree(p).query(p, k=k)
    out = []
    for i, nb in enumerate(idx):
        d = p[nb] - p[nb].mean(0)
        w = np.linalg.eigvalsh(np.cov(d.T))
        w = np.clip(w, 0, None)
        curv = w[0] / (w.sum() + 1e-12)                  # 表面変動率(大=エッジ/角)
        if curv > thresh:
            out.append(p[i])
    return np.asarray(out) if out else np.zeros((0, 3))


def intersect_plane_object_model_3d(points, plane=(0.0, 0.0, 1.0, 0.0), tol: float = 0.05) -> np.ndarray:
    """平面(a,b,c,d)の近傍(距離<tol)の点=断面を返す(intersect_plane_object_model_3d)。"""
    p = _pts(points)
    a, b, c, d = plane
    nrm = np.array([a, b, c], float)
    dist = np.abs(p @ nrm + d) / (np.linalg.norm(nrm) + 1e-12)
    return p[dist < tol]


def triangulate_object_model_3d(points):
    """主平面へ投影して Delaunay 三角形分割(triangulate_object_model_3d)。三角形頂点 index を返す。"""
    from scipy.spatial import Delaunay
    p = _pts(points)
    if len(p) < 4:
        return {"points": p, "triangles": np.zeros((0, 3), int)}
    d = p - p.mean(0)
    _, V = np.linalg.eigh(np.cov(d.T))
    proj = d @ V[:, 1:]                                  # 分散最大の 2 主軸へ投影
    tri = Delaunay(proj).simplices
    return {"points": p, "triangles": tri}


def projective_trans_object_model_3d(points, H=None) -> np.ndarray:
    """4x4 射影変換を適用(projective_trans_object_model_3d)。既定は恒等。"""
    p = _pts(points)
    H = np.eye(4) if H is None else np.asarray(H, float)
    hom = np.column_stack([p, np.ones(len(p))]) @ H.T
    w = hom[:, 3:4]
    return hom[:, :3] / np.where(np.abs(w) < 1e-12, 1.0, w)


def area_object_model_3d(points) -> float:
    """点群を主平面 Delaunay 三角形化し表面積の近似を返す(area_object_model_3d)。"""
    tri = triangulate_object_model_3d(points)
    P, T = tri["points"], tri["triangles"]
    if len(T) == 0:
        return 0.0
    a = P[T[:, 1]] - P[T[:, 0]]
    b = P[T[:, 2]] - P[T[:, 0]]
    return float(0.5 * np.linalg.norm(np.cross(a, b), axis=1).sum())


def get_bounding_box_object_model_3d(points):
    """軸並行外接箱の (min, max, extent) を返す(get_bounding_box_object_model_3d)。"""
    p = _pts(points)
    lo, hi = p.min(0), p.max(0)
    return {"min": lo, "max": hi, "extent": hi - lo}


def reduce_object_model_3d_by_view(points, axis: int = 2, keep: float = 0.5):
    """指定軸で手前 keep 割合の点のみ残す(視点による簡易間引き、reduce_object_model_3d_by_view)。"""
    p = _pts(points)
    if len(p) == 0:
        return p
    thr = np.quantile(p[:, axis], keep)
    return p[p[:, axis] <= thr]
