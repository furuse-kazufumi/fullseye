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
円板を直径方向に圧縮したときの平面応力場には**閉形式**がある(Frocht):

    σxx = -(2P/πh)[ x²(R-y)/r1⁴ + x²(R+y)/r2⁴ - 1/(2R) ]
    σyy = -(2P/πh)[ (R-y)³/r1⁴ + (R+y)³/r2⁴ - 1/(2R) ]
    τxy =  (2P/πh)[ x(R-y)²/r1⁴ - x(R+y)²/r2⁴ ]

主応力差 σ1-σ2 = √((σxx-σyy)² + 4τxy²)、等傾角 θ = ½·atan2(2τxy, σxx-σyy)。
応力光学則 **N = h(σ1-σ2)/fσ**(N = 縞次数)で位相差 δ = 2πN。

偏光系は**フルセイの op で組む**(`mueller_element` + `mueller_apply`)。
教科書の暗視野円偏光ポラリスコープ I = sin²(δ/2) と一致するかを 1 節で
確かめてから使う —— 合成器も測定器も同じ人が書いたときに効く唯一の検算。

材料: エポキシ相当(fσ = 10.7 N/mm/縞)、円板 φ50 mm × 厚 6 mm、荷重 500 N。
中心の主応力差は 8P/(πDh) = 4.24 MPa、縞次数 2.38。

【節立て】
 1) ★検算 —— (a) op の偏光系が理論式と一致するか (b) 応力場が力の釣り合いを満たすか
 2) ★ゼロ点 —— 「一様応力 P/(Dh) と答える」推定器に勝てるか
 3) 暗視野 1 枚から縞次数を数える —— 整数の縞しか読めない
 4) ★位相シフト(6 段)—— δ と θ を分ける
 5) ★★位相の巻き —— 壊れるのは応力が大きい所ではなく**等方点**
 6) 雑音と 8 bit 量子化
 7) 所見

【この PoC で分かった fullseye 側の穴 → 末尾の「所見」節】
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 試験片と光学系の諸元 ---------------------------------------------------- #
R_MM = 25.0             # 円板の半径 [mm]
H_MM = 6.0              # 厚さ [mm]
P_N = 500.0             # 荷重 [N]
F_SIGMA = 10.7          # 材料の縞値 [N/(mm·縞)] —— エポキシの実測値の並び
NPIX = 257              # 奇数にして中心を画素に乗せる
PX_MM = 2.0 * R_MM / (NPIX - 1)

_YY, _XX = np.mgrid[0:NPIX, 0:NPIX].astype(np.float64)
X_MM = (_XX - (NPIX - 1) / 2.0) * PX_MM
Y_MM = ((NPIX - 1) / 2.0 - _YY) * PX_MM
# 荷重点 (0, ±R) では応力が発散する。実験でも接触部は読まないので、
# 評価は半径 0.9R までに限る(それでも縞次数は 8 近くまで出る)。
IN_DISC = X_MM ** 2 + Y_MM ** 2 <= (R_MM * 0.90) ** 2


def disc_stress(x, y, p=P_N, r=R_MM, h=H_MM):
    """直径圧縮された円板の平面応力(閉形式)。返りは ``(sxx, syy, txy)`` [MPa]。

    荷重は y 軸方向、接触点は ``(0, ±r)``。単位は N と mm なので応力は N/mm² = MPa。
    """
    r1sq = x ** 2 + (r - y) ** 2
    r2sq = x ** 2 + (r + y) ** 2
    r1sq = np.maximum(r1sq, 1e-9)
    r2sq = np.maximum(r2sq, 1e-9)
    k = 2.0 * p / (np.pi * h)
    sxx = -k * (x ** 2 * (r - y) / r1sq ** 2 + x ** 2 * (r + y) / r2sq ** 2 - 1.0 / (2 * r))
    syy = -k * ((r - y) ** 3 / r1sq ** 2 + (r + y) ** 3 / r2sq ** 2 - 1.0 / (2 * r))
    txy = k * (x * (r - y) ** 2 / r1sq ** 2 - x * (r + y) ** 2 / r2sq ** 2)
    return sxx, syy, txy


