# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_photoelasticity — 光弾性で**応力**を測る(円板の直径圧縮、真値は閉形式)。

    py -3.11 examples/poc_photoelasticity.py

【この PoC が答える問い】
実験力学の教室でいちばん普通の問い —「透明な試験片を偏光板ではさんで縞を撮った。
この縞から応力が何 MPa か言えるか。どこで言えなくなるか」。
答えは「主応力差は **±2 % 台**で言える。ただし縞次数が 0.5 を超えた瞬間に
位相が巻き、**巻きを解く手順を持たない限り応力は多価**になる。しかも
巻き戻しが最初に失敗するのは応力が大きい所ではなく、**主応力差がゼロになる
等方点(isotropic point)**という、いちばん応力が小さい所」。

【グラウンドトゥルース(自分で仕込んだ真値)】
円板を直径方向に圧縮したときの平面応力場には**閉形式**がある(Hondros / Frocht)。
応力場から偏光像までは**光弾性の族の op**(``photoelastic.py``)で組む:

    brazilian_disc_stress → principal_stress → photoelastic_retardation
      → polariscope_intensity(暗視野・明視野・平面偏光)
      → photoelastic_polarization_images(6 強度)→ photoelastic_phase_estimate

応力光学則は N = h(σ1-σ2)/fσ(N = 縞次数)、位相差 δ = 2πN。
族の op は 1 節で ``mueller_element`` の素子を 1 枚ずつ並べた鎖(別の実装)と
突き合わせてから使う。旧版(2026-09-06、応力場も位相子の場も手書き)の計算は
``tests/test_poc_photoelasticity_ops.py`` に独立な参照として残し、値の一致を門にしてある。

材料: エポキシ相当(fσ = 10.7 N/mm/縞)、円板 φ50 mm × 厚 6 mm、荷重 500 N。
中心の主応力差は 8P/(πDh) = 4.24 MPa、縞次数 2.38。

【節立て】
 1) ★検算 —— (a) Mueller の鎖が教科書式と、族の偏光像が鎖と一致するか (b) 応力場が力の釣り合いを満たすか
 2) ★ゼロ点 —— 「一様応力 P/(Dh) と答える」推定器に勝てるか
 3) 暗視野 1 枚から縞次数を数える —— 整数の縞しか読めない
 4) ★位相シフト —— δ と θ を分ける
 5) ★★位相の巻き —— 壊れるのは応力が大きい所ではなく**等方点**
 6) 雑音と 8 bit 量子化
 7) 所見
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import photoelastic as pe                                        # noqa: E402
from fullseye.evaluation import save_video as save_evaluation_video  # noqa: E402

# --- 試験片と光学系の諸元(表示は mm・MPa、op へは SI で渡す)------------------ #
R_MM = 25.0             # 円板の半径 [mm]
H_MM = 6.0              # 厚さ [mm]
P_N = 500.0             # 荷重 [N]
F_SIGMA = 10.7          # 材料の縞値 [N/(mm·縞)] —— エポキシの実測値の並び
LAMBDA_M = 5.5e-7       # 波長 [m]。fσ はこの波長での値(δ は fσ だけで決まる)
C_PA = LAMBDA_M / (F_SIGMA * 1e3)   # 応力光学係数 [Pa⁻¹] = λ/fσ(5.1e-11、樹脂の桁)
NPIX = 257              # 奇数にして中心を画素に乗せる
PX_MM = 2.0 * R_MM / (NPIX - 1)


def fields(npix=NPIX):
    """円板の応力場 → 主応力差・等傾角・位相差(全部 op)。返りは表示単位の dict。

    ``dsig`` [MPa] = σ1-σ2、``theta`` [rad] = σ1 の向き(x 軸から反時計回り)、
    ``delta`` [rad]、``order`` = 縞次数、``in_disc`` = 半径 0.9R の内側
    (荷重点 (0, ±R) では応力が発散する。実験でも接触部は読まないので評価はここまで。
    それでも縞次数は 12 まで出る)。
    """
    disc = pe.brazilian_disc_stress(radius_m=R_MM * 1e-3, thickness_m=H_MM * 1e-3,
                                    load_n=P_N, size=npix)
    ps = pe.principal_stress(disc["sxx"], disc["syy"], disc["txy"])
    ret = pe.photoelastic_retardation(ps["difference"], H_MM * 1e-3, C_PA, LAMBDA_M)
    in_disc = np.hypot(disc["x"], disc["y"]) <= R_MM * 1e-3 * 0.90
    return {"dsig": ps["difference"] / 1e6, "theta": np.deg2rad(ps["angle_deg"]),
            "angle_deg": ps["angle_deg"], "delta": ret["delta_rad"], "order": ret["fringe_order"],
            "in_disc": in_disc, "disc": disc, "ret": ret}


def build_fields():
    """``(σ1-σ2 [MPa], θ [rad], δ [rad])`` —— ViEW2026 の掃引ビューア(tools/)もこれを呼ぶ。"""
    f = fields()
    return f["dsig"], f["theta"], f["delta"]


_F = fields()
IN_DISC = _F["in_disc"]


