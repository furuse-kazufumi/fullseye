# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ⑲: 卓球の球を先駆者の目で測る —— 真値つきの台で、多カメラ追跡・三角測量・軌道予測・跳ね・スピンを定理で採点する。

ロボット卓球の視覚(1988 年の MIT のロボットから、今の 4 カメラ・数百 fps の研究機まで)は同じ構えでできている:
複数のカメラで球を見つけ → 三角測量で 3-D の点にし → 抗力とマグヌスの入った運動方程式で先を読み → 跳ねを越えて予測し →
できれば模様からスピンを測る。この PoC はその一式を numpy の op(:mod:`ballistics` / :mod:`balltrack` / :mod:`ballworld`)で組み、
**世界の側が持つ真値**(球の中心・姿勢・接触時刻・角速度は生成時に決めた式)で採点する。台は ITTF の寸法、球は 40 mm の薄殻。

門(真値の出どころ):
  1. **真空の恒等式**: 抗力もマグヌスも 0 なら RK4 の飛翔は閉形式の放物線と 1e-12、放物線の最小二乗は g = 9.81 を 1e-9 で戻す。
  2. **跳ねの定理**: 乱数 500 通りの衝突で接触点まわりの角運動量が保存(1e-12)、運動エネルギーは増えず、v_z' = −e v_z。
  3. **頂点の等比と ITTF の跳ね**: 落として跳ねる頂点は e^{2k}h₀(1e-6)、e = 0.9 で 30.5 cm から落とすと最初の跳ねは 24.7 cm
     —— ITTF の球の跳ねの規格(30.5 cm から 24〜26 cm)の中(公表値、規格本文で要確認)。頂点列と接触間隔からの e の推定は 1e-5 で戻る。
  4. **検出はサブピクセル**: 2 台のカメラ(1024 × 800、55°)で球(像で半径 ≈ 4 px)を色度で検出した中心は真値の投影と中央値 < 0.3 px。
  5. **三角測量は真値に戻る**: 真値の投影を DLT に入れると 1e-9 m。検出から三角測量した 3-D の軌跡は真値と中央値 < 3 mm。
  6. **Kalman は物理を知っている**: 等加速度モデルは放物線に厳密なので、真値を入れた新息は収束後 1e-9。検出からの推定速度は真値と < 0.15 m/s。
  7. **跳ねの検出**: 3-D の軌跡の z の局所最小は、世界の接触時刻と 1 コマ(10 ms)以内。
  8. **跳ねを越える予測**: 跳ねる前の 15 コマから初期状態を当て、抗力 + マグヌス + 跳ねの運動方程式で先を読む —— 真のスピンを
     知っていれば着地点は真値と < 2 cm、スピンを無視すると外れる(その差 = マグヌスの分、数字で出す)。
  9. **反発係数を測る**: 跳ねの前後の区間ごとに放物線を当てて接触時の v_z を出し、e = −v_z'/v_z が真値 0.9 と 2 % 以内。
 10. **スピンを模様から**: 跳ね際の近接カメラ(1000 fps、20 コマ、ストロボ照明)で球の黒い模様(14 個、見えるのは 4〜6 個)を検出し、前のコマと向きで対応づけて
     Kabsch で回転を当てた角速度が真値と 5 % 以内。
 11. **ラリーの本数が指標**(ユーザー指定): 自由に動く 2 本のラケットで打ち合う。片方は勝つ打ち方(遠い隅を速く)、片方は前回に近い少しずらした
     位置へ返す。打つ前に真の物理で先読みして外すなら巻き戻す(回数を数える)。送り合いは上限まで続き、攻める側が入ると短く終わり、
     知覚に雑音を足すと短くなる —— 知覚・予測・制御の一式を 1 つの数で採点する。

正直に書くこと: 球の検出は色(橙)が既知の合成映像で、実写の照明・ぼけ・背景は無い。スピンの近接カメラは球が視野に入る 20 ms だけの
「都合のよい」配置。空力係数(C_d = 0.4、C_L のスピン比モデル)は文献の代表値で、真値は同じ式で作っている(空力の門ではない)。
先駆者の実機は実写の 3〜4 台のカメラで、ここは 2 + 1 台の合成。

Run: py -3.11 examples/poc_ball_bounce.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import ballistics as B  # noqa: E402
import balltrack as BT  # noqa: E402
import ballworld as BW  # noqa: E402
import driveworld as DW  # noqa: E402
import racket as RK  # noqa: E402
import annotate as AN  # noqa: E402

