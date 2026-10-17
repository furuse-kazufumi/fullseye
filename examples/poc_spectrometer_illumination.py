# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 分光器と照明系の完成度 —— 帯域の幅はどこから来るか、光源の模様は視野に写るか。

【問い】ハイパースペクトルの PoC は「帯域の幅 10 nm」、クロマティック共焦点の PoC は「分光器の線幅」を
**与えられた数字**として使っていた。その数字は、入口スリットの幅・格子の溝の密度と照らされた本数・鏡の焦点距離・
検出器の画素から決まる。同じように、顕微鏡や同軸落射の照明の「むら」は、光源のどの面がどこへ写るか(共役)で
決まる。この PoC は、格子の式と近軸の共役から両方を組み立て、閉形式・公表の分光器・壊した模型で採点する。

新 op 8 本:

* `gratingspec`(`opsoptics` の新カテゴリ `spectrometer`、5 本): `grating_dispersion`(格子の式・分散・
  分解能 mN・重なる次数)/ `czerny_turner_design`(帯域と検出器からカメラの焦点距離、Shafer のコマの条件)/
  `spectrometer_bandpass`(スリットの像 ⊗ 画素 ⊗ 回折の装置関数の FWHM、エタンデュ)/ `spectrometer_slit_image`
  (3 次元の格子の式で smile と keystone)/ `spectrometer_spectrum`(入力スペクトル → 画素の読み、2 次・3 次の重なり)。
* `illumdesign`(`illumination`、3 本): `illumination_train`(ケーラー / クリティカルの照明系の共役)/
  `illumination_field`(標本の点と方向から光源まで近軸で逆に追う放射照度)/ `coaxial_illumination`
  (ハーフミラーの往復 R·T と、鏡面・つや消しの部品にカメラが見る像)。

章:

  1. **格子の式と公表の分光器**: 2 本の公開論文(CC BY 4.0)の Czerny–Turner を設計表に起こし、
     Shafer の角(14.968°)、像の幅(40 / 43 / 50 µm)、分解能(0.385〜0.391 nm)を突き合わせる。
  2. **分解能とスループットの取引**: スリットを広げるとエタンデュ(光の量)は比例して増え、帯域の幅も比例して太る。
     細くすると回折の床(0.886 λ / (mN))で止まり、そこから先は光だけを失う。Hg の黄色の 2 本(576.96 / 579.07 nm)が
     分かれるスリットの上限。
  3. **線の曲がり(smile)と台形の歪み(keystone)**: 長いスリットの像を 3 次元で追うと、スペクトル線は長い波長の側へ
     放物線に曲がる。曲率半径 ρ = f cos β / (sin α + sin β)。★面内の式を流用した「壊した模型」は曲がりを 0 にし、
     閉形式の門に落ちる。
  4. **迷光の次数**: Hg ランプの紫外線 253.65 nm / 365.02 nm は 2 次で 507.3 / 730.0 nm の画素に**偽の線**を作る。
     ロングパス 400 nm で消える。
  5. **ハイパースペクトルの帯域の幅はどこから来るか**: 900〜1700 nm の InGaAs の分光器で、HSI の PoC の
     「10 nm」がスリット何 µm に当たるかを解き、画素・回折の寄与と並べる。
  6. **クロマティック共焦点の分光器**: 可視の分光器のスリットを広げると、薄い透明板の表裏の 2 ピークが 1 つに潰れ、
     readout は厚さを当て推量せず拒否する(chromconf を読むだけ)。
  7. **照明系**: コイルの縞の光源を、クリティカル照明は視野へ写し、ケーラー照明は消す(視野の CV 1e-16)。
     視野の直径 = 視野絞り × |M|、E = L π NA²。★開口絞りをコンデンサの焦点面から 4 mm 外す探針で、縞が漏れる。
  8. **同軸落射**: 往復の R·T(50/50 で 1/4、optscene の同軸の光と同じ値)、鏡面の部品に写るパネルのむら
     (1 + h/H 倍に引き伸ばされる)、テレセントリックで 1 倍、視野の端のけられ。

【外部真値】格子の式・分散・分解能・自由スペクトル範囲(Palmer, *Diffraction Grating Handbook* 8th ed. 2020 の
式 (2-1)〜(2-27)、(8-11a)、(8-12))、Littrow の線の曲率 f / (2 tan β)(Fastie 1952)、矩形の瞳の sinc² の半値、
第 2 実装の `mathops.wave_grating_orders`(別の符号の約束)、薄肉レンズの共役、一様な長方形の Lambert 面の
形態係数の閉形式。
【公表値】Z. Feng ほか, "High-Performance Ultra-Thin Spectrometer Optical Design Based on Coddington's Equations",
Sensors 21(2):323 (2021), DOI 10.3390/s21020323, CC BY 4.0(表 1 と本文の設計値、分解能)/ "Three Criteria of M-Type
Spectrometers for Engineering", Sensors 25(8):2439 (2025), CC BY 4.0(表 1・3・7)。Hg の線の波長は NIST の原子スペクトルの
表の値(空気中)。
【正直な開示】鏡は無収差、カメラは歪曲の無い直線写像。公表の分光器の「端で悪くなる分解能」(Feng の 0.75 nm)は収差の
効果で、ここでは出ない(この PoC の値は下限)。Feng の中心 0.4 nm は、本文の f_col 40 mm・スリット 25 µm からスリットの
像だけで 0.49 nm になり、合わない(差は解かずに残す)。高次の回折効率は 1 次との比 0.3 の定数(模型)。照明は近軸で、
cos⁴ とレンズの収差は入れていない。
【学習した数】0。【較正】0。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import chromconf as CC  # noqa: E402
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import gratingspec as GS  # noqa: E402
import illumdesign as ID  # noqa: E402
import mathops  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}