def specimen_frames(delta, theta):
    """円偏光照明の試料を 6 強度の偏光計で撮った像 ``(6, H, W)``(0/45/90/135/右/左)。

    エポキシは C > 0 なので σ1 が**遅相軸**。op の位相子の角は進相軸なので θ + 90° を渡す
    (``photoelastic_retardation`` の docstring の規約)。
    """
    return pe.photoelastic_polarization_images(delta, np.rad2deg(theta) + 90.0, "stokes6")


def stokes_from_frames(frames):
    """6 強度 → 試料を出た Stokes ``(S0, S1, S2, S3)``。偏光計で測れるのはこの 4 つだけ。"""
    i0, i45, i90, i135, ir, il = frames
    return i0 + i90, i0 - i90, i45 - i135, ir - il


def polariscope_image(delta, theta, analyser_deg=90.0):
    """円偏光ポラリスコープ P(0°)→QWP(45°)→試料→QWP(-45°)→A(analyser) の強度。

    検光子 90° が暗視野(= ``polariscope_intensity(..., "circular_dark")``)、0° が明視野。
    途中の角度は族の op に無いので、試料を出た Stokes(:func:`specimen_frames`)に
    後段の 2 素子を ``mueller_element`` / ``mueller_apply`` で掛ける(ViEW2026 の掃引用)。
    """
    s = np.stack(stokes_from_frames(specimen_frames(delta, theta)), axis=-1)
    post = (np.asarray(fs.mueller_element("polarizer", analyser_deg))
            @ np.asarray(fs.mueller_element("quarter_wave", -45.0)))
    return np.asarray(fs.mueller_apply(post, s))[..., 0]


def to_mpa(delta_rad):
    """位相差 [rad] → 主応力差 [MPa](縞次数 = waves、N = h(σ1-σ2)/fσ)。"""
    return F_SIGMA * pe.retardation_convert(delta_rad, "rad", "waves") / H_MM


# =========================================================================== #
def section1_check():
    print("=" * 78)
    print("1) ★検算 —— 族の偏光像と、応力場そのもの")
    print("=" * 78)
    # (a) 族の op(閉形式)と、mueller_element の素子を 1 枚ずつ並べた鎖(optics 側の別実装)。
    q1 = np.asarray(fs.mueller_element("quarter_wave", 45.0))
    post = (np.asarray(fs.mueller_element("polarizer", 90.0))
            @ np.asarray(fs.mueller_element("quarter_wave", -45.0)))
    s_in = np.asarray(fs.mueller_apply(q1, np.array([1.0, 1.0, 0.0, 0.0])))
    d_deg = np.arange(0.0, 361.0, 15.0)
    th_deg = np.array([0.0, 13.0, 30.0, 45.0, 71.0])
    dd, tt = np.meshgrid(np.deg2rad(d_deg), th_deg, indexing="ij")     # δ [rad] × θ [deg]
    i_op = pe.polariscope_intensity(dd, tt, "circular_dark")
    frames = pe.photoelastic_polarization_images(dd, tt + 90.0, "stokes6")
    worst_t = worst_i = worst_s = 0.0
    for a in range(dd.shape[0]):
        for b in range(dd.shape[1]):
            # 暗視野は進相軸の取り方に依らない。教科書式との照合は初版と同じ角(θ)のまま、
            # 族の op との照合は op の規約(進相軸 = σ1 + 90°)で組む。
            i_text = float(np.sin(np.deg2rad(d_deg[a]) / 2.0) ** 2)
            m0 = np.asarray(fs.mueller_element("retarder", th_deg[b], d_deg[a]))
            worst_t = max(worst_t, abs(float((post @ (m0 @ s_in))[0]) - i_text))
            m = np.asarray(fs.mueller_element("retarder", th_deg[b] + 90.0, d_deg[a]))
            s = m @ s_in
            worst_i = max(worst_i, abs(float((post @ s)[0]) - float(i_op[a, b])))
            got = np.array([f[a, b] for f in stokes_from_frames(frames)])
            worst_s = max(worst_s, float(np.max(np.abs(got - s))))
    n_case = dd.size
    print("  (a) mueller_element の鎖(暗視野円偏光)vs 教科書式 I = sin²(δ/2)      :"
          " %d 通りの最大差 %.3e" % (n_case, worst_t))
    print("      `polariscope_intensity`(暗視野円偏光)vs mueller_element の鎖:"
          " %d 通りの最大差 %.3e" % (n_case, worst_i))
    print("      `photoelastic_polarization_images` の Stokes vs 同じ鎖     :"
          " %d 通りの最大差 %.3e" % (n_case, worst_s))
    print("      → 一致。**しかも暗視野は θ に依らない**(円偏光系の要件)ことも同時に確認。")
    # ★所見を固定する: δ を 15 度刻みで一周・θ を 5 通り振っても機械精度で一致する。
    #   族の op(閉形式)と optics の素子の鎖は別の実装なので、ここは自己一致ではない。
    #   ここが緩んだら 3 節以降で測っているのは「読み取り手順」ではなく op のバグ。
    assert n_case == 125
    assert worst_t < 1e-12 and worst_i < 1e-12 and worst_s < 1e-12, (worst_t, worst_i, worst_s)

    # (b) 応力場が力の釣り合いを満たすか(水平直径上の σyy を積分すると -P/h)。
    r_m, h_m = R_MM * 1e-3, H_MM * 1e-3
    x = np.linspace(-r_m * (1 - 1e-9), r_m * (1 - 1e-9), 20001)
    on_line = pe.brazilian_disc_stress(r_m, h_m, P_N, x=x, y=np.zeros_like(x))
    load = np.trapezoid(on_line["syy"], x) * h_m
    print()
    print("  (b) 水平直径上の σyy を積分した力: %.3f N(真値 -%.1f N、誤差 %.3f %%)"
          % (load, P_N, 100 * abs(load / (-P_N) - 1)))
    c = (NPIX - 1) // 2
    d0 = float(_F["dsig"][c, c])
    closed = 8 * P_N / (np.pi * 2 * R_MM * H_MM)
    n_centre = float(_F["order"][c, c])
    fv = _F["ret"]["fringe_value_n_per_m"]
    print("      中心の主応力差 %.4f MPa(閉形式 8P/(πDh) = %.4f)" % (d0, closed))
    print("      中心の縞次数 N = h(σ1-σ2)/fσ = %.3f(材料縞値 λ/C = %.1f N/m を op が返す)"
          % (n_centre, fv))
    print()
    print("  → ここまで近似ゼロ。以降のずれは全部『読み取り手順』のもの。")
    # ★応力場そのものの検算も固定する。積分した力が荷重に一致しなければ
    #   「真値」ではないし、中心値は閉形式 8P/(πDh) と代数的に同じはず。
    assert abs(load / (-P_N) - 1.0) < 1e-4, "力の釣り合いが崩れた: %.4f N" % load
    assert abs(d0 / closed - 1.0) < 1e-9, (d0, closed)
    #   C = λ/fσ で渡したので、op の返す材料縞値は fσ に戻る(単位の取り違えの門)。
    assert abs(fv / (F_SIGMA * 1e3) - 1.0) < 1e-12, fv
    return n_centre