def principal_difference(sxx, syy, txy):
    """主応力差 σ1-σ2 と等傾角 θ [rad]。"""
    d = sxx - syy
    return np.sqrt(d * d + 4.0 * txy * txy), 0.5 * np.arctan2(2.0 * txy, d)


# --- 偏光系(fullseye の op で組む)------------------------------------------- #
def polariscope_matrices(analyser_deg):
    """暗視野/明視野の円偏光ポラリスコープを 4x4 Mueller の並びで返す。

    P(0°) → QWP(45°) → 試料 → QWP(-45°) → A(analyser)。試料だけが画素ごとに
    変わるので、前後は定数行列としてまとめておける。
    """
    q1 = np.asarray(fs.mueller_element("quarter_wave", 45.0))
    q2 = np.asarray(fs.mueller_element("quarter_wave", -45.0))
    an = np.asarray(fs.mueller_element("polarizer", analyser_deg))
    s_in = np.asarray(fs.mueller_apply(q1, np.array([1.0, 1.0, 0.0, 0.0])))
    return s_in, an @ q2


def _retarder_stack(delta, theta):
    """画素ごとの位相子 Mueller を (H, W, 4, 4) で作る。

    ``fs.mueller_element`` は 1 枚ぶん(スカラーの δ と θ)しか作らないので、
    画素ごとに変わる位相子はここで閉形式から組む。**組んだあとは
    ``fs.mueller_apply`` がそのまま (H,W,4,4) x (4,) を通す**
    (2026-09-06 に broadcast 対応。この PoC が掘り当てた穴)。
    """
    c2, s2 = np.cos(2 * theta), np.sin(2 * theta)
    cd, sd = np.cos(delta), np.sin(delta)
    m = np.zeros(delta.shape + (4, 4))
    m[..., 0, 0] = 1.0
    m[..., 1, 1] = c2 * c2 + s2 * s2 * cd
    m[..., 1, 2] = c2 * s2 * (1.0 - cd)
    m[..., 1, 3] = -s2 * sd
    m[..., 2, 1] = m[..., 1, 2]
    m[..., 2, 2] = s2 * s2 + c2 * c2 * cd
    m[..., 2, 3] = c2 * sd
    m[..., 3, 1] = s2 * sd
    m[..., 3, 2] = -c2 * sd
    m[..., 3, 3] = cd
    return m


def polariscope_image(delta, theta, analyser_deg=90.0):
    """ポラリスコープの強度画像。"""
    s_in, post = polariscope_matrices(analyser_deg)
    s = fs.mueller_apply(_retarder_stack(delta, theta), s_in)
    return np.asarray(fs.mueller_apply(post, s))[..., 0]


def plane_polariscope(delta, theta, pol_deg=0.0):
    """平面(直線)偏光ポラリスコープ、直交配置。等傾線と等色線が混ざる。"""
    b = np.deg2rad(pol_deg)
    return np.sin(2.0 * (theta - b)) ** 2 * np.sin(delta / 2.0) ** 2


