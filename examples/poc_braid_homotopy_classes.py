# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""同じ始点と同じ終点を結ぶ複数ロボットの計画を「回り方」で分ける —— 時空の組紐と Dynnikov 座標(2026-10-06)。

3 台のロボットが柱のある床で持ち場を入れ替える。どの計画も始点と終点は同じなのに、柱の上を回るか下を回るか、
誰が誰の前を横切るかで「連続に変形しても移り合えない」違いがある。時間を縦軸に積むと、各台の軌跡と柱は紐になり、
計画は**組紐**になる。組紐の類(ホモトピー類)を Dynnikov 座標(整数の組)で数え、既存の計画器が出した多数の候補を
類に分け、類ごとに最も安い代表を選ぶ。題材の背景は平面の複数エージェント経路計画のホモトピー
(doi:10.1613/jair.1.19243)。本文は使っていない —— 下の外から来る数学と比べる。

外から来るもの:
  * 組紐の関係式 σᵢσᵢ₊₁σᵢ = σᵢ₊₁σᵢσᵢ₊₁、σᵢσⱼ = σⱼσᵢ(|i − j| ≥ 2)、σσ⁻¹ = 1 —— Dynnikov の作用で恒等的に成り立つはず。
  * Artin 表現(自由群の自己同型、忠実)と Dehornoy の取っ手簡約 —— Dynnikov と独立な 2 つの判定。
  * 参照実装(MIT)の出力 240 件(tests/data/braidpath_reference.json、座標・自明か・Dehornoy の順序の主の文字)。
  * 巻き数の閉形式: k 周の公転で k、純粋な組紐で 2W = 対の交差の符号つきの数。
  * 1 台が柱(3 × 3)のまわりを回る類ごとの最短の費用 = d + 16 m(柱を囲む輪は 16 手)。
被験者(既存の op): agvfleet.mapf_cbs(最適な計画)・mapf_prioritized(経由点つきの候補)・grid_distances(切り込みの BFS)。

門(既定 11 本、numpy + scipy、数秒):
  1 関係式の恒等性 / 2 3 つの判定の一致(両側)/ 3 参照実装との一致 / 4 巻き数の閉形式 / 5 交換子(巻き数 0 でも別の類)/
  6 1 台の類ごとの最短 = 閉形式と切り込みの BFS / 7 既存の計画器を被験者に(類は列挙の中、費用は最短以上)/
  8 3 台の候補を類に分ける(最適な計画は最も安い類)/ 9 摂動で類が変わらない(両側)/ 10 角度・時間の細分・三重点のずらしに
  依らない / 11 出力が空・定数・inf でない。
図(FULLSEYE_FIGURE_DIR があるとき、等倍・可逆): 01 同じ始点と終点で類の違う 3 つの計画を時空の 3-D 組紐として回す GIF /
  02 その静止画 / 03 床の上の 3 つの計画 / 04 1 台の類ごとの最短経路(短い順に 5 本)/ 05 類の表。
