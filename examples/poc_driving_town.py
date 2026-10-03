# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""教習所の要素を自動で継いで町を 1 つに組み、1 本の通し走行を採点する —— 自動運転 PoC 系列の集大成の土台(2026-10-04)。

著者の発案: 「各 PoC 系列で 1 回ずつ集大成を作る。第 1 弾は運転」→ これまで要素ごとに置いて個別に採点してきた交差点・踏切・
坂道・縦列駐車を **1 本の道に継ぎ、入口から出口まで通して走り、途中の停止線を全部採点する**。学習は使わず、継ぐ規約・
縦の運転(IDM)・採点はどれも閉形式か既存 op の第 2 実装(drivetown)。ユーザー指摘で 2 つ足した: 「踏切の遮断機がないな」→
遮断機つき警報機・遮断かん・列車を置き、踏切の状態機械(drivecrossing)で「警報中なら上がるまで待つ」。「海外は交通ルールが
そもそも異なる」→ 法規パック(town_rules: JP / US / DE)で通行の側と踏切で止まる条件を切り替える(JP 以外は一次確認なし = 断定しない)。

何をするか:
  1. **継ぐ**: road(30) → 交差点 → road(20) → 踏切 → road(20) → 坂道 → road(20) → 縦列駐車 → road(30) を ``town_chain`` で
     自動配置(要素 k+1 の entry を要素 k の exit に、0.05 m 食い込ませる)。examples/poc_driving_school.py の私的な tf / ahead を
     公開 op にした物。
  2. **走る**: 中心線に沿う縦だけの運転。先の停止線を止まっている先行車と見なして IDM(drivetraffic.idm_accel)で減速、
     停止線の手前で止まり、交差点は 2 秒・踏切は左右確認 1 秒 × 2 往復の後に発進。列車があれば警報 → 降下 → 遮断 → 列車 → 上昇の
     状態機械(解釈基準の 15 + 20 s、crossing_timing_check で最小値を確認)が動き、警報が止んでかんが上がるまで待つ。
  3. **採点**: 停止位置・加速度・速度・∫v dt = s・停止回数・制動距離の定理、踏切は drivecrossing.crossing_stop_check を実際に呼ぶ、
     同じ指令を drivelong.long_simulate(RK4)に渡した第 2 実装と止まった位置が一致。警報中に踏切の中に居た時間 = 0。
  4. **法規パック**: JP(左・常に停止)/ US・DE(右・警報中だけ)で同じ町を走り、停止の回数と選ばれる停止線が変わる。
  5. **見る**: driveworld で 3-D 化し、車載カメラの通し走行(信号・遮断かん・列車・坂が映る)と俯瞰図・速度の図・法規の表・台帳の表。

門(どれも定理か第 2 実装):
  * 継ぎ目: 配置後の exit と次の entry の位置差 = overlap(1e-9)、向きの差 = 0(1e-9)。中心線の総延長 = Σ centerline_length −
    overlap × 継ぎ目数(直線の町は 1e-9、弧のある要素は 1e-3)。中心線: 直線部の標本間隔 = step、始点 = 最初の entry、終点 = 最後の exit。
  * 停止線: 走行車線の物だけ(交差点 4 本のうち 1 本 + 踏切 1 本)、位置は規格の寸法から閉形式(1e-9)。side を変えると交差点の
    停止線は交差点の中心について鏡像。
  * 走行: (a) 停止は停止線の 0〜1.0 m 手前 (b) |a| ≤ max(a_max, b_max)、0 ≤ v ≤ v_max (c) 台形則の ∫v dt と s の差 ≤ dt·v_max
    (d) 停止回数 = 目標の停止線の数 (e) 制動距離 ≥ v²/(2 b_max)(定理)。dt を 0.05 → 0.02 に細かくしても同じ。
  * 踏切: crossing_stop_check が ok。第 2 実装: 同じ IDM 指令を long_simulate(RK4、dt 0.01)に渡し、止まった位置の差 ≤ dt·v_max。
  * 列車: 時刻は解釈基準の最小を満たす(既存 op)、警報中に踏切の中に居た時間 0、発進は警報停止 + 上昇の後、crossing_stop_check が
    警報中の区間つきで ok。警報が間に合わない距離で始まれば進む = drivecrossing の unavoidable。
  * 法規: 既定(引数なし)= JP と同じ停止(回帰)、JP は 2 回・US / DE は(列車なし)1 回、US / DE でも警報中は踏切で止まる。
  * 台帳: 159 場面、reproduced ≥ 38、not_reproducible ≤ 10(tests/test_kyosoku_ledger.py の下限)。
  * 図の中身: 車載カメラの各コマは定数でなく、停止中のコマに信号機、遮断中のコマに下りた遮断かん(ラベル 4)と点いた警報灯、
    通過中のコマに列車(ラベル 6)、坂の手前のコマに斜面が映る(面の真値から)。

正直に: 横は中心線に貼り付け(縦だけ)、信号は「2 秒待てば青」の規則で灯火の色は読まない(閉ループの読みは poc_driving_school)。
他車・歩行者は置かない。IDM の停止は漸近的なので「止まった」は v ≤ v_stop で切り、停止位置は 0.5 m の余白の手前 ±数 cm。
US / DE の規則は二次情報(verified False)で、数字は JP の値の流用。右側通行でも白線・柱は JP の幾何のまま。警報から降下 7 s・
降下 8 s・上昇 6 s・列車 80 m・20 m/s は仮定。この PoC は教則の場面を名指ししない(台帳の件数表を出すだけ)。
Run: py -3.11 examples/poc_driving_town.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import drivecourse as DC  # noqa: E402
import drivetown as TW  # noqa: E402
import driveworld as DW  # noqa: E402
import examplefig as figs  # noqa: E402

