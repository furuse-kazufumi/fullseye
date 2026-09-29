# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ⑰: 衝突までの時間と安全距離 —— τ 理論の光学流と RSS の閉形式を、教習所の世界の真値で採点する。

対向車が近づいてくる。あと何秒でぶつかるか(τ、Lee 1976)は、距離も速度も知らずに **像が広がる速さ** だけで
分かる —— というのが τ 理論で、ハエもヒトもこれで制動する。一方、ぶつからないために **何 m 空けるべきか** は
Mobileye の RSS(Shalev-Shwartz ら 2017)が応答時間と加減速の上限から閉形式で与える。この PoC は 14 巡目に開校した
教習所の周回コース(直線 80 m・幅 8 m、左側通行)で、自車(8 m/s)の対向車線を同じ速さで来る車を車載カメラで撮り、
**世界の側の真値**(深度像・姿勢・速度)で両方を採点する。

τ を 3 つの経路で出す(:mod:`drivettc`):
  真値 = 深度像と 2 コマの間の剛体運動から画素ごとに閉形式(τ₀ = Z₀Δt/(Z₀−Z₁))。
  流れから = 光学流(:func:`flow.optical_flow_lk`)→ :func:`sceneflow.time_to_contact`(FoE からの半径 / 半径方向の流れ)。
  大きさから = 対向車の見かけの面積 n から τ₀ = Δt / (1 − √(n₀/n₁))。
安全距離は :mod:`rsssafety`(閉形式 + 最悪ケースの時間積分が第 2 実装、公表値は ad-rss-lib のパラメータ表と試験の期待値)。

門(真値の出どころ):
  1. **恒等式**: 純並進では、真の流れを time_to_contact に入れた値は「1 コマ後の τ」で、1 コマ足すと真の τ₀ と 1e-9 で一致(全コマ・全画素)。
  2. **dτ/dt = −1**: 対向車の最も近い画素の真の τ は、姿勢から出す閉形式(距離 / 閉じる速さ)と一致し、1 秒に 1 秒ずつ減る。
  3. **流れの τ**: 対向車の画素の光学流(LK、5 段)から出した τ の真値との相対差 —— 車が像で十分大きい区間の中央値で門、
     遠い区間(流れがサブピクセル)と直前(流れが数十画素)は正直に数字を出す。
  4. **大きさの τ**: 面積の平方根の変化(コマ間隔 0.5 s)から出した τ が真値と 10 % 以内で、量子化の許容区間(面積 ±周長/2 画素)に入る。
  5. **RSS の公表値**: ad-rss-lib のパラメータ表と横方向の試験の期待値(5 点)、50 km/h の同方向で ≈ 40 m / ≈ 80 m。
  6. **RSS の Lemma 2 は積分と一致**: 最悪ケース(先行が急制動、後続は応答時間だけ加速して減速)を時間積分した最小間隔が
     d₀ − d_min と 1e-6 で一致、d₀ = d_min でちょうど 0。
  7. **教習所で止まる**: 前方の停車車両に RSS が「危険」を出した瞬間に proper response(応答時間は速度維持、その後 4 m/s² で制動)
     すると、停止時の間隔が閉形式 gap(t_b) − (vρ + v²/2b) と 1e-9 で一致し、正である。
  8. **τ は騒ぎ、RSS は騒がない**: 対向車線の車は τ が 0.3 s まで落ちるが、横の安全距離(0.73 m)は車線の間隔(2.2 m)より小さく、
     RSS は一度も「危険」を出さない。対向車が横へ 0.6 m/s で寄ってくると横が危険になり、そのとき縦はもう安全距離(83 m)の中で、
     最悪ケースの積分は衝突する(閉形式と一致)—— RSS ではこの衝突の責任は寄ってきた側にある。

正直に書くこと: 光学流の τ が効くのは流れが 1〜十数画素のときで、遠い(サブピクセル)と近すぎる(ピラミッドの外)は外れる。
真の FoE を与えている(自車の運動は既知とした)。対向車の画素の切り出しは世界の面 id(完全な検出器の代役)。

Run: py -3.11 examples/poc_ttc_rss.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import drivecourse as DC  # noqa: E402
import driveworld as DW  # noqa: E402
import drivettc as TT  # noqa: E402
import rsssafety as RS  # noqa: E402
import flow as FL  # noqa: E402
import sceneflow as SF  # noqa: E402
import annotate as AN  # noqa: E402

T0 = time.time()
CAR = (4.5, 1.8, 1.0)                 # 車体 (長さ, 幅, 後軸から後端)
LOOP_R, LOOP_S, LOOP_W = 30.0, 80.0, 8.0
Y_EGO, Y_ONC = -LOOP_R + 2.0, -LOOP_R - 2.0     # 南の直線: 東行きは北側(左側通行)、西行きは南側
V_EGO = V_ONC = 8.0                   # 28.8 km/h(教習所の速さ)
DT = 0.1
X_STOP = 40.0                         # 前方に停まっている車(自車線)
CAM_FWD, CAM_H = 1.0, 1.35
OK = []


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def ahead(pose, d):
    x, y, yaw = pose
    return (x + d * math.cos(yaw), y + d * math.sin(yaw), yaw)


