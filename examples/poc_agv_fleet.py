# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""遅れても詰まらない倉庫 —— AGV の群れは「計画が正しい」だけでは止まる(2026-10-03)。

著者の発案: 「運転って言えば、もっと簡単で製造業でよく使われる AGV 系は全然やってないな」「技術課題とか調べて、
PoC してみましょう」。調べると、AGV の現場で止まる原因の上位は**複数台の交通** —— 狭い通路のデッドロックと、
計画どおりに走れない(滑り・人・荷役で数秒遅れる)ときの連鎖的な詰まりだった。

何をするか(床の格子を走る AGV、Kiva 型の格子航法):
  1. 12 台の搬送計画を焦点探索の CBS で作る(衝突 = 同じマス・すれ違い・追従を全部禁じる)。
  2. 同じ計画を 2 通りに実行する。各車両は 1 手ごとに確率 p で遅れる。
     - 素朴: 「次のマスが空いていれば進む」—— 順番の約束が無い。
     - 行動依存グラフ(ADG、Hönig ら 2019): 「同じマスを先に使う車が抜けるまで待つ」。
  3. 計画の 1 台分を VDA 5050(v3.0.0、MIT)の order に書き出し、仕様の規則で検査する。

門(どれも定理か第 2 実装):
  * CBS の総コストが、全台を 1 つの状態にした A*(第 2 実装)の最適値と一致する(Sharon ら 2015 の最適性)。
  * 焦点探索のコスト ≤ w · 最適(小さな問題で真値と照合)。
  * 優先度付き計画は、解があるのに**どの優先順でも**見つけられない問題がある(Ma ら 2019 の不完全性)を実例で。
  * ADG は遅れを 1000 通り入れても衝突 0・デッドロック 0、遅れが無ければ計画の時間で終わる。素朴な実行は詰まる。
  * VDA 5050 の order: ノードの sequenceId は偶数・エッジは奇数・エッジ数 = ノード数 − 1・base → horizon。

正直に: 格子の 1 手 = 一定時間の離散モデルで、加減速・旋回・車体の大きさは入れていない(マス = 車 1 台ぶんの区画)。
遅れは手ごとの独立な確率で、実際の遅れ(人・荷役)は連続時間で偏る。VDA 5050 の検査は自前の第 2 実装で、公式の
JSON スキーマとの照合は環境変数 FULLSEYE_VDA5050_DIR(スキーマの置き場、github.com/VDA5050/VDA5050)がある時だけ行う。
Run: py -3.11 examples/poc_agv_fleet.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agvfleet as AF  # noqa: E402
import examplefig as figs  # noqa: E402

N_AGV = 12
DELAY = 0.3
SEEDS = 1000
CELL = 26                                           # 1 マスの画素
PALETTE = np.array([[0.90, 0.30, 0.25], [0.20, 0.55, 0.85], [0.30, 0.70, 0.35], [0.95, 0.65, 0.15],
                    [0.60, 0.40, 0.80], [0.15, 0.70, 0.70], [0.85, 0.45, 0.65], [0.55, 0.55, 0.20],
                    [0.40, 0.30, 0.25], [0.20, 0.35, 0.55], [0.75, 0.20, 0.45], [0.45, 0.75, 0.80]])

_GATES = []


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def scene(seed=5):
    grid, info = AF.warehouse_grid(n_rack_rows=2, n_rack_cols=3, rack_len=3, aisle=2, margin=1)
    free = [tuple(map(int, x)) for x in np.argwhere(grid)]
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(free), 2 * N_AGV, replace=False)
    return grid, [free[i] for i in idx[:N_AGV]], [free[i] for i in idx[N_AGV:]]


# --------------------------------------------------------------------------- #
# 描画(俯瞰)
# --------------------------------------------------------------------------- #
def _disc(img, cy, cx, r, color):
    h, w = img.shape[:2]
    y0, y1, x0, x1 = max(0, int(cy - r - 1)), min(h, int(cy + r + 2)), max(0, int(cx - r - 1)), min(w, int(cx + r + 2))
    yy, xx = np.mgrid[y0:y1, x0:x1]
    a = np.clip(r + 0.5 - np.hypot(yy - cy, xx - cx), 0, 1)[..., None]
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + np.asarray(color) * a


