# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""エアホッケーのパックを追い、予測し、5 節リンクで打ち返す —— 学習なし、閉形式と外部シムを門に(2026-10-04)。

物理シミュ × Fullseye 系列の第 3 弾。低価格のエアホッケーロボット(Shinjo, Beltran-Hernandez, Hamaya, Tanaka, IROS 2024,
doi 10.1109/iros58592.2024.10801458)の鎖 **カメラ → パック検出 → 速度推定 → 軌道予測 → 5 節リンクの動作計画** を、Fullseye の
既存部品(:func:`balltrack.ball_detect` / :func:`balltrack.ball_track` / :func:`balltrack.kalman_ca`、:func:`ballistics.slide_stop_distance`、
:func:`calib.image_to_world_plane`)と新モジュール :mod:`puck`(26 op)で、全部ルールで組む。外から来るものは 3 系統:
  * **閉形式**: Coulomb の等減速 a = μg(停止距離 v₀²/(2μg))、壁は法線 −e・接線 kₜ(2 つの反発係数。記法は Cross 2022, Eur. J. Phys.,
    doi 10.1088/1361-6404/ac4b47。Spong 2001 の衝突模型は原文を読めていないので未検証)、区間ごとの閉形式を壁で繋ぐ(鏡映法と一致)、
    5 節リンクの FK/IK(円と円の交点)。
  * **外部シム(第 2 実装、MIT)**: Robot Air Hockey Challenge の台の MJCF(Liu ほか、arXiv 2411.05718)。★読んで分かったこと: パックと
    台面の接触は切ってあり、減速は滑り関節の **粘性減衰 c/m = 0.5 /s**(Coulomb ではない)、壁は軟接触で e・kₜ は測って出る。
    配布物は repo に同梱せず、環境変数 FULLSEYE_AIRHOCKEY_DATA の下に置いたときだけ(--full)。
  * **第 2 実装(自前)**: Coulomb 版の最小 MJCF(摩擦のある平面の円柱)で等減速を MuJoCo でも確かめる(--full)。

門(16 + --full 6): 停止距離 = ballistics(1e-9)、壁の反発 e²、鏡映法 = 区間予測(200 本、1e-9)、閉形式の自己整合 + Euler、FK∘IK(1e-9)+
届かない → None、作業域の境界と守備線の届く区間(隅は届かない: 正直)、検出の重心(50 点、< 0.05 px)、速度の最小二乗(真値 1e-9・検出 1 %)、
雑音ありの交点(20 本、3σ)、打点計画(間に合う / too_late / unreachable / no_crossing)、モーションブラー = v·τ/2、綴り壊し、μ の推定(10 %)、
壁の e・kₜ(2 / 3 %)、速いパックで対応が切れる、kalman_ca の新息; --full: Challenge の減衰が粘性(1 %)、粘性の閉形式 vs MuJoCo(1 mm)、
測った e・kₜ で壁の後(10 mm)、自前 Coulomb MJCF の減速(5 %)、描画 → 色検出 → 針穴(5 mm / 1.5 mm)、全鎖 20 本(届く交点は全部打つ)。
図(FULLSEYE_FIGURE_DIR があるとき 6 枚): 343 px/m のコマに検出・予測線・交点 + パックの等倍切り出し(副画素の重心)、予測の扇が細る GIF、
速度誤差 vs N、5 節リンクが先回りする GIF、壊れる場所(ブラー・kₜ の扇・速いパック)、MuJoCo vs 閉形式(--full なら 3 本、無ければ閉形式 2 本)。
正直に: 5 節リンクの寸法・サーボ 6 rad/s・打具 40 mm・守備線 x = −0.75・既定 μ / e / kₜ は **仮定**(論文の実機の数は読めていない)。実機映像は
無い(合成 + MuJoCo、照明・レンズ歪み・ローリングシャッター無し)。壁の滑り/把持の 2 領域と回転は未実装。
Run: py -3.11 examples/poc_air_hockey_intercept.py [--full]        (--full は mujoco と FULLSEYE_AIRHOCKEY_DATA)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as AN  # noqa: E402
import ballistics as B  # noqa: E402
import balltrack as BT  # noqa: E402
import examplefig as figs  # noqa: E402
import imagedraw as ID  # noqa: E402
import puck as PK  # noqa: E402

TB = PK.puck_table(mu=0.02, e=0.8, kt=0.9)
CAM = PK.puck_camera(TB, px_per_m=200.0)
LINK = PK.fivebar_link()
X_DEF = -0.75                         # 守備線(ロボット側の端の壁の内面 −0.974 から 0.224 m 手前、仮定)
FPS = 120.0
OMEGA = 6.0                           # サーボの角速度の上限 [rad/s] (仮定)
MALLET_R = 0.04                       # 打具の半径 [m] (仮定)
FULL = "--full" in sys.argv
_GATES: list[tuple[str, bool]] = []
_NUM: dict = {}


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