_GATES = []
CAM_W, CAM_H, CAM_FOV = 640, 400, 60.0
EYE_BACK, EYE_H = 2.05, 1.35          # 運転者の目: 前端から 2.05 m 後ろ(poc_driving_crossing と同じ)、高さ 1.35 m
N_FRAMES = 12
T_WARN = 20.0                         # 列車の警報の始まり [s](車が踏切に着く 29.9 s の手前 → 着いたとき降下中)


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def ledger_path() -> Path:
    for p in (Path(__file__).resolve().parents[1] / "docs" / "drive" / "kyosoku_scenarios.json",
              Path.cwd() / "docs" / "drive" / "kyosoku_scenarios.json"):
        if p.is_file():
            return p
    raise SystemExit("FAIL: docs/drive/kyosoku_scenarios.json が見つからない")


def joint_errors(layout):
    ov = layout["chain"]["overlap"]
    dp = max(abs(math.hypot(ex[0] - en[0], ex[1] - en[1]) - ov) for ex, en in layout["chain"]["joints"])
    dy = max(abs(math.atan2(math.sin(ex[2] - en[2]), math.cos(ex[2] - en[2]))) for ex, en in layout["chain"]["joints"])
    return dp, dy


def second_implementation(run):
    """同じ IDM 指令を drivelong.long_simulate(RK4、事象で刻みを切る)に渡し、最初の停止までを積分する。"""
    import drivelong as DL
    import drivetraffic as DT
    p = run["params"]
    line = run["stop_lines"][0]["s"]

    def cmd(t, s, v):
        gap = line - s
        if gap <= 0:
            return 0.0, p["b_max"]
        vv = max(v, 0.0)
        a = DT.idm_accel(vv, gap, vv, v0=p["v_max"], T=p["idm_T"], a=p["a_max"], b=p["b_max"], s0=p["stop_margin"])
        a = min(p["a_max"], max(-p["b_max"], a))
        return max(a, 0.0), max(-a, 0.0)

    prm = DL.long_params(c_rr=0.0, cda=0.0, a_drive_max=p["a_max"], a_brake_max=p["b_max"], reaction=0.0, a_creep=0.0)
    return DL.long_simulate(0.0, 0.0, cmd, road=None, t_end=run["stops"][0][2], dt=0.01, params=prm)


def part_chain():
    print("== 1. 継ぐ(town_chain: 要素 k+1 の entry を要素 k の exit に、閉形式の剛体配置)")
    L = TW.town_layout()
    kinds = [e["kind"] for e in L["elements"]]
    print("  要素 %d: %s" % (len(kinds), " → ".join(kinds)))
    dp, dy = joint_errors(L)
    gate("継ぎ目 8 か所: exit と次の entry の位置差 = overlap(1e-9)、向きの差 = 0(1e-9)", dp <= 1e-9 and dy <= 1e-9,
         "位置 %.1e / 向き %.1e" % (dp, dy))
    ch = L["chain"]
    expect = ch["lengths"].sum() - ch["overlap"] * (len(kinds) - 1)
    gate("中心線の総延長 = Σ centerline_length − overlap × 8(直線の町は厳密)", abs(ch["total_length"] - expect) <= 1e-9,
         "%.4f m(差 %.1e)" % (ch["total_length"], abs(ch["total_length"] - expect)))
    curved = TW.town_chain([DC.course_road(10.0), DC.course_s_curve(), DC.course_road(10.0), DC.course_crank(), DC.course_loop_bend()],
                           start=(5.0, -3.0, 0.7))
    dpc, dyc = joint_errors(curved)
    ex2 = curved["chain"]["lengths"].sum() - 0.05 * 4
    rel = abs(curved["chain"]["total_length"] - ex2) / ex2
    gate("弧のある要素(S 字・クランク・半円)を継いでも継ぎ目は 1e-9、総延長は弧の折線近似ぶん(< 1e-3)だけ短い",
         dpc <= 1e-9 and dyc <= 1e-9 and rel < 1e-3 and curved["chain"]["total_length"] < ex2, "位置 %.1e / 相対差 %.1e" % (dpc, rel))
    C = TW.town_centerline(L, step=0.5)
    d = np.hypot(np.diff(C[:, 1]), np.diff(C[:, 2]))
    ends = max(np.abs(C[0, 1:] - L["elements"][0]["entry"]).max(), np.abs(C[-1, 1:3] - L["elements"][-1]["exit"][:2]).max())
    gate("中心線 %d 点: 標本間隔 = 0.5 m(最後の 1 区間だけ余り)、始点 = 最初の entry、終点 = 最後の exit" % len(C),
         np.allclose(d[:-1], 0.5, atol=1e-9) and d[-1] <= 0.5 + 1e-9 and ends <= 1e-9, "間隔のずれ %.1e / 端 %.1e" % (np.abs(d[:-1] - 0.5).max(), ends))
    st = TW.town_stop_lines(L)
    rt = TW.town_stop_lines(L, side="right")
    s_int = 30.0 - 0.05 + (23.5 - (3.5 + 3.0 + 4.0 + 2.0))
    s_crs = 30.0 + 47.0 + 20.0 - 3 * 0.05 + (7.3 - 1.3 - 0.5)
    centre = 30.0 - 0.05 + 23.5
    gate("停止線は走行車線の 2 本だけ(交差点 4 本のうち 1 本・踏切 1 本)、位置は規格の寸法から閉形式",
         [x["kind"] for x in st] == ["intersection", "crossing"] and abs(st[0]["s"] - s_int) <= 1e-9 and abs(st[1]["s"] - s_crs) <= 1e-9,
         "s = %.2f / %.2f m" % (st[0]["s"], st[1]["s"]))
    gate("side = right では交差点の停止線が交差点の中心について鏡像の 1 本(s_left + s_right = 2 × 中心)、踏切は同じ位置",
         abs(st[0]["s"] + rt[0]["s"] - 2 * centre) <= 1e-9 and rt[0]["s"] > st[0]["s"] and abs(rt[1]["s"] - st[1]["s"]) <= 1e-9,
         "右側通行の交差点の停止線 s = %.2f m(踏切の白線は JP の左車線だけ → drawn = %s)" % (rt[0]["s"], rt[1]["drawn"]))
    return L


