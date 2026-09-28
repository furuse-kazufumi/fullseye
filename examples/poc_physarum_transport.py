# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""粘菌は最適輸送を解く —— 源と吸込を「質量の分布」にすると、同じ管の力学が Earth Mover 距離へ収束する。

    py -3.11 examples/poc_physarum_transport.py

PoC ⑫(粘菌の管は迷路を解く)は源 1 つ・吸込 1 つだった。源と吸込を供給ベクトル b(Σ b = 0、正 = 質量が入る、
負 = 出る)にすると、同じ力学 —— キルヒホッフで圧力を解き、Q = D (p_u − p_v) / L、dD/dt = |Q| − D —— が

    min Σ_e L_e |q_e|   s.t. 各節点の正味の流出 = b

の解、すなわちグラフ上の L1 最適輸送(Beckmann 問題 = b⁺ と b⁻ の 1-Wasserstein 距離)へ収束する
(Bonifaci 2017 *J. Math. Biol.*; Facca–Karrenbauer–Kolev–Mehlhorn 2020 *TCS*; 連続体は Facca–Cardin–Putti
2018 *SIAM J. Appl. Math.*)。Fullseye の op 2 本で回す:

* ``graph_physarum_transport`` —— 重み付きグラフ + 供給ベクトル。
* ``physarum_transport_image`` —— 質量画像 2 枚(画素を長さ 1 の管で結ぶ = マンハッタン距離の EMD)。

op は費用 Σ L|Q|(上界)と一緒に **Kantorovich–Rubinstein の下界**(圧力を 1-Lipschitz にした McShane 包絡
φ の bᵀφ)を返す。真の距離は必ずその間に在るので、隙間 = 「いまの流れが最適から幾ら離れているか」の証明書
になり、隙間が閉じたら止まる。

この PoC が測る主張:
    **管の力学は、答えを知らずに最適輸送へ来る。** 5 つの真値のどれとも一致する。
検査する恒等式(下の assert、当てはめた数字は無い):
1. 木の閉形式: 木では辺 e を渡る質量が一意に決まり W1 = Σ_e L_e |部分木の供給の和|。乱数の木 5 本で相対 1e-6。
2. 1 次元の閉形式: 不等間隔の 1 次元格子で W1 = 累積分布の差の積分(既存 op ``wasserstein_1d``)。
3. 割当問題: 点 m 個 ↔ m 個の完全 2 部グラフ(ユークリッド長)で W1 = Hungarian 法の最小割当 / m
   (Birkhoff: 輸送 LP の最適は整数解)。生き残った管の集合 = 最適割当そのもの。
4. 最小費用流の LP: 小さな格子の乱数質量で ``scipy.optimize.linprog``(HiGHS)の最適値。
5. 平行移動の定理: 形を (dr, dc) 画素ずらした画像との EMD = |dr| + |dc|(4 近傍)。上界は各画素を真っ直ぐ
   運ぶ流れ、下界は φ = ±r ± c(1-Lipschitz)で、両者が一致する。
6. 弱双対性: どの反復でも 下界 ≤ 真値 ≤ 費用(厳密)。単一対では 下界 = Dijkstra の距離(圧力の包絡 = 最短路の
   ポテンシャル)。
7. 距離の公理: 対称、質量と長さに線形、三角不等式。

先行研究: 粘菌の力学が最適輸送を解くことは上の論文が証明している。GitHub の Physarum 実装(迷路・Steiner 木)
に「双対の下界で証明書を返す」「木・1 次元・割当・LP の真値で門をかけた」物は見つからなかった(2026-09-28 に
Web と RAD を引いた)。Facca らの DMK ソルバは FEM の連続体版で別物。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import examplefig as figs  # noqa: E402
import physarum_search as PS  # noqa: E402
from colortransport import wasserstein_1d  # noqa: E402


# ---- 真値の作り方 -------------------------------------------------------------------------------
def random_tree(n: int, seed: int):
    """節点 k の親を 0..k−1 から一様に引く木、辺長 U(0.5, 1.5)。"""
    rng = np.random.default_rng(seed)
    A = np.zeros((n, n))
    parent = np.full(n, -1)
    for k in range(1, n):
        p = int(rng.integers(0, k))
        parent[k] = p
        A[k, p] = A[p, k] = rng.uniform(0.5, 1.5)
    return A, parent


def tree_w1(A, parent, s) -> float:
    """木の上の W1 の閉形式: Σ_e L_e |部分木の供給の和|(子は親より番号が大きい)。"""
    sub = np.asarray(s, float).copy()
    for k in range(len(parent) - 1, 0, -1):
        sub[parent[k]] += sub[k]
    return float(sum(A[k, parent[k]] * abs(sub[k]) for k in range(1, len(parent))))


