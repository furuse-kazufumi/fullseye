# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""柔らかい手首のペグ挿入 —— Whitney の準静的幾何を門に、手首 RGB-D の計測で穴へ寄せ、MuJoCo の接触で確かめる(2026-10-04)。

物理シミュ × Fullseye 系列の第 1 弾(「自作の罠は限界: 真値・門・被験者の 1 つを外から」の物理側)。外から来るものは 2 つ:
  * **定理** = Whitney 1982(ASME J. Dyn. Sys. Meas. Control 104(1), DOI 10.1115/1.3149634。**原著は有料で未読**。式は著者本人の
    MIT OCW 2.875 Class 3 のスライド本文から: 二点接触の深さ l/d = c/θ、θ_m = √(2c)、くさび θ > c/μ、かじりの平行四辺形 λ = l/(2rμ))。
  * **接触の物理** = MuJoCo(接触点・法線力・mj_geomDistance)。学習は使わない —— 計測 → 補正 → 下げる → 力で減速、のルールだけ。

自分で作ったのは 3 つ: 3-D の円柱で厳密にした二点接触の深さ l tan θ = 2R − r(cos θ + sec θ)(導出、l sin θ ≈ 2c_r が 4 次まで)、
真の姿勢から接触点数を幾何だけで予測する第 2 実装、手首 RGB-D 1 枚から穴中心とペグ先端を 3-D で読む計測(反エイリアスの縁を板の
平面へ持ち上げて円を当て、ペグは depth の点群に既知半径の円柱を当て、先端は影の端を投影した縁の円で合わせる)。

門(numpy、常に走る): Whitney の量の手計算(c = 0.0385、θ_m = 15.9°、面取り許容 1.2 mm、c/μ = 7.35°)、l₂ sin θ = 2c_r(1.5〜6° で
0.3977〜0.3999 mm)、2-D の長方形近似は 6° で 0.52 mm ずれる(反例)、幾何の第 2 実装が l₂ ∓ 0.05 mm で 1 点 / 2 点、くさび・かじり・
面取りの閉形式、PnP の恒等式(1e-9)、既知半径の円当てはめ(全周で measure.fit_circle と 1e-9、25° の弧では中央値で 5 倍以上良い)、
合成 RGB-D(解析的レイキャスト)で穴中心 ≤ 0.1 px・相対ずれ ≤ 0.03 mm、MJCF の罠 2 つ(numslices=128、offsamples)。
門(mujoco があるとき): 深度バッファは MSAA でサンプル 0 の位置 (−0.125, +0.375) px、8 姿勢で穴中心 ≤ 0.2 px(自由な円)/ ≤ 0.06 px
(治具の図面の半径で当てる)・相対ずれ ≤ 0.03 / 0.015 mm・先端の横 ≤ 0.05 px(軸方向は ≤ 1.0 px —— 0.3 px は**未達**)、mj_geomDistance で測った l₂ が閉形式と 0.08 mm 以内(1.5〜6°)、接触状態が
l₂ ∓ 0.3 mm で一点 / 二点に切り替わる、ε = (2, 1) mm・θ = 2° の挿入が成功して二点接触の始まりで l sin θ = 0.40 ± 0.01 mm、
格子 ε₀ {0, 1, 2, 3} mm × θ₀ {0, 1.5, 3}°: 補正なしは 1 mm まで(面取りの許容 1.2 mm)・補正ありは 12 / 12。

図(FULLSEYE_FIGURE_DIR があるとき): 手首カメラの重ね図(真値 緑・推定 赤・縁の点 黄、右下に拡大)、挿入の GIF(補正あり)、
補正なしで面取りを滑る GIF、l₂ の理論線 3 本と実測点、かじりの図(2 つの深さ)、成功率の表。