def part_run(L):
    print("== 2. 走る(JP、縦だけ、IDM で停止線の手前に止まり、待って発進)と採点")
    runs = {dt: TW.town_run(L, dt=dt) for dt in (0.05, 0.02)}
    r = runs[0.05]
    p = r["params"]
    print("  通し %.1f m を %.1f s(dt %.2f、%d 刻み)、v_max %.0f m/s、a_max %.1f、b_max %.1f、規則 %s" % (
        r["total_length"], r["t"][-1], p["dt"], len(r["t"]), p["v_max"], p["a_max"], p["b_max"], p["jurisdiction"]))
    for (s_stop, kind, t_a, t_l) in r["stops"]:
        print("  停止 %-12s s = %.2f m、t = %.2f → %.2f s(%.1f s 待ち)" % (kind, s_stop, t_a, t_l, t_l - t_a))
    cks = {dt: TW.town_checks(rr, L) for dt, rr in runs.items()}
    ck = cks[0.05]
    before = [e["before"] for e in ck["stops"]]
    gate("(a) 停止位置は停止線の 0〜1.0 m 手前(2 本とも)", ck["count_ok"] and all(0 <= b <= 1.0 for b in before),
         "手前 %s m" % ", ".join("%.3f" % b for b in before))
    gate("(b) |a| ≤ max(a_max, b_max)、0 ≤ v ≤ v_max", np.max(np.abs(r["a"])) <= 3.0 + 1e-9 and 0 <= r["v"].min() and r["v"].max() <= 8.0 + 1e-9,
         "|a| 最大 %.3f、v 最大 %.3f" % (np.max(np.abs(r["a"])), r["v"].max()))
    gate("(c) 台形則の ∫v dt と s の差 ≤ dt·v_max(台形則で積分しているので実際は丸めまで)",
         ck["kinematics"]["integral_gap"] <= p["dt"] * p["v_max"] and ck["kinematics"]["integral_gap"] <= 1e-8, "%.1e m" % ck["kinematics"]["integral_gap"])
    gate("(d) 停止回数 = 目標の停止線の数(2)", ck["count_ok"] and len(r["stops"]) == 2)
    gate("(e) 制動距離 ≥ v²/(2 b_max)(定理: 減速度が b_max を超えないなら)", all(b["ok"] for b in ck["braking"]),
         "; ".join("%s: %.1f m ≥ %.1f m (v %.1f)" % (b["kind"], b["distance"], b["lower_bound"], b["v_brake"]) for b in ck["braking"]))
    gate("dt を 0.02 に細かくしても (a)〜(e) が全部通る", cks[0.02]["ok"], "手前 %s m" % ", ".join("%.3f" % e["before"] for e in cks[0.02]["stops"]))
    cx = ck["stops"][1]["crossing"]
    gate("踏切: drivecrossing.crossing_stop_check が ok(止まった・左右を見た・中で止まらない・進入した)",
         cx["ok"] and cx["entered"] and cx["looked"] == ["left", "right"], "違反 %s、見た %s、進入 t = %.2f s" % (cx["violations"], cx["looked"], cx["t_entry"]))
    res = second_implementation(r)
    s_stop = r["stops"][0][0]
    diff_end = abs(float(res["s"][-1]) - s_stop)
    diff_all = float(np.max(np.abs(np.interp(res["t"], r["t"], r["s"]) - res["s"])))
    gate("第 2 実装: 同じ IDM 指令を long_simulate(RK4、dt 0.01)に渡すと、止まった位置の差 ≤ dt·v_max",
         diff_end <= p["dt"] * p["v_max"] and diff_all <= p["dt"] * p["v_max"], "停止位置の差 %.3f m、軌跡の最大差 %.3f m(許容 %.2f)" % (diff_end, diff_all, p["dt"] * p["v_max"]))
    gate("採点の総合 ok(town_checks)", ck["ok"])
    return r, ck


