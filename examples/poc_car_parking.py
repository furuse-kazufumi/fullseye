# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""車は最短でどう曲がるか —— Dubins・Reeds–Shepp の閉形式と、占有格子の上の Hybrid A* で縦列駐車。

    py -3.11 examples/poc_car_parking.py

前輪で舵を切る車(最小回転半径 ρ)が姿勢 (x, y, θ) から姿勢 (x', y', θ') へ移る最短の道には定理がある。
前進だけなら Dubins(1957): 最短路は「円弧・直線・円弧」の 3 区間で語は 6 つ(LSL RSR LSR RSL RLR LRL)。
後退を許せば Reeds–Shepp(1990): 高々 5 区間で語は 48(Sussmann–Tang 1991 で 46)。どちらも区間長は閉形式で、
Fullseye の op ``car_dubins_path`` / ``car_reeds_shepp_path`` がそれを返す。障害物があれば Hybrid A*
(Dolgov・Thrun・Montemerlo・Diebel 2010)—— 占有格子の上で、{左・直進・右} × {前進・後退} の運動基本形を
A* で繋ぎ、障害物を無視した Reeds–Shepp 長をヒューリスティックに、節点から目標へ Reeds–Shepp の
「解析的な一撃」を試す —— が ``car_hybrid_astar``。

この PoC が測る主張:
    **閉形式は最小で、探索は閉形式を下回らない。** どの真値とも一致する。
検査する恒等式・不等式(下の assert、当てはめた数字は無い):
1. 閉形式の全候補は前進積分で目標に着く(n_rejected = 0)。Reeds–Shepp の 18 の語族が候補にも最短にも現れる。
2. 第 2 実装: 語ごとの区間長を未知数にした終点方程式を SLSQP で多数の初期値から解く(閉形式の構造を仮定しない)。
   その最小は閉形式を下回らず、閉形式に届く。
3. 定理の不等式と対称: ユークリッド距離 ≤ RS ≤ Dubins、可逆 L(s, g) = L(g, s)、鏡映、剛体変換で不変、ρ に比例、
   三角不等式。
4. 整列した目標では RS = Dubins = 距離、語は S。真後ろでは RS は後退 1 本。
5. Hybrid A*: 障害物の無い駐車場では費用 = Reeds–Shepp 長と厳密一致(最初の一撃が通る)。前進のみなら Dubins 長。
6. 縦列駐車(2 台の間の車室): 費用 ≥ RS 下界、返す姿勢列は車体の矩形で衝突せず、|Δθ| ≤ Δs/ρ、始点と終点が一致。
7. fail-closed: 壁で塞ぐと ValueError(部分的な道を返さない)。

先行研究: Dubins・Reeds–Shepp・Hybrid A* はどれも教科書の範囲で、OMPL / PythonRobotics に実装がある。
この PoC の持ち分は「候補を積分で検証して落とした数を返す」「最適化器の第 2 実装で最小性を測る」「Hybrid A* の
答えを閉形式で挟む」の 3 つを numpy だけで門にしたこと。RS の式を写すときに mod2pi の折り方((−π, π] か
[0, 2π) か)を間違えると CCSC 系 8 語が一度も候補に出ない —— 語族を数える門で見つけた。
教則の場面: S112(docs/drive/kyosoku_scenarios.json、交通の方法に関する教則の再現台帳)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import examplefig as figs  # noqa: E402
import carpath as CP  # noqa: E402

RS_TYPES = ("LRL", "RLR", "LRLR", "RLRL", "LRSL", "RLSR", "LSRL", "RSLR", "LRSR", "RLSL",
            "RSRL", "LSLR", "LSR", "RSL", "LSL", "RSR", "LRSLR", "RLSRL")
DUBINS_TYPES = ("LSL", "RSR", "LSR", "RSL", "RLR", "LRL")


# ---- 第 2 実装(最適化器)-------------------------------------------------------------------------
def oracle(start, goal, rho, types, forward_only, n_starts=12, seed=0):
    """語 word の区間長 l を未知数に min Σ|l| s.t. 終点 = goal を SLSQP で解く(閉形式の構造を仮定しない)。"""
    from scipy.optimize import minimize
    x, y, phi = CP._relative(start, goal, rho)
    rng = np.random.default_rng(seed)
    d = math.hypot(x, y)
    best = math.inf
    for word in types:
        lo = [0.0 if forward_only else -(2 * math.pi if k != "S" else d + 4.0) for k in word]
        hi = [(2 * math.pi if k != "S" else d + 4.0) for k in word]

        def endpoint(l, word=word):
            ex, ey, eth = CP._integrate(word, l, (0.0, 0.0, 0.0), 1.0)
            return np.array([ex - x, ey - y, 2.0 * math.sin(0.5 * (eth - phi))])

        for _ in range(n_starts):
            r = minimize(lambda l: float(np.sum(np.sqrt(l * l + 1e-12))), rng.uniform(lo, hi), method="SLSQP",
                         bounds=list(zip(lo, hi)), constraints=[{"type": "eq", "fun": endpoint}],
                         options={"maxiter": 200, "ftol": 1e-12})
            if np.max(np.abs(endpoint(r.x))) < 1e-6:
                best = min(best, float(np.sum(np.abs(r.x))))
    return best * rho


# ---- 描画(numpy だけ)----------------------------------------------------------------------------
class Canvas:
    """世界座標(m)→ 画素。y は上向き。"""

    def __init__(self, xmax, ymax, px_per_m=24, bg=1.0):
        self.s = px_per_m
        self.W, self.H = int(round(xmax * px_per_m)), int(round(ymax * px_per_m))
        self.img = np.full((self.H, self.W, 3), bg, np.float32)

    def _pix(self, x, y):
        return (self.H - 1 - y * self.s), x * self.s

    def line(self, p0, p1, color, width=1):
        r0, c0 = self._pix(*p0)
        r1, c1 = self._pix(*p1)
        n = int(max(abs(r1 - r0), abs(c1 - c0))) + 2
        rr = np.round(np.linspace(r0, r1, n)).astype(int)
        cc = np.round(np.linspace(c0, c1, n)).astype(int)
        for dr in range(-(width // 2), width - width // 2):
            for dc in range(-(width // 2), width - width // 2):
                r, c = rr + dr, cc + dc
                ok = (r >= 0) & (r < self.H) & (c >= 0) & (c < self.W)
                self.img[r[ok], c[ok]] = color

    def polyline(self, pts, color, width=1):
        for a, b in zip(pts[:-1], pts[1:]):
            self.line(a[:2], b[:2], color, width)

    def rect_fill(self, x0, y0, x1, y1, color):
        r1, c0 = self._pix(x0, y0)
        r0, c1 = self._pix(x1, y1)
        r0, r1 = max(0, int(round(r0))), min(self.H, int(round(r1)) + 1)
        c0, c1 = max(0, int(round(c0))), min(self.W, int(round(c1)) + 1)
        self.img[r0:r1, c0:c1] = color

    def car(self, pose, footprint, color, width=2):
        L, Wd, back = footprint
        x, y, th = pose
        c, s = math.cos(th), math.sin(th)
        corners = [(-back, -Wd / 2), (L - back, -Wd / 2), (L - back, Wd / 2), (-back, Wd / 2)]
        pts = [(x + u * c - v * s, y + u * s + v * c) for u, v in corners]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            self.line(a, b, color, width)
        # 前を示す線
        fx, fy = x + (L - back) * c, y + (L - back) * s
        self.line((x, y), (fx, fy), color, 1)

    def arrow(self, pose, length, color, width=2):
        x, y, th = pose
        self.line((x, y), (x + length * math.cos(th), y + length * math.sin(th)), color, width)
        self.line((x, y), (x + 0.25 * length * math.cos(th + 2.6), y + 0.25 * length * math.sin(th + 2.6)), color, width)
        self.line((x, y), (x + 0.25 * length * math.cos(th - 2.6), y + 0.25 * length * math.sin(th - 2.6)), color, width)

    def occupancy(self, occ, cell, color=(0.2, 0.2, 0.2)):
        rows, cols = np.nonzero(occ)
        for r, c in zip(rows, cols):
            self.rect_fill(c * cell, r * cell, (c + 1) * cell, (r + 1) * cell, color)


def gear_colors(points, segments, rho):
    """区間ごとの前進/後退で色を分けた折れ線の列 [(pts, color)]。"""
    out, i = [], 0
    for kind, gear, length in segments:
        n = max(1, int(math.ceil(length / 0.05 - 1e-9))) if kind else 1
        seg = points[i:i + n + 1]
        out.append((seg, (0.85, 0.15, 0.15) if gear > 0 else (0.1, 0.35, 0.9)))
        i += n
    return out


def draw_path(cv, res, width=2):
    """前進 = 赤、後退 = 青。points は step 刻み(car_* op は 0.05 m)。"""
    P = res["points"]
    if "segments" in res and all(len(s) == 3 for s in res["segments"]):
        # 各区間の点数は長さ / step から復元できる(op は区間ごとに ceil(len/step) 点)
        i = 0
        for kind, gear, length in res["segments"]:
            n = max(1, int(math.ceil(length / 0.05 - 1e-9)))
            cv.polyline(P[i:i + n + 1], (0.85, 0.15, 0.15) if gear > 0 else (0.1, 0.35, 0.9), width)
            i += n
    else:
        cv.polyline(P, (0.85, 0.15, 0.15), width)


def parking_lot():
    """18 m × 8 m、cell 0.25 m。下に縁石、駐車車両 2 台(4.5 × 1.8 m)の間に 7.5 m の車室(x 5.0〜12.5)。
    6.5 m の車室(車長 + 2.0 m)は ρ 4.5 m・cell 0.25 m・θ 48 分割では到達不能になる(正直に: この離散化の限界)。"""
    cell = 0.25
    occ = np.zeros((int(8 / cell), int(18 / cell)), bool)
    occ[0:2, :] = True                       # 縁石 (y < 0.5)
    for x0 in (0.5, 12.5):                   # 駐車車両
        c0, c1 = int(x0 / cell), int((x0 + 4.5) / cell)
        occ[2:int((0.5 + 1.8) / cell), c0:c1] = True
    occ[-1, :] = True                        # 上の壁
    return occ, cell


def main():
    t_total = time.time()
    rng = np.random.default_rng(0)
    truths = []

    # ---- 1. 候補は全部着く・語族は全部出る --------------------------------------------------------
    print("1. 閉形式の候補は前進積分で全部目標に着くか、Reeds–Shepp の 18 語族が全部現れるか(400 対)")
    fam_c, fam_b, n_rej, n_cand = set(), set(), 0, []
    pairs = []
    for _ in range(400):
        s = (rng.uniform(-6, 6), rng.uniform(-6, 6), rng.uniform(-math.pi, math.pi))
        g = (rng.uniform(-6, 6), rng.uniform(-6, 6), rng.uniform(-math.pi, math.pi))
        rho = rng.uniform(0.5, 2.0)
        d = CP.car_dubins_path([s, g], radius=rho)
        r = CP.car_reeds_shepp_path([s, g], radius=rho)
        n_rej += d["n_rejected"] + r["n_rejected"]
        n_cand.append(r["n_candidates"])
        fam_c.update(w.upper() for w, _ in r["candidates"])
        fam_b.add(r["word"].upper())
        pairs.append((s, g, rho, d["length"], r["length"]))
    assert n_rej == 0, n_rej
    assert fam_c == set(RS_TYPES) and fam_b == set(RS_TYPES), (sorted(set(RS_TYPES) - fam_c), sorted(set(RS_TYPES) - fam_b))
    print("   落ちた候補 0 / 対あたりの RS 候補 %.1f 本(%d〜%d)/ 語族 18 が候補にも最短にも出た" % (np.mean(n_cand), min(n_cand), max(n_cand)))

    # ---- 2. 第 2 実装 -----------------------------------------------------------------------------
    print("2. 第 2 実装(語ごとの区間長を SLSQP で解く、閉形式の構造は仮定しない)")
    t = time.time()
    orc = []
    for k in range(3):
        s, g, rho, dl, rl = pairs[k]
        o_rs = oracle(s, g, rho, RS_TYPES, False, seed=k)
        o_du = oracle(s, g, rho, DUBINS_TYPES, True, seed=k)
        assert o_rs >= rl - 1e-6 and o_du >= dl - 1e-6, (o_rs, rl, o_du, dl)
        assert abs(o_rs - rl) <= 1e-4 * (1 + rl) and abs(o_du - dl) <= 1e-4 * (1 + dl), (o_rs, rl, o_du, dl)
        orc.append((rl, o_rs, dl, o_du))
        truths += [("RS 最適化器 %d" % (k + 1), o_rs, rl), ("Dubins 最適化器 %d" % (k + 1), o_du, dl)]
        print("   対 %d: RS 閉形式 %.6f / 最適化器 %.6f、Dubins 閉形式 %.6f / 最適化器 %.6f" % (k + 1, rl, o_rs, dl, o_du))
    print("   %.1f 秒" % (time.time() - t))

    # ---- 3. 不等式と対称 ----------------------------------------------------------------------------
    print("3. 距離 ≤ RS ≤ Dubins、可逆、鏡映、剛体変換、ρ に比例、三角不等式(400 対 + 200 組)")
    worst_gap = 0.0
    for s, g, rho, dl, rl in pairs:
        eu = math.hypot(g[0] - s[0], g[1] - s[1])
        assert eu - 1e-9 <= rl <= dl + 1e-9
        worst_gap = max(worst_gap, dl - rl)
        assert abs(CP.car_reeds_shepp_path([g, s], radius=rho)["length"] - rl) <= 1e-9 * (1 + rl)
        d2 = CP.car_dubins_path([(g[0], g[1], g[2] + math.pi), (s[0], s[1], s[2] + math.pi)], radius=rho)["length"]
        assert abs(d2 - dl) <= 1e-9 * (1 + dl)
        m = CP.car_reeds_shepp_path([(s[0], -s[1], -s[2]), (g[0], -g[1], -g[2])], radius=rho)["length"]
        assert abs(m - rl) <= 1e-9 * (1 + rl)
        a, tx, ty = rng.uniform(-math.pi, math.pi), rng.uniform(-5, 5), rng.uniform(-5, 5)
        ca, sa = math.cos(a), math.sin(a)
        T = lambda p: (ca * p[0] - sa * p[1] + tx, sa * p[0] + ca * p[1] + ty, p[2] + a)  # noqa: E731
        assert abs(CP.car_reeds_shepp_path([T(s), T(g)], radius=rho)["length"] - rl) <= 1e-9 * (1 + rl)
        k = rng.uniform(0.3, 3.0)
        assert abs(CP.car_reeds_shepp_path([(k * s[0], k * s[1], s[2]), (k * g[0], k * g[1], g[2])], radius=k * rho)["length"] - k * rl) <= 1e-9 * (1 + k * rl)
    for _ in range(200):
        a, b, c = [(rng.uniform(-4, 4), rng.uniform(-4, 4), rng.uniform(-math.pi, math.pi)) for _ in range(3)]
        for fn in (CP.car_reeds_shepp_path, CP.car_dubins_path):
            assert fn([a, c], radius=1.0)["length"] <= fn([a, b], radius=1.0)["length"] + fn([b, c], radius=1.0)["length"] + 1e-9
    print("   全部成立。Dubins − RS の最大 %.3f(後退が効く分)" % worst_gap)

    # ---- 4. 整列 ---------------------------------------------------------------------------------
    d = CP.car_dubins_path([(1, 2, 0.3), (1 + 5 * math.cos(0.3), 2 + 5 * math.sin(0.3), 0.3)], radius=1.7)
    r = CP.car_reeds_shepp_path([(1, 2, 0.3), (1 + 5 * math.cos(0.3), 2 + 5 * math.sin(0.3), 0.3)], radius=1.7)
    assert abs(d["length"] - 5) < 1e-9 and abs(r["length"] - 5) < 1e-9 and r["word"] == "S"
    rb = CP.car_reeds_shepp_path([(0, 0, 0), (-2, 0, 0)], radius=1.0)
    assert rb["word"] == "s" and abs(rb["length"] - 2) < 1e-9
    truths += [("整列 5 m (Dubins)", d["length"], 5.0), ("整列 5 m (RS)", r["length"], 5.0), ("真後ろ 2 m (RS)", rb["length"], 2.0)]
    print("4. 整列した目標: Dubins %.6f、RS %.6f(語 %s)、真後ろ 2 m は RS %.6f(語 %s)" % (d["length"], r["length"], r["word"], rb["length"], rb["word"]))

    # ---- 5. Hybrid A*: 空の駐車場 = 閉形式 -----------------------------------------------------------
    occ, cell = parking_lot()
    rho, fp = 5.5, (4.5, 1.8, 1.0)
    # 障害物の無い 40 × 30 m(格子の外は衝突なので、閉形式の道が収まる広さにする —— 12 × 8 m の駐車場では
    # ρ 5.5 m の Dubins の道が外へ出て「到達不能」が正しい答えになる)
    empty = np.zeros((60, 80), bool)
    s, g = (8.0, 10.0, 0.0), (28.0, 18.0, math.pi / 2)
    h0 = CP.car_hybrid_astar(empty, [s, g], radius=rho, cell=0.5, n_theta=72)
    rs0 = CP.car_reeds_shepp_path([s, g], radius=rho)["length"]
    assert abs(h0["cost"] - rs0) < 1e-9 and h0["closed_by_shot"] and h0["n_expanded"] == 1
    hd = CP.car_hybrid_astar(empty, [s, g], radius=rho, cell=0.5, n_theta=72, allow_reverse=False)
    du0 = CP.car_dubins_path([s, g], radius=rho)["length"]
    assert abs(hd["cost"] - du0) < 1e-9 and hd["closed_by_shot"]
    truths += [("空の格子 Hybrid A* (RS)", h0["cost"], rs0), ("空の格子 Hybrid A* (Dubins)", hd["cost"], du0)]
    print("5. 障害物の無い格子: Hybrid A* %.6f = RS %.6f(展開 %d、一撃)/ 前進のみ %.6f = Dubins %.6f" % (h0["cost"], rs0, h0["n_expanded"], hd["cost"], du0))

    # ---- 6. 縦列駐車 ------------------------------------------------------------------------------
    s, g = (2.0, 4.2, 0.0), (7.5, 1.5, 0.0)   # 車線から、2 台の間の車室(x 5.0〜12.5、後軸 7.5 → 車体 6.5〜11.0、y 0.6〜2.4)へ
    t = time.time()
    h = CP.car_hybrid_astar(occ, [s, g], radius=rho, cell=cell, n_theta=72, footprint=fp, return_tree=True)
    t_park = time.time() - t
    rs_lb = CP.car_reeds_shepp_path([s, g], radius=rho)["length"]
    P = h["points"]
    coll = CP._Collision(occ, cell, 0.0, fp)
    assert not coll.blocked(P)
    dd = np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1]))
    dth = np.abs([CP._wrap(v) for v in np.diff(P[:, 2])])
    ok = dd > 1e-9
    assert np.all(dth[ok] * rho <= dd[ok] * 1.001 + 1e-6)
    assert h["cost"] >= h["lower_bound"] - 1e-9 and abs(h["lower_bound"] - rs_lb) < 1e-9
    assert np.allclose(P[0], s) and np.allclose(P[-1], g)
    n_rev = sum(1 for _, gr, _ in h["segments"] if gr < 0)
    n_switch = sum(1 for a, b in zip(h["segments"][:-1], h["segments"][1:]) if a[1] != b[1])
    assert coll.blocked(CP.car_reeds_shepp_path([s, g], radius=rho)["points"])  # 障害物を無視した RS は車にぶつかる
    print("6. 縦列駐車: 費用 %.3f m ≥ RS 下界 %.3f m(RS の道は駐車車両にぶつかる)、展開 %d・生成 %d、区間 %d(後退 %d、切替 %d)、%.1f 秒"
          % (h["cost"], rs_lb, h["n_expanded"], h["n_generated"], len(h["segments"]), n_rev, n_switch, t_park))

    # ---- 7. fail-closed -----------------------------------------------------------------------------
    wall = occ.copy()
    wall[:, int(6.0 / cell)] = True   # 始点の車体(前端 x 5.5)と車室(x 6.5〜)の間を塞ぐ
    try:
        CP.car_hybrid_astar(wall, [s, g], radius=rho, cell=cell, n_theta=36, footprint=fp)
        raise AssertionError("壁を塞いだのに道が返った")
    except ValueError as e:
        assert "unreachable" in str(e)
    print("7. 壁で塞ぐと ValueError(部分的な道は返さない)")

    # ---- 図 ---------------------------------------------------------------------------------------
    if figs.enabled():
        # 01: Dubins の 6 語
        s6, g6 = (2.0, 2.0, 0.6), (7.0, 5.0, -2.2)
        d6 = CP.car_dubins_path([s6, g6], radius=1.5)
        panels, caps = [], []
        for w, L in d6["candidates"]:
            cv = Canvas(10, 8, 20)
            ok_, _ = CP._dubins(s6, g6, 1.5)
            lens = [c[2] for c in ok_ if c[1] == w][0]
            cv.polyline(CP._sample(w, lens, s6, 1.5, 0.05), (0.85, 0.15, 0.15) if w == d6["word"] else (0.5, 0.5, 0.5), 3)
            cv.arrow(s6, 1.0, (0.1, 0.6, 0.1), 3)
            cv.arrow(g6, 1.0, (0.1, 0.35, 0.9), 3)
            panels.append(cv.img)
            caps.append("%s  %.3f m%s" % (w, L, "  ← 最短" if w == d6["word"] else ""))
        figs.save_grid("dubins_six_words", panels, caps, ncols=3,
                       title="Dubins: 同じ始点(緑)→ 終点(青)へ 6 語の道。最短(赤)は %s、%.3f m(ρ = 1.5 m)" % (d6["word"], d6["length"]),
                       caption="前進だけの車の最短路は LSL/RSR/LSR/RSL/RLR/LRL の 6 語に限られる(定理)。区間長は閉形式で、"
                               "各候補は前進積分で終点を検証してある。この対では %d 語が目標に届く。" % len(d6["candidates"]))
        # 02: Reeds–Shepp の一覧(始点 (0,0,0) から 4×4 の目標)
        panels, caps = [], []
        for gy in (3.0, 1.0, -1.0, -3.0):
            for gx in (-3.0, -1.0, 1.0, 3.0):
                gg = (gx, gy, math.pi / 2)
                rr = CP.car_reeds_shepp_path([(0, 0, 0), gg], radius=1.0)
                dd_ = CP.car_dubins_path([(0, 0, 0), gg], radius=1.0)
                cv = Canvas(10, 10, 16)
                off = lambda p: (p[0] + 5, p[1] + 5, p[2])  # noqa: E731
                cv.polyline(np.array([off(p) for p in dd_["points"]]), (0.75, 0.75, 0.75), 2)
                i = 0
                for kind, gear, length in rr["segments"]:
                    n = max(1, int(math.ceil(length / 0.05 - 1e-9)))
                    cv.polyline(np.array([off(p) for p in rr["points"][i:i + n + 1]]), (0.85, 0.15, 0.15) if gear > 0 else (0.1, 0.35, 0.9), 3)
                    i += n
                cv.arrow(off((0, 0, 0)), 1.0, (0.1, 0.6, 0.1), 3)
                cv.arrow(off(gg), 1.0, (0.1, 0.1, 0.1), 3)
                panels.append(cv.img)
                caps.append("(%+.0f, %+.0f, 90°) %s %.2f / Dubins %.2f" % (gx, gy, rr["word"], rr["length"], dd_["length"]))
        figs.save_grid("reeds_shepp_gallery", panels, caps, ncols=4,
                       title="Reeds–Shepp: 始点 (0, 0, 0°)(緑)から 16 の目標(黒、向き 90°)へ。赤 = 前進、青 = 後退、灰 = Dubins(前進のみ)",
                       caption="小文字 = 後退の区間。後退を許すと Dubins より必ず短いか等しい(400 対で確認、最大差 %.3f)。ρ = 1 m。" % worst_gap)
        # 03/04: 縦列駐車
        frames = []
        tree = h["tree"]
        base = Canvas(18, 8, 40)
        base.occupancy(occ, cell)
        for p in tree[1:]:
            r0, c0 = base._pix(p[0], p[1])
            r0, c0 = int(round(r0)), int(round(c0))
            if 0 <= r0 < base.H and 0 <= c0 < base.W:
                base.img[r0, c0] = (0.75, 0.85, 0.75)
        cv = Canvas(18, 8, 40)
        cv.img[:] = base.img
        draw_path(cv, {"points": P, "segments": h["segments"]}, 3)
        # points は 0.125 m 刻み(cell/2)なので区間の点数の復元が違う → 全体を前進/後退で塗り分ける
        cv.img[:] = base.img
        i = 0
        for kind, gear, length in h["segments"]:
            n = max(1, int(math.ceil(length / (0.5 * cell) - 1e-9)))
            cv.polyline(P[i:i + n + 1], (0.85, 0.15, 0.15) if gear > 0 else (0.1, 0.35, 0.9), 3)
            i += n
        cv.car(s, fp, (0.1, 0.6, 0.1), 2)
        cv.car(g, fp, (0.1, 0.1, 0.1), 2)
        figs.save("parking_tree", cv.img,
                  caption="縦列駐車の Hybrid A*: 灰 = 障害物(縁石・駐車車両 2 台・壁)、薄緑の点 = 展開した %d 姿勢、赤 = 前進、青 = 後退。"
                          "費用 %.3f m、障害物を無視した Reeds–Shepp の下界 %.3f m。cell %.2f m、θ 72 分割、ρ %.1f m、車体 %.1f × %.1f m。"
                          % (h["n_generated"], h["cost"], h["lower_bound"], cell, rho, fp[0], fp[1]))
        idx = np.linspace(0, len(P) - 1, 40).astype(int)
        for k in idx:
            fr = Canvas(18, 8, 40)
            fr.img[:] = cv.img
            fr.car(P[k], fp, (0.9, 0.5, 0.0), 3)
            frames.append(fr.img)
        frames = [frames[0]] * 4 + frames + [frames[-1]] * 8
        figs.save_gif("parking_gif", frames, fps=8,
                      caption="車(橙)が Hybrid A* の道を辿って 2 台の間に入る。%d コマ、前進 %d 区間・後退 %d 区間、切替 %d 回。"
                              % (len(frames), len(h["segments"]) - n_rev, n_rev, n_switch))
        # 05: 真値の散布
        tv = np.array([v for _, _, v in truths])
        mv = np.array([v for _, v, _ in truths])
        figs.save_plot("truths", [("測った値", tv, mv), ("y = x", tv, tv)], kinds=["scatter", "line"],
                       xlabel="真値(閉形式 / 定理)", ylabel="op の答え", title="%d 件の真値と op の答え(点は y = x の上に乗る)" % len(truths),
                       caption="; ".join("%s %.4f" % (n, v) for n, v, _ in truths))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS: 候補 0 落ち・語族 18/18、第 2 実装 6 件一致、不等式と対称 400 対、整列 3 件、空の格子で Hybrid A* = 閉形式 2 件、"
          "縦列駐車は衝突なし・実現可能・下界以上、壁は ValueError。合計 %.1f 秒。" % (time.time() - t_total))


if __name__ == "__main__":
    main()