def section2_zero_point(dsig, delta):
    print()
    print("=" * 78)
    print("2) ★ゼロ点 —— 「一様応力と答える」推定器に勝てるか")
    print("=" * 78)
    naive = P_N / (2 * R_MM * H_MM)
    m = IN_DISC & (np.abs(delta) < np.pi)          # 巻きの無い領域だけで比べる
    err0 = float(np.mean(np.abs(naive - dsig[m])))
    print("  ゼロ点 = 公称圧縮応力 P/(D·h) = %.4f MPa と一律に答える。" % naive)
    print("  巻きの無い領域(N < 0.5、円板の %.0f %%)での平均絶対誤差:"
          % (100 * m.sum() / IN_DISC.sum()))
    print("    ゼロ点 : %.4f MPa" % err0)
    # ★ゼロ点の水準を固定する。以降の「◯倍」はすべてこの 1.09 MPa を分母にしている
    #   ので、ここが動くと比較の意味が変わる。
    assert 1.0 < err0 < 1.2, err0
    return naive, m, err0


def section3_dark_field(dsig, theta, delta, naive, m):
    print()
    print("=" * 78)
    print("3) 暗視野 1 枚から縞次数を数える —— 整数しか読めない")
    print("=" * 78)
    ang = np.rad2deg(theta)
    img = pe.polariscope_intensity(delta, ang, "circular_dark")
    # 暗線(I=0)は N が整数の等値線。最も素朴な読み方 = 「最寄りの暗線の次数」を読む。
    n_int = np.round(pe.retardation_convert(delta, "rad", "waves"))
    est = F_SIGMA * n_int / H_MM
    e = float(np.mean(np.abs(est[m] - dsig[m])))
    print("  暗視野画像の輝度: 最小 %.4f 最大 %.4f(理論 sin²(δ/2) と同形)"
          % (img[IN_DISC].min(), img[IN_DISC].max()))
    print("  最寄りの暗線の整数次数だけを読んだときの平均絶対誤差: %.4f MPa" % e)
    gain = float(np.mean(np.abs(naive - dsig[m]))) / max(e, 1e-12)
    print("  ゼロ点 %.4f MPa に対して %.2f 倍。"
          % (float(np.mean(np.abs(naive - dsig[m]))), gain))
    # ★所見を固定する: 暗視野 1 枚から整数の縞だけ読む素朴な手順は、ゼロ点に
    #   **2 倍も勝てない**。分解能が fσ/h = 1.78 MPa の刻みに律速されるため。
    #   4 節の位相シフト(誤差が機械精度まで落ちる)との対比がこの PoC の骨格。
    assert 1.5 < gain < 2.5, gain
    assert e > 0.3, e
    bright = pe.polariscope_intensity(delta, ang, "circular_bright")
    plane = pe.polariscope_intensity(delta, ang, "plane_dark", polarizer_deg=0.0)
    figs.save_grid("polariscope",
                   [np.where(IN_DISC, img, 0.0), np.where(IN_DISC, bright, 0.0),
                    np.where(IN_DISC, plane, 0.0), np.where(IN_DISC, dsig, 0.0)],
                   ["暗視野(円偏光)", "明視野(円偏光)",
                    "平面偏光(等傾線が混ざる)", "主応力差 σ1-σ2 [MPa](真値)"],
                   title="円板の直径圧縮 —— ポラリスコープ像と真値",
                   caption="応力場も偏光像も光弾性の族の op(brazilian_disc_stress → polariscope_intensity)で組んだ。")
    print("  → 整数の縞しか読まないと **fσ/h = %.3f MPa の刻み**でしか答えられない。"
          % (F_SIGMA / H_MM))
    print("     縞が 2 本しか出ていない試験片では、これは実質「3 段階」の分解能。")
    return e, gain


