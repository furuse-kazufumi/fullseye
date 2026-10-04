# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""視触覚センサのマーカー場から「触覚双極子」で把持内の傾き・ねじりトルクを読む —— Gauss の法則が半空間で恒等式になることを門に(2026-10-04)。

物理シミュ × Fullseye 系列の第 2 弾の第 3 本(第 1 本 = poc_tacsim_elastic_membrane 法線荷重、第 2 本 = poc_tacsim_marker_shear 接線荷重)。
再実装した方法 = Fuchioka & Hamaya, ICRA 2024, arXiv 2404.15626(学習なし・光学模型なし: マーカー変位場の発散を「電荷」と見て双極子
p = (1/N) Σ r_i (∇·v)_i、原点は正負の電荷の重心の中点、トルクは双極子に直交、係数は力覚センサで較正)。著者のコードは無ライセンスなので
読まず、本文の式だけから書いた。外から来るものは 2 系統:
  * **閉形式**(Johnson, *Contact Mechanics*, CUP 1985): 平頭押し込み子の圧 p = P/(2πa√(a²−r²))(式 3.34)+ 傾きモーメントの反対称項
    3Mx/(2πa³√(a²−r²))(∫ x p dA = M、導出)、Boussinesq の点荷重解(§3.2)、Hertz 圧の表面変位(式 3.41b・3.42a)、楕円 Hertz 圧(式 4.24)、
    無滑りねじり(Reissner–Sagoci)q_θ = 3M_z r/(4πa³√(a²−r²))・β = 3M_z/(16Ga³)、Cattaneo–Mindlin の部分滑り(:mod:`tacslip`)。
  * **有限要素の節点変位**(有限厚ドーム状ゲル、Robo-Touch/Taxim リポジトリ同梱、MIT ライセンス、環境変数 FULLSEYE_TAXIM_DATA の下、無ければ [skip])。
自分で導いたのは 3 つ(全部門に): **Gauss の法則は半空間で厳密** ∇·ū = −(1−2ν)p/(2G)(だから面積重みの双極子は圧力の 1 次モーメント = M に比例し、
押し込み子の形に依らない)、Cerruti 点荷重の場の発散 −(1−ν)Qx/(2πGr³)(純せん断が窓全体に偽の傾き (1−ν)/(1−2ν)·Q·R を作る → 窓を固着円に限る)、
基線形式(|u| を電荷に)は零点後の対称な傾きで恒等的に 0(|u| は M の偶関数)。
被験者 = 既存 op: :func:`tacslip.marker_track`(重心と対応)、:func:`tacslip.cerruti_kernel` / :func:`cerruti_surface_displacement`(ねじりの独立実装)、
:func:`sceneflow.flow_divergence` / :func:`flow_curl`(格子の第 2 実装)、:func:`pivops.piv_vorticity`(符号規約 (dy, dx) で −curl)、
:func:`tacsim.hertz_sphere` ほか。新モジュール :mod:`tactorque` 17 op。

門(16、FEM の 2 本はデータがあるとき、門だけ 1.6 s): 平頭圧の格子積分(Σp h² = P・Σx p h² = M、縁 1/√ で 0.9 %)と離れの fail-closed、Boussinesq 核 vs
3.41b / 3.42a / 平頭 u_z、Gauss 恒等式(ν 0.48 と 0.3、0.2 %)、純法線で双極子 0(3 形式、1e-15)、D ∝ M(R² = 1.000000、係数は閉形式と 0.04 %、
原点不変)、基線形式は符号を知らない、3 形状(平頭・球・稜)で係数が同じ(密 0.001 %・格子 0.25 %)、ねじり(∫r q dA = M_z、β を畳み込みで、
剛体回転の当てはめ、curl = 2β、piv_vorticity = −curl)、重ね合わせの分解(傾き 2.4 %・ねじり 0.5 %・並進 0.04 px)、純せん断の漏れ(窓 c − 1.5 ピッチで
≤ 0.001 N·mm、全窓で 32 N·mm)、雑音 0.03 px → σ_M = 0.11 N·mm(∝ σ)、綴り壊し 11 本 + nan ≠ 0、散在最小二乗 = 中心差分(1e-15)、像から
(描画 → 追跡 → 分解、M1 誤差 0.7 %・追跡 0.005 px・961/961)、FEM の符号(有限厚は膨らむ: 発散 + の核と − の環、半空間と逆)、FEM の斜め荷重の
双極子はせん断漏れの符号。
図(FULLSEYE_FIGURE_DIR があるとき 6 枚): マーカー像 + 追跡ベクトル + 双極子矢印(等倍切り出し)と追跡場の発散、M を上げる GIF、分解の地図、
FEM の法線 vs 斜め、壊れる場所(雑音・窓半径・窓中心)、3 形状の係数。
正直に: 半空間の係数 −(1−2ν)/(2G) は実機(有限厚・ほぼ非圧縮)の大きさを与えない(ν 0.48 で 1 N·mm が 0.06 px)—— 実機は較正、という論文の立場と
同じ。Johnson の式番号のうち傾いた平頭・平頭の u_z・Reissner–Sagoci は本文で未確認(独立実装で数値検証)。Lubkin の部分滑りねじりは未実装。
Run: py -3.11 examples/poc_tactile_dipole_torque.py        (FULLSEYE_TAXIM_DATA=<FEM 節点ファイルの親> で FEM の 2 門も)
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import pivops  # noqa: E402
import sceneflow as SF  # noqa: E402
import tacsim as T  # noqa: E402
import tacslip as S  # noqa: E402
import tactorque as TQ  # noqa: E402

# 寸法: 平頭押し込み子 a = 3 mm、P = 2 N → 離れない限界 M = Pa/3 = 2 N·mm。視野 16 mm、門の格子 128 px(125 µm/px)、像の格子 256 px(62.5 µm/px)。
E_GEL, NU, R_BALL, P_LOAD, MU = 0.2e6, 0.48, 6.0e-3, 2.0, 0.5
A_PUNCH = 3.0e-3
N, FOV = 128, 16.0e-3
PITCH = FOV / N
G_GEL = E_GEL / (2.0 * (1.0 + NU))
COEF = -(1.0 - 2.0 * NU) / (2.0 * G_GEL)                     # 半空間の閉形式: D = COEF · M1
MK_PX = 4.0                                                   # マーカー格子 0.5 mm = 4 px(門の格子)
MK_AREA = (MK_PX * PITCH) ** 2
FIT_R = 1.5 * MK_PX * PITCH                                   # 発散の平面当ての近傍半径 = 1.5 ピッチ(3×3)
FULL = "--full" in sys.argv
_GATES: list[tuple[str, bool]] = []
_NUM: dict = {}


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def _lattice(n, pitch_px):
    mk = S.membrane_markers(n, pitch_px)
    mk = mk[(mk[:, 0] >= 0) & (mk[:, 0] < n) & (mk[:, 1] >= 0) & (mk[:, 1] < n)]
    return mk, (mk - (n - 1) / 2.0) * (FOV / n)


def sample_markers(fields, pts_px):
    """格子場 (n, n) をマーカー中心 [px] で双線形標本化して (N, 2) に。"""
    p = np.asarray(pts_px, np.float64)
    return np.column_stack([ndimage.map_coordinates(np.asarray(f, np.float64), [p[:, 1], p[:, 0]], order=1, mode="nearest") for f in fields])


def _dense_dipole(ux, uy, X, Y, pitch, window=None, origin="midpoint"):
    div = SF.flow_divergence(ux, uy) / pitch
    pts = np.column_stack([X.ravel(), Y.ravel()])
    u = np.column_stack([ux.ravel(), uy.ravel()])
    return TQ.tactile_dipole_moment(pts, u, "divergence", origin=origin, area=pitch ** 2, rho=div.ravel(), window=window)