#: 公表の分光器 1(Feng ほか 2021、表 1 と本文)
FENG = dict(groove_density_per_mm=900.0, wavelength_min_nm=670.0, wavelength_max_nm=1130.0, incidence_deg=45.0,
            collimator_f_mm=40.0, detector_length_mm=28.67, collimator_offaxis_deg=14.5, camera_f_mm=68.0)
#: 公表の分光器 2(M 型 2025、表 1・3・7)
MTYPE = dict(groove_density_per_mm=1200.0, wavelength_min_nm=500.0, wavelength_max_nm=750.0, incidence_deg=9.0,
             collimator_f_mm=104.1667 / 2.0, detector_length_mm=28.672, collimator_offaxis_deg=6.5,
             camera_f_mm=148.3872 / 2.0)
#: Hg の輝線(空気中の波長 nm、相対強度は見せ方のための目安)
HG = ((253.65, 1.0), (365.02, 0.6), (404.66, 0.5), (435.83, 0.8), (546.07, 1.0), (576.96, 0.35), (579.07, 0.4))


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def lamp(lo=240.0, hi=800.0, step=0.01, width=0.004, lines=HG, base=0.0):
    lam = np.arange(lo, hi, step)
    y = np.full(lam.size, base)
    for l0, a in lines:
        y = y + a * np.exp(-0.5 * ((lam - l0) / width) ** 2)
    return np.column_stack([lam, y])


def resolved(r, l1, l2):
    """2 つの山のあいだに、低い方の山の 80 % より深い谷があるか(Rayleigh の谷 0.81 に近い目安)。

    山は 2 本の中点の左右それぞれの最大、谷はその 2 つの山のあいだの最小(平らな頂上は谷にならない)。
    """
    mid = 0.5 * (l1 + l2)
    sel = np.where((r[:, 0] > l1 - 3.0) & (r[:, 0] < l2 + 3.0))[0]
    left = sel[r[sel, 0] <= mid]
    right = sel[r[sel, 0] > mid]
    il = left[int(np.argmax(r[left, 1]))]
    ir = right[int(np.argmax(r[right, 1]))]
    valley = float(r[min(il, ir):max(il, ir) + 1, 1].min())
    return valley < 0.8 * min(float(r[il, 1]), float(r[ir, 1]))


# --------------------------------------------------------------------------- #
# 1. 格子の式と公表の分光器                                                     #
# --------------------------------------------------------------------------- #
def chapter_published():
    print("\n1. 格子の式と公表の分光器")
    g = GS.grating_dispersion(1200, 550, 10, 1, focal_length_mm=100.0, illuminated_width_mm=25.0)
    r = mathops.wave_grating_orders(1000.0 / 1200, 550, -math.sin(math.radians(10)), orders=(1,))
    gate("格子の式: 第 2 実装(mathops、d(sin_out − sin_in) = mλ)と β が一致",
         abs(float(r["angle_deg"][0]) - g["beta_deg"]) < 1e-9, "β = %.6f°" % g["beta_deg"])
    gate("分解能 mN と上限 2W/λ(Palmer (2-19)・(2-23))",
         g["resolving_power"] <= g["resolving_power_max"] and abs(g["resolving_power"] - 30000.0) < 1e-6,
         "mN = %.0f、2W/λ = %.0f" % (g["resolving_power"], g["resolving_power_max"]))
    lit = math.degrees(math.asin(600e-6 * 1200 / 2.0))
    gl = GS.grating_dispersion(1200, 600, lit, 1)
    gate("Littrow の角分散 2 tan β / λ(Palmer (2-15))",
         abs(gl["angular_dispersion_rad_per_nm"] - 2 * math.tan(math.radians(lit)) / 600) < 1e-15)
    Df = GS.czerny_turner_design(**FENG)
    gate("Feng 2021: Shafer の条件でカメラ鏡の軸外し角 14.968°(表 1)",
         abs(Df["shafer_offaxis_deg"] - 14.968) < 1e-3, "%.4f°" % Df["shafer_offaxis_deg"])
    gate("Feng 2021: 中心の回折角 5.906°(表 1)", abs(Df["beta_center_deg"] - 5.906) < 1e-3,
         "%.4f°" % Df["beta_center_deg"])
    gate("Feng 2021: 式 (16) のカメラの焦点距離 ≈ r₄/2 = 68 mm(1.5 % 以内)",
         abs(Df["camera_f_linear_mm"] - 68.0) / 68.0 < 0.015, "%.2f mm" % Df["camera_f_linear_mm"])
    Bf = GS.spectrometer_bandpass(Df, 25.0, 14.0, 0.12, [670.0, 900.0, 1130.0])
    NUMBERS["feng_fwhm_center_nm"] = float(Bf["fwhm_nm"][1])
    print("   Feng 2021 の中心の分解能: 公表 0.4 nm / この module %.3f nm(スリットの像だけで %.3f nm)"
          " —— ★合わない(開示)" % (Bf["fwhm_nm"][1], Bf["slit_limited_nm"][1]))
    Dm = GS.czerny_turner_design(**MTYPE)
    Bm = GS.spectrometer_bandpass(Dm, 25.0, 14.0, 0.11, [500.0, 625.0, 750.0])
    pub_img = np.array([40.0, 43.0, 50.0])
    pub_res = np.array([0.391, 0.386, 0.385])
    e_img = np.abs(Bm["slit_image_um"] - pub_img) / pub_img
    e_res = np.abs(Bm["fwhm_nm"] - pub_res) / pub_res
    gate("M 型 2025: 像の幅 40 / 43 / 50 µm(表 7)と 6 % 以内", np.all(e_img < 0.06),
         "%s µm" % np.round(Bm["slit_image_um"], 1))
    gate("M 型 2025: 分解能 0.391 / 0.386 / 0.385 nm(表 7)と 3.5 % 以内", np.all(e_res < 0.035),
         "%s nm" % np.round(Bm["fwhm_nm"], 4))
    NUMBERS["mtype_fwhm_nm_625"] = float(Bm["fwhm_nm"][1])
    rows = [["Feng 2021(900 本/mm)", "Shafer の角", "14.968°", "%.4f°" % Df["shafer_offaxis_deg"]],
            ["", "カメラの f(式 16)", "68 mm(r₄ = 136)", "%.2f mm" % Df["camera_f_linear_mm"]],
            ["", "中心の分解能", "0.40 nm", "%.3f nm ★" % Bf["fwhm_nm"][1]],
            ["M 型 2025(1200 本/mm)", "像の幅 500 / 625 / 750 nm", "40 / 43 / 50 µm",
             " / ".join("%.1f" % v for v in Bm["slit_image_um"]) + " µm"],
            ["", "分解能 500 / 625 / 750 nm", "0.391 / 0.386 / 0.385",
             " / ".join("%.3f" % v for v in Bm["fwhm_nm"]) + " nm"]]
    return {"Dm": Dm, "rows": rows}