def section4_phase_shift(dsig, theta, delta, m):
    print()
    print("=" * 78)
    print("4) ★位相シフト —— δ と θ を分ける。ただし分けきれない")
    print("=" * 78)
    print("  ※ここは**手順の検算**(雑音ゼロで、同じ強度式から解き戻す)。")
    print("    実測の誤差は 6 節(雑音・量子化)で出す。")
    frames = specimen_frames(delta, theta)
    _s0, s1, s2, s3 = stokes_from_frames(frames)

    # (i) 等傾角。平面偏光 4 枚から 4θ が出る。
    i0, i1, i2, i3 = (pe.polariscope_intensity(delta, np.rad2deg(theta), "plane_dark", polarizer_deg=b)
                      for b in (0.0, 22.5, 45.0, 67.5))
    th_hat = 0.25 * np.arctan2(i3 - i1, i2 - i0)
    ang = np.abs(np.mod(th_hat - theta + np.pi / 4, np.pi / 2) - np.pi / 4)
    ang_p90 = float(np.rad2deg(np.percentile(ang[IN_DISC], 90)))
    print()
    print("  等傾角 θ の誤差: 中央値 %.4f 度 / 90 パーセンタイル %.4f 度"
          % (np.rad2deg(np.median(ang[IN_DISC])), ang_p90))
    # ★雑音ゼロで同じ強度式から解き戻しているので、θ は**厳密に**戻るはず
    #   (4 枚の平面偏光から 4θ を出す代数がそのまま逆写像になっている)。
    assert ang_p90 < 1e-6, ang_p90

    # (ii) 位相差。θ を使うと sinδ の**符号まで**取れる(進相軸 = θ + 90° で読む)。
    fast = th_hat + np.pi / 2
    d_hat = np.arctan2(s2 * np.cos(2 * fast) - s1 * np.sin(2 * fast), s3)     # (-π, π]
    wrapped_true = np.mod(delta + np.pi, 2 * np.pi) - np.pi
    err = np.abs(np.mod(d_hat - wrapped_true + np.pi, 2 * np.pi) - np.pi)
    agree = 100 * float(np.mean((err < 0.05)[IN_DISC]))
    print("  巻いたままの δ(-π, π] の一致率: %.1f %%(誤差 < 0.05 rad)" % agree)
    print()
    print("  → ★残りの %.1f %% は**符号が反転**している。原因は光弾性で有名な"
          % (100 - agree))
    print("     (δ, θ) ↔ (-δ, θ+90°) の二義性 —— 出てくる Stokes が同じなので、")
    print("     **1 波長の 1 回の測定では原理的に分けられない**。等傾角の")
    print("     復元も 4θ からなので θ は π/2 の周期しか決まらず、その飛びが")
    print("     そのまま δ の符号の飛びになる。")
    # 符号を捨てた |δ| ∈ [0, π] は `photoelastic_phase_estimate`(6 強度)がそのまま返す。
    est = pe.photoelastic_phase_estimate(frames, "stokes6")
    fold_gap = float(np.max(np.abs(est["delta_rad"] - np.abs(d_hat))[IN_DISC]))
    abs_err = float(np.mean(np.abs(to_mpa(est["delta_rad"])[m] - dsig[m])))
    print("     |δ| だけを使えば(`photoelastic_phase_estimate` の返り)主応力差は"
          " N<0.5 の領域で誤差 %.2e MPa。" % abs_err)
    print("     op の |δ| と上の符号つき推定の絶対値の差: 最大 %.1e rad" % fold_gap)
    # ★所見を固定する。
    #   (1) 一致率は 95 % を超えるが、**100 % にはならない**。残りは (δ,θ) ↔ (-δ,θ+90°)
    #       の二義性で符号が反転した画素で、1 波長 1 回の測定では原理的に消せない。
    assert 95.0 < agree < 99.5, agree
    #   (2) 符号を捨てて |δ| だけ使えば、巻きの無い領域では機械精度で戻る
    #       (3 節の 0.58 MPa と比べると 15 桁ちがう)。op の閉形式の逆算と、
    #       平面偏光の θ を経由した上の手順は同じ |δ| を出す。
    assert abs_err < 1e-12, abs_err
    assert fold_gap < 1e-12, fold_gap
    return d_hat, th_hat, s1, s2, s3, abs_err, agree