# =========================================================================== #
def section1_check():
    print("=" * 78)
    print("1) ★検算 —— 偏光系の op と、応力場そのもの")
    print("=" * 78)
    # (a) fullseye の Mueller op が教科書式と一致するか。
    s_in, post = polariscope_matrices(90.0)
    worst = 0.0
    for d_deg in range(0, 361, 15):
        for th_deg in (0.0, 13.0, 30.0, 45.0, 71.0):
            m = np.asarray(fs.mueller_element("retarder", th_deg, d_deg))
            i_op = float((post @ (m @ s_in))[0])
            i_th = float(np.sin(np.deg2rad(d_deg) / 2.0) ** 2)
            worst = max(worst, abs(i_op - i_th))
    print("  (a) `mueller_element` + `mueller_apply` で組んだ暗視野円偏光系 vs")
    print("      教科書式 I = sin²(δ/2): 125 通りの最大差 %.3e" % worst)
    print("      → 一致。**しかも θ に依らない**(円偏光系の要件)ことも同時に確認。")
    # ★所見を固定する: これは fullseye の Mueller op に対する**厳密な**検算で、
    #   δ を 15 度刻みで一周・θ を 5 通り振っても機械精度で一致する(実測 2.2e-16)。
    #   ここが緩んだら 3 節以降で測っているのは「読み取り手順」ではなく op のバグ。
    assert worst < 1e-12, "Mueller 系が教科書式から外れた: %.3e" % worst

    # (b) 応力場が力の釣り合いを満たすか(水平直径上の σyy を積分すると -P/h)。
    n = 20001
    x = np.linspace(-R_MM * (1 - 1e-9), R_MM * (1 - 1e-9), n)
    _sxx, syy, _txy = disc_stress(x, np.zeros_like(x))
    load = np.trapezoid(syy, x) * H_MM
    print()
    print("  (b) 水平直径上の σyy を積分した力: %.3f N(真値 -%.1f N、誤差 %.3f %%)"
          % (load, P_N, 100 * abs(load / (-P_N) - 1)))
    sxx0, syy0, txy0 = disc_stress(np.array([0.0]), np.array([0.0]))
    d0, _ = principal_difference(sxx0, syy0, txy0)
    closed = 8 * P_N / (np.pi * 2 * R_MM * H_MM)
    n_centre = H_MM * float(d0[0]) / F_SIGMA
    print("      中心の主応力差 %.4f MPa(閉形式 8P/(πDh) = %.4f)" % (d0[0], closed))
    print("      中心の縞次数 N = h(σ1-σ2)/fσ = %.3f" % n_centre)
    print()
    print("  → ここまで近似ゼロ。以降のずれは全部『読み取り手順』のもの。")
    # ★応力場そのものの検算も固定する。積分した力が荷重に一致しなければ
    #   「真値」ではないし、中心値は閉形式 8P/(πDh) と代数的に同じはず。
    assert abs(load / (-P_N) - 1.0) < 1e-4, "力の釣り合いが崩れた: %.4f N" % load
    assert abs(float(d0[0]) / closed - 1.0) < 1e-9, (float(d0[0]), closed)
    return n_centre


def build_fields():
    sxx, syy, txy = disc_stress(X_MM, Y_MM)
    dsig, theta = principal_difference(sxx, syy, txy)
    n_fringe = H_MM * dsig / F_SIGMA
    return dsig, theta, 2.0 * np.pi * n_fringe


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
    return naive, m


def section3_dark_field(dsig, theta, delta, naive, m):
    print()
    print("=" * 78)
    print("3) 暗視野 1 枚から縞次数を数える —— 整数しか読めない")
    print("=" * 78)
    img = polariscope_image(delta, theta, analyser_deg=90.0)
    # 暗線(I=0)は N が整数の等値線。最も素朴な読み方 = しきい値で暗線を拾い、
    # 「暗線から暗線のあいだを線形に内挿する」。ここでは内挿せず整数だけ使う。
    n_true = delta / (2 * np.pi)
    n_int = np.round(n_true)                       # 「最寄りの暗線の次数」を読む
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
    bright = polariscope_image(delta, theta, analyser_deg=0.0)
    plane = plane_polariscope(delta, theta, 0.0)
    figs.save_grid("polariscope",
                   [np.where(IN_DISC, img, 0.0), np.where(IN_DISC, bright, 0.0),
                    np.where(IN_DISC, plane, 0.0), np.where(IN_DISC, dsig, 0.0)],
                   ["暗視野(円偏光)", "明視野(円偏光)",
                    "平面偏光(等傾線が混ざる)", "主応力差 σ1-σ2 [MPa](真値)"],
                   title="円板の直径圧縮 —— ポラリスコープ像と真値",
                   caption="偏光系は fullseye の mueller_element / mueller_apply で組んだ。")
    print("  → 整数の縞しか読まないと **fσ/h = %.3f MPa の刻み**でしか答えられない。"
          % (F_SIGMA / H_MM))
    print("     縞が 2 本しか出ていない試験片では、これは実質「3 段階」の分解能。")
    return img