def draw_floor(grid, goals=None):
    h, w = grid.shape
    img = np.ones((h * CELL, w * CELL, 3)) * 0.93
    for r in range(h):
        for c in range(w):
            y, x = r * CELL, c * CELL
            if not grid[r, c]:
                img[y:y + CELL, x:x + CELL] = (0.35, 0.33, 0.30)              # 棚
            else:
                img[y:y + CELL, x:x + 1] = 0.82
                img[y:y + 1, x:x + CELL] = 0.82                                # 床の格子(QR の升)
    if goals:
        for i, (r, c) in enumerate(goals):
            y, x = r * CELL + 3, c * CELL + 3
            col = PALETTE[i % len(PALETTE)]
            img[y:y + CELL - 6, x:x + 2] = col
            img[y:y + CELL - 6, x + CELL - 8:x + CELL - 6] = col
            img[y:y + 2, x:x + CELL - 6] = col
            img[y + CELL - 8:y + CELL - 6, x:x + CELL - 6] = col               # 目的地 = 色の枠
    return img


def draw_state(base, pos, title, waits=(), cycle=()):
    import annotate
    img = base.copy()
    for i, (r, c) in enumerate(pos):
        _disc(img, r * CELL + CELL / 2, c * CELL + CELL / 2, CELL * 0.36, PALETTE[i % len(PALETTE)])
    cyc = set(cycle)
    for a, b in waits:
        pa, pb = pos[a], pos[b]
        p0 = (pa[1] * CELL + CELL / 2, pa[0] * CELL + CELL / 2)
        p1 = (pb[1] * CELL + CELL / 2, pb[0] * CELL + CELL / 2)
        color = "wrong" if (a, b) in cyc else (0.25, 0.25, 0.25)
        img = annotate.arrow(img, p0, p1, color=color, width=3 if (a, b) in cyc else 1,
                             head_len=8.0, head_width=7.0)
    if title:                                           # 題名は格子の上の余白に(格子の上の行を隠さない)
        band = np.ones((42, img.shape[1], 3))
        img = np.concatenate([annotate.text_box(band, title, (6, 4), anchor="lt", font_size=13), img], axis=0)
    return np.clip(img, 0, 1)


def wait_cycle(edges):
    """待ちの辺(i → i が待つ相手)から閉路を 1 つ取り出す(デッドロックの証拠)。"""
    nxt = dict(edges)
    for s in nxt:
        seen, v = [], s
        while v in nxt and v not in seen:
            seen.append(v)
            v = nxt[v]
        if v in seen:
            loop = seen[seen.index(v):]
            return [(loop[k], loop[(k + 1) % len(loop)]) for k in range(len(loop))]
    return []


# --------------------------------------------------------------------------- #
# 節
# --------------------------------------------------------------------------- #
def section_optimality(n_cases=40):
    print("\n=== 1. CBS は最適 —— 全台を 1 つの状態にした A*(第 2 実装)と総コストを突き合わせる ===")
    rng = np.random.default_rng(1)
    agree = done = 0
    ecbs_ok = ecbs_n = 0
    for _ in range(4 * n_cases):
        if done >= n_cases:
            break
        g = rng.random((5, 5)) > 0.2
        free = [tuple(map(int, x)) for x in np.argwhere(g)]
        n = int(rng.integers(2, 4))
        if len(free) < 2 * n:
            continue
        idx = rng.choice(len(free), 2 * n, replace=False)
        S, G = [free[i] for i in idx[:n]], [free[i] for i in idx[n:]]
        j = AF.mapf_joint_astar(g, S, G)
        if not j["solved"]:
            continue
        c = AF.mapf_cbs(g, S, G, max_nodes=20000)
        if not c["solved"]:
            continue                                   # 時間切れ(難しい問題)は数えない —— 件数は下で印字
        done += 1
        agree += int(c["cost"] == j["cost"] and not AF.plan_conflicts(c["paths"]))
        e = AF.mapf_ecbs(g, S, G, w=1.3)
        if e["solved"]:
            ecbs_n += 1
            ecbs_ok += int(e["cost"] <= 1.3 * j["cost"] + 1e-9 and not AF.plan_conflicts(e["paths"]))
    print("  CBS = 最適: %d / %d、焦点探索(w=1.3)≤ 1.3·最適: %d / %d" % (agree, done, ecbs_ok, ecbs_n))
    gate("CBS の総コストが結合 A* の最適値と一致", done >= n_cases * 0.8 and agree == done, "(%d/%d)" % (agree, done))
    gate("焦点探索のコスト ≤ w · 最適", ecbs_n >= 10 and ecbs_ok == ecbs_n, "(%d/%d)" % (ecbs_ok, ecbs_n))
    return {"agree": agree, "done": done, "ecbs_ok": ecbs_ok, "ecbs_n": ecbs_n}