def centered_supply(n: int, seed: int, k_src=5, k_dst=5) -> np.ndarray:
    rng = np.random.default_rng(seed)
    s = np.zeros(n)
    src = rng.choice(n, k_src, replace=False)
    dst = rng.choice(np.setdiff1d(np.arange(n), src), k_dst, replace=False)
    s[src] = rng.uniform(0.5, 1.5, k_src)
    s[dst] = -rng.uniform(0.5, 1.5, k_dst)
    s[dst] *= s[src].sum() / -s[dst].sum()
    return s


def lattice(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    A = np.zeros((n * n, n * n))
    for r in range(n):
        for c in range(n):
            u = r * n + c
            if c + 1 < n:
                A[u, u + 1] = A[u + 1, u] = rng.uniform(0.5, 1.5)
            if r + 1 < n:
                A[u, u + n] = A[u + n, u] = rng.uniform(0.5, 1.5)
    return A


def disk(H, W, cy, cx, r) -> np.ndarray:
    yy, xx = np.mgrid[:H, :W]
    return ((yy - cy) ** 2 + (xx - cx) ** 2 <= r * r).astype(float)


# ---- 描画(numpy だけ) ---------------------------------------------------------------------------
def raster_lines(H, W, p0, p1, alpha):
    """線分の束を加算で描く(PoC ⑬ と同じ作り)。"""
    acc = np.zeros((H, W))
    if len(p0) == 0:
        return acc
    L = np.hypot(*(p1 - p0).T)
    m = np.maximum(2, np.ceil(L * 1.5).astype(int))
    for k in np.unique(m):
        sel = m == k
        t = np.linspace(0.0, 1.0, k)[None, :, None]
        pts = p0[sel][:, None, :] * (1 - t) + p1[sel][:, None, :] * t
        a = np.repeat(alpha[sel], k)
        x = np.clip(np.rint(pts[..., 0]).astype(int).ravel(), 0, W - 1)
        y = np.clip(np.rint(pts[..., 1]).astype(int).ravel(), 0, H - 1)
        np.add.at(acc, (y, x), a)
    return acc


def stamp(img, xy, r, rgb):
    H, W = img.shape[:2]
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = (xx ** 2 + yy ** 2) <= r * r
    for x, y in xy:
        x, y = int(round(x)), int(round(y))
        y0, y1 = max(0, y - r), min(H, y + r + 1)
        x0, x1 = max(0, x - r), min(W, x + r + 1)
        if y1 <= y0 or x1 <= x0:
            continue
        sub = d[y0 - (y - r):y1 - (y - r), x0 - (x - r):x1 - (x - r)]
        img[y0:y1, x0:x1][sub] = rgb
    return img


def bipartite_panel(pa, pb, pairs, weights, size=300, pad=24):
    """点 A(赤)・点 B(青)と、管(白、太さ = 重み)を 1 枚に。"""
    img = np.full((size, size, 3), 0.08)
    sc = size - 2 * pad
    A = pa * sc + pad
    B = pb * sc + pad
    w = np.asarray(weights, float)
    w = w / max(w.max(), 1e-12)
    lines = raster_lines(size, size, A[pairs[:, 0]], B[pairs[:, 1]], w)
    lines = np.clip(lines, 0, 1)
    img = img * (1 - lines[..., None]) + lines[..., None] * np.array([0.95, 0.95, 0.85])
    stamp(img, A, 5, (0.95, 0.25, 0.2))
    stamp(img, B, 5, (0.25, 0.55, 1.0))
    return img


def tubes_frame(D, a, b, scale=8):
    """導電度の画像(白)の上に源(赤)と吸込(青)を薄く重ねる。"""
    H, W = D.shape
    t = np.sqrt(D / max(D.max(), 1e-12))
    f = np.full((H, W, 3), 0.06)
    f += t[..., None] * np.array([0.9, 0.9, 0.8])
    f += 0.35 * (a / max(a.max(), 1e-12))[..., None] * np.array([1.0, 0.15, 0.1])
    f += 0.35 * (b / max(b.max(), 1e-12))[..., None] * np.array([0.1, 0.4, 1.0])
    f = np.clip(f, 0, 1)
    return np.repeat(np.repeat(f, scale, 0), scale, 1)


def main():
    t_all = time.perf_counter()
    truths = []                                                        # (名前, 真値, 粘菌の費用, 下界)

    # ---- 1. 木の閉形式 ------------------------------------------------------------------------------
    print("1. 木の閉形式(W1 = Σ L_e |部分木の供給|)")
    worst = 0.0
    for seed in range(5):
        A, parent = random_tree(30, seed)
        s = centered_supply(30, seed)
        r = PS.graph_physarum_transport(A, s, dt=0.3)
        w = tree_w1(A, parent, s)
        assert r["dual_bound"] <= w + 1e-9 and w <= r["cost"] + 1e-9 * w            # 6. 弱双対性
        assert abs(r["cost"] - w) <= 1e-6 * w                                        # 1.
        assert np.allclose(r["flow"].sum(1), s, atol=1e-9)                           # キルヒホッフ
        worst = max(worst, abs(r["cost"] - w) / w)
        truths.append(("木 seed %d" % seed, w, r["cost"], r["dual_bound"]))
        print("   seed %d: 粘菌 %.6f / 閉形式 %.6f / 下界 %.6f、%d 反復%s" % (
            seed, r["cost"], w, r["dual_bound"], r["iters"], "(D 収束)" if r["converged"] else "(隙間で停止)"))
    print("   最大相対誤差 %.1e" % worst)

    # ---- 2. 1 次元の閉形式 --------------------------------------------------------------------------
    rng = np.random.default_rng(3)
    x = np.sort(rng.uniform(0, 10, 40))
    A = np.zeros((40, 40))
    for k in range(39):
        A[k, k + 1] = A[k + 1, k] = x[k + 1] - x[k]
    a = rng.uniform(0, 1, 40); a /= a.sum()
    b = rng.uniform(0, 1, 40); b /= b.sum()
    r1 = PS.graph_physarum_transport(A, a - b, dt=0.3)
    w1 = wasserstein_1d(x, x, p=1, u_weights=a, v_weights=b)
    assert abs(r1["cost"] - w1) <= 1e-6 * w1 and r1["dual_bound"] <= w1 + 1e-9      # 2.
    truths.append(("1 次元", w1, r1["cost"], r1["dual_bound"]))
    print("2. 1 次元(不等間隔 40 点): 粘菌 %.6f = wasserstein_1d %.6f、%d 反復" % (r1["cost"], w1, r1["iters"]))

    # ---- 3. 割当問題 --------------------------------------------------------------------------------
    from scipy.optimize import linear_sum_assignment
    m = 12
    rng = np.random.default_rng(5)
    pa, pb = rng.uniform(0.05, 0.95, (m, 2)), rng.uniform(0.05, 0.95, (m, 2))
    C = np.sqrt(((pa[:, None, :] - pb[None, :, :]) ** 2).sum(-1))
    L = np.zeros((2 * m, 2 * m))
    L[:m, m:] = C
    L[m:, :m] = C.T
    s = np.concatenate([np.full(m, 1.0 / m), np.full(m, -1.0 / m)])
    r3 = PS.graph_physarum_transport(L, s, dt=0.3, max_iters=20000)
    ri, ci = linear_sum_assignment(C)
    w3 = C[ri, ci].sum() / m
    assert abs(r3["cost"] - w3) <= 1e-5 * w3 and r3["dual_bound"] <= w3 + 1e-9      # 3.
    Dm = r3["conductance"][:m, m:]
    on = Dm[ri, ci]
    off = Dm.copy(); off[ri, ci] = 0.0
    assert on.min() > 0.5 * Dm.max() and off.max() < 0.02 * Dm.max()                # 生き残った管 = 最適割当
    truths.append(("割当 12×12", w3, r3["cost"], r3["dual_bound"]))
    print("3. 割当(点 %d ↔ %d): 粘菌 %.6f = Hungarian %.6f、%d 反復。最適割当の管 ≥ %.2f、それ以外 ≤ %.3f(最大 = 1)"
          % (m, m, r3["cost"], w3, r3["iters"], on.min() / Dm.max(), off.max() / Dm.max()))
    # 途中の管(図用): 同じ式を 1 / 40 反復で止めて撮る
    iu, ju = np.nonzero(np.triu(L, 1))
    g = PS.Graph(n=2 * m, edges=np.column_stack([iu, ju]).astype(int), length=L[iu, ju], coords=np.zeros((2 * m, 2), int))
    shots3 = []
    Dcur, done = None, 0
    for k in (1, 40, r3["iters"]):
        rr = PS.solve_transport(g, s, dt=0.3, max_iters=k - done, tol=0.0, gap_tol=0.0, D_init=Dcur)
        Dcur, done = rr.D, k
        shots3.append((k, Dcur.copy()))

    # ---- 4. 小さな格子の LP -------------------------------------------------------------------------
    from scipy.optimize import linprog
    rng = np.random.default_rng(2)
    Ai, Bi = rng.uniform(0, 1, (6, 6)), rng.uniform(0, 1, (6, 6))
    r4 = PS.physarum_transport_image(Ai, Bi, dt=0.3)
    gg, _ = PS._grid_graph(6, 6, 4)
    E = len(gg.edges)
    M = np.zeros((36, E))
    M[gg.edges[:, 0], np.arange(E)] = 1.0
    M[gg.edges[:, 1], np.arange(E)] = -1.0
    sv = (Ai / Ai.sum() - Bi / Bi.sum()).ravel()
    lp = linprog(np.concatenate([gg.length, gg.length]), A_eq=np.hstack([M, -M]), b_eq=sv, bounds=(0, None), method="highs")
    assert lp.status == 0 and abs(r4["cost"] - lp.fun) <= 1e-4 * lp.fun and r4["dual_bound"] <= lp.fun + 1e-9   # 4.
    truths.append(("格子 6×6 LP", float(lp.fun), r4["cost"], r4["dual_bound"]))
    print("4. 格子 6×6 の乱数質量: 粘菌 %.6f = LP(HiGHS)%.6f、%d 反復、隙間 %.1e" % (r4["cost"], lp.fun, r4["iters"], r4["gap"]))

    # ---- 5. 平行移動の定理 ---------------------------------------------------------------------------
    H = W = 24
    shape = disk(H, W, 7, 6, 3.2)
    dr, dc = 5, 8
    moved = np.roll(np.roll(shape, dr, 0), dc, 1)
    r5 = PS.physarum_transport_image(shape, moved, dt=0.3)
    assert abs(r5["cost"] - (dr + dc)) <= 1e-5 * (dr + dc) and r5["dual_bound"] <= dr + dc + 1e-9   # 5.
    truths.append(("平行移動 (5, 8)", float(dr + dc), r5["cost"], r5["dual_bound"]))
    print("5. 円盤を (%d, %d) 画素ずらす: EMD %.6f = |dr| + |dc| = %d、%d 反復(最短路が多数あるので D は揺れ、隙間 %.1e で停止)"
          % (dr, dc, r5["cost"], dr + dc, r5["iters"], r5["gap"]))

    # ---- 6. 単一対 = 最短路、下界 = Dijkstra --------------------------------------------------------
    from scipy.sparse.csgraph import dijkstra
    A7 = lattice(7, 0)
    s7 = np.zeros(49); s7[0] = 1.0; s7[48] = -1.0
    r6 = PS.graph_physarum_transport(A7, s7, dt=0.3)
    d7 = dijkstra(A7, indices=0)[48]
    assert abs(r6["dual_bound"] - d7) <= 1e-9 and d7 <= r6["cost"] + 1e-12 and abs(r6["cost"] - d7) <= 1e-5 * d7   # 6.
    truths.append(("単一対 7×7", float(d7), r6["cost"], r6["dual_bound"]))
    print("6. 源 1・吸込 1(7×7 格子): 下界 %.9f = Dijkstra %.9f(圧力の McShane 包絡 = 最短路のポテンシャル)、費用 %.9f"
          % (r6["dual_bound"], d7, r6["cost"]))

    # ---- 7. 距離の公理(画像) -------------------------------------------------------------------------
    a1 = disk(H, W, 6, 6, 3.0)
    a2 = disk(H, W, 17, 7, 2.5) + disk(H, W, 7, 17, 2.5)
    a3 = disk(H, W, 12, 12, 5.0) - disk(H, W, 12, 12, 2.5)
    c12 = PS.physarum_transport_image(a1, a2, dt=0.3)["cost"]
    c21 = PS.physarum_transport_image(a2, a1, dt=0.3)["cost"]
    c23 = PS.physarum_transport_image(a2, a3, dt=0.3)["cost"]
    c13 = PS.physarum_transport_image(a1, a3, dt=0.3)["cost"]
    assert abs(c12 - c21) <= 1e-5 * c12                                              # 対称
    assert c13 <= c12 + c23 + 1e-6                                                    # 三角不等式
    r_scaled = PS.graph_physarum_transport(2.0 * A, 3.0 * (a - b), dt=0.3)
    assert abs(r_scaled["cost"] - 6.0 * w1) <= 1e-6 * 6.0 * w1                       # 長さと質量に線形
    print("7. 距離の公理: 円盤→2 円盤 %.4f = 逆向き %.4f、円盤→輪 %.4f ≤ %.4f + %.4f、長さ 2 倍・質量 3 倍で費用 6 倍(%.6f)"
          % (c12, c21, c13, c12, c23, r_scaled["cost"] / w1))

    # ---- 8. 動く図: 円盤 → 2 つの円盤 ----------------------------------------------------------------
    n_shots = 36
    r8 = PS.physarum_transport_image(a1, a2, dt=0.3, snapshots=n_shots)
    print("8. 円盤 → 2 円盤(%d×%d、4 近傍): EMD %.4f、下界 %.4f、%d 反復、途中経過 %d 枚" % (
        H, W, r8["cost"], r8["dual_bound"], r8["iters"], len(r8["snapshots"])))
    t_total = time.perf_counter() - t_all

    if figs.enabled():
        frames = [tubes_frame(Dk, a1, a2) for Dk in r8["snapshots"]]
        frames = [frames[0]] * 4 + frames + [frames[-1]] * 8
        figs.save_gif("transport_tubes_gif", frames, fps=8,
                      caption="円盤(赤)の質量を 2 つの円盤(青)へ運ぶ管が張られていく(明るさ = 導電度の平方根)。"
                              "%d×%d 画素、4 近傍、%d 反復、%d コマ。最後に残る管の束が最適輸送の流れ。"
                              % (H, W, r8["iters"], len(frames)))
        pick = [0, len(r8["snapshots"]) // 6, len(r8["snapshots"]) // 3, len(r8["snapshots"]) - 1]
        figs.save_grid("transport_tubes", [tubes_frame(r8["snapshots"][k], a1, a2, 6) for k in pick],
                       ["%d 反復" % r8["snapshot_iters"][k] for k in pick], ncols=4,
                       title="円盤 → 2 円盤: 管は最初は一様に張られ、使われる道だけが太って残る",
                       caption="EMD %.4f(画素単位)。粘菌の費用 %.4f、Kantorovich–Rubinstein の下界 %.4f。" % (
                           r8["cost"], r8["cost"], r8["dual_bound"]))
        pairs = np.column_stack([iu, ju - m])
        panels = [bipartite_panel(pa, pb, pairs, D[np.arange(len(D))]) for _, D in shots3]
        hung = np.zeros(len(iu)); hung[np.ravel_multi_index((ri, ci), (m, m))] = 1.0
        panels.append(bipartite_panel(pa, pb, pairs, hung))
        figs.save_grid("assignment_tubes", panels,
                       ["%d 反復(全 %d 本の管)" % (shots3[0][0], len(iu)), "%d 反復" % shots3[1][0],
                        "%d 反復(収束)" % shots3[2][0], "Hungarian 法の最適割当"], ncols=2,
                       title="12 点 ↔ 12 点の割当: 太さ = 導電度。残った管は Hungarian 法の割当と一致する",
                       caption="完全 2 部グラフ 144 本、ユークリッド長。粘菌の費用 %.6f = 最小割当 %.6f。" % (r3["cost"], w3))
        it_c = np.arange(1, len(r8["cost_history"]) + 1)
        dh = r8["dual_history"]
        figs.save_plot("sandwich", [("費用 Σ L|Q|(上界)", it_c, r8["cost_history"]),
                                    ("Kantorovich–Rubinstein の下界", dh[:, 0], dh[:, 1])],
                       xlabel="反復", ylabel="費用(画素単位)", title="真値は必ず 2 本の間に在る: 上界と下界が閉じたら止める",
                       caption="円盤 → 2 円盤。下界は 10 反復ごとに圧力の McShane 包絡から。隙間 %.1e で停止(相対 1e-6 以下)。"
                               % r8["gap"], kinds=["line", "scatter"],
                       ylim=(float(min(dh[:, 1].min(), r8["cost_history"].min())) * 0.9, float(r8["cost_history"][:20].max()) * 1.05))
        names = [t[0] for t in truths]
        tv = np.array([t[1] for t in truths]); cv = np.array([t[2] for t in truths]); dv = np.array([t[3] for t in truths])
        figs.save_plot("five_truths", [("粘菌の費用", tv, cv), ("下界", tv, dv), ("y = x", tv, tv)],
                       xlabel="真値(閉形式 / Hungarian / LP / Dijkstra)", ylabel="粘菌", kinds=["scatter", "scatter", "line"],
                       title="%d 件の真値と粘菌の費用・下界(点は y = x の上に乗る)" % len(truths),
                       caption="; ".join("%s %.4g" % (n, v) for n, v in zip(names, tv)))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS: 真値 %d 件(木 5・1 次元・割当・LP・平行移動・単一対)すべてと一致、弱双対性は全反復で成立、距離の公理 3 つ。"
          "合計 %.1f 秒。" % (len(truths), t_total))


if __name__ == "__main__":
    main()
