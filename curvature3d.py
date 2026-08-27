"""curvature3d — 点群の主曲率・平均/ガウス曲率・shape index(局所二次曲面フィット)。

match3d.curvature_maps は voxel 場の曲率だが、ここは**非構造点群**の各点で局所 Monge パッチ
w=f(u,v) を最小二乗フィットし、第一/第二基本形式から主曲率 k1,k2 を出す(再パラメータ化に頑健)。
符号規約 = **外向き法線で凸を正**(近傍重心から離れる向きに法線を統一)。ガウス曲率 K=k1k2 は
法線の反転に不変、平均曲率 H・shape index は向きに依存するので上記規約で一貫させる。

GT: 半径 R の球 → k1=k2=1/R・K=1/R² / 円柱 → k1=1/R,k2=0・K=0 / 平面 → 0。
shape index(Koenderink)= 球(凸)+1・円柱 +0.5・鞍点 0・平面 不定(0 扱い)。

用途: 把持アフォーダンス(凸/凹/鞍点判定)、表面分類、曲率異常による欠陥検出(Physical AI)。
"""
import numpy as np
from scipy.spatial import cKDTree


def _knn_idx(points, k):
    """各点の (自身含む) k+1 近傍インデックス。→ (N, k+1) int。"""
    p = np.asarray(points, float)
    k = min(k, len(p) - 1)
    tree = cKDTree(p)
    _, idx = tree.query(p, k=k + 1)
    return np.atleast_2d(idx)


def _principal_at(local):
    """クエリ点を原点にした近傍 (m,3) → 主曲率 (k1>=k2) と外向き法線。

    PCA で法線(最小固有ベクトル)を推定 → 接線基底で Monge 形 w=du+ev+au²+buv+cv² を
    フィット → 第一/第二基本形式の shape operator 固有値で k1,k2。凸(外向き)を正に符号統一。
    """
    if len(local) < 5:
        return 0.0, 0.0, np.array([0.0, 0.0, 1.0])
    C = local.T @ local
    w_eig, V = np.linalg.eigh(C)
    normal = V[:, 0]                 # 最小固有値方向 = 法線
    centroid = local.mean(axis=0)
    if np.dot(centroid, normal) > 0:  # 近傍の重心から離れる向き(外向き)へ
        normal = -normal
    t1 = V[:, 2] - np.dot(V[:, 2], normal) * normal
    t1 /= np.linalg.norm(t1) + 1e-12
    t2 = np.cross(normal, t1)
    u = local @ t1
    v = local @ t2
    wc = local @ normal
    A = np.stack([u, v, u * u, u * v, v * v], axis=1)
    coef, *_ = np.linalg.lstsq(A, wc, rcond=None)
    d, e, a, b, c = coef
    fx, fy, fxx, fxy, fyy = d, e, 2 * a, b, 2 * c
    denom = np.sqrt(1 + fx * fx + fy * fy)
    I1 = np.array([[1 + fx * fx, fx * fy], [fx * fy, 1 + fy * fy]])
    II = np.array([[fxx, fxy], [fxy, fyy]]) / denom
    S = np.linalg.solve(I1, II)      # shape operator
    ev = np.sort(np.linalg.eigvals(S).real)
    # 外向き法線だと凸面は負固有値 → 符号反転して凸=正、k1>=k2 を維持
    k1, k2 = -ev[0], -ev[1]
    return k1, k2, normal


def _curvatures(points, k):
    """全点の (k1, k2, normals)。→ (N,), (N,), (N,3)。"""
    p = np.asarray(points, float)
    idx = _knn_idx(p, k)
    n = len(p)
    K1 = np.zeros(n)
    K2 = np.zeros(n)
    NRM = np.zeros((n, 3))
    for i in range(n):
        local = p[idx[i]] - p[i]     # クエリ点を原点に
        K1[i], K2[i], NRM[i] = _principal_at(local)
    return K1, K2, NRM


def principal_curvatures(points, k=25):
    """各点の主曲率 (k1>=k2)。→ (k1 (N,), k2 (N,))。凸(外向き法線)を正。"""
    K1, K2, _ = _curvatures(points, k)
    return K1, K2


def mean_curvature(points, k=25):
    """平均曲率 H=(k1+k2)/2。→ (N,)。外向き法線で凸=正。"""
    K1, K2, _ = _curvatures(points, k)
    return (K1 + K2) / 2.0


def gaussian_curvature(points, k=25):
    """ガウス曲率 K=k1·k2(法線の反転に不変)。→ (N,)。"""
    K1, K2, _ = _curvatures(points, k)
    return K1 * K2


def shape_index(points, k=25):
    """Koenderink の shape index s∈[-1,1](凸球+1・円柱+0.5・鞍点0・凹球-1)。→ (N,)。"""
    K1, K2, _ = _curvatures(points, k)
    diff = K1 - K2
    ssum = K1 + K2
    s = np.zeros_like(K1)
    flat = np.abs(diff) < 1e-9
    s[~flat] = (2.0 / np.pi) * np.arctan(ssum[~flat] / diff[~flat])
    # k1≈k2(臍点): 曲率が有意なら sign、無ければ 0(平面)
    umb = flat & (np.abs(ssum) > 1e-6)
    s[umb] = np.sign(ssum[umb])
    return s


def curvedness(points, k=25):
    """curvedness C=√((k1²+k2²)/2)(曲がりの強さ、shape index と直交な量)。→ (N,)。"""
    K1, K2, _ = _curvatures(points, k)
    return np.sqrt((K1 ** 2 + K2 ** 2) / 2.0)


def estimate_normals(points, k=25):
    """外向き(近傍重心から離れる)に統一した点群法線。→ (N,3)。"""
    _, _, NRM = _curvatures(points, k)
    return NRM