# ======================================================================================================================
def numpy_part() -> dict:
    t0 = time.time()
    rng = np.random.default_rng(20261004)
    print("== 閉形式と合成カメラ(台 %.3f × %.3f m、パック r %.5f m、%g px/m、μ %g、e %g、kₜ %g)" %
          (2 * TB["x_half"], 2 * TB["y_half"], TB["puck_radius"], CAM["px_per_m"], TB["mu"], TB["e"], TB["kt"]))
    ctx = {}

    # ── 1. 停止距離
    big = PK.puck_table(mu=0.02, x_half=100.0, y_half=100.0)
    pr = PK.puck_slide_predict((0, 0), (1.3, 0.4), big, 1e3)
    v0 = float(np.hypot(1.3, 0.4))
    d_cf = PK.puck_stop_distance(v0, big)
    err = max(abs(float(np.linalg.norm(pr["p_end"])) - d_cf), abs(d_cf - B.slide_stop_distance(v0, 0.02))) / d_cf
    gate("門 1 停止距離: 区間予測 = v²/(2μg) = ballistics.slide_stop_distance", err < 1e-9, "d = %.4f m、相対 %.1e、events %s" % (d_cf, err, pr["events"]))

    # ── 2. 壁の反発
    b1 = PK.puck_wall_bounce((0.0, -1.3), (0, 1), 0.8, 0.9)
    b2 = PK.puck_wall_bounce((0.7, -1.3), (0, 1), 0.8, 0.9)
    e1 = abs(b1["energy_ratio"] - 0.64)
    e2 = max(abs(b2["vn_out"] - 0.8 * 1.3), abs(b2["vt_out"] - 0.9 * 0.7), abs(b2["v"][1] - 0.8 * 1.3), abs(b2["v"][0] - 0.9 * 0.7))
    gate("門 2 壁の反発: 法線だけなら運動エネルギー比 e²、斜めなら vₙ' = −e vₙ・vₜ' = kₜ vₜ", e1 < 1e-12 and e2 < 1e-12, "|ΔE/E − e²| %.1e、斜め %.1e" % (e1, e2))

    # ── 3. 鏡映法(第 2 実装)
    tb1 = PK.puck_table(mu=0.0, e=1.0, kt=1.0)
    worst, nb = 0.0, 0
    for _ in range(200):
        p0 = rng.uniform([-0.9, -0.45], [0.9, 0.45])
        v = rng.uniform([-3, -3], [3, 3])
        T = rng.uniform(0.2, 4.0)
        prm = PK.puck_slide_predict(p0, v, tb1, T, model="none", goals=False)
        worst = max(worst, float(np.abs(prm["p_end"] - PK.puck_mirror_path(p0, v, tb1, T)).max()))
        nb = max(nb, prm["n_bounces"])
    _NUM["mirror_max_m"] = worst
    gate("門 3 鏡映法 = 区間予測(摩擦なし・e = kₜ = 1、200 本、最大 %d 回反射)" % nb, worst < 1e-9, "max |Δp| %.1e m" % worst)

    # ── 4. 自己整合 + Euler
    pr = PK.puck_slide_predict((0.3, 0.1), (-1.6, 0.9), TB, 3.0)
    c = PK.puck_crossing_point(pr, X_DEF)
    self_err = abs(PK.puck_state_at(pr, c["t"])["p"][0, 0] - X_DEF)
    h = 1e-6
    tt = np.array([0.1, 0.3, 0.6, 0.9])
    verr = float(np.abs((PK.puck_state_at(pr, tt + h)["p"] - PK.puck_state_at(pr, tt - h)["p"]) / (2 * h) - PK.puck_state_at(pr, tt)["v"]).max())
    dt = 1e-5
    p, v = np.array([0.3, 0.1]), np.array([-1.6, 0.9])
    r = TB["puck_radius"]
    xb, yb = TB["x_half"] - r, TB["y_half"] - r
    t = 0.0
    while t < 1.0 - 1e-12:
        s = np.linalg.norm(v)
        if s > 0:
            v = v - min(TB["mu"] * TB["g"] * dt, s) * v / s
        p = p + v * dt
        for ax, bd in ((0, xb), (1, yb)):
            if abs(p[ax]) > bd:
                p[ax] = np.sign(p[ax]) * (2 * bd - abs(p[ax]))
                n = np.zeros(2)
                n[ax] = -np.sign(p[ax])
                v = PK.puck_wall_bounce(v, n, TB["e"], TB["kt"])["v"]
        t += dt
    int_err = float(np.linalg.norm(p - PK.puck_state_at(pr, 1.0)["p"][0]))
    _NUM["euler_diff_m"] = int_err
    gate("門 4 閉形式の自己整合(x(t_cross) = x_line、dp/dt = v)と半陰的 Euler dt = 1e-5 の一致", self_err < 1e-12 and verr < 1e-6 and int_err < 2e-4,
         "x %.1e、v %.1e、Euler |Δp| %.2e m(閾値 2e-4 = O(dt·v) の 10 倍、events %s)" % (self_err, verr, int_err, pr["events"]))

    # ── 5. FK∘IK
    ws = PK.fivebar_workspace(LINK, n=81)
    pts = np.argwhere(ws["mask"])
    worst = 0.0
    for iy, ix in pts[rng.choice(len(pts), 400, replace=False)]:
        E = np.array([ws["xs"][ix], ws["ys"][iy]])
        worst = max(worst, float(np.linalg.norm(PK.fivebar_fk(PK.fivebar_ik(E, LINK), LINK)["E"] - E)))
    far = LINK["A1"] + np.array([LINK["l1"] + LINK["l2"] + 1e-3, 0.0])
    _NUM["workspace_area_m2"] = ws["area"]
    gate("門 5 5 節リンク FK∘IK = 恒等(作業域 400 点)、届かなければ None、枝の綴り",
         worst < 1e-9 and PK.fivebar_ik(far, LINK) is None and _raises(PK.fivebar_ik, (-0.75, 0.0), LINK, branch="outt"),
         "max |FK(IK(E)) − E| %.1e m、作業域 %.3f m²、x_max %.3f" % (worst, ws["area"], ws["x_max"]))
    ctx["ws"] = ws

    # ── 6. 作業域の境界と守備線
    reach = LINK["l1"] + LINK["l2"]
    ok_b = True
    for ang in np.linspace(0.35, 0.9, 7):
        u = np.array([np.cos(ang), np.sin(ang)])
        ok_b &= (PK.fivebar_ik(LINK["A1"] + (reach - 1e-6) * u, LINK) is not None) and (PK.fivebar_ik(LINK["A1"] + (reach + 1e-6) * u, LINK) is None)
        u2 = np.array([np.cos(-ang), np.sin(-ang)])
        ok_b &= (PK.fivebar_ik(LINK["A2"] + (reach - 1e-6) * u2, LINK) is not None) and (PK.fivebar_ik(LINK["A2"] + (reach + 1e-6) * u2, LINK) is None)
    ri = PK.fivebar_reach_interval(LINK, X_DEF)
    yb_puck = TB["y_half"] - TB["puck_radius"]
    _NUM["reach_y"] = (ri["y_lo"], ri["y_hi"])
    gate("門 6 到達円 l₁ + l₂ の ±1e-6 m で内外が分かれる、守備線で届く区間", ok_b and ri["ok"] and ri["y_hi"] < yb_puck,
         "x = %.2f で y ∈ [%.3f, %.3f] m、パックは |y| ≤ %.3f まで来る → 隅は届かない(正直)" % (X_DEF, ri["y_lo"], ri["y_hi"], yb_puck))
    ctx["reach"] = ri

    # ── 7. 検出の重心
    errs = []
    for _ in range(50):
        p0 = rng.uniform([-0.9, -0.45], [0.9, 0.45])
        d = PK.puck_detect(PK.puck_render_frame(CAM, p0), CAM)
        tp = PK.puck_world_to_pixel(CAM, [p0])[0]
        errs.append((d["col"] - tp[0], d["row"] - tp[1]))
    errs = np.array(errs)
    cmax, crms = float(np.abs(errs).max()), float(np.sqrt(np.mean(errs ** 2)))
    _NUM["centroid_max_px"], _NUM["centroid_rms_px"] = cmax, crms
    gate("門 7 検出の重心 vs 真値(合成 50 点、ブラー無し)", cmax < 0.05,
         "max %.4f px、rms %.4f px(= %.3f mm; しきい値 0.85 の根拠: 0.5 だと縁の画素が切れて 0.08 px、puck_detect の docstring)" % (cmax, crms, 1e3 * crms / CAM["px_per_m"]))

    # ── 8. 速度の最小二乗
    p0, v0 = np.array([0.4, 0.15]), np.array([-1.4, 0.55])
    syn = PK.puck_synth_frames(TB, CAM, p0, v0, fps=FPS, n_frames=24, noise=0.01, rng=rng)
    ve = PK.puck_velocity_estimate(syn["t"], syn["truth_xy"], TB)
    exact = float(np.linalg.norm(ve["v_ref"] - syn["truth_v"][-1]))
    tr = PK.puck_track(syn["frames"], CAM)
    Ns, errsN, sigN = [], [], []
    for N in range(3, 25):
        veN = PK.puck_velocity_estimate(syn["t"][:N], tr["xy"][:N], TB)
        Ns.append(N)
        errsN.append(float(np.linalg.norm(veN["v_ref"] - syn["truth_v"][N - 1])))
        sigN.append(veN["sigma_v"])
    errsN, sigN = np.array(errsN), np.array(sigN)
    speed = float(np.linalg.norm(v0))
    i12 = Ns.index(12)
    _NUM["vel_err_vs_N"] = {"N": Ns, "err_mps": errsN.tolist(), "sigma_v": sigN.tolist(), "speed": speed}
    gate("門 8 速度の最小二乗: 真値の位置 → 1e-9、検出(雑音 σ 0.01)N = 12 → 3σ_v の内側かつ 1 %",
         exact < 1e-9 and tr["frame"].size == 24 and errsN[i12] < 3 * np.sqrt(2) * sigN[i12] + 1e-4 and errsN[i12] / speed < 0.01,
         "真値 %.1e; N = 12: 誤差 %.4f m/s(%.2f %%)、σ_v %.4f; N = 24: %.2f %%" % (exact, errsN[i12], 100 * errsN[i12] / speed, sigN[i12], 100 * errsN[-1] / speed))

    # ── 9. 雑音ありの交点
    err_y, sig_y, lead, n_launch = [], [], [], 0
    for _ in range(20):
        p0 = rng.uniform([0.2, -0.35], [0.8, 0.35])
        ang = rng.uniform(-0.6, 0.6)
        sp = rng.uniform(0.8, 2.0)
        v0 = sp * np.array([-np.cos(ang), np.sin(ang)])
        truth_c = PK.puck_crossing_point(PK.puck_slide_predict(p0, v0, TB, 6.0), X_DEF)
        if truth_c is None:
            continue
        n_launch += 1
        syn = PK.puck_synth_frames(TB, CAM, p0, v0, fps=FPS, n_frames=12, noise=0.01, rng=rng)
        tr = PK.puck_track(syn["frames"], CAM)
        ve = PK.puck_velocity_estimate(syn["t"][tr["frame"]], tr["xy"], TB)
        c = PK.puck_crossing_point(PK.puck_slide_predict(ve["p_ref"], ve["v_ref"], TB, 6.0, t0=ve["t_ref"]), X_DEF)
        if c is None:
            err_y.append(np.inf); sig_y.append(np.nan); lead.append(np.nan)
            continue
        err_y.append(abs(c["p"][1] - truth_c["p"][1]))
        lead.append(c["t"] - ve["t_ref"])
        ys = []
        for _ in range(60):
            cc = PK.puck_crossing_point(PK.puck_slide_predict(ve["p_ref"] + rng.normal(0, ve["sigma_p"], 2), ve["v_ref"] + rng.normal(0, ve["sigma_v"], 2),
                                                               TB, 6.0, t0=ve["t_ref"]), X_DEF)
            if cc is not None:
                ys.append(cc["p"][1])
        sig_y.append(float(np.std(ys)) if len(ys) > 2 else np.nan)
    ce, cs, lead = np.array(err_y), np.array(sig_y), np.array(lead)
    fin = np.isfinite(ce)
    rms = float(np.sqrt(np.mean(ce[fin] ** 2))) if fin.any() else np.inf
    ratio = ce[fin] / np.maximum(cs[fin], 1e-6)
    _NUM["crossing_err_mm"] = (1e3 * ce[fin]).tolist()
    gate("門 9 雑音ありの検出(12 コマ)から予測した交点 vs 閉形式の真値(20 本)",
         n_launch >= 10 and fin.all() and bool(np.all(ce[fin] < 3.0 * cs[fin] + 2e-3)) and rms < 0.02,
         "%d 本: rms %.1f mm、max %.1f mm、max |err|/σ_mc %.2f(閾値 3σ + 2 mm の床: MC 60 本の σ 自体が ±10 %% ぶれる)、先行時間 %.2f〜%.2f s" %
         (n_launch, 1e3 * rms, 1e3 * ce[fin].max(), ratio.max(), np.nanmin(lead), np.nanmax(lead)))

    # ── 10. 打点計画
    q0 = PK.fivebar_ik((X_DEF, 0.0), LINK)
    pr = PK.puck_slide_predict((0.5, 0.1), (-1.5, 0.3), TB, 4.0)
    c = PK.puck_crossing_point(pr, X_DEF)
    plan = PK.striker_plan(c, q0, LINK, omega_max=OMEGA)
    fkE = PK.fivebar_fk(plan["q_target"], LINK)["E"]
    tq = np.linspace(0, plan["t_cross"], 200)
    Q = PK.fivebar_trajectory(q0, plan, tq)
    rate = float(np.abs(np.diff(Q, axis=0) / np.diff(tq)[:, None]).max())
    fast = PK.striker_plan(PK.puck_crossing_point(PK.puck_slide_predict((-0.3, 0.3), (-8.0, -1.0), TB, 4.0), X_DEF), q0, LINK, omega_max=OMEGA)
    corner = PK.striker_plan({"t": 5.0, "p": np.array([X_DEF, 0.47]), "v": np.zeros(2)}, q0, LINK, omega_max=OMEGA)
    none_ = PK.striker_plan(None, q0, LINK)
    _NUM["plan"] = {"t_cross": plan["t_cross"], "t_move": plan["t_move"], "E": plan["E"].tolist()}
    gate("門 10 打点計画: 交点へ先回り(角速度 ≤ ω_max)、速すぎれば too_late、隅は unreachable、交わらなければ no_crossing",
         plan["feasible"] and np.linalg.norm(fkE - c["p"]) < 1e-9 and rate <= OMEGA * (1 + 1e-9) and plan["t_arrive"] <= c["t"]
         and fast["reason"] == "too_late" and corner["reason"] == "unreachable" and none_["reason"] == "no_crossing",
         "E = (%.3f, %.3f) at t = %.3f s、移動 %.3f s、max 角速度 %.2f rad/s; 8 m/s: %s; y = 0.47: %s" %
         (c["p"][0], c["p"][1], c["t"], plan["t_move"], rate, fast["reason"], corner["reason"]))

    # ── 11. モーションブラー
    v = np.array([-1.6, 0.0])
    shifts, pred_shift, rad = [], [], []
    for blur_px in (0.0, 2.0, 5.0, 10.0, 20.0):
        tau = blur_px / (np.linalg.norm(v) * CAM["px_per_m"])
        p0 = np.array([0.2, 0.05])
        d = PK.puck_detect(PK.puck_render_frame(CAM, p0, v=v, exposure=tau), CAM, radius_tol=1.5)
        tp = PK.puck_world_to_pixel(CAM, [p0])[0]
        shifts.append(d["col"] - tp[0]); pred_shift.append(-blur_px / 2.0); rad.append(d["radius"])
    shifts, pred_shift = np.array(shifts), np.array(pred_shift)
    berr = float(np.abs(shifts - pred_shift).max())
    _NUM["blur"] = {"blur_px": [0, 2, 5, 10, 20], "shift_px": shifts.tolist(), "pred_px": pred_shift.tolist(), "radius_px": rad}
    gate("門 11 モーションブラーは重心を v·τ/2 ずらす(コマの時刻 = 露光の始め; 露光の中央の時刻を打てば消える)", berr < 0.1,
         "ブラー 0/2/5/10/20 px → ずれ %s px、|Δ| max %.3f px" % (np.round(shifts, 2).tolist(), berr))

    # ── 12. 綴り壊し
    sp_ok = (_raises(PK.puck_slide_predict, (0, 0), (1, 0), TB, 1.0, model="Coulumb") and _raises(PK.puck_detect, PK.puck_render_frame(CAM, (0, 0)), CAM, mode="drak")
             and _raises(PK.fivebar_fk, (0.3, 2.0), LINK, branch="forwad") and _raises(PK.puck_table, e=1.2)
             and _raises(PK.puck_velocity_estimate, [0, 1], [[0, 0], [1, 1]], TB) and _raises(PK.puck_scene_mjcf, TB, fovy=0.0)
             and PK.puck_crossing_point(PK.puck_slide_predict((0, 0), (0.3, 0.0), TB, 5.0), X_DEF) is None)
    gate("門 12 綴り壊し・不正入力は fail-closed(model / mode / branch / e > 1 / N < 3 / fovy)、交わらなければ None", sp_ok)

    # ── 13. μ
    syn = PK.puck_synth_frames(TB, CAM, (0.5, 0.0), (-1.2, 0.2), fps=FPS, n_frames=36, rng=rng)
    mu_exact = PK.puck_mu_from_decel(syn["t"], syn["truth_xy"], TB["g"])["mu"]
    mu_det = PK.puck_mu_from_decel(syn["t"], PK.puck_track(syn["frames"], CAM)["xy"], TB["g"])["mu"]
    _NUM["mu_det"] = mu_det
    gate("門 13 μ を減速から(向きに沿った距離の二次式): 真値 → 1e-9、検出 36 コマ(0.3 s)→ 10 %",
         abs(mu_exact - TB["mu"]) < 1e-9 and abs(mu_det - TB["mu"]) / TB["mu"] < 0.10,
         "真値 %.1e、検出 μ = %.4f(真 %.4f、%.1f %%; 0.3 s の曲がりは 0.8 px)" % (abs(mu_exact - TB["mu"]), mu_det, TB["mu"], 100 * abs(mu_det - TB["mu"]) / TB["mu"]))

    # ── 14. 壁の e・kₜ
    syn = PK.puck_synth_frames(TB, CAM, (0.3, 0.30), (-1.0, 1.2), fps=FPS, n_frames=30, rng=rng)
    tr = PK.puck_track(syn["frames"], CAM)
    rw = PK.puck_restitution_from_wall(syn["t"][tr["frame"]], tr["xy"], TB)
    rw_ex = PK.puck_restitution_from_wall(syn["t"], syn["truth_xy"], TB)
    _NUM["restitution"] = {"e": rw["e"], "kt": rw["kt"]}
    gate("門 14 壁の e・kₜ を跳ねた軌跡から: 真値 → 1e-6、検出 → e 2 %・kₜ 3 %",
         abs(rw_ex["e"] - TB["e"]) < 1e-6 and abs(rw_ex["kt"] - TB["kt"]) < 1e-6 and abs(rw["e"] - TB["e"]) / TB["e"] < 0.02 and abs(rw["kt"] - TB["kt"]) / TB["kt"] < 0.03,
         "壁 %s: e = %.4f(真 %.2f)、kₜ = %.4f(真 %.2f)" % (rw["wall"], rw["e"], TB["e"], rw["kt"], TB["kt"]))

    # ── 15. 速いパック
    found = {}
    for step_px in (20.0, 35.0, 45.0, 80.0):
        sp = step_px / CAM["px_per_m"] * FPS
        syn = PK.puck_synth_frames(TB, CAM, (0.8, 0.0), (-sp, 0.0), fps=FPS, n_frames=10, rng=rng)
        found[step_px] = int(PK.puck_track(syn["frames"], CAM, max_jump_px=40.0)["found"].sum())
    _NUM["fast_found"] = found
    gate("門 15 速いパック: 1 コマ 20 / 35 px は全部繋がり、max_jump 40 px を超える 45 / 80 px で対応が切れる",
         found[20.0] == 10 and found[35.0] == 10 and found[45.0] < 10 and found[80.0] < 10,
         "10 コマ中 %s(45 px/コマ = %.1f m/s at %g fps)" % (found, 45 / CAM["px_per_m"] * FPS, FPS))

    # ── 16. kalman_ca
    syn = PK.puck_synth_frames(TB, CAM, (0.5, 0.0), (-1.2, 0.3), fps=FPS, n_frames=30, rng=rng)
    inn = float(np.abs(BT.kalman_ca(syn["truth_xy"], 1.0 / FPS, q=1e-3, r=1e-12)["innovation"][10:]).max())
    gate("門 16 既存 balltrack.kalman_ca を閉形式の経路に: 等加速度模型が厳密なので新息 → 0", inn < 1e-6, "10 コマ以降の max |新息| %.1e m" % inn)
    ctx["t_numpy"] = time.time() - t0
    print("  numpy の門 %.2f s" % ctx["t_numpy"])
    return ctx


