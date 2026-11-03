# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 光切断で段差と溶接ビードの高さを測り、その数字に「どこまで信じてよいか」を付ける

    py -3.11 examples/poc_light_section_step_weld_floor.py

光切断(シート光・レーザー三角測量)は、搬送中の部品の断面をインラインで測る 3-D 計測の
いちばん普及した方式です。この PoC は Fullseye の ``light_section`` 族だけで、次の 4 段を通します。

1. **光面の校正**: 既知の高さ(0 / 3 / 6 mm のゲージブロック)に当てた光条から、光面の式
   ``n · X = d`` を当てる(``light_plane_calibrate``)。真の装置との差を角度と距離で出す。
2. **走査で測る**: 段差 2.00 mm のブロックの上に、高さが走査の向きにゆっくり変わる溶接ビード
   (1.20 ± 0.10 mm)を置き、40 フレーム走査して点群と高さ地図を作る。中心の取り方 3 変種
   (重心 / ガウス / Steger)で段差とビードの高さを測り、真値と比べる。
3. **スペックルの床**(Fullseye だけの層): 実物のレーザー光条は粒々(スペックル)。同じ装置の
   光学の数字(波長 0.65 µm・観察開口 sin u = 0.01・三角測量角 30°・光条の半幅 150 µm)で、
   コヒーレント結像のシミュ(``light_section_speckle_floor``)と Dorsch ら(1994)の閉形式を並べる。
   開口を振ると床が 1/sin u で動き、独立なパターン(角度・波長の多重化)の数 N で 1/√N に下がる。
4. **不確かさの予算**: スペックル・読み出し雑音・校正の残差を GUM の表
   (``light_section_uncertainty_budget``)にし、既存の ``gum_expanded`` で拡張不確かさ U を出す。
   ビードの高さを「測定値 ± U」で書き、何が U を決めているか(支配的な成分)を言う。

真値: 断面は描画に入れた ``(x, h)``、装置は ``light_section_rig`` の幾何。光条の像は
``camera.project_points``(順方向)で描き、測る側は視線と光面の交点(逆方向)で、別のコード。

★正直に書いておくこと(合成であること):
  * 2 章の画像は**なめらかなガウスの光条 + 加法雑音**(スペックルなし)。スペックルは 3 章で、
    coherent の物体側の座標(倍率 1)の別のシミュで扱い、2 章の画像には入れていない。
    だから 2 章の誤差は「アルゴリズムと校正の誤差」で、実機の誤差は 3 章の床が下から抑える。
  * 光条の太さは一定、前縮み・デフォーカス・自己遮蔽(段差の影)・多重反射は入れていない。
    段差の縁の数列は光条が切れる(実機では影になる)ので、高さは縁から 1 mm 離して測る。
  * 3 章の閉形式の 2π は、Dorsch らを引く公開の論文(Ettl ら, arXiv:1401.1946, 2014)の形。
    原論文の本文は読めていない。シミュとの比(実測 0.9 前後)は表に出す。
  * √(w/L) の平均の規則(光条に沿って長さ L で平均すると床が下がる)は実測の規則。

走らせ方: ``py -3.11 examples/poc_light_section_step_weld_floor.py``
(図は ``FULLSEYE_FIGURE_DIR`` を指定したときだけ書く)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402  (台帳の公開経路 fs.ledger を使う)

LG = fs.ledger
CHECKS = []

THETA_DEG = 30.0
STANDOFF_MM = 200.0
FOCAL_PX = 2000.0
SHAPE = (480, 640)
X = np.linspace(-15.0, 15.0, 1201)
STEP_MM = 2.00
BEAD0_MM, BEAD_AMP_MM = 1.20, 0.10
N_FRAMES = 40
DY_MM = 0.25
NOISE = 0.01

# 3 章の光学(光条の物体側の数字)
WAVE_UM = 0.65
SIN_U = 0.01
LINE_W_UM = 150.0
SIM_PIX_UM = 10.0          # シミュの物体側の画素(重心の床は画素の大きさによらない —— coherent の門)


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))


def surface(x, k):
    """フレーム k の断面: 段差 2 mm(x > 2)+ x = −6 の溶接ビード(高さが走査でゆっくり変わる)。"""
    bead_h = BEAD0_MM + BEAD_AMP_MM * math.sin(2.0 * math.pi * k / N_FRAMES)
    return np.where(x > 2.0, STEP_MM, 0.0) + bead_h * np.exp(-((x + 6.0) / 1.5) ** 2), bead_h