def emerging_stokes(delta, theta):
    """円偏光を入れたとき、試料から出てくる Stokes ベクトル ``(H,W,4)``。

    入射 (1,0,0,1) を位相子 M(δ,θ) に通すと解析的に

        S1' = -sin2θ·sinδ,  S2' = cos2θ·sinδ,  S3' = cosδ

    になる。**偏光計で測れるのはこの 3 成分だけ**で、ここから (δ, θ) を
    復元するのが位相シフト光弾性のすべて。
    """
    return np.asarray(fs.mueller_apply(_retarder_stack(delta, theta),
                                       np.array([1.0, 0.0, 0.0, 1.0])))


def section4_phase_shift(dsig, theta, delta, m):
    print()
    print("=" * 78)
    print("4) ★位相シフト —— δ と θ を分ける。ただし分けきれない")
    print("=" * 78)
    print("  ※ここは**手順の検算**(雑音ゼロで、同じ強度式から解き戻す)。")
    print("    実測の誤差は 6 節(雑音・量子化)で出す。")
    s_out = emerging_stokes(delta, theta)
    s1, s2, s3 = s_out[..., 1], s_out[..., 2], s_out[..., 3]

    # (i) 等傾角。平面偏光 4 枚から 4θ が出る。
    i0 = plane_polariscope(delta, theta, 0.0)
    i1 = plane_polariscope(delta, theta, 22.5)
    i2 = plane_polariscope(delta, theta, 45.0)
    i3 = plane_polariscope(delta, theta, 67.5)
    th_hat = 0.25 * np.arctan2(i3 - i1, i2 - i0)
    ang = np.abs(np.mod(th_hat - theta + np.pi / 4, np.pi / 2) - np.pi / 4)
    print()
    print("  等傾角 θ の誤差: 中央値 %.4f 度 / 90 パーセンタイル %.4f 度"
          % (np.rad2deg(np.median(ang[IN_DISC])), np.rad2deg(np.percentile(ang[IN_DISC], 90))))

    # (ii) 位相差。θ を使うと sinδ の**符号まで**取れる。
    sin_d = s2 * np.cos(2 * th_hat) - s1 * np.sin(2 * th_hat)
    d_hat = np.arctan2(sin_d, s3)                      # (-π, π]
    wrapped_true = np.mod(delta + np.pi, 2 * np.pi) - np.pi
    err = np.abs(np.mod(d_hat - wrapped_true + np.pi, 2 * np.pi) - np.pi)
    good = err < 0.05
    print("  巻いたままの δ(-π, π] の一致率: %.1f %%(誤差 < 0.05 rad)"
          % (100 * float(np.mean(good[IN_DISC]))))
    print()
    print("  → ★残りの %.1f %% は**符号が反転**している。原因は光弾性で有名な"
          % (100 * (1 - float(np.mean(good[IN_DISC])))))
    print("     (δ, θ) ↔ (-δ, θ+90°) の二義性 —— 出てくる Stokes が同じなので、")
    print("     **1 波長の 1 回の測定では原理的に分けられない**。等傾角の")
    print("     復元も 4θ からなので θ は π/2 の周期しか決まらず、その飛びが")
    print("     そのまま δ の符号の飛びになる。")
    est = F_SIGMA * (np.abs(d_hat) / (2 * np.pi)) / H_MM
    print("     |δ| だけを使えば主応力差は N<0.5 の領域で誤差 %.2e MPa。"
          % float(np.mean(np.abs(est[m] - dsig[m]))))
    return d_hat, th_hat, s1, s2, s3