正直に: 巻き数は可換な量なので交換子の形の違いを見逃す(門 5)。類は無限にあり、候補の抽出が見つけた類しか並ばない。
Run: py -3.11 examples/poc_braid_homotopy_classes.py
"""
from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agvfleet as AF  # noqa: E402
import braidpath as B  # noqa: E402
import examplefig as figs  # noqa: E402

_GATES: list[tuple[str, bool]] = []
STARTS, GOALS = [(4, 1), (4, 11), (0, 6)], [(4, 11), (4, 1), (8, 6)]
NAMES = ("A", "B", "C")


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail), flush=True)


def pillar_grid():
    g = np.ones((9, 13), bool)
    g[3:6, 5:8] = False
    return g


def _ref_path() -> Path:
    here = Path(__file__).resolve().parent
    for p in (here.parent / "tests" / "data" / "braidpath_reference.json", here / "data" / "braidpath_reference.json"):
        if p.is_file():
            return p
    raise FileNotFoundError("braidpath_reference.json (tests/data) が見つからない")


def _rewrite(w, n, steps, rng):
    w = list(w)
    for _ in range(steps):
        r = rng.random()
        if r < 0.3 and len(w) >= 3:
            k = rng.randrange(len(w) - 2)
            a, b, c = w[k:k + 3]
            if a == c and abs(abs(a) - abs(b)) == 1 and (a > 0) == (b > 0):
                w[k:k + 3] = [b, a, b]
                continue
        if r < 0.6 and len(w) >= 2:
            k = rng.randrange(len(w) - 1)
            a, b = w[k:k + 2]
            if abs(abs(a) - abs(b)) >= 2:
                w[k:k + 2] = [b, a]
                continue
        k = rng.randint(0, len(w))
        i, s = rng.randint(1, n - 1), rng.choice([1, -1])
        w[k:k] = [s * i, -s * i]
    return w


def sample_plans(g, n_samples=60, seed=0):
    """既存の計画器で候補を作る: 最適な CBS の 1 本 + 経由点つきの優先度付き計画(2 区間をつなぐ)。"""
    plans, costs = [], []
    base = AF.mapf_cbs(g, STARTS, GOALS)
    plans.append(base)
    costs.append(base["cost"])
    rng = random.Random(seed)
    free = [tuple(int(v) for v in c) for c in np.argwhere(g)]
    for _ in range(n_samples):
        vias = [rng.choice(free) for _ in STARTS]
        p1 = AF.mapf_prioritized(g, STARTS, vias, order=rng.sample(range(3), 3))
        if not p1["solved"]:
            plans.append(None)
            continue
        p2 = AF.mapf_prioritized(g, vias, GOALS, order=rng.sample(range(3), 3))
        if not p2["solved"]:
            plans.append(None)
            continue
        T1 = max(len(p) for p in p1["paths"])
        paths = [list(a) + [a[-1]] * (T1 - len(a)) + list(b[1:]) for a, b in zip(p1["paths"], p2["paths"])]
        if AF.plan_conflicts(paths):
            plans.append(None)
            continue
        plans.append({"paths": paths})
        costs.append(AF.plan_cost(paths))
    return plans, base


def _perturb(P, amp, rng):
    T = P.shape[1]
    t = np.linspace(0, 1, T)
    w = np.sin(np.pi * t)[None, :, None]
    noise = rng.normal(0, 1, (P.shape[0], 4, 2))
    bump = sum(noise[:, h][:, None, :] * np.sin((h + 1) * np.pi * t)[None, :, None] for h in range(4)) / 4
    return P + amp * w * bump


def _refine(P, m):
    t0 = np.arange(P.shape[1])
    t1 = np.linspace(0, P.shape[1] - 1, (P.shape[1] - 1) * m + 1)
    return np.stack([np.stack([np.interp(t1, t0, P[k, :, d]) for d in range(2)], -1) for k in range(P.shape[0])])


def run() -> dict:
    out = {}
    rng = random.Random(1)
    # 1. 関係式の恒等性(乱数の実数の座標と整数の座標)
    worst_i, worst_r, nchk = 0, 0.0, 0
    for trial in range(400):
        n = rng.randint(3, 7)
        real = trial % 2 == 1
        co = [rng.uniform(-40, 40) if real else rng.randint(-25, 25) for _ in range(2 * (n - 1))]
        i, s = rng.randint(1, n - 2), rng.choice([1, -1])
        pairs = [([s * i, s * (i + 1), s * i], [s * (i + 1), s * i, s * (i + 1)]), ([i, -i], []), ([-(i + 1), i + 1], [])]
        j = rng.randint(1, n - 1)
        if abs(i - j) >= 2:
            pairs.append(([i, s * j], [s * j, i]))
        for lhs, rhs in pairs:
            a = B.dynnikov_act(co, lhs)["key"]
            b = B.dynnikov_act(co, rhs)["key"] if rhs else tuple(co)
            e = max(abs(x - y) for x, y in zip(a, b))
            worst_r, worst_i = (max(worst_r, e), worst_i) if real else (worst_r, max(worst_i, e))
            nchk += 1
    wrong = 0
    for _ in range(100):                     # 否定の側: 関係式でない σ₁σ₂ = σ₂σ₁(隣り合う対の可換)は破れるはず
        co = [rng.randint(-20, 20) for _ in range(6)]
        wrong += B.dynnikov_act(co, [1, 2])["key"] != B.dynnikov_act(co, [2, 1])["key"]
    gate("1 組紐の関係式が Dynnikov の作用で恒等的に成り立つ", worst_i == 0 and worst_r < 1e-11 and wrong >= 75,
         "%d 通り: 整数の最大のずれ %d、実数 %.1e(丸め)/ 関係式でない σ₁σ₂ = σ₂σ₁ は 100 回中 %d 回破れる"
         % (nchk, worst_i, worst_r, wrong))
    # 2. 3 つの独立な判定(両側)
    n_eq = n_ne = 0
    for trial in range(200):
        n = rng.randint(2, 6)
        w = [rng.choice([1, -1]) * rng.randint(1, n - 1) for _ in range(rng.randint(0, 12))]
        if trial % 2:
            v = _rewrite(w, n, 8, rng)
        else:
            v = list(w)
            v.insert(rng.randint(0, len(v)), rng.choice([1, -1]) * rng.randint(1, n - 1))
        r = B.braid_equivalent(w, v, n, method="all")
        n_eq += r["equal"] and trial % 2 == 1
        n_ne += (not r["equal"]) and trial % 2 == 0
    gate("2 Dynnikov・取っ手簡約・Artin 表現の 3 つが両側で一致", n_eq == 100 and n_ne == 100,
         "関係式で書き換えた同じ組紐 %d/100 を同じ、1 文字足した組紐 %d/100 を違うと 3 つとも判定" % (n_eq, n_ne))
    # 3. 参照実装
    cases = json.loads(_ref_path().read_text())["cases"]
    ok_c = ok_r = n_triv = 0
    for c in cases:
        dy = B.dynnikov_coordinates(c["word"], c["n"])
        ok_c += [v for p in zip(dy["a"], dy["b"]) for v in p] == c["ref_dynnikov_interleaved"]
        r = B.braid_reduce(c["word"], c["n"]).tolist()
        if r:
            m = min(abs(x) for x in r)
            sg = 1 if [x for x in r if abs(x) == m][0] > 0 else -1
            ok_r += (m, sg) == (c["ref_main_index"], c["ref_main_sign"])
        else:
            ok_r += c["ref_reduced_length"] == 0
            n_triv += 1
    gate("3 参照実装(MIT)の出力と一致", ok_c == len(cases) and ok_r == len(cases),
         "Dynnikov 座標 %d/%d、自明か・Dehornoy の主の文字と符号 %d/%d(自明 %d 件・自明でない %d 件、座標の最大 %d)"
         % (ok_c, len(cases), ok_r, len(cases), n_triv, len(cases) - n_triv,
            max(max([abs(v) for v in c["ref_dynnikov_interleaved"]] or [0]) for c in cases)))
    # 4. 巻き数の閉形式
    errs = []
    for turns in (1, 2, -3):
        t = np.linspace(0, 1, 200)
        a = np.stack([np.cos(2 * math.pi * turns * t), np.sin(2 * math.pi * turns * t)], -1)
        P = np.stack([a, np.zeros_like(a)])
        errs.append(abs(B.pairwise_winding(P)[0, 1] - turns))
        errs.append(abs(int(B.braid_from_trajectories(P)["word"].sum()) - 2 * turns))
    npr = np.random.default_rng(5)
    pure_err, npure = 0.0, 0
    for _ in range(20):
        K, T = 4, 400
        t = np.linspace(0, 1, T)
        P = np.repeat(npr.uniform(-3, 3, (K, 1, 2)), T, axis=1)
        for h in range(1, 4):
            amp = npr.normal(0, 1.2 / h, (K, 2))
            ph = npr.uniform(0, 2 * math.pi, (K, 2))
            P += amp[:, None, :] * (np.sin(2 * math.pi * h * t[None, :, None] + ph[:, None, :]) - np.sin(ph)[:, None, :])
        try:
            br = B.braid_from_trajectories(P)
            W = B.pairwise_winding(P)
        except ValueError:
            continue
        order, cr = list(br["start_order"]), {}
        for x in br["word"].tolist():
            p = abs(x) - 1
            u, v = sorted((order[p], order[p + 1]))
            cr[(u, v)] = cr.get((u, v), 0) + (1 if x > 0 else -1)
            order[p], order[p + 1] = order[p + 1], order[p]
        pure_err = max(pure_err, max(abs(2 * W[i, j] - cr.get((i, j), 0)) for i in range(K) for j in range(i + 1, K)))
        npure += 1
    gate("4 巻き数の閉形式", max(errs) < 1e-12 and pure_err < 1e-9 and npure >= 12,
         "k 周の公転 (1, 2, −3) で巻き数 = k・文字の和 = 2k(最大のずれ %.1e)/ 乱数の閉じた動き %d 組で 2W = 対の交差の数(%.1e)"
         % (max(errs), npure, pure_err))
    # 5. 交換子
    seg = []
    for cx, sgn in ((-1.0, 1), (1.0, 1), (-1.0, -1), (1.0, -1)):
        th = np.linspace(0, 2 * math.pi, 60, endpoint=False) * sgn
        st = math.pi if cx > 0 else 0.0
        seg.append(np.stack([cx + np.cos(st + th), np.sin(st + th)], -1))
    loop = np.vstack(seg + [np.zeros((1, 2))])[None]
    O2 = np.array([[-1.0, 0.0], [1.0, 0.0]])
    Wc = B.pairwise_winding(loop, O2)
    rc = B.homotopy_class_compare(loop, np.zeros_like(loop), O2)
    gate("5 交換子: 巻き数は全部 0 なのに組紐は自明でない", np.max(np.abs(Wc[0, 1:])) < 1e-12 and not rc["same"],
         "2 つの穴のまわりを a b a⁻¹ b⁻¹: 巻き数 (%.1e, %.1e)、組紐の商 %s(長さ %d)"
         % (Wc[0, 1], Wc[0, 2], rc["quotient"].tolist(), rc["quotient"].size))
    out["commutator"] = (loop, O2)
    # 6. 1 台の類ごとの最短
    g = pillar_grid()
    t0 = time.process_time()
    hs = B.homotopy_shortest_paths(g, (4, 1), (4, 11), k=5)
    t_hs = time.process_time() - t0
    gu, gd = g.copy(), g.copy()
    gu[0:3, 6] = False
    gd[6:, 6] = False
    cut = (AF.grid_distances(gu, (4, 11))[4, 1], AF.grid_distances(gd, (4, 11))[4, 1])
    closed = [14 + 16 * (m // 2) for m in range(5)]
    gate("6 1 台の類ごとの最短の費用 = 閉形式 d + 16 m = 切り込みの BFS",
         hs["costs"].tolist() == closed and sorted(cut) == closed[:2] and len(set(hs["keys"])) == 5,
         "費用 %s(閉形式 %s)、柱の上 / 下に切り込みを入れた BFS %s、開いた状態 %d(%.2f s)"
         % (hs["costs"].astype(int).tolist(), closed, [int(c) for c in cut], hs["states"], t_hs))
    out["single"] = hs
    # 7. 既存の計画器を被験者に(1 台、穴 2 つ)
    g2 = np.ones((10, 14), bool)
    g2[2:4, 4:7] = False
    g2[6:8, 8:11] = False
    s2, e2 = (5, 0), (5, 13)
    ex = B.homotopy_shortest_paths(g2, s2, e2, k=8)
    exact = dict(zip(ex["keys"], ex["costs"]))
    r7 = random.Random(7)
    free2 = [tuple(int(v) for v in c) for c in np.argwhere(g2)]
    hit = {}
    for _ in range(60):
        v = r7.choice(free2)
        if v in (s2, e2):
            continue
        a = AF.mapf_cbs(g2, [s2], [v])["paths"][0]
        b = AF.mapf_cbs(g2, [v], [e2])["paths"][0]
        path = list(a) + list(b[1:])
        key = B.dynnikov_coordinates(B.braid_from_trajectories(B.grid_paths_to_xy([path]), ex["obstacles"])["word"],
                                     1 + len(ex["obstacles"]))["key"]
        hit[key] = min(hit.get(key, 10 ** 9), len(path) - 1)
    inside = [k for k, c in hit.items() if c <= ex["costs"][-1]]
    cheap = sorted(exact.items(), key=lambda kv: kv[1])[:2]
    gate("7 既存の計画器(経由点つき)の経路は列挙した類に入り、費用は類の最短以上",
         bool(inside) and all(k in exact for k in inside) and all(hit[k] >= exact[k] for k in inside)
         and all(k in hit and hit[k] == c for k, c in cheap),
         "経由点 60 個 → 類 %d(列挙の範囲 %d 手以内に %d、全部が列挙の 8 類の中)、安い 2 類 %s 手はちょうど当たる、列挙の費用 %s"
         % (len(hit), int(ex["costs"][-1]), len(inside), [int(c) for _k, c in cheap], ex["costs"].astype(int).tolist()))
    # 8. 3 台の候補を類に分ける
    t0 = time.process_time()
    plans, base = sample_plans(g)
    O = B.grid_hole_points(g)
    rep = B.braid_class_representatives(plans, O, costs=[AF.plan_cost(p["paths"]) if p else None for p in plans])
    t_rep = time.process_time() - t0
    cls = rep["classes"]
    gate("8 3 台の候補を類に分け、最適な計画(CBS)は最も安い類の代表",
         rep["n_classes"] >= 5 and cls[0]["best"] == 0 and cls[0]["cost"] == base["cost"]
         and all(c["cost"] >= base["cost"] for c in cls),
         "候補 %d(失敗 %d)→ 類 %d、安い順の費用 %s、多い類 %s 本、三重点のずらし %s(%.2f s)"
         % (rep["n_plans"], rep["n_failed"], rep["n_classes"], [int(c["cost"]) for c in cls[:6]],
            sorted((c["count"] for c in cls), reverse=True)[:4], "あり" if rep["jitter"] > 0 else "なし", t_rep))
    reps = [B.grid_paths_to_xy(plans[c["best"]]["paths"]) for c in cls]
    out.update(plans=plans, rep=rep, reps=reps, O=O, grid=g)
    Ws = [np.round(B.pairwise_winding(R, O), 9) for R in reps]
    n_pairs = len(Ws) * (len(Ws) - 1) // 2
    same_full = sum(np.array_equal(Ws[i], Ws[j]) for i in range(len(Ws)) for j in range(i + 1, len(Ws)))
    same_pillar = sum(np.array_equal(Ws[i][3, :3], Ws[j][3, :3]) for i in range(len(Ws)) for j in range(i + 1, len(Ws)))
    print("      巻き数との比較: %d 類の %d 対のうち、柱のまわりの巻き数だけでは %d 対が重なる / 対ごとの巻き数の行列ぜんぶでは %d 対"
          "(この場面では分けられた —— 一般には分けられない、門 5)" % (len(Ws), n_pairs, same_pillar, same_full), flush=True)
    out["winding_overlap"] = (same_pillar, same_full, n_pairs)
    # 9. 摂動(両側)
    nr = np.random.default_rng(8)
    same = diff = tot_s = tot_d = 0
    for i, P in enumerate(reps[:6]):
        Q = _perturb(P, 0.12, nr)
        same += B.homotopy_class_compare(P, Q, O)["same"]
        tot_s += 1
        for j, R in enumerate(reps[:6]):
            if j != i:
                diff += not B.homotopy_class_compare(Q, R, O)["same"]
                tot_d += 1
    gate("9 摂動で類が変わらない(両側)", same == tot_s and diff == tot_d,
         "振幅 0.12 マスの滑らかな摂動: 同じ類 %d/%d を同じ、違う類 %d/%d を違うと判定" % (same, tot_s, diff, tot_d))
    # 10. 角度・細分・三重点
    def verdicts(angle, refine=1):
        res = []
        for i in range(5):
            for j in range(5):
                A, Bm = reps[i], reps[j]
                if refine > 1:
                    A, Bm = _refine(A, refine), _refine(Bm, refine)
                res.append(B.homotopy_class_compare(A, Bm, O, angle=angle)["same"])
        return res
    v0 = verdicts(B.DEFAULT_ANGLE)
    angles = (0.0, 0.37, 1.1, 2.4, -0.8)
    same_ang = all(verdicts(a) == v0 for a in angles)
    same_ref = verdicts(B.DEFAULT_ANGLE, 3) == v0
    t = np.linspace(0, 1, 2)
    Pt = np.stack([np.stack([5 + t, -2 + 0 * t], -1), np.stack([7 - t, -6 + 0 * t], -1)])
    Ot = np.array([[6.0, -4.0]])
    try:
        B.braid_from_trajectories(Pt, Ot, jitter=0.0)
        tp_raise = False
    except B.TriplePointError:
        tp_raise = True
    rj = B.braid_from_trajectories(Pt, Ot)
    keys = {B.dynnikov_coordinates(B.braid_from_trajectories(Pt + npr.normal(0, 1e-3, (2, 1, 2)), Ot, jitter=0.0)["word"],
                                   3)["key"] for _ in range(10)}
    tp_ok = tp_raise and keys == {B.dynnikov_coordinates(rj["word"], 3)["key"]}
    gate("10 類の判定は射影の角度・時間の細分・三重点のずらしに依らない", sum(v0) == 5 and same_ang and same_ref and tp_ok,
         "5 類の 25 対の判定が角度 %d 通り・3 倍の細分で同じ / 点対称の動きの三重点: ずらしなしは止める、ずらし %.1e の類 = "
         "1e-3 の乱数の摂動 10 回の類" % (len(angles), rj["jitter"]))
    # 11. 中身
    vals = [np.asarray(B.dynnikov_coordinates(c["word"], 4)["a"] + B.dynnikov_coordinates(c["word"], 4)["b"], float)
            for c in cls[:3]]
    big = B.dynnikov_coordinates([1, -2] * 60, 3)
    W3 = B.pairwise_winding(reps[0], O)
    gate("11 出力が空・定数・inf でない", all(v.size and np.all(np.isfinite(v)) and np.ptp(v) > 0 for v in vals)
         and big["bits"] > 63 and np.ptp(W3) > 0 and np.all(np.isfinite(W3)),
         "類の座標 %s / (σ₁σ₂⁻¹)^60 の座標は %d bit(64 bit を超えても溢れない)" % ([v.astype(int).tolist() for v in vals[:2]], big["bits"]))
    return out


# ======================================================================================================================
# 図
_COLORS = ("#d1495b", "#2e86ab", "#edae49")


def _agent_curve(P, k, sub=8):
    """格子の経路の角を丸めずに、各刻みを sub 等分して時刻を連続に(3-D の紐の見た目のため)。"""
    R = _refine(P, sub)
    t = np.linspace(0, P.shape[1] - 1, R.shape[1])
    return R[k, :, 0], R[k, :, 1], t


def _braid_frames(reps, O, cls, azims, size=(1260, 480)):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=(size[0] / 100, size[1] / 100), dpi=100)
    canvas = FigureCanvasAgg(fig)
    axes = [fig.add_subplot(1, 3, i + 1, projection="3d") for i in range(3)]
    Tmax = max(P.shape[1] for P in reps[:3]) - 1
    frames = []
    for az in azims:
        for i, ax in enumerate(axes):
            ax.cla()
            P = reps[i]
            for k in range(P.shape[0]):
                x, y, t = _agent_curve(P, k)
                ax.plot(x, y, t, color=_COLORS[k], lw=2.6, label=NAMES[k])
                ax.scatter([x[0]], [y[0]], [0], color=_COLORS[k], s=24)
                ax.scatter([x[-1]], [y[-1]], [t[-1]], color=_COLORS[k], s=24, marker="s")
            for ox, oy in O:
                ax.plot([ox, ox], [oy, oy], [0, Tmax], color="#444444", lw=5, alpha=0.8)
            ax.set_xlim(0, 12)
            ax.set_ylim(-8, 0)
            ax.set_zlim(0, Tmax)
            ax.set_xlabel("x [cell]")
            ax.set_ylabel("y [cell]")
            ax.set_zlabel("time [step]")
            ax.view_init(elev=18, azim=az)
            w = " ".join(("s%d" % x) if x > 0 else ("s%d^-1" % -x) for x in cls[i]["word"].tolist()) or "trivial"
            ax.set_title("class %d: cost %d\nreduced word %s" % (i + 1, int(cls[i]["cost"]), w), fontsize=9)
        axes[0].legend(loc="upper left", fontsize=8, title="robot", title_fontsize=8)
        fig.suptitle("Same starts and goals, different braids (grey pole = pillar, time runs upward)", fontsize=11)
        fig.subplots_adjust(left=0.0, right=0.97, top=0.9, bottom=0.02, wspace=0.08)
        canvas.draw()
        frames.append(np.asarray(canvas.buffer_rgba())[..., :3].copy())
    return frames


def _floor_view(reps, O, g, cls, size=(1260, 360)):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=(size[0] / 100, size[1] / 100), dpi=100)
    canvas = FigureCanvasAgg(fig)
    for i in range(3):
        ax = fig.add_subplot(1, 3, i + 1)
        ax.imshow(~g, cmap="Greys", extent=(-0.5, g.shape[1] - 0.5, -g.shape[0] + 0.5, 0.5), vmin=0, vmax=1.6)
        P = reps[i]
        for k in range(P.shape[0]):
            off = (k - 1) * 0.12
            ax.plot(P[k, :, 0] + off, P[k, :, 1] + off, color=_COLORS[k], lw=2.2, label=NAMES[k])
            ax.annotate("", xy=(P[k, -1, 0] + off, P[k, -1, 1] + off), xytext=(P[k, -2, 0] + off, P[k, -2, 1] + off),
                        arrowprops=dict(arrowstyle="->", color=_COLORS[k], lw=2))
            ax.plot(P[k, 0, 0], P[k, 0, 1], "o", color=_COLORS[k])
        ax.plot(O[:, 0], O[:, 1], "x", color="black", ms=9, mew=2)
        ax.set_title("class %d (cost %d, %d of the candidates)" % (i + 1, int(cls[i]["cost"]), cls[i]["count"]), fontsize=9)
        ax.set_xticks(range(0, 13, 2))
        ax.set_aspect("equal")
    fig.axes[0].legend(loc="lower left", fontsize=8)
    fig.suptitle("Floor view of the same three plans (x = pillar's representative point; circle = start)", fontsize=11)
    fig.subplots_adjust(left=0.03, right=0.99, top=0.86, bottom=0.06, wspace=0.12)
    canvas.draw()
    return np.asarray(canvas.buffer_rgba())[..., :3].copy()


def _single_view(hs, g, size=(1500, 400)):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=(size[0] / 100, size[1] / 100), dpi=100)
    canvas = FigureCanvasAgg(fig)
    n = len(hs["paths"])
    for i, (p, c, w) in enumerate(zip(hs["paths"], hs["costs"], hs["words"])):
        ax = fig.add_subplot(1, n, i + 1)
        ax.imshow(~g, cmap="Greys", extent=(-0.5, g.shape[1] - 0.5, -g.shape[0] + 0.5, 0.5), vmin=0, vmax=1.6)
        x, y = p[:, 1].astype(float), -p[:, 0].astype(float)
        ax.plot(x, y, color="#d1495b", lw=2.2)
        step = max(1, len(x) // 6)
        for k in range(step, len(x), step):
            ax.annotate("", xy=(x[k], y[k]), xytext=(x[k - 1], y[k - 1]),
                        arrowprops=dict(arrowstyle="->", color="#d1495b", lw=1.8))
        ax.plot(x[0], y[0], "o", color="#2e86ab")
        ax.plot(x[-1], y[-1], "s", color="#2e86ab")
        ax.plot(hs["obstacles"][:, 0], hs["obstacles"][:, 1], "x", color="black", ms=9, mew=2)
        ax.set_title("#%d  cost %d\nword %s" % (i + 1, int(c), " ".join(str(v) for v in w.tolist())), fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_aspect("equal")
    fig.suptitle("One robot, pillar in the middle: shortest path of each homotopy class, in order "
                 "(cost 14 + 16 m; circle = start, square = goal)", fontsize=11)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.78, bottom=0.03, wspace=0.06)
    canvas.draw()
    return np.asarray(canvas.buffer_rgba())[..., :3].copy()


def make_figures(out):
    t0 = time.time()
    reps, O, cls, g = out["reps"], out["O"], out["rep"]["classes"], out["grid"]
    azims = np.linspace(-60, 300, 37)[:-1]
    frames = _braid_frames(reps, O, cls, azims)
    figs.save_gif("braid_classes_spacetime", frames, fps=10.0,
                  caption="同じ始点と終点を結ぶ 3 台の計画の、類の違う 3 つ(安い順)を時空の組紐として回す。灰色の柱が障害物、"
                          "時間は上向き。類 1 は最適な計画(CBS)。")
    figs.save("braid_classes_spacetime_still", frames[0], caption="図 01 の最初のコマ(等倍・可逆 PNG)。")
    figs.save("braid_classes_floor", _floor_view(reps, O, g, cls),
              caption="同じ 3 つの計画を床の上から見る(× は柱の代表の点)。")
    figs.save("braid_single_agent_classes", _single_view(out["single"], g),
              caption="1 台が柱を避けて左から右へ: 類ごとの最短経路を短い順に 5 本(費用 14・14・30・30・46 = 14 + 16m)。")
    rows = []
    for i, c in enumerate(cls[:8]):
        W = B.pairwise_winding(reps[i], O) if i < len(reps) else None
        rows.append([str(i + 1), str(int(c["cost"])), str(c["count"]), " ".join(str(x) for x in c["word"].tolist()) or "-",
                     " / ".join("%+.2f" % W[k, 3] for k in range(3)) if W is not None else ""])
    figs.save_table("braid_class_table", ["class", "cost", "count", "reduced word", "winding about pillar A/B/C"], rows,
                    title="Homotopy classes among the planner's candidates",
                    caption="候補を類に分けた表(費用の安い順)。巻き数は柱のまわりの回転数。")
    print("  図: %s(%.1f s)" % (figs.errors() or "ok", time.time() - t0))


def main() -> int:
    t0 = time.time()
    out = run()
    print("  門の所要 %.2f s" % (time.time() - t0))
    if figs.enabled():
        make_figures(out)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _n, ok in _GATES if not ok)
    print("門 %d 本、通過 %d" % (len(_GATES), len(_GATES) - n_ng))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