def section1_calibrate(rig):
    print("=" * 78)
    print("1) 光面の校正(既知の高さ 0 / 3 / 6 mm のゲージブロック)")
    print("=" * 78)
    hs = [0.0, 3.0, 6.0]
    cl = [LG.laser_line_center_gauss(LG.light_section_render(rig, np.column_stack([X, np.full_like(X, h)]),
                                                             noise=NOISE, seed=10 + i, sampling="pixel"))
          for i, h in enumerate(hs)]
    cal = LG.light_plane_calibrate(cl, LG.light_section_targets(rig, hs), rig["K"], R=rig["R"], t=rig["t"])
    ang = math.degrees(math.acos(min(1.0, abs(float(cal["plane_normal"] @ rig["plane_normal"])))))
    dd = cal["plane_d"] - rig["plane_d"]
    print("  点 %d 個、残差 rms %.4f mm、法線の角度の誤差 %.5f°、d の誤差 %+.4f mm"
          % (cal["n_points"], cal["rms_mm"], ang, dd))
    check(ang < 0.01 and abs(dd) < 0.05, "校正した光面が真の光面と一致", "(%.5f°, %+.4f mm)" % (ang, dd))
    try:
        LG.light_plane_calibrate(cl[:1], LG.light_section_targets(rig, hs[:1]), rig["K"])
        check(False, "高さ 1 つでは面が決まらない(拒むはず)")
    except ValueError:
        check(True, "高さ 1 つだけの校正は拒まれる(点が 1 直線に並ぶ)")
    return cal


def _measure(Hmap, xcol, truth_bead):
    """高さ地図の 1 行(フレーム)から段差とビードの高さ(縁から 1 mm 離す)。"""
    base = (xcol > -2.5) & (xcol < 1.0)
    top = (xcol > 3.0) & (xcol < 13.0)
    bead = (xcol > -7.0) & (xcol < -5.0)
    out = []
    for k in range(Hmap.shape[0]):
        h = Hmap[k]
        b0 = np.nanmedian(h[base])
        out.append((np.nanmedian(h[top]) - b0, np.nanmax(h[bead]) - b0, truth_bead[k]))
    return np.array(out)


