# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
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
    """各点の k 近傍インデックスと Euclid 距離(自己を除く)。→ (idx (N,k) int, dist (N,k) float)。

    ``scipy.spatial.cKDTree`` で各点の k+1 近傍を引き、自分自身(距離 0)を除いた k 個を返す。
    ``idx[i, j]`` は点 i に j 番目に近い点の添字、``dist[i, j]`` はその Euclid 距離(座標の単位)で、
    各行は距離の昇順。

    - ``points``: (N,3) など任意次元の座標(float64 に変換)。形状の検証はしない。
    - ``k``: 近傍数(既定 8)。``N-1`` を超える値は黙って ``N-1`` に切り詰める。
    - N < 2 のときは例外を出さず、形 (N,0) の空配列を 2 つ返す。

    罠: 座標が重複していると KD-tree が自己を列 0 に返さないことがある。その場合は行ごとに自己の
    位置を探して除き、k+1 個の中に自己が無ければ最遠の 1 つを落とす(結果はやはり k 個)。
    ``geodesic_distances`` / ``farthest_point_sampling`` はこの結果を隣接行列(有向 CSR、
    Dijkstra 側で無向化)にして測地距離の近似に使う。
    """
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
    """source から全点への測地距離(kNN グラフ上 Dijkstra)。→ (N,) float(不達は inf)。

    ``knn_graph(points, k)`` で作った k 近傍グラフ(辺の重み = 点間の Euclid 距離 = 弦長)を
    ``directed=False`` で無向化し、``scipy.sparse.csgraph.dijkstra`` で単一始点最短路を解く。
    ``d[i]`` は source から点 i までのグラフ上の経路長で ``d[source] = 0``、source と繋がっていない
    連結成分の点は ``inf``。単位は座標の単位そのまま。

    - ``points``: (N,3) の点群(float64 に変換)。
    - ``source``: 始点の添字(0..N-1 の整数。範囲外は scipy 側で例外)。
    - ``k``: 近傍数(既定 8)。小さいとグラフが分断されて ``inf`` が増え、大きいと離れた面どうしを
      直結する「近道」が生まれて曲面に沿わない距離になる(薄い板の表裏、折り返した面など)。

    精度: 辺が弦長なので弧をわずかに過小評価する一方、経路のジグザグが過大評価を生む(モジュール
    docstring の Bernstein らの挟み込み評価を参照)。三角メッシュがあるなら近傍数に依存しない
    ``geodesic_mesh`` を使う。この距離で均等に間引くには ``farthest_point_sampling``。
    """
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