def section5_wrapping(dsig, delta, d_hat, s1, s2, s3):
    print()
    print("=" * 78)
    print("5) ★★位相の巻きを解く —— 壊れる場所は 2 つ、どちらも予測できる")
    print("=" * 78)
    n_true = pe.retardation_convert(delta, "rad", "waves")
    print("  縞次数 N: 最小 %.3f / 中央 %.3f / 最大 %.3f(半径 0.9R まで)"
          % (n_true[IN_DISC].min(), np.median(n_true[IN_DISC]), n_true[IN_DISC].max()))
    print("  N > 0.5 = 位相が巻いている画素: %.1f %%"
          % (100 * float(np.mean(n_true[IN_DISC] > 0.5))))

    # 縞の間隔。1 縞あたり 2 画素を切ると標本化定理から復元できない。
    gy, gx = np.gradient(n_true)
    px_per_fringe = 1.0 / np.maximum(np.hypot(gx, gy), 1e-12)
    aliased = IN_DISC & (px_per_fringe < 2.0)
    print("  1 縞あたりの画素数: 中央 %.1f / 最小 %.2f。**2 画素未満** = %.1f %%"
          % (np.median(px_per_fringe[IN_DISC]), px_per_fringe[IN_DISC].min(),
             100 * aliased.sum() / IN_DISC.sum()))

    # 変調度 = sinδ と cosδ の振幅。等方点(δ→0 mod 2π)でゼロに落ちる。
    modulation = np.hypot(np.hypot(s1, s2), s3)
    lowmod = IN_DISC & (np.hypot(s1, s2) < 0.05)
    print("  変調度 |sinδ| < 0.05(等方点および N が整数の帯): %.1f %%"
          % (100 * lowmod.sum() / IN_DISC.sum()))
    print("  (Stokes の大きさは %.4f〜%.4f = 減偏光なし。変調が落ちるのは"
          % (modulation[IN_DISC].min(), modulation[IN_DISC].max()))
    print("   光量ではなく**位相の感度**のほう)")

    wrapped = np.mod(d_hat + np.pi, 2 * np.pi) - np.pi
    print()
    print("  %-34s %12s" % ("巻き戻しの入力", "一致率(<π/2)"))
    print("  " + "-" * 50)
    rates = {}
    for label, mask in [("そのまま(マスク無し)", None),
                        ("標本化不足を外す", ~aliased),
                        ("標本化不足 + 低変調を外す", ~aliased & ~lowmod)]:
        kw = {} if mask is None else {"mask": mask}
        unwrapped = np.asarray(fs.ledger.unwrap_phase_2d(wrapped, **kw))
        valid = IN_DISC & np.isfinite(unwrapped)
        off = float(np.median((unwrapped - delta)[valid]))
        ok = np.abs(unwrapped - off - delta) < 0.5 * np.pi
        rates[label] = 100 * float(np.mean(ok[valid]))
        print("  %-34s %11.1f %%  (評価画素 %d)" % (label, rates[label], valid.sum()))
    print()
    # ★所見を固定する。
    #   (1) 減偏光は無い(Stokes の大きさが厳密に 1)。変調が落ちるのは光量ではなく
    #       **位相の感度**のほうだ、という 5 節の主張の根拠。
    assert abs(float(modulation[IN_DISC].min()) - 1.0) < 1e-9 \
        and abs(float(modulation[IN_DISC].max()) - 1.0) < 1e-9, \
        (float(modulation[IN_DISC].min()), float(modulation[IN_DISC].max()))
    #   (2) ★★実測は「マスクを渡すと直る」という素朴な期待の**逆**を言っている:
    #       低変調の画素まで外すと一致率が 90 % を割る。低変調の画素を抜くと領域が
    #       分断され、skimage の unwrap が島ごとに別の 2π オフセットを選ぶため。
    #       「どちらもマスクで外せる」は**予報としては正しいが、処方としては誤り**。
    assert rates["そのまま(マスク無し)"] > 90.0, rates
    assert rates["標本化不足 + 低変調を外す"] < 90.0, rates
    figs.save_grid("unwrap",
                   [np.where(IN_DISC, wrapped, np.nan),
                    np.where(IN_DISC, np.hypot(s1, s2), np.nan),
                    np.where(IN_DISC, px_per_fringe, np.nan),
                    np.where(IN_DISC, n_true, np.nan)],
                   ["巻いたままの δ [rad]", "変調度 |sinδ|(小さい所で壊れる)",
                    "1 縞あたりの画素数(2 未満で壊れる)", "縞次数 N(真値)"],
                   title="巻き戻しが壊れる場所は撮る前に分かる",
                   signed=[True, False, False, False],
                   caption="左下 2 枚が「壊れる予報」。予報は当たるが、外せば直るとは限らない。")
    print("  → ★壊れる場所は 2 つあり、**どちらも撮る前に分かる**:")
    print("     (1) 縞が細かすぎる(1 縞 2 画素未満)—— 標本化定理。荷重点の近く。")
    print("     (2) 変調が落ちる —— δ が 2π の整数倍に近い帯と、主応力差が")
    print("         ゼロになる等方点。**いちばん応力が小さい所**が含まれる。")
    print("  → ★★ところが実測は「予報した画素を外せば直る」の**逆**を言う:")
    print("     マスク無し %.1f %% / 標本化不足だけ外して %.1f %% / 低変調まで外すと %.1f %%。"
          % (rates["そのまま(マスク無し)"], rates["標本化不足を外す"],
             rates["標本化不足 + 低変調を外す"]))
    print("     外すほど領域が分断され、`unwrap_phase_2d` が島ごとに別の 2π を")
    print("     選ぶため。**予報としては正しいが、処方としては誤り** ——")
    print("     信頼できない画素は「捨てる」のでなく「重みを下げて繋いだまま解く」")
    print("     必要がある(重みつきアンラップ。いまの薄いラッパには口が無い)。")
    return rates