def cam_pose(pose):
    x, y, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    return DW.camera_pose((x + CAM_FWD * c, y + CAM_FWD * s, CAM_H), (x + 20.0 * c, y + 20.0 * s, 0.9))


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    # ─────────────────────────────── 1. 世界 ─────────────────────────────
    print("== 1. 教習所の周回コース(14 巡目)の南の直線に、自車・対向車・停車車両を置く")
    LOOP = DC.course_loop(LOOP_S, LOOP_R, LOOP_W)
    LAYOUT = DC.course_layout(LOOP["elements"], LOOP["placements"])
    WORLD = DW.world_build(LAYOUT, props=[("sedan", X_STOP, Y_EGO, 0.0), ("street_light", -20.0, -25.0, -math.pi / 2),
                                          ("street_light", 10.0, -25.0, -math.pi / 2),        # 街灯の腕は南の直線(y = −30)の側へ
                                          ("suv", -20.0, LOOP_R - 2.0, math.pi, None, "white"),
                                          ("truck", 25.0, LOOP_R + 2.0, 0.0, None, "silver")])   # 左側通行: 北の直線は内側(y = 28)が西行き、外側(y = 32)が東行き
    ONC = DW.add_asset(WORLD, "taxi", 40.0, Y_ONC, math.pi)
    EGO = DW.load_asset("sedan")
    K = DW.camera_intrinsics(60.0, 640, 400)
    f_onc = WORLD["objects"][ONC]["faces"]
    print("  三角形 %d, 物体 %d。自車 x = −40 → 東へ %.0f m/s、対向車 x = 40 → 西へ %.0f m/s(横の間隔 %.1f m = 車線 4 m − 車幅 1.8 m)、"
          "停車車両 x = %.0f" % (len(WORLD["F"]), len(WORLD["objects"]), V_EGO, V_ONC, 4.0 - CAR[1], X_STOP))

    def ego_pose(t):
        return (-40.0 + V_EGO * t, Y_EGO, 0.0)

    def onc_x(t):
        return 40.0 - V_ONC * t

    def ego_mesh(pose):
        return DW.place_mesh(EGO["V"], *ahead(pose, CAR[0] / 2 - CAR[2]))

    def set_scene(t):
        DW.world_move(WORLD, ONC, onc_x(t), Y_ONC, math.pi)

    def render(t, width=640, height=400, Kc=None, with_ego=False):
        set_scene(t)
        P = cam_pose(ego_pose(t))
        ego = (ego_mesh(ego_pose(t)), EGO["F"], EGO["color"]) if with_ego else None
        return DW.world_camera(WORLD, P, Kc if Kc is not None else K, width, height, ego=ego), P

    # ─────────────────────────────── 2. τ: 真値 / 流れ / 大きさ ─────────────────────────────
    print("== 2. 対向車が来る 4.5 秒(%d コマ)を車載カメラ(60°, 640 × 400)で撮り、τ を 3 つの経路で出す" % (int(4.5 / DT) + 1))
    M_ONC = np.eye(4)
    M_ONC[0, 3] = -V_ONC * DT                                          # 対向車の 1 コマの世界での動き
    fwd = -cam_pose(ego_pose(0.0))[2, :3]                              # カメラ光軸の世界での向き(少し下向き)
    COS_PITCH = float(fwd @ np.array([1.0, 0.0, 0.0]))
    t_frames = np.round(np.arange(0.0, 4.5 + 1e-9, DT), 6)
    K_SCALE = 5                                                        # 大きさの τ はコマ間隔 0.5 s(面積の量子化に勝つため)
    frames = [render(t) for t in t_frames] + [render(t_frames[-1] + k * DT) for k in range(1, K_SCALE + 1)]
    rec = {k: [] for k in ("t", "tau_closed", "tau_truth_min", "tau_truth_med", "tau_lk", "tau_scale", "tau_ident_err",
                           "n_px", "foe_err", "scale_lo", "scale_hi", "flow_px", "n_lk")}
    t_render = time.time()
    for k, t in enumerate(t_frames):
        c0, P0 = frames[k]
        c1, P1 = frames[k + 1]
        T_onc = TT.relative_motion(P0, P1, M_ONC)
        taxi = (c0["face"] >= f_onc[0]) & (c0["face"] < f_onc[1])
        taxi1 = (c1["face"] >= f_onc[0]) & (c1["face"] < f_onc[1])
        # 真値: 画素ごと(τ₀ = Z₀Δt/(Z₀−Z₁))と、姿勢からの閉形式(最も近い面 = 前バンパー、光軸に沿った距離)
        tru = TT.ttc_truth(c0["depth"], K, T_onc, DT)
        d_axis = ((onc_x(t) - CAR[0] / 2) - (ego_pose(t)[0] + CAM_FWD)) * COS_PITCH
        tau_closed = TT.ttc_from_range(d_axis, (V_EGO + V_ONC) * COS_PITCH)
        # 恒等式: 真の流れ → time_to_contact → 1 コマ足す = 真の τ₀
        ft = TT.flow_from_depth_motion(c0["depth"], K, T_onc)
        foe = TT.foe_from_motion(K, T_onc)
        ident = TT.ttc_from_flow(ft["u"], ft["v"], DT, foe=foe)
        ok = ft["valid"] & np.isfinite(tru["tau"]) & taxi
        ident_err = float(np.max(np.abs(ident["tau_map"][ok] - tru["tau"][ok]) / tru["tau"][ok])) if ok.any() else np.nan
        # 流れから: LK(5 段)、対向車の画素、真の FoE
        g0, g1 = c0["color"].mean(-1), c1["color"].mean(-1)
        u, v = FL.optical_flow_lk(g0, g1, window=15, levels=5)
        lk = TT.ttc_from_flow(u, v, DT, foe=foe, mask=taxi)
        foe_est = SF.focus_of_expansion(u, v)
        # 大きさから: 面積 n の平方根 ∝ 1/Z、コマ間隔 K_SCALE·DT。量子化の許容 = 面積 ±(周長/2)画素(縁の画素が半分ずつ)
        cS = frames[k + K_SCALE][0]
        taxiS = (cS["face"] >= f_onc[0]) & (cS["face"] < f_onc[1])
        DS = K_SCALE * DT
        n0, n1 = int(taxi.sum()), int(taxiS.sum())
        e0, e1 = TT.label_extent(taxi.astype(int), 1), TT.label_extent(taxiS.astype(int), 1)
        per0, per1 = 2 * (e0["width"] + e0["height"]), 2 * (e1["width"] + e1["height"])
        if n0 > 0 and n1 > n0:                                          # 通り過ぎたコマ(面積 0)は測れない
            tau_scale = TT.ttc_from_scale(math.sqrt(n0), math.sqrt(n1), DS)
            lo = TT.ttc_from_scale(math.sqrt(n0 + per0 / 2), math.sqrt(n1 - per1 / 2), DS) if n1 - per1 / 2 > n0 + per0 / 2 else float("inf")
            hi = TT.ttc_from_scale(math.sqrt(max(n0 - per0 / 2, 1.0)), math.sqrt(n1 + per1 / 2), DS)
        else:
            tau_scale = lo = hi = float("nan")
        rec["t"].append(t)
        rec["tau_closed"].append(tau_closed)
        rec["tau_truth_min"].append(float(np.nanmin(tru["tau"][taxi])))
        rec["tau_truth_med"].append(float(np.nanmedian(tru["tau"][taxi])))
        rec["tau_lk"].append(lk["tau"])
        rec["n_lk"].append(lk["n"])
        rec["tau_scale"].append(tau_scale)
        rec["scale_lo"].append(hi)                                       # 区間の下端(面積の誤差が τ を小さく見せる側)
        rec["scale_hi"].append(lo)
        rec["tau_ident_err"].append(ident_err)
        rec["n_px"].append(n0)
        rec["foe_err"].append(float(np.hypot(foe_est[0] - foe[0], foe_est[1] - foe[1])))
        rec["flow_px"].append(float(np.nanmedian(np.hypot(ft["u"], ft["v"])[taxi])) if taxi.any() else np.nan)
    R = {k: np.asarray(v, float) for k, v in rec.items()}
    print("  描画 + 流れ %.1f s。t = 0 / 2 / 4 / 4.5 s: 対向車 %d / %d / %d / %d 画素、真の流れ %.1f / %.1f / %.1f / %.1f px" % (
        time.time() - t_render, *[int(R["n_px"][np.argmin(np.abs(R["t"] - tt))] if tt <= 4.5 else 0) for tt in (0, 2, 4, 4.5)],
        *[R["flow_px"][np.argmin(np.abs(R["t"] - tt))] for tt in (0, 2, 4, 4.5)]))
    gate("恒等式: 真の流れ → time_to_contact + 1 コマ = 真の τ₀(%d コマ、対向車の全画素、相対差 < 1e-9)" % len(R["t"]),
         np.nanmax(R["tau_ident_err"]) < 1e-9, "max %.1e" % np.nanmax(R["tau_ident_err"]))
    e_closed = np.abs(R["tau_truth_min"] - R["tau_closed"]) / R["tau_closed"]
    slope = np.polyfit(R["t"], R["tau_truth_min"], 1)[0]
    # 画素の中心は前バンパーの極点をちょうど踏まないので、最近点の深度は数 cm 奥(8 m 先で 1e-2)。傾きは深度像の τ で測る
    gate("dτ/dt = −1: 最も近い画素の真の τ = 前バンパーまでの距離 / 閉じる速さ(相対差 < 1e-2、画素の中心が極点を踏まない分)、"
         "深度像の τ の傾き −1 ± 0.02",
         e_closed.max() < 1e-2 and abs(slope + 1.0) < 0.02, "max %.1e, slope %.4f" % (e_closed.max(), slope))
    big = R["n_px"] >= 150
    e_lk = np.abs(R["tau_lk"] - R["tau_truth_med"]) / R["tau_truth_med"]
    e_lk_big = e_lk[big & np.isfinite(e_lk)]
    print("  LK の τ(真の FoE): 相対差 中央値 %.3f(車 ≥ 150 px の %d コマ)/ 全 %d コマの中央値 %.3f、最大 %.2f。"
          "遠い区間(< 150 px、流れ < 1 px)は %s" % (
              np.median(e_lk_big), big.sum(), len(e_lk), np.nanmedian(e_lk), np.nanmax(e_lk),
              ", ".join("%.2f" % e for e in e_lk[~big][:6])))
    gate("流れの τ: 対向車が 150 画素以上の区間で、LK の τ の相対差の中央値 < 0.1(90 % 点は情報として出す)",
         np.median(e_lk_big) < 0.1, "median %.3f p90 %.3f max %.3f" % (np.median(e_lk_big), np.percentile(e_lk_big, 90), e_lk_big.max()))
    has_s = np.isfinite(R["tau_scale"]) & big
    e_sc = np.abs(R["tau_scale"] - R["tau_closed"]) / R["tau_closed"]
    in_band = (R["tau_closed"] >= R["scale_lo"] - 1e-9) & (R["tau_closed"] <= R["scale_hi"] + 1e-9) & has_s
    resolv = np.isfinite(R["scale_hi"]) & has_s
    print("  大きさの τ(コマ間隔 %.1f s): 車 ≥ 150 px の %d コマで相対差 中央値 %.3f、90 %% 点 %.3f。量子化の許容区間 [面積 ±周長/2] が"
          "有限なのは %d コマ、そのうち真値が区間内 %d(外れる %d コマは車のシルエットが平面でなく、近づくと側面が見えてくる分)" % (
              K_SCALE * DT, has_s.sum(), np.median(e_sc[has_s]), np.percentile(e_sc[has_s], 90), resolv.sum(), in_band.sum(),
              resolv.sum() - in_band.sum()))
    gate("大きさの τ: 車 ≥ 150 px で相対差の中央値 < 0.1、量子化の許容区間に ≥ 80 % が入る(外れは平面でないシルエット)",
         np.median(e_sc[has_s]) < 0.1 and in_band.sum() >= 0.8 * resolv.sum(), "%d / %d" % (in_band.sum(), resolv.sum()))
    print("  FoE(流れ全体から推定)と真の FoE の距離: 中央値 %.1f px、最小 %.1f px —— 路面に模様が無く、流れは車と街灯にしか無い(正直な数字、門にしない)" % (
        np.median(R["foe_err"]), R["foe_err"].min()))

    # ─────────────────────────────── 3. RSS: 公表値と定理 ─────────────────────────────
    print("== 3. RSS(Shalev-Shwartz 2017)の安全距離: 公表パラメータ(ad-rss-lib)で閉形式を確かめ、最悪ケースの積分と突き合わせる")
    P_EGO = RS.rss_params(rho=1.0)                                     # ρ_ego = 1 s(表の既定)
    P_OTH = RS.rss_params(rho=2.0)                                     # ρ_other = 2 s
    kmh = 50.0 / 3.6
    P2 = RS.rss_params(rho=2.0)
    d40 = RS.rss_longitudinal_same(kmh, kmh, RS.rss_params(rho=2.0, accel_max=0.0), P2)
    d80 = RS.rss_longitudinal_same(kmh, kmh, RS.rss_params(rho=2.0, accel_max=4.0), P2)
    print("  同方向 50 km/h、ρ = 2 s、制動 4 / 8 m/s²: 加速 0 → %.1f m、加速 4 m/s² → %.1f m(公表図: ≈ 40 m と ≈ 80 m)" % (d40, d80))
    lat_pub = {0.0: 1.1, 1.0: 1.19, -1.0: 1.19, 5.0: 2.9, -5.0: 2.9}
    lat_got = {vk: RS.rss_lateral(vk / 3.6, vk / 3.6, P_OTH, P_OTH) for vk in lat_pub}
    lat_err = max(abs(lat_got[vk] - lat_pub[vk]) for vk in lat_pub)
    print("  横方向(両車が同じ横速度 km/h → 安全距離 m): %s" % ", ".join("%+.0f → %.3f (公表 %.2f)" % (vk, lat_got[vk], lat_pub[vk]) for vk in lat_pub))
    gate("RSS の公表値: 50 km/h の同方向で |d − 40| < 1 と 75 < d < 90、横方向の試験値 5 点と ±0.01",
         abs(d40 - 40.0) < 1.0 and 75.0 < d80 < 90.0 and lat_err < 0.01, "lat max err %.4f" % lat_err)
    d_min_8 = RS.rss_longitudinal_same(V_EGO, 0.0, P_EGO)
    sim0 = RS.rss_worst_case_gap(d_min_8, V_EGO, 0.0, P_EGO)
    rng = np.random.default_rng(0)
    worst = 0.0
    for _ in range(50):
        vr, vf, d0 = rng.uniform(0, 25), rng.uniform(0, 25), rng.uniform(0, 120)
        bmin = rng.uniform(2, 6)
        pr = RS.rss_params(rho=rng.uniform(0.3, 2.0), accel_max=rng.uniform(0, 4), brake_min=bmin,
                           brake_max=rng.uniform(6, 10), brake_min_correct=rng.uniform(1, bmin))
        dm = RS.rss_longitudinal_same(vr, vf, pr)
        s = RS.rss_worst_case_gap(d0, vr, vf, pr)
        worst = max(worst, abs(s["min_gap"] - (d0 - dm)) if d0 >= dm else 0.0)
        if (d0 < dm) != s["collided"]:
            worst = np.inf
    gate("Lemma 2 = 最悪ケースの積分: v = 8 → d_min %.2f m で min_gap = 0(|·| < 1e-6)、乱数 50 組で |min_gap − (d₀ − d_min)| < 1e-6、衝突の有無も一致" % d_min_8,
         abs(sim0["min_gap"]) < 1e-6 and worst < 1e-6, "max %.1e" % worst)

    # ─────────────────────────────── 4. 教習所の場面 ─────────────────────────────
    print("== 4. 場面 A: 自車線の停車車両に RSS が「危険」を出した瞬間に制動する / 場面 B: 対向車は τ が騒ぐが RSS は騒がない")
    T_END = 10.0
    n_steps = int(round(T_END / DT))
    x_e, v_e = ego_pose(0.0)[0], V_EGO
    t_b, gap_b, x_stop = None, None, None
    A = {k: [] for k in ("t", "x", "v", "gap", "dmin", "danger")}
    for i in range(n_steps + 1):
        t = i * DT
        gap = (X_STOP - CAR[0] / 2) - (x_e + CAR[0] - CAR[2])         # 停車車両の後端 − 自車の前端
        chk = RS.rss_longitudinal_check(gap, v_e, 0.0, P_EGO)
        if chk["dangerous"] and t_b is None:
            t_b, gap_b = t, gap
        A["t"].append(t)
        A["x"].append(x_e)
        A["v"].append(v_e)
        A["gap"].append(gap)
        A["dmin"].append(chk["safe_distance"])
        A["danger"].append(chk["dangerous"])
        # 次のコマへ(proper response: t_b から ρ の間は速度維持、その後 brake_min で停止まで。区分ごとの厳密な運動学)
        if t_b is None or t + 1e-9 < t_b + P_EGO["rho"]:
            x_e += v_e * DT
        else:
            b = P_EGO["brake_min"]
            t_stop = v_e / b
            if t_stop >= DT:
                x_e += v_e * DT - 0.5 * b * DT * DT
                v_e -= b * DT
            else:
                x_e += v_e * t_stop - 0.5 * b * t_stop * t_stop
                v_e = 0.0
        if v_e <= 0.0 and x_stop is None:
            x_stop = x_e
    A = {k: np.asarray(v, float) for k, v in A.items()}
    gap_final = float(A["gap"][-1])
    closed_final = gap_b - (V_EGO * P_EGO["rho"] + V_EGO ** 2 / (2 * P_EGO["brake_min"]))
    print("  危険と判定 t_b = %.1f s(間隔 %.2f m < d_min %.2f m)→ 応答時間 %.0f s は速度維持、%.0f m/s² で制動 → 停止 x = %.2f、間隔 %.3f m" % (
        t_b, gap_b, d_min_8, P_EGO["rho"], P_EGO["brake_min"], x_stop, gap_final))
    gate("場面 A: 停止時の間隔 = gap(t_b) − (vρ + v²/2b) と 1e-9 で一致し、正(%.2f m)" % gap_final,
         abs(gap_final - closed_final) < 1e-9 and gap_final > 0, "closed %.6f" % closed_final)
    gate("場面 A: 危険の判定前は全コマで gap > d_min、判定後は制動して速度 0 に至る",
         np.all(A["gap"][~A["danger"].astype(bool)] > A["dmin"][~A["danger"].astype(bool)]) and A["v"][-1] == 0.0)
    # 場面 B: 対向車線(横の間隔 2.2 m、横速度 0)
    lat_gap = 4.0 - CAR[1]
    lat_chk = RS.rss_lateral_check(lat_gap, 0.0, 0.0, P_EGO, P_OTH)
    d_opp = RS.rss_longitudinal_opposite(V_EGO, V_ONC, P_EGO, P_OTH)
    t_pass = np.array([t for t in t_frames])
    gap_opp = (onc_x(t_pass) - CAR[0] / 2) - (ego_pose(0.0)[0] + V_EGO * t_pass + CAR[0] - CAR[2])
    print("  場面 B: 横の安全距離 %.3f m < 横の間隔 %.2f m → RSS は「危険」を出さない(縦の対向の安全距離は %.1f m で、直線 80 m の間ずっと"
          " gap %.1f〜%.1f m はその中にある —— 縦だけ見れば常に近すぎる)。τ の真値は %.2f s まで落ちる" % (
              lat_chk["safe_distance"], lat_gap, d_opp, gap_opp.min(), gap_opp.max(), R["tau_closed"].min()))
    gate("場面 B: τ < 1 s まで落ちても横が安全(%.3f < %.2f m)なので RSS は危険を出さない" % (lat_chk["safe_distance"], lat_gap),
         R["tau_closed"].min() < 1.0 and not lat_chk["dangerous"] and np.all(gap_opp < d_opp))
    # 場面 B': 対向車が t = 1 s から横へ 0.6 m/s で寄ってくる
    V_LAT = 0.6
    T_DRIFT = 1.0
    lat_chk_d = RS.rss_lateral_check(lat_gap, 0.0, -V_LAT, P_EGO, P_OTH)     # c1 = 自車(横軸は自車 → 対向車の向き)、c2 は自車へ向かう
    k_b = int(np.argmin(np.abs(t_pass - T_DRIFT)))
    gap_b_opp = float(gap_opp[k_b])
    sim_opp = RS.rss_worst_case_gap_opposite(gap_b_opp, V_EGO, V_ONC, P_EGO, P_OTH)
    sim_eq = RS.rss_worst_case_gap_opposite(d_opp, V_EGO, V_ONC, P_EGO, P_OTH)
    print("  場面 B': 横速度 0.6 m/s で寄ると横の安全距離は %.3f m > %.2f m → t = %.1f s に危険。そのとき縦の間隔 %.2f m < %.1f m なので"
          "最悪ケース(両車が応答時間だけ加速してから制動)は %s(最小間隔 %.2f m)。d₀ = d_min なら最小間隔 %.1e" % (
              lat_chk_d["safe_distance"], lat_gap, T_DRIFT, gap_b_opp, d_opp,
              "衝突する" if sim_opp["collided"] else "衝突しない", sim_opp["min_gap"], sim_eq["min_gap"]))
    gate("場面 B': 横が危険になった瞬間の縦の間隔は対向の安全距離の中で、最悪ケースの積分は衝突する(閉形式と一致)",
         lat_chk_d["dangerous"] and gap_b_opp < d_opp and sim_opp["collided"] and abs(sim_eq["min_gap"]) < 1e-6)

    # ─────────────────────────────── 5. 図 ─────────────────────────────
    if figs.enabled():
        print("== 5. 図")
        # 5a. 平面(t = 3 s)
        Kb = DW.camera_intrinsics(50.0, 960, 600)
        set_scene(3.0)
        top = DW.world_camera(WORLD, DW.camera_pose((0.0, -15.0, 58.0), (0.0, -15.0 + 0.01, 0.0), up=(0.0, 1.0, 0.0)),
                              Kb, 960, 600, ego=(ego_mesh(ego_pose(3.0)), EGO["F"], EGO["color"]))["color"]
        top = np.asarray(AN.text_box(top, "t = 3.0 s  自車 → 8 m/s(北の車線)  対向車 ← 8 m/s(南の車線)  停車車両 x = 40",
                                     (12, 12), anchor="lt", font_size=14))
        figs.save("scene_plan", top,
                  "教習所の周回コース(14 巡目)の南の直線 80 m を真上から(t = 3 s): 東行きの自車(8 m/s、北側の車線)、西行きの対向車"
                  "(8 m/s、南側の車線、横の間隔 2.2 m)、自車線の先に停まっている車(x = 40)。左側通行。世界はコースの外 8 m で終わる。")
        # 5b. 車載カメラ + 光学流(t = 3 s)
        k3 = int(np.argmin(np.abs(t_frames - 4.0)))
        c0, P0 = frames[k3]
        c1, P1 = frames[k3 + 1]
        T_onc = TT.relative_motion(P0, P1, M_ONC)
        taxi = (c0["face"] >= f_onc[0]) & (c0["face"] < f_onc[1])
        g0, g1 = c0["color"].mean(-1), c1["color"].mean(-1)
        u, v = FL.optical_flow_lk(g0, g1, window=15, levels=5)
        foe = TT.foe_from_motion(K, T_onc)
        img = c0["color"].copy()
        rr, cc = np.mgrid[0:400, 0:640]
        sel = taxi & (rr % 5 == 0) & (cc % 5 == 0) & np.isfinite(u) & (np.hypot(u, v) > 0.05)
        for y, x in zip(rr[sel], cc[sel]):
            img = np.asarray(AN.arrow(img, (float(x), float(y)), (float(x + 3 * u[y, x]), float(y + 3 * v[y, x])),
                                      color="emphasis", width=1, head_len=4.0, head_width=3.0))
        img = np.asarray(AN.crosshair(img, (float(foe[0]), float(foe[1])), color="right", width=1, gap=4, extent=10))
        img = np.asarray(AN.text_box(img, "t = 4.0 s   τ 真値 %.2f s   流れから %.2f s   大きさから %.2f s   (矢印 = LK の流れ × 3、十字 = 真の FoE)" % (
            R["tau_truth_med"][k3], R["tau_lk"][k3], R["tau_scale"][k3]), (10, 390), anchor="lb", font_size=12))
        figs.save("incar_flow", img,
                  "t = 4 s の車載カメラ(60°, 640 × 400)。対向車の画素の光学流(Lucas–Kanade 5 段、×3 で描く)は真の FoE(十字)から外へ向かい、"
                  "その半径方向の速さから τ = %.2f s(真値 %.2f s)。路面には模様が無いので流れは車と街灯にしか無い。" % (
                      R["tau_lk"][k3], R["tau_truth_med"][k3]))
        # 5c. τ の曲線
        fin = np.isfinite(R["tau_lk"]) & (R["tau_lk"] < 8.0)
        fs_ = np.isfinite(R["tau_scale"]) & (R["tau_scale"] < 8.0)
        figs.save_plot("tau_curves", [("真値(距離 / 閉じる速さ)", R["t"], R["tau_closed"]),
                                      ("真値(深度像、対向車の画素の中央値)", R["t"], R["tau_truth_med"]),
                                      ("流れから(LK、真の FoE)", R["t"][fin], R["tau_lk"][fin]),
                                      ("大きさから(面積の平方根、コマ間隔 0.5 s)", R["t"][fs_], R["tau_scale"][fs_])],
                       kinds=["line", "line", "scatter", "scatter"], xlabel="t [s]", ylabel="τ [s]", ylim=(0.0, 8.0),
                       caption="対向車の τ(衝突までの時間)の 4 本: 真値は 5 s から 1 秒に 1 秒ずつ減る(傾き −1)。流れからの τ は車が像で大きい区間"
                               "(t ≥ 2 s、≥ 150 px)で真値に乗り、遠い区間はサブピクセルの流れで外れる。大きさからの τ(コマ間隔 0.5 s)は量子化の許容区間に入る。")
        # 5d. 場面 A
        figs.save_plot("rss_same_direction", [("停車車両までの間隔 [m]", A["t"], A["gap"]), ("RSS の安全距離 d_min [m]", A["t"], A["dmin"]),
                                              ("自車の速さ × 3 [m/s]", A["t"], 3.0 * A["v"])],
                       xlabel="t [s]", ylabel="m", caption="場面 A: 停車車両への間隔(青)が RSS の安全距離(橙、v = 8 で %.2f m)を割った t = %.1f s に「危険」→ "
                                                            "応答時間 1 s は速度維持、その後 4 m/s² で制動。停止時の間隔 %.2f m は閉形式と 1e-9 で一致。"
                                                            "制動中は v が下がるので d_min も下がる。" % (d_min_8, t_b, gap_final))
        # 5e. 場面 B / B'
        lat_drift = np.where(t_pass >= T_DRIFT, lat_gap - V_LAT * (t_pass - T_DRIFT), lat_gap)
        dmin_lat_d = np.where(t_pass >= T_DRIFT, lat_chk_d["safe_distance"], lat_chk["safe_distance"])
        figs.save_plot("rss_lateral", [("横の間隔(車線どおり)[m]", t_pass, np.full_like(t_pass, lat_gap)),
                                       ("横の安全距離(横速度 0)[m]", t_pass, np.full_like(t_pass, lat_chk["safe_distance"])),
                                       ("横の間隔(t = 1 s から 0.6 m/s で寄る)[m]", t_pass, lat_drift),
                                       ("横の安全距離(寄ってくる)[m]", t_pass, dmin_lat_d),
                                       ("τ の真値 [s]", t_pass, R["tau_closed"])],
                       xlabel="t [s]", ylabel="m / s", ylim=(0.0, 5.5),
                       caption="場面 B: 対向車線なら横の間隔 2.2 m > 横の安全距離 %.2f m で、τ が %.1f s まで落ちても RSS は危険を出さない。"
                               "場面 B': 対向車が 0.6 m/s で寄ってくると横の安全距離は %.2f m に跳ね、t = 1 s に危険 —— そのとき縦の間隔 %.1f m は"
                               "対向の安全距離 %.1f m の中で、最悪ケースは衝突する。責任は寄ってきた側。" % (
                                   lat_chk["safe_distance"], R["tau_closed"].min(), lat_chk_d["safe_distance"], gap_b_opp, d_opp))
        # 5f. GIF: 車載カメラで 0 → 10 s(τ と RSS の状態を書き込む)
        Kg = DW.camera_intrinsics(60.0, 480, 300)
        gif = []
        t_gif = np.round(np.arange(0.0, T_END + 1e-9, 2 * DT), 6)
        for t in t_gif:
            i = int(round(t / DT))
            x_e_t = A["x"][i]
            set_scene(t)
            P = cam_pose((x_e_t, Y_EGO, 0.0))
            cg = DW.world_camera(WORLD, P, Kg, 480, 300)
            fr = cg["color"]
            k = int(np.argmin(np.abs(t_frames - t)))
            if t <= 4.5 + 1e-9:                                           # 対向車の画素に LK の流れの矢印(×4)と真の FoE
                set_scene(t + DT)
                cg1 = DW.world_camera(WORLD, cam_pose((x_e_t + V_EGO * DT, Y_EGO, 0.0)), Kg, 480, 300)
                ug, vg = FL.optical_flow_lk(cg["color"].mean(-1), cg1["color"].mean(-1), window=11, levels=5)
                tx = (cg["face"] >= f_onc[0]) & (cg["face"] < f_onc[1])
                rg, cgg = np.mgrid[0:300, 0:480]
                sel = tx & (rg % 6 == 0) & (cgg % 6 == 0) & np.isfinite(ug) & (np.hypot(ug, vg) > 0.05)
                for y, x in zip(rg[sel], cgg[sel]):
                    L_ = min(4.0, 40.0 / float(np.hypot(ug[y, x], vg[y, x])))      # 近いと流れが数十画素なので長さを 40 px で抑える
                    fr = np.asarray(AN.arrow(fr, (float(x), float(y)), (float(x + L_ * ug[y, x]), float(y + L_ * vg[y, x])),
                                             color="emphasis", width=1, head_len=3.0, head_width=2.5))
                foe_g = TT.foe_from_motion(Kg, TT.relative_motion(P, cam_pose((x_e_t + V_EGO * DT, Y_EGO, 0.0)), M_ONC))
                fr = np.asarray(AN.crosshair(fr, (float(foe_g[0]), float(foe_g[1])), color="right", width=1, gap=3, extent=8))
            if t <= 4.5 + 1e-9:
                line1 = "t = %4.1f s   τ 真値 %.2f s   流れから %s" % (t, R["tau_closed"][k], ("%.2f s" % R["tau_lk"][k]) if np.isfinite(R["tau_lk"][k]) and R["tau_lk"][k] < 20 else "—")
            else:
                line1 = "t = %4.1f s   対向車は通り過ぎた" % t
            if A["danger"][i] and A["v"][i] > 0:
                line2 = "RSS: 危険(間隔 %.1f m < d_min %.1f m)→ 制動 v = %.1f m/s" % (A["gap"][i], A["dmin"][i], A["v"][i])
                col = "wrong"
            elif A["v"][i] == 0.0:
                line2 = "RSS: 停止。間隔 %.2f m" % A["gap"][i]
                col = "right"
            else:
                line2 = "RSS: 安全(停車車両まで %.1f m ≥ %.1f m、対向車は横 %.1f m ≥ %.2f m)" % (A["gap"][i], A["dmin"][i], lat_gap, lat_chk["safe_distance"])
                col = "right"
            fr = np.asarray(AN.text_box(fr, line1, (8, 8), anchor="lt", font_size=12))
            fr = np.asarray(AN.text_box(fr, line2, (8, 292), anchor="lb", font_size=12, color=col))
            gif.append(fr)
        figs.save_gif("approach_gif", gif, fps=5,
                      caption="車載カメラで 0 → 10 s(%d コマ): 対向車が来る間はその画素の光学流(矢印 ×4、長さ 40 px まで)と真の FoE(十字)を描き、τ の真値と"
                              "流れからの τ を並べる。通り過ぎたあと自車線の停車車両に RSS が「危険」を出した瞬間(t = %.1f s)に制動して "
                              "%.2f m 手前で止まる。" % (len(gif), t_b, gap_final))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))

    print("== 結果: %d / %d 門, %.1f s" % (sum(OK), len(OK), time.time() - T0))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