def part_train(L, r0):
    print("== 2b. 列車(警報 %.0f s に開始): 着いたとき降下中 → 遮断かんが上がって警報が止むまで待ってから渡る" % T_WARN)
    r = TW.town_run(L, train=T_WARN)
    ck = TW.town_checks(r, L)
    TR = r["train"]
    tc = TR["timing_check"]
    print("  時刻: 警報 %.0f → 降下 %.0f〜%.0f(遮断)→ 列車到達 %.0f → 通過 %.2f → 上昇完了 %.2f s(列車 %.0f m・%.0f m/s)" % (
        TR["t_warning"], TR["t_lower_start"], TR["t_closed"], TR["t_arrival"], TR["t_clear"], TR["forbidden_interval"][1], TR["length"], TR["v_train"]))
    for (s_stop, kind, t_a, t_l) in r["stops"]:
        print("  停止 %-12s s = %.2f m、t = %.2f → %.2f s(%.1f s 待ち)" % (kind, s_stop, t_a, t_l, t_l - t_a))
    gate("時刻は解釈基準の最小を満たす(crossing_timing_check: 警報→遮断 %.0f s ≥ 10、遮断→到達 %.0f s ≥ 15)" % (tc["warn_to_closed"], tc["closed_to_arrival"]),
         tc["meets_minimum"] and ck["train"]["timing_meets_minimum"])
    go = [ev for ev in r["events"] if ev[0] == "go" and ev[3] == "crossing"][0]
    gate("発進は警報停止 + 上昇の後(go %.2f s ≥ %.2f s)、待ちの mode 'wait' と event 'wait_gate' がある" % (go[1], TR["forbidden_interval"][1]),
         ck["train"]["go_after_clear"] and "wait" in set(r["mode"]) and any(ev[0] == "wait_gate" for ev in r["events"]),
         "待ち %.1f s(確認 4 s を含む)" % (r["stops"][1][3] - r["stops"][1][2]))
    gate("警報中(降下〜上昇)に車体が踏切面にかかっていた時間 = 0", ck["train"]["inside_while_forbidden_s"] == 0.0,
         "%.3f s" % ck["train"]["inside_while_forbidden_s"])
    cx = ck["stops"][1]["crossing"]
    gate("crossing_stop_check(警報中の区間つき)が ok、進入 t = %.2f s は区間の外" % cx["t_entry"], cx["ok"] and cx["t_entry"] > TR["forbidden_interval"][1],
         "違反 %s" % cx["violations"])
    gate("列車なしの走行と、踏切に着くまでは同じ(停止線の位置・到着時刻が一致)", r0["stops"][0] == r["stops"][0] and r0["stops"][1][:3] == r["stops"][1][:3])
    gate("採点の総合 ok(列車つき)", ck["ok"])
    return r, ck


def part_rules(L):
    print("== 5. 法規パック(town_rules): 同じ町を JP / US / DE で走る(US / DE は一次確認なし = verified False)")
    rows, res = [], {}
    r_free = TW.town_run(L, rules=TW.town_rules("US"))
    s_line = r_free["stop_lines"][1]["s"]
    t_late = float(np.interp(s_line - 4.0, r_free["s"], r_free["t"]))
    for j in ("JP", "US", "DE"):
        R = TW.town_rules(j)
        for label, tr in (("列車なし", None), ("警報 %.0f s" % T_WARN, T_WARN), ("警報が 4 m 手前で開始", t_late)):
            r = TW.town_run(L, rules=R, train=tr)
            ck = TW.town_checks(r, L)
            res[(j, label)] = (r, ck)
            kinds = [k for _, k, *_ in r["stops"]]
            evs = sorted({ev[0] for ev in r["events"] if ev[0] in ("commit", "pass", "wait_gate")})
            rows.append([j, R["side"], R["crossing_stop"], label, "%d" % len(kinds), "+".join(kinds) or "-",
                         "%.2f" % r["stop_lines"][0]["s"], "%.1f" % r["t"][-1], ",".join(evs) or "-", "ok" if ck["ok"] else "NG",
                         "yes" if R["verified"] else "no"])
    hdr = ["規則", "側", "踏切", "列車", "停止", "どこで", "交差点の停止線 s", "所要 [s]", "事象", "採点", "一次確認"]
    for row in rows:
        print("  " + " | ".join("%s=%s" % (h, v) for h, v in zip(hdr, row)))
    r_def = TW.town_run(L)
    gate("既定(引数なし)= town_rules('JP') と同じ停止(回帰)", r_def["stops"] == res[("JP", "列車なし")][0]["stops"] and r_def["params"]["jurisdiction"] == "JP")
    gate("JP は 2 回(交差点 + 踏切)、US / DE は列車なしで 1 回(踏切は止まらず通過 = pass)",
         [k for _, k, *_ in res[("JP", "列車なし")][0]["stops"]] == ["intersection", "crossing"]
         and all([k for _, k, *_ in res[(j, "列車なし")][0]["stops"]] == ["intersection"] for j in ("US", "DE")))
    gate("side = right では鏡像の停止線(s = %.2f)に止まり、左では s = %.2f" % (res[("US", "列車なし")][0]["stop_lines"][0]["s"], res[("JP", "列車なし")][0]["stop_lines"][0]["s"]),
         abs(res[("US", "列車なし")][0]["stops"][0][0] - res[("JP", "列車なし")][0]["stops"][0][0] - 25.0) < 0.05)
    gate("US / DE でも警報中は踏切で止まり、上がるまで待つ(2 回停止、確認の look は無い)",
         all([k for _, k, *_ in res[(j, "警報 %.0f s" % T_WARN)][0]["stops"]] == ["intersection", "crossing"]
             and res[(j, "警報 %.0f s" % T_WARN)][1]["ok"] and not any(ev[0] == "look" for ev in res[(j, "警報 %.0f s" % T_WARN)][0]["events"])
             for j in ("US", "DE")))
    late_us = res[("US", "警報が 4 m 手前で開始")]
    cx = late_us[1]["stops"][1]["crossing"]
    gate("US で警報が止まれない距離(4 m < v²/2b = %.1f m)で始まれば進む(commit)、drivecrossing は unavoidable で違反に数えない" % (8.0 ** 2 / 6.0),
         any(ev[0] == "commit" for ev in late_us[0]["events"]) and cx["unavoidable"] and cx["ok"] and late_us[1]["ok"])
    late_jp = res[("JP", "警報が 4 m 手前で開始")]
    gate("JP は同じ警報でも常に停止するので、着いてから上がるまで待つ(違反なし)",
         [k for _, k, *_ in late_jp[0]["stops"]] == ["intersection", "crossing"] and late_jp[1]["ok"] and late_jp[1]["train"]["inside_while_forbidden_s"] == 0.0)
    gate("採点は 9 通り全部 ok", all(ck["ok"] for _, ck in res.values()))
    return hdr, rows