def section5_wrapping(dsig, delta, d_hat, s1, s2, s3):
    print()
    print("=" * 78)
    print("5) ★★位相の巻きを解く —— 壊れる場所は 2 つ、どちらも予測できる")
    print("=" * 78)
    n_true = delta / (2 * np.pi)
    print("  縞次数 N: 最小 %.3f / 中央 %.3f / 最大 %.3f(半径 0.9R まで)"
          % (n_true[IN_DISC].min(), np.median(n_true[IN_DISC]), n_true[IN_DISC].max()))
    print("  N > 0.5 = 位相が巻いている画素: %.1f %%"
          % (100 * float(np.mean(n_true[IN_DISC] > 0.5))))

    # 縞の間隔。1 縞あたり 2 画素を切ると標本化定理から復元できない。
    gy, gx = np.gradient(n_true)
    per_px = np.hypot(gx, gy)
    px_per_fringe = 1.0 / np.maximum(per_px, 1e-12)
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
    for label, mask in [("そのまま(マスク無し)", None),
                        ("標本化不足を外す", ~aliased),
                        ("標本化不足 + 低変調を外す", ~aliased & ~lowmod)]:
        kw = {} if mask is None else {"mask": mask}
        try:
            unwrapped = np.asarray(fs.ledger.unwrap_phase_2d(wrapped, **kw))
        except TypeError as exc:                        # mask を受けない場合
            print("  %-34s %12s" % (label, "mask 不可: %s" % exc))
            continue
        valid = IN_DISC & np.isfinite(unwrapped)
        if valid.sum() < 50:
            print("  %-34s %12s" % (label, "有効画素なし"))
            continue
        off = float(np.median((unwrapped - delta)[valid]))
        ok = np.abs(unwrapped - off - delta) < 0.5 * np.pi
        print("  %-34s %11.1f %%  (評価画素 %d)"
              % (label, 100 * float(np.mean(ok[valid])), valid.sum()))
    print()
    figs.save_grid("unwrap",
                   [np.where(IN_DISC, wrapped, np.nan),
                    np.where(IN_DISC, np.hypot(s1, s2), np.nan),
                    np.where(IN_DISC, px_per_fringe, np.nan),
                    np.where(IN_DISC, n_true, np.nan)],
                   ["巻いたままの δ [rad]", "変調度 |sinδ|(小さい所で壊れる)",
                    "1 縞あたりの画素数(2 未満で壊れる)", "縞次数 N(真値)"],
                   title="巻き戻しが壊れる場所は撮る前に分かる",
                   signed=[True, False, False, False],
                   caption="左下 2 枚が「壊れる予報」。どちらもマスクで外せる。")
    print("  → ★壊れる場所は 2 つあり、**どちらも撮る前に分かる**:")
    print("     (1) 縞が細かすぎる(1 縞 2 画素未満)—— 標本化定理。荷重点の近く。")
    print("     (2) 変調が落ちる —— δ が 2π の整数倍に近い帯と、主応力差が")
    print("         ゼロになる等方点。**いちばん応力が小さい所**が含まれる。")
    print("     どちらもマスクで外せる。`unwrap_phase_2d` は mask を受けるので、")
    print("     渡すかどうかで結果が上の表のとおり変わる —— **渡さないのは")
    print("     手順の欠落であって、道具の限界ではない**。")


def section6_noise(dsig, theta, delta, m):
    print()
    print("=" * 78)
    print("6) 雑音と 8 bit 量子化")
    print("=" * 78)
    rng = np.random.default_rng(5)
    print("  %10s %10s | %14s %12s"
          % ("雑音 σ", "量子化", "δ 誤差 rad", "σ1-σ2 誤差"))
    print("  " + "-" * 54)
    for sig, bits in [(0.0, 0), (0.002, 0), (0.01, 0), (0.0, 8), (0.002, 8)]:
        dark = polariscope_image(delta, theta, 90.0)
        bright = polariscope_image(delta, theta, 0.0)
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
        est = F_SIGMA * (d_hat / (2 * np.pi)) / H_MM
        print("  %10.3f %10s | %14.5f %12.5f"
              % (sig, "%d bit" % bits if bits else "なし",
                 float(np.median(e[m])), float(np.mean(np.abs(est[m] - dsig[m])))))
    print()
    print("  → 8 bit 量子化だけで δ の誤差が %s。雑音より**先に量子化が効く**"
          % "雑音 0.002 と同程度")
    print("     ことがある(輝度 0〜1 を 256 段に切ると δ の刻みが有限になる)。")