def section6_noise(dsig, theta, delta, m):
    print()
    print("=" * 78)
    print("6) 雑音と 8 bit 量子化")
    print("=" * 78)
    rng = np.random.default_rng(5)
    ang = np.rad2deg(theta)
    rows = {}
    print("  %10s %10s | %14s %12s"
          % ("雑音 σ", "量子化", "δ 誤差 rad", "σ1-σ2 誤差"))
    print("  " + "-" * 54)
    for sig, bits in [(0.0, 0), (0.002, 0), (0.01, 0), (0.0, 8), (0.002, 8)]:
        dark = pe.polariscope_intensity(delta, ang, "circular_dark")
        bright = pe.polariscope_intensity(delta, ang, "circular_bright")
        if sig > 0:
            dark = dark + rng.normal(0, sig, dark.shape)
            bright = bright + rng.normal(0, sig, bright.shape)
        if bits:
            q = 2 ** bits - 1
            dark = np.round(np.clip(dark, 0, 1) * q) / q
            bright = np.round(np.clip(bright, 0, 1) * q) / q
        d_hat = 2.0 * np.arctan2(np.sqrt(np.maximum(dark, 0)),
                                 np.sqrt(np.maximum(bright, 0)))
        e = np.abs(np.mod(d_hat - delta + np.pi, 2 * np.pi) - np.pi)
        rows[(sig, bits)] = (float(np.median(e[m])),
                             float(np.mean(np.abs(to_mpa(d_hat)[m] - dsig[m]))))
        print("  %10.3f %10s | %14.5f %12.5f"
              % (sig, "%d bit" % bits if bits else "なし",
                 rows[(sig, bits)][0], rows[(sig, bits)][1]))
    print()
    print("  → 8 bit 量子化だけで δ の誤差が %s。雑音より**先に量子化が効く**"
          % "雑音 0.002 と同程度")
    print("     ことがある(輝度 0〜1 を 256 段に切ると δ の刻みが有限になる)。")
    # ★所見を固定する。
    #   (1) 雑音も量子化も無ければ、明視野/暗視野の比から δ は**厳密に**戻る。
    assert rows[(0.0, 0)][0] < 1e-9, rows[(0.0, 0)]
    #   (2) ★8 bit 量子化「だけ」の誤差が、雑音 σ=0.002 だけの誤差と同オーダー
    #       (実測 0.00277 vs 0.00305)。カメラの bit 深さは雑音と同じ重さで効く。
    assert rows[(0.0, 8)][0] > 0.5 * rows[(0.002, 0)][0], (rows[(0.0, 8)], rows[(0.002, 0)])
    #   (3) 雑音は 5 倍にすると誤差も同じ桁で増える(比例の確認)。
    assert rows[(0.01, 0)][0] > 3.0 * rows[(0.002, 0)][0], (rows[(0.01, 0)], rows[(0.002, 0)])
    return rows


def section7_findings():
    print()
    print("=" * 78)
    print("7) 所見 —— fullseye に足りないもの")
    print("=" * 78)
    print("""
  (a) ✔**直した(2026-10-23)**: 光弾性の族が無かった。初版(2026-09-06)は
      応力場の閉形式も、画素ごとの位相子の 4x4 も、平面偏光の強度式も
      ここに手書きしていた。いまは `photoelastic.py` の op 12 本のうち 7 本を
      呼ぶだけで、手書きの式は残っていない。旧版の計算は
      `tests/test_poc_photoelasticity_ops.py` に独立な参照として残し、
      族の op との一致(主応力差・位相差・偏光像・各節の数値)を門にしている。

  (b) ★**書き直しで見つかった符号**: 初版は σ1 の向きを位相子の**進相軸**に
      渡していた。エポキシ(C > 0)では σ1 は**遅相軸**(op の規約)。
      暗視野・明視野・平面偏光の強度は (δ,θ) ↔ (-δ,θ+90°) で変わらないので
      画像では見えず、試料を出た Stokes の S1・S2 の符号と、円偏光
      ポラリスコープの検光子を 0°/90° 以外に回した像だけが変わる。
      この版は op の規約(進相軸 = σ1 + 90°)に合わせた。

  (c) ★★**位相アンラップに「信頼度の重み」の口が無い**。
      `unwrap_phase_2d` は skimage の実装で、5 節のとおり**等方点の近くで
      必ず壊れる**。壊れる場所は事前に分かる(変調度 = 明視野+暗視野の
      振幅が小さい所)が、★**その画素をマスクで外すと一致率はむしろ下がる**
      —— 領域が分断され、島ごとに別の 2π が選ばれるため。要るのは
      「捨てる口」ではなく**重みつきアンラップ**(信頼度の低い画素を
      繋いだまま従属させる)で、それが無い。干渉計・位相シフト法・InSAR
      すべてに効く。空間をたどらない道として、族には多波長で画素ごとに
      次数を決める `retardation_unwrap_multiwavelength` があるが、
      撮る波長を増やす別の測定なので、この PoC(1 波長)の問いには使っていない。

  (d) 応力・ひずみの単位を持つ量が族をまたいで散らばっている。
      `piv_strain_rate`(流体のひずみ速度)、`poc_dic_strain` が要求した
      Green-Lagrange、ここで要る主応力差 —— **同じ「応力/ひずみ」という
      語で 3 つ別のものを指している**。

  (e) 1 節 (a) は**族の op と optics の素子の鎖の厳密な照合**になっている
      (125 通りで最大差が機械精度)。どちらかが壊れればここで落ちる。
""")


