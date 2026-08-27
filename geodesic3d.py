"""geodesic3d — 曲面/点群上の測地距離(EDT の線→面拡張: kNN・メッシュグラフ上 Dijkstra + FPS)。

距離変換(EDT)は「格子上の直線距離」だが、Physical AI では**曲面に沿った距離**が要る
(把持面上の移動コスト、地形踏破コスト、パーツ表面の展開)。ここでは点群/三角メッシュを
グラフ化し、その上の最短路を測地距離の離散近似として計算する(Isomap/Dijkstra 型)。

理論的裏付け(Bernstein–de Silva–Langford–Tenenbaum 2000, "Graph approximations to
geodesics on embedded manifolds"): サンプリングが十分密なら kNN グラフ最短路 d_G は真の
多様体測地 d_M を (1-ε1) d_M ≤ d_G ≤ (1+ε2) d_M で挟む。エッジは弦長(直線距離)なので
弧をわずかに**過小評価**する一方、経路のジグザグが**過大評価**へ寄与し、密なら後者が優勢で
実測は数%の上振れに収まる(球面一様サンプリングで ~8% が経験的上限)。

用途: 表面測地距離(展開/経路)、地形踏破コスト、測地 farthest-point sampling(均等間引き)。
"""
from typing import Tuple

import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra


def knn_graph(points: np.ndarray, k: int = 8) -> Tuple[np.ndarray, np.ndarray]:
    """各点の k 近傍インデックスと Euclid 距離(自己を除く)。→ (idx (N,k) int, dist (N,k) float)。"""
    P = np.asarray(points, dtype=float)
    n = P.shape[0]
    if n < 2:
        return np.zeros((n, 0), dtype=int), np.zeros((n, 0), dtype=float)
    k = int(min(k, n - 1))
    tree = cKDTree(P)
    dist, idx = tree.query(P, k=k + 1)
    dist = np.atleast_2d(dist)
    idx = np.atleast_2d(idx)
    ar = np.arange(n)
    # 通常 query は自己(距離 0)を列 0 で返す。その速い経路を優先。
    if np.array_equal(idx[:, 0], ar):
        return idx[:, 1:k + 1].astype(int), dist[:, 1:k + 1].astype(float)
    # 重複座標などで自己が列 0 でない場合の堅牢な除去(自己が無ければ最遠を落とす)。
    out_i = np.empty((n, k), dtype=int)
    out_d = np.empty((n, k), dtype=float)
    for i in range(n):
        ri, rd = idx[i], dist[i]
        pos = np.nonzero(ri == i)[0]
        drop = int(pos[0]) if pos.size else k  # 自己が無ければ最遠(末尾)を除去
        keep = [j for j in range(k + 1) if j != drop][:k]
        out_i[i] = ri[keep]
        out_d[i] = rd[keep]
    return out_i, out_d


def _knn_csr(points: np.ndarray, k: int) -> csr_matrix:
    """kNN から重み付き隣接行列(有向 CSR、Euclid 距離重み)を組む。Dijkstra は directed=False で無向化。"""
    idx, dist = knn_graph(points, k)
    n = idx.shape[0]
    m = idx.shape[1]
    rows = np.repeat(np.arange(n), m)
    cols = idx.ravel()
    data = dist.ravel()
    return csr_matrix((data, (rows, cols)), shape=(n, n))


def geodesic_distances(points: np.ndarray, source: int, k: int = 8) -> np.ndarray:
    """source から全点への測地距離(kNN グラフ上 Dijkstra)。→ (N,) float(不達は inf)。"""
    g = _knn_csr(points, k)
    d = dijkstra(g, directed=False, indices=int(source))
    return np.asarray(d, dtype=float)


def geodesic_mesh(vertices: np.ndarray, faces: np.ndarray, source: int) -> np.ndarray:
    """三角メッシュのエッジグラフ上 Dijkstra で source から各頂点への測地距離。→ (V,) float。"""
    V = np.asarray(vertices, dtype=float)
    F = np.asarray(faces, dtype=int)
    if F.size == 0:
        n = V.shape[0]
        out = np.full(n, np.inf)
        if 0 <= int(source) < n:
            out[int(source)] = 0.0
        return out
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=0)
    # 無向エッジを (min,max) で一意化してから重みを与える。csr_matrix は重複 (i,j) の
    # 重みを黙って加算するため、重複面・非多様体・不整合ワインディングでは同一エッジが
    # 複数回積まれ測地距離が膨張する(重複面で最大 2 倍)。弦長は重複でも同値なので、
    # 一意エッジに 1 つだけ与えれば正しい。退化エッジ(i==j)は自己ループなので除去。
    lo = np.minimum(e[:, 0], e[:, 1])
    hi = np.maximum(e[:, 0], e[:, 1])
    pairs = np.stack([lo, hi], axis=1)
    nondegen = pairs[:, 0] != pairs[:, 1]
    pairs = pairs[nondegen]
    uniq = np.unique(pairs, axis=0)
    seg = np.linalg.norm(V[uniq[:, 0]] - V[uniq[:, 1]], axis=1)
    n = V.shape[0]
    # 片方向のみ格納(dijkstra は directed=False で無向化)。重複加算はもう起きない。
    g = csr_matrix((seg, (uniq[:, 0], uniq[:, 1])), shape=(n, n))
    d = dijkstra(g, directed=False, indices=int(source))
    return np.asarray(d, dtype=float)


def farthest_point_sampling(points: np.ndarray, n: int, k: int = 8, start: int = 0) -> np.ndarray:
    """測地距離での最遠点サンプリング(均等間引き)。→ 選択インデックス列 (n,) int。"""
    P = np.asarray(points, dtype=float)
    N = P.shape[0]
    n = int(max(0, min(n, N)))
    if n == 0:
        return np.zeros((0,), dtype=int)
    start = int(start) % N
    g = _knn_csr(P, k)
    selected = [start]
    # mind[i] = 既選択集合への測地距離の最小値(集合距離 = 各メンバ単源距離の要素毎 min)。
    mind = np.asarray(dijkstra(g, directed=False, indices=start), dtype=float).copy()
    mind[start] = -np.inf  # 再選択防止
    for _ in range(1, n):
        nxt = int(np.argmax(mind))
        selected.append(nxt)
        dn = np.asarray(dijkstra(g, directed=False, indices=nxt), dtype=float)
        mind = np.minimum(mind, dn)
        mind[selected] = -np.inf
    return np.asarray(selected, dtype=int)