def section_prioritized():
    print("\n=== 2. 優先度付き計画は不完全 —— 解があるのに、どの優先順でも見つけられない ===")
    rng = np.random.default_rng(1)
    for _ in range(2000):
        g = rng.random((4, 5)) > 0.25
        free = [tuple(map(int, x)) for x in np.argwhere(g)]
        n = 2
        if len(free) < 2 * n:
            continue
        idx = rng.choice(len(free), 2 * n, replace=False)
        S, G = [free[i] for i in idx[:n]], [free[i] for i in idx[n:]]
        c = AF.mapf_cbs(g, S, G, max_nodes=3000)
        if not c["solved"]:
            continue
        pp = [AF.mapf_prioritized(g, S, G, order=o) for o in itertools.permutations(range(n))]
        if all(not r["solved"] for r in pp):
            j = AF.mapf_joint_astar(g, S, G)
            print("  見つけた: 出発 %s → 目的地 %s、CBS の総コスト %d(結合 A* も %s)" % (S, G, c["cost"], j["cost"]))
            gate("優先度付き計画が全順で失敗し、CBS と結合 A* は解ける", j["solved"] and j["cost"] == c["cost"])
            return {"grid": g, "starts": S, "goals": G, "cbs": c, "pp": pp}
    gate("優先度付き計画の反例が見つかる", False)
    return None


def deadlock_kind(res):
    """素朴な実行のデッドロックの種類: 待ちの閉路(cycle)か、着いて居座る車による封鎖(parked)。"""
    if wait_cycle(res["waits_for"]):
        return "cycle"
    return "parked"