# ======================================================================================================================
def full_part(ctx: dict) -> dict:
    print("== --full: MuJoCo(配布物の MJCF と自前の Coulomb MJCF)")
    ctx["mj"] = None
    try:
        import mujoco  # noqa: F401
    except ImportError:
        skip("門 17〜22", "mujoco が無い")
        return ctx
    try:
        xml, assets = PK.puck_challenge_mjcf()
    except (FileNotFoundError, OSError, ValueError) as exc:
        skip("門 17〜19・21〜22", "Challenge の MJCF が読めない: %s" % exc)
        xml = None
    rng = np.random.default_rng(7)
    tb_v = PK.puck_table(damping=0.005, mass=0.01)
    mj = {}
    if xml is not None:
        run = PK.puck_mujoco_run(xml, assets, (0.0, 0.0), (0.3, 1.0), fps=1000.0, duration=3.0, render=False)
        s = np.hypot(run["v"][:, 0], run["v"][:, 1])
        i_b = int(np.argmax(np.abs(np.diff(run["v"][:, 1])) > 0.05))
        slope = np.polyfit(run["t"][: i_b - 2], np.log(s[: i_b - 2]), 1)[0]
        e_n = -run["v"][i_b + 5, 1] / run["v"][i_b - 5, 1]
        kt_m = run["v"][i_b + 5, 0] / run["v"][i_b - 5, 0]
        mj.update({"decay_rate": float(slope), "e_n": float(e_n), "kt": float(kt_m), "y_hit": float(run["xy"][i_b, 1])})
        gate("門 17 Challenge の table.xml は単独で走り、速さは exp(−c/m t) で落ちる(粘性、Coulomb ではない); e・kₜ は測って出る",
             abs(slope + 0.5) / 0.5 < 0.01 and 0.5 < e_n < 1.0,
             "傾き %.4f /s(c/m = 0.5)、e_n = %.3f、kₜ = %.3f、衝突 y = %.4f(壁 %.4f)" % (slope, e_n, kt_m, run["xy"][i_b, 1], tb_v["y_half"] - tb_v["puck_radius"]))
        pr = PK.puck_slide_predict((0.0, 0.0), (0.3, 1.0), tb_v, 3.0, model="viscous")
        dpos = np.linalg.norm(PK.puck_state_at(pr, run["t"][: i_b - 2])["p"] - run["xy"][: i_b - 2], axis=1)
        mj["viscous_err_mm"] = float(1e3 * dpos.max())
        gate("門 18 粘性の閉形式 vs MuJoCo(最初の壁の前)", dpos.max() < 1e-3, "max |Δp| %.3f mm(%.2f s)" % (1e3 * dpos.max(), run["t"][i_b - 2]))
        tb_m = PK.puck_table(damping=0.005, mass=0.01, e=float(np.clip(e_n, 0, 1)), kt=float(np.clip(kt_m, 0, 1)))
        pr = PK.puck_slide_predict((0.0, 0.0), (0.3, 1.0), tb_m, 3.0, model="viscous", goals=False)
        j = min(i_b + 400, len(run["t"]) - 1)
        d_after = float(np.linalg.norm(PK.puck_state_at(pr, run["t"][j])["p"][0] - run["xy"][j]))
        mj["after_bounce_err_mm"] = 1e3 * d_after
        gate("門 19 測った e・kₜ で壁 1 回の後 0.4 s", d_after < 0.01, "|Δp| %.1f mm(軟接触は数 ms 続く、閉形式は瞬時)" % (1e3 * d_after))
    tb_c = PK.puck_table(mu=0.05, e=0.8, kt=0.9)
    run_c = PK.puck_mujoco_run(PK.puck_scene_mjcf(tb_c), None, (-0.5, 0.0), (1.0, 0.0), fps=1000.0, duration=1.2, render=False, puck_joint="puck_free")
    sc = np.hypot(run_c["v"][:, 0], run_c["v"][:, 1])
    m = (run_c["t"] > 0.05) & (sc > 0.2)
    a_fit = -np.polyfit(run_c["t"][m], sc[m], 1)[0]
    mj["coulomb_decel_err"] = abs(a_fit - tb_c["mu"] * tb_c["g"]) / (tb_c["mu"] * tb_c["g"])
    gate("門 20 自前の Coulomb MJCF(摩擦のある平面の円柱): 速さが μg で直線に落ちる", mj["coulomb_decel_err"] < 0.05,
         "a = %.4f m/s²、μg = %.4f(%.1f %%; 軟接触の摩擦は厳密な Coulomb でない)" % (a_fit, tb_c["mu"] * tb_c["g"], 100 * mj["coulomb_decel_err"]))
    if xml is not None:
        shape = (480, 800)
        cam_m = PK.puck_pinhole_camera(tb_v, 1.5, 50.0, shape)
        run = PK.puck_mujoco_run(xml, assets, (0.3, 0.2), (-1.2, 0.4), fps=50.0, duration=0.3, render=True, shape=shape)
        det = [PK.puck_detect(f.astype(np.float64) / 255.0, cam_m, mode="color", color=(1.0, 0.32, 0.32), color_tol=0.45, radius_tol=0.6) for f in run["frames"]]
        if not all(d is not None for d in det):
            gate("門 21 MuJoCo の描画 → 色検出 → 針穴ホモグラフィ", False, "パックが見つからないコマがある")
            bias = np.zeros(2)
        else:
            dxy = np.array([[d["x"], d["y"]] for d in det]) - run["xy"]
            bias = dxy.mean(0)
            scatter = float(np.sqrt(np.mean((dxy - bias) ** 2)))
            mj["detect_bias_mm"] = (1e3 * bias).tolist(); mj["detect_scatter_mm"] = 1e3 * scatter
            gate("門 21 MuJoCo の描画 → 色検出 → 針穴ホモグラフィ vs 真値", np.linalg.norm(bias) < 5e-3 and scatter < 1.5e-3,
                 "偏り (%.2f, %.2f) mm、散らばり %.2f mm(%.3f px、%.0f px/m; 偏りは site の高さと描画の量子化 → 鎖では引く)"
                 % (1e3 * bias[0], 1e3 * bias[1], 1e3 * scatter, scatter * cam_m["px_per_m"], cam_m["px_per_m"]))
        q0 = PK.fivebar_ik((X_DEF, 0.0), LINK)
        ri = PK.fivebar_reach_interval(LINK, X_DEF)
        rows = []
        for k in range(20):
            p0 = rng.uniform([0.2, -0.3], [0.7, 0.3])
            ang = rng.uniform(-0.7, 0.7)
            sp = rng.uniform(0.8, 2.0)
            v0 = sp * np.array([-np.cos(ang), np.sin(ang)])
            run = PK.puck_mujoco_run(xml, assets, p0, v0, fps=50.0, duration=2.0, render=False)
            xs = run["xy"][:, 0]
            idx = np.where((xs[:-1] > X_DEF) & (xs[1:] <= X_DEF))[0]
            if idx.size == 0:
                rows.append({"truth": None})
                continue
            i0 = idx[0]
            f = (xs[i0] - X_DEF) / (xs[i0] - xs[i0 + 1])
            y_true = run["xy"][i0, 1] + f * (run["xy"][i0 + 1, 1] - run["xy"][i0, 1])
            t_true = run["t"][i0] + f * (run["t"][i0 + 1] - run["t"][i0])
            run_r = PK.puck_mujoco_run(xml, assets, p0, v0, fps=50.0, duration=0.24, render=True, shape=shape)
            det = [PK.puck_detect(fr.astype(np.float64) / 255.0, cam_m, mode="color", color=(1.0, 0.32, 0.32), color_tol=0.45, radius_tol=0.6) for fr in run_r["frames"]]
            tt = np.array([t for t, d in zip(run_r["t"], det) if d is not None])
            xy = np.array([[d["x"], d["y"]] for d in det if d is not None]) - bias
            ve = PK.puck_velocity_estimate(tt, xy, tb_m, model="viscous")
            c = PK.puck_crossing_point(PK.puck_slide_predict(ve["p_ref"], ve["v_ref"], tb_m, 4.0, model="viscous", goals=False, t0=ve["t_ref"]), X_DEF)
            plan = PK.striker_plan(c, q0, LINK, omega_max=OMEGA, t_now=float(ve["t_ref"]))
            err_y = abs(c["p"][1] - y_true) if c is not None else np.inf
            err_t = abs(c["t"] - t_true) if c is not None else np.inf
            reachable = ri["y_lo"] <= y_true <= ri["y_hi"]
            rows.append({"truth": (float(y_true), float(t_true)), "err_y_mm": 1e3 * err_y, "err_t_ms": 1e3 * err_t, "reason": plan["reason"],
                         "hit": bool(plan["feasible"] and err_y < TB["puck_radius"] + MALLET_R), "reachable": bool(reachable)})
        with_truth = [r_ for r_ in rows if r_["truth"] is not None]
        reach_rows = [r_ for r_ in with_truth if r_["reachable"]]
        hits = sum(r_["hit"] for r_ in reach_rows)
        errs = np.array([r_["err_y_mm"] for r_ in with_truth if np.isfinite(r_["err_y_mm"])])
        errs_t = np.array([r_["err_t_ms"] for r_ in with_truth if np.isfinite(r_["err_t_ms"])])
        reasons = {}
        for r_ in with_truth:
            reasons[r_["reason"]] = reasons.get(r_["reason"], 0) + 1
        mj["pipeline"] = {"crossed": len(with_truth), "reachable": len(reach_rows), "hits": hits, "err_y_mm": errs.tolist(), "err_t_ms": errs_t.tolist(), "reasons": reasons}
        gate("門 22 全鎖 20 本(描画 → 検出 → 粘性の最小二乗 → 測った e・kₜ で予測 → 5 節リンクの計画): 交点はパック + 打具の半径の内側、届く本は全部打つ",
             len(with_truth) >= 10 and len(errs) == len(with_truth) and errs.max() < 1e3 * (TB["puck_radius"] + MALLET_R) and hits == len(reach_rows) and len(reach_rows) >= 5,
             "20 本中 %d 本が守備線を横切り、届く区間 |y| ≤ %.3f の %d 本は %d 本打てた; %d 本は届かない隅(辞退、正直); 交点誤差 中央 %.1f mm・max %.1f mm、時刻 max %.0f ms; %s"
             % (len(with_truth), ri["y_hi"], len(reach_rows), hits, len(with_truth) - len(reach_rows), np.median(errs), errs.max(), errs_t.max(), reasons))
        mj["xml"] = xml; mj["assets"] = assets; mj["tb_m"] = tb_m
    ctx["mj"] = mj
    return ctx


