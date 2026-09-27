# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""粘菌の管は迷路を解く —— 太る・細るだけの力学が最短路に収束することを、定理と Dijkstra で挟む。

    py -3.11 examples/poc_physarum_maze.py

粘菌 *Physarum polycephalum* は、管を流れる流量で管を太らせ・細らせるだけで迷路の最短路を残す
(Tero ら 2010, *Science* 327:439)。その力学 —— 管の導電度 D、キルヒホッフで圧力を解き、流量
Q = D (p_u − p_v) / L、dD/dt = |Q| − D —— は、最短路が一意なら導電度がその指示関数(最短路の管は 1、
それ以外は 0)に収束することが証明されている(Bonifaci・Mehlhorn・Varma 2012)。

Fullseye の op 2 本で回す:

* ``graph_physarum_path`` —— 重み付きグラフ(辺の長さの行列)の上で。
* ``physarum_route`` —— コスト画像の上で(隣の画素を長さ (c_u + c_v)/2 の管で結ぶ)。

この PoC が測る唯一の主張:

    **管の力学は、答えを知らずに最短路へ来る。** 15×15 の格子(辺長は乱数)5 通り、迷路 1 つ、
    なだらかな地形 1 つ —— どれも粘菌の道は Dijkstra / route_through_array の最小コスト経路と
    厳密に一致する(道の長さの差 < 1e-9)。

検査する恒等式(下の assert、当てはめた数字は無い):

1. 道の一致: 粘菌の道の長さ = Dijkstra(scipy.sparse.csgraph)の最短距離、画像では
   経路コスト = ``skimage.graph.route_through_array``(第 2 実装)。
2. 流れの長さの不等式: 単位流量の長さ Σ|Q_e| L_e は最短路以上(厳密)で、収束で等号へ。
3. 指示関数への収束(Bonifaci): 収束した seed では最短路の管の導電度 > 0.99、それ以外 < 0.01。
   打ち切りになった seed は「2 番目に短い道との差」が収束した seed のどれよりも小さい(収束の速さは
   その差で決まる。2 位は、最短路の辺を 1 本ずつ外した Dijkstra の最小 = 厳密)。
4. Lyapunov 関数 V = Σ L_e D_e(Bonifaci の「設備費」)は連続時間で単調非増加で、最短路の長さ以上
   (等号は指示関数)。ここでは Euler の刻み dt で回すので、途中経過の区間で増えた回数を数えて
   報告し、最後の V ≥ 最短路 だけを門にする。
5. 迷路の道は壁を 1 画素も通らない。

15×15 の格子は afterman の粘菌 PoC(2026-08-30、厳密版 5 seed 中 4 が 600 反復以内)と同じ作り
(辺長 U(0.5, 1.5)、左上 → 右下、dt 0.3)で、反復数を並べて報告する。
先行研究: Tero 2010 の再実装は GitHub に複数ある(robert-30/physarum-maze 等)が、Dijkstra との一致を
門にした物・コスト画像の上で route_through_array を真値にした物は見つからなかった。Jones 2010 の
「Physarum machine」(粒子の走化性)は別の模型で、ここでは扱わない。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import examplefig as figs  # noqa: E402
import physarum_search as PS  # noqa: E402


def lattice(n: int, seed: int) -> np.ndarray:
    """n×n 格子、辺長 U(0.5, 1.5)(最短路はほぼ確実に一意)。"""
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