# --------------------------------------------------------------------------- #
# 2. 分解能とスループット                                                       #
# --------------------------------------------------------------------------- #
def chapter_tradeoff(Dm):
    print("\n2. 分解能とスループットの取引")
    ws = np.unique(np.round(np.geomspace(1.0, 150.0, 12 if REDUCED else 48), 3))
    ws[-1] = 150.0
    curves = {}
    for na in (0.02, 0.05, 0.11):
        fw = [GS.spectrometer_bandpass(Dm, float(w), 0.0, na, [625.0], pupil="rectangular")["fwhm_nm"][0] for w in ws]
        curves[na] = np.array(fw)
    et = np.array([GS.spectrometer_bandpass(Dm, float(w), 0.0, 0.05, [625.0])["etendue_mm2sr"] for w in ws])
    floor = {na: GS.spectrometer_bandpass(Dm, 0.0, 0.0, na, [625.0], pupil="rectangular") for na in curves}
    for na, B in floor.items():
        ref = GS.SINC2_FWHM * 625.0 / B["grating_resolving_power"]
        gate("回折の床 = 0.8859 λ / (mN)(NA %.2f、N = %.0f 本)" % (na, B["grooves_illuminated"]),
             abs(B["fwhm_nm"][0] - ref) / ref < 5e-4, "%.4f nm" % B["fwhm_nm"][0])
    gate("エタンデュ ∝ スリットの幅(150 / 1 = 150 倍)", abs(et[-1] / et[0] - 150.0) < 1e-9 and ws[0] == 1.0)
    big = curves[0.11][-1]
    slit_lim = 150e-3 * Dm["groove_spacing_nm"] * math.cos(math.radians(9.0)) / Dm["collimator_f_mm"]
    gate("広いスリットの帯域 = w d cos α / (m f_col)(150 µm、2 % 以内)", abs(big - slit_lim) / slit_lim < 0.02,
         "%.3f nm 対 %.3f nm" % (big, slit_lim))
    # Hg の黄色の 2 本
    sp = lamp(560.0, 600.0, lines=((576.96, 1.0), (579.07, 1.1)))
    slits = (10.0, 50.0, 150.0, 250.0, 400.0)
    spec = {w: GS.spectrometer_spectrum(Dm, sp, w, 14.0, 0.11, max_order_multiple=1) for w in slits}
    res = {w: resolved(spec[w], 576.96, 579.07) for w in slits}
    fw = {w: GS.spectrometer_bandpass(Dm, w, 14.0, 0.11, [578.0])["fwhm_nm"][0] for w in slits}
    print("   Hg 576.96 / 579.07 nm(間隔 2.11 nm): " +
          ", ".join("%d µm → FWHM %.2f nm %s" % (w, fw[w], "分かれる" if res[w] else "潰れる") for w in slits))
    gate("FWHM < 間隔 2.11 nm のスリットだけが 2 本に分ける(Rayleigh の目安と整合)",
         all(res[w] == (fw[w] < 2.11) for w in slits))
    NUMBERS["hg_doublet_last_resolving_slit_um"] = max(w for w in slits if res[w])
    return {"ws": ws, "curves": curves, "et": et, "floor": floor, "spec": spec, "fw": fw}


# --------------------------------------------------------------------------- #
# 3. smile と keystone                                                          #
# --------------------------------------------------------------------------- #
def chapter_smile(Dm):
    print("\n3. smile と keystone")
    S = GS.spectrometer_slit_image(Dm, 4.0, [500.0, 546.07, 625.0, 700.0, 750.0], n_points=41)
    e = np.abs(S["smile_um"] - S["smile_closed_um"]) / S["smile_closed_um"]
    gate("smile = y'² (sin α + sin β) / (2 f cos β)(閉形式と 0.2 % 以内、5 波長)", np.all(e < 2e-3),
         "546 nm で %.1f µm(画素 %.1f 個)" % (S["smile_um"][1], S["smile_um"][1] / 14.0))
    gate("線は長い波長の側へ曲がる(Palmer 7.2)", np.all(S["smile_um"] > 0))
    lit = math.degrees(math.asin(625e-6 * 1200 / 2.0))
    Dl = GS.czerny_turner_design(1200.0, 600.0, 650.0, lit, 100.0, 10.0, 5.0, camera_f_mm=100.0)
    Sl = GS.spectrometer_slit_image(Dl, 1.0, [625.0])
    gate("Littrow の曲率半径 f / (2 tan β)(Fastie 1952)",
         abs(Sl["curvature_radius_mm"][0] - 100.0 / (2 * math.tan(math.radians(lit)))) < 1e-9,
         "%.2f mm" % Sl["curvature_radius_mm"][0])
    Sb = GS.spectrometer_slit_image(Dm, 4.0, [500.0, 546.07, 625.0, 700.0, 750.0], n_points=41, rule="scalar")
    gate("★探針: 面内の式を流用した壊した模型は smile が 0 で、閉形式の門に落ちる",
         np.max(np.abs(Sb["smile_um"])) < 1e-6 and not np.all(np.abs(Sb["smile_um"] - Sb["smile_closed_um"])
                                                              / Sb["smile_closed_um"] < 2e-3))
    big = S["keystone_closed_um"] > 1.0
    gate("keystone = y'(λ_c)(1 / cos(β − β_c) − 1)(3 % 以内)",
         np.count_nonzero(big) >= 2 and np.all(np.abs(S["keystone_um"][big] - S["keystone_closed_um"][big]) / S["keystone_closed_um"][big] < 0.03),
         "端の 750 nm で %.1f µm" % S["keystone_um"][-1])
    gate("アナモルフィック倍率: 追跡 = (f_cam/f_col)(cos α/cos β)/cos²(β − β_c)",
         np.allclose(S["anamorphic_trace"], S["anamorphic_closed"], rtol=1e-6))
    NUMBERS["smile_546_um"] = float(S["smile_um"][1])
    NUMBERS["keystone_750_um"] = float(S["keystone_um"][-1])
    return S