T0 = time.time()
FPS = 100                            # 追跡カメラ
FPS_SPIN = 1000                      # 近接カメラ
T_END = 0.6
BALL_COLOR = (1.0, 0.55, 0.05)
E_TRUE, MU_TRUE = 0.9, 0.25
OK = []


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def _circle(img, c, r, color):
    return np.asarray(AN.crosshair(img, (float(c[0]), float(c[1])), color=color, width=1, gap=int(r) + 2, extent=int(r) + 8))


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    bp = B.ball_params()
    ip = B.impact_params(E_TRUE, MU_TRUE)
    # ─────────────────────────────── 1. 力学の定理 ─────────────────────────────
    print("== 1. 力学の定理: 真空の恒等式・跳ねの角運動量・頂点の等比・ITTF の跳ね")
    bv = B.ball_params(rho=0.0)
    f = B.flight_ode([0, 0, 1], [2, 0.5, 3], [0, 0, 0], bv, 0.6, 1e-3)
    vac = np.abs(f["p"] - B.flight_vacuum([0, 0, 1], [2, 0.5, 3], f["t"])).max()
    fit = B.fit_parabola(f["t"], f["p"])
    gate("真空の恒等式: RK4 = 閉形式(1e-12)、放物線の当てはめ g = 9.81(1e-9)", vac < 1e-12 and abs(fit["g"] - 9.81) < 1e-9,
         "差 %.1e、g %.9f" % (vac, fit["g"]))
    rng = np.random.default_rng(19)
    worst, e_ok, reg = 0.0, True, {"grip": 0, "slip": 0}
    for _ in range(500):
        v = rng.normal(0, 5, 3)
        v[2] = -abs(v[2]) - 0.1
        w = rng.normal(0, 200, 3)
        ipk = B.impact_params(rng.uniform(0.3, 1.0), rng.uniform(0, 0.6))
        b = B.bounce(v, w, [0, 0, 1], bp, ipk)
        L0 = B.contact_angular_momentum(v, w, [0, 0, 1], bp)
        L1 = B.contact_angular_momentum(b["v"], b["omega"], [0, 0, 1], bp)
        worst = max(worst, np.abs(L1 - L0).max() / max(1e-12, np.abs(L0).max()))
        E0 = 0.5 * bp["mass"] * v @ v + 0.5 * bp["inertia"] * w @ w
        E1 = 0.5 * bp["mass"] * b["v"] @ b["v"] + 0.5 * bp["inertia"] * b["omega"] @ b["omega"]
        e_ok &= E1 <= E0 + 1e-12 and abs(b["v"][2] + ipk["e"] * v[2]) < 1e-12
        reg[b["regime"]] += 1
    print("  乱数 500 通りの衝突(e ∈ [0.3, 1]、μ ∈ [0, 0.6]): 接触点まわりの角運動量の相対誤差 最大 %.1e、転がりに移る %d / 滑ったまま %d" % (
        worst, reg["grip"], reg["slip"]))
    gate("跳ねの定理: 角運動量保存(1e-12)、エネルギーは増えない、v_z' = −e v_z", worst < 1e-12 and e_ok)
    h0 = 0.305
    drop = B.flight_simulate([0, 0, h0 + bp["radius"]], [0, 0, 0], [0, 0, 0], bv, ip, 5.0, 5e-4)     # 総時間 4.74 s より長く
    ct = np.array([c["t"] for c in drop["contacts"]])
    apex = []
    for i in range(len(ct) - 1):
        m = (drop["t"] > ct[i]) & (drop["t"] < ct[i + 1])
        if m.any():
            apex.append(drop["p"][m, 2].max() - bp["radius"])
    apex = np.asarray(apex)
    ap_err = np.abs(apex[:5] - B.apex_sequence(h0, E_TRUE, 5)[1:]).max()
    e_ap = B.restitution_from_apexes(np.r_[h0, apex[:6]])["e"]
    e_iv = B.restitution_from_intervals(ct[:8])["e"]
    spec = (0.24, 0.26)
    print("  30.5 cm から落とす(e = %.2f): 頂点 %s cm、閉形式 e^{2k}h₀ との差 %.1e。最初の跳ね %.1f cm は ITTF の規格 24〜26 cm の中。"
          "頂点列からの e %.6f、接触間隔からの e %.6f、総時間 %.3f s(閉形式 %.3f s)" % (
              E_TRUE, np.round(100 * apex[:4], 1).tolist(), ap_err, 100 * apex[0], e_ap, e_iv, drop["rest_t"] or float("nan"), B.bounce_total_time(h0, E_TRUE)))
    gate("頂点の等比(1e-6)と ITTF の跳ね(24〜26 cm)、e の推定(1e-5)", ap_err < 1e-6 and spec[0] <= apex[0] <= spec[1]
         and abs(e_ap - E_TRUE) < 1e-5 and abs(e_iv - E_TRUE) < 1e-5)

    # ─────────────────────────────── 2. 世界と真値 ─────────────────────────────
    print("== 2. ITTF の台に球(40 mm、模様 14 個)を置き、トップスピンの打球を %d fps で %.1f 秒撮る(カメラ 2 台 + 近接 1 台)" % (FPS, T_END))
    tp = BW.table_params()
    H = tp["height"]
    world = BW.table_world(tp)
    MARKERS = [((1, 0, 0), 11.0), ((-1, 0, 0), 11.0), ((0, 1, 0), 11.0), ((0, -1, 0), 11.0), ((0, 0, 1), 11.0), ((0, 0, -1), 11.0)]
    MARKERS += [((sx, sy, sz), 11.0) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    mesh = BW.ball_mesh(bp["radius"], 3, BALL_COLOR, markers=MARKERS)          # 6 軸 + 8 隅 = 14 個の黒い点(常に 4〜6 個が見える)
    p0 = np.array([-1.30, 0.15, H + 0.28])
    v0 = np.array([6.5, -0.35, 1.15])
    w0 = np.array([0.0, 240.0, 0.0])           # トップスピン(+x へ進む球の上面が前へ)
    sim = B.flight_simulate(p0, v0, w0, bp, ip, T_END, 1e-4, table_z=H, table_xy=world["bounds"])
    contact = sim["contacts"][0]
    print("  真値: 接触 t = %.4f s、点 (%.3f, %.3f)、v_in %s → v_out %s、ω %s → %s(%s)" % (
        contact["t"], contact["p"][0], contact["p"][1], np.round(contact["v_in"], 2), np.round(contact["v_out"], 2),
        np.round(contact["omega_in"], 1), np.round(contact["omega_out"], 1), contact["regime"]))
    t_frames = np.arange(0.0, T_END + 1e-9, 1.0 / FPS)
    P_true = np.column_stack([np.interp(t_frames, sim["t"], sim["p"][:, k]) for k in range(3)])
    V_true = np.column_stack([np.interp(t_frames, sim["t"], sim["v"][:, k]) for k in range(3)])
    W_true = np.column_stack([np.interp(t_frames, sim["t"], sim["omega"][:, k]) for k in range(3)])
    R = np.eye(3)
    R_true = []
    t_prev = 0.0
    for k, t in enumerate(t_frames):                       # 姿勢の積分(コマの間は角速度一定とみなす)
        if k:
            R = BW.rotation_from_omega(W_true[k - 1], t - t_prev) @ R
        R_true.append(R.copy())
        t_prev = t
    ball = BW.add_ball(world, mesh, P_true[0], R_true[0])
    rig = BW.camera_rig(tp, n=2, width=1024, height_px=800, fov_deg=55.0)
    frames = [[] for _ in rig]
    truth_uv = [[] for _ in rig]
    t_r = time.time()
    for k, t in enumerate(t_frames):
        BW.ball_set_pose(world, ball, P_true[k], R_true[k])
        for c, cam in enumerate(rig):
            view = DW.world_camera(world, cam["pose"], cam["K"], cam["width"], cam["height"])
            frames[c].append(view["color"])
            truth_uv[c].append(BW.ball_truth(world, ball, cam)["uv"])
    print("  %d コマ × %d 台を描画(%.1f s)" % (len(t_frames), len(rig), time.time() - t_r))

    # ─────────────────────────────── 3. 検出 → 追跡 → 三角測量 → Kalman ─────────────────────────────
    print("== 3. 色度で検出 → 等速予測で追跡 → DLT で三角測量 → 等加速度 Kalman")
    tracks, det_err = [], []
    for c, cam in enumerate(rig):
        dets = [BT.ball_detect(fr, mode="chroma", color=BALL_COLOR, color_tol=0.12, radius_range=(1.5, 30)) for fr in frames[c]]
        tr = BT.ball_track(dets, max_jump=60.0)
        tracks.append(tr)
        tu = np.asarray(truth_uv[c])
        det_err += list(np.hypot(tr["col"] - tu[tr["frame"], 0], tr["row"] - tu[tr["frame"], 1]))
    det_err = np.asarray(det_err)
    print("  検出 %d / %d コマ、中心の誤差 中央値 %.3f px、90 %% 点 %.3f px、最大 %.3f px(像の半径 ≈ %.1f px)" % (
        sum(len(t["frame"]) for t in tracks), 2 * len(t_frames), np.median(det_err), np.percentile(det_err, 90), det_err.max(),
        cam["K"][0, 0] * bp["radius"] / 3.6))
    gate("検出はサブピクセル: 中央値 < 0.3 px、全コマで見つかる", np.median(det_err) < 0.3 and all(t["found"].all() for t in tracks))
    poses = [c["pose"] for c in rig]
    Ks = [c["K"] for c in rig]
    ident = max(np.linalg.norm(BT.triangulate_dlt([truth_uv[0][k], truth_uv[1][k]], poses, Ks)["p"] - P_true[k]) for k in range(len(t_frames)))
    tri = BT.track_triangulate(tracks, poses, Ks, len(t_frames))
    tri_err = np.linalg.norm(tri["p"] - P_true[tri["frame"]], axis=1)
    print("  三角測量: 真値の投影から %.1e m、検出から 中央値 %.2f mm、90 %% 点 %.2f mm、最大 %.2f mm(再投影 rms 中央値 %.3f px)" % (
        ident, 1e3 * np.median(tri_err), 1e3 * np.percentile(tri_err, 90), 1e3 * tri_err.max(), np.median(tri["reproj_rms"])))
    gate("三角測量: 真値の投影で 1e-9 m、検出から中央値 < 3 mm", ident < 1e-9 and np.median(tri_err) < 3e-3)
    dt = 1.0 / FPS
    P_vac = B.flight_vacuum(p0, v0, t_frames)                       # 放物線(等加速度モデルが厳密な真値)
    kf_true = BT.kalman_ca(P_vac, dt, q=1e-2, r=1e-9)
    inn_true = np.abs(kf_true["innovation"][10:]).max()
    kf_drag = BT.kalman_ca(P_true, dt, q=1e-2, r=1e-9)
    inn_drag = np.abs(kf_drag["innovation"][10:int(contact["t"] * FPS) - 1]).max()
    Z = np.full((len(t_frames), 3), np.nan)
    Z[tri["frame"]] = tri["p"]
    kf = BT.kalman_ca(Z, dt, q=50.0, r=(2e-3) ** 2)
    kb = int(contact["t"] * FPS)
    v_err = np.linalg.norm(kf["x"][10:kb - 1, 1::3] - V_true[10:kb - 1], axis=1)
    print("  Kalman(等加速度): 放物線の真値を入れた新息 最大 %.1e m(抗力 + マグヌスの真値だと %.1e m = モデルの外)、検出からの速度の誤差 中央値 %.3f m/s"
          "(跳ねの前、|v| ≈ %.1f m/s)" % (inn_true, inn_drag, np.median(v_err), np.linalg.norm(V_true[kb // 2])))
    gate("Kalman は物理を知っている: 放物線の真値の新息 < 1e-6、検出からの速度 < 0.15 m/s", inn_true < 1e-6 and np.median(v_err) < 0.15)

    # ─────────────────────────────── 4. 跳ねの検出・予測・反発係数 ─────────────────────────────
    print("== 4. 跳ねを検出し、跳ねる前の 15 コマから跳ねを越えて予測し、反発係数を測る")
    bd = BT.bounce_detect(t_frames[tri["frame"]], tri["p"][:, 2], min_gap=2)
    b_err = np.abs(bd["t"][0] - contact["t"]) if len(bd["t"]) else np.inf
    print("  z の局所最小: t = %s、真値 %.4f s(差 %.1f ms)" % (np.round(bd["t"], 3).tolist(), contact["t"], 1e3 * b_err))
    gate("跳ねの検出: 接触時刻と 1 コマ以内", len(bd["t"]) >= 1 and b_err <= dt + 1e-9)
    n_fit = 15
    sel = tri["frame"] < n_fit
    t_sel, p_sel = t_frames[tri["frame"][sel]], tri["p"][sel]
    ident_fit = B.flight_fit(t_frames[:n_fit], P_true[:n_fit], w0, bp)
    fit_ident = max(np.linalg.norm(ident_fit["p0"] - P_true[0]), np.linalg.norm(ident_fit["v0"] - V_true[0]))
    landing = {}
    for label, w_used, fitter in (("真のスピン", w0, "ode"), ("スピン無視", np.zeros(3), "ode"), ("放物線 + 真のスピン", w0, "parabola")):
        f0 = B.flight_fit(t_sel, p_sel, w_used, bp) if fitter == "ode" else B.fit_parabola(t_sel - t_sel[0], p_sel)
        pr = B.flight_simulate(f0["p0"], f0["v0"], w_used, bp, ip, T_END - t_sel[0], 1e-4, table_z=H, table_xy=world["bounds"])
        if pr["contacts"]:
            c1 = pr["contacts"][0]
            landing[label] = (np.linalg.norm(c1["p"][:2] - contact["p"][:2]), c1["t"] + t_sel[0] - contact["t"], pr)
        else:
            landing[label] = (np.inf, np.inf, pr)
    print("  初期状態の当てはめ(運動方程式、6 パラメータの Gauss-Newton): 真値の軌跡なら %.1e で戻る。検出から(跳ねる前の %d コマ = %.2f s): "
          "真のスピンを知っていれば着地点 %.1f cm(時刻の差 %.1f ms)、スピンを無視すると %.1f cm、放物線で当てると(真のスピンでも)%.1f cm" % (
              fit_ident, n_fit, n_fit * dt, 100 * landing["真のスピン"][0], 1e3 * landing["真のスピン"][1], 100 * landing["スピン無視"][0],
              100 * landing["放物線 + 真のスピン"][0]))
    gate("跳ねを越える予測: 真値で 1e-9、真のスピンで着地点 < 2 cm、スピン無視は 2 倍以上外れる",
         fit_ident < 1e-9 and landing["真のスピン"][0] < 0.02 and landing["スピン無視"][0] > 2 * landing["真のスピン"][0])
    pre = (tri["frame"] >= kb - 12) & (tri["frame"] <= kb - 1)
    post = (tri["frame"] >= kb + 1) & (tri["frame"] <= kb + 12)
    fa = B.fit_parabola(t_frames[tri["frame"][pre]], tri["p"][pre])
    fb = B.fit_parabola(t_frames[tri["frame"][post]], tri["p"][post])
    e_par = -(fb["v0"][2] - fb["g"] * contact["t"]) / (fa["v0"][2] - fa["g"] * contact["t"])

    # ─────────────────────────────── 5. スピンを模様から ─────────────────────────────
    print("== 5. 跳ね際の近接カメラ(%d fps、ストロボ照明)で見えている模様(2 個以上)を検出し、前のコマと対応づけて Kabsch で角速度を当てる" % FPS_SPIN)
    t_sp = np.arange(0, 20) / FPS_SPIN + contact["t"] + 0.02
    cam_sp = None
    dirs = []
    spin_frames = []
    for k, t in enumerate(t_sp):
        pk = np.column_stack([np.interp([t], sim["t"], sim["p"][:, j]) for j in range(3)])[0]
        wk = np.column_stack([np.interp([t], sim["t"], sim["omega"][:, j]) for j in range(3)])[0]
        if k == 0:
            R_sp = R_true[int(round(t_sp[0] * FPS))]
            pm = np.column_stack([np.interp([t_sp[10]], sim["t"], sim["p"][:, j]) for j in range(3)])[0]   # 窓の真ん中の位置を狙う
            eye = pm + np.array([0.0, -0.6, 0.15])
            Ksp = DW.camera_intrinsics(20.0, 256, 256)
            cam_sp = {"pose": DW.camera_pose(eye, pm), "K": Ksp, "width": 256, "height": 256}
        else:
            R_sp = BW.rotation_from_omega(wk, 1.0 / FPS_SPIN) @ R_sp
        BW.ball_set_pose(world, ball, pk, R_sp)
        view = DW.world_camera(world, cam_sp["pose"], cam_sp["K"], 256, 256, ambient=0.7)     # 近接カメラはストロボ照明(陰影を弱く)
        spin_frames.append(view["color"])
        tr_ = BW.ball_truth(world, ball, cam_sp)
        d_ball = BT.ball_detect(view["color"], mode="chroma", color=BALL_COLOR, color_tol=0.2, radius_range=(10, 120))
        if not d_ball:
            dirs.append(None)
            continue
        cb = (d_ball[0]["col"], d_ball[0]["row"])
        rb = d_ball[0]["radius"] + 0.5                                  # 検出した等価半径(真値は使わない)
        gray = view["color"].mean(-1)
        rr, cc = np.mgrid[0:256, 0:256]
        inside = np.hypot(cc - cb[0], rr - cb[1]) < rb * 0.85           # 縁は模様が潰れるので内側だけ
        marks = BT.ball_detect(np.where(inside, gray, 1.0), mode="dark", thresh=0.2, radius_range=(1.5, 12))
        if len(marks) < 2:
            dirs.append(None)
            continue
        dirs.append(np.asarray([BT.marker_direction((m["col"], m["row"]), cb, rb) for m in marks]))
    w_est, w_ref = [], []
    for k in range(len(t_sp) - 1):
        if dirs[k] is None or dirs[k + 1] is None:
            continue
        # 模様の対応: 向きが最も近い組を貪欲に(1 コマの回転 ≈ 0.25 rad なので角度 0.5 rad 以内)
        d0, d1 = dirs[k], dirs[k + 1]
        cosang = d0 @ d1.T
        pairs = []
        used = set()
        for i, j in sorted(((i, j) for i in range(len(d0)) for j in range(len(d1))), key=lambda ij: -cosang[ij]):
            if i in {a for a, _ in pairs} or j in used or cosang[i, j] < np.cos(0.5):
                continue
            pairs.append((i, j))
            used.add(j)
        if len(pairs) < 2:
            continue
        s = BT.spin_from_markers(d0[[i for i, _ in pairs]], d1[[j for _, j in pairs]], 1.0 / FPS_SPIN)
        Rc = np.asarray(cam_sp["pose"])[:3, :3]
        w_est.append(Rc.T @ s["omega"])                       # カメラ系 → 世界系
        w_ref.append(np.column_stack([np.interp([t_sp[k]], sim["t"], sim["omega"][:, j]) for j in range(3)])[0])
    w_est = np.asarray(w_est)
    w_ref = np.asarray(w_ref)
    w_med = np.median(w_est, axis=0) if len(w_est) else np.full(3, np.nan)
    w_true_sp = np.median(w_ref, axis=0) if len(w_ref) else np.full(3, np.nan)
    sp_err = np.linalg.norm(w_med - w_true_sp) / np.linalg.norm(w_true_sp) if len(w_est) else np.inf
    print("  模様が 2 つ以上対応づいたコマ組 %d / %d、角速度の中央値 %s rad/s(真値 %s、|ω| %.0f rpm)、相対誤差 %.1f %%" % (
        len(w_est), len(t_sp) - 1, np.round(w_med, 1), np.round(w_true_sp, 1), np.linalg.norm(w_true_sp) * 60 / (2 * np.pi), 100 * sp_err))
    gate("スピンを模様から: 5 % 以内", sp_err < 0.05 and len(w_est) >= 5)
    # 反発係数: 前後の区間を運動方程式で当て(前 = 打球のスピン、後 = 近接カメラで測ったスピン)、接触時刻まで進める / 戻す
    w_post = w_med if np.all(np.isfinite(w_med)) else w0
    fa2 = B.flight_fit(t_frames[tri["frame"][pre]], tri["p"][pre], w0, bp)
    fb2 = B.flight_fit(t_frames[tri["frame"][post]], tri["p"][post], w_post, bp)
    vz_in = B.flight_state_at(fa2["p0"], fa2["v0"], w0, bp, contact["t"] - fa2["t0"])["v"][2]
    vz_out = B.flight_state_at(fb2["p0"], fb2["v0"], w_post, bp, contact["t"] - fb2["t0"])["v"][2]        # 負の時間 = 戻す
    e_est = -vz_out / vz_in
    e_true_v = -contact["v_out"][2] / contact["v_in"][2]
    print("  反発係数: 前後 12 コマずつを運動方程式で当てて接触時刻の v_z %.3f → %.3f、e = %.4f(真値 %.2f、世界の衝突では %.4f)。放物線の当てはめだと %.4f"
          "(抗力とマグヌスを g に吸って %.1f %% ずれる)" % (vz_in, vz_out, e_est, E_TRUE, e_true_v, e_par, 100 * abs(e_par - E_TRUE) / E_TRUE))
    gate("反発係数を測る: 運動方程式の当てはめで 2 % 以内", abs(e_est - E_TRUE) / E_TRUE < 0.02)

    # ─────────────────────────────── 6. ラリー ─────────────────────────────
    print("== 6. 自由に動くラケット 2 本で打ち合う: 送り合い / 攻め vs 送り / 知覚に雑音(ラリーの本数が指標)")
    rp = RK.racket_params()
    ipr = B.impact_params(E_TRUE, MU_TRUE)
    t_r = time.time()
    r_feed = RK.rally_simulate(bp, rp, tp, strategies=(RK.strategy_feeder, RK.strategy_feeder), retries=0, max_hits=12, seed=1, table_ip=ipr)
    r_att = RK.rally_simulate(bp, rp, tp, strategies=(RK.strategy_attacker, RK.strategy_feeder), retries=0, max_hits=12, seed=1, table_ip=ipr)
    r_att_rw = RK.rally_simulate(bp, rp, tp, strategies=(RK.strategy_attacker, RK.strategy_feeder), retries=6, max_hits=12, seed=1, table_ip=ipr)
    noise_hits = []
    for sig in (0.0, 0.05, 0.10):
        rng_n = np.random.default_rng(7)

        def perceive(t, p_, v_, w_, sig=sig, rng_n=rng_n):
            return p_ + rng_n.normal(0, sig, 3), v_, w_

        rn = RK.rally_simulate(bp, rp, tp, strategies=(RK.strategy_feeder, RK.strategy_feeder), retries=0, max_hits=8, seed=1,
                               table_ip=ipr, perceive=perceive)
        noise_hits.append((sig, rn["hits"], rn["end_reason"]))
    print("  送り合い %d 本(%s)、攻め vs 送り %d 本(%s)、巻き戻しあり %d 本(%s、巻き戻し %d 回)。知覚の位置雑音 → 本数: %s(%.1f s)" % (
        r_feed["hits"], r_feed["end_reason"], r_att["hits"], r_att["end_reason"], r_att_rw["hits"], r_att_rw["end_reason"], r_att_rw["rewinds"],
        ", ".join("%.0f mm → %d(%s)" % (1e3 * a, b, c) for a, b, c in noise_hits), time.time() - t_r))
    gate("ラリーの本数が指標: 送り合いは上限 12 本まで続き、攻める側が入ると短く終わり、雑音を増やしても本数は増えない(減らない区間は板の大きさの余裕 —— 正直に数字で)",
         r_feed["hits"] == 12 and r_att["hits"] < 12 and noise_hits[-1][1] <= noise_hits[0][1])

    # ─────────────────────────────── 7. 図 ─────────────────────────────
    if figs.enabled():
        print("== 7. 図")
        k_mid = kb // 2
        img = frames[0][k_mid].copy()
        tu = truth_uv[0][k_mid]
        img = _circle(img, tu, 6, "right")
        img = np.asarray(AN.text_box(img, "カメラ 1(1024 × 800、55°)t = %.2f s  緑の十字 = 球の真値の投影" % t_frames[k_mid], (10, 10), anchor="lt", font_size=13))
        figs.save("rig_view", img, "追跡カメラ 1 のコマ(t = %.2f s)。ITTF の台(2.74 × 1.525 m、高さ 0.76 m、ネット 15.25 cm)と 40 mm の球(像で半径 ≈ 4 px)。"
                                   "十字は世界の側の真値の投影。" % t_frames[k_mid])
        tu0 = np.asarray(truth_uv[0])
        figs.save_plot("tracks_2d", [("真値の投影(カメラ 1)", tu0[:, 0], -tu0[:, 1]), ("検出(色度、等速予測で追跡)", tracks[0]["col"], -tracks[0]["row"])],
                       kinds=["line", "scatter"], xlabel="col [px]", ylabel="−row [px]",
                       caption="カメラ 1 の像での球の軌跡: 真値の投影(線)と検出(点)。中心の誤差の中央値 %.2f px。" % np.median(det_err))
        pr_s = landing["真のスピン"][2]
        pr_n = landing["スピン無視"][2]
        figs.save_plot("trajectory_xz", [("真値(抗力 + マグヌス + 跳ね)", sim["p"][:, 0], sim["p"][:, 2] - H),
                                          ("三角測量(検出から)", tri["p"][:, 0], tri["p"][:, 2] - H),
                                          ("予測: 最初の %d コマ + 真のスピン" % n_fit, pr_s["p"][:, 0], pr_s["p"][:, 2] - H),
                                          ("予測: スピンを無視", pr_n["p"][:, 0], pr_n["p"][:, 2] - H)],
                       kinds=["line", "scatter", "line", "line"], xlabel="x [m](台の中心 = 0)", ylabel="台からの高さ [m]",
                       caption="x–z 面の軌跡。検出から三角測量した点(誤差の中央値 %.1f mm)は真値に乗る。跳ねる前の %d コマから当てた初期状態で"
                               "先を読むと、真のスピン(%d rpm のトップスピン)を知っていれば着地点は %.1f cm、スピンを無視すると %.1f cm 外れる。" % (
                                   1e3 * np.median(tri_err), n_fit, int(np.linalg.norm(w0) * 60 / (2 * np.pi)), 100 * landing["真のスピン"][0], 100 * landing["スピン無視"][0]))
        n_show = min(8, len(apex))
        figs.save_plot("drop_apexes", [("頂点(シミュレーション)", np.arange(1, n_show + 1), 100 * apex[:n_show]),
                                       ("閉形式 e^{2k} h₀", np.arange(0, n_show + 1), 100 * B.apex_sequence(h0, E_TRUE, n_show)),
                                       ("ITTF の規格 24 cm", np.array([0, n_show]), np.array([24.0, 24.0])),
                                       ("ITTF の規格 26 cm", np.array([0, n_show]), np.array([26.0, 26.0]))],
                       kinds=["scatter", "line", "line", "line"], xlabel="跳ねの回数 k", ylabel="頂点の高さ [cm]",
                       caption="30.5 cm から落とした球(e = %.2f)の頂点: 閉形式 e^{2k}h₀ と 1e-6 で一致し、最初の跳ね %.1f cm は ITTF の規格 24〜26 cm の中。" % (E_TRUE, 100 * apex[0]))
        panels = []
        for k in (0, 6, 12, 18):
            im = spin_frames[k]
            if dirs[k] is not None:
                pass
            panels.append(np.clip(im, 0, 1))
        figs.save_grid("spin_frames", panels, ["t₀", "t₀ + 6 ms", "t₀ + 12 ms", "t₀ + 18 ms"], ncols=4,
                       caption="跳ね際の近接カメラ(1000 fps、256 × 256、20°)の 4 コマ。見えている黒い模様(14 個のうち 4〜6 個)の向きを前のコマと対応づけ、Kabsch で回転を当てて角速度 %s rad/s(真値 %s)。" % (
                           np.round(w_med, 0), np.round(w_true_sp, 0)))
        gif = []
        for k in range(len(t_frames)):
            fr = frames[0][k]
            # 2 × 2 平均で 512 × 400 に
            small = fr.reshape(400, 2, 512, 2, 3).mean(axis=(1, 3))
            m = tracks[0]["frame"] == k
            if m.any():
                c_ = (tracks[0]["col"][m][0] / 2, tracks[0]["row"][m][0] / 2)
                small = _circle(small, c_, 3, "emphasis")
            if k < len(kf["x"]) and k >= 10:
                pk_ = BT.reproject(kf["x"][k, 0::3][None], rig[0]["pose"], rig[0]["K"])[0] / 2
                if np.all(np.isfinite(pk_)):
                    small = np.asarray(AN.crosshair(small, (float(pk_[0]), float(pk_[1])), color="right", width=1, gap=2, extent=6))
            lp = BT.reproject(landing["真のスピン"][2]["contacts"][0]["p"][None], rig[0]["pose"], rig[0]["K"])[0] / 2
            small = np.asarray(AN.crosshair(small, (float(lp[0]), float(lp[1])), color="wrong", width=1, gap=2, extent=8))
            txt = "t = %.2f s  橙 = 検出  緑 = Kalman  赤 = 予測した着地点(真のスピン)" % t_frames[k]
            if k >= kb:
                txt += "  跳ねた: e 推定 %.3f" % e_est
            small = np.asarray(AN.text_box(small, txt, (8, 8), anchor="lt", font_size=11))
            gif.append(small)
        figs.save_gif("rally_gif", gif, fps=10,
                      caption="追跡カメラ 1(2 × 2 平均で 512 × 400)、%d fps を 1/10 速で。橙の十字は検出、緑は Kalman の状態の投影、赤は跳ねる前の %d コマから予測した着地点。"
                              "球は %d rpm のトップスピンで、台で 1 度跳ねる(e = %.2f)。" % (FPS, n_fit, int(np.linalg.norm(w0) * 60 / (2 * np.pi)), E_TRUE))
        # ラリーの GIF: 送り合いの最初の 3 秒をカメラ 1(640 × 400、50 fps → 1/5 速)で。ラケットは板(15 × 16 cm)を世界に置いて描く
        Kr = DW.camera_intrinsics(55.0, 640, 400)
        cam_r = {"pose": rig[0]["pose"], "K": Kr}
        rk_mesh_V, rk_mesh_F = BW._box(-0.005, 0.005, -rp["width"] / 2, rp["width"] / 2, -rp["height"] / 2, rp["height"] / 2)
        rk_ids = [DW.world_add(world, rk_mesh_V + np.array([-1.55, 0, H + 0.25]), rk_mesh_F, 26, (0.75, 0.15, 0.15), name="racket0"),
                  DW.world_add(world, rk_mesh_V + np.array([1.55, 0, H + 0.25]), rk_mesh_F, 26, (0.15, 0.15, 0.75), name="racket1")]
        gif2 = []
        t_g = np.arange(0.0, min(3.0, r_feed["t"][-1]), 1.0 / 50)
        R_g = np.eye(3)
        for k, t in enumerate(t_g):
            i = int(np.searchsorted(r_feed["t"], t))
            i = min(i, len(r_feed["t"]) - 1)
            BW.ball_set_pose(world, ball, r_feed["p"][i], R_g)
            for side in (0, 1):
                v0_, v1_ = world["objects"][rk_ids[side]]["verts"]
                world["V"][v0_:v1_] = rk_mesh_V + r_feed["racket_pos"][i, side]
            view = DW.world_camera(world, cam_r["pose"], Kr, 640, 400)
            fr = view["color"]
            n_hit = int(np.sum(r_feed["hit_times"] <= t))
            fr = np.asarray(AN.text_box(fr, "t = %.2f s  ラリー %d 本目(送り合い、真値の知覚)  赤 = ラケット 0、青 = ラケット 1" % (t, n_hit), (8, 8), anchor="lt", font_size=12))
            gif2.append(fr)
        figs.save_gif("rally_two_rackets", gif2, fps=10,
                      caption="自由に動く 2 本のラケット(板 15 × 16 cm、速さ ≤ 6 m/s、加速度 ≤ 60 m/s²)の送り合い(前回に近い少しずらした位置へ返す)、"
                              "最初の 3 秒を 1/5 速で。相手コートに 1 度跳ねた球を面 x = ±1.55 m で迎え撃ち、狙った点へ運動方程式で返す。この設定では上限 %d 本まで続く。"
                              "攻める側(遠い隅を速く)が入ると %d 本で終わる(%s)。" % (r_feed["hits"], r_att["hits"], r_att["end_reason"]))
        figs.save_plot("rally_vs_noise", [("送り合いの本数(上限 8)", np.array([1e3 * a for a, _, _ in noise_hits]), np.array([b for _, b, _ in noise_hits], float))],
                       kinds=["line"], xlabel="知覚の位置雑音 [mm]", ylabel="ラリーの本数",
                       caption="知覚(球の位置)にガウス雑音を足したときのラリーの本数(送り合い、上限 8 本): %s。知覚・予測・制御の一式を 1 つの数で採点する指標。" % (
                           "、".join("%.0f mm → %d 本" % (1e3 * a, b) for a, b, _ in noise_hits)))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))

    print("== 結果: %d / %d 門, %.1f s" % (sum(OK), len(OK), time.time() - T0))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