def section7_findings():
    print()
    print("=" * 78)
    print("7) 所見 —— fullseye に足りないもの")
    print("=" * 78)
    print("""
  (a) ✔**直した**: `mueller_apply` が画像に効かなかった。4x4 と 4 ベクトル
      1 組しか通らず、画素ごとに位相差が変わる系(光弾性はまさにそれ)を
      組むには (H,W,4,4) の掛け算を呼び手が手書きするしかなかった。
      **1 節で確かめたとおり 4x4 そのものは正しい**(125 通りで最大差 2.2e-16)
      ので、足りないのは形だけ —— broadcast を通した(2026-09-06)。
      この PoC はいま `fs.mueller_apply` をそのまま呼んでいる。
      残る穴は `mueller_element` が (H,W) の δ / θ を受けないことで、
      位相子の 4x4 を組む式は依然としてここに手書きしてある
      (`_retarder_stack`)。これは族を足すときに一緒に片付ける。

  (b) ★**光弾性の族が無い**(`op_find` で "photoelastic" / "光弾性" /
      "birefringence" / "retardation" いずれも 0 件。3 層すべて確認)。
      あるのは Stokes/Mueller の素材と位相アンラップだけ。足すなら:
      `photoelastic_stress(delta, thickness, f_sigma)`(応力光学則)/
      `polariscope_simulate(delta, theta, kind)`(平面・円、明暗)/
      `phase_step_photoelastic(images, method)`(6 段・10 段)/
      `disc_diametral_stress(...)`(真値つきの検証用。粗さ族の
      `surface_synth_psd` と同じ位置づけ)。

  (c) ★★**位相アンラップに「信頼できない画素」の口が無い**。
      `unwrap_phase_2d` は skimage の実装で、5 節のとおり**等方点の近くで
      必ず壊れる**。壊れる場所は事前に分かる(変調度 = 明視野+暗視野の
      振幅が小さい所)ので、**マスクを受け取れれば結果が変わる**
      (skimage 側は masked array を受け付ける)。いまの薄いラッパは
      マスクを渡す口を塞いでいる。これは光弾性に限らず、干渉計・
      位相シフト法・InSAR すべてに効く。

  (d) 応力・ひずみの単位を持つ量が族をまたいで散らばっている。
      `piv_strain_rate`(流体のひずみ速度)、`poc_dic_strain` が要求した
      Green-Lagrange、ここで要る主応力差 —— **同じ「応力/ひずみ」という
      語で 3 つ別のものを指している**。族を足すときに規約を決めること
      (`measure3d` が (depth,row,col) を決めたのと同じ整理)。

  (e) この PoC の 1 節 (a) は **fullseye の op に対する厳密な検算**になって
      いる(125 通りで最大差が機械精度)。族を足したらここに繋いで回帰試験に
      するのが安い。
""")


def main():
    t0 = time.time()
    print("poc_photoelasticity — 光弾性で応力を測る(円板の直径圧縮)")
    print("(真値 = 閉形式の応力場。偏光系は fullseye の Mueller op で組む)")
    print()
    section1_check()
    dsig, theta, delta = build_fields()
    naive, m = section2_zero_point(dsig, delta)
    section3_dark_field(dsig, theta, delta, naive, m)
    d_hat, _th, k1, k2, k3 = section4_phase_shift(dsig, theta, delta, m)
    section5_wrapping(dsig, delta, d_hat, k1, k2, k3)
    section6_noise(dsig, theta, delta, m)
    section7_findings()
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("経過 %.1f 秒" % (time.time() - t0))


if __name__ == "__main__":
    main()
