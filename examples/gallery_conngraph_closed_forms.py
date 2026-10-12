# -*- coding: utf-8 -*-
"""事例: 結合グラフの op を教科書の閉形式で確かめる(conngraph ギャラリー)

平たく言うと:
  コネクトーム(神経の結合表)を読む conngraph の op は、どれも「隣接行列 W」を受けて数を返す。
  その数が正しいかは、形の分かったグラフ(星・道・環・完全グラフ・二つの塊)なら紙と鉛筆で出せる。
  ここではその手計算を真値にして 10 op を 1 本ずつ呼び、「何を期待し、何が出て、合ったか」を印字する。
  外れたら exit 1。図は作らない、乱数は使わない。

確かめ方(op ごとの真値):
  * graph_binarize               —— |W| > thresh の辺だけ 1(負の重みも絶対値で数える)
  * graph_components             —— 繋がっていない三角形と道は 2 成分、番号はノード順の初出
  * graph_betweenness            —— 無向の星(6 点)の中心 (n−1)(n−2)/2 = 10・葉 0、無向の道 i(n−1−i)、有向の道は順序対
  * graph_clustering_coefficient —— 完全グラフ 1、木 0、三角形 + 垂れ下がり 1 点で (1/3 + 1 + 1 + 0)/4 = 7/12
  * graph_laplacian_spectrum     —— 環(8 点)の 2 − 2cos(2πk/8)、二つの成分なら零固有値が 2 個
  * graph_layout_spectral        —— 道の Fiedler ベクトルは単調(並びが道の順になる)、各軸 [0, 1]、dim=2 で z = 0
  * graph_modularity             —— 離れた K4 二つを塊ごとに分けると Q = 1/2、全部 1 群なら厳密に 0
  * graph_motif_count            —— 有向三角形 cycle3 = 1、FFL = 1、相互結合の完全 K4 で 6 / 24 / 8
  * graph_edges_as_lines         —— 線分の端点 = 配置の座標、重み = W、対角は出さない
  * graph_adjacency_image        —— log1p(|W|)/max の画像、order="degree" で星の中心が先頭の行に来る

    py -3.11 examples/gallery_conngraph_closed_forms.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import conngraph as CG  # noqa: E402

ROWS: list = []


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def undirected(n: int, edges) -> np.ndarray:
    """無向の辺の並びから対称な 0/1 の隣接行列を作る。"""
    W = np.zeros((n, n))
    for a, b in edges:
        W[a, b] = W[b, a] = 1.0
    return W


def directed(n: int, edges) -> np.ndarray:
    """有向の辺 a→b の並びから隣接行列を作る(W[a, b] = 1)。"""
    W = np.zeros((n, n))
    for a, b in edges:
        W[a, b] = 1.0
    return W


def star(n: int, hub: int = 0) -> np.ndarray:
    return undirected(n, [(hub, j) for j in range(n) if j != hub])


def complete(n: int) -> np.ndarray:
    return np.ones((n, n)) - np.eye(n)


def demo_structure() -> None:
    W = np.array([[0.0, -0.5, 0.2], [0.05, 0.0, 0.0], [0.0, 0.3, 0.0]])
    B = CG.graph_binarize(W, thresh=0.1)
    want = (np.abs(W) > 0.1).astype(float)
    check("graph_binarize", "重み (−0.5, 0.2, 0.05, 0.3)、thresh 0.1", f"辺 {int(want.sum())} 本(負の −0.5 も 1)",
          f"辺 {int(B.sum())} 本、行列の一致 {np.array_equal(B, want)}", np.array_equal(B, want))

    tri_path = undirected(7, [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 6)])
    lab = CG.graph_components(tri_path)
    check("graph_components", "三角形 {0,1,2} と道 {3..6}", "[0 0 0 1 1 1 1]", str(lab.tolist()),
          lab.tolist() == [0, 0, 0, 1, 1, 1, 1])
    perm = [4, 0, 5, 1, 6, 2, 3]  # 道の点を先に置く
    labp = CG.graph_components(tri_path[np.ix_(perm, perm)])
    check("graph_components", "同じグラフをノード順を混ぜて", "初出順の番号 [0 1 0 1 0 1 0]", str(labp.tolist()),
          labp.tolist() == [0, 1, 0, 1, 0, 1, 0])

    bc = CG.graph_betweenness(star(6))
    check("graph_betweenness", "無向の星(6 点)", "中心 (n−1)(n−2)/2 = 10、葉 0", str(np.round(bc, 12).tolist()),
          abs(bc[0] - 10) < 1e-12 and np.all(np.abs(bc[1:]) < 1e-12))
    bp = CG.graph_betweenness(undirected(5, [(i, i + 1) for i in range(4)]))
    wp = [i * (4 - i) for i in range(5)]
    check("graph_betweenness", "無向の道(5 点)", f"i(n−1−i) = {wp}", str(np.round(bp, 12).tolist()), np.allclose(bp, wp))
    bd = CG.graph_betweenness(directed(3, [(0, 1), (1, 2)]))
    check("graph_betweenness", "有向の道 0→1→2", "中央 1(順序対 (0,2) の 1 本だけ)", str(np.round(bd, 12).tolist()),
          np.allclose(bd, [0, 1, 0]))

    c_full = CG.graph_clustering_coefficient(complete(5))
    c_tree = CG.graph_clustering_coefficient(star(6))
    c_mix = CG.graph_clustering_coefficient(undirected(4, [(0, 1), (1, 2), (2, 0), (0, 3)]))
    check("graph_clustering_coefficient", "完全グラフ K5 / 木(星)", "1 / 0", f"{c_full} / {c_tree}",
          abs(c_full - 1) < 1e-12 and abs(c_tree) < 1e-12)
    check("graph_clustering_coefficient", "三角形 + 垂れ下がり 1 点", f"(1/3 + 1 + 1 + 0)/4 = {7 / 12:.12f}",
          f"{c_mix:.12f}", abs(c_mix - 7 / 12) < 1e-12)


def demo_spectral() -> None:
    n = 8
    ring = undirected(n, [(i, (i + 1) % n) for i in range(n)])
    ev = CG.graph_laplacian_spectrum(ring)
    want = np.sort([2 - 2 * math.cos(2 * math.pi * k / n) for k in range(n)])
    check("graph_laplacian_spectrum", "環(8 点)", "2 − 2cos(2πk/8) を昇順に",
          f"最大差 {np.abs(ev - want).max():.1e}", np.abs(ev - want).max() < 1e-10)
    two = undirected(7, [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 6)])
    ev2 = CG.graph_laplacian_spectrum(two)
    nz = int(np.sum(np.abs(ev2) < 1e-9))
    check("graph_laplacian_spectrum", "三角形 + 道(2 成分)", "零固有値 2 個", f"{nz} 個", nz == 2)
    # 有向でも向きを畳む: 片向きの環は無向の環と同じスペクトル
    ev3 = CG.graph_laplacian_spectrum(directed(n, [(i, (i + 1) % n) for i in range(n)]))
    check("graph_laplacian_spectrum", "片向きの環(向きを畳む)", "無向の環と同じ固有値",
          f"最大差 {np.abs(ev3 - want).max():.1e}", np.abs(ev3 - want).max() < 1e-10)

    m = 9
    P = CG.graph_layout_spectral(undirected(m, [(i, i + 1) for i in range(m - 1)]), dim=2, seed=0)
    x = P[:, 0]
    mono = bool(np.all(np.diff(x) > 0) or np.all(np.diff(x) < 0))
    check("graph_layout_spectral", "道(9 点)の第 1 軸", "Fiedler ベクトルは道の順に単調",
          f"単調 {mono}(x = {np.round(x, 3).tolist()})", mono)
    check("graph_layout_spectral", "形と範囲(dim=2)", "(9, 3)、各軸 [0, 1]、z = 0",
          f"{P.shape}、最小 {P.min():.3f}、最大 {P.max():.3f}、|z| 最大 {np.abs(P[:, 2]).max()}",
          P.shape == (m, 3) and P.min() >= 0 and P.max() <= 1 and np.all(P[:, 2] == 0))
    P2 = CG.graph_layout_spectral(two, dim=2, seed=0)
    lab = CG.graph_components(two)
    a, b = P2[lab == 0, :2], P2[lab == 1, :2]
    gap = min(np.linalg.norm(p - q) for p in a for q in b)
    span = max(np.ptp(a, axis=0).max(), np.ptp(b, axis=0).max())
    check("graph_layout_spectral", "2 成分は成分ごとに箱を分ける", "成分間の最短距離 > 成分内の広がり",
          f"間 {gap:.3f}、内 {span:.3f}", gap > span)


def demo_counts() -> None:
    k4 = complete(4)
    two = np.zeros((8, 8))
    two[:4, :4] = k4
    two[4:, 4:] = k4
    q = CG.graph_modularity(two, [0, 0, 0, 0, 1, 1, 1, 1])
    q1 = CG.graph_modularity(two, [0] * 8)
    check("graph_modularity", "離れた K4 二つを塊ごとに", "Q = (1/24)(24 − 2·12·12/24) = 1/2", f"{q:.15f}",
          abs(q - 0.5) < 1e-12)
    check("graph_modularity", "全部 1 群", "厳密に 0", f"{q1}", q1 == 0.0)
    qbad = CG.graph_modularity(two, [0, 1, 0, 1, 0, 1, 0, 1])
    check("graph_modularity", "塊をまたいで交互に分ける", "1/2 より小さい(負)", f"{qbad:.6f}", qbad < 0.0)

    cyc = directed(3, [(0, 1), (1, 2), (2, 0)])
    ffl = directed(3, [(0, 1), (1, 2), (0, 2)])
    got = (CG.graph_motif_count(cyc, "cycle3"), CG.graph_motif_count(cyc, "ffl"),
           CG.graph_motif_count(ffl, "cycle3"), CG.graph_motif_count(ffl, "ffl"))
    check("graph_motif_count", "有向三角形 / FFL(a→b→c, a→c)", "cycle3 1・ffl 0 / cycle3 0・ffl 1", str(got),
          got == (1.0, 0.0, 0.0, 1.0))
    full = tuple(CG.graph_motif_count(k4, m) for m in ("reciprocal", "ffl", "cycle3"))
    check("graph_motif_count", "相互結合の完全 K4", "reciprocal C(4,2)=6・ffl 12×2=24・cycle3 4·3·2/3=8", str(full),
          full == (6.0, 24.0, 8.0))


def demo_drawing() -> None:
    W = np.array([[0.5, 2.0, 0.0], [0.0, 0.0, -1.0], [3.0, 0.0, 0.0]])  # 対角 0.5 は出さない
    P = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 2.0, 1.0]])
    t = CG.graph_edges_as_lines(W, P, thresh=0.0)
    pre, post = np.asarray(t["pre"], int), np.asarray(t["post"], int)
    ends_ok = (np.allclose(np.c_[t["x0"], t["y0"], t["z0"]], P[pre])
               and np.allclose(np.c_[t["x1"], t["y1"], t["z1"]], P[post]))
    pairs = sorted(zip(pre.tolist(), post.tolist()))
    check("graph_edges_as_lines", "3 辺 + 自己結合 1 本", "線分 3 本 (0,1)(1,2)(2,0)、端点 = P、重み = W",
          f"{pairs}、端点一致 {ends_ok}、重み {np.asarray(t['weight']).tolist()}",
          pairs == [(0, 1), (1, 2), (2, 0)] and ends_ok and np.allclose(t["weight"], W[pre, post]))

    Ws = star(5, hub=3) * 2.0
    img = CG.graph_adjacency_image(Ws, order="none", log=True)
    want = np.log1p(np.abs(Ws)) / np.log1p(2.0)
    check("graph_adjacency_image", "星(中心 3)、order none", "log1p(|W|)/max", f"最大差 {np.abs(img - want).max():.1e}",
          np.abs(img - want).max() < 1e-12)
    imd = CG.graph_adjacency_image(Ws, order="degree", log=False)
    row0 = int((imd[0] > 0).sum())
    check("graph_adjacency_image", "同じ星、order degree", "先頭の行 = 中心(非零 4 個)、値は 0/1",
          f"先頭の行の非零 {row0}、値 {sorted(set(np.round(imd.ravel(), 12).tolist()))}",
          row0 == 4 and set(np.round(imd.ravel(), 12).tolist()) == {0.0, 1.0})


def main() -> int:
    t0 = time.time()
    demo_structure()
    demo_spectral()
    demo_counts()
    demo_drawing()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len({r[0] for r in ROWS})} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