def perfect_maze(cells: int, seed: int) -> np.ndarray:
    """深さ優先の掘り進みで作る迷路(通路 True)。完全迷路なので任意の 2 点間の道は 1 本。"""
    rng = np.random.default_rng(seed)
    H = W = 2 * cells + 1
    free = np.zeros((H, W), bool)
    stack = [(1, 1)]
    free[1, 1] = True
    while stack:
        r, c = stack[-1]
        nbrs = [(r + dr, c + dc) for dr, dc in ((2, 0), (-2, 0), (0, 2), (0, -2))
                if 0 < r + dr < H and 0 < c + dc < W and not free[r + dr, c + dc]]
        if not nbrs:
            stack.pop()
            continue
        nr, nc = nbrs[rng.integers(len(nbrs))]
        free[(r + nr) // 2, (c + nc) // 2] = True
        free[nr, nc] = True
        stack.append((nr, nc))
    return free


def terrain(n: int, seed: int) -> np.ndarray:
    """なだらかな地形(余弦の和)。谷が安く、丘が高い。"""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] / n
    z = np.zeros((n, n))
    for _ in range(6):
        kx, ky = rng.uniform(1, 4, 2)
        z += rng.uniform(0.5, 1) * np.cos(2 * np.pi * (kx * x + ky * y) + rng.uniform(0, 2 * np.pi))
    z = (z - z.min()) / (z.max() - z.min())
    return 0.2 + 2.0 * z ** 2 + 0.01 * rng.uniform(0, 1, (n, n))


def _without(A: np.ndarray, u: int, v: int) -> np.ndarray:
    B = A.copy()
    B[u, v] = B[v, u] = 0.0
    return B


def draw_tubes(cond: np.ndarray, n: int, cell: int = 22, width: int = 9) -> np.ndarray:
    """格子の管を、導電度に比例した太さの線で描く(0 = 描かない)。"""
    img = np.zeros((n * cell + 1, n * cell + 1))
    iu, ju = np.nonzero(np.triu(cond, 1))
    for u, v in zip(iu, ju):
        w = max(1, int(round(width * min(cond[u, v], 1.0))))
        r0, c0 = divmod(int(u), n)
        r1, c1 = divmod(int(v), n)
        y0, x0 = r0 * cell + cell // 2, c0 * cell + cell // 2
        y1, x1 = r1 * cell + cell // 2, c1 * cell + cell // 2
        h = w // 2
        img[min(y0, y1) - h:max(y0, y1) + h + 1, min(x0, x1) - h:max(x0, x1) + h + 1] = np.maximum(
            img[min(y0, y1) - h:max(y0, y1) + h + 1, min(x0, x1) - h:max(x0, x1) + h + 1], 0.25 + 0.75 * min(cond[u, v], 1.0))
    return img


def draw_path(img: np.ndarray, path: np.ndarray, value: float) -> np.ndarray:
    out = img.copy()
    out[tuple(path.T)] = value
    return out