def ground_z(L, s):
    return float(TW._ground_z(L, np.asarray([s]))[0])


def camera_at(L, s_front):
    """前端の弧長 s_front の車の運転者の目からのカメラ(前端の 2.05 m 後ろ、高さ 1.35 m、約 19 m 先の路面の 0.9 m 上を見る)。"""
    P, c = TW._chain_polyline(L)
    s_e = max(0.0, s_front - EYE_BACK)
    s_t = min(L["chain"]["total_length"], s_front + 17.0)
    e = TW._point_at(P, c, s_e)
    tg = TW._point_at(P, c, s_t)
    return DW.camera_pose((e[0], e[1], ground_z(L, s_e) + EYE_H), (tg[0], tg[1], ground_z(L, s_t) + 0.9))


def part_world(L, r):
    print("== 3. 3-D の世界と車載カメラ(列車つきの JP 走行。信号は停止線を離れるときに青へ、踏切の設備は状態機械で)")
    t0 = time.perf_counter()
    # 路面の格子は 2 m: 描画器はカメラの背後に頂点を持つ三角形を落とすので、4 m だと足元の升ごと消えて画面の下が空になる
    W = TW.town_world(L, ground_step=2.0)
    tbl = W["town"]
    g = tbl["gear"][0]
    print("  面 %d、停止線 %d、信号 %d 基、踏切 %d(柱 %d・遮断かん %d・警報灯 %d・列車 1)、全長 %.1f m(%.2f s)" % (
        len(W["F"]), len(tbl["stop_lines"]), len(tbl["signals"]), len(tbl["crossings"]), len(g["posts"]), len(g["booms"]), len(g["lamps"]),
        tbl["total_length"], time.perf_counter() - t0))
    gate("world['town'] の表: 停止線 2・信号 4・踏切 1(遮断かん 2・警報灯 8)、停止線の位置は town_stop_lines と同じ",
         len(tbl["stop_lines"]) == 2 and len(tbl["signals"]) == 4 and len(tbl["crossings"]) == 1 and len(g["booms"]) == 2 and len(g["lamps"]) == 8
         and all(abs(a[0] - b["x"]) < 1e-9 for a, b in zip(tbl["stop_lines"], TW.town_stop_lines(L))))
    sig_pose = [sg for sg in tbl["signals"] if abs(math.atan2(math.sin(sg[2] - math.pi), math.cos(sg[2] - math.pi))) < 1e-6][0]
    idx = [i for i, o in enumerate(W["objects"]) if o.get("name") == "traffic_light"
           and abs(o["pose"][0] - sig_pose[0]) < 1e-6 and abs(o["pose"][1] - sig_pose[1]) < 1e-6][0]
    ramp = [o for o in W["objects"] if o.get("name") == "ramp"][0]["faces"]
    rails = [o["faces"] for o in W["objects"] if o.get("name") == "rail"]
    booms = [W["objects"][i]["faces"] for i, *_ in g["booms"]]
    train_f = W["objects"][g["train"]]["faces"]
    lamp_f = [f for f, _ in g["lamps"]]
    K = DW.camera_intrinsics(CAM_FOV, CAM_W, CAM_H)
    TR = r["train"]
    t_leave_int = [st for st in r["stops"] if st[1] == "intersection"][0][3]
    st_cross = [st for st in r["stops"] if st[1] == "crossing"][0]
    i_slope_el = [e["kind"] for e in L["elements"]].index("slope")
    # コマの時刻: 走行を等間隔に割り、信号待ち・遮断中(かん下)・列車通過・上昇後の発進・坂の手前を必ず入れる
    t_pick = list(np.linspace(0.0, r["t"][-1], N_FRAMES - 4))
    t_int_stop = [st for st in r["stops"] if st[1] == "intersection"][0][2] + 0.5
    t_closed = TR["t_closed"] + 2.0
    t_train = TR["t_arrival"] + 1.2
    t_go = st_cross[3] + 0.3
    t_slope = float(np.interp(L["chain"]["s_start"][i_slope_el] - 2.0, r["s"], r["t"]))
    t_pick = sorted(t_pick + [t_int_stop, t_closed, t_train, t_go, t_slope])
    frames, infos, seen = [], [], set()
    t0 = time.perf_counter()
    for tp in t_pick:
        i = int(np.argmin(np.abs(r["t"] - tp)))
        tt = float(r["t"][i])
        DW.set_signal_state(W, idx, "green" if tt >= t_leave_int - 1e-9 else "red")
        st = TW.town_crossing_state(W, tt, TR, exposure=0.5 / 30.0)
        key = (round(float(r["s"][i]), 2), bool(tt >= t_leave_int - 1e-9), st["state_name"], round(float(st["train_y"]), 0))
        if key in seen:
            continue
        seen.add(key)
        cam = DW.world_camera(W, camera_at(L, float(r["s"][i])), K, CAM_W, CAM_H)
        frames.append(cam["color"])
        face = cam["face"]
        cnt = lambda ranges: int(sum(np.sum((face >= f0) & (face < f1)) for f0, f1 in ranges))  # noqa: E731
        lit = max((float(W["face_color"][f0:f1, 0].max()) for f0, f1 in lamp_f), default=0.0)
        infos.append({"t": tt, "s": float(r["s"][i]), "v": float(r["v"][i]), "mode": str(r["mode"][i]),
                      "std": float(cam["color"].std()), "signal": int(np.sum(cam["label"] == 3)),
                      "sky_bottom": int(np.sum(cam["label"][CAM_H * 3 // 4:] == -1)),
                      "rail": cnt(rails), "ramp": cnt([ramp]), "boom": cnt(booms), "train": cnt([train_f]), "lamp_px": cnt(lamp_f),
                      "gate": st["state_name"], "boom_angle": st["boom_angle"], "lamp_lit": lit, "state": W["objects"][idx]["state"]})
    print("  車載カメラ %d コマ(%d×%d)を %.2f s で描いた" % (len(frames), CAM_W, CAM_H, time.perf_counter() - t0))
    for inf in infos:
        print("    t %5.1f s  s %6.1f m  v %4.1f  %-6s 信号 %-5s 踏切 %-8s かん %.2f  std %.3f  画素: 信号機 %4d  遮断かん %4d  警報灯 %3d  列車 %5d  レール %4d  斜面 %5d" % (
            inf["t"], inf["s"], inf["v"], inf["mode"], inf["state"], inf["gate"], inf["boom_angle"], inf["std"], inf["signal"], inf["boom"],
            inf["lamp_px"], inf["train"], inf["rail"], inf["ramp"]))
    pick = lambda tp: int(np.argmin([abs(inf["t"] - tp) for inf in infos]))  # noqa: E731
    i_stop, i_closed, i_train, i_go, i_slope = pick(t_int_stop), pick(t_closed), pick(t_train), pick(t_go), pick(t_slope)
    gate("車載カメラの %d コマ(≥ 8)はどれも定数でなく(std > 0.05)、画面の下 1/4 に空が無い(足元まで路面が映る)" % len(frames),
         len(frames) >= 8 and all(inf["std"] > 0.05 and inf["sky_bottom"] == 0 for inf in infos),
         "std 最小 %.3f、下 1/4 の空の画素 最大 %d" % (min(inf["std"] for inf in infos), max(inf["sky_bottom"] for inf in infos)))
    gate("信号待ちのコマに信号機(ラベル 3)が映り灯火は赤、発進後のコマは青",
         infos[i_stop]["signal"] > 20 and infos[i_stop]["state"] == "red" and infos[i_stop]["mode"] == "hold"
         and any(inf["state"] == "green" and inf["t"] > t_leave_int for inf in infos), "信号機の画素 %d" % infos[i_stop]["signal"])
    gate("遮断中のコマ(t %.1f s)に下りた遮断かん(ラベル 4、かんの角 0)の面が映り、警報灯の面が点いている(R ≥ 0.9)" % infos[i_closed]["t"],
         infos[i_closed]["gate"] == "closed" and infos[i_closed]["boom"] > 100 and infos[i_closed]["boom_angle"] == 0.0 and infos[i_closed]["lamp_lit"] >= 0.9,
         "遮断かんの画素 %d、警報灯の画素 %d、灯の R %.2f" % (infos[i_closed]["boom"], infos[i_closed]["lamp_px"], infos[i_closed]["lamp_lit"]))
    gate("列車の通過中のコマ(t %.1f s)に列車(ラベル 6)が映る" % infos[i_train]["t"], infos[i_train]["train"] > 1000, "列車の画素 %d" % infos[i_train]["train"])
    gate("発進後のコマ(t %.1f s)は上昇済み(idle、かん上)で、遮断かんの面は水平の時より少ない" % infos[i_go]["t"],
         infos[i_go]["gate"] == "idle" and infos[i_go]["boom"] < infos[i_closed]["boom"], "遮断かんの画素 %d(遮断中 %d)" % (infos[i_go]["boom"], infos[i_closed]["boom"]))
    gate("踏切の手前のコマにレールの面が映る", infos[i_closed]["rail"] > 0, "レールの画素 %d" % infos[i_closed]["rail"])
    gate("坂道の手前のコマに斜面の面(ramp)が映る(画素 > 500、面の真値から)", infos[i_slope]["ramp"] > 500,
         "斜面の画素 %d(坂の上のコマは描画器が大きな三角形を落とすので斜面が消える: driveworld の限界)" % infos[i_slope]["ramp"])
    return W, frames, infos, (i_stop, i_closed, i_train, i_go, i_slope)


def part_ledger():
    print("== 4. 教則の場面の台帳(category × status)")
    S = TW.kyosoku_summary(ledger_path())
    bs = S["by_status"]
    print("  %d 場面: %s" % (S["total"], ", ".join("%s %d" % kv for kv in bs.items())))
    gate("台帳 159 場面、reproduced ≥ 38、not_reproducible ≤ 10(tests/test_kyosoku_ledger.py の下限と整合)",
         S["total"] == 159 and bs["reproduced"] >= 38 and bs["not_reproducible"] <= 10 and sum(bs.values()) == 159)
    gate("表の行の合計 = 159(category の数 %d)" % len(S["categories"]), sum(row[-1] for row in S["table"]) == 159)
    return S


def make_figures(L, r, ck, W, frames, infos, picks, S, rules_table):
    if not figs.enabled():
        return
    # (1) 俯瞰図
    series, kinds, styles, colors = [], [], [], []
    for k, e in enumerate(L["elements"]):
        P = np.vstack([e["polygon"], e["polygon"][:1]])
        series.append(("要素の多角形" if k == 0 else "", P[:, 0], P[:, 1])); kinds.append("line"); styles.append(None); colors.append("neutral")
    C = TW.town_centerline(L, 0.5)
    series.append(("中心線", C[:, 1], C[:, 2])); kinds.append("line"); styles.append("dashed"); colors.append("reference")
    for k, e in enumerate(L["elements"]):
        for seg in np.asarray(e.get("stop_lines", np.zeros((0, 2, 2)))).reshape(-1, 2, 2):
            series.append(("停止線(全部)" if not any(lbl == "停止線(全部)" for lbl, *_ in series) else "", seg[:, 0], seg[:, 1]))
            kinds.append("line"); styles.append(None); colors.append("emphasis")
    series.append(("走行軌跡(前端)", r["x"], r["y"])); kinds.append("line"); styles.append("dotted"); colors.append("right")
    sx = np.array([st[0] for st in r["stops"]]); sy = np.interp(sx, r["s"], r["y"])
    series.append(("止まった位置", sx, sy)); kinds.append("scatter"); styles.append(None); colors.append("wrong")
    sg = np.array(W["town"]["signals"])
    series.append(("信号機", sg[:, 0], sg[:, 1])); kinds.append("scatter"); styles.append(None); colors.append("emphasis")
    posts = np.array([W["objects"][i]["pose"] if W["objects"][i]["pose"] else (0, 0, 0) for i in W["town"]["gear"][0]["posts"]])
    gp = np.array([TW._to_world3(np.array([[px, py, 0.0]]), W["town"]["gear"][0]["placement"])[0, :2]
                   for px, py in ((W["town"]["gear"][0]["zone"][0] - 0.3, 4.0), (W["town"]["gear"][0]["zone"][1] + 0.3, -4.0))])
    series.append(("遮断機", gp[:, 0], gp[:, 1])); kinds.append("scatter"); styles.append(None); colors.append("wrong")
    del posts
    figs.save_plot("town_overview", series, xlabel="x [m]", ylabel="y [m]", title="町の俯瞰図: 9 要素を自動で継いだ 1 本の道(全長 %.1f m)" % r["total_length"],
                   size=(1600, 420), aspect="equal", kinds=kinds, styles=styles, colors=colors,
                   caption="road → 交差点 → road → 踏切 → road → 坂道 → road → 縦列駐車 → road を town_chain で継いだ町(縮尺は等倍)。停止線は交差点 4 本と踏切 1 本の全部を描き、"
                           "走行路の 2 本の手前に止まった位置(手前 %s m)と遮断機の柱 2 本を印にした。" % ", ".join("%.2f" % e["before"] for e in ck["stops"]))
    # (2) 速度・加速度(列車つき)
    TR = r["train"]
    vlines = []
    for (s_stop, kind, t_a, t_l) in r["stops"]:
        vlines += [("停止 %s" % kind, np.array([t_a, t_a]), np.array([-3.0, 8.0])), ("", np.array([t_l, t_l]), np.array([-3.0, 8.0]))]
    band = [("警報〜上昇完了 [%.0f, %.1f] s" % TR["forbidden_interval"], np.array(TR["forbidden_interval"]), np.array([-3.0, -3.0])),
            ("列車が踏切に [%.0f, %.1f] s" % (TR["t_arrival"], TR["t_clear"]), np.array([TR["t_arrival"], TR["t_clear"]]), np.array([-2.6, -2.6]))]
    figs.save_plot("town_speed_time", [("速度 v [m/s]", r["t"], r["v"]), ("加速度 a [m/s²]", r["t"], r["a"])] + vlines + band,
                   xlabel="t [s]", ylabel="v [m/s] / a [m/s²]", title="通し走行の速度と加速度(列車あり: 踏切で警報が止むまで待つ)",
                   kinds=["line", "line"] + ["line"] * (len(vlines) + 2), styles=[None, None] + ["dashed"] * len(vlines) + [None, None],
                   colors=["right", "neutral"] + ["emphasis", "emphasis"] * len(r["stops"]) + ["wrong", "reference"], size=(1200, 400),
                   caption="IDM(a_max 1.5、b_max 3.0、v_max 8)で停止線の手前に止まる。交差点は 2 秒。踏切は左右確認 4 秒の後、警報 %.0f s に始まった状態機械"
                           "(降下 → 遮断 → 列車 → 上昇)が idle に戻る %.1f s まで待って発進。下の帯 = 警報中の区間と列車が踏切に居る区間。|a| の最大 %.2f m/s²。"
                           % (TR["t_warning"], TR["forbidden_interval"][1], np.max(np.abs(r["a"]))))
    slines = [("停止線 %s" % st["kind"], np.array([st["s"], st["s"]]), np.array([0.0, 8.0])) for st in TW.town_stop_lines(L)]
    figs.save_plot("town_speed_distance", [("速度 v [m/s]", r["s"], r["v"])] + slines, xlabel="s [m](前端の弧長)", ylabel="v [m/s]",
                   title="速度と道のり(縦線 = 停止線の位置)", kinds=["line"] + ["line"] * len(slines), styles=[None] + ["dashed"] * len(slines),
                   colors=["right"] + ["emphasis"] * len(slines), size=(1100, 360),
                   caption="止まった位置は停止線の %s m 手前。制動距離 %s m(定理の下限 %s m)。" % (
                       ", ".join("%.2f" % e["before"] for e in ck["stops"]), ", ".join("%.1f" % b["distance"] for b in ck["braking"]),
                       ", ".join("%.1f" % b["lower_bound"] for b in ck["braking"])))
    # (3) 車載カメラ
    figs.save_gif("town_drive_through", frames, fps=2.0,
                  caption="車載カメラ(%d×%d、%d コマ)で町を通し走行。赤信号で止まり、青で発進、踏切で止まって左右を見て、下りた遮断かんと点滅する警報灯の前で"
                          "列車が過ぎて上がるまで待ってから渡り、坂を越えて縦列駐車の前を抜ける。" % (CAM_W, CAM_H, len(frames)))
    i_stop, i_closed, i_train, i_go, i_slope = picks
    i_green = next(i for i, inf in enumerate(infos) if inf["state"] == "green")
    figs.save_grid("town_camera_frames", [frames[i_stop], frames[i_green], frames[i_closed], frames[i_train], frames[i_go], frames[i_slope]],
                   ["赤信号で停止(t %.1f s)" % infos[i_stop]["t"], "青で発進(t %.1f s)" % infos[i_green]["t"],
                    "踏切: 遮断中(t %.1f s)" % infos[i_closed]["t"], "踏切: 列車の通過(t %.1f s)" % infos[i_train]["t"],
                    "踏切: 上がって発進(t %.1f s)" % infos[i_go]["t"], "坂道の手前(t %.1f s)" % infos[i_slope]["t"]],
                   ncols=3, caption="GIF の 6 コマ(静止画)。面の真値から数えた画素: 信号機 %d、遮断かん %d(遮断中)、列車 %d、斜面 %d。遮断かんの黄黒と警報灯の赤は"
                                    "drivecrossing の状態機械(crossing_gate_state / crossing_lamp_signal)の値で描いている。" % (
                       infos[i_stop]["signal"], infos[i_closed]["boom"], infos[i_train]["train"], infos[i_slope]["ramp"]))
    # (4) 法規パックの表
    hdr, rows = rules_table
    figs.save_table("town_rules_table", hdr, rows, title="法規パックで同じ町の走り方が変わる(JP / US / DE × 列車なし・警報 20 s・間に合わない警報)",
                    caption="JP = 左側通行・踏切は常に停止 + 左右確認(道路交通法 33 条 1 項、本文で確認)。US / DE = 右側通行・警報中だけ停止"
                            "(二次情報、一次確認 = no → 数字・規則を断定しない。保持 2 s は JP の流用)。交差点の停止線は side で鏡像の 1 本になる。"
                            "事象: pass = 止まらず通過、wait_gate = 上がるまで待った、commit = 止まれない距離で警報が始まり進んだ(drivecrossing の unavoidable)。")
    # (5) 台帳
    header = ["category"] + list(S["statuses"]) + ["合計"]
    rows2 = [[row[0]] + ["%d" % v for v in row[1:]] for row in S["table"]]
    rows2.append(["合計"] + ["%d" % S["by_status"][st] for st in S["statuses"]] + ["%d" % S["total"]])
    figs.save_table("town_kyosoku_table", header, rows2, title="教則の場面の再現台帳(category × status、%d 場面)" % S["total"],
                    caption="docs/drive/kyosoku_scenarios.json の件数。reproduced %d / partial %d / pending %d / not_reproducible %d。" % tuple(S["by_status"][st] for st in S["statuses"]))


def main():
    t0 = time.perf_counter()
    L = part_chain()
    r0, ck0 = part_run(L)
    r, ck = part_train(L, r0)
    W, frames, infos, picks = part_world(L, r)
    S = part_ledger()
    rules_table = part_rules(L)
    make_figures(L, r, ck, W, frames, infos, picks, S, rules_table)
    n_ok = sum(ok for _, ok in _GATES)
    print("\n== 結果: %d/%d 門, %.1f s" % (n_ok, len(_GATES), time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
        raise SystemExit("FAIL: figures")
    if n_ok != len(_GATES):
        raise SystemExit("FAIL: " + ", ".join(n for n, ok in _GATES if not ok))
    print("\nPASS")


if __name__ == "__main__":
    main()