def _v_txt(img, s, xy, anchor="lt", fs_=12):
    """文字の板。**小さな板(パネル 1 枚)にだけ**描く —— 全面に描くと遅い。"""
    import annotate as AN

    return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=fs_), dtype=np.float64)


def fig_load_video(npx=361, n_load=120, n_rot=90, n_hold=10, fps=15.0):
    """★動画: 荷重を 0 → P まで上げて縞が湧き出す様子(前半)と、P のまま平面偏光子の対を
    0 → 90 度回して等傾線(黒い帯)が動く様子(後半)。

    応力場・偏光像は本文と同じ族の op(:func:`fields` と ``polariscope_intensity``)。
    描画用に格子を ``npx`` 画素へ細かくしただけで、式は本文と同じ。乱数は使わない。
    応力は荷重に比例するので、荷重 p の場は P_N の場を p/P_N 倍して作る。
    図を出さない実行では呼ばれない。
    """
    if not figs.enabled():
        return None
    import annotate as AN
    import imgio

    f_full = fields(npx)
    disc = f_full["in_disc"]
    pmm = 2.0 * R_MM / (npx - 1)
    rim = np.abs(np.hypot(f_full["disc"]["x"], f_full["disc"]["y"]) * 1e3 - R_MM) < 0.6 * pmm
    dsig_full, theta, ang = f_full["dsig"], f_full["theta"], f_full["angle_deg"]
    vmax = float(np.percentile(dsig_full[disc], 99.0))
    c0 = (npx - 1) // 2                                      # 中心の画素
    n_c_full = float(f_full["order"][c0, c0])                # 荷重 P_N での中心の縞次数
    loads = np.linspace(0.0, P_N, n_load)
    i_centre = np.sin(np.pi * n_c_full * loads / P_N) ** 2

    S, GAP, TB = npx, 6, 34
    FW, FH = 3 * S + 2 * GAP, TB + S
    xs = [0, S + GAP, 2 * (S + GAP)]
    base = np.full((FH, FW, 3), 0.06)

    def title(f, k, s):
        strip = f[0:TB, xs[k]:xs[k] + S]
        f[0:TB, xs[k]:xs[k] + S] = _v_txt(strip, s, (4, TB // 2), anchor="lm", fs_=13)

    # 右のパネル(中心の明るさ vs 荷重)の軸は 1 度だけ描く
    plot = np.full((S, S, 3), 0.10)
    ax = AN.axes_transform((46, 40, S - 62, S - 96), (0.0, P_N), (0.0, 1.0))
    plot = np.asarray(AN.axes_frame(plot, ax), np.float64)
    plot = np.asarray(AN.ticks(plot, ax, xticks=[0, 100, 200, 300, 400, 500],
                               yticks=[0.0, 0.5, 1.0], font_size=10), np.float64)
    plot = _v_txt(plot, "荷重 P [N]", (S // 2 + 20, S - 4), anchor="cb", fs_=10)

    def disc_rgb(v):
        out = np.where(disc[..., None], v, 0.0)
        out[rim] = 0.45
        return out

    frames = []
    base1 = base.copy()
    title(base1, 0, "暗視野(円偏光)= 等色線")
    title(base1, 1, "主応力差 σ1-σ2(真値、0〜%.1f MPa)" % vmax)
    title(base1, 2, "中心の明るさ(0 = 暗線が中心を通過)")
    base1[TB:, xs[2]:xs[2] + S] = plot
    for k, p in enumerate(loads):
        f = base1.copy()
        s_ = p / P_N
        dark = pe.polariscope_intensity(f_full["delta"] * s_, ang, "circular_dark")
        a = disc_rgb(np.repeat(np.clip(dark, 0, 1)[..., None], 3, 2))
        n_c = n_c_full * s_
        a = _v_txt(a, "荷重 P = %3.0f N\n中心の縞次数 N = %.2f\n(閉形式 h(σ1-σ2)/fσ)" % (p, n_c), (5, 5), fs_=12)
        f[TB:, xs[0]:xs[0] + S] = a
        sig = np.asarray(imgio.apply_cmap(dsig_full * s_, "inferno", vmin=0.0, vmax=vmax), np.float64)
        b = _v_txt(disc_rgb(sig), "中心 %.3f MPa\n(8P/(πDh))" % (8 * p / (np.pi * 2 * R_MM * H_MM)),
                   (5, 5), fs_=12)
        f[TB:, xs[1]:xs[1] + S] = b
        pl = f[TB:, xs[2]:xs[2] + S]
        if k >= 1:
            pl = np.asarray(AN.plot_series(pl, ax, loads[:k + 1], i_centre[:k + 1],
                                           color=(0.95, 0.85, 0.35), width=2), np.float64)
        n_pass = int(np.floor(n_c + 1e-9))
        pl = _v_txt(pl, "暗線の通過 %d 回 → 縞次数は %d 以上" % (n_pass, n_pass), (8, 6), fs_=11)
        f[TB:, xs[2]:xs[2] + S] = pl
        frames.append(np.clip(f, 0.0, 1.0))
    last_plot = frames[-1][TB:, xs[2]:xs[2] + S].copy()
    frames += [frames[-1]] * n_hold

    # 後半: 荷重 P_N のまま、直交させた平面偏光子の対を回す
    base2 = base.copy()
    title(base2, 0, "平面偏光(直交)= 等色線 + 等傾線")
    title(base2, 1, "等傾角 θ(真値)と、いま黒くなる向き")
    title(base2, 2, "中心の明るさ(荷重 %.0f N で止めた)" % P_N)
    base2[TB:, xs[2]:xs[2] + S] = last_plot
    th_rgb = np.asarray(imgio.apply_cmap(np.mod(theta, np.pi) / np.pi, "twilight", vmin=0.0, vmax=1.0),
                        np.float64)
    for bdeg in np.linspace(0.0, 90.0, n_rot):
        f = base2.copy()
        plane = pe.polariscope_intensity(f_full["delta"], ang, "plane_dark", polarizer_deg=float(bdeg))
        a = disc_rgb(np.repeat(np.clip(plane, 0, 1)[..., None], 3, 2))
        a = _v_txt(a, "偏光子 %.0f 度 / 検光子 %.0f 度" % (bdeg, bdeg + 90.0), (5, 5), fs_=12)
        f[TB:, xs[0]:xs[0] + S] = a
        on = disc & (np.abs(np.sin(2.0 * (theta - np.deg2rad(bdeg)))) < 0.05)
        b = th_rgb.copy()
        b[on] = (1.0, 1.0, 1.0)
        b = _v_txt(disc_rgb(b), "白 = 主応力の向きが %.0f 度か %.0f 度\n(この点が左で黒い帯になる)"
                   % (bdeg, bdeg + 90.0), (5, 5), fs_=11)
        f[TB:, xs[1]:xs[1] + S] = b
        frames.append(np.clip(f, 0.0, 1.0))
    frames += [frames[-1]] * n_hold
    save_evaluation_video(
        "load_and_isoclinics", frames, capture_fps=fps, playback_fps=fps, hold_frames=0, gif_stride=3,
        display_scale=720 / frames[0].shape[1], interpolation="linear",
        caption="動画(%d コマ、円板 φ%.0f mm を %d 画素で描画、半径 0.9R の外は描かない): 前半は荷重を"
                            " 0 → %.0f N へ上げる。暗視野(円偏光)の暗線は縞次数が整数の等値線で、荷重点から湧き出して"
                            "中心へ寄る。中心の縞次数は荷重に比例して %.2f まで増え(閉形式 h(σ1-σ2)/fσ)、右のグラフの"
                            "中心の明るさ sin²(πN) が 0 に落ちるたびに暗線が中心を通過する(通過 %d 回)。後半は荷重 %.0f N の"
                            "まま、直交させた平面偏光子の対を 0 → 90 度回す。平面偏光の黒には 2 種類あり、回しても動かない"
                            "縞は等色線(暗視野と同じ)、回すと動く黒い帯が等傾線 = 主応力の向きが偏光子と平行か直交する点"
                            "で、中央の真値 θ の図で白く塗った点と重なる。"
                            "応力場と偏光像は光弾性の族の op(brazilian_disc_stress / principal_stress / "
                            "photoelastic_retardation / polariscope_intensity)。"
                            % (len(frames), 2 * R_MM, npx, P_N, n_c_full, int(np.floor(n_c_full)), P_N))
    return {"n_centre": n_c_full, "frames": len(frames)}


def run():
    """全節を回して、門が見る数値を dict で返す(テストが旧版の参照と突き合わせる)。"""
    n_centre = section1_check()
    dsig, theta, delta = _F["dsig"], _F["theta"], _F["delta"]
    naive, m, err0 = section2_zero_point(dsig, delta)
    e3, gain3 = section3_dark_field(dsig, theta, delta, naive, m)
    d_hat, _th, s1, s2, s3, abs_err, agree = section4_phase_shift(dsig, theta, delta, m)
    rates = section5_wrapping(dsig, delta, d_hat, s1, s2, s3)
    rows = section6_noise(dsig, theta, delta, m)
    return {"n_centre": n_centre, "err0": err0, "e3": e3, "gain3": gain3, "agree": agree,
            "abs_err": abs_err, "rates": rates, "rows": rows, "d_hat": d_hat}


def main():
    t0 = time.time()
    print("poc_photoelasticity — 光弾性で応力を測る(円板の直径圧縮)")
    print("(真値 = 閉形式の応力場。応力場から偏光像まで光弾性の族の op で組む)")
    print()
    out = run()
    section7_findings()
    # 動画は既存の図の**最後**に書く(番号が後ろの図のファイル名をずらさないように)。
    if figs.enabled():
        fig_load_video()
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("経過 %.1f 秒" % (time.time() - t0))
    print("\nPASS: 中心の縞次数 %.3f を閉形式どおりに合成し、位相シフトで解き戻すと"
          "主応力差の誤差は %.1e MPa(8 bit 量子化だけでも δ に %.5f rad 乗る)"
          % (out["n_centre"], out["abs_err"], out["rows"][(0.0, 8)][0]))


if __name__ == "__main__":
    main()