正直に: 剛体 + ばねの手首で、把持のずれは手首ヒンジの静止角、実機の遅れ・たわみ・カメラの較正誤差は入れていない。先端の軸方向は
影の端 1 画素の被覆率だけから読むので 0.5〜0.8 px(0.3 px 未達)。接触点数の予測と接触計算の一致は生で 0.69(±1 で 0.96)—— 柔らかい
接触は 0 / 1 点、1 / 2 点の間でちらつく。くさびは本 PoC の θ ≤ 3°・μ = 0.3 では起きない領域で、起こす実験はしていない。原著未読。
踏んだ罠: MSAA の depth はサンプル 0 の位置(傾けた平面で実測、depth は offsamples=0 で別コンパイル)、円柱の既定 28 スライスで半径が
0.04 mm 内側(numslices=128)、2-D の長方形近似は θ = 6° で 0.5 mm 違う。
Run: py -3.11 examples/poc_pegsim_insertion.py   (mujoco が無ければ mujoco の門は [skip]、numpy の門だけで PASS)
"""
from __future__ import annotations

import math
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import camera  # noqa: E402
import examplefig as figs  # noqa: E402
import measure as FM  # noqa: E402
import pegsim as P  # noqa: E402
import render3d  # noqa: E402

_GATES = []
DEG = math.pi / 180.0
KP = P.peg_params()


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def _wrist_cam_xmat():
    s2 = 1 / math.sqrt(2)
    x = np.array([0.0, -1.0, 0.0])
    y = np.array([s2, 0.0, s2])
    return np.column_stack([x, y, np.cross(x, y)])


def numpy_part():
    print("== 1. numpy の門(Whitney の量・第 2 実装・当てはめ・合成 RGB-D・MJCF)")
    wc = P.whitney_clearance(KP)
    gate("Whitney の量: c = 0.0385、θ_m = √(2c) = 15.9°、面取りの許容 W + c_r = 1.2 mm、くさびの境目 c/μ = 7.35°",
         abs(wc["c"] - 0.2 / 5.2) < 1e-12 and abs(math.degrees(wc["theta_m"]) - 15.89) < 0.01
         and abs(wc["eps_chamfer_max"] - 1.2e-3) < 1e-12 and abs(math.degrees(wc["theta_wedge"]) - 7.353) < 0.01,
         "(θ_m の厳密値 arccos(d/D) = %.2f°)" % math.degrees(wc["theta_m_exact"]))
    tilts = (1.5, 2.0, 3.0, 4.0, 6.0)
    ls = [P.two_point_depth(KP, th * DEG) * math.sin(th * DEG) * 1e3 for th in tilts]
    dsm = [abs(P.two_point_depth(KP, th * DEG) - P.two_point_depth(KP, th * DEG, "small_angle")) * 1e3 for th in tilts]
    gate("二点接触の深さ(厳密 (1′)): l₂ sin θ = 2c_r = 0.400 mm を 1.5〜6° で 0.3975〜0.4000、小角の式との差 < 0.03 mm",
         min(ls) >= 0.3975 and max(ls) <= 0.4 + 1e-9 and max(dsm) < 0.03, "l₂ sin θ = %s mm" % [round(v, 4) for v in ls])
    l6, l6r = P.two_point_depth(KP, 6 * DEG), P.two_point_depth(KP, 6 * DEG, "rectangle")
    gate("反例: 2-D の長方形近似 D = d/cos θ + l tan θ は 6° で 0.45〜0.6 mm 浅い(縁の点の高さ r sin θ を無視するから)",
         0.45e-3 < l6 - l6r < 0.6e-3, "厳密 %.3f mm、長方形 %.3f mm" % (l6 * 1e3, l6r * 1e3))
    ok = True
    for th in tilts:
        l2 = P.two_point_depth(KP, th * DEG)
        xt = -KP["R"] + KP["r"] * math.cos(th * DEG)
        a = (math.sin(th * DEG), 0.0, math.cos(th * DEG))
        lo = P.contact_state_predict(KP, (xt, 0.0, -(KP["chamfer"] + l2 - 0.05e-3)), a, tol=1e-9)
        hi = P.contact_state_predict(KP, (xt, 0.0, -(KP["chamfer"] + l2 + 0.05e-3)), a, tol=1e-9)
        ok &= (lo["n"], lo["where"], hi["n"], hi["where"]) == (1, "tip", 2, "tip+mouth")
    gate("第 2 実装: 真の姿勢から接触点数を幾何だけで予測すると l₂ − 0.05 mm で 1 点(tip)、l₂ + 0.05 mm で 2 点(tip+mouth)、5 角度", ok)
    w3, w8 = P.wedging_check(KP, 3 * DEG), P.wedging_check(KP, 8 * DEG)
    k6 = P.peg_params(mu=0.6)
    agree = all(P.wedging_check(KP, th * DEG)["possible"] == (P.wedging_check(KP, th * DEG)["lambda"] < 1.0)
                for th in (2.0, 3.0, 4.0, 6.0, 8.0, 10.0))
    gate("くさび: μ = 0.3 では 3° で不可・8° で可(境目 7.35°)、μ = 0.6 では 3° 不可・4° 可(3.67°)、θ > c/μ ⇔ λ < 1 が 6 角度で一致",
         (not w3["possible"]) and w8["possible"] and (not P.wedging_check(k6, 3 * DEG)["possible"])
         and P.wedging_check(k6, 4 * DEG)["possible"] and agree,
         "μ = 0.6 の境目 %.2f°" % math.degrees(P.whitney_clearance(k6)["theta_wedge"]))
    j = P.jamming_diagram(KP, 5e-3)
    lam = 5e-3 / (KP["d"] * KP["mu"])
    V = j["vertices"]
    yA = V[0, 1] + (V[1, 1] - V[0, 1]) * (0 - V[0, 0]) / (V[1, 0] - V[0, 0])
    gate("かじりの図(p.34): λ = l/(2rμ) = %.3f at 5 mm、辺の縦軸切片 = ±λ、原点は内側、F_x/F_z = 1/μ の外と M/(rF_z) = λ の上は外側、"
         "深さ 2 倍で λ 2 倍" % lam,
         abs(j["lambda"] - lam) < 1e-12 and abs(yA - lam) < 1e-12 and P.jamming_diagram(KP, 5e-3, 0.0, 0.0)["inside"]
         and not P.jamming_diagram(KP, 5e-3, 1 / KP["mu"] + 0.01, 0.0)["inside"]
         and not P.jamming_diagram(KP, 5e-3, 0.0, lam + 0.01)["inside"]
         and abs(P.jamming_diagram(KP, 10e-3)["lambda"] - 2 * lam) < 1e-12)
    gate("面取りの許容: |ε₀| ≤ 1.2 mm は補正なしで救える、2 mm・3 mm は救えない(格子の結果の根拠)",
         P.chamfer_capture(KP, 1.2e-3)["captured"] and not P.chamfer_capture(KP, 1.2001e-3)["captured"]
         and not P.chamfer_capture(KP, 2e-3)["captured"] and not P.chamfer_capture(KP, 3e-3)["captured"])
    # PnP の恒等式
    ext = P.camera_world_to_cv(_wrist_cam_xmat(), np.array([-0.06, 0.0, 0.07]))
    R, t = ext["R"], ext["t"]
    K = render3d.intrinsics_from_fov(40.0, 640, 480)
    phis = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    X = np.vstack([np.column_stack([6.2e-3 * np.cos(phis), 6.2e-3 * np.sin(phis), np.zeros(8)]),
                   [0.002, 0.001, 0.010], [0.002, 0.001, 0.030], [0.03, 0.02, 0.0], [-0.02, 0.03, 0.0]])
    uv, _ = camera.project_points(X, K, R, t)
    R2, t2, rms = camera.solve_pnp(X, uv, K)
    rot_err = math.degrees(math.acos(min(1.0, (np.trace(R2 @ R.T) - 1) / 2)))
    gate("PnP の恒等式: MuJoCo のカメラ姿勢を OpenCV の (R, t) に写して投影した 12 点から camera.solve_pnp が姿勢を戻す(回転 < 1e-7°、"
         "並進 < 1e-9 m、再投影 rms < 1e-9 px)", rot_err < 1e-7 and np.linalg.norm(t2 - t) < 1e-9 and rms < 1e-9,
         "rot %.1e°, rms %.1e px" % (rot_err, rms))
    cy, cx, r = 120.3, 200.7, 37.0
    ph = np.linspace(0, 2 * np.pi, 90, endpoint=False)
    full = np.column_stack([cy + r * np.sin(ph), cx + r * np.cos(ph)])
    a_fit, b_fit = P.circle_fit_known_radius(full, r), FM.fit_circle(full)
    ph25 = np.linspace(0.2, 0.2 + 25 * DEG, 25)
    ek, ef = [], []
    for seed in range(10):
        rng = np.random.default_rng(seed)
        arc = np.column_stack([cy + r * np.sin(ph25), cx + r * np.cos(ph25)]) + rng.normal(0, 0.1, (25, 2))
        k_, f_ = P.circle_fit_known_radius(arc, r), FM.fit_circle(arc)
        ek.append(math.hypot(k_["cy"] - cy, k_["cx"] - cx))
        ef.append(math.hypot(f_["cy"] - cy, f_["cx"] - cx))
    gate("既知半径の円当てはめ: 全周では measure.fit_circle と中心が 1e-9 で一致、25° の弧 + 0.1 px の雑音(10 種)では中心の誤差の中央値が"
         " 5 倍以上小さい", abs(a_fit["cy"] - b_fit["cy"]) < 1e-9 and abs(a_fit["cx"] - b_fit["cx"]) < 1e-9
         and np.median(ef) > 5 * np.median(ek) and np.median(ek) < 0.3,
         "known %.3f px / free %.3f px(中央値)" % (np.median(ek), np.median(ef)))
    t0 = time.time()
    th = 2.0 * DEG
    tip = np.array([0.002, 0.001, 0.010])
    axis = np.array([math.sin(th), 0.0, math.cos(th)])
    syn = P.peg_synthetic_rgbd(KP, tip, axis)
    rgb, depth, K, R, t = syn["rgb"], syn["depth"], syn["K"], syn["R"], syn["t"]
    res = P.peg_offset_from_rgbd(rgb, depth, K, R.T)
    uv_true = np.vstack([syn["uv_tip"], syn["uv_hole"]])
    he = res["hole"]["uv"] - uv_true[1]
    te = res["tip"]["uv"] - uv_true[0]
    gate("合成 RGB-D(peg_synthetic_rgbd: 解析的レイキャスト 320×240、画素中心の深度 + 16 倍超標本の色、mujoco 不要): 穴中心 ≤ 0.1 px、相対ずれ ≤ 0.03 mm、"
         "先端の横 ≤ 0.1 px・軸方向 ≤ 1.0 px、半径 6.2 mm ± 0.01",
         np.abs(he).max() < 0.1 and abs(res["dx"] - 0.002) < 0.03e-3 and abs(res["dy"] - 0.001) < 0.03e-3
         and abs(te[0]) < 0.1 and abs(te[1]) < 1.0 and abs(res["hole"]["radius"] - 6.2e-3) < 0.01e-3,
         "穴 (%.3f, %.3f) px、ずれ (%.4f, %.4f) mm、先端 (%.3f, %.3f) px、%.1f s"
         % (he[0], he[1], (res["dx"] - 0.002) * 1e3, (res["dy"] - 0.001) * 1e3, te[0], te[1], time.time() - t0))
    ell = res["hole"]["ellipse"]
    gate("画像面の楕円の中心は円の中心の投影でない(透視の偏り > 0.3 px)—— 3-D で当てる理由",
         math.hypot(ell["cx"] - uv_true[1][0], ell["cy"] - uv_true[1][1]) > 0.3,
         "%.2f px" % math.hypot(ell["cx"] - uv_true[1][0], ell["cy"] - uv_true[1][1]))
    root = ET.fromstring(P.peg_scene_mjcf(KP))
    names = [g.get("name") or "" for g in root.findall(".//geom")]
    q = root.find("visual/quality")
    gate("MJCF(mujoco 不要)が罠 2 つを持つ: numslices=128(既定 28 では円柱の半径が 0.04 mm 内側)、offsamples は RGB 用 4 / depth 用 0、"
         "壁の箱 %d 個" % KP["n_seg"],
         sum(n.startswith("wall") for n in names) == KP["n_seg"] and q.get("numslices") == "128" and q.get("offsamples") == "4"
         and ET.fromstring(P.peg_scene_mjcf(KP, offsamples=0)).find("visual/quality").get("offsamples") == "0")
    return {"rgb": rgb, "res": res, "uv_true": uv_true}


def mujoco_part():
    print("== 2. mujoco の門(深度バッファ・計測・l₂・接触状態・挿入・格子)")
    out = {}
    t0 = time.time()
    a4, a0 = P.peg_depth_sample_offset(4), P.peg_depth_sample_offset(0)
    gate("深度バッファの位置: offsamples=4 は (du, dv) = (−0.125, +0.375) px(サンプル 0)、offsamples=0 は (0, 0)(画素中心)、残差 < 1 µm",
         (a4["du_px"], a4["dv_px"]) == (-0.125, 0.375) and (a0["du_px"], a0["dv_px"]) == (0.0, 0.0)
         and a4["resid_mm"] < 1e-3 and a0["resid_mm"] < 1e-3, "(%.1f s)" % (time.time() - t0))
    sc = P.peg_scene_build(KP)
    rng = np.random.default_rng(3)
    poses = [((3e-3, 3e-3, 8e-3), 2.0, (0, 1, 0)), ((-3e-3, 3e-3, 6e-3), -2.0, (1, 0, 0)),
             ((3e-3, -3e-3, 10e-3), 3.0, (1, 0, 0)), ((-3e-3, -3e-3, 4e-3), -3.0, (0, 1, 0))]
    for _ in range(4):
        poses.append((tuple(rng.uniform([-3e-3, -3e-3, 4e-3], [3e-3, 3e-3, 10e-3])), float(rng.uniform(-3, 3)),
                      (1, 0, 0) if rng.uniform() < 0.5 else (0, 1, 0)))
    d, ids = sc["data"], sc["ids"]
    hole_px, hole_px_k, tip_px, dxy, dxy_k, radii, overlay_first = [], [], [], [], [], [], None
    t0 = time.time()
    for tip, tilt_deg, ax in poses:
        P.peg_set_pose(sc, tip, tilt_deg * DEG, ax)
        img = P.peg_wrist_render(sc)
        res = P.peg_offset_from_rgbd(img["rgb"], img["depth"], img["K"], img["R_cam_to_world"], r_peg=KP["r"])
        res_k = P.peg_offset_from_rgbd(img["rgb"], img["depth"], img["K"], img["R_cam_to_world"], r_peg=KP["r"],
                                       hole_radius=KP["R"] + KP["chamfer"])
        truth = np.vstack([d.site_xpos[ids["tip"]], d.site_xpos[ids["hole_center"]]])
        uv, _ = camera.project_points(truth, img["K"], img["R"], img["t"])
        hole_px.append(res["hole"]["uv"] - uv[1])
        hole_px_k.append(res_k["hole"]["uv"] - uv[1])
        tip_px.append(res["tip"]["uv"] - uv[0])
        dxy.append([res["dx"] - truth[0][0], res["dy"] - truth[0][1]])
        dxy_k.append([res_k["dx"] - truth[0][0], res_k["dy"] - truth[0][1]])
        radii.append(res["hole"]["radius"])
        if overlay_first is None:
            overlay_first = P.peg_measure_overlay(img["rgb"], uv, np.vstack([res["tip"]["uv"], res["hole"]["uv"]]), res["hole"]["edge_uv"])
    hole_px, hole_px_k, tip_px = np.abs(hole_px), np.abs(hole_px_k), np.abs(tip_px)
    dxy, dxy_k = np.abs(dxy) * 1e3, np.abs(dxy_k) * 1e3
    assert len(hole_px) == 8
    gate("8 姿勢(構造 4 + 乱数 4、|ε| ≤ 3 mm、|θ| ≤ 3°)の計測、穴の円は自由な当てはめ: 穴中心 max ≤ 0.2 px、相対ずれ max ≤ 0.03 mm、"
         "先端の横 ≤ 0.05 px、半径 6.2 mm ± 0.025(numslices=128)。ペグが低く構えて縁の半分近くを隠す姿勢(ε = −3 mm、高さ 4 mm)で中心 0.18 px・"
         "半径 −0.020 mm(残り 7 姿勢は ± 0.005 mm)",
         hole_px.max() < 0.2 and dxy.max() < 0.03 and tip_px[:, 0].max() < 0.05 and max(abs(r - 6.2e-3) for r in radii) < 0.025e-3,
         "穴 max (%.3f, %.3f) px、ずれ max (%.4f, %.4f) mm、半径の誤差 %.1f〜%.1f µm、先端の横 max %.3f px、%.1f s"
         % (hole_px[:, 0].max(), hole_px[:, 1].max(), dxy[:, 0].max(), dxy[:, 1].max(), min(radii) * 1e6 - 6200, max(radii) * 1e6 - 6200,
            tip_px[:, 0].max(), time.time() - t0))
    gate("同じ 8 姿勢、穴の円を治具の図面の半径 R + W = 6.2 mm で当てる(既知半径): 穴中心 max ≤ 0.06 px、相対ずれ max ≤ 0.015 mm —— "
         "隠れた縁は半径を知っていれば補える(サーボはこちらを使う)",
         hole_px_k.max() < 0.06 and dxy_k.max() < 0.015,
         "穴 max (%.3f, %.3f) px、ずれ max (%.4f, %.4f) mm" % (hole_px_k[:, 0].max(), hole_px_k[:, 1].max(), dxy_k[:, 0].max(), dxy_k[:, 1].max()))
    gate("先端の軸方向(画像の縦): max ≤ 1.0 px —— 影の端 1 画素の被覆率だけから読む限界で、目標 0.3 px は**未達**(正直に)",
         tip_px[:, 1].max() <= 1.0, "max %.2f px、rms %.2f px" % (tip_px[:, 1].max(), np.sqrt((tip_px[:, 1] ** 2).mean())))
    out["overlay"] = overlay_first
    t0 = time.time()
    rows_l2 = []
    for th in (1.5, 2.0, 3.0, 4.0, 6.0):
        sim = P.peg_two_point_depth_sim(KP, th * DEG, scene=sc)
        rows_l2.append((th, sim, P.two_point_depth(KP, th * DEG), P.two_point_depth(KP, th * DEG, "small_angle"),
                        P.two_point_depth(KP, th * DEG, "rectangle")))
    diffs = [abs(s - e) * 1e3 for _, s, e, _, _ in rows_l2]
    lsin = [s * math.sin(th * DEG) * 1e3 for th, s, _, _, _ in rows_l2]
    try:
        P.peg_two_point_depth_sim(KP, 1.0 * DEG, scene=sc)
        no_two_point_at_1deg = False
    except ValueError:
        no_two_point_at_1deg = True
    gate("l₂ を接触計算(mj_geomDistance の二分法)で測ると閉形式 (1′) と 0.08 mm 以内(1.5〜6°)、l₂ sin θ ∈ [0.395, 0.400] mm、"
         "1° は穴の深さの中で二点接触しない(閉形式 22.9 mm > 20 mm)",
         max(diffs) < 0.08 and min(lsin) >= 0.395 and max(lsin) <= 0.400 and no_two_point_at_1deg,
         "差 %s mm、l₂ sin θ %s mm、%.1f s" % ([round(v, 3) for v in diffs], [round(v, 4) for v in lsin], time.time() - t0))
    out["rows_l2"] = rows_l2
    ok = True
    for th, sim, _, _, _ in rows_l2[1:3]:
        xt = -KP["R"] + KP["r"] * math.cos(th * DEG) - 0.004e-3
        P.peg_set_pose(sc, (xt, 0.0, -(KP["chamfer"] + sim - 0.3e-3)), th * DEG)
        s1 = P.peg_contact_state(sc)["state"]
        P.peg_set_pose(sc, (xt, 0.0, -(KP["chamfer"] + sim + 0.3e-3)), th * DEG)
        s2 = P.peg_contact_state(sc)["state"]
        ok &= (s1, s2) == ("one_point", "two_point")
    gate("接触状態(mj_contact を先端側 / 口側に割る)が l₂ − 0.3 mm で one_point、l₂ + 0.3 mm で two_point(2°・3°)", ok)
    P.peg_scene_close(sc)
    t0 = time.time()
    run = P.peg_insertion_run(KP, eps_mm=(2.0, 1.0), tilt_deg=2.0, correct=True, record=True, frame_every=0.15)
    servo = [s for s in run["servo"] if "error" not in s]
    tn = [math.hypot(s["true_dx_mm"], s["true_dy_mm"]) for s in servo]
    onset = [(dep, tl) for dep, tl, st in zip(run["rec"]["depth"], run["rec"]["tilt"], run["rec"]["state"]) if st == "two_point"]
    lsin_onset = ((onset[0][0] - KP["chamfer"]) * math.sin(onset[0][1] * DEG) * 1e3) if onset else float("nan")
    nc, npd = np.asarray(run["rec"]["n_con"]), np.asarray(run["rec"]["n_pred"])
    gate("挿入 1 走行 ε = (2, 1) mm・θ = 2°・補正あり: 成功(深さ ≥ 15 mm)、サーボ %d 回で真のずれが単調に減る(%.2f → %.3f mm)、"
         "最初の測定 (%.3f, %.3f) mm" % (len(servo), tn[0] if tn else float("nan"), tn[-1] if tn else float("nan"),
                                      servo[0]["dx_mm"] if servo else float("nan"), servo[0]["dy_mm"] if servo else float("nan")),
         run["success"] and len(servo) >= 4 and all(b < a for a, b in zip(tn, tn[1:])) and tn[-1] < 0.1
         and abs(servo[0]["dx_mm"] - 2.0) < 0.02 and abs(servo[0]["dy_mm"] - 1.0) < 0.02,
         "深さ %.2f mm、最大力 %.1f N、%.1f s" % (run["final_depth_mm"], run["max_force_N"], time.time() - t0))
    gate("二点接触の始まり(接触計算が two_point を初めて出した刻)で l sin θ = 0.40 ± 0.01 mm = 2c_r(Whitney の式を接触の物理が再現)",
         bool(onset) and abs(lsin_onset - 0.4) < 0.01, "l sin θ = %.4f mm at θ = %.2f°" % (lsin_onset, onset[0][1] if onset else float("nan")))
    gate("接触点数: 幾何の予測と接触計算が ±1 で ≥ 90 % 一致(生の一致は 0.7 前後 —— 柔らかい接触は 0/1 点・1/2 点の間でちらつく、正直に)",
         np.mean(np.abs(nc - npd) <= 1) >= 0.9, "生 %.2f、±1 %.2f、刻 %d" % (np.mean(nc == npd), np.mean(np.abs(nc - npd) <= 1), len(nc)))
    out["run"] = run
    t0 = time.time()
    slide = P.peg_insertion_run(KP, eps_mm=(0.866, 0.5), tilt_deg=2.0, correct=False, record=True, frame_every=0.15)
    gate("補正なし ε₀ = 1 mm(< 1.2 mm)・θ = 2°: 面取りが柔らかい手首を横へ押して成功、面取り接触か一点接触を経る",
         slide["success"] and bool({"chamfer", "one_point"} & set(slide["rec"]["state"])),
         "深さ %.2f mm、最大力 %.1f N、状態 %s、%.1f s" % (slide["final_depth_mm"], slide["max_force_N"], sorted(set(slide["rec"]["state"])), time.time() - t0))
    out["slide"] = slide
    t0 = time.time()
    grid = P.peg_insertion_grid(KP, eps_mm_list=(0.0, 1.0, 2.0, 3.0), tilt_deg_list=(0.0, 1.5, 3.0))
    sm = grid["summary"]
    off, on = sm["rate"][False], sm["rate"][True]
    gate("格子 ε₀ {0, 1, 2, 3} mm × θ₀ {0, 1.5, 3}° × {補正なし, あり} = 24 走行: 補正なしは 1 mm まで全部成功・2 mm 以上は全部失敗"
         "(面取りの許容 1.2 mm)、補正ありは 12 / 12",
         sm["max_eps_all_ok"][False] == 1.0 and np.all(off[2:] == 0.0) and sm["success_count"][True] == (12, 12),
         "補正なし %d / %d、補正あり %d / %d、%.1f s" % (*sm["success_count"][False], *sm["success_count"][True], time.time() - t0))
    out["grid"] = grid
    return out


def figures(np_out, mj_out):
    print("== 図")
    ths = np.linspace(1.0, 10.0, 91)
    ex = np.array([P.two_point_depth(KP, t * DEG) for t in ths]) * 1e3
    sa = np.array([P.two_point_depth(KP, t * DEG, "small_angle") for t in ths]) * 1e3
    re = np.array([P.two_point_depth(KP, t * DEG, "rectangle") for t in ths]) * 1e3
    series = [("exact (1'): l tan θ = 2R − r(cos θ + sec θ)", ths, ex), ("small angle: l = 2c_r / sin θ", ths, sa),
              ("2-D rectangle (wrong by 0.5 mm at 6°)", ths, re)]
    kinds, styles = ["line", "line", "line"], [None, "dashed", "dotted"]
    if mj_out and "rows_l2" in mj_out:
        series.append(("MuJoCo mj_geomDistance", [r[0] for r in mj_out["rows_l2"]], [r[1] * 1e3 for r in mj_out["rows_l2"]]))
        kinds.append("scatter")
        styles.append(None)
    figs.save_plot("pegsim_two_point_depth", series, xlabel="tilt θ [deg]", ylabel="two-point onset depth l₂ [mm]",
                   title="Two-point contact depth: r = 5.0, R = 5.2 mm", kinds=kinds, styles=styles, size=(640, 400), ylim=(0, 25),
                   caption="傾き θ で二点接触が始まる深さ l₂(最狭部から)。3-D の円柱で厳密にした (1′) と小角の式 l₂ sin θ = 2c_r は重なり、"
                           "2-D の長方形近似は θ = 6° で 0.5 mm 浅い。点は MuJoCo の mj_geomDistance の二分法で測った値(閉形式と 0.07 mm 以内)。"
                           "1° では 22.9 mm と穴の深さ 20 mm を超え、二点接触は起きない。")
    series, kinds, styles = [], [], []
    for ell_mm in (2.0, 8.0):
        V = P.jamming_diagram(KP, ell_mm * 1e-3)["vertices"]
        Vc = np.vstack([V, V[:1]])
        series.append(("l = %.0f mm, λ = %.2f" % (ell_mm, P.jamming_diagram(KP, ell_mm * 1e-3)["lambda"]), Vc[:, 0], Vc[:, 1]))
        kinds.append("line")
        styles.append(None if ell_mm > 2 else "dashed")
    series += [("inside (moves)", [0.0, 1.0], [0.0, 0.5]), ("outside (jams)", [1 / KP["mu"] + 0.5, 0.0], [0.0, 6.0])]
    kinds += ["scatter", "scatter"]
    styles += [None, None]
    figs.save_plot("pegsim_jamming_diagram", series, xlabel="F_x / F_z", ylabel="M / (r F_z)", title="Jamming diagram, μ = 0.3",
                   kinds=kinds, styles=styles, size=(560, 480), xlim=(-5, 5), ylim=(-8, 8),
                   caption="Whitney のかじりの図(OCW p.34): 二点接触中にペグが進むのは加える力の比がこの平行四辺形の内側にあるとき。"
                           "縦辺は F_x/F_z = ±1/μ、縦軸の切片は ±λ(λ = l/(2rμ))。深さ l が増えると縦に広がり、かじりにくくなる。")
    if mj_out:
        if mj_out.get("run") and mj_out["run"]["overlays"]:
            ov = mj_out["run"]["overlays"]
            sel = [ov[0], ov[1], ov[2], ov[-1]] if len(ov) >= 4 else ov
            panels = [o[::2, ::2] for o in sel]
            figs.save_grid("pegsim_wrist_overlay", panels, ncols=2,
                           captions=["servo iter %d" % k for k in ([0, 1, 2, len(ov) - 1] if len(ov) >= 4 else range(len(sel)))],
                           caption="手首 RGB-D(640×480、半分に縮小)から読んだ穴中心とペグ先端。緑の大きな十字 = 真値、赤の小さな十字 = 推定、"
                                   "黄の点 = 円当てはめに使った反エイリアスの縁。右下は穴まわりの 3 倍拡大。サーボ 1 回で横ずれは半分になる。")
        elif mj_out.get("overlay") is not None:
            figs.save("pegsim_wrist_overlay", mj_out["overlay"], caption="手首 RGB-D から読んだ穴中心とペグ先端(緑 = 真値、赤 = 推定)。")
        if mj_out.get("run") and mj_out["run"]["frames_side"]:
            fr = [f[::2, ::2] for f in mj_out["run"]["frames_side"]]
            figs.save_gif("pegsim_insert_corrected", fr, fps=6.0,
                          caption="補正ありの挿入(ε₀ = (2, 1) mm、θ₀ = 2°、側面カメラ、0.15 s ごと): サーボで穴の上に寄せ、下げ、一点 → 二点接触を経て 15 mm。")
        if mj_out.get("slide") and mj_out["slide"]["frames_side"]:
            fr = [f[::2, ::2] for f in mj_out["slide"]["frames_side"]]
            figs.save_gif("pegsim_chamfer_slide_no_correction", fr, fps=6.0,
                          caption="補正なし(ε₀ = 1 mm < 面取りの許容 1.2 mm、θ₀ = 2°): 面取りが柔らかい手首を横へ押し、ペグが滑り込む。2 mm では入口で止まる。")
        if mj_out.get("grid"):
            sm = mj_out["grid"]["summary"]
            header = ["ε₀ [mm]"] + ["off θ₀=%.1f°" % t for t in sm["tilt_deg"]] + ["on θ₀=%.1f°" % t for t in sm["tilt_deg"]]
            rows = []
            for i, e in enumerate(sm["eps_mm"]):
                rows.append(["%.1f" % e] + ["%s" % ("ok" if v >= 1 else "fail") for v in sm["rate"][False][i]]
                            + ["%s" % ("ok" if v >= 1 else "fail") for v in sm["rate"][True][i]])
            figs.save_table("pegsim_success_grid", header, rows, title="Insertion success: correction off / on",
                            caption="初期横ずれ ε₀ × 傾き θ₀ の成功 / 失敗(各 1 走行、ずれの向きは 30°)。補正なしは面取りの許容 1.2 mm までしか救えず、"
                                    "手首カメラで補正すると 3 mm・3° まで全部入る。")
    elif np_out:
        figs.save("pegsim_wrist_overlay", P.peg_measure_overlay(np_out["rgb"], np_out["uv_true"],
                                                     np.vstack([np_out["res"]["tip"]["uv"], np_out["res"]["hole"]["uv"]]),
                                                     np_out["res"]["hole"]["edge_uv"]),
                  caption="mujoco が無いときの代替図: 解析的レイキャストの合成 RGB-D(320×240)から読んだ穴中心とペグ先端(緑 = 真値、赤 = 推定)。")
    print("  figures:", figs.errors())


def main() -> int:
    t_all = time.time()
    np_out = numpy_part()
    mj_out = None
    try:
        import mujoco  # noqa: F401
        have_mj = True
    except ImportError:
        have_mj = False
    if have_mj:
        mj_out = mujoco_part()
    else:
        print("== 2. mujoco の門: [skip] mujoco が無い(pip install mujoco)。numpy の門だけで判定する")
    if figs.enabled():
        figures(np_out, mj_out)
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