def section2_scan(rig, cal):
    print()
    print("=" * 78)
    print("2) 走査: 段差 %.2f mm + 溶接ビード %.2f ± %.2f mm、%d フレーム(雑音 %.0f %%)"
          % (STEP_MM, BEAD0_MM, BEAD_AMP_MM, N_FRAMES, 100 * NOISE))
    print("=" * 78)
    frames, truth = [], []
    for k in range(N_FRAMES):
        h, bh = surface(X, k)
        truth.append(bh)
        frames.append(LG.light_section_render(rig, np.column_stack([X, h]), noise=NOISE, seed=100 + k,
                                              sampling="pixel"))
    # 列 → 世界の x(高さ 0 の面で。高さ地図の格子は (フレーム, 列))
    c0 = LG.laser_line_center_gauss(LG.light_section_render(rig, np.column_stack([X, np.zeros_like(X)])))
    P0 = LG.light_section_profile(c0, rig)
    xcol = np.full(SHAPE[1], np.nan)
    xcol[np.rint(c0["col"][c0["valid"]]).astype(int)] = P0[:, 0]
    rows = []
    res = {}
    # ★列全体の重心(既定)は雑音の正の側を 480 行ぶん拾って列の真ん中へ引かれる: 段差の誤差 −0.67 mm、
    #   ビード +0.68 mm(実測)。窓を光条の幅に絞った重心(±8 行)で比べる。教訓として 1 行だけ残す。
    Hc = LG.light_section_height_map(frames, cal, method="centroid")
    qc = _measure(Hc, xcol, truth)
    print("  centroid(列全体、窓なし)段差の誤差 %+.3f mm ← 雑音を列全体で拾う。窓は必須"
          % (qc[:, 0] - STEP_MM).mean())
    check(abs((qc[:, 0] - STEP_MM).mean()) > 0.1, "窓なしの重心は雑音 1 % で 0.1 mm 以上ずれる(教訓の記録)")
    kws = {"centroid": {"half_window": 8}, "gauss": None, "steger": None}
    for m in ("centroid", "gauss", "steger"):
        t0 = time.time()
        Hm = LG.light_section_height_map(frames, cal, method=m, center_kw=kws[m])
        dt = time.time() - t0
        q = _measure(Hm, xcol, truth)
        e_step = q[:, 0] - STEP_MM
        e_bead = q[:, 1] - q[:, 2]
        res[m] = (e_step, e_bead)
        rows.append([m, "%+.4f" % e_step.mean(), "%.4f" % e_step.std(), "%+.4f" % e_bead.mean(),
                     "%.4f" % e_bead.std(), "%.0f" % (1000 * dt / N_FRAMES)])
        print("  %-8s 段差の誤差 %+.4f ± %.4f mm、ビードの誤差 %+.4f ± %.4f mm(%.0f ms / フレーム)"
              % (m, e_step.mean(), e_step.std(), e_bead.mean(), e_bead.std(), 1000 * dt / N_FRAMES))
    pts = LG.light_section_scan(frames, cal, step_mm=(0.0, DY_MM, 0.0), method="gauss")
    # Steger(Hessian による線の中心)を 1 枚に直に: 2-D の点(列も実数)と線の法線を返す
    st = LG.laser_line_center_steger(frames[0], sigma=1.5)
    print("  Steger(フレーム 0): 有効 %d 列、法線の行成分の中央値 %.3f(水平に近い光条で ≈ ±1)"
          % (st["n_valid"], float(np.nanmedian(np.abs(st["ny"])))))
    print("  点群(gauss): %d 点、Y の範囲 %.2f .. %.2f mm(= −k·%.2f mm)"
          % (pts.shape[0], pts[:, 1].min(), pts[:, 1].max(), DY_MM))
    for m, (es, eb) in res.items():
        check(abs(es.mean()) < 0.01 and abs(eb.mean()) < 0.02,
              "%s: 段差とビードの高さが真値と一致(偏り < 10 / 20 µm)" % m,
              "(%+.4f, %+.4f mm)" % (es.mean(), eb.mean()))
    check(abs(pts[:, 1].min() + DY_MM * (N_FRAMES - 1)) < 0.01, "走査の点群が部品の座標に戻る(校正した光面で 10 µm 以内)")
    if figs.enabled():
        Hg = LG.light_section_height_map(frames, cal, method="gauss")
        figs.save("height_map", np.repeat(np.nan_to_num(Hg[:, 150:490], nan=-0.5), 4, axis=0),
                  caption="高さ地図(フレーム × 列、gauss): 段差 2 mm と高さの変わるビード", colorbar=True)
        figs.save("line_frame0", frames[0], caption="フレーム 0 の光条(加法雑音 1 %)")
        figs.save_table("scan_errors", ["推定器", "段差の偏り [mm]", "段差のばらつき", "ビードの偏り [mm]",
                                        "ビードのばらつき", "ms/フレーム"], rows,
                        title="2 章: 3 変種の中心で測った高さの誤差(真値との差、40 フレーム)")
    return res


def section3_speckle():
    print()
    print("=" * 78)
    print("3) スペックルの床(λ %.2f µm・sin u %.3f・θ %.0f°・光条の半幅 %.0f µm)"
          % (WAVE_UM, SIN_U, THETA_DEG, LINE_W_UM))
    print("=" * 78)
    st = math.sin(math.radians(THETA_DEG))
    base = dict(wavelength_um=WAVE_UM, sin_theta=st, line_width_um=LINE_W_UM, pixel_um=SIM_PIX_UM)
    r = LG.light_section_speckle_floor(sin_u_obs=SIN_U, n_trials=10, **base)
    print("  重心: シミュ %.2f µm(95 %% %.2f–%.2f)、閉形式 %.2f µm、比 %.3f、粒径 %.0f µm"
          % (r["sim_delta_z_um"], *r["sim_ci95_um"], r["closed_form_delta_z_um"],
             r["ratio_sim_to_closed_form"], r["speckle_fwhm_um"]))
    check(0.8 < r["ratio_sim_to_closed_form"] < 1.15, "シミュの床が Dorsch の閉形式と一致(±15 %)",
          "(比 %.3f)" % r["ratio_sim_to_closed_form"])
    est = {}
    for m, kw in (("gauss5", {"half_window": 2}), ("steger", None)):
        e = LG.light_section_speckle_floor(sin_u_obs=SIN_U, n_trials=6, method="gauss" if m == "gauss5" else m,
                                           center_kw=kw, **base)
        est[m] = e["sim_delta_z_um"]
        print("  %-6s: シミュ %.2f µm(床の %.2f 倍)" % (m, e["sim_delta_z_um"], e["ratio_sim_to_closed_form"]))
    check(est["gauss5"] > 2.0 * r["sim_delta_z_um"], "山の 5 点だけのガウス当てはめは粒を追って床の 2 倍以上")
    sw_u = LG.light_section_floor_sweep("sin_u_obs", [0.005, 0.01, 0.02], n_trials=6, **base)
    print("  開口の掃引: sin u = %s → シミュ %s µm、傾き %.3f(閉形式 %.3f)"
          % (sw_u["values"], np.round(sw_u["sim_delta_z_um"], 2), sw_u["slope_sim"], sw_u["slope_closed_form"]))
    check(abs(sw_u["slope_sim"] + 1.0) < 0.15, "床は 1/sin u で下がる(傾き −1 ± 0.15)", "(%.3f)" % sw_u["slope_sim"])
    sw_n = LG.light_section_floor_sweep("n_patterns", [1, 4, 16], n_trials=6, sin_u_obs=SIN_U, **base)
    print("  多重化の掃引: N = %s → シミュ %s µm、傾き %.3f(閉形式 −0.5)"
          % (sw_n["values"].astype(int), np.round(sw_n["sim_delta_z_um"], 2), sw_n["slope_sim"]))
    check(abs(sw_n["slope_sim"] + 0.5) < 0.1, "独立なパターン N 枚で 1/√N(傾き −0.5 ± 0.1)", "(%.3f)" % sw_n["slope_sim"])
    if figs.enabled():
        img = LG.laser_line_coherent(shape=(64, 256), wavelength_um=WAVE_UM, sin_u_obs=0.04, pixel_um=2.5,
                                     line_width_um=40.0, pixel_oversample=2, seed=3)
        figs.save("speckled_line", img, caption="スペックルの光条(拡大、sin u = 0.04): 重心は粒で揺れる")
        figs.save_plot("floor_vs_aperture",
                       [("simulation", np.log10(sw_u["values"]), np.log10(sw_u["sim_delta_z_um"])),
                        ("closed form", np.log10(sw_u["values"]), np.log10(sw_u["closed_form_delta_z_um"]))],
                       xlabel="log10 sin u", ylabel="log10 δz [µm]", title="スペックルの床は 1/sin u")
    return r