def section_execution(grid, S, G):
    print("\n=== 3. 遅れても詰まらない —— 同じ計画を、素朴な実行と行動依存グラフで %d 通りずつ ===" % SEEDS)
    t0 = time.perf_counter()
    plan = AF.mapf_ecbs(grid, S, G, w=1.1)
    t_plan = time.perf_counter() - t0
    gate("12 台の計画が解けて衝突なし", plan["solved"] and not AF.plan_conflicts(plan["paths"]),
         "(コスト %s ≤ 1.1 × 下界 %s、%.1f 秒)" % (plan["cost"], plan["lower_bound"], t_plan))
    gate("焦点探索のコスト ≤ w · 下界(倉庫)", plan["cost"] <= 1.1 * plan["lower_bound"] + 1e-9)
    paths = plan["paths"]
    adg = AF.adg_build(paths)
    ok = 0
    naive_dead = 0
    kinds = {}
    makespans = []
    for seed in range(SEEDS):
        r = AF.adg_execute(adg, DELAY, seed)
        ok += int(r["finished"] and r["collisions"] == 0)
        makespans.append(r["makespan"])
        q = AF.naive_execute(paths, DELAY, seed)
        if q["deadlock"]:
            naive_dead += 1
            kinds[deadlock_kind(q)] = kinds.get(deadlock_kind(q), 0) + 1
    plan_span = max(len(p) for p in paths) - 1
    r0 = AF.adg_execute(adg, 0.0, 0)
    print("  遅れ p = %.1f: ADG は %d / %d が衝突なしで全台到着(所要の平均 %.1f 手、計画は %d 手)、"
          "素朴な実行は %d / %d がデッドロック" % (DELAY, ok, SEEDS, np.mean(makespans), plan_span, naive_dead, SEEDS))
    print("  素朴な実行のデッドロックの種類: 待ちの閉路 %d / 着いた車による封鎖 %d"
          % (kinds.get("cycle", 0), kinds.get("parked", 0)))
    gate("ADG: 遅れ %d 通りで衝突 0・デッドロック 0" % SEEDS, ok == SEEDS)
    gate("ADG: 遅れが無ければ計画の時間以内に終わる", r0["finished"] and r0["makespan"] <= plan_span,
         "(%d ≤ %d)" % (r0["makespan"], plan_span))
    gate("素朴な実行は遅れで詰まる(遅れ 0 なら詰まらない)",
         naive_dead > SEEDS // 10 and not AF.naive_execute(paths, 0.0, 0)["deadlock"],
         "(%d / %d)" % (naive_dead, SEEDS))
    rates = []
    for p in (0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5):
        nd = sum(AF.naive_execute(paths, p, s)["deadlock"] for s in range(200))
        ad = sum(not AF.adg_execute(adg, p, s)["finished"] for s in range(200))
        rates.append((p, nd / 200.0, ad / 200.0))
    print("  遅れの確率 → デッドロック率(素朴 / ADG): " + ", ".join("%.2f→%.2f/%.2f" % r for r in rates))
    return {"paths": paths, "adg": adg, "rates": rates, "plan": plan, "naive_dead": naive_dead, "adg_ok": ok,
            "kinds": kinds}