def main() -> None:
    from scipy.sparse.csgraph import dijkstra
    from skimage.graph import route_through_array

    # ---- 1. 15×15 の格子 5 通り(afterman の PH と同じ作り)----------------------------------
    print("15×15 の格子(辺長 U(0.5, 1.5)、左上 → 右下、dt 0.3):")
    rows, tubes = [], {}
    for seed in range(5):
        A = lattice(15, seed)
        d = float(dijkstra(A, indices=0)[224])
        # afterman の PH と同じ基準(600 反復の時点で、流れを辿った道が最短路と一致するか)。
        # frac を 0 に近づけて「まだ拮抗している」拒否を外し、道の読み取りだけを見る。
        early = PS.graph_physarum_path(A, 0, 224, dt=0.3, max_iters=600, tol=0.0, frac=1e-12)
        hit600 = abs(early["path_length"] - d) < 1e-9
        tubes[seed] = (early["conductance"], None)
        r = PS.graph_physarum_path(A, 0, 224, dt=0.3, max_iters=3000)
        tubes[seed] = (tubes[seed][0], r["conductance"])
        assert abs(r["path_length"] - d) < 1e-9, (seed, r["path_length"], d)           # 恒等式 1
        assert r["flow_length"] >= d - 1e-12                                            # 恒等式 2(厳密)
        on = r["conductance"][r["path"][:-1], r["path"][1:]]
        off = r["conductance"].copy()
        off[r["path"][:-1], r["path"][1:]] = 0
        off[r["path"][1:], r["path"][:-1]] = 0
        # 2 番目に短い道: 最短路の辺を 1 本ずつ外して Dijkstra を引き直した最小(最短路と違う道は
        # 必ずその辺のどれかを欠くので、これは厳密に「最短路以外で最短」)。収束の速さを決めるのはこの差。
        second = min(float(dijkstra(_without(A, u, v), indices=0)[224]) for u, v in zip(r["path"][:-1], r["path"][1:]))
        rows.append((seed, r["iters"], r["converged"], d, r["flow_length"] - d, on.min(), off.max(), second - d, hit600))
        print("   seed %d: %4d 反復%s  最短 %.4f(2 位との差 %.4f)  流れの長さ − 最短 %.1e  最短路の管の最小 D %.4f  その他の最大 D %.1e"
              % (seed, r["iters"], "(収束)" if r["converged"] else "(打ち切り)", d, second - d, r["flow_length"] - d, on.min(), off.max()))
    conv = [x for x in rows if x[2]]
    cut = [x for x in rows if not x[2]]
    assert conv and all(x[5] > 0.99 and x[6] < 1e-2 for x in conv)                     # 恒等式 3(収束した seed)
    if cut:
        # 打ち切りの seed は、2 位との差が収束した seed のどれよりも小さい(速さは差で決まる)
        assert max(x[7] for x in cut) < min(x[7] for x in conv), (cut, conv)
    within600 = sum(1 for x in rows if x[8])
    print("   5 / 5 で道は Dijkstra と一致。%d / 5 が収束(最短路の管 > 0.99、他 < 0.01)、打ち切り %d は 2 位との差が小さい順。"
          "600 反復の時点で道が一致 %d / 5(afterman の厳密版は 4 / 5)" % (len(conv), len(cut), within600))

    # ---- 2. 迷路(完全迷路 = 道は 1 本、壁のコスト 1000)------------------------------------
    free = perfect_maze(10, 3)
    rng = np.random.default_rng(0)
    cost = np.where(free, rng.uniform(0.9, 1.1, free.shape), 1000.0)
    H, W = cost.shape
    start, end = (1, 1), (H - 2, W - 2)
    m = PS.physarum_route(cost, start, end, snapshots=24, dt=0.2, max_iters=4000)
    p_true, c_true = route_through_array(cost, start, end, fully_connected=False, geometric=False)
    assert abs(m["path_cost"] - c_true) < 1e-9 and m["path"].tolist() == [list(p) for p in p_true]   # 恒等式 1
    assert free[tuple(m["path"].T)].all()                                                            # 恒等式 5
    assert m["flow_length"] >= m["route_length"] - 1e-12
    print("迷路 %d×%d: 粘菌の道 %d 画素、コスト %.3f = route_through_array %.3f、壁を通った画素 0、%d 反復%s"
          % (H, W, len(m["path"]), m["path_cost"], c_true, m["iters"], "(収束)" if m["converged"] else "(打ち切り)"))
    # Lyapunov V = Σ L D(Bonifaci)の単調性を、Euler の刻み dt 0.2 で途中経過ごとに数える
    shots = m["snapshots"]
    V = m["snapshot_cost"]
    ups = int((np.diff(V) > 1e-9 * V[0]).sum())
    print("   V = Σ L·D は %.1f → %.3f(最短路の長さ %.3f)、%d 区間のうち増えた区間 %d" % (V[0], V[-1], m["route_length"], len(V) - 1, ups))
    assert V[-1] >= m["route_length"] - 1e-9                                                     # V ≥ 最短(等号は指示関数)

    # ---- 3. なだらかな地形 ----------------------------------------------------------------------
    z = terrain(32, 1)
    t = PS.physarum_route(z, (2, 2), (29, 29), dt=0.2, max_iters=2500)
    p2, c2 = route_through_array(z, (2, 2), (29, 29), fully_connected=False, geometric=False)
    assert abs(t["path_cost"] - c2) < 1e-9 and t["path"].tolist() == [list(p) for p in p2]           # 恒等式 1
    print("地形 32×32: 粘菌の道 %d 画素、コスト %.3f = route_through_array %.3f、%d 反復%s"
          % (len(t["path"]), t["path_cost"], c2, t["iters"], "(収束)" if t["converged"] else "(打ち切り)"))

    if figs.enabled():
        pick = [0, 2, 5, 9, 15, 23]
        panels = [np.where(free, shots[k], 0.0) for k in pick]
        caps = ["%d 反復" % m["snapshot_iters"][k] for k in pick]
        figs.save_grid("maze_tubes", panels, caps, ncols=3,
                       title="管が太る過程: 行き止まりの管が細り、最短路だけ 1 に残る(明るさ = 導電度)",
                       caption="%d×%d の完全迷路(左上 → 右下)。dt %.1f、%d 反復で収束。" % (H, W, 0.2, m["iters"]))
        frames = []
        for s in shots:
            f = np.stack([np.where(free, s, 0.0)] * 3, -1)
            f[~free] = (0.25, 0.25, 0.3)
            frames.append(np.clip(f, 0, 1))
        figs.save_gif("maze_tubes_gif", [np.repeat(np.repeat(f, 12, 0), 12, 1) for f in frames], fps=6,
                      caption="同じ迷路、%d コマ。行き止まりから順に細り、最後に最短路だけが残る。" % len(frames))
        zt = (z - z.min()) / (z.max() - z.min())
        figs.save_grid("terrain_route",
                       [zt, draw_path(zt, t["path"], 1.0), t["conductance"], draw_path(np.zeros_like(zt), np.array(p2), 1.0)],
                       ["コスト(暗 = 安い)", "粘菌の道(白)", "収束した導電度", "route_through_array の道(白)"], ncols=2,
                       title="なだらかな地形: 谷を選ぶ道は、Dijkstra 型の最小コスト経路と 1 画素も違わない",
                       caption="32×32。経路コスト %.3f、%d 反復。" % (t["path_cost"], t["iters"]))
        # 格子の管を太さで描く: 収束の速い seed と、2 位との差が小さくて 2 本が拮抗したままの seed
        fast = max(conv, key=lambda x: x[7])[0]
        slow = min(rows, key=lambda x: x[7])[0]
        panels = [draw_tubes(tubes[fast][0], 15), draw_tubes(tubes[fast][1], 15),
                  draw_tubes(tubes[slow][0], 15), draw_tubes(tubes[slow][1], 15)]
        gap = {x[0]: x[7] for x in rows}
        it = {x[0]: x[1] for x in rows}
        figs.save_grid("lattice_tubes", panels,
                       ["seed %d、600 反復(2 位との差 %.3f)" % (fast, gap[fast]), "seed %d、%d 反復" % (fast, it[fast]),
                        "seed %d、600 反復(2 位との差 %.3f)" % (slow, gap[slow]), "seed %d、%d 反復" % (slow, it[slow])],
                       ncols=2, gray=True,
                       title="管の太さ = 導電度。2 位との差が小さいと、2 本の道が長く拮抗する",
                       caption="15×15 の格子、辺長 U(0.5, 1.5)、左上 → 右下。上: 差 %.3f の seed は %d 反復で 1 本に収束。"
                               "下: 差 %.3f の seed は 3000 反復でも 2 本目が残る(道の読み取りは流れを辿るので最短路に一致)。"
                               % (gap[fast], it[fast], gap[slow]))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS: 格子 5 / 5・迷路・地形のすべてで粘菌の道が最小コスト経路と一致(差 < 1e-9)。600 反復の時点で一致 %d / 5、"
          "迷路 %d 反復、地形 %d 反復。" % (within600, m["iters"], t["iters"]))


if __name__ == "__main__":
    main()