def section4_budget(cal, res, sp):
    print()
    print("=" * 78)
    print("4) 不確かさの予算(GUM)と測定値 ± U")
    print("=" * 78)
    st = math.sin(math.radians(THETA_DEG))
    b = LG.light_section_uncertainty_budget(WAVE_UM, SIN_U, st, line_width_um=LINE_W_UM, pixel_um=SIM_PIX_UM,
                                            noise_rel=NOISE, window_rows=160,
                                            calib_rms_um=1000.0 * cal["rms_mm"], calib_dof=cal["n_points"] - 3)
    for s_, u, c, dz in zip(b["source"], b["u"], b["sensitivity"], b["delta_z_um"]):
        print("  %-12s u = %7.3f µm × 感度 %.3f → %7.3f µm" % (s_, u, c, dz))
    ex = LG.gum_expanded(b)
    U = float(ex["expanded"][0])
    k = float(ex["k"][0]) if "k" in ex else U / b["combined_u_z_um"]
    print("  合成 u_c = %.2f µm、拡張 U = %.2f µm(k = %.2f)、支配的な成分 = %s"
          % (b["combined_u_z_um"], U, k, b["dominant"]))
    check(b["dominant"] == "speckle", "この装置の不確かさを決めているのはスペックル(画素の雑音ではない)")
    eb = res["gauss"][1]
    print("  ビードの高さ(フレーム 10、gauss): %.4f mm ± %.3f mm(U、k ≈ 2)。2 章の合成画像の誤差 %.4f mm は"
          % (BEAD0_MM + BEAD_AMP_MM + eb[10], U / 1000.0, abs(eb[10])))
    print("  スペックルを入れていない画像の値で、実機ではこの U が下限になる。")
    check(sp["closed_form_delta_z_um"] > 1000.0 * float(np.abs(eb).mean()),
          "スペックルの床(%.1f µm)は 2 章の合成画像の誤差(%.1f µm)より大きい = 実機を決めるのは床"
          % (sp["closed_form_delta_z_um"], 1000.0 * float(np.abs(eb).mean())))


def main() -> int:
    t0 = time.time()
    rig = LG.light_section_rig(THETA_DEG, STANDOFF_MM, FOCAL_PX, SHAPE)
    cal = section1_calibrate(rig)
    res = section2_scan(rig, cal)
    sp = section3_speckle()
    section4_budget(cal, res, sp)
    print()
    bad = [c for c in CHECKS if not c[0]]
    print("門: %d / %d 合格(%.1f 秒)" % (len(CHECKS) - len(bad), len(CHECKS), time.time() - t0))
    if figs.enabled():
        assert not figs.errors(), figs.errors()
    if not bad:
        print("PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