# ======================================================================================================================
def _rgb(gray):
    g = np.clip(np.asarray(gray, np.float64), 0, 1)
    return np.stack([g, g, g], axis=-1)


def figures(ctx: dict) -> None:
    print("== 図")
    rng = np.random.default_rng(7)
    p0, v0 = np.array([0.45, 0.12]), np.array([-1.5, 0.75])
    truth_c = PK.puck_crossing_point(PK.puck_slide_predict(p0, v0, TB, 6.0), X_DEF)

    def path_px(cam, pred, t_to, t_from=0.0):
        return PK.puck_world_to_pixel(cam, PK.puck_state_at(pred, np.linspace(t_from, t_to, 200))["p"])

    # ── 1. 343 px/m のコマ + 検出 + 予測線 + 交点、パックの等倍切り出し(副画素の重心)
    cam_h = PK.puck_camera(TB, px_per_m=343.0)
    syn = PK.puck_synth_frames(TB, cam_h, p0, v0, fps=FPS, n_frames=16, noise=0.01, rng=rng)
    tr = PK.puck_track(syn["frames"], cam_h)
    ve = PK.puck_velocity_estimate(syn["t"], tr["xy"], TB)
    pr = PK.puck_slide_predict(ve["p_ref"], ve["v_ref"], TB, 4.0, t0=ve["t_ref"])
    c = PK.puck_crossing_point(pr, X_DEF)
    xdef = PK.puck_world_to_pixel(cam_h, [[X_DEF, -TB["y_half"]], [X_DEF, TB["y_half"]]])
    frame = _rgb(syn["frames"][-1])
    img = ID.draw_line(frame, xdef[0], xdef[1], color="reference", width=1)
    img = ID.draw_polyline(img, path_px(cam_h, pr, c["t"] + 0.3, ve["t_ref"]), color="emphasis", width=2)
    for k in range(tr["frame"].size):
        img = ID.draw_circle(img, (tr["col"][k], tr["row"][k]), 2.0, color="right", fill=True)
    cp = PK.puck_world_to_pixel(cam_h, [c["p"]])[0]
    img = AN.crosshair(img, cp, color="emphasis", gap=8, extent=22)
    err_mm = 1e3 * abs(c["p"][1] - truth_c["p"][1])
    img = AN.text_box(img, "crossing in %.0f ms, err %.1f mm" % (1e3 * (c["t"] - ve["t_ref"]), err_mm), (cp[0] + 14, cp[1] - 50), color="emphasis")
    # 等倍切り出し(最近傍 ×8、副画素の重心を十字で)
    col, row = tr["col"][-1], tr["row"][-1]
    rp = TB["puck_radius"] * cam_h["px_per_m"]
    half = int(rp + 6)
    r0, c0 = int(round(row)) - half, int(round(col)) - half
    crop = frame[r0:r0 + 2 * half, c0:c0 + 2 * half]
    up = 8
    crop_up = np.repeat(np.repeat(crop, up, axis=0), up, axis=1)
    cc = ((col - c0 + 0.5) * up, (row - r0 + 0.5) * up)
    crop_up = AN.crosshair(crop_up, cc, color="right", gap=6, extent=40)
    crop_up = ID.draw_circle(crop_up, cc, rp * up, color="emphasis", width=1)
    tp = syn["truth_px"][-1]
    crop_up = AN.text_box(crop_up, "centroid err %.3f px" % float(np.hypot(col - tp[0], row - tp[1])), (8, 8), color="neutral")
    H1, W1 = img.shape[:2]
    H2, W2 = crop_up.shape[:2]
    Hc = max(H1, H2)
    canvas = np.full((Hc, W1 + 12 + W2, 3), 0.25)
    canvas[:H1, :W1] = img
    canvas[:H2, W1 + 12:W1 + 12 + W2] = crop_up
    figs.save("airhockey_frame_detect_predict", canvas,
              caption="343 px/m の真上カメラの 16 コマ目(120 fps、雑音 σ 0.01)。緑の点 = 検出した中心 16 個、橙 = 等減速 + 壁反射の予測線、十字 = 守備線 x = −0.75 "
                      "との交点(真値との差 %.1f mm、%.0f ms 先)。右 = パックの等倍切り出し(最近傍 %d 倍、%d×%d px)に副画素の重心(緑の十字、真値との差 %.3f px)と"
                      "期待半径の円。重心は被覆率で読むので画素の 1/100 まで出る —— 門 7 は 50 点で max %.4f px。"
                      % (err_mm, 1e3 * (c["t"] - ve["t_ref"]), up, 2 * half, 2 * half, float(np.hypot(col - tp[0], row - tp[1])), _NUM["centroid_max_px"]))

    # ── 2. GIF: 予測の扇がコマを重ねるほど細る(粗いカメラ 100 px/m・雑音 σ 0.06)
    cam_c = PK.puck_camera(TB, px_per_m=100.0)
    syn_c = PK.puck_synth_frames(TB, cam_c, p0, v0, fps=FPS, n_frames=16, noise=0.06, rng=rng)
    tr_c = PK.puck_track(syn_c["frames"], cam_c, thresh=0.75)
    xdef_c = PK.puck_world_to_pixel(cam_c, [[X_DEF, -TB["y_half"]], [X_DEF, TB["y_half"]]])
    frames_gif, bands = [], []
    for N in range(3, 17):
        veN = PK.puck_velocity_estimate(syn_c["t"][:N], tr_c["xy"][:N], TB)
        prN = PK.puck_slide_predict(veN["p_ref"], veN["v_ref"], TB, 4.0, t0=veN["t_ref"])
        ys = []
        for _ in range(80):
            cc2 = PK.puck_crossing_point(PK.puck_slide_predict(veN["p_ref"] + rng.normal(0, veN["sigma_p"], 2), veN["v_ref"] + rng.normal(0, veN["sigma_v"], 2),
                                                                TB, 4.0, t0=veN["t_ref"]), X_DEF)
            if cc2 is not None:
                ys.append(cc2["p"][1])
        im = np.kron(_rgb(syn_c["frames"][N - 1]), np.ones((2, 2, 1)))
        im = ID.draw_line(im, 2 * xdef_c[0], 2 * xdef_c[1], color="reference", width=1)
        cN = PK.puck_crossing_point(prN, X_DEF)
        t_to = (cN["t"] if cN else veN["t_ref"] + 1.0) + 0.2
        im = ID.draw_polyline(im, 2 * path_px(cam_c, prN, t_to, veN["t_ref"]), color="emphasis", width=2)
        band = np.nan
        if len(ys) > 2:
            lo, hi = np.percentile(ys, [2.5, 97.5])
            band = 1e3 * (hi - lo)
            a = 2 * PK.puck_world_to_pixel(cam_c, [[X_DEF, lo], [X_DEF, hi]])
            im = ID.draw_line(im, a[0] - [5, 0], a[1] - [5, 0], color="wrong", width=5)
            im = ID.draw_line(im, a[0] + [5, 0], a[1] + [5, 0], color="wrong", width=5)
            bands.append((N, band))
        im = AN.crosshair(im, 2 * PK.puck_world_to_pixel(cam_c, [truth_c["p"]])[0], color="right", gap=6, extent=16)
        im = AN.text_box(im, "N = %2d frames   95 %% band = %.0f mm" % (N, band), (10, 8), color="neutral")
        frames_gif.append((np.clip(im, 0, 1) * 255).astype(np.uint8))
    _NUM["cone_band_mm_vs_N"] = bands
    figs.save_gif("airhockey_prediction_cone_narrows", frames_gif, fps=3,
                  caption="粗いカメラ(100 px/m、雑音 σ 0.06)でも、コマが増えるほど守備線上の交点の 95 %% 帯(赤)が細る: N = 3 で %.0f mm → N = 16 で %.0f mm。緑の十字 = 真の交点。"
                          % (bands[0][1], bands[-1][1]))

    # ── 3. 速度の誤差 vs N
    vn = _NUM["vel_err_vs_N"]
    Ns = np.array(vn["N"])
    figs.save_plot("airhockey_velocity_error_vs_N", [("|v_hat - v| from detections", Ns, 1e3 * np.array(vn["err_mps"])), ("3 sigma_v (least squares)", Ns, 3e3 * np.sqrt(2) * np.array(vn["sigma_v"]))],
                   xlabel="frames N (120 fps)", ylabel="velocity error [mm/s]", title="speed %.2f m/s" % vn["speed"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                   caption="検出から最小二乗で出した速度の誤差は N とともに縮み、最小二乗の分散の 3σ(破線)の内側に収まる(N = 12 で %.2f %%、N = 24 で %.2f %%)。"
                           % (100 * vn["err_mps"][Ns.tolist().index(12)] / vn["speed"], 100 * vn["err_mps"][-1] / vn["speed"]))

    # ── 4. 5 節リンクが交点へ届く GIF
    syn = PK.puck_synth_frames(TB, CAM, p0, v0, fps=FPS, n_frames=16, noise=0.01, rng=rng)
    tr = PK.puck_track(syn["frames"], CAM)
    ve = PK.puck_velocity_estimate(syn["t"][:8], tr["xy"][:8], TB)
    pr = PK.puck_slide_predict(ve["p_ref"], ve["v_ref"], TB, 4.0, t0=ve["t_ref"])
    c = PK.puck_crossing_point(pr, X_DEF)
    q0 = PK.fivebar_ik((X_DEF, 0.0), LINK)
    plan = PK.striker_plan(c, q0, LINK, omega_max=OMEGA, t_now=float(ve["t_ref"]))
    cam_w = PK.puck_camera(TB, px_per_m=200.0, margin=0.14)
    tt = np.linspace(ve["t_ref"], c["t"] + 0.05, 18)
    Q = PK.fivebar_trajectory(q0, plan, tt)
    truth_path = PK.puck_state_at(syn["pred"], tt)["p"]
    frames_gif = []
    for i, t in enumerate(tt):
        im = _rgb(PK.puck_render_frame(cam_w, truth_path[i]))
        fk = PK.fivebar_fk(Q[i], LINK)
        A1, A2, B1, B2, E = (PK.puck_world_to_pixel(cam_w, [x])[0] for x in (LINK["A1"], LINK["A2"], fk["B1"], fk["B2"], fk["E"]))
        im = ID.draw_polyline(im, [A1, B1, E, B2, A2], color="emphasis", width=3)
        for P_ in (A1, A2, B1, B2):
            im = ID.draw_circle(im, P_, 4, color="neutral", fill=True)
        im = ID.draw_circle(im, E, MALLET_R * cam_w["px_per_m"], color="right", width=2)
        im = ID.draw_polyline(im, PK.puck_world_to_pixel(cam_w, PK.puck_state_at(pr, np.linspace(ve["t_ref"], c["t"], 100))["p"]), color="reference", width=1)
        im = AN.text_box(im, "t = %.0f ms  %s  (move %.0f ms, cross %.0f ms)" % (1e3 * (t - ve["t_ref"]), plan["reason"], 1e3 * plan["t_move"], 1e3 * (c["t"] - ve["t_ref"])), (10, 8), color="neutral")
        frames_gif.append((np.clip(im, 0, 1) * 255).astype(np.uint8))
    figs.save_gif("airhockey_fivebar_intercept", frames_gif, fps=6,
                  caption="8 コマで予測した交点へ、5 節リンク(一定角速度 ≤ %g rad/s、寸法は仮定)が %.0f ms で先回りして打具(緑の円、半径 %.0f mm は仮定)を置く。"
                          "交点の到着は %.0f ms 先。" % (OMEGA, 1e3 * plan["t_move"], 1e3 * MALLET_R, 1e3 * (c["t"] - ve["t_ref"])))

    # ── 5. 壊れる場所
    bl = _NUM["blur"]
    pa = figs.render_plot([("centroid shift", np.array(bl["blur_px"], float), np.array(bl["shift_px"])), ("-v tau / 2", np.array(bl["blur_px"], float), np.array(bl["pred_px"]))],
                          xlabel="blur length v tau [px]", ylabel="centroid shift [px]", title="(a) motion blur", styles=[None, "dashed"], colors=["emphasis", "reference"], size=(560, 360))
    im = _rgb(PK.puck_render_frame(CAM, (0.3, 0.30)))
    xdef = PK.puck_world_to_pixel(CAM, [[X_DEF, -TB["y_half"]], [X_DEF, TB["y_half"]]])
    for kt in (0.6, 0.7, 0.8, 0.9, 1.0):
        prk = PK.puck_slide_predict((0.3, 0.30), (-1.0, 1.2), PK.puck_table(mu=0.02, e=0.8, kt=kt), 2.0)
        im = ID.draw_polyline(im, path_px(CAM, prk, 1.6), color="emphasis" if kt == 0.9 else "neutral", width=1)
    im = ID.draw_line(im, xdef[0], xdef[1], color="reference", width=1)
    im = AN.text_box(im, "(b) kt = 0.6 ... 1.0 (wall spin unknown)", (10, 8), color="neutral")
    ff = _NUM["fast_found"]
    pc = figs.render_plot([("frames kept of 10", np.array(sorted(ff)), np.array([ff[k] for k in sorted(ff)], float))], xlabel="puck step per frame [px] (max_jump = 40)",
                          ylabel="frames tracked", title="(c) under-sampled puck", colors=["wrong"], size=(560, 360))
    figs.save_grid("airhockey_where_it_breaks", [pa, im, pc], ncols=3, captions=["blur", "kt unknown", "fast puck"],
                   caption="どこで壊れるか。(a) モーションブラーは重心を v·τ/2 ずらす(閉形式どおり、|Δ| max %.3f px; 露光の中央の時刻を打てば消える)。"
                           "(b) 壁の接線保持 kₜ を知らないと跳ねた後の予測が扇に開く(0.6〜1.0)。(c) 1 コマの移動が max_jump 40 px を超えると ball_track の対応が切れる"
                           "(10 コマ中 %s)。" % (float(np.abs(np.array(bl["shift_px"]) - np.array(bl["pred_px"])).max()), {int(k): v for k, v in ff.items()}))

    # ── 6. MuJoCo vs 閉形式(--full なら 3 本、無ければ閉形式の 2 本)
    tt6 = np.linspace(0.0, 2.0, 401)
    mj = ctx.get("mj") or {}
    e_use = float(np.clip(mj.get("e_n", 0.8), 0, 1)); kt_use = float(np.clip(mj.get("kt", 0.9), 0, 1))
    tbv = PK.puck_table(damping=0.005, mass=0.01, e=e_use, kt=kt_use)
    sv = np.linalg.norm(PK.puck_state_at(PK.puck_slide_predict((0.0, 0.0), (0.3, 1.0), tbv, 2.0, model="viscous", goals=False), tt6)["v"], axis=1)
    tbc = PK.puck_table(mu=0.02, e=e_use, kt=kt_use)
    sc = np.linalg.norm(PK.puck_state_at(PK.puck_slide_predict((0.0, 0.0), (0.3, 1.0), tbc, 2.0, model="coulomb", goals=False), tt6)["v"], axis=1)
    series = [("viscous closed form (c/m = 0.5 /s)", tt6, sv), ("Coulomb mu = 0.02", tt6, sc)]
    styles = ["dashed", "dotted"]; colors = ["reference", "wrong"]
    if mj.get("xml") is not None:
        run = PK.puck_mujoco_run(mj["xml"], mj["assets"], (0.0, 0.0), (0.3, 1.0), fps=200.0, duration=2.0, render=False)
        series = [("MuJoCo (Challenge table.xml)", run["t"], np.hypot(run["v"][:, 0], run["v"][:, 1]))] + series
        styles = [None] + styles; colors = ["emphasis"] + colors
        cap = ("Challenge の台では速さが指数で落ちる(粘性減衰 c/m = 0.5 /s、実測の傾き %.4f /s)。測った e_n = %.3f・kₜ = %.3f を入れた粘性の閉形式(破線)は MuJoCo に重なり"
               "(壁の前 %.3f mm、壁 1 回の後 %.1f mm)、Coulomb の直線減速(点線)は別の模型 —— 第 2 実装が模型の違いを暴いた。"
               % (mj["decay_rate"], mj["e_n"], mj["kt"], mj["viscous_err_mm"], mj["after_bounce_err_mm"]))
    else:
        cap = ("閉形式の 2 模型(粘性減衰 c/m = 0.5 /s と Coulomb μ = 0.02)の速さ。MuJoCo の実測線は --full(mujoco + FULLSEYE_AIRHOCKEY_DATA)のときだけ重ねる: "
               "Challenge の台は粘性で、Coulomb の直線減速とは別の模型。")
    figs.save_plot("airhockey_mujoco_vs_closed_form", series, xlabel="t [s]", ylabel="speed [m/s]", title="puck speed", styles=styles, colors=colors, caption=cap)
    print("  figures:", figs.errors() or "ok")


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    ctx = numpy_part()
    if FULL:
        ctx = full_part(ctx)
    else:
        skip("門 17〜22(MuJoCo)", "--full のときだけ(mujoco と FULLSEYE_AIRHOCKEY_DATA)")
    if figs.enabled():
        figures(ctx)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