def section_vda5050(paths):
    print("\n=== 4. VDA 5050 の order に書き出す(v3.0.0、MIT)===")
    orders = [AF.vda5050_order(p, order_id="agv%02d" % i, released_nodes=min(3, len(set(map(tuple, p)))))
              for i, p in enumerate(paths)]
    errs = [e for o in orders for e in AF.vda5050_check(o)]
    o = orders[0]
    print("  1 台目: ノード %d・エッジ %d、base %d ノード(released)、horizon %d"
          % (len(o["nodes"]), len(o["edges"]), sum(n["released"] for n in o["nodes"]),
             sum(not n["released"] for n in o["nodes"])))
    gate("全台の order が仕様の規則を満たす", not errs, "(違反 %d)" % len(errs))
    broken = json.loads(json.dumps(o))
    broken["edges"][0]["sequenceId"] = 2
    gate("規則の検査は壊した order を落とす", bool(AF.vda5050_check(broken)))
    sdir = os.environ.get("FULLSEYE_VDA5050_DIR")
    if sdir:
        try:
            import jsonschema
            schema = json.loads(Path(sdir, "json_schemas", "order.schema").read_text(encoding="utf-8"))
            for od in orders:
                jsonschema.validate(od, schema)
            gate("公式の JSON スキーマ(order.schema)にも合格", True)
        except Exception as exc:                        # noqa: BLE001
            gate("公式の JSON スキーマ(order.schema)にも合格", False, "(%s)" % exc)
    else:
        print("  [skip] 公式スキーマとの照合は FULLSEYE_VDA5050_DIR がある時だけ")
    return orders


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def figures(grid, S, G, ex, pp_case):
    if not figs.enabled():
        return
    base = draw_floor(grid, G)
    paths, adg = ex["paths"], ex["adg"]
    dead = [s for s in range(SEEDS) if AF.naive_execute(paths, DELAY, s)["deadlock"]]
    cyc_seeds = [s for s in dead if deadlock_kind(AF.naive_execute(paths, DELAY, s)) == "cycle"]
    seed = cyc_seeds[0] if cyc_seeds else dead[0]       # 閉路の例があればそれを見せる
    nv = AF.naive_execute(paths, DELAY, seed)
    ad = AF.adg_execute(adg, DELAY, seed)
    T = max(len(nv["trajectories"][0]), len(ad["trajectories"][0])) + 6
    cyc = wait_cycle(nv["waits_for"])
    frames = []
    for t in range(T):
        pn = [tr[min(t, len(tr) - 1)] for tr in nv["trajectories"]]
        pa = [tr[min(t, len(tr) - 1)] for tr in ad["trajectories"]]
        stuck = t >= len(nv["trajectories"][0]) - 1
        left = draw_state(base, pn, "素朴: 空いていれば進む" + ("  → デッドロック" if stuck else ""),
                          waits=nv["waits_for"] if stuck else (), cycle=cyc if stuck else ())
        right = draw_state(base, pa, "行動依存グラフ: 順番を守る" + ("  → 全台到着" if t >= len(ad["trajectories"][0]) - 1 else ""))
        sep = np.ones((left.shape[0], 8, 3))
        frames.append(np.concatenate([left, sep, right], axis=1))
    n_cyc, n_dead = ex["kinds"].get("cycle", 0), ex["naive_dead"]
    why = (("赤の矢印が「互いに相手を待つ」閉路 —— ただしこれは珍しい例で、%d 件のデッドロックのうち閉路は %d 件、"
            "残りは先に着いて居座った車が後から通るはずの車の道を塞ぐ封鎖" % (n_dead, n_cyc)) if cyc else
           "先に着いて居座った車が、後から通るはずの車の道を塞ぐ(計画では通る側が先に抜けるはずだった)")
    figs.save_video("agv_naive_vs_adg", frames, fps=4,
                    caption="同じ 12 台の計画・同じ遅れ(1 手ごとに 30 %%)。左は詰まる —— %s。右は全台が着く" % why)
    figs.save("agv_naive_vs_adg_still", frames[-1], caption="最後のコマ(左: デッドロック、右: 全台到着)")
    figs.save_plot("agv_deadlock_vs_delay",
                   [("素朴な実行", [r[0] for r in ex["rates"]], [r[1] for r in ex["rates"]]),
                    ("行動依存グラフ", [r[0] for r in ex["rates"]], [r[2] for r in ex["rates"]])],
                   xlabel="1 手ごとに遅れる確率", ylabel="デッドロックした割合(200 通り)",
                   title="計画は同じ。実行の約束だけが違う", kinds=["line", "line"],
                   caption="同じ 12 台の計画を、遅れの確率ごとに 200 通り走らせたデッドロックの割合。行動依存グラフはどの確率でも 0、"
                           "素朴な実行は遅れ 5 % ですでに 2 割を超える")
    if pp_case is not None:
        g2, S2, G2 = pp_case["grid"], pp_case["starts"], pp_case["goals"]
        b2 = draw_floor(g2, G2)
        cb = pp_case["cbs"]["paths"]
        T2 = max(len(p) for p in cb)
        fr2 = []
        for t in range(T2 + 3):
            pos = [p[min(t, len(p) - 1)] for p in cb]
            fr2.append(np.kron(draw_state(b2, pos, None), np.ones((3, 3, 1))))     # 小さいので 3 倍に
        figs.save_gif("agv_prioritized_counterexample", fr2, fps=2,
                      caption="優先度付き計画が、どちらを先にしても解けない問題(CBS の総コスト %d)。"
                              "CBS は片方に道を譲らせて解く" % pp_case["cbs"]["cost"])


def main():
    t0 = time.perf_counter()
    grid, S, G = scene()
    opt = section_optimality()
    pp = section_prioritized()
    ex = section_execution(grid, S, G)
    section_vda5050(ex["paths"])
    figures(grid, S, G, ex, pp)
    n_ok = sum(ok for _, ok in _GATES)
    print("\n== 結果: %d/%d 門, %.1f s" % (n_ok, len(_GATES), time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
        raise SystemExit(1)
    if n_ok != len(_GATES):
        raise SystemExit("FAIL: " + ", ".join(n for n, ok in _GATES if not ok))
    print("\nPASS")
    return {"optimality": opt, "execution": {k: ex[k] for k in ("rates", "naive_dead", "adg_ok")}}


if __name__ == "__main__":
    main()