def detector_frame(Dm, lines, slit_height_mm=4.0, cols=(530.0, 590.0), px=14.0, rule="vector"):
    """長いスリットの分光像(検出器の 1 コマ): 行 = スリットに沿った位置、列 = 波長(画素 14 µm)。

    返り値 (像, 各線のスリット中心の列位置)。行ごとに線の位置を追跡し、線の幅は装置関数の FWHM のガウス。
    """
    xl = GS.spectrometer_slit_image(Dm, slit_height_mm, [cols[0], cols[1]], 3, rule=rule)["x_mm"][:, 1]
    nc = int(round((xl[1] - xl[0]) * 1e3 / px))
    yimg = abs(float(GS.spectrometer_slit_image(Dm, slit_height_mm, [cols[0]], 3, rule=rule)["y_mm"][0, -1]))
    nr = int(round(2.0 * yimg * 1.1 * 1e3 / px)) | 1
    img = np.zeros((nr, nc))
    B = GS.spectrometer_bandpass(Dm, 25.0, px, 0.11, [578.0])
    sig = B["fwhm_um"][0] / 2.3548 / px
    cc = np.arange(nc)
    n_s = int(round(slit_height_mm * 1e3 / px)) | 1
    refs = []
    for l0, a in lines:
        S = GS.spectrometer_slit_image(Dm, slit_height_mm, [l0], n_s, rule=rule)
        xs, ys = S["x_mm"][0], S["y_mm"][0]
        refs.append((xs[n_s // 2] - xl[0]) * 1e3 / px)
        rows_y = (nr / 2.0 - np.arange(nr)) * px * 1e-3                 # 各行の像の高さ [mm]
        order = np.argsort(ys)
        inside = (rows_y >= ys.min()) & (rows_y <= ys.max())
        xrow = np.interp(rows_y[inside], ys[order], xs[order])           # 行ごとの線の位置(追跡の補間)
        for r0, x in zip(np.where(inside)[0], xrow):
            img[r0, :] = np.maximum(img[r0, :], a * np.exp(-0.5 * ((cc - (x - xl[0]) * 1e3 / px) / sig) ** 2))
    return img / img.max(), refs


# --------------------------------------------------------------------------- #
# 4. 迷光の次数                                                                 #
# --------------------------------------------------------------------------- #
def chapter_orders(Dm):
    print("\n4. 迷光の次数(Hg ランプ)")
    sp = lamp(240.0, 760.0, step=0.01)
    plain = GS.spectrometer_spectrum(Dm, sp, 25.0, 14.0, 0.11, max_order_multiple=3, higher_order_efficiency=0.3)
    filt = GS.spectrometer_spectrum(Dm, sp, 25.0, 14.0, 0.11, max_order_multiple=3, higher_order_efficiency=0.3,
                                    longpass_nm=400.0)

    def peak_near(r, l0, tol=1.0):
        m = np.abs(r[:, 0] - l0) < tol
        return r[m, 0][int(np.argmax(r[m, 1]))], float(r[m, 1].max())

    for uv in (253.65, 365.02):
        pos, h = peak_near(plain, 2 * uv)
        _, hf = peak_near(filt, 2 * uv)
        gate("Hg %.2f nm の 2 次が %.1f nm の画素に偽の線(フィルタで消える)" % (uv, 2 * uv),
             abs(pos - 2 * uv) < 0.3 and h > 0.0 and hf < 1e-9 * h, "位置 %.2f nm、フィルタ後 %.1e" % (pos, hf / h))
    pos, _ = peak_near(plain, 546.07)
    gate("1 次の 546.07 nm は 1 画素以内", abs(pos - 546.07) < 0.13, "%.3f nm" % pos)
    g = GS.grating_dispersion(1200, 507.3, 9.0, 1)
    gate("grating_dispersion の overlaps が 2 次の 253.65 nm を名指し",
         any(m == 2 and abs(l - 253.65) < 1e-6 for m, l in g["overlaps"]))
    return {"plain": plain, "filt": filt}


# --------------------------------------------------------------------------- #
# 5. ハイパースペクトルの帯域の幅                                               #
# --------------------------------------------------------------------------- #
def chapter_hsi():
    print("\n5. ハイパースペクトル(900〜1700 nm、InGaAs 15 µm × 640 画素)の帯域の幅")
    D = GS.czerny_turner_design(150.0, 900.0, 1700.0, 0.0, 50.0, 9.6, 8.0)
    P = D["reciprocal_dispersion_nm_per_mm"][1]
    w10 = 10.0 * abs(D["order"]) * D["collimator_f_mm"] / (D["groove_spacing_nm"] * 1.0) * 1e3   # µm、cos α = 1
    rows = {}
    for w in (8.0, 25.0, w10):
        rows[w] = GS.spectrometer_bandpass(D, w, 15.0, 0.1, [900.0, 1300.0, 1700.0])
    B10 = rows[w10]
    gate("「10 nm」はスリット %.0f µm に当たる(スリットの閉形式、全帯域で 3 %% 以内)" % w10,
         np.all(np.abs(B10["fwhm_nm"] - 10.0) / 10.0 < 0.03), "%s nm" % np.round(B10["fwhm_nm"], 2))
    B25 = rows[25.0]
    print("   画素 15 µm = %.2f nm、カメラ f %.1f mm、スリット 25 µm で FWHM %.2f nm(%s)"
          % (15e-3 * P, D["camera_f_mm"], B25["fwhm_nm"][1], B25["regime"][1]))
    gate("スリット 8 µm(像 %.1f µm < 画素 15 µm)では帯域の幅は画素で決まる" % rows[8.0]["slit_image_flat_um"][1],
         rows[8.0]["regime"][1] == "pixel", "%.2f nm" % rows[8.0]["fwhm_nm"][1])
    NUMBERS["hsi_slit_for_10nm_um"] = w10
    NUMBERS["hsi_fwhm_25um_nm"] = float(B25["fwhm_nm"][1])
    S = GS.spectrometer_slit_image(D, 6.0, [900.0, 1300.0, 1700.0])
    NUMBERS["hsi_smile_px"] = float(np.max(np.abs(S["smile_um"])) / 15.0)
    NUMBERS["hsi_keystone_px"] = float(np.max(np.abs(S["keystone_um"])) / 15.0)
    print("   スリット 6 mm の smile 最大 %.2f 画素、keystone 最大 %.2f 画素(理想の鏡、歪曲なし)"
          % (NUMBERS["hsi_smile_px"], NUMBERS["hsi_keystone_px"]))
    return {"D": D, "rows": rows, "w10": w10}


# --------------------------------------------------------------------------- #
# 6. クロマティック共焦点の分光器                                               #
# --------------------------------------------------------------------------- #
def chapter_chromconf():
    print("\n6. クロマティック共焦点の分光器(chromconf を読むだけ)")
    P = CC.chromatic_confocal_probe()
    D = GS.czerny_turner_design(600.0, 450.0, 700.0, 10.0, 50.0, 28.672, 8.0)
    slits = (25.0, 100.0, 200.0, 400.0) if REDUCED else (10.0, 25.0, 50.0, 100.0, 200.0, 400.0)
    ts = (40.0, 60.0, 100.0)
    table = {}
    for w in slits:
        fw = float(GS.spectrometer_bandpass(D, w, 14.0, 0.1, [575.0])["fwhm_nm"][0])
        for t in ts:
            sp = CC.chromatic_confocal_spectrum(P, 500.0, stack=((CC.GLASS_CROWN, t),), substrate=1.0,
                                                spectrometer_fwhm_nm=fw, wl_step_nm=0.1)
            try:
                pk = CC.chromatic_confocal_peaks(sp)
                rd = CC.chromatic_confocal_readout(pk, P, layer_material=CC.GLASS_CROWN)
                table[(w, t)] = (fw, float(rd["thickness_um"]))
            except ValueError:
                table[(w, t)] = (fw, None)
    for w in slits:
        print("   スリット %3d µm(FWHM %.2f nm): " % (w, table[(w, ts[0])][0]) +
              ", ".join("%d µm → %s" % (t, "拒否" if table[(w, t)][1] is None else "%.1f µm" % table[(w, t)][1])
                        for t in ts))
    gate("細いスリット(25 µm)は 40 µm の板の表裏を分け、厚さを 3 % 以内で読む",
         table[(25.0, 40.0)][1] is not None and abs(table[(25.0, 40.0)][1] - 40.0) / 40.0 < 0.03)
    gate("太いスリット(400 µm)では 100 µm の板まで 1 ピークに潰れ、readout は拒否する",
         all(table[(400.0, t)][1] is None for t in ts))
    gate("拒否はスリットを広げるほど厚い板へ広がる(単調)",
         all(sum(table[(slits[i], t)][1] is None for t in ts) <= sum(table[(slits[i + 1], t)][1] is None for t in ts)
             for i in range(len(slits) - 1)))
    return {"table": table, "slits": slits, "ts": ts}


# --------------------------------------------------------------------------- #
# 7. 照明系                                                                     #
# --------------------------------------------------------------------------- #
def filament(n=64, periods=4):
    xx = np.arange(n)[None, :] * np.ones((n, 1))
    yy = np.arange(n)[:, None] * np.ones((1, n))
    coil = 0.3 + 0.7 * (np.sin(xx / n * 2.0 * math.pi * periods) > 0.0)
    return coil * (0.8 + 0.2 * np.cos((yy - n / 2) / n * math.pi))


def chapter_illumination():
    print("\n7. 照明系(ケーラー / クリティカル)")
    fil = filament()
    K = ID.illumination_train("kohler", source_mm=8.0, aperture_stop_mm=3.0)
    C = ID.illumination_train("critical")
    n = 33 if REDUCED else 129
    k = 24 if REDUCED else 40
    Ek = ID.illumination_field(K, fil, shape=(n, n), n_pupil=k)
    Ec = ID.illumination_field(C, fil, shape=(n, n), n_pupil=k)
    inner = slice(n // 4, n - n // 4)
    ck, cc = Ek[inner, inner], Ec[inner, inner]
    cv_k, cv_c = ck.std() / ck.mean(), cc.std() / cc.mean()
    gate("ケーラー: コイルの縞は視野に写らない(CV < 1e-9)", cv_k < 1e-9, "CV = %.1e" % cv_k)
    gate("クリティカル: 縞が写る(CV > 0.2)", cv_c > 0.2, "CV = %.3f" % cv_c)
    gate("ケーラーの視野の直径 = 視野絞り × |M|(薄肉の閉形式)",
         abs(K["field_diameter_mm"] - 6.0 * abs(K["field_stop_magnification"])) < 1e-12,
         "%.3f mm、NA %.3f" % (K["field_diameter_mm"], K["illumination_na"]))
    Eu = ID.illumination_field(K, None, shape=(5, 5), n_pupil=96)
    gate("一様な光源で E = L π NA²(1 % 以内)", abs(Eu[2, 2] / (math.pi * K["illumination_na"] ** 2) - 1) < 0.01,
         "%.5f 対 %.5f" % (Eu[2, 2], math.pi * K["illumination_na"] ** 2))
    bad = {"elements": [dict(e) for e in K["elements"]], "field_diameter_mm": K["field_diameter_mm"]}
    for e in bad["elements"]:
        if e["name"] in ("condenser", "specimen"):
            e["z_mm"] += 4.0
    Eb = ID.illumination_field(bad, fil, shape=(n, n), n_pupil=k, field_mm=0.65)
    cb = Eb[inner, inner]
    cv_b = cb.std() / cb.mean()
    gate("★探針: 開口絞りをコンデンサの焦点面から 4 mm 外すと、縞が視野に漏れる(CV > 1e-3)", cv_b > 1e-3,
         "CV = %.4f" % cv_b)
    NUMBERS.update(kohler_cv=cv_k, critical_cv=cv_c, broken_kohler_cv=cv_b)
    return {"fil": fil, "Ek": Ek, "Ec": Ec, "Eb": Eb, "K": K, "C": C}


# --------------------------------------------------------------------------- #
# 8. 同軸落射                                                                   #
# --------------------------------------------------------------------------- #
def chapter_coaxial():
    print("\n8. 同軸落射(ハーフミラー)")
    C0 = ID.coaxial_illumination()
    gate("往復 R·T = 1/4(50/50、optscene の同軸の光と同じ値)",
         C0["round_trip"] == 0.25 and C0["splitter_reflectance"] * C0["splitter_transmittance"] == 0.25)
    Rs = np.linspace(0.05, 0.9, 171)
    rt = np.array([ID.coaxial_illumination(reflectance=float(r), absorptance=0.06)["round_trip"] for r in Rs])
    gate("吸収 6 % なら最適 R = (1 − A)/2 = 0.47、最大 (1 − A)²/4", abs(Rs[int(np.argmax(rt))] - 0.47) < 0.006
         and abs(rt.max() - 0.94 ** 2 / 4) < 1e-4)
    n = 48
    yy, xx = np.mgrid[0:n, 0:n]
    panel = (0.75 + 0.25 * xx / (n - 1)) * (1.0 - 0.35 * np.exp(-((xx - 30) ** 2 + (yy - 18) ** 2) / 40.0))
    sh = (65, 65) if REDUCED else (241, 241)
    Ce = ID.coaxial_illumination(panel_mm=50.0, field_mm=22.0, panel_radiance=panel, shape=sh)
    Ct = ID.coaxial_illumination(panel_mm=50.0, field_mm=22.0, panel_radiance=panel, shape=sh, telecentric=True)
    Cm = ID.coaxial_illumination(panel_mm=50.0, field_mm=22.0, part="matte", panel_radiance=panel,
                                 shape=(41, 41) if REDUCED else (121, 121), n_panel=40)
    gate("鏡面の部品: カメラの像の端は (panel/2) / (1 + h/H) でけられる",
         abs(Ce["vignetting_edge_mm"] - 25.0 / 1.3) < 1e-12, "%.2f mm" % Ce["vignetting_edge_mm"])
    xs = np.linspace(-22.0, 22.0, sh[1])
    lit = xs[Ce["image"][sh[0] // 2] > 0]
    gate("像のけられの位置 = 閉形式(1 画素以内)", abs(lit.max() - Ce["vignetting_edge_mm"]) <= xs[1] - xs[0])
    gate("テレセントリックならパネルは 1 倍で写り、視野 22 mm < 25 mm でけられない",
         Ct["panel_scale"] == 1.0 and np.all(Ct["image"] > 0))
    Cc = ID.coaxial_illumination(part="matte", shape=(5, 5), n_panel=200, field_mm=1.0)
    gate("つや消しの部品の中心 = 長方形の Lambert 面の閉形式 × R·T/π(0.2 % 以内)",
         abs(Cc["image"][2, 2] / Cc["matte_centre_closed"] - 1) < 2e-3)
    return {"panel": panel, "Ce": Ce, "Ct": Ct, "Cm": Cm, "Rs": Rs, "rt": rt}


# --------------------------------------------------------------------------- #
# 図                                                                           #
# --------------------------------------------------------------------------- #
def make_figures(pub, tr, Dm, orders, hsi, ccf, ill, coax):
    # 1. 取引: 左 = 細いスリットの側(回折の床)、右 = 分解能とエタンデュの取引(両対数)
    small = tr["ws"] <= 30.0
    left = figs.render_plot([("NA %.2f" % na, tr["ws"][small], c[small]) for na, c in tr["curves"].items()]
                            + [("回折の床 0.886 λ/(mN)(NA %.2f)" % na, np.array([0.0, 30.0]),
                                np.array([tr["floor"][na]["fwhm_nm"][0]] * 2)) for na in tr["curves"]],
                            xlabel="スリットの幅 [µm]", ylabel="帯域の幅 FWHM [nm]",
                            title="細くしても回折の床で止まる(625 nm、矩形の瞳)",
                            styles=[None, None, None, "dashed", "dashed", "dashed"], size=(640, 420))
    R = 625.0 / tr["curves"][0.05]
    right = figs.render_plot([("NA 0.05(スリット 1〜150 µm)", np.log10(tr["et"] / tr["et"][0]), np.log10(R)),
                              ("回折の床 λ/FWHM", np.array([0.0, math.log10(150.0)]),
                               np.log10(np.array([625.0 / tr["floor"][0.05]["fwhm_nm"][0]] * 2))),
                              ("傾き −1(スリットで決まる: 光 × 分解能 = 一定)", np.array([1.0, math.log10(150.0)]),
                               np.log10(R[-1]) + (math.log10(150.0) - np.array([1.0, math.log10(150.0)])))],
                             xlabel="log10 エタンデュ(スリット 1 µm を 0)", ylabel="log10 分解能 λ/FWHM",
                             title="光を 10 倍集めると分解能は 1/10(広いスリット)", styles=[None, "dashed", "dotted"],
                             colors=[None, "reference", "neutral"], size=(640, 420))
    figs.save("resolution_vs_throughput", np.concatenate([left, right], axis=1),
              "スリットの幅で帯域の幅とエタンデュがどう動くか(1200 本/mm、M 型 2025 の設計、625 nm)。左: 細いスリットは"
              "回折の床 0.886 λ / (mN) で止まり、NA を上げて照らす溝を増やすと床が下がる。右: 広いスリットでは光の量と"
              "分解能の積が一定(傾き −1)、細くしていくと床に当たって光だけを失う。")
    figs.save_plot("mercury_yellow_doublet",
                   [("スリット %d µm(FWHM %.2f nm)" % (w, tr["fw"][w]), r[k, 0], r[k, 1] / r[:, 1].max())
                    for w, r in tr["spec"].items() for k in [(r[:, 0] >= 572.0) & (r[:, 0] <= 584.0)]],
                   xlabel="波長 [nm](画素の中心)", ylabel="読み(最大 = 1)", xlim=(572.0, 584.0),
                   title="Hg 576.96 / 579.07 nm: 帯域の幅 < 2.11 nm で 2 本",
                   caption="Hg の黄色の 2 本を、スリットの幅を変えて読む。FWHM が間隔 2.11 nm を超えると 1 本に潰れる。",
                   size=(900, 420))
    # 3. 分光像(smile): 1 コマ(等倍)に、中心の点を通る真っすぐな赤い参照線を重ねる + 546 nm の線の 4 倍拡大
    lines = ((546.07, 1.0), (576.96, 0.45), (579.07, 0.5))

    def overlay(fr, refs):
        im = np.dstack([fr, fr, fr])
        for c in refs:
            c0 = int(round(c))
            im[::8, c0, :] = (0.9, 0.15, 0.1)
            im[1::8, c0, :] = (0.9, 0.15, 0.1)
        return im

    fr, refs = detector_frame(Dm, lines, cols=(540.0, 585.0))
    frb, refsb = detector_frame(Dm, lines, cols=(540.0, 585.0), rule="scalar")
    gap = np.ones((fr.shape[0], 8, 3))
    top = np.concatenate([fs.text_box(overlay(fr, refs), "3 次元の格子の式(正しい)", (6, 6), anchor="lt", font_size=13), gap,
                          fs.text_box(overlay(frb, refsb), "面内の式の流用(壊した模型)", (6, 6), anchor="lt", font_size=13)],
                         axis=1)
    c0 = int(round(refs[0]))
    zoom = []
    for f, r in ((fr, refs), (frb, refsb)):
        z = overlay(f, r)[:, max(0, c0 - 20):c0 + 21]
        zoom.append(np.repeat(z, 6, axis=1))                       # 横だけ 6 倍(縦は等倍)
    zr = np.concatenate([fs.text_box(zoom[0], "546 nm 横×6(正しい)", (4, 4), anchor="lt", font_size=11),
                         np.ones((zoom[0].shape[0], 8, 3)),
                         fs.text_box(zoom[1], "横×6(壊した模型)", (4, 4), anchor="lt", font_size=11)], axis=1)
    pad = np.ones((top.shape[0], 12, 3))
    figs.save("slit_image_smile", np.concatenate([top, pad, zr], axis=1),
              "長いスリット(4 mm)の Hg 546 / 577 / 579 nm を検出器の 1 コマに描く(画素 14 µm、左 2 枚は等倍、右は 546 nm の線を"
              "横に 6 倍)。赤の点線は線の中心を通る真っすぐな参照。正しい 3 次元の式では線の両端が長い波長の側(右)へ約 3 画素"
              "曲がる(smile)。面内の式を流用した模型は真っすぐ —— 閉形式の門に落ちる。")
    S = GS.spectrometer_slit_image(Dm, 4.0, [546.07, 576.96, 579.07], n_points=41)
    figs.save_plot("smile_closed_form",
                   [("%.2f nm(追跡)" % l, S["slit_points_mm"], (S["x_mm"][i] - S["x_mm"][i][20]) * 1e3 / 14.0)
                    for i, l in enumerate(S["wavelengths_nm"])]
                   + [("閉形式 y'²/(2ρ)(546 nm)", S["slit_points_mm"],
                       (S["y_mm"][0] ** 2 / (2 * S["curvature_radius_mm"][0])) * 1e3 / 14.0)],
                   xlabel="スリットに沿った位置 [mm]", ylabel="線のずれ [画素 14 µm]",
                   title="smile: 中央からのずれ", styles=[None, None, None, "dashed"],
                   colors=[None, None, None, "reference"], size=(640, 420),
                   caption="smile の追跡(実線)と閉形式 y'²/(2ρ)、ρ = f cos β / (sin α + sin β)(破線)。")
    # 4. 迷光の次数
    figs.save_plot("second_order_ghosts",
                   [("フィルタなし", orders["plain"][:, 0], orders["plain"][:, 1]),
                    ("ロングパス 400 nm", orders["filt"][:, 0], orders["filt"][:, 1])],
                   xlabel="波長 [nm](1 次の校正)", ylabel="読み",
                   title="Hg ランプ: 253.65 と 365.02 nm が 2 次で 507.3 / 730.0 nm に化ける",
                   caption="1 次の 500〜750 nm の検出器に、紫外の Hg 線の 2 次の像が偽の線として乗る(効率 0.3 の模型)。"
                           "ロングパス 400 nm で消える。", styles=[None, "dashed"], size=(960, 420))
    # 5. HSI
    series = []
    for w, B in hsi["rows"].items():
        ls = B["line_shapes"][1]
        ls = ls[np.abs(ls[:, 0]) <= 15.0]
        series.append(("スリット %.0f µm(FWHM %.1f nm、%s)" % (w, B["fwhm_nm"][1], B["regime"][1]), ls[:, 0], ls[:, 1]))
    g = np.linspace(-15, 15, 301)
    series.append(("HSI の PoC の仮定: ガウス 10 nm", g, np.exp(-4 * math.log(2) * (g / 10.0) ** 2)))
    figs.save_plot("hsi_band_shape", series, xlabel="Δλ [nm]", ylabel="装置関数(最大 = 1)",
                   title="HSI の「10 nm」はどこから来るか(1300 nm、InGaAs 15 µm)", styles=[None, None, None, "dashed"],
                   colors=[None, None, None, "reference"], xlim=(-15, 15),
                   caption="150 本/mm・コリメータ f 50 mm・InGaAs 15 µm の分光器。スリット 8 µm では画素で決まる %.1f nm、"
                           "25 µm で %.1f nm、10 nm にするにはスリット %.0f µm(台形の装置関数で、ガウスではない)。"
                           % (hsi["rows"][8.0]["fwhm_nm"][1], hsi["rows"][25.0]["fwhm_nm"][1], hsi["w10"]),
                   size=(900, 420))
    # 6. chromconf
    rows = [["スリット %d µm" % w, "%.2f nm" % ccf["table"][(w, ccf["ts"][0])][0]]
            + ["拒否" if ccf["table"][(w, t)][1] is None else "%.1f µm" % ccf["table"][(w, t)][1] for t in ccf["ts"]]
            for w in ccf["slits"]]
    figs.save_table("chromconf_plate_vs_slit", ["分光器", "FWHM"] + ["板 %d µm" % t for t in ccf["ts"]], rows,
                    title="クロマティック共焦点: 分光器のスリットと読める板の厚さ",
                    caption="可視の分光器(600 本/mm)のスリットを広げると、薄い板の表裏の 2 ピークが 1 つに潰れ、readout は"
                            "厚さを当て推量せず拒否する。")
    # 7. 照明(全パネル同じ大きさ、0 を黒・各パネルの最大を白)
    n = ill["Ek"].shape[0]
    iy = (np.arange(n) * ill["fil"].shape[0] // n).astype(int)
    src = ill["fil"][np.ix_(iy, iy)]                      # 最近傍で n × n へ
    figs.save_grid("kohler_vs_critical", [src, ill["Ec"], ill["Ek"], ill["Eb"]],
                   ["光源(コイルの縞)", "クリティカル: 縞が写る(CV %.2f)" % NUMBERS["critical_cv"],
                    "ケーラー: 一様(CV %.0e)" % NUMBERS["kohler_cv"],
                    "壊したケーラー(焦点面から 4 mm、CV %.3f)" % NUMBERS["broken_kohler_cv"]], ncols=2, gray=True,
                   vrange=[None] + [(0.0, float(ill[k].max())) for k in ("Ec", "Ek", "Eb")],
                   caption="同じ縞の光源で、クリティカル照明は光源を標本に写し、ケーラー照明は光源をコンデンサの前側焦点面に"
                           "写して視野を一様にする(明るさは各パネルの最大を白に。クリティカルの NA は 0.05、ケーラーは 0.15)。開口絞りを焦点面から外すと縞と縁のぼけが出る。")
    # 8. 同軸(全パネル同じ大きさ、鏡面の 2 枚は同じ尺度 0〜R·T)
    m = coax["Ce"]["image"].shape[0]

    def up(a):                                            # 最近傍で m × m へ(値は作らない)
        iy = (np.arange(m) * a.shape[0] // m).astype(int)
        ix = (np.arange(m) * a.shape[1] // m).astype(int)
        return a[np.ix_(iy, ix)]

    figs.save_grid("coaxial_views", [up(coax["panel"]), coax["Ce"]["image"], coax["Ct"]["image"], up(coax["Cm"]["image"])],
                   ["パネルの放射輝度(50 mm 角)", "鏡面・通常のレンズ(1.3 倍、端がけられる)", "鏡面・テレセントリック(1 倍)",
                    "つや消しの部品(模様は消え、周辺が落ちる)"], ncols=2, gray=True,
                   vrange=[None, (0.0, 0.25), (0.0, 0.25), None],
                   caption="同軸落射(視野 44 mm 角): 鏡面の部品はパネルそのものを写す(R·T = 1/4)。通常のレンズは 1 + h/H 倍に"
                           "引き伸ばし、視野の端でパネルの外を見て黒くなる。テレセントリックは 1 倍。つや消しの部品はパネル全体を"
                           "積分するので模様は消えるが、パネルが有限なぶん周辺が暗くなる。")
    figs.save_table("published_spectrometers", ["分光器", "量", "公表値", "この module"], pub["rows"],
                    title="公表の分光器との照合(CC BY 4.0 の論文)",
                    caption="Feng 2021 の中心の分解能だけが合わない(スリットの像だけで 0.49 nm)。差は解かずに残す。")


def main():
    t0, c0 = time.time(), time.process_time()
    print("PoC 分光器と照明系(予算 %s)" % ("reduced" if REDUCED else "full"))
    pub = chapter_published()
    Dm = pub["Dm"]
    tr = chapter_tradeoff(Dm)
    chapter_smile(Dm)
    orders = chapter_orders(Dm)
    hsi = chapter_hsi()
    ccf = chapter_chromconf()
    ill = chapter_illumination()
    coax = chapter_coaxial()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(pub, tr, Dm, orders, hsi, ccf, ill, coax)
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    for k, v in NUMBERS.items():
        print("   %s = %.6g" % (k, v))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