# ======================================================================================================================
def numpy_part() -> dict:
    t0 = time.time()
    print("== 閉形式(Johnson 1985)と論文の式(arXiv 2404.15626)")
    X, Y, r, _ = T._grid(N, FOV)
    ES = T.combined_modulus(E_GEL, NU)
    hz = T.hertz_sphere(P_LOAD, R_BALL, ES)
    kb = TQ.boussinesq_kernel(N, PITCH, G_GEL, NU)
    kc = S.cerruti_kernel(N, PITCH, G_GEL, NU)
    mk_px, mk_m = _lattice(N, MK_PX)
    ctx = {"X": X, "Y": Y, "r": r, "hz": hz, "kb": kb, "kc": kc, "mk_px": mk_px, "mk_m": mk_m}

    # ── 1. 平頭押し込み子の圧力(閉形式の自己検算)
    M_TEST = 1.0e-3
    p0 = TQ.punch_pressure(X, Y, A_PUNCH, P_LOAD, (0.0, 0.0), pitch=PITCH)
    pM = TQ.punch_pressure(X, Y, A_PUNCH, P_LOAD, (M_TEST, 0.0), pitch=PITCH)
    m0 = TQ.pressure_first_moment(p0, X, Y, PITCH); mM = TQ.pressure_first_moment(pM, X, Y, PITCH)
    eP, eM = abs(m0["P"] / P_LOAD - 1.0), abs(mM["M1"][0] / M_TEST - 1.0)
    _NUM["punch_P_grid_err"] = eP; _NUM["punch_M1_grid_err"] = eM
    gate("門 1 平頭圧の格子積分 Σp h² = P、Σx p h² = M(縁 1/√、4×4 副標本)",
         eP < 0.015 and eM < 0.015 and abs(mM["M1"][1]) < 1e-12 * M_TEST and abs(mM["P"] - m0["P"]) < 1e-9,
         "P %.2f %%、M1 %.2f %%(閾値 1.5 %%、実測 0.57 / 0.86)、M1_y %.1e、離れの fail-closed %s"
         % (100 * eP, 100 * eM, mM["M1"][1], _raises(lambda: TQ.punch_pressure(X, Y, A_PUNCH, P_LOAD, (0.7 * P_LOAD * A_PUNCH, 0.0)))))
    ctx.update({"p0": p0, "pM": pM, "M_TEST": M_TEST, "M1_grid": mM["M1"][0]})

    # ── 2. Boussinesq 核 vs Johnson 3.41b / 3.42a / 平頭の u_z
    ph = T.hertz_pressure(r, hz["a"], hz["p0"])
    u = TQ.boussinesq_surface_displacement(ph, kb)
    rr = np.maximum(r, 1e-12)
    ur_num = (u["ux"] * X + u["uy"] * Y) / rr
    ur_cf = S.hertz_surface_ur(r, hz["a"], hz["p0"], G_GEL, NU)
    e_ur = float(np.sqrt(np.mean((ur_num - ur_cf) ** 2)) / np.abs(ur_cf).max())
    e_uz = float(np.sqrt(np.mean((u["uz"] - T.hertz_surface_uz(r, hz["a"], hz["delta"], R_BALL)) ** 2)) / hz["delta"])
    uzp = TQ.boussinesq_surface_displacement(p0, kb)["uz"]
    uz_cf = TQ.punch_surface_uz(r, A_PUNCH, P_LOAD, G_GEL, NU)
    e_uzp = float(np.sqrt(np.mean((uzp - uz_cf) ** 2)) / uz_cf.max())
    _NUM.update({"kernel_ur_err": e_ur, "kernel_uz_err": e_uz, "punch_uz_err": e_uzp})
    gate("門 2 Boussinesq 核: Hertz 圧 → ū_r(3.41b)・ū_z(3.42a)、平頭 P → ū_z(δ = P(1−ν)/4Ga、外は arcsin)",
         e_ur < 1e-3 and e_uz < 1e-3 and e_uzp < 0.01,
         "相対 RMS ū_r %.4f %%、ū_z %.4f %%、平頭 ū_z %.3f %%(閾値 0.1 / 0.1 / 1 %%)" % (100 * e_ur, 100 * e_uz, 100 * e_uzp))

    # ── 3. Gauss の法則 ∇·ū = −(1−2ν) p/(2G)(2 つの ν、2 つの圧)
    worst = 0.0
    for nu in (NU, 0.3):
        G_ = E_GEL / (2.0 * (1.0 + nu))
        kb_ = kb if nu == NU else TQ.boussinesq_kernel(N, PITCH, G_, nu)
        for nm, p in (("hertz", ph), ("punch+M", pM)):
            uu = TQ.boussinesq_surface_displacement(p, kb_)
            div = SF.flow_divergence(uu["ux"], uu["uy"]) / PITCH
            cf = TQ.surface_divergence_closed_form(p, G_, nu)
            a_ = hz["a"] if nm == "hertz" else A_PUNCH
            m = r < 0.8 * a_
            worst = max(worst, float(np.sqrt(np.mean((div[m] - cf[m]) ** 2)) / np.abs(cf[m]).max()))
    _NUM["gauss_worst"] = worst
    gate("門 3 Gauss の法則は半空間で厳密: ∇·ū vs −(1−2ν)p/2G(r < 0.8a、ν 0.48 と 0.3)",
         worst < 5e-3, "最悪の相対 RMS %.3f %%(閾値 0.5 %%、実測 Hertz 0.11 / 平頭 0.21)" % (100 * worst))

    # ── 4. 純法線 → 双極子 0(3 形式)
    ref = abs(COEF * M_TEST)
    pts_d = np.column_stack([X.ravel(), Y.ravel()])
    u_d = np.column_stack([u["ux"].ravel(), u["uy"].ravel()])
    div_h = SF.flow_divergence(u["ux"], u["uy"]) / PITCH
    z_div = np.abs(TQ.tactile_dipole_moment(pts_d, u_d, "divergence", origin="centre", area=PITCH ** 2, rho=div_h.ravel())["D"]).max() / ref
    z_nc = np.abs(TQ.tactile_dipole_moment(pts_d, u_d, "norm_cross", origin="centre", area=PITCH ** 2)["D"]).max() / ref
    z_rad = np.abs(TQ.tactile_dipole_moment(pts_d, u_d, "radial", origin="centre", area=PITCH ** 2)["D"]).max() / ref
    up = TQ.boussinesq_surface_displacement(p0, kb)
    z_punch = np.abs(_dense_dipole(up["ux"], up["uy"], X, Y, PITCH, origin="centre")["D"]).max() / ref
    z_all = max(z_div, z_nc, z_rad, z_punch)
    _NUM["normal_only_rel"] = z_all
    gate("門 4 純法線(Hertz、平頭 P)→ 双極子 = 0(3 形式)", z_all < 1e-9, "max |D|/|D(M = 1 N·mm)| = %.1e(閾値 1e-9)" % z_all)

    # ── 5. D ∝ M(格子マーカー 0.5 mm、零点 = 把持後)、原点の不変性、形式の比較
    Ms = np.linspace(0.0, 1.5e-3, 7)
    sweep = {"M": Ms, "div": [], "nc": [], "rad": [], "Dy": [], "fields": []}
    for M in Ms:
        pm = TQ.punch_pressure(X, Y, A_PUNCH, P_LOAD, (M, 0.0), pitch=PITCH)
        dp = TQ.tilt_shear_field(p0, pm, kb)
        um = sample_markers((dp["ux"], dp["uy"]), mk_px)
        dd = TQ.tactile_dipole_moment(mk_m, um, "divergence", area=MK_AREA, radius=FIT_R)
        sweep["div"].append(dd["D"][0]); sweep["Dy"].append(dd["D"][1])
        sweep["nc"].append(TQ.tactile_dipole_moment(mk_m, um, "norm_cross", origin="centre", area=MK_AREA)["D"][0])
        sweep["rad"].append(TQ.tactile_dipole_moment(mk_m, um, "radial", origin="centre", area=MK_AREA)["D"][0])
        sweep["fields"].append((dp["ux"], dp["uy"], um, dd))
    fit = TQ.dipole_to_torque_fit(sweep["div"], Ms)
    k_rel = fit["k"] / (COEF * ctx["M1_grid"] / M_TEST)
    dy_rel = float(np.abs(np.array(sweep["Dy"][1:]) / np.array(sweep["div"][1:])).max())
    dd_mid = sweep["fields"][-1][3]
    dd_cen = TQ.tactile_dipole_moment(mk_m, sweep["fields"][-1][2], "divergence", origin="centre", area=MK_AREA, radius=FIT_R)
    orig_rel = float(np.abs(dd_mid["D"] - dd_cen["D"]).max() / np.abs(dd_mid["D"]).max())
    net_q = float(np.nansum(dd_mid["rho"]) / np.nansum(np.abs(dd_mid["rho"])))
    _NUM.update({"sweep_R2": fit["R2"], "sweep_k_rel": k_rel, "sweep_Dy_rel": dy_rel, "origin_rel": orig_rel, "lattice_net_charge": net_q,
                 "rmse_M_Nmm": fit["rmse_M"] * 1e3})
    gate("門 5 傾きの双極子 ∝ M(0〜1.5 N·mm の 7 点、0.5 mm 格子): R² > 0.999、k = −(1−2ν)/2G と 0.5 %、D_y/D_x < 1e-3、原点不変",
         fit["R2"] > 0.999 and abs(k_rel - 1.0) < 5e-3 and dy_rel < 1e-3 and orig_rel < 1e-3,
         "R² = %.6f、k/閉形式 = %.5f(格子の M1 に対して)、D_y/D_x = %.1e、中点原点 vs 中心原点 %.1e(閾値 1e-3: 格子の正味電荷 Σρ/Σ|ρ| = %.1e)、残差 %.4f N·mm"
         % (fit["R2"], k_rel, dy_rel, orig_rel, net_q, fit["rmse_M"] * 1e3))
    nc_rel = float(np.abs(sweep["nc"][-1]) / abs(sweep["div"][-1]))
    rad_rel = float(np.abs(sweep["rad"][-1]) / abs(sweep["div"][-1]))
    _NUM.update({"form_norm_cross_rel": nc_rel, "form_radial_rel": rad_rel})
    gate("門 6 基線形式(式 10–11、|u| を電荷に)は符号を知らない: 零点後の対称な傾きで |u| は M の偶関数 → D = 0。放射形式も小さい",
         nc_rel < 1e-3 and rad_rel < 1e-2, "|D_norm|/|D_div| = %.1e(閾値 1e-3)、|D_radial|/|D_div| = %.1e(閾値 1e-2)" % (nc_rel, rad_rel))
    ctx["sweep"] = sweep

    # ── 7. 3 形状(平頭 / 球 = ずらした Hertz / 楕円 = 稜)の係数
    d_shift = M_TEST / P_LOAD
    shapes = {"flat punch": (p0, pM),
              "sphere": (TQ.hertz_pressure_shifted(X, Y, hz), TQ.hertz_pressure_shifted(X, Y, hz, (d_shift, 0.0))),
              "ridge": (TQ.ellipse_pressure_shifted(X, Y, 2e-3, 6e-3, P_LOAD), TQ.ellipse_pressure_shifted(X, Y, 2e-3, 6e-3, P_LOAD, (d_shift, 0.0)))}
    shape_rows = []
    for nm, (pa, pb) in shapes.items():
        dp = TQ.tilt_shear_field(pa, pb, kb)
        M1g = TQ.pressure_first_moment(pb - pa, X, Y, PITCH)["M1"][0]
        um = sample_markers((dp["ux"], dp["uy"]), mk_px)
        k_lat = TQ.tactile_dipole_moment(mk_m, um, "divergence", area=MK_AREA, radius=FIT_R)["D"][0] / COEF
        k_den = _dense_dipole(dp["ux"], dp["uy"], X, Y, PITCH)["D"][0] / COEF
        shape_rows.append({"shape": nm, "M1_grid": M1g, "k_lattice_vs_M1": k_lat / M1g, "k_dense_vs_M1": k_den / M1g, "k_lattice_vs_M": k_lat / M_TEST,
                           "dp": pb - pa})
    kl = np.array([s["k_lattice_vs_M1"] for s in shape_rows]); kd = np.array([s["k_dense_vs_M1"] for s in shape_rows])
    spread_l = float(np.ptp(kl) / kl.mean()); spread_d = float(np.ptp(kd) / kd.mean())
    _NUM.update({"shape_spread_lattice": spread_l, "shape_spread_dense": spread_d, "shape_k_vs_nominal": {s["shape"]: s["k_lattice_vs_M"] for s in shape_rows}})
    gate("門 7 形状不変(半空間の恒等式): 平頭 / 球 / 稜 で係数が同じ", spread_d < 2e-3 and spread_l < 5e-3,
         "密な格子のばらつき %.3f %%(閾値 0.2)、0.5 mm 格子 %.3f %%(閾値 0.5); 名目 M に対して %s"
         % (100 * spread_d, 100 * spread_l, "、".join("%s %.4f" % (s["shape"], s["k_lattice_vs_M"]) for s in shape_rows)))
    ctx["shapes"] = shape_rows

    # ── 8. ねじり: Reissner–Sagoci の β を Cerruti 畳み込みで検証、剛体回転の当てはめ、curl
    MZ = 0.5e-3
    tf = TQ.torsion_stick_field(X, Y, A_PUNCH, MZ, kc, G_GEL)
    tq = float((np.hypot(tf["qx"], tf["qy"]) * r).sum() * PITCH ** 2 / MZ)
    uth = (-tf["ux"] * Y + tf["uy"] * X) / rr
    m = (r < 0.9 * A_PUNCH) & (r > 0.1 * A_PUNCH)
    ratio = uth[m] / r[m]
    e_beta = float(ratio.mean() / tf["beta"] - 1.0); s_beta = float(ratio.std() / ratio.mean())
    um_t = sample_markers((tf["ux"], tf["uy"]), mk_px)
    rf = TQ.rigid_rotation_fit(mk_m, um_t, (0.0, 0.0, 0.9 * A_PUNCH))
    curl = SF.flow_curl(tf["ux"], tf["uy"]) / PITCH
    vort = pivops.piv_vorticity(np.stack([tf["uy"], tf["ux"]]), spacing=PITCH)      # 第 2 実装: flow = (dy, dx)、d(dx)/dy − d(dy)/dx = −curl
    m8 = r < 0.8 * A_PUNCH
    e_curl = float(curl[m8].mean() / (2.0 * tf["beta"]) - 1.0)
    e_vort = float(np.abs(vort[m8] + curl[m8]).max() / np.abs(curl[m8]).max())
    dec_t = TQ.torque_decompose(mk_m, um_t, MK_AREA, G_GEL, NU, a=A_PUNCH, window=(0.0, 0.0, 0.9 * A_PUNCH), radius=FIT_R)
    leak_t = float(np.abs(dec_t["M1"]).max())
    _NUM.update({"torsion_torque_quad": tq, "torsion_beta_err": e_beta, "torsion_beta_unif": s_beta, "torsion_omega_fit_err": rf["omega"] / tf["beta"] - 1,
                 "torsion_curl_err": e_curl, "torsion_Mz_rel": dec_t["Mz"] / MZ, "torsion_tilt_leak_Nmm": leak_t * 1e3, "torsion_omega_curl_rel": dec_t["omega_curl"] / tf["beta"]})
    gate("門 8 ねじり(無滑り): ∫r q dA = M_z、畳み込みの円内 u_θ/r が一様に β = 3M_z/16Ga³、剛体回転の当てはめ、curl = 2β、piv_vorticity = −curl",
         abs(tq - 1.0) < 0.015 and abs(e_beta) < 0.01 and s_beta < 3e-3 and abs(rf["omega"] / tf["beta"] - 1.0) < 0.01 and abs(e_curl) < 0.02
         and e_vort < 1e-9 and abs(dec_t["Mz"] / MZ - 1.0) < 0.01 and leak_t < 0.01e-3,
         "積分 %.4f、β %.2f %%、一様性 %.2f %%、ω_fit %.2f %%、curl %.2f %%、piv_vorticity = −curl %.1e、M_z/真 %.4f、傾きへの漏れ %.4f N·mm(平均 curl/2 は %.2f β: 縁のバイアス)"
         % (tq, 100 * e_beta, 100 * s_beta, 100 * (rf["omega"] / tf["beta"] - 1), 100 * e_curl, e_vort, dec_t["Mz"] / MZ, leak_t * 1e3, dec_t["omega_curl"] / tf["beta"]))
    ctx["torsion"] = {"tf": tf, "curl": curl, "um": um_t}

    # ── 9. 重ね合わせ(傾き + ねじり + 並進)の分解
    dpM = TQ.tilt_shear_field(p0, pM, kb)
    T_PX = 1.0
    ux_s = dpM["ux"] + tf["ux"] + T_PX * PITCH; uy_s = dpM["uy"] + tf["uy"]
    um_s = sample_markers((ux_s, uy_s), mk_px)
    win_out = (0.0, 0.0, A_PUNCH + FIT_R)
    win_in = (0.0, 0.0, 0.9 * A_PUNCH)
    dec_out = TQ.torque_decompose(mk_m, um_s, MK_AREA, G_GEL, NU, a=A_PUNCH, window=win_out, radius=FIT_R)
    dec_in = TQ.torque_decompose(mk_m, um_s, MK_AREA, G_GEL, NU, a=A_PUNCH, window=win_in, radius=FIT_R)
    eM_out = abs(dec_out["M1"][0] / ctx["M1_grid"] - 1.0)
    eMz_in = abs(dec_in["Mz"] / MZ - 1.0)
    e_t = float(np.abs(dec_in["translation"] / PITCH - np.array([T_PX, 0.0])).max())
    um_tilt = sample_markers((dpM["ux"], dpM["uy"]), mk_px)
    eM_tilt = abs(TQ.torque_decompose(mk_m, um_tilt, MK_AREA, G_GEL, NU, a=A_PUNCH, window=win_out, radius=FIT_R)["M1"][0] / ctx["M1_grid"] - 1.0)
    _NUM.update({"super_M1_err_out": eM_out, "super_Mz_err_in": eMz_in, "super_t_err_px": e_t, "tilt_fraction_window_09a": dec_in["M1"][0] / ctx["M1_grid"],
                 "tilt_only_err_out": eM_tilt})
    gate("門 9 重ね合わせ 傾き 1 N·mm + ねじり 0.5 N·mm + 並進 1 px → 発散双極子で傾き(窓 a + 1.5 ピッチ)、剛体回転でねじり(窓 0.9a)、平均で並進",
         eM_out < 0.04 and eM_tilt < 0.005 and eMz_in < 0.01 and e_t < 0.05,
         "M1 %.2f %%(閾値 4: ねじり → 傾きの漏れ、傾き単独なら %.2f %%)、M_z %.2f %%、並進 %.3f px; 窓 0.9a だけなら M1 は真値の %.3f 倍(固定比、較正で吸収)"
         % (100 * eM_out, 100 * eM_tilt, 100 * eMz_in, e_t, dec_in["M1"][0] / ctx["M1_grid"]))
    ctx["super"] = {"ux": ux_s, "uy": uy_s, "um": um_s, "dec_out": dec_out, "dec_in": dec_in, "MZ": MZ, "T_PX": T_PX}

    # ── 10. 純せん断(Cattaneo–Mindlin)の漏れ: 窓で切る
    shear_rows = []
    for qr in (0.05, 0.3, 0.6):
        mp = S.mindlin_partial_slip(qr * MU * P_LOAD, hz, MU, G_GEL, NU)
        fld = S.membrane_shear_field(hz, mp, X, Y, kc)
        um = sample_markers((fld["ux"], fld["uy"]), mk_px)
        row = {"qr": qr, "Q": qr * MU * P_LOAD, "c": mp["c"], "delta_x_px": mp["delta_x"] / PITCH, "um": um}
        for tag, Rw in (("stick-fit", mp["c"] - FIT_R), ("stick", mp["c"]), ("contact", hz["a"]), ("full", None)):
            win = None if Rw is None else (0.0, 0.0, Rw)
            dec = TQ.torque_decompose(mk_m, um, MK_AREA, G_GEL, NU, a=hz["a"], window=win, radius=FIT_R)
            row[tag] = {"M1_leak_Nmm": float(np.abs(dec["M1"]).max() * 1e3), "t_px": float(dec["translation"][0] / PITCH), "n": dec["n"]}
        shear_rows.append(row)
    leak_in = max(rw["stick-fit"]["M1_leak_Nmm"] for rw in shear_rows)
    leak_full = shear_rows[1]["full"]["M1_leak_Nmm"]
    leak_pred = (1.0 - NU) / (1.0 - 2.0 * NU) * shear_rows[1]["Q"] * (FOV / 2.0) * 1e3
    t_err = max(abs(rw["stick-fit"]["t_px"] / rw["delta_x_px"] - 1.0) for rw in shear_rows)
    _NUM.update({"shear_leak_stickfit_Nmm": leak_in, "shear_leak_full_Nmm_q03": leak_full, "shear_leak_pred_Nmm_q03": leak_pred, "shear_delta_x_err": t_err})
    gate("門 10 純せん断(Q/μP 0.05 / 0.3 / 0.6): 固着円 − 当てはめ半径の窓では傾きの双極子 ≈ 0、並進 = δ_x、全窓は (1−ν)/(1−2ν)·Q·R だけ漏れる",
         leak_in < 0.005 and t_err < 0.01 and abs(leak_full / leak_pred - 1.0) < 0.15,
         "漏れ max %.4f N·mm(閾値 0.005、実測 ≤ 0.0012); δ_x %.2f %%; 全窓の漏れ %.1f N·mm vs 導出 %.1f(Q = 0.3 N、ν 0.48 → 13·Q·R、正方窓 vs 円窓で 15 %% の門)"
         % (leak_in, 100 * t_err, leak_full, leak_pred))
    ctx["shear_rows"] = shear_rows

    # ── 11. 雑音 0.03 px → トルク分解能
    um1 = sweep["fields"][4][2]                                 # M = 1.0 N·mm
    trials = 200 if FULL else 60
    res = TQ.dipole_torque_resolution(mk_m, um1, 0.03, PITCH, COEF, MK_AREA, FIT_R, trials=trials, window=(0.0, 0.0, 1.5 * A_PUNCH))
    res_full = TQ.dipole_torque_resolution(mk_m, um1, 0.03, PITCH, COEF, MK_AREA, FIT_R, trials=trials, window=None)
    res_lo = TQ.dipole_torque_resolution(mk_m, um1, 0.01, PITCH, COEF, MK_AREA, FIT_R, trials=trials, window=(0.0, 0.0, 1.5 * A_PUNCH))
    sig = float(res["sigma_M"][0] * 1e3)
    _NUM.update({"noise_sigma_M_Nmm_003px_1p5a": sig, "noise_sigma_M_Nmm_003px_full": float(res_full["sigma_M"][0] * 1e3),
                 "noise_sigma_M_Nmm_001px_1p5a": float(res_lo["sigma_M"][0] * 1e3), "noise_snr_1Nmm": float(res["snr"][0]),
                 "noise_markers_in_window": int((np.hypot(mk_m[:, 0], mk_m[:, 1]) <= 1.5 * A_PUNCH).sum()), "max_u_px_1Nmm": float(np.abs(um1).max() / PITCH)})
    gate("門 11 重心の雑音 0.03 px → トルク分解能(半空間 ν 0.48、0.5 mm 格子、窓 1.5a)",
         sig < 0.2 and res["snr"][0] > 5 and abs(res_lo["sigma_M"][0] / res["sigma_M"][0] - 1.0 / 3.0) < 0.15,
         "σ_M = %.3f N·mm(閾値 0.2、実測 0.11)、1 N·mm の SNR %.1f、全窓 σ_M = %.2f N·mm、0.01 px → %.3f N·mm(∝ σ)、信号 max |u| = %.3f px"
         % (sig, res["snr"][0], res_full["sigma_M"][0] * 1e3, res_lo["sigma_M"][0] * 1e3, np.abs(um1).max() / PITCH))

    # ── 12. 綴り壊し・fail-closed
    bad = [
        _raises(lambda: TQ.tactile_dipole_moment(mk_m, um1, "divergance", area=MK_AREA, radius=FIT_R)),
        _raises(lambda: TQ.tactile_dipole_moment(mk_m, um1, "divergence", weight="mean ", area=MK_AREA, radius=FIT_R)),
        _raises(lambda: TQ.tactile_dipole_moment(mk_m, um1, "divergence", origin="middle", area=MK_AREA, radius=FIT_R)),
        _raises(lambda: TQ.tactile_dipole_moment(mk_m, um1, "divergence", weight="area", radius=FIT_R)),
        _raises(lambda: TQ.tactile_dipole_moment(mk_m[:2], um1[:2], "norm_cross", origin="centre", area=MK_AREA)),
        _raises(lambda: TQ.dipole_to_torque_fit([1.0], [1.0])),
        _raises(lambda: TQ.marker_divergence(mk_m, um1, 0.0)),
        _raises(lambda: TQ.torque_decompose(mk_m, um1, MK_AREA, G_GEL, NU)),
        _raises(lambda: TQ.punch_pressure(X, Y, A_PUNCH, P_LOAD, (P_LOAD * A_PUNCH, 0.0))),
        _raises(lambda: TQ.boussinesq_surface_displacement(p0[:64], kb)),
        _raises(lambda: TQ.torsion_stick_field(X, Y, A_PUNCH, MZ, kc, 0.0)),
    ]
    nan_ok = bool(np.isnan(TQ.marker_divergence(mk_m, um1, 0.3 * MK_PX * PITCH)["div"]).all())
    gate("門 12 綴り壊し・fail-closed: 11 本の不正入力が ValueError、当てはめ半径が小さすぎると nan(黙って 0 にしない)",
         all(bad) and nan_ok, "%d / %d raise、nan ≠ 0 %s" % (sum(bad), len(bad), nan_ok))

    # ── 13. 格子の第 2 実装: 散在最小二乗 vs sceneflow の中心差分
    ux_g = sweep["fields"][-1][0]; uy_g = sweep["fields"][-1][1]
    pts_g = np.column_stack([X.ravel(), Y.ravel()]); u_g = np.column_stack([ux_g.ravel(), uy_g.ravel()])
    dc = TQ.marker_divergence(pts_g, u_g, 1.01 * PITCH)                      # 5 点(十字)の平面当て = 中心差分そのもの
    div_sf = SF.flow_divergence(ux_g, uy_g) / PITCH
    dct = TQ.marker_divergence(pts_g, np.column_stack([tf["ux"].ravel(), tf["uy"].ravel()]), 1.01 * PITCH)
    curl_sf = SF.flow_curl(tf["ux"], tf["uy"]) / PITCH
    inner = np.ones((N, N), bool); inner[0, :] = inner[-1, :] = inner[:, 0] = inner[:, -1] = False
    e_div = float(np.abs(dc["div"].reshape(N, N)[inner] - div_sf[inner]).max() / np.abs(div_sf).max())
    e_curl2 = float(np.abs(dct["curl"].reshape(N, N)[inner] - curl_sf[inner]).max() / np.abs(curl_sf).max())
    gate("門 13 第 2 実装: 格子上の 5 点の平面当て = sceneflow.flow_divergence / flow_curl(内側の画素; 3×3 の 9 点は行平均の差分で縁で 11 % 違う)",
         e_div < 1e-9 and e_curl2 < 1e-9, "最大相対差 div %.1e、curl %.1e" % (e_div, e_curl2))

    # ── 14. 像から: 平頭押し込みの膜を描き、マーカーを追跡して双極子
    N2 = 256; P2 = FOV / N2
    X2, Y2, r2, _ = T._grid(N2, FOV)
    kb2 = TQ.boussinesq_kernel(N2, P2, G_GEL, NU)
    h = -TQ.punch_surface_uz(r2, A_PUNCH, P_LOAD, G_GEL, NU)
    gy, gx = np.gradient(h, P2)
    nrm = np.dstack([-gx, -gy, np.ones_like(h)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    bg = T.membrane_render_rgb(nrm, T.membrane_lights(55.0), ambient=0.03)
    pts2 = S.membrane_markers(N2, 8.0)
    M_IMG = 1.5e-3
    pa2 = TQ.punch_pressure(X2, Y2, A_PUNCH, P_LOAD, (0.0, 0.0), pitch=P2); pb2 = TQ.punch_pressure(X2, Y2, A_PUNCH, P_LOAD, (M_IMG, 0.0), pitch=P2)
    dp2 = TQ.tilt_shear_field(pa2, pb2, kb2)
    p_cur = S.displace_markers(pts2, dp2["ux"], dp2["uy"], P2)
    img_ref = S.membrane_render_markers(bg, pts2, 2.5, 0.85); img_cur = S.membrane_render_markers(bg, p_cur, 2.5, 0.85)
    m_ref = S.marker_image(img_ref, bg); m_cur = S.marker_image(img_cur, bg)
    c2 = (N2 - 1) / 2.0
    frame = TQ.grasp_torque_frame(m_ref, m_cur, 0.85, 8.0, 2.5, P2, G_GEL, NU, a=A_PUNCH, window=(c2, c2, (A_PUNCH + 1.5 * 8.0 * P2) / P2))
    M1g2 = TQ.pressure_first_moment(pb2 - pa2, X2, Y2, P2)["M1"][0]
    u_true = sample_markers((dp2["ux"], dp2["uy"]), frame["track"]["p0"])
    trk_rms = float(np.sqrt(((frame["track"]["u"] * P2 - u_true) ** 2).mean()) / P2)
    e_img = abs(frame["M1"][0] / M1g2 - 1.0)
    _NUM.update({"image_M1_err": e_img, "image_track_rms_px": trk_rms, "image_matched": frame["track"]["matched"],
                 "image_max_u_px": float(np.hypot(dp2["ux"], dp2["uy"]).max() / P2), "image_M1_y_Nmm": float(frame["M1"][1] * 1e3)})
    gate("門 14 像から(62.5 µm/px、8 px 格子、半径 2.5 px): 描画 → marker_track → torque_decompose、M = 1.5 N·mm",
         e_img < 0.10 and trk_rms < 0.03 and frame["track"]["matched"] >= 600,
         "M1 %.1f %%(閾値 10 %%)、追跡 RMS %.4f px、対応 %d、信号 max |u| %.3f px、M1_y %.4f N·mm"
         % (100 * e_img, trk_rms, frame["track"]["matched"], np.hypot(dp2["ux"], dp2["uy"]).max() / P2, frame["M1"][1] * 1e3))
    ctx["image"] = {"img_ref": img_ref, "img_cur": img_cur, "frame": frame, "M": M_IMG, "P2": P2, "N2": N2, "u_true": u_true, "M1g": M1g2}
    ctx["t_numpy"] = time.time() - t0
    return ctx


# ======================================================================================================================
def fem_part(ctx: dict) -> dict:
    print("== 有限要素の節点変位(第 2 真値、FULLSEYE_TAXIM_DATA)")
    root = os.environ.get("FULLSEYE_TAXIM_DATA", "").strip()
    ctx["fem"] = None
    if not root:
        skip("門 15/16 FEM", "FULLSEYE_TAXIM_DATA が未設定(配布物同梱の FEM 節点ファイルを取得し、その親ディレクトリを指す。手順は tacslip の docstring)")
        return ctx
    names = ("0705_dome_node_dz_0.3", "0705_dome_node_dxdz_0.3")
    try:
        fz = S.fem_nodes_load(os.path.join(root, "calibs", names[0]), names[0])
        fx = S.fem_nodes_load(os.path.join(root, "calibs", names[1]), names[1])
    except (FileNotFoundError, ValueError, OSError) as exc:
        skip("門 15/16 FEM", "節点ファイルが読めない: %s" % exc)
        return ctx
    SP = 0.155e-3                                                # 節点間隔の中央値(実測)
    out = {}
    for f in (fz, fx):
        Pn = np.column_stack([f["X"], f["Y"]]); U = np.column_stack([f["dx"], f["dy"]])
        dc = TQ.marker_divergence(Pn, U, 2.5 * SP)
        out[f["name"]] = {"P": Pn, "U": U, "dz": f["dz"], "dc": dc}
    c0 = out[names[0]]["P"][np.argmax(out[names[0]]["dz"])]
    prof = {}
    for nm in names:
        o = out[nm]; rr = np.hypot(o["P"][:, 0] - c0[0], o["P"][:, 1] - c0[1]); o["rr"] = rr
        core = o["dc"]["valid"] & (rr < 0.4e-3); ring = o["dc"]["valid"] & (rr >= 0.4e-3) & (rr < 1.2e-3)
        prof[nm] = {"div_core": float(np.nanmean(o["dc"]["div"][core])), "div_ring": float(np.nanmean(o["dc"]["div"][ring])),
                    "n_core": int(core.sum()), "n_ring": int(ring.sum())}
    pz = prof[names[0]]
    gate("門 15 FEM のドーム(有限厚): 押し込み子の下で発散は正(膨らみ)、周りに負の環 —— 半空間の (1−2ν) 結合と符号が逆",
         pz["div_core"] > 0.01 and pz["div_ring"] < 0.0 and prof[names[1]]["div_core"] > 0.01,
         "dz のみ: 核 %.3f(n %d)、環 %.4f(n %d); dx+dz: 核 %.3f" % (pz["div_core"], pz["n_core"], pz["div_ring"], pz["n_ring"], prof[names[1]]["div_core"]))
    area = SP ** 2; win = (c0[0], c0[1], 2.0e-3)
    Dz = TQ.tactile_dipole_moment(out[names[0]]["P"], out[names[0]]["U"], "divergence", origin=(c0[0], c0[1]), area=area, rho=out[names[0]]["dc"]["div"], window=win)
    Dx = TQ.tactile_dipole_moment(out[names[1]]["P"], out[names[1]]["U"], "divergence", origin=(c0[0], c0[1]), area=area, rho=out[names[1]]["dc"]["div"], window=win)
    tz = out[names[0]]["U"][Dz["keep"]].mean(0); tx = out[names[1]]["U"][Dx["keep"]].mean(0)
    m1z = TQ.tactile_dipole_moment(out[names[0]]["P"], out[names[0]]["U"], "divergence", origin=(c0[0], c0[1]), area=area, rho=out[names[0]]["dz"], window=win)["D"]
    m1x = TQ.tactile_dipole_moment(out[names[1]]["P"], out[names[1]]["U"], "divergence", origin=(c0[0], c0[1]), area=area, rho=out[names[1]]["dz"], window=win)["D"]
    dDx = Dx["D"][0] - Dz["D"][0]; dtx = tx[0] - tz[0]; dM1x = m1x[0] - m1z[0]
    ratio = abs(Dz["D"][0] / dDx)
    _NUM["fem"] = {"D_dz": Dz["D"].tolist(), "D_dxdz": Dx["D"].tolist(), "t_dz_um": (tz * 1e6).tolist(), "t_dxdz_um": (tx * 1e6).tolist(), "n": Dz["n"], "prof": prof}
    gate("門 16 FEM の斜め(dx+dz)− 法線(dz): 増える x 双極子の符号は −(加わった x 並進)= 導出した Cerruti のせん断漏れ; dz のみの x 双極子は ≈ 0",
         np.sign(dDx) == -np.sign(dtx) and ratio < 0.05 and dM1x > 0,
         "ΔD_x = %.2e m³、Δt_x = %+.1f µm(圧の重心は +x に寄り dz の 1 次モーメント +%.1e)、|D_x(dz)|/|ΔD_x| = %.3f(閾値 0.05); D_y は両方 ≈ %.1e(ドームの斜面で dz 押しも y に斜め: t_y %.0f µm)"
         % (dDx, dtx * 1e6, dM1x, ratio, Dz["D"][1], tz[1] * 1e6))
    ctx["fem"] = {"out": out, "c0": c0, "Dz": Dz, "Dx": Dx, "prof": prof, "names": names}
    return ctx


# ======================================================================================================================
def _crop_up(img, cy, cx, half, up):
    y0, x0 = int(round(cy)) - half, int(round(cx)) - half
    c = img[y0:y0 + 2 * half, x0:x0 + 2 * half]
    return np.kron(c, np.ones((up, up) + (1,) * (c.ndim - 2)))


def _draw_segments(img, p0s, p1s, color, width: int = 1):
    """多数の線分を一度に描く(numpy、アンチエイリアスなし)。"""
    out = np.asarray(img, np.float64).copy()
    H, W = out.shape[:2]
    p0s = np.asarray(p0s, np.float64); p1s = np.asarray(p1s, np.float64)
    if len(p0s) == 0:
        return out
    n = int(np.ceil(np.hypot(*(p1s - p0s).T).max())) * 2 + 2
    t = np.linspace(0.0, 1.0, n)
    xs = p0s[:, 0, None] + (p1s[:, 0] - p0s[:, 0])[:, None] * t
    ys = p0s[:, 1, None] + (p1s[:, 1] - p0s[:, 1])[:, None] * t
    xi = np.rint(xs).astype(int).ravel(); yi = np.rint(ys).astype(int).ravel()
    for dy in range(-(width // 2), width - width // 2):
        for dx in range(-(width // 2), width - width // 2):
            xx, yy = xi + dx, yi + dy
            ok = (xx >= 0) & (xx < W) & (yy >= 0) & (yy < H)
            out[yy[ok], xx[ok]] = color
    return out


def _circle(img, cxy, r_px, color, width=1):
    th = np.linspace(0, 2 * np.pi, 361)
    p = np.column_stack([cxy[0] + r_px * np.cos(th), cxy[1] + r_px * np.sin(th)])
    return _draw_segments(img, p[:-1], p[1:], color, width)


def _arrow(img, p0, p1, color, width=3):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    img = _draw_segments(img, [p0], [p1], color, width)
    d = p1 - p0; L = np.hypot(*d)
    if L < 1e-9:
        return img
    d = d / L; nrm = np.array([-d[1], d[0]]); h = max(6.0, 0.18 * L)
    a1 = p1 - h * d + 0.5 * h * nrm; a2 = p1 - h * d - 0.5 * h * nrm
    return _draw_segments(img, [p1, p1], [a1, a2], color, width)


def _splat(shape, pts, vals, r_px, vmax, bg=0.5):
    """散在点の符号つき値を円盤で塗った RGB(青 − 白 + 赤、背景 bg)。"""
    H, W = shape
    img = np.full((H, W, 3), bg)
    yy, xx = np.mgrid[0:H, 0:W]
    for (x, y), v in zip(pts, vals):
        if not np.isfinite(v):
            continue
        m = (xx - x) ** 2 + (yy - y) ** 2 <= r_px * r_px
        t = float(np.clip(v / vmax, -1, 1))
        col = np.array([1.0, 1.0 - abs(t), 1.0 - abs(t)]) if t >= 0 else np.array([1.0 - abs(t), 1.0 - abs(t), 1.0])
        img[m] = col
    return img


def figures(ctx: dict) -> None:
    print("== 図")
    X, Y = ctx["X"], ctx["Y"]; mk_m = ctx["mk_m"]; mk_px = ctx["mk_px"]
    # ── 1. マーカー像 + 追跡ベクトル + 双極子矢印(等倍切り出し)、追跡場の発散
    im = ctx["image"]; fr = im["frame"]; P2 = im["P2"]; N2 = im["N2"]; c2 = (N2 - 1) / 2.0
    half = int(round((A_PUNCH + 1.5e-3) / P2)); up = 2
    o = round(c2) - half
    cur = np.clip(_crop_up(im["img_cur"], c2, c2, half, up), 0, 1)
    p0 = fr["track"]["p0"]; u = fr["track"]["u"]
    inside = (np.abs(p0[:, 0] - c2) < half - 2) & (np.abs(p0[:, 1] - c2) < half - 2)
    AMP = 40.0
    vec = _draw_segments(cur, (p0[inside] - o) * up, (p0[inside] + AMP * u[inside] - o) * up, (0.1, 0.9, 0.9))
    cc = ((c2 - o) * up, (c2 - o) * up)
    vec = _circle(vec, cc, A_PUNCH / P2 * up, (1.0, 1.0, 0.2))
    og = fr["origin"] / P2                                       # grasp_torque_frame の座標は画素 × pitch(中心を引いていない)
    Dn = fr["D"] / np.linalg.norm(fr["D"]) * 0.8 * A_PUNCH / P2
    vec = _arrow(vec, (og - o) * up, (og + Dn - o) * up, (1.0, 0.15, 0.1), 4)
    div = fr["div"]; k = np.isfinite(div)
    dmap = _splat((2 * half * up, 2 * half * up), (p0[k] - o) * up, div[k], 2.5 * up, float(np.abs(div[k]).max()))
    dmap = _circle(dmap, cc, A_PUNCH / P2 * up, (0.2, 0.2, 0.2))
    dmap = _arrow(dmap, (og - o) * up, (og + Dn - o) * up, (1.0, 0.15, 0.1), 4)
    figs.save_grid("tactorque_marker_field_dipole", [vec, dmap], ncols=2,
                   captions=["markers + tracked u x%d, dipole (red), punch edge (yellow)" % int(AMP), "divergence of the tracked field per marker"],
                   caption="平頭押し込み子(a = 3 mm、P = 2 N)に傾きモーメント M = %.1f N·mm を掛けた後のマーカー像(62.5 µm/px、±%.1f mm を 2 倍)。"
                           "追跡ベクトル(水色、%d 倍、真の最大 |u| = %.3f px)は押し込み子の縁で向きが反転し、右の発散地図では縁に正負の「電荷」が分かれる。"
                           "赤 = 双極子(原点は正負の重心の中点)。この像から M1 = %.3f N·mm(格子の真値 %.3f、誤差 %.1f %%)、対応 %d 個、追跡 RMS %.4f px。"
                           % (im["M"] * 1e3, half * P2 * 1e3, int(AMP), _NUM["image_max_u_px"], fr["M1"][0] * 1e3, im["M1g"] * 1e3, 100 * _NUM["image_M1_err"],
                              fr["track"]["matched"], _NUM["image_track_rms_px"]))

    # ── 2. GIF: M を上げる
    sw = ctx["sweep"]; Ms = sw["M"]
    vmax = max(float(np.nanmax(np.abs(f[3]["rho"]))) for f in sw["fields"][1:])
    size_l = 420; sc = size_l / N
    frames = []
    line_M = np.linspace(0, Ms[-1], 50) * 1e3
    line_D = COEF * (ctx["M1_grid"] / ctx["M_TEST"]) * np.linspace(0, Ms[-1], 50) * 1e9
    for i, (ux, uy, um, dd) in enumerate(sw["fields"]):
        rho = dd["rho"]; k = np.isfinite(rho)
        left = _splat((size_l, size_l), mk_px[k] * sc, rho[k], 1.3 * sc, vmax, bg=0.97)
        left = _circle(left, ((N - 1) / 2 * sc, (N - 1) / 2 * sc), A_PUNCH / PITCH * sc, (0.25, 0.25, 0.25))
        left = _draw_segments(left, mk_px * sc, (mk_px + 60.0 * um / PITCH) * sc, (0.1, 0.1, 0.1))
        if np.linalg.norm(dd["D"]) > 0:
            L = 2.5e-3 * (Ms[i] / Ms[-1]) / PITCH * sc
            og = ((dd["origin"] / PITCH) + (N - 1) / 2) * sc
            left = _arrow(left, og, og + np.array([np.sign(dd["D"][0]) * L, 0.0]), (1.0, 0.15, 0.1), 4)
        right = figs.render_plot([("closed form -(1-2nu)/2G * M1", line_M, line_D), ("dipole from the 0.5 mm lattice", Ms[:i + 1] * 1e3, np.array(sw["div"][:i + 1]) * 1e9)],
                                 xlabel="tilt moment M [N mm]", ylabel="dipole D_x [1e-9 m^3]", title="M = %.2f N mm" % (Ms[i] * 1e3), size=(420, size_l),
                                 xlim=(0, 1.6), kinds=["line", "scatter"], styles=["dashed", None], colors=["reference", "emphasis"])
        frames.append(np.hstack([left, np.asarray(right, np.float64)]))
    figs.save_gif("tactorque_dipole_grows_with_M", frames, fps=1.5,
                  caption="傾きモーメントを 0 → 1.5 N·mm に 7 段で上げる。左 = マーカー 1 個ごとの発散(赤 +・青 −、押し込み子の縁に正負の対が立つ)と変位(60 倍)、"
                          "赤矢印 = 双極子(長さ ∝ M)。右 = 格子マーカーの双極子 D_x が閉形式の線 −(1−2ν)/2G·M1(破線)に乗る: R² = %.6f、傾きの比 %.4f。"
                          % (_NUM["sweep_R2"], _NUM["sweep_k_rel"]))

    # ── 3. 分解の地図
    su = ctx["super"]; dec = su["dec_out"]; deci = su["dec_in"]
    div_g = SF.flow_divergence(su["ux"], su["uy"]) / PITCH; curl_g = SF.flow_curl(su["ux"], su["uy"]) / PITCH
    figs.save_grid("tactorque_decomposition_maps", [su["ux"] / PITCH, div_g, curl_g], ncols=3, signed=True,
                   captions=["u_x [px] of tilt + torsion + shift", "divergence -> tilt", "curl -> torsion"],
                   caption="重ね合わせた場(傾き 1 N·mm + ねじり 0.5 N·mm + 並進 1 px)を 3 つに分ける: 発散の双極子が傾き(M1 = %.3f N·mm、真値 %.3f、窓 a + 当てはめ半径)、"
                           "剛体回転の最小二乗がねじり(M_z = %.3f N·mm、真値 %.3f、窓 0.9a)、平均が並進(%.3f px、真値 1)。発散・curl は定数の微分が 0 なので並進に影響されない。"
                           "ねじりは傾きへ %.4f N·mm 漏れる。" % (dec["M1"][0] * 1e3, ctx["M1_grid"] * 1e3, deci["Mz"] * 1e3, su["MZ"] * 1e3, deci["translation"][0] / PITCH,
                                                     _NUM["torsion_tilt_leak_Nmm"]))

    # ── 4. FEM
    fe = ctx.get("fem")
    if fe is not None:
        c0 = fe["c0"]; Wpx = 520; pm_ = 6e-3 / Wpx
        panels, caps = [], []
        for nm in fe["names"]:
            o_ = fe["out"][nm]; k = o_["dc"]["valid"] & (o_["rr"] < 3e-3)
            pts_px = (o_["P"][k] - c0) / pm_ + Wpx / 2
            img = _splat((Wpx, Wpx), pts_px, o_["dc"]["div"][k], 4.0, 0.03, bg=0.97)
            Dv = (fe["Dz"] if nm == fe["names"][0] else fe["Dx"])["D"]
            L = 2.0e-3 * Dv / max(np.linalg.norm(fe["Dx"]["D"]), 1e-300) / pm_
            img = _arrow(img, (Wpx / 2, Wpx / 2), (Wpx / 2 + L[0], Wpx / 2 + L[1]), (0.1, 0.1, 0.1), 5)
            panels.append(img); caps.append(nm.replace("0705_dome_node_", "FEM dome ") + "  div per node (+-0.03)")
        series = []
        for nm in fe["names"]:
            o_ = fe["out"][nm]; rr = o_["rr"]; edges = np.linspace(0, 3e-3, 16); mids, dv = [], []
            for a0, a1 in zip(edges[:-1], edges[1:]):
                mm = o_["dc"]["valid"] & (rr >= a0) & (rr < a1)
                if mm.sum() >= 3:
                    mids.append(0.5 * (a0 + a1) * 1e3); dv.append(float(np.nanmean(o_["dc"]["div"][mm])))
            series.append(("div, " + ("dz only" if nm == fe["names"][0] else "dx+dz"), np.array(mids), np.array(dv)))
        series.append(("zero", np.array([0.0, 3.0]), np.array([0.0, 0.0])))
        prof_img = figs.render_plot(series, xlabel="r from the indent centre [mm]", ylabel="div(dx, dy) per node", title="radial profile: + core, - ring",
                                    size=(Wpx, Wpx), kinds=["line", "line", "line"], styles=[None, None, "dashed"], colors=["emphasis", "right", "reference"])
        panels.append(np.asarray(prof_img, np.float64)); caps.append("radial profile")
        pz = fe["prof"][fe["names"][0]]
        figs.save_grid("tactorque_fem_oblique_vs_normal", panels, ncols=3, captions=caps,
                       caption="第 2 真値: 有限要素の節点変位(有限厚のドーム状ゲル、Robo-Touch/Taxim リポジトリ同梱、MIT、節点 15,230・間隔 0.155 mm)。法線押し込み(dz)と斜め(dx+dz)の"
                               "面内変位の発散を節点ごとに塗った(赤 +・青 −、±0.03)。有限厚ゲルは押し込み子の下で膨らむ: 発散は核で +%.3f、0.4〜1.2 mm の環で %.4f —— "
                               "半空間の (1−2ν) 結合(ν < 0.5 で内向き = 負)と符号が逆。斜め荷重は平均変位が x に %+.0f µm 動き、双極子は −x に増える(矢印): 導出した"
                               "Cerruti のせん断漏れの符号そのもので、傾きトルクの検証にはならない(|D_x(dz)|/|ΔD_x| = %.3f)。"
                               % (pz["div_core"], pz["div_ring"], _NUM["fem"]["t_dxdz_um"][0] - _NUM["fem"]["t_dz_um"][0], abs(fe["Dz"]["D"][0] / (fe["Dx"]["D"][0] - fe["Dz"]["D"][0]))))
    else:
        print("  (FEM の図は FULLSEYE_TAXIM_DATA があるときだけ)")

    # ── 5. 壊れる場所
    um1 = ctx["sweep"]["fields"][4][2]
    sigs = np.array([0.005, 0.01, 0.02, 0.03, 0.05, 0.1])
    sm = np.array([TQ.dipole_torque_resolution(mk_m, um1, s, PITCH, COEF, MK_AREA, FIT_R, trials=40, window=(0, 0, 1.5 * A_PUNCH))["sigma_M"][0] * 1e3 for s in sigs])
    smf = np.array([TQ.dipole_torque_resolution(mk_m, um1, s, PITCH, COEF, MK_AREA, FIT_R, trials=40, window=None)["sigma_M"][0] * 1e3 for s in sigs])
    pa = figs.render_plot([("window 1.5a (%d markers)" % _NUM["noise_markers_in_window"], np.log10(sigs), np.log10(sm)), ("full 16 mm window", np.log10(sigs), np.log10(smf)),
                           ("signal 1 N mm", np.log10(sigs[[0, -1]]), np.array([0.0, 0.0]))],
                          xlabel="log10 centroid noise sigma [px]", ylabel="log10 torque resolution sigma_M [N mm]", title="(a) noise: sigma_M proportional to sigma",
                          size=(520, 380), kinds=["scatter", "scatter", "line"], styles=[None, None, "dashed"], colors=["emphasis", "wrong", "reference"])
    rw = ctx["shear_rows"][1]; hz = ctx["hz"]
    um_q = rw["um"]
    Rs = np.linspace(1.0e-3, 7.5e-3, 14); leaks = []
    for Rw in Rs:
        try:
            leaks.append(abs(TQ.torque_decompose(mk_m, um_q, MK_AREA, G_GEL, NU, a=hz["a"], window=(0, 0, Rw), radius=FIT_R)["M1"][0]) * 1e3)
        except ValueError:
            leaks.append(np.nan)
    leaks = np.array(leaks); kk = np.isfinite(leaks) & (leaks > 0)
    pb = figs.render_plot([("false tilt from pure shear Q = %.2f N" % rw["Q"], Rs[kk] * 1e3, np.log10(leaks[kk])),
                           ("stick radius c = %.2f mm" % (rw["c"] * 1e3), np.array([rw["c"], rw["c"]]) * 1e3, np.array([-5.5, 2.0])),
                           ("contact a = %.2f mm" % (hz["a"] * 1e3), np.array([hz["a"], hz["a"]]) * 1e3, np.array([-5.5, 2.0]))],
                          xlabel="window radius [mm]", ylabel="log10 false tilt [N mm]", title="(b) shear leak vs window radius (6 decades)",
                          size=(520, 380), kinds=["scatter", "line", "line"], styles=[None, "dashed", "dashed"], colors=["emphasis", "right", "wrong"])
    offs = np.linspace(0, 2.0e-3, 9); errs = []
    for ox in offs:
        dd = TQ.torque_decompose(mk_m, um1, MK_AREA, G_GEL, NU, a=A_PUNCH, window=(ox, 0.0, A_PUNCH + FIT_R), radius=FIT_R)
        errs.append(100 * (dd["M1"][0] / ctx["M1_grid"] - 1.0))
    pc = figs.render_plot([("tilt error", offs * 1e3, np.array(errs)), ("zero", np.array([0.0, 2.0]), np.array([0.0, 0.0]))],
                          xlabel="window centre offset from the contact [mm]", ylabel="tilt error [%]", title="(c) window off-centre",
                          size=(520, 380), kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"])
    figs.save_grid("tactorque_where_it_breaks", [pa, pb, pc], ncols=3, captions=["noise", "shear leak vs window", "window centre"],
                   caption="壊れる場所。(a) 重心の雑音: σ_M ∝ σ、0.03 px で窓 1.5a なら %.3f N·mm、全窓なら %.2f N·mm(マーカーを増やしても雑音が増えるだけ)。"
                           "(b) 純せん断 Q = %.2f N(Cattaneo–Mindlin)は全窓で %.1f N·mm の偽の傾きに見える((1−ν)/(1−2ν)·Q·R、導出)が、固着円 − 当てはめ半径の窓では %.4f N·mm "
                           "—— 窓半径で 6 桁動く。(c) 窓の中心が接触から 2 mm ずれると傾きを %.1f %% 失う(双極子は原点に依らないが、窓で切ると依る)。"
                           % (_NUM["noise_sigma_M_Nmm_003px_1p5a"], _NUM["noise_sigma_M_Nmm_003px_full"], rw["Q"], rw["full"]["M1_leak_Nmm"], rw["stick-fit"]["M1_leak_Nmm"], errs[-1]))

    # ── 6. 形状
    sh = ctx["shapes"]
    panels = [s_["dp"] for s_ in sh]
    bar = figs.render_plot([("dense grid", np.arange(3), np.array([s_["k_dense_vs_M1"] for s_ in sh])), ("0.5 mm lattice", np.arange(3) + 0.15, np.array([s_["k_lattice_vs_M1"] for s_ in sh])),
                            ("1", np.array([-0.5, 2.5]), np.array([1.0, 1.0]))],
                           xlabel="0 flat punch / 1 sphere / 2 ridge", ylabel="dipole / (-(1-2nu)/2G * M1)", title="coefficient per shape", size=(N * 3, N * 3),
                           ylim=(0.99, 1.01), kinds=["scatter", "scatter", "line"], styles=[None, None, "dashed"], colors=["emphasis", "right", "reference"])
    panels = [np.kron(p_, np.ones((3, 3))) for p_ in panels] + [np.asarray(bar, np.float64)]
    figs.save_grid("tactorque_shape_coefficient", panels, ncols=4, signed=[True, True, True, False],
                   captions=["flat punch + moment: delta p", "sphere shifted by M/P", "ridge (ellipse) shifted", "coefficient"],
                   caption="圧力の 1 次モーメントが同じ 1 N·mm の 3 つの押し込み子: 平頭にモーメント、Hertz 球を M/P だけずらす、細長い楕円(稜)をずらす。"
                           "Δp の形は全く違うが、半空間では双極子/モーメントの係数が同じ(密な格子で %.3f %%、0.5 mm 格子で %.3f %%)—— Gauss の恒等式の帰結。"
                           "論文は実機(有限厚のゲル)で物体ごとに較正係数が違うと報告している。" % (100 * _NUM["shape_spread_dense"], 100 * _NUM["shape_spread_lattice"]))
    print("  figures:", figs.errors() or "ok")


def main() -> int:
    t_all = time.time()
    ctx = numpy_part()
    ctx = fem_part(ctx)
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
