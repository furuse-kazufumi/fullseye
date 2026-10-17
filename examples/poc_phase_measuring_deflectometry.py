# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 写真では見えない µm の凹みを、画面に映した縞の鏡像で見つける —— 位相計測デフレクトメトリ(PMD)

    py -3.11 examples/poc_phase_measuring_deflectometry.py

【問い】車の塗装パネルやスマホのカバーガラスの「深さ数 µm、直径数 mm の凹み」は、照明を当てて撮った
写真ではまず見えない。光沢面は鏡なので、写真に写るのは照明そのものだからだ。そこで面の前に画面を置き、
位相シフト縞を表示して、その**鏡像**を撮る。面が 1e-3 rad 傾くと、反射は 2e-3 rad 曲がり、30 cm 先の
画面では 0.6 mm ずれる —— 傾きを、画面までの距離をてこにして測る。それが位相計測デフレクトメトリ
(Knauer ら 2004)。新 op 6 本(`deflectometry`、`opsspecular` の `deflectometry`)で、次を実測します。

  0. **撮る前に感度を印字する**(`deflectometry_sensitivity`): 画面の画素ピッチ / (2d) と、位相シフトの
     雑音から出る傾きの雑音 σ_u / (2d)、高さと傾きの不定性の係数 sin θ / d。
  1. **写真 vs 縞の鏡像**: 深さ 3 µm と 1 µm の凹み・うねり 0.8 µm・研磨ムラ 0.12 µm を仕込んだ塗装パネル。
     ソフトボックスの写真では凹みの信号が 8 bit の 1 段にも届かないのに、縞の鏡像 → 位相 → 勾配 → 曲率では
     はっきり見える。勾配を Frankot–Chellappa で積分して凹みの深さを真値と突き合わせる。
  2. **閉形式の感度 vs 実測**: 画素の位相雑音・面の傾きの雑音を、閉形式と比べる。
  3. **壊れるところ** —— どれも数字と図で:
     (a) 高さと傾きの不定性: 部品を 0.3 mm 浮かせて置くと、平らな板が傾いて曲がって見える(凹みは変わらない)。
         画面の距離を 2 % 間違えると凹みの深さが 2 % 狂う。
     (b) ざらつき: 拡散成分の割合を上げると縞の振幅が (1 − k_d) 倍に落ち、雑音が 1 / (1 − k_d) 倍に増え、
         最後は粗い縞の次数が飛んで崩れる(GIF)。
     (c) ガラスの裏面反射: 表と裏の 2 つの縞が重なり、位相が asin(R_裏 / R_表) まで引っぱられる。
     (d) ピント: 面に合わせると画面の縞がぼけて振幅が落ち、画面に合わせると凹みがぼけて浅く見える。
  4. **実データ(CC0)**: 鏡面に磨いた 300 mm 角の鋼板を裏からハンマーで叩き、板に映った十字格子を 75 kHz で撮った
     公開データ(Kaufmann・Olufsen・Fagerholt、DataverseNO doi:10.18710/TKS7SI)。格子の位相を 2 つの実装
     (窓つき DFT の格子法 / 標本化モアレ)で読んで突き合わせ、時間方向につないで傾きにし、仮想場の方法(VFM)で
     板が受けた力を出して、**ハンマーの先の力の記録(外部の真値)**と比べる。窓はハンマーを見ずに、荷重の無い
     対照の窓の「見かけの力」が最小になるものを選ぶ。データの著者の公開コード recolo を第 2 の実装として並べる。
     格子の変調度の低い窓・積分できない傾きの場・時間方向につなげない間引きは、値を返さず拒否する。

【真値】仕込んだ面の高さは解析式で、勾配も解析的に既知(順方向の描画にもその解析値を渡す)。深さの真値は
同じ物差し(中心と環の差)を真の高さに当てた値。【学習】0。【較正】0(装置の幾何は既知とする)。

★正直に書いておくこと:
  * 合成です。カメラはピンホール + 薄レンズのぼけ、画面は平らで輝度は角度に依らない。画面の画素の格子と
    液晶の階調の非線形(Wu ら 2015 の主な誤差源)は入れていません。装置の幾何(距離・角度)は既知としていて、
    実機ではこの較正が精度の大半を決めます(3(a) の 2 % はその感度)。
  * 拡散成分は「画面の平均輝度を一様に足す」近似、裏面は平らで表と平行です。
  * 積分(Frankot–Chellappa)は周期境界なので、視野の縁のうねりは歪みます。深さは局所の物差しで測ります。

  * 4 節の実データ: 時刻の対応(image_0150 = ハンマーの 0 秒)はデータの著者の公開コードに従った。力の符号
    (板を押す向きを +)は約束で、データから決まらない 1 bit。合否の幅(峰 10 %、力積 12 %、3 駒)は、recolo の
    結果とこの解析の結果を見たあとで決めた —— 盲検の幅ではない。原本(110 MB)は repo の外で、CI は記録を読む。

出典: Knauer, Kaminski & Häusler, Proc. SPIE 5457, 366 (2004) / Wu ら, Opt. Eng. 54(6), 064103 (2015) /
Frankot & Chellappa, IEEE PAMI 10(4), 439 (1988) / Wang, Cossairt & Willomitzer, Optica 12 (2025) /
Kaufmann, Olufsen, Fagerholt & Aune, Int. J. Impact Eng. 171, 104369 (2023, CC BY 4.0) / Grédiac, Sur & Blaysat,
Strain 52, 205 (2016) / Ri, Fujigaki & Morimoto, Exp. Mech. 50, 501 (2010) / Olufsen ら, JOSS 6(67), 3869 (2021)。

走らせ方: ``py -3.11 examples/poc_phase_measuring_deflectometry.py``(図は ``FULLSEYE_FIGURE_DIR`` か
既定の ``out/figures/<PoC 名>/``)。4 節を原本から解析し直すなら、DataverseNO doi:10.18710/TKS7SI の画像と
ハンマーの記録を落としたディレクトリを ``FULLSEYE_PMD_HAMMER_DATA`` に入れる(数分。無ければ記録を読む)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import annotate as AN  # noqa: E402
import examplefig as figs  # noqa: E402
import fringe  # noqa: E402
import fullseye as fs  # noqa: E402  (台帳の公開経路 fs.ledger を使う)
import glassmirror  # noqa: E402
import photometric  # noqa: E402

CHECKS = []

N = 320                    # 面の格子とカメラの画素(一辺)。視野 40 mm → 0.125 mm / 画素
PERIOD = 10.0              # 細かい縞の周期 [mm](画面上)
COARSE = 160.0             # 次数を決める粗い縞の周期 [mm](見える画面の範囲より長い)
NOISE = 0.004              # 画素の雑音([0, 1] の単位、8 bit の約 1 段)
BITS = 8
SIGMA_PX = 1.0             # 曲率の前に傾きを均すガウスの σ [画素]

# 仕込む欠陥(塗装パネル): (中心 x, 中心 y [mm], 深さ [mm], σ [mm])
DIMPLE_A = (-8.0, -5.0, 3.0e-3, 1.2)       # 深さ 3 µm、直径(±2σ)約 5 mm
DIMPLE_B = (9.0, 7.0, 1.0e-3, 1.0)         # 深さ 1 µm、直径約 4 mm
WAVE = (0.8e-3, 12.0)                      # うねり: 振幅 0.8 µm、波長 12 mm(斜め)
POLISH = (6.0, -11.0, 0.12e-3, 0.9)        # 研磨ムラ: 中心、振幅 0.12 µm、波長 0.9 mm(楕円の斑)


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))


# --------------------------------------------------------------------------- #
# 試料(解析的な高さと勾配)                                                    #
# --------------------------------------------------------------------------- #
def surface(XX, YY, parts=("A", "B", "wave", "polish")):
    """塗装パネルの高さ [mm] と解析的な勾配 (∂h/∂x, ∂h/∂y)。"""
    h = np.zeros_like(XX)
    p = np.zeros_like(XX)
    q = np.zeros_like(XX)
    for key, (x0, y0, dep, s) in (("A", DIMPLE_A), ("B", DIMPLE_B)):
        if key not in parts:
            continue
        g = np.exp(-((XX - x0) ** 2 + (YY - y0) ** 2) / (2 * s * s))
        h += -dep * g
        p += dep * (XX - x0) / s ** 2 * g
        q += dep * (YY - y0) / s ** 2 * g
    if "wave" in parts:
        amp, lam = WAVE
        k = 2 * np.pi / lam
        ph = k * (XX * 0.8 + YY * 0.6)
        h += amp * np.sin(ph)
        p += amp * k * 0.8 * np.cos(ph)
        q += amp * k * 0.6 * np.cos(ph)
    if "polish" in parts:
        x0, y0, amp, lam = POLISH
        k = 2 * np.pi / lam
        env = np.exp(-((XX - x0) ** 2 / (2 * 4.0 ** 2) + (YY - y0) ** 2 / (2 * 2.0 ** 2)))
        ex = -(XX - x0) / 4.0 ** 2 * env
        ey = -(YY - y0) / 2.0 ** 2 * env
        c = np.cos(k * (XX - x0) * 0.3 + k * (YY - y0) * 0.95)
        sn = np.sin(k * (XX - x0) * 0.3 + k * (YY - y0) * 0.95)
        h += amp * env * c
        p += amp * (ex * c - env * sn * k * 0.3)
        q += amp * (ey * c - env * sn * k * 0.95)
    return h, p, q


def measure_phase(h, p, q, rig, **kw):
    """縞(細かい + 粗い、x と y、各 4 枚)を撮って、絶対位相 2 枚と変調度と細かい縞の巻き込み位相を返す。"""
    out = {}
    for d in ("x", "y"):
        fine = fs.ledger.deflectometry_render(h, rig, PERIOD, 4, d, slope_x=p, slope_y=q, **kw)
        coarse = fs.ledger.deflectometry_render(h, rig, COARSE, 4, d, slope_x=p, slope_y=q,
                                                **dict(kw, seed=kw.get("seed", 0) + 101))
        w = fringe.wrapped_phase(fine)
        c = fringe.wrapped_phase(coarse) * (COARSE / PERIOD)
        out[d] = fringe.absolute_phase(w, c)
        out["w" + d] = w
        out["mod" + d] = fringe.modulation(fine)
        out["img" + d] = fine
    return out


def decode(h, p, q, rig, z_ref=0.0, decode_rig=None, **kw):
    ph = measure_phase(h, p, q, rig, **kw)
    n = fs.ledger.deflectometry_phase_to_slope(ph["x"], ph["y"], decode_rig or rig, PERIOD, z_ref=z_ref)
    return n, ph


def integrate(n, sp):
    """法線マップ → 高さ [mm]。既存の `sfp_height`(Frankot–Chellappa を鏡像拡張した領域で解く)を使う。

    ★周期境界のままの `photometric.integrate_normals` は傾きの平均(直流)を表せず、一様な傾きを捨てる ——
    「部品を浮かせると傾いて見える」が高さに出なかった。鏡像拡張なら傾いた平面がそのまま戻る。"""
    return fs.ledger.sfp_height(np.where(np.isfinite(n), n, [0.0, 0.0, 1.0])) * sp


def depth(z, XX, YY, dimple):
    """局所の物差し: 半径 3σ〜4σ の環に 2 次の面を当て、中心(半径 0.25σ 以内)へ外挿した値 − 中心の平均。

    ★環の平均をそのまま使うと、面全体の曲がり(画面の距離の誤差が作る見かけの椀、うねり)が r²/2R だけ
    深さに混ざる —— 画面の距離を 2 % 間違えたとき、深さが「2 % 浅く」でなく 7.5 % 深く出た(実測)。
    外観検査の形状除去と同じく、局所の 2 次形状を外してから測る。真値にも同じ物差しを当てる。"""
    x0, y0, _, s = dimple
    dx, dy = XX - x0, YY - y0
    r2 = dx ** 2 + dy ** 2
    ring = (r2 > (3 * s) ** 2) & (r2 < (4 * s) ** 2) & np.isfinite(z)
    core = (r2 < (0.25 * s) ** 2) & np.isfinite(z)
    basis = lambda m: np.stack([np.ones(m.sum()), dx[m], dy[m], dx[m] ** 2, dx[m] * dy[m], dy[m] ** 2], axis=1)
    coef = np.linalg.lstsq(basis(ring), z[ring], rcond=None)[0]
    return float(np.mean(basis(core) @ coef - z[core]))


def peak_snr(k, XX, YY, dimple, noise_mask):
    """曲率マップの凹みの中心の値 / 平らな場所の曲率の標準偏差。"""
    x0, y0, _, s = dimple
    core = (XX - x0) ** 2 + (YY - y0) ** 2 < (0.25 * s) ** 2
    return float(np.nanmean(k[core]) / np.nanstd(k[noise_mask]))


def main():
    t0 = time.time()
    c0 = time.process_time()
    rig = fs.ledger.deflectometry_rig()          # θ 20°、カメラ 400 mm、画面 300 mm、視野 40 mm、開口 4 mm
    X = (np.arange(N) - (N - 1) / 2.0) * rig["field_mm"] / (N - 1)
    XX, YY = np.meshgrid(X, X)
    sp = float(X[1] - X[0])
    d = rig["screen_distance_mm"]
    th = math.radians(rig["incidence_deg"])
    print("装置: 入射 %.0f°、カメラまで %.0f mm、画面まで %.0f mm、視野 %.0f mm(%d 画素、%.3f mm / 画素)"
          % (rig["incidence_deg"], rig["camera_distance_mm"], d, rig["field_mm"], N, sp))

    # ---- 0. 撮る前の感度 -------------------------------------------------------- #
    print("\n[0] 撮る前に感度を印字する(閉形式)")
    sens = fs.ledger.deflectometry_sensitivity(rig, PERIOD, 4, NOISE, bits=BITS)
    print("  画面の画素ピッチ %.2f mm / (2d) = %.2e rad(縞を使わず画素を数えた場合の傾きの刻み)"
          % (rig["screen_pixel_mm"], sens["slope_pixel_bound"]))
    print("  位相の雑音 √(2/N)·σ/b = %.2e rad → 画面の座標 %.1f µm → 傾きの雑音 x %.2e / y %.2e rad"
          % (sens["phase_noise_rad"], 1000 * sens["screen_noise_mm"], sens["slope_noise_x"], sens["slope_noise_y"]))
    print("  高さと傾きの不定性: 面が 1 mm ずれると傾きが %.2e rad 狂う(sin θ / d)" % sens["height_slope_coupling"])
    print("  ピント: 面に合わせると画面側の錯乱円 %.1f mm(縞の振幅 × %.2f)、画面に合わせると面側 %.1f mm"
          % (sens["blur_screen_focus_surface_mm"], sens["contrast_focus_surface"],
             sens["blur_surface_focus_screen_mm"]))
    a_dep, a_s = DIMPLE_A[2], DIMPLE_A[3]
    slope_a = a_dep / a_s * math.exp(-0.5)
    print("  凹み A(深さ %.0f µm、σ %.1f mm)の最大傾き %.2e rad = 画素の刻みの %.1f 倍、傾きの雑音の %.0f 倍"
          % (1000 * a_dep, a_s, slope_a, slope_a / sens["slope_pixel_bound"], slope_a / sens["slope_noise_x"]))

    screen = fs.ledger.deflectometry_screen_pattern(rig, PERIOD, 4, "x")
    sw = rig["screen_size_mm"][0]
    nu = int(round(sw / rig["screen_pixel_mm"]))
    step = int(math.ceil(max(nu, round(rig["screen_size_mm"][1] / rig["screen_pixel_mm"])) / 1024))
    u_mid = (np.arange(0, nu, step) + 0.5) * rig["screen_pixel_mm"] - sw / 2.0    # 間引いた画素の中心
    gap_screen = float(np.abs(np.angle(np.exp(1j * (fringe.wrapped_phase(screen)[0] - 2 * np.pi * u_mid / PERIOD)))).max())
    check(gap_screen < 1e-9, "画面に出す縞(%d × %d 画素の 4 枚)を復号すると、画面の座標 2πu/周期 がそのまま戻る"
          % (screen[0].shape[1], screen[0].shape[0]), "最大の差 %.1e rad" % gap_screen)
    flat0 = np.zeros((N, N))
    w0 = fringe.wrapped_phase(fs.ledger.deflectometry_render(flat0, rig, PERIOD, 4, "x"))
    print("  画面 %.0f × %.0f mm(画素 %.2f mm)、縞の周期 %.0f mm。平らな鏡の視野には縞が %.1f 本映る"
          % (sw, rig["screen_size_mm"][1], rig["screen_pixel_mm"], PERIOD,
             float(np.ptp(np.unwrap(w0[N // 2]))) / (2 * np.pi)))

    # ---- 1. 写真 vs 縞の鏡像 ---------------------------------------------------- #
    print("\n[1] 写真では見えない凹みを、縞の鏡像で見る")
    h, p, q = surface(XX, YY)
    flat = np.zeros_like(h)
    photo = fs.ledger.deflectometry_render(h, rig, kind="softbox", slope_x=p, slope_y=q,
                                           noise_sigma=NOISE, bits=BITS, seed=7)[0]
    photo_clean = fs.ledger.deflectometry_render(h, rig, kind="softbox", slope_x=p, slope_y=q)[0]
    photo_flat = fs.ledger.deflectometry_render(flat, rig, kind="softbox")[0]
    sig_photo = float(np.abs(photo_clean - photo_flat).max())
    lsb = 1.0 / (2 ** BITS - 1)
    print("  ソフトボックスの写真: 欠陥が変える明るさは最大 %.5f(8 bit の 1 段 %.5f の %.2f 倍、雑音 σ %.3f)"
          % (sig_photo, lsb, sig_photo / lsb, NOISE))
    check(sig_photo < lsb, "写真(ソフトボックスの映り込み)では、凹みの信号が 8 bit の 1 段にも届かない",
          "最大 %.5f < %.5f" % (sig_photo, lsb))
    uni = fs.ledger.deflectometry_render(h, rig, kind="uniform", slope_x=p, slope_y=q)[0]
    check(float(np.ptp(uni)) < 1e-12, "一様な白い画面の映り込みでは、欠陥の信号は 0(鏡は照明しか写さない、丸めの桁)",
          "ptp %.1e" % float(np.ptp(uni)))

    n_meas, ph = decode(h, p, q, rig, noise_sigma=NOISE, bits=BITS, seed=1)
    pm, qm = photometric.normals_to_gradients(n_meas)
    ex, ey = pm - p, qm - q
    n_clean, ph_clean = decode(h, p, q, rig)
    pc, qc = photometric.normals_to_gradients(n_clean)
    pol = ((XX - POLISH[0]) / 9.0) ** 2 + ((YY - POLISH[1]) / 5.0) ** 2 <= 1.0
    e_round = np.maximum(np.abs(pc - p), np.abs(qc - q))
    disc = float(e_round[~pol].max())
    disc_pol = float(e_round[pol].max())
    slope_pol = float(np.hypot(p, q)[pol].max())
    print("  雑音なしの往復(描画 → 位相 → 傾き)の誤差: 研磨ムラの外で最大 %.2e rad(凹み A の最大の傾きの %.1f %%)、"
          "研磨ムラの中で %.2e rad(その傾き %.2e の %.0f %%)"
          % (disc, 100 * disc / slope_a, disc_pol, slope_pol, 100 * disc_pol / slope_pol))
    print("  ★研磨ムラの波長 0.9 mm は格子 7.2 画素ぶん。双線形の読み直しの誤差は (格子 × 波数)² / 8 ≈ 10 % の桁で、"
          "凹みのように滑らかな形では小さい(格子を細かくすると 2 乗で減る: tests/test_deflectometry.py)")
    check(disc < 0.03 * slope_a, "雑音なしの往復で、滑らかな形(凹み・うねり)の傾きが解析的な真値に合う(格子の離散化だけ)",
          "最大 %.2e rad" % disc)
    k_map = fs.ledger.slope_to_curvature(n_meas, sp, "mean", SIGMA_PX)
    k_true = fs.ledger.slope_to_curvature(
        np.dstack([-p, -q, np.ones_like(p)]) / np.sqrt(1 + p * p + q * q)[..., None], sp, "mean", SIGMA_PX)
    far = np.ones_like(h, bool)
    for dm in (DIMPLE_A, DIMPLE_B):
        far &= (XX - dm[0]) ** 2 + (YY - dm[1]) ** 2 > (4 * dm[3]) ** 2
    far &= ((XX - POLISH[0]) / 9.0) ** 2 + ((YY - POLISH[1]) / 5.0) ** 2 > 1.0
    edge = 8
    far[:edge] = far[-edge:] = False
    far[:, :edge] = far[:, -edge:] = False
    k_noise = k_map - k_true
    snr_a = float(np.nanmean(k_map[(XX - DIMPLE_A[0]) ** 2 + (YY - DIMPLE_A[1]) ** 2 < (0.25 * DIMPLE_A[3]) ** 2])
                  / np.nanstd(k_noise[far]))
    snr_b = float(np.nanmean(k_map[(XX - DIMPLE_B[0]) ** 2 + (YY - DIMPLE_B[1]) ** 2 < (0.25 * DIMPLE_B[3]) ** 2])
                  / np.nanstd(k_noise[far]))
    snr_photo = sig_photo / NOISE
    core_a = (XX - DIMPLE_A[0]) ** 2 + (YY - DIMPLE_A[1]) ** 2 < (0.25 * DIMPLE_A[3]) ** 2
    print("  曲率マップ: 凹み A の中心 %.2e /mm(同じ均しをかけた真値 %.2e、均す前の閉形式 D/σ² %.2e)、"
          "雑音 σ %.2e /mm → SNR A %.0f、B %.0f(写真の SNR %.2f)"
          % (np.nanmean(k_map[core_a]), np.nanmean(k_true[core_a]), DIMPLE_A[2] / DIMPLE_A[3] ** 2,
             np.nanstd(k_noise[far]), snr_a, snr_b, snr_photo))
    check(snr_a > 30 and snr_b > 8 and snr_photo < 0.25,
          "曲率マップでは深さ 3 µm も 1 µm も雑音の何倍も上に立つ(写真では雑音の 1/4 未満)",
          "SNR A %.0f / B %.0f / 写真 %.3f" % (snr_a, snr_b, snr_photo))
    z = integrate(n_meas, sp)
    dep_a, dep_a_true = depth(z, XX, YY, DIMPLE_A), depth(h, XX, YY, DIMPLE_A)
    dep_b, dep_b_true = depth(z, XX, YY, DIMPLE_B), depth(h, XX, YY, DIMPLE_B)
    print("  積分した高さの凹みの深さ: A %.3f µm(真値 %.3f)、B %.3f µm(真値 %.3f)"
          % (1000 * dep_a, 1000 * dep_a_true, 1000 * dep_b, 1000 * dep_b_true))
    check(abs(dep_a / dep_a_true - 1) < 0.02 and abs(dep_b / dep_b_true - 1) < 0.03,
          "傾きを積分した凹みの深さが真値に合う(A は 2 %、B は 3 % 以内)",
          "A %+.1f %% / B %+.1f %%" % (100 * (dep_a / dep_a_true - 1), 100 * (dep_b / dep_b_true - 1)))
    row = int(np.argmin(np.abs(X - DIMPLE_A[1])))
    zt = h[row] - h[row].mean()
    zr = z[row] - z[row].mean()
    mid = np.abs(X - DIMPLE_A[0]) < 4 * DIMPLE_A[3]
    prof_rms = float(np.sqrt(np.mean(((zr - zr[mid].mean()) - (zt - zt[mid].mean()))[mid] ** 2)))
    check(prof_rms < 0.1e-3, "凹み A を通る断面が真値と重なる(凹みの ±4σ、RMS)", "%.3f µm" % (1000 * prof_rms))

    # ---- 2. 閉形式の感度 vs 実測 ------------------------------------------------ #
    print("\n[2] 閉形式の感度と実測")
    dphi = np.angle(np.exp(1j * (ph["wx"] - ph_clean["wx"])))
    sphi = float(np.std(dphi[edge:-edge, edge:-edge]))
    r_phi = sphi / sens["phase_noise_rad"]
    check(0.9 < r_phi < 1.1, "カメラの画素の位相雑音 = √(2/N)·σ/b(8 bit の量子化を 2 乗和で)",
          "実測 %.2e / 閉形式 %.2e = %.2f" % (sphi, sens["phase_noise_rad"], r_phi))
    ex_n, ey_n = pm - pc, qm - qc
    sx_m = float(np.std(ex_n[edge:-edge, edge:-edge]))
    sy_m = float(np.std(ey_n[edge:-edge, edge:-edge]))
    rx, ry = sx_m / sens["slope_noise_x"], sy_m / sens["slope_noise_y"]
    print("  面の傾きの雑音: x %.2e(閉形式 %.2e、比 %.2f)、y %.2e(閉形式 %.2e、比 %.2f)"
          % (sx_m, sens["slope_noise_x"], rx, sy_m, sens["slope_noise_y"], ry))
    print("  比が 1 より小さいのは、面の格子点をカメラの画素の間で双線形に読むから: 独立な雑音の重み付き平均は"
          " 標準偏差を √(Σw²) 倍にし、小数位置が一様に散れば各軸 2/3 → √(4/9) = 0.67")
    check(0.6 < rx < 0.8 and 0.6 < ry < 0.8,
          "面の傾きの雑音 = σ_u / (2d)、σ_u / (2d cos θ) × 双線形の読み直し 0.67(±0.1)", "x %.2f / y %.2f" % (rx, ry))
    check(sx_m < sens["slope_pixel_bound"] / 10,
          "位相シフトの補間は「画面の画素 / (2d)」の刻みを 1 桁以上下回る",
          "%.2e < %.2e / 10" % (sx_m, sens["slope_pixel_bound"]))

    # ---- 3a. 高さと傾きの不定性 ------------------------------------------------- #
    print("\n[3a] 高さと傾きの不定性: 部品を浮かせて置く / 画面の距離を間違える")
    lifts = [0.0, 0.1, 0.2, 0.3, 0.5]
    cen = []
    for dz in lifts:
        n_l, _ = decode(h + dz, p, q, rig)
        pl, _ql = photometric.normals_to_gradients(n_l)
        cen.append(float(pl[N // 2, N // 2] - p[N // 2, N // 2]))
    pred = [dz * sens["height_slope_coupling"] for dz in lifts]
    gap = max(abs(abs(c) - pr) / pr for c, pr in zip(cen[1:], pred[1:]))
    print("  視野の中心の見かけの傾き:", ", ".join("%.1f mm → %.2e" % (dz, c) for dz, c in zip(lifts, cen)))
    check(gap < 0.05, "見かけの傾き = Δz·sin θ / d(視野の中心、Δz = 0.1〜0.5 mm)", "最大のずれ %.1f %%" % (100 * gap))
    dz = 0.3
    n_l, _ = decode(h + dz, p, q, rig)
    z_l = integrate(n_l, sp)
    z_0 = integrate(n_clean, sp)
    dzm = z_l - z_0
    A = np.stack([np.ones(N * N), XX.ravel(), YY.ravel(), (XX ** 2 + YY ** 2).ravel()], axis=1)
    inner = (np.abs(XX) < 15) & (np.abs(YY) < 15)
    coef = np.linalg.lstsq(A[inner.ravel()], dzm.ravel()[inner.ravel()], rcond=None)[0]
    bowl_r = 1.0 / (2 * coef[3]) / 1000.0 if coef[3] != 0 else float("inf")
    dep_l = depth(z_l, XX, YY, DIMPLE_A)
    pl, ql = photometric.normals_to_gradients(n_l)
    tilt = float(np.mean(pl - pc))
    print("  0.3 mm 浮かせると: 見かけの傾き %.2e rad(40 mm で %.1f µm の段差)、見かけの曲がり 半径 %.0f m の椀、"
          "凹み A の深さ %.3f µm(浮かせる前 %.3f)" % (tilt, 1000 * tilt * 40, bowl_r, 1000 * dep_l, 1000 * dep_a_true))
    check(abs(dep_l / dep_a_true - 1) < 0.03 and abs(tilt) > 10 * sens["slope_noise_x"],
          "浮かせても凹みの深さは変わらず、面全体の傾きだけが狂う(局所の欠陥検査は不定性に強い)",
          "深さ %+.1f %%、傾き %.2e rad" % (100 * (dep_l / dep_a_true - 1), tilt))
    rig_wrong = fs.ledger.deflectometry_rig(screen_distance_mm=d * 1.02)
    n_w, _ = decode(h, p, q, rig, decode_rig=rig_wrong)
    z_w = integrate(n_w, sp)
    dep_w = depth(z_w, XX, YY, DIMPLE_A)
    print("  画面の距離を 2 %% 長く思い込むと: 凹み A の深さ %.3f µm(%+.1f %%)" % (1000 * dep_w, 100 * (dep_w / dep_a_true - 1)))
    dzw = z_w - z_0
    coef_w = np.linalg.lstsq(A[inner.ravel()], dzw.ravel()[inner.ravel()], rcond=None)[0]
    bowl_w = 1.0 / (2 * coef_w[3]) / 1000.0 if coef_w[3] != 0 else float("inf")
    print("  距離の誤差は面全体を半径 %.0f m の椀に見せる(局所の 2 次形状を外して深さを測る理由)" % bowl_w)
    check(-0.03 < dep_w / dep_a_true - 1 < -0.01, "画面の距離を 2 % 長く思い込むと、凹みの深さが約 2 % 浅く出る(傾き ∝ 1/d)",
          "%+.2f %%" % (100 * (dep_w / dep_a_true - 1)))

    # ---- 3b. ざらつき(拡散成分) ------------------------------------------------- #
    print("\n[3b] ざらつき: 拡散成分の割合 k_d を上げていく")
    kds = [0.0, 0.5, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99, 0.995]
    rows_kd, frames, noise_kd, pred_kd, jumps_kd, snrb_kd = [], [], [], [], [], []
    for kd in kds:
        n_k, _ = decode(h, p, q, rig, diffuse_fraction=kd, noise_sigma=NOISE, bits=BITS, seed=3)
        pk, qk = photometric.normals_to_gradients(n_k)
        err = (pk - pc)[edge:-edge, edge:-edge]
        jump = float(np.mean(np.abs(err) > 0.5 * PERIOD / (2 * d)))      # 次数の飛び = 半周期ぶん以上の傾き
        s_k = fs.ledger.deflectometry_sensitivity(rig, PERIOD, 4, NOISE, bits=BITS, diffuse_fraction=kd)
        good = np.abs(err) < 0.25 * PERIOD / (2 * d)
        sm = float(np.std(err[good])) if good.any() else float("nan")
        kk = fs.ledger.slope_to_curvature(n_k, sp, "mean", SIGMA_PX)
        sb = float(np.nanmean(kk[(XX - DIMPLE_B[0]) ** 2 + (YY - DIMPLE_B[1]) ** 2 < (0.25 * DIMPLE_B[3]) ** 2])
                   / np.nanstd((kk - k_true)[far]))
        noise_kd.append(sm)
        pred_kd.append(s_k["slope_noise_x"])
        jumps_kd.append(jump)
        snrb_kd.append(sb)
        frames.append(np.clip(kk, -2.5e-3, 2.5e-3))
        rows_kd.append([("%.3f" % kd).rstrip("0").rstrip("."), "%.3f" % s_k["fringe_amplitude"],
                        "%.2e" % sm, "%.2e" % s_k["slope_noise_x"], "%.1f" % sb, "%.2f %%" % (100 * jump)])
        print("  k_d %.3f: 縞の振幅 %.4f、傾きの雑音 %.2e(閉形式 %.2e)、凹み B の SNR %5.1f、次数の飛び %.2f %%"
              % (kd, s_k["fringe_amplitude"], sm, s_k["slope_noise_x"], sb, 100 * jump))
    ratios = [m / pr for m, pr, j in zip(noise_kd, pred_kd, jumps_kd) if j == 0.0]
    check(all(0.6 < r < 0.85 for r in ratios) and len(ratios) >= 4,
          "次数が飛ばないあいだ、傾きの雑音は閉形式(× 双線形の 0.67)どおり 1 / (1 − k_d) で増える",
          "比 %s" % " / ".join("%.2f" % r for r in ratios))
    first_jump = next((kd for kd, j in zip(kds, jumps_kd) if j > 0.001), None)
    lost_b = next((kd for kd, s in zip(kds, snrb_kd) if s < 3.0), None)
    last_ok = max(kd for kd, s, j in zip(kds, snrb_kd, jumps_kd) if s > 5.0 and j == 0.0)
    amp_ok = FRINGE_B * (1 - last_ok) * sens["contrast_focus_surface"]
    print("  凹み B(1 µm)が SNR 3 を割る k_d = %s、粗い縞の次数が 0.1 %% 以上で飛ぶ k_d = %s" % (lost_b, first_jump))
    print("  ★2 つは同じ k_d で起きる: 粗い縞(周期 160 mm)の位相雑音は細かい縞の 16 倍に読み替わるので、雑音が"
          "半周期 π に届くと次数が飛び、飛んだ画素が曲率の雑音も押し上げる")
    check(last_ok >= 0.85 and first_jump is not None and first_jump > last_ok,
          "k_d 0.85(縞の振幅が 8 bit の約 15 段)までは 1 µm の凹みが見え、それより荒れると次数が飛んで崩れる",
          "見える上限 k_d %.2f(振幅 %.3f)、次数が飛ぶ k_d %s" % (last_ok, amp_ok, first_jump))

    # ---- 3c. ガラスの裏面反射 ----------------------------------------------------- #
    print("\n[3c] カバーガラスの裏面反射(n 1.52、無反射コートなし)")
    ng = 1.52
    ci = math.cos(th)
    r1 = float(glassmirror.fresnel_dielectric(ci, 1.0, ng))
    ct = math.cos(math.asin(math.sin(th) / ng))
    rb = float(glassmirror.fresnel_dielectric(ct, ng, 1.0))
    r2 = (1 - r1) * rb * (1 - rb)
    bound = math.asin(r2 / r1)
    print("  表の反射 R1 %.4f、裏から戻る R2 = (1 − R1)·R_b·(1 − R_b) %.4f → 位相の誤差の上限 asin(R2/R1) = %.2f rad"
          % (r1, r2, bound))
    thick = [0.1, 0.3, 0.55, 1.1, 2.0]
    gl_err, gl_dep = [], []
    for t in thick:
        phg = measure_phase(h, p, q, rig, back_thickness_mm=t, refractive_index=ng)
        e = np.angle(np.exp(1j * (phg["wx"] - ph_clean["wx"])))[edge:-edge, edge:-edge]
        gl_err.append(float(np.abs(e).max()))
        n_g = fs.ledger.deflectometry_phase_to_slope(phg["x"], phg["y"], rig, PERIOD)
        z_g = integrate(n_g, sp)
        gl_dep.append(depth(z_g, XX, YY, DIMPLE_A))
        print("  厚さ %.2f mm: 位相の誤差 最大 %.3f rad、凹み A の深さ %.3f µm(%+.0f %%)"
              % (t, gl_err[-1], 1000 * gl_dep[-1], 100 * (gl_dep[-1] / dep_a_true - 1)))
    check(max(gl_err) <= bound * 1.03, "裏面の縞が引っぱる位相は、2 つのフェーザの和の上限 asin(R2/R1) を超えない",
          "最大 %.3f ≤ %.3f rad" % (max(gl_err), bound))
    # 内訳: 凹みの斜面は表と平らな裏面のあいだで「くさび」になる。表の反射は傾き α で −2α 曲がるが、
    # 裏面で返る光はくさびのプリズムを往復して +(2 n cos θt / cos θ − 2)α と**逆向き**に曲がる(入射面内、一次近似)。
    # 薄い板(2 つの縞の位相差 ≈ 0)では、和の位相の傾きへの感度は重みつき平均 → 凹みの見かけの深さの比。
    ghost = 2 * ng * ct / ci - 2
    ratio_pred = (2 * r1 - ghost * r2) / (2 * (r1 + r2))
    phg = measure_phase(h, p, q, rig, back_thickness_mm=thick[0], refractive_index=ng)
    n_g = fs.ledger.deflectometry_phase_to_slope(phg["x"], phg["y"], rig, PERIOD)
    pg, _qg = photometric.normals_to_gradients(n_g)
    inner_m = np.zeros_like(h, bool)
    inner_m[edge:-edge, edge:-edge] = True
    sel = inner_m & np.isfinite(pg)
    ratio_meas = float(np.polyfit(p[sel], pg[sel], 1)[0])
    print("  ★内訳: 裏面の光は凹みの斜面(くさび)を往復して逆向きに +%.2f α 曲がる(表は −2α)→ 薄い板の傾きの感度は"
          " (2 R1 − %.2f R2) / 2(R1 + R2) = %.3f、実測(x の傾きの回帰)%.3f" % (ghost, ghost, ratio_pred, ratio_meas))
    check(abs(ratio_meas - ratio_pred) < 0.02,
          "裏面の縞は凹みを逆向きに映す: 薄いガラスの傾きの感度 = くさびのプリズムの閉形式(1/4 に縮む)",
          "実測 %.3f / 閉形式 %.3f" % (ratio_meas, ratio_pred))
    worst_dep = max(abs(g / dep_a_true - 1) for g in gl_dep)
    check(worst_dep > 0.5, "その結果、無反射コートの無いカバーガラスでは凹みが半分以下の深さにしか見えない",
          "最悪 %+.0f %%" % (-100 * worst_dep))

    # ---- 3d. ピント ------------------------------------------------------------- #
    print("\n[3d] ピントをどこに合わせるか(開口 8 mm)")
    rig8 = fs.ledger.deflectometry_rig(aperture_mm=8.0)
    alphas = [0.0, 0.25, 0.5, 1.0]
    mods, deps = [], []
    ref = {dd: fringe.wrapped_phase(fs.ledger.deflectometry_render(flat, rig8, COARSE, 4, dd)) * (COARSE / PERIOD)
           for dd in ("x", "y")}
    for a in alphas:
        phf = {}
        for dd in ("x", "y"):
            im = fs.ledger.deflectometry_render(h, rig8, PERIOD, 4, dd, slope_x=p, slope_y=q, focus=a,
                                                aperture_samples=24)
            phf[dd] = fringe.absolute_phase(fringe.wrapped_phase(im), ref[dd])
            phf["mod" + dd] = fringe.modulation(im)
        mods.append(float(np.median(phf["modx"])) / (FRINGE_B / 0.5))
        n_f = fs.ledger.deflectometry_phase_to_slope(phf["x"], phf["y"], rig8, PERIOD)
        z_f = integrate(n_f, sp)
        deps.append(depth(z_f, XX, YY, DIMPLE_A) / dep_a_true)
        print("  ピント %.2f(0 = 面、1 = 画面の虚像): 縞の振幅 × %.2f、凹み A の深さ × %.2f" % (a, mods[-1], deps[-1]))
    s8 = fs.ledger.deflectometry_sensitivity(rig8, PERIOD)
    check(abs(mods[0] - s8["contrast_focus_surface"]) < 0.03,
          "面にピント: 縞の振幅は画面側の錯乱円 A·d/L の円板の MTF どおりに落ちる",
          "実測 %.3f / 閉形式 %.3f" % (mods[0], s8["contrast_focus_surface"]))
    check(mods[-1] > 0.99 and deps[-1] < 0.9 and deps[0] > 0.97,
          "画面にピント: 縞はくっきりするが、面がぼけて凹みが浅く見える(面にピントなら深さは保たれる)",
          "画面にピントで深さ × %.2f、面にピントで × %.2f" % (deps[-1], deps[0]))
    print("  開口積分(24 点)は面にピントの閉形式と %.1f %% で合う(点の数を増やすと閉形式へ: tests/test_deflectometry.py)"
          % (100 * abs(mods[0] / s8["contrast_focus_surface"] - 1)))

    # ---- fail-closed --------------------------------------------------------- #
    refused = 0
    for bad in (dict(diffuse_fraction=1.0), dict(focus="lens"), dict(period_mm=0.0), dict(n_steps=2)):
        try:
            fs.ledger.deflectometry_render(h, rig, **bad)
        except ValueError:
            refused += 1
    try:
        bad_rig = dict(rig)
        bad_rig["camera"] = rig["camera"] * 1.1
        fs.ledger.deflectometry_phase_to_slope(ph["x"], ph["y"], bad_rig, PERIOD)
    except ValueError:
        refused += 1
    check(refused == 5, "測れない設定は黙って値を返さず拒否する(k_d = 1、知らないピント、周期 0、N = 2、手で動かした装置)",
          "%d / 5" % refused)

    real = real_chapter()

    elapsed = time.time() - t0
    cpu = time.process_time() - c0
    # 原本 280 枚の解析し直し(FULLSEYE_PMD_HAMMER_DATA があるときだけ、CI では走らない)は、この門の外で数える
    re_cpu = real["reanalysis_cpu"] if real is not None else 0.0
    cpu -= re_cpu
    # ★2026-10-15: 手元 23 秒の計算が、CI の並列のシャード(py3.12 3/4)では壁時計 120.6 秒になり、この門だけが赤に
    #   なった。壁時計は同じ機械で走る他のテストの負荷を数えてしまう。この門が抑えたいのは「この PoC 自身の計算量」
    #   なので、プロセスの CPU 時間で測る(壁時計は併記する。テスト側の 600 秒の打ち切りは別にある)。
    check(cpu < 120.0, "所要時間(この PoC 自身の CPU 時間。CI の上限に余裕を残す)",
          "CPU %.1f 秒(壁時計 %.1f 秒%s)" % (cpu, elapsed, "、原本の解析し直し CPU %.1f 秒を除く" % re_cpu if re_cpu else ""))

    if figs.enabled():
        small = fs.ledger.deflectometry_screen_pattern(rig, PERIOD, 4, "x", max_side_px=480)
        figs.save_grid("screen_patterns", small,
                       ["δ = 0", "δ = π/2", "δ = π", "δ = 3π/2"],
                       title="画面に出す位相シフト縞(周期 10 mm、4 枚)", ncols=2, gray=True, vrange=(0.0, 1.0),
                       caption="面の前の画面(%.0f × %.0f mm)にこの 4 枚を順に出し、面に映った鏡像を撮る。"
                               "縦縞は画面の u(入射面内)を、同じ 4 枚を横縞にしたものが v を符号化する。"
                               "粗い縞(周期 160 mm)の 4 枚で次数を決める。" % (sw, rig["screen_size_mm"][1]))
        _figures(rig, X, XX, YY, h, p, q, photo, ph, pm, qm, k_map, z, row, lifts, cen, pred, dzm, bowl_r,
                 kds, frames, noise_kd, pred_kd, rows_kd, thick, gl_err, gl_dep, bound, dep_a_true,
                 alphas, mods, deps, sens, dep_a, dep_b, dep_b_true, snr_a, snr_b, sig_photo, sx_m, sy_m,
                 (r1, r2, ratio_pred, ratio_meas), s8)
        if real is not None:
            _real_figures(real)
    assert not figs.errors(), figs.errors()

    bad = [ck for ck in CHECKS if not ck[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(CHECKS), len(CHECKS) - len(bad), elapsed))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


FRINGE_B = 0.45     # 画面の縞の振幅(deflectometry.FRINGE_AMPLITUDE と同じ値。表の欄に使う)


def _crop(a, XX, YY, cx, cy, half):
    m = (np.abs(XX[0] - cx) <= half)
    r = (np.abs(YY[:, 0] - cy) <= half)
    return a[np.ix_(r, m)]


def _figures(rig, X, XX, YY, h, p, q, photo, ph, pm, qm, k_map, z, row, lifts, cen, pred, dzm, bowl_r,
             kds, frames, noise_kd, pred_kd, rows_kd, thick, gl_err, gl_dep, bound, dep_a_true,
             alphas, mods, deps, sens, dep_a, dep_b, dep_b_true, snr_a, snr_b, sig_photo, sx_m, sy_m,
             glass, s8):
    um = 1000.0
    r1, r2, ratio_pred, ratio_meas = glass
    figs.save_grid("sample", [h * um, k_map],
                   ["仕込んだ高さ [µm](真値)", "測った平均曲率 [1/mm](±2.5e-3)"],
                   title="塗装パネルに仕込んだもの: 凹み 3 µm と 1 µm、うねり 0.8 µm、研磨ムラ 0.12 µm",
                   ncols=2, signed=[True, True], vrange=[None, (-2.5e-3, 2.5e-3)],
                   caption="左が真値の高さ(視野 40 mm、青 = 高い・橙 = 低い)。左上が凹み A(3 µm)、右下が凹み B(1 µm)、"
                           "右上の斑が研磨ムラ、全体の斜めの縞がうねり。右は縞の鏡像から測った平均曲率(青 = 凹み)。")
    wx = ph["wx"]
    figs.save_grid("photo_vs_pmd",
                   [photo, ph["imgx"][0], wx, pm, qm, k_map],
                   ["写真(ソフトボックスの映り込み)", "画面の縞の鏡像(1 枚目)", "位相(巻き込み、周期 10 mm)",
                    "勾配 ∂z/∂x [rad]", "勾配 ∂z/∂y [rad]", "平均曲率 [1/mm]"],
                   title="同じ塗装パネル: 写真では見えない凹みが、縞の鏡像の位相・勾配・曲率で見える",
                   ncols=3, gray=[True, True, False, False, False, False],
                   signed=[False, False, True, True, True, True],
                   vrange=[(0.0, 1.0), (0.0, 1.0), (-math.pi, math.pi), (-2e-3, 2e-3), (-2e-3, 2e-3),
                           (-2.5e-3, 2.5e-3)],
                   caption="写真の欠陥の信号は最大 %.5f(8 bit の 1 段 = 0.0039 より小さい)。縞の鏡像は凹みで縞が"
                           "わずかに曲がる(1 周期の 1 割弱)だけだが、位相 → 勾配 → 曲率と進むほどはっきりする。"
                           "曲率マップの SNR は凹み A で %.0f、B で %.0f。" % (sig_photo, snr_a, snr_b))
    cx, cy = DIMPLE_A[0], DIMPLE_A[1]
    ph_c = _crop(photo, XX, YY, cx, cy, 5.0)
    figs.save_grid("dimple_zoom",
                   [ph_c, _crop(ph["imgx"][0], XX, YY, cx, cy, 5.0), _crop(k_map, XX, YY, cx, cy, 5.0)],
                   ["写真(明るさを 25 倍に伸ばした)", "縞の鏡像", "平均曲率"],
                   title="凹み A(深さ 3 µm)の 10 mm 四方: 伸ばしても写真は雑音だけ",
                   ncols=3, gray=[True, True, False], signed=[False, False, True],
                   vrange=[(float(np.median(ph_c)) - 0.02, float(np.median(ph_c)) + 0.02), (0.0, 1.0),
                           (-2.5e-3, 2.5e-3)],
                   caption="写真は表示の幅を ±0.02(全幅の 1/25)まで狭めても、雑音(σ 0.004)と 8 bit の段しか見えない。")
    xs = X
    zt_row = (h[row] - h[row].mean()) * um
    zr_row = (z[row] - z[row].mean()) * um
    figs.save_plot("dimple_profile",
                   [("真値", xs, zt_row), ("縞の鏡像から(勾配を積分)", xs, zr_row),
                    ("差 × 10", xs, 10 * (zr_row - zt_row))],
                   xlabel="x [mm]", ylabel="高さ [µm](行の平均を 0)", title="凹み A を通る断面: 復元と真値",
                   colors=["reference", "emphasis", "neutral"], styles=["dashed", None, "dotted"], size=(760, 340),
                   caption="真値(破線)と復元(実線)はほぼ重なるので、差を 10 倍にして点線で重ねた。凹み A の深さ(局所の 2 次形状を"
                           "外した物差し): 復元 %.3f µm、真値 %.3f µm。凹み B: %.3f / %.3f µm。うねり 0.8 µm も重なっている。"
                           % (dep_a * um, dep_a_true * um, dep_b * um, dep_b_true * um))
    figs.save_table("sensitivity",
                    ["量", "閉形式", "実測"],
                    [["傾きの刻み(画面の画素 / 2d)", "%.2e rad" % sens["slope_pixel_bound"], "—"],
                     ["位相の雑音 √(2/N)·σ/b", "%.2e rad" % sens["phase_noise_rad"], "(本文)"],
                     ["傾きの雑音 x = σ_u / 2d", "%.2e rad" % sens["slope_noise_x"], "%.2e rad" % sx_m],
                     ["傾きの雑音 y = σ_u / (2d cos θ)", "%.2e rad" % sens["slope_noise_y"], "%.2e rad" % sy_m],
                     ["高さ → 傾き sin θ / d", "%.2e rad/mm" % sens["height_slope_coupling"],
                      "%.2e rad/mm" % (abs(cen[-1]) / lifts[-1])]],
                    title="撮る前の閉形式と、撮った後の実測",
                    caption="傾きの雑音の実測が閉形式より小さいのは、面の格子点をカメラの画素の間で双線形に読むため(独立な雑音の平均)。")
    figs.save_plot("height_slope_ambiguity",
                   [("閉形式 Δz·sin θ / d", np.asarray(lifts), np.asarray(pred) * 1e3),
                    ("実測(視野の中心)", np.asarray(lifts), np.abs(np.asarray(cen)) * 1e3)],
                   xlabel="部品を浮かせた高さ Δz [mm]", ylabel="見かけの傾き [mrad]",
                   title="高さと傾きは分けられない: 浮かせた分だけ傾いて見える",
                   kinds=["line", "scatter"], colors=["reference", "wrong"], styles=["dashed", None], size=(620, 360),
                   caption="1 台のカメラと 1 枚の画面では、面が Δz 高いことと、法線が Δz sin θ / d 傾いていることが"
                           "同じ位相を作る(PMD の既知の不定性)。")
    G = np.stack([np.ones(XX.size), XX.ravel(), YY.ravel()], axis=1)
    plane = (G @ np.linalg.lstsq(G, dzm.ravel(), rcond=None)[0]).reshape(dzm.shape)
    figs.save_grid("ambiguity_map", [dzm * um, (dzm - plane) * um],
                   ["0.3 mm 浮かせたときの、積分した高さの狂い [µm]", "そこから平面を引いた残り [µm]"],
                   title="浮かせた平らな板は、傾いて曲がった板に見える(凹みは変わらない)",
                   ncols=2, signed=True,
                   caption="平らな板を 0.3 mm 浮かせただけで、測った高さは 40 mm で約 14 µm 傾く(左、視野の中心で 3.4e-4 rad)。"
                           "傾きの狂いは視野の中で一様でない(画素ごとに入射角と距離が違う)ので、平面を引いても半径 %.0f m の椀に"
                           "相当する曲がりが残る(右)。凹みの位置に残る小さな濃淡が局所の影響で、深さは 1 %% 未満しか変わらない。"
                           % abs(bowl_r))
    lut = np.asarray(fs.diverging_lut(256))
    labeled = []
    for kd, fr, rw in zip(kds, frames, rows_kd):
        idx = np.clip((np.nan_to_num(fr) / 2.5e-3 * 0.5 + 0.5) * 255.0, 0, 255).astype(np.int32)
        rgb = np.clip(lut[idx], 0.0, 1.0)
        rgb = np.asarray(AN.text_box(rgb, "k_d = %g   縞の振幅 %s" % (kd, rw[1]), (6, 6), anchor="lt", font_size=13,
                                     max_width=rgb.shape[1] - 12))
        labeled.append(rgb)
    figs.save_gif("diffuse_sweep", labeled, fps=1.5,
                  caption="拡散成分 k_d = %s と上げていったときの平均曲率(±2.5e-3 /mm)。雑音が 1/(1 − k_d) で増え、"
                          "浅い凹み B が先に沈み、最後は粗い縞の次数が飛ぶ。" % ", ".join("%g" % k for k in kds))
    ok = [i for i, v in enumerate(noise_kd) if np.isfinite(v)]
    figs.save_plot("diffuse_noise",
                   [("閉形式 σ_u / 2d × 双線形 0.67", np.log10(1 - np.asarray(kds)[ok]),
                     np.log10(np.asarray(pred_kd)[ok] * 2.0 / 3.0)),
                    ("実測", np.log10(1 - np.asarray(kds)[ok]), np.log10(np.asarray(noise_kd)[ok]))],
                   xlabel="log10(1 − k_d)(右が鏡、左がざらざら)", ylabel="log10(傾きの雑音 [rad])",
                   title="ざらつくほど縞の振幅が落ち、傾きの雑音は 1 / (1 − k_d) で増える",
                   kinds=["line", "scatter"], colors=["reference", "emphasis"], styles=["dashed", None], size=(620, 380),
                   caption="右の 4 点(k_d ≤ 0.85)は傾き −1 の直線(1 / (1 − k_d))に乗る。k_d ≥ 0.9 では粗い縞の次数が"
                           "飛び始め、飛んだ画素(誤差が周期の 1/4 を超えるもの)を雑音の計算から外すので、実測は直線から"
                           "外れて頭打ちになる —— ここから先は「雑音が増える」でなく「測れない」の領域。")
    figs.save_table("diffuse_table", ["k_d", "縞の振幅", "傾きの雑音", "閉形式", "凹み B の SNR", "次数の飛び"],
                    rows_kd, title="拡散成分と壊れ方",
                    caption="8 bit・雑音 σ 0.004。振幅が 1 段(0.0039)に近づくと位相が決まらない。")
    figs.save_plot("glass_back_reflection",
                   [("位相の誤差の最大", np.asarray(thick), np.asarray(gl_err)),
                    ("上限 asin(R2/R1)", np.asarray(thick), np.full(len(thick), bound))],
                   xlabel="ガラスの厚さ [mm]", ylabel="位相の誤差 [rad]",
                   title="カバーガラスの裏面の縞が、表の縞の位相を引っぱる",
                   kinds=["line", "line"], colors=["wrong", "reference"], styles=[None, "dashed"], size=(620, 360),
                   caption="表と裏の反射率はほぼ同じ(R1 %.3f、R2 %.3f)なので、2 つの縞の和の位相は上限 %.2f rad まで"
                           "ずれ得る。しかも裏面の光は凹みの斜面(くさび)を往復して逆向きに曲がるので、傾きの感度は"
                           "閉形式 %.3f(実測 %.3f)に縮み、凹みの深さは厚さによらず %s %% と狂う。" % (
                               r1, r2, bound, ratio_pred, ratio_meas,
                               " / ".join("%+.0f" % (100 * (g / dep_a_true - 1)) for g in gl_dep)))
    figs.save_plot("glass_depth",
                   [("凹み A の見かけの深さ / 真値", np.asarray(thick), np.asarray(gl_dep) / dep_a_true),
                    ("閉形式(薄い板、くさびのプリズム)", np.asarray(thick), np.full(len(thick), ratio_pred)),
                    ("無反射コートあり(裏面の反射 0)", np.asarray(thick), np.ones(len(thick)))],
                   xlabel="ガラスの厚さ [mm]", ylabel="比", ylim=(0.0, 1.1),
                   title="カバーガラスでは、凹みが 1/4 の深さにしか見えない",
                   kinds=["line", "line", "line"], colors=["wrong", "reference", "right"],
                   styles=[None, "dashed", "dotted"], size=(620, 360),
                   caption="凹みの斜面は表と平らな裏面のあいだで「くさび」になる。表で返る光は −2α 曲がるが、裏面で返る光は"
                           "くさびを往復して +%.2f α と逆向きに曲がり、2 つの縞の和の位相では傾きの感度が"
                           " (2 R1 − %.2f R2) / 2(R1 + R2) = %.3f に縮む(実測 %.3f)。厚い板では 2 つの縞の位相差が"
                           "開いて少し戻る。" % (2 * 1.52 * math.cos(math.asin(math.sin(math.radians(20.0)) / 1.52))
                                              / math.cos(math.radians(20.0)) - 2,
                                              2 * 1.52 * math.cos(math.asin(math.sin(math.radians(20.0)) / 1.52))
                                              / math.cos(math.radians(20.0)) - 2, ratio_pred, ratio_meas))
    figs.save_plot("focus_tradeoff",
                   [("縞の振幅(面にピントで落ちる)", np.asarray(alphas), np.asarray(mods)),
                    ("凹みの深さ / 真値(画面にピントで落ちる)", np.asarray(alphas), np.asarray(deps))],
                   xlabel="ピントの位置(0 = 面、1 = 画面の虚像)", ylabel="比",
                   title="ピントは面と画面の両方には合わない(開口 8 mm)",
                   colors=["emphasis", "wrong"], size=(620, 360),
                   caption="面に合わせると画面側の錯乱円 A·d/L = %.0f mm で縞の振幅が %.2f 倍に落ちる。画面に合わせると"
                           "縞はくっきりするが、面側の錯乱円 A·d/(L+d) = %.1f mm で凹みがぼけ、深さが %.2f 倍に見える"
                           "(開口の 24 点で光線を追った)。" % (s8["blur_screen_focus_surface_mm"], mods[0],
                                                          s8["blur_surface_focus_screen_mm"], deps[-1]))


# =========================================================================== #
# 4. 実データの章(CC0): 鏡面の鋼板をハンマーで叩き、格子の鏡像から傾き → 力    #
# =========================================================================== #
# データ: Kaufmann, Olufsen, Fagerholt (NTNU), "Experimental data for force reconstruction using impact hammer
# and deflectometry", DataverseNO, doi:10.18710/TKS7SI(CC0 1.0、取得 2026-10-18)。生の 280 枚(110 MB)は repo の
# 外に置き、FULLSEYE_PMD_HAMMER_DATA がそのディレクトリを指すときだけ全部を解析する。repo には切り出した 3 枚と、
# 全解析の記録(力の時系列など)を data/pmd_real/hammer_grid_cc0.npz に置く(作り方は tools/gen_pmd_real.py)。
REAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_ENV = "FULLSEYE_PMD_HAMMER_DATA"
REAL_NPZ = os.path.join(REAL_ROOT, "data", "pmd_real", "hammer_grid_cc0.npz")
REAL_SOURCE = ("R. Kaufmann, S. N. Olufsen, E. Fagerholt (NTNU), Experimental data for force reconstruction using "
               "impact hammer and deflectometry, DataverseNO, doi:10.18710/TKS7SI, CC0 1.0 (切り出し・位相解析は Fullseye)")
GRID_PX = 5                   # 格子 1 周期の画素数(データの説明書き)
GRID_PITCH_M = 5.88433e-3     # 印刷した十字格子の周期 [m]
GRID_DIST_M = 1.37            # 板(鏡)と格子の距離 h [m]
PIXEL_M = GRID_PITCH_M / 10   # 板の上の画素の間隔: カメラも格子も板から h の距離にあるので p / (2 × 5 画素)
FPS = 75000.0                 # 高速度カメラの駒の速さ
T0_FRAME = 150                # ハンマーの時刻 0 は image_0150(データの著者が公開したコード recolo の例と同じ対応)
REF_FRAMES = tuple(range(1, 31))
SEQ_FRAMES = tuple(f for f in range(150, 401) if f != 384)    # 原本に image_0384 は無い
PLATE_E, PLATE_NU, PLATE_T, PLATE_RHO = 190e9, 0.3, 4.95e-3, 7.9e3
MOD_MIN = 0.05                # 格子の変調度の下限。窓の中に 1 画素でも下回る所があれば、その窓は拒否する
JUMP_MAX = math.pi / 2        # 隣の駒との位相の差の上限。超えたら時間方向のつなぎ(2π の次数)が決まらない
CURL_MAX = 0.3                # 傾きの場の回転 / 発散。超えたら「ある面の勾配」として積分できない
SIG_FRAMES = 6.0              # 時間方向のガウスの σ [駒](データの著者の例と同じ。比べるハンマーにも同じものを掛ける)
CANDIDATES = tuple((h, m) for h in (60, 70, 85, 100, 120) for m in (40, 50, 60, 70, 80) if h - m >= 10)
ZERO_MODES = ("border", "corners", "bottom")
# 第 2 の実装: データの著者が公開した recolo(MIT、commit 05b14f0)を同じ画像で手元で走らせた値(2026-10-18)。
# 例のままの設定(区分的な仮想場 20 点、部分領域 20:50 の和)。比べる相手のハンマーには同じ σ = 6 駒のガウスを掛けた。
RECOLO = {"peak_N": 363.6, "t_peak_ms": 1.773, "corr": 0.987, "impulse_Ns": 0.1912, "whole_plate_peak_N": 422.2}
WIN_T = (0.9e-3, 2.8e-3)      # 比べる時間の範囲 [s](打撃の前後)


def grid_phase(img, pitch=GRID_PX):
    """十字格子の 1 枚 → x と y の搬送波の複素振幅と局所の平均(格子法: ガウス窓 σ = 1 周期の窓つき DFT)。

    Grédiac, Sur & Blaysat, Strain 52, 205 (2016) の格子法。返り値の偏角が格子の位相、絶対値の 2 倍 / 平均が変調度。
    **Raises** ``ValueError``: 2 次元でない、または 6 周期に満たない画像。"""
    from scipy.ndimage import gaussian_filter
    a = np.asarray(img, dtype=float)
    if a.ndim != 2 or min(a.shape) < 6 * pitch:
        raise ValueError("grid_phase: 2 次元で 6 周期以上の画像が要る(%r)" % (a.shape,))
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(float)

    def sm(z):
        return gaussian_filter(z, float(pitch), mode="nearest", truncate=3.0)

    k = 2.0 * math.pi / pitch
    cx = sm(a * np.cos(k * xx)) - 1j * sm(a * np.sin(k * xx))
    cy = sm(a * np.cos(k * yy)) - 1j * sm(a * np.sin(k * yy))
    return cx, cy, sm(a)


def _interp_every(a, k, pitch):
    """最後の軸を k, k + p, k + 2p, … で間引き、元の格子へ線形補間で戻す(端は最寄りの標本のまま)。"""
    n = a.shape[-1]
    s = a[..., k::pitch]
    pos = (np.arange(n, dtype=float) - k) / pitch
    j0 = np.clip(np.floor(pos).astype(int), 0, s.shape[-1] - 1)
    j1 = np.clip(j0 + 1, 0, s.shape[-1] - 1)
    f = np.clip(pos - np.floor(pos), 0.0, 1.0)
    f = np.where(pos < 0, 0.0, f)
    return s[..., j0] * (1.0 - f) + s[..., j1] * f


def sampling_moire_phase(img, pitch=GRID_PX):
    """第 2 の実装: 標本化モアレ法(Ri, Fujigaki & Morimoto, Exp. Mech. 50, 501 (2010))。

    直交方向に 1 周期の箱で均して他方の格子を消し、p 画素おきに間引いて線形補間した p 枚のモアレ縞(位相が 2π/p
    ずつずれる)を、p 段の位相シフトとして読む。窓つき DFT とは平滑化の形も位相の取り方も違う。x と y の複素振幅を返す。"""
    from scipy.ndimage import uniform_filter1d
    a = np.asarray(img, dtype=float)
    if a.ndim != 2 or min(a.shape) < 6 * pitch:
        raise ValueError("sampling_moire_phase: 2 次元で 6 周期以上の画像が要る(%r)" % (a.shape,))
    out = []
    for axis in (1, 0):
        b = uniform_filter1d(a, pitch, axis=1 - axis, mode="nearest")
        b = np.moveaxis(b, axis, -1)
        z = np.zeros(b.shape, complex)
        for k in range(pitch):
            z += _interp_every(b, k, pitch) * np.exp(-2j * math.pi * k / pitch)
        out.append(np.moveaxis(z, -1, axis))
    return out[0], out[1]


def _phase_smooth(phi, sigma):
    """巻き込み位相を、単位円の上で(cos と sin を別々に)ガウスで均す。"""
    from scipy.ndimage import gaussian_filter
    e = np.exp(1j * np.asarray(phi))
    return np.angle(gaussian_filter(e.real, sigma) + 1j * gaussian_filter(e.imag, sigma))


def phase_change(c, c_ref):
    """基準の駒からの位相の変化(巻き込み、[-π, π])。"""
    return np.angle(c * np.conj(c_ref))


def grid_modulation(cx, cy, mean):
    """格子の変調度(x と y の小さい方)。黒い枠・影・ピンぼけで 0 に近づく。"""
    return 2.0 * np.minimum(np.abs(cx), np.abs(cy)) / np.maximum(mean, 1e-9)


def slope_from_phase(dphi):
    """位相の変化 → 板の傾きの変化 [rad]: 格子の上の見かけの変位 u = p Δφ / 2π、傾き = u / 2h(Kaufmann ら 2023 の式 1)。

    符号は「ハンマーが板を押す向きを +」にする約束(カメラの軸の向きはデータから決まらない 1 bit)。"""
    return -GRID_PITCH_M * np.asarray(dphi) / (4.0 * math.pi * GRID_DIST_M)


def curl_ratio(sx, sy, sigma=3.0):
    """傾きの場の回転と発散の RMS の比。ある面の勾配なら回転は 0(雑音だけ)。"""
    from scipy.ndimage import gaussian_filter
    a = gaussian_filter(np.asarray(sx, float), sigma)
    b = gaussian_filter(np.asarray(sy, float), sigma)
    curl = np.gradient(a, axis=0) - np.gradient(b, axis=1)
    div = np.gradient(a, axis=1) + np.gradient(b, axis=0)
    return float(np.sqrt(np.mean(curl ** 2)) / max(np.sqrt(np.mean(div ** 2)), 1e-30))


def require_integrable(sx, sy):
    """回転 / 発散が CURL_MAX を超える傾きの場は、積分も仮想仕事も意味を持たないので拒否する。"""
    r = curl_ratio(sx, sy)
    if not r <= CURL_MAX:
        raise ValueError("傾きの場が積分できない: 回転 / 発散 = %.2f > %.2f(x と y の軸か符号の取り違え)" % (r, CURL_MAX))
    return r


def temporal_unwrap(wrapped, region=None, stride=1, gate=True):
    """駒の列の巻き込み位相を、時間方向に 1 駒ずつつなぐ(stride 駒おきに間引いてつなぐこともできる)。

    隣の駒との差が JUMP_MAX を超えた画素が region の中に 1 つでもあれば、2π の次数が決まらないので拒否する
    (gate=False は探針用: 拒否せずにつないで、どれだけ間違えるかを見る)。返り値は (つないだ位相, 差の最大)。"""
    w = np.asarray(wrapped)[::stride]
    w = w.astype(np.float32 if w.dtype == np.float32 else float)
    reg = np.ones(w.shape[1:], bool) if region is None else region
    out = np.empty_like(w)
    out[0] = w[0]
    jmax = 0.0
    for k in range(1, len(w)):
        d = np.angle(np.exp(1j * (w[k] - out[k - 1])))
        jmax = max(jmax, float(np.abs(d[reg]).max()))
        out[k] = out[k - 1] + d
    if gate and jmax > JUMP_MAX:
        raise ValueError("時間方向のつなぎが決まらない: 隣の駒との位相差 %.2f rad > %.2f rad(%d 駒おき)"
                         % (jmax, JUMP_MAX, stride))
    return out, jmax


def _smooth_step(u):
    u = np.clip(u, 0.0, 1.0)
    a = np.where(u > 0, np.exp(-1.0 / np.maximum(u, 1e-300)), 0.0)
    b = np.where(u < 1, np.exp(-1.0 / np.maximum(1.0 - u, 1e-300)), 0.0)
    return a / (a + b)


def plateau_window(n, m, step):
    """仮想変位の 1 次元の形: 中央が平ら(= 1)で、両端の m 標本で C∞ に 0 へ落ちる窓と、その 1〜3 階の導関数。

    端で値も全導関数も 0 なので、窓の縁での境界の仮想仕事(縁の反力・モーメント)が消える。3 階まで
    滑らかでないと(多項式の smoothstep では 3 階が端で跳ぶ)、部分積分した和の端の 1 標本が誤差を作る
    (点荷重のグリーン関数で確かめた: 7 次の smoothstep でも m = 40 で 2.2 倍、この窓は m = 60 で 1e-4)。"""
    if n < 2 * m + 2 or m < 4:
        raise ValueError("plateau_window: 窓 %d 標本に、両端 %d 標本の傾斜と平らな部分が入らない" % (n, m))
    over = 64
    s = np.arange((n - 1) * over + 1) / over
    out = [_smooth_step(s / m) * _smooth_step((n - 1 - s) / m)]
    for _ in range(3):
        out.append(np.gradient(out[-1], 1.0 / over, edge_order=2))
    return [o[::over] / step ** k for k, o in enumerate(out)]


def vfm_window_terms(sx, sy, w, box, m, impact, mod):
    """仮想場の方法(VFM)で、窓 box の中の点荷重を測る 2 つの項を駒ごとに返す。

    Kirchhoff 板: ∫ p w* dS = ρt ∫ ẅ w* dS + D ∫ ∇²w ∇²w* dS(窓の外とは仮想場が 0 なので縁の項が消える)。
    点荷重が窓の平らな部分(w* = 1)にあれば左辺は力 F そのもの。曲げの項は部分積分で
    −D ∫ ∇w · ∇(∇²w*) dS にし、**測った傾きを微分しない**(Kaufmann ら は 3 点差分で曲率を出す)。
    返り値: (曲げの項 [N], ∫ w w* dS [m³])。 慣性の項は呼び手が時間で 2 回微分する。

    **Raises** ``ValueError``: 窓が格子の変調度の低い所(MOD_MIN 未満)にかかる、荷重点が平らな部分の外。"""
    r0, r1, c0, c1 = box
    if not (0 <= r0 < r1 <= mod.shape[0] and 0 <= c0 < c1 <= mod.shape[1]):
        raise ValueError("窓 %r が視野の外にはみ出す" % (box,))
    mm = float(mod[r0:r1, c0:c1].min())
    if mm < MOD_MIN:
        raise ValueError("窓 %r の格子の変調度 %.3f < %.2f(枠・影・ピンぼけ)—— 位相が雑音" % (box, mm, MOD_MIN))
    by = plateau_window(r1 - r0, m, PIXEL_M)
    bx = plateau_window(c1 - c0, m, PIXEL_M)
    wv = by[0][:, None] * bx[0][None, :]
    if impact is not None:
        iy, ix = impact[0] - r0, impact[1] - c0
        if not (0 <= iy < r1 - r0 and 0 <= ix < c1 - c0) or wv[iy, ix] < 1.0 - 1e-9:
            raise ValueError("荷重点 %r が窓 %r の平らな部分に無い(w* が 1 でない所の力は F にならない)" % (impact, box))
    lx = bx[3][None, :] * by[0][:, None] + bx[1][None, :] * by[2][:, None]
    ly = bx[2][None, :] * by[1][:, None] + bx[0][None, :] * by[3][:, None]
    d_plate = PLATE_E * PLATE_T ** 3 / (12.0 * (1.0 - PLATE_NU ** 2))
    da = PIXEL_M * PIXEL_M
    bend = -d_plate * da * (np.einsum("kij,ij->k", sx[:, r0:r1, c0:c1], lx)
                            + np.einsum("kij,ij->k", sy[:, r0:r1, c0:c1], ly))
    inert = da * np.einsum("kij,ij->k", w[:, r0:r1, c0:c1], wv)
    return bend, inert, float(wv.sum() * da)


def vfm_force(bend, inert, t):
    """曲げの項 + ρt × (∫ w w* の 2 階の時間微分)。どちらにも同じ時間のガウス(SIG_FRAMES)を掛ける。"""
    from scipy.ndimage import gaussian_filter1d
    js = gaussian_filter1d(bend, SIG_FRAMES)
    acc = np.gradient(np.gradient(gaussian_filter1d(inert, SIG_FRAMES), t), t)
    return js + PLATE_RHO * PLATE_T * acc, js


def _load_tif(path):
    from PIL import Image
    with Image.open(path) as im:
        a = np.asarray(im)
    if a.ndim != 2 or a.dtype.kind not in "ui":
        raise ValueError("%s: 2 次元の整数の画像でない(%s %s)" % (path, a.dtype, a.shape))
    return a.astype(float)


def analyze_hammer_dataset(path, report=print):
    """原本の 280 枚とハンマーの記録から、全部を解析する(FULLSEYE_PMD_HAMMER_DATA があるときと gen_pmd_real)。"""
    from scipy.ndimage import gaussian_filter, gaussian_filter1d
    names = ["image_%04d.tif" % f for f in REF_FRAMES + SEQ_FRAMES]
    missing = [n for n in names if not os.path.isfile(os.path.join(path, n))]
    for n in ("hammer_force.txt", "hammer_time.txt"):
        if not os.path.isfile(os.path.join(path, n)):
            missing.append(n)
    if missing:
        raise ValueError("%s に無いファイル %d 個(例 %s)" % (path, len(missing), missing[:3]))
    hf = np.loadtxt(os.path.join(path, "hammer_force.txt"))
    ht = np.loadtxt(os.path.join(path, "hammer_time.txt"))
    if hf.shape != ht.shape or hf.ndim != 1 or not np.all(np.diff(ht) > 0):
        raise ValueError("ハンマーの記録の形が合わない(%s / %s)" % (hf.shape, ht.shape))
    ref = np.mean([_load_tif(os.path.join(path, "image_%04d.tif" % f)) for f in REF_FRAMES], axis=0)
    rx, ry, rm = grid_phase(ref)
    mod = grid_modulation(rx, ry, rm)
    rows = np.where(np.median(mod, axis=1) >= MOD_MIN)[0]
    cols = np.where(np.median(mod, axis=0) >= MOD_MIN)[0]
    # 窓つき DFT の窓(σ = 1 周期)は 3σ = 15 画素先まで届くので、変調度の低い縁から 15 画素は内側へ寄せる
    # (8 画素だと右端の画素で隣の駒との位相差が 1.72 rad になり、時間方向のつなぎの門が拒否した)。
    ins = 3 * GRID_PX
    R0, R1, C0, C1 = int(rows[0]) + ins, int(rows[-1]) + 1 - ins, int(cols[0]) + ins, int(cols[-1]) + 1 - ins
    crop = (slice(R0, R1), slice(C0, C1))
    wx, wy = [], []
    for f in SEQ_FRAMES:
        cx, cy, _ = grid_phase(_load_tif(os.path.join(path, "image_%04d.tif" % f)))
        wx.append(phase_change(cx, rx)[crop].astype(np.float32))
        wy.append(phase_change(cy, ry)[crop].astype(np.float32))
    wx = np.asarray(wx)
    wy = np.asarray(wy)
    modc = mod[crop]
    good = modc >= MOD_MIN
    px, jx = temporal_unwrap(wx, good)
    py, jy = temporal_unwrap(wy, good)
    del wx, wy
    sx = slope_from_phase(px).astype(np.float32)
    sy = slope_from_phase(py).astype(np.float32)
    del py
    t = (np.asarray(SEQ_FRAMES, float) - T0_FRAME) / FPS
    nt = len(t)
    rms = np.sqrt(np.mean(sx ** 2 + sy ** 2, axis=(1, 2)))
    base = float(rms[:60].mean())
    k0 = int(np.argmax(rms > 10.0 * base))
    lap = (np.gradient(gaussian_filter(sx[k0 + 8], 8.0), axis=1)
           + np.gradient(gaussian_filter(sy[k0 + 8], 8.0), axis=0))
    inner = np.zeros(lap.shape, bool)
    inner[20:-20, 20:-20] = True
    impact = tuple(int(v) for v in np.unravel_index(np.argmax(np.abs(lap) * inner), lap.shape))
    # 傾き → たわみ(既存の sfp_height: 鏡像拡張した Frankot–Chellappa)
    w0 = np.empty_like(sx)
    for k in range(nt):
        n = np.dstack([-sx[k], -sy[k], np.ones_like(sx[k])]).astype(float)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        w0[k] = fs.ledger.sfp_height(n) * PIXEL_M
    zero = {"border": np.concatenate([w0[:, :3].reshape(nt, -1), w0[:, -3:].reshape(nt, -1),
                                      w0[:, :, :3].reshape(nt, -1), w0[:, :, -3:].reshape(nt, -1)], axis=1).mean(1),
            "corners": np.mean([w0[:, :5, :5].mean((1, 2)), w0[:, :5, -5:].mean((1, 2)),
                                w0[:, -5:, :5].mean((1, 2)), w0[:, -5:, -5:].mean((1, 2))], axis=0),
            "bottom": 0.5 * (w0[:, -5:, :5].mean((1, 2)) + w0[:, -5:, -5:].mean((1, 2)))}
    win = (t > WIN_T[0]) & (t < WIN_T[1])
    iy, ix = impact
    cache = {}

    def force(cy_, cx_, half, m, mode, imp):
        key = (cy_, cx_, half, m)
        if key not in cache:
            cache[key] = vfm_window_terms(sx, sy, w0, (cy_ - half, cy_ + half, cx_ - half, cx_ + half), m, imp, modc)
        bend, inert, wsum = cache[key]
        return vfm_force(bend, inert - zero[mode] * wsum, t)[0]

    table = []
    for half, m in CANDIDATES:
        for mode in ZERO_MODES:
            try:
                f_imp = force(iy, ix, half, m, mode, impact)
            except ValueError:
                continue
            nulls = []
            for dy, dx in ((-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (0, 1), (0, -1), (1, 0)):
                try:
                    f0 = force(iy + 2 * dy * half, ix + 2 * dx * half, half, m, mode, None)
                except ValueError:
                    continue
                nulls.append((float(np.abs(f0[win]).max()), (iy + 2 * dy * half, ix + 2 * dx * half), f0))
            if len(nulls) >= 2:
                table.append((max(v[0] for v in nulls), half, m, mode, f_imp, nulls))
    if not table:
        raise ValueError("荷重の無い対照の窓を 2 つ以上置ける窓の大きさが無い")
    table.sort(key=lambda r: (round(r[0], 6), r[1], r[2], ZERO_MODES.index(r[3])))
    floor, half, m, mode, F, nulls = table[0]
    hs_raw = np.interp(t, ht, hf)
    hs = gaussian_filter1d(hs_raw, SIG_FRAMES)
    bend, inert, wsum = cache[(iy, ix, half, m)]
    F2, J = vfm_force(bend, inert - zero[mode] * wsum, t)
    # 窓の大きさを変えると(同じ傾斜幅)
    sizes = []
    for h2 in (60, 70, 85, 100, 130, 160, 190):
        if h2 - m < 10:
            continue
        try:
            fz = force(iy, ix, h2, m, mode, impact)
        except ValueError:
            continue
        sizes.append((h2, float(fz[win].max())))
    # 探針: この板の位相の振れは最大でも π の手前(|Δφ| ≤ 2.9 rad)なので、基準と直接比べても次数は狂わない。
    # 門が効くことを確かめるため、測った位相を k 倍した列(格子を k 倍遠くに置いたのと同じ感度)を作り、
    # 1 駒ずつ / 間引いてつないだ結果を、k 倍した真の列と比べる。「2π を取り違えた間引きは必ず拒否されたか」を見る。
    stride_rows = []
    direct_wrong = []
    for kk in (1.0, 1.5, 2.5):
        truth = (kk * px).astype(np.float32)
        wr = np.angle(np.exp(1j * truth)).astype(np.float32)
        direct_wrong.append((kk, float(np.abs(truth[:, good]).max()), float(np.mean(np.abs(truth[:, good]) > math.pi))))
        for s in (1, 2, 4, 8, 16):
            un, jm = temporal_unwrap(wr, good, stride=s, gate=False)
            slip = float(np.mean(np.abs(un - truth[::s])[:, good] > math.pi))
            stride_rows.append((kk, s, jm, slip, float(jm > JUMP_MAX)))
        del truth, wr
    pre = t < 1.1e-3
    report("  格子の変調度で切った視野 %d:%d × %d:%d、荷重点(打撃の直後のたわみの中心)= (%d, %d)、打撃の始まり image_%04d"
        % (R0, R1, C0, C1, iy + R0, ix + C0, SEQ_FRAMES[k0]))
    return {
        "t": t, "F": F2, "bend": J, "inertia": F2 - J, "hammer_raw": hs_raw, "hammer_smooth": hs,
        "hammer_t": ht, "hammer_f": hf,
        "null_F": np.asarray([v[2] for v in nulls]), "null_centres": np.asarray([v[1] for v in nulls]),
        "floor": floor, "half": half, "m": m, "mode": mode, "impact": np.asarray(impact), "crop": np.asarray([R0, R1, C0, C1]),
        "jump_x": jx, "jump_y": jy, "pre_std": float(F2[pre].std()),
        "sizes": np.asarray(sizes), "strides": np.asarray(stride_rows), "direct_wrong": np.asarray(direct_wrong),
        "candidates": np.asarray([(r[0], r[1], r[2], ZERO_MODES.index(r[3]), float(r[4][win].max())) for r in table]),
        "curl": curl_ratio(sx[k0 + 20], sy[k0 + 20]),
        "slope_peak_x": sx[int(np.argmax(rms))], "slope_peak_y": sy[int(np.argmax(rms))],
        "frame_peak": SEQ_FRAMES[int(np.argmax(rms))],
    }


def force_scores(t, F, hs):
    """力の時系列を、同じ σ で均したハンマーの記録と比べる数(峰・峰の時刻・相関・力積)。"""
    win = (t > WIN_T[0]) & (t < WIN_T[1])
    k = int(np.argmax(F[win]))
    kh = int(np.argmax(hs[win]))
    return {"peak": float(F[win][k]), "t_peak": float(t[win][k]), "peak_h": float(hs[win][kh]),
            "t_peak_h": float(t[win][kh]), "corr": float(np.corrcoef(F[win], hs[win])[0, 1]),
            "impulse": _trapz(F[win], t[win]), "impulse_h": _trapz(hs[win], t[win])}


def _trapz(y, x):
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))


def real_chapter():
    """4 節: 公開の実データ(CC0)で、格子の鏡像 → 位相 → 傾き → 板の力 を、ハンマーの力の記録と突き合わせる。"""
    print("\n== 4. 実データ(CC0): 鏡面の鋼板をハンマーで叩き、格子の鏡像の動きから力を測る")
    print("  出典: " + REAL_SOURCE)
    if not os.path.isfile(REAL_NPZ):
        check(False, "実データの切り出し data/pmd_real/hammer_grid_cc0.npz がある", REAL_NPZ)
        return None
    z = np.load(REAL_NPZ)
    r0, c0 = (int(v) for v in z["crop_origin"])
    ref = z["ref_mean_x8"].astype(float) / 8.0
    rx, ry, rm = grid_phase(ref)
    mod = grid_modulation(rx, ry, rm)
    out = {"ref": ref, "mod": mod, "origin": (r0, c0), "z": z}
    # (a) 窓つき DFT(格子法)と標本化モアレの 2 つの実装で、同じ 2 駒の位相の変化を読む
    sx_ref, sy_ref = sampling_moire_phase(ref)
    from scipy.ndimage import binary_erosion
    g = mod >= MOD_MIN
    g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = False
    inner = binary_erosion(g, iterations=3 * GRID_PX)     # 変調度の低い所と縁から 3σ(窓の届く範囲)離す
    agree = []
    for key in ("frame_hammer_peak", "frame_max_slope"):
        img = z[key].astype(float)
        cx, cy, _ = grid_phase(img)
        mx, my = sampling_moire_phase(img)
        for nm, a, b in (("x", phase_change(cx, rx), phase_change(mx, sx_ref)),
                         ("y", phase_change(cy, ry), phase_change(my, sy_ref))):
            d0 = np.angle(np.exp(1j * (a[inner] - b[inner])))
            a5, b5 = _phase_smooth(a, GRID_PX), _phase_smooth(b, GRID_PX)
            d = np.angle(np.exp(1j * (a5[inner] - b5[inner])))
            agree.append((key, nm, float(np.sqrt(np.mean(d ** 2))), float(np.corrcoef(a5[inner], b5[inner])[0, 1]),
                          float(np.sqrt(np.mean(d0 ** 2)))))
        out[key] = (phase_change(cx, rx), phase_change(cy, ry), phase_change(mx, sx_ref))
    worst_rms = max(a[2] for a in agree)
    worst_corr = min(a[3] for a in agree)
    print("  2 つの実装(窓つき DFT / 標本化モアレ)の位相の変化の差(視野の %.0f %%): そのままでは RMS 最大 %.4f rad"
          "(標本化モアレは平滑が弱く雑音が多い)、両方に同じ σ = 1 周期の平滑を掛けると RMS 最大 %.4f rad・相関 最小 %.5f"
          % (100 * inner.mean(), max(a[4] for a in agree), worst_rms, worst_corr))
    check(worst_rms < 0.02 and worst_corr > 0.999,
          "実画像の格子の位相: 窓つき DFT(格子法)と標本化モアレ(第 2 の実装)が同じ分解能で一致する",
          "RMS %.4f rad < 0.02、相関 %.5f > 0.999(2 駒 × x, y)" % (worst_rms, worst_corr))
    # (b) 積分できる場か(x と y の軸・符号の取り違えを捕まえる)
    ax, ay, _ = out["frame_max_slope"]
    gx, gy = slope_from_phase(ax), slope_from_phase(ay)
    sl = (slice(30, None), slice(10, -10))
    ratio = require_integrable(gx[sl], gy[sl])
    refused = 0
    try:
        require_integrable(gx[sl], -gy[sl])
    except ValueError:
        refused += 1
    try:
        require_integrable(gy[sl], gx[sl])
    except ValueError:
        refused += 1
    check(ratio < CURL_MAX and refused == 2,
          "傾きの場は積分できる(回転 / 発散が小さい)。y の符号を反転・x と y を入れ替えると拒否する",
          "回転 / 発散 %.3f < %.2f、壊した 2 通りは %d / 2 拒否" % (ratio, CURL_MAX, refused))
    # (c) 変調度の低い所(板の上端の枠の影)にかかる窓は、値を返さず拒否する
    mrow = np.median(mod, axis=1)
    print("  格子の変調度(行の中央値): 上端 %.3f → 20 行目 %.3f → 中央 %.3f(下限 %.2f)"
          % (mrow[2], mrow[20], mrow[len(mrow) // 2], MOD_MIN))
    nseq = 4
    dummy = np.zeros((nseq,) + mod.shape)
    try:
        vfm_window_terms(dummy, dummy, dummy, (0, 120, 60, 180), 40, None, mod)
        low_ok = False
    except ValueError as e:
        low_ok = "変調度" in str(e)
    check(low_ok, "格子の変調度が下限を割る窓(板の上端の枠の影)は、力を返さず拒否する",
          "窓 0:120 の最小 %.3f < %.2f" % (float(mod[0:120, 60:180].min()), MOD_MIN))
    # (d) 全解析の記録(原本 280 枚から。CI では原本が無いので記録を読む)
    rec = {k: z[k] for k in z.files if k.startswith("rec_")}
    data_dir = os.environ.get(REAL_ENV, "")
    if data_dir:
        print("  %s = %s があるので、原本の 280 枚から全部を解析し直す(数分)" % (REAL_ENV, data_dir))
        c_re = time.process_time()
        res = analyze_hammer_dataset(data_dir)
        reanalysis_cpu = time.process_time() - c_re
        live = {"rec_t": res["t"], "rec_F": res["F"], "rec_hammer_smooth": res["hammer_smooth"],
                "rec_floor": res["floor"], "rec_half": res["half"], "rec_m": res["m"]}
        drift = float(np.max(np.abs(live["rec_F"] - rec["rec_F"])))
        check(drift < 0.5, "原本から解析し直した力の時系列が、commit した記録と一致する(記録が古びていない)",
              "最大差 %.3f N < 0.5 N" % drift)
    else:
        reanalysis_cpu = 0.0
        print("  %s が無いので、原本からの全解析は飛ばし、記録(tools/gen_pmd_real.py が原本から作った値)を読む" % REAL_ENV)
    t, F, hs = rec["rec_t"], rec["rec_F"], rec["rec_hammer_smooth"]
    sc = force_scores(t, F, hs)
    half, m = int(rec["rec_half"]), int(rec["rec_m"])
    mode = ZERO_MODES[int(rec["rec_mode"])]
    floor = float(rec["rec_floor"])
    print("  窓の選び方(ハンマーを見ない): 候補 %d 通りのうち、荷重の無い対照の窓 %d つでの見かけの力の最大"
          "(床)が最小のもの → 半幅 %d 画素(%.0f mm)、傾斜 %d 画素、たわみの基準 = %s。床 %.1f N"
          % (len(rec["rec_candidates"]), len(rec["rec_null_F"]), half, half * PIXEL_M * 1e3, m, mode, floor))
    print("  ハンマー(同じ σ = %g 駒で均した): 峰 %.1f N @ %.3f ms、力積 %.4f N·s(均す前の峰 %.1f N)"
          % (SIG_FRAMES, sc["peak_h"], sc["t_peak_h"] * 1e3, sc["impulse_h"], float(rec["rec_hammer_raw"].max())))
    print("  格子の鏡像から(VFM): 峰 %.1f N @ %.3f ms(%+.1f %%、%+.0f µs)、相関 %.3f、力積 %.4f N·s(%+.1f %%)"
          % (sc["peak"], sc["t_peak"] * 1e3, 100 * (sc["peak"] / sc["peak_h"] - 1), 1e6 * (sc["t_peak"] - sc["t_peak_h"]),
             sc["corr"], sc["impulse"], 100 * (sc["impulse"] / sc["impulse_h"] - 1)))
    print("  第 2 の実装 recolo(データの著者の公開コード): 峰 %.1f N @ %.3f ms(%+.1f %%)、相関 %.3f、力積 %.4f N·s"
          % (RECOLO["peak_N"], RECOLO["t_peak_ms"], 100 * (RECOLO["peak_N"] / sc["peak_h"] - 1), RECOLO["corr"],
             RECOLO["impulse_Ns"]))
    pre = float(rec["rec_pre_std"])
    jump = float(max(rec["rec_jump_x"], rec["rec_jump_y"]))
    check(jump < JUMP_MAX, "時間方向のつなぎが決まる: 75 kHz の隣の駒との位相差が π/2 未満(使う視野の全画素)",
          "最大 %.2f rad < %.2f rad" % (jump, JUMP_MAX))
    check(pre < 5.0, "打撃の前(t < 1.1 ms)の見かけの力が小さい(位相の雑音の床)", "標準偏差 %.2f N < 5 N" % pre)
    check(floor < 0.1 * sc["peak_h"], "荷重の無い対照の窓の見かけの力(床)が、ハンマーの峰の 1 割未満",
          "%.1f N < %.1f N" % (floor, 0.1 * sc["peak_h"]))
    check(abs(sc["peak"] / sc["peak_h"] - 1) < 0.10, "力の峰がハンマーの記録(外部の真値)と 10 % 以内",
          "%.1f N 対 %.1f N(%+.1f %%)" % (sc["peak"], sc["peak_h"], 100 * (sc["peak"] / sc["peak_h"] - 1)))
    check(abs(sc["t_peak"] - sc["t_peak_h"]) <= 3.0 / FPS + 1e-9, "峰の時刻がハンマーと 3 駒(40 µs)以内",
          "%+.0f µs" % (1e6 * (sc["t_peak"] - sc["t_peak_h"])))
    check(sc["corr"] > 0.97, "力の時系列の形がハンマーと合う(0.9〜2.8 ms の相関)", "%.3f > 0.97" % sc["corr"])
    check(abs(sc["impulse"] / sc["impulse_h"] - 1) < 0.12, "力積がハンマーと 12 % 以内",
          "%.4f 対 %.4f N·s(%+.1f %%)" % (sc["impulse"], sc["impulse_h"], 100 * (sc["impulse"] / sc["impulse_h"] - 1)))
    check(abs(sc["peak"] / RECOLO["peak_N"] - 1) < 0.05, "第 2 の実装(recolo)の峰と 5 % 以内",
          "%.1f 対 %.1f N(%+.1f %%)" % (sc["peak"], RECOLO["peak_N"], 100 * (sc["peak"] / RECOLO["peak_N"] - 1)))
    strides = rec["rec_strides"]
    for kk, pmax, frac in rec["rec_direct_wrong"]:
        rows_k = [r for r in strides if r[0] == kk]
        print("  位相 × %.1f(最大 %.2f rad): 基準と直接比べると 2π を取り違える画素 %.4f %%;つなぐと " % (kk, pmax, 100 * frac)
              + "、".join("%d 駒おき 差 %.2f rad %s 取り違え %.4f %%" % (int(s), jm, "拒否" if rf else "通す", 100 * sl)
                         for _, s, jm, sl, rf in rows_k))
    silent = [(kk, int(s)) for kk, s, jm, sl, rf in strides if sl > 0 and not rf]
    refused = [(kk, int(s)) for kk, s, jm, sl, rf in strides if rf]
    full_rate = [sl for kk, s, jm, sl, rf in strides if s == 1]
    check(not silent and refused and max(full_rate) == 0.0
          and max(fr for _, _, fr in rec["rec_direct_wrong"]) > 0.0,
          "時間方向のつなぎ: 2π を取り違えた間引きは 1 つ残らず拒否され、75 kHz の 1 駒ずつなら位相を 2.5 倍にしても取り違え 0",
          "黙って間違えた組 %d、拒否 %d 組、直接比べると取り違える画素の最大 %.3f %%"
          % (len(silent), len(refused), 100 * max(fr for _, _, fr in rec["rec_direct_wrong"])))
    sizes = rec["rec_sizes"]
    print("  窓を大きくすると峰が育つ: " + "、".join("半幅 %d → %.0f N" % (int(h), p) for h, p in sizes)
          + "(recolo の板全体の和は %.0f N)" % RECOLO["whole_plate_peak_N"])
    out.update({"rec": rec, "scores": sc, "reanalysis_cpu": reanalysis_cpu})
    return out


def _box_overlay(img, boxes, value, widths=None):
    """画像に窓の枠を描く(線の太さは widths、既定 2 画素)。枠が画像の外にはみ出す分は描かない。"""
    a = np.array(img, dtype=float)
    for i, (r0, r1, c0, c1) in enumerate(boxes):
        lw = 2 if widths is None else int(widths[i])
        r0, r1 = max(int(r0), 0), min(int(r1), a.shape[0])
        c0, c1 = max(int(c0), 0), min(int(c1), a.shape[1])
        if r0 >= r1 or c0 >= c1:
            continue
        a[r0:r0 + lw, c0:c1] = value
        a[r1 - lw:r1, c0:c1] = value
        a[r0:r1, c0:c0 + lw] = value
        a[r0:r1, c1 - lw:c1] = value
    return a


def _real_figures(real):
    """4 節の図。npz の切り出しと記録だけで描く(原本が無くても同じ図が出る)。"""
    z, rec, sc = real["z"], real["rec"], real["scores"]
    r0, c0 = real["origin"]
    R0, _, C0, _ = (int(v) for v in rec["rec_crop"])
    iy, ix = (int(v) for v in rec["rec_impact"])
    cy, cx = iy + R0 - r0, ix + C0 - c0               # npz の切り出しの中の荷重点
    zoom = 6
    half_z = 24
    ref = real["ref"]
    dfm = z["frame_max_slope"].astype(float)

    def zoomed(a):
        c = a[cy - half_z:cy + half_z, cx - half_z:cx + half_z]
        return np.kron(c, np.ones((zoom, zoom)))

    lo, hi = float(np.percentile(ref, 1)), float(np.percentile(ref, 99.5))
    figs.save_grid("real_grid_mirror",
                   [zoomed(ref), zoomed(dfm)],
                   ["打撃の前(30 枚の平均)", "たわみが最大の駒(image_%04d)" % int(rec["rec_frame_peak"])],
                   title="実物: 鏡面の鋼板に映った十字格子(荷重点のまわり 48 × 48 画素を 6 倍に拡大)",
                   ncols=2, gray=True, vrange=[(lo, hi), (lo, hi)],
                   caption="1 周期 = 5 画素(印刷した格子の周期 5.88 mm、板から 1.37 m)。たわんだ板の鏡像では格子が"
                           "わずかに歪む(1 周期の 1/3 ほど)が、目ではほとんど分からない。出典: " + REAL_SOURCE)
    ax_w, ay_w, ax_m = z_phase = real["frame_max_slope"]
    del z_phase
    diff = np.angle(np.exp(1j * (ax_w - ax_m)))
    diff5 = np.angle(np.exp(1j * (_phase_smooth(ax_w, GRID_PX) - _phase_smooth(ax_m, GRID_PX))))
    figs.save_grid("real_phase_two_methods",
                   [ax_w, ax_m, 20.0 * diff, 20.0 * diff5],
                   ["窓つき DFT(格子法)Δφx", "標本化モアレ(第 2 の実装)Δφx", "差 × 20(そのまま)",
                    "差 × 20(両方に同じ σ = 1 周期の平滑)"],
                   title="同じ実画像の位相の変化を、2 つの実装で読む(たわみが最大の駒)",
                   ncols=2, signed=True, vrange=[(-math.pi, math.pi)] * 4,
                   caption="基準(打撃の前の 30 枚の平均)からの位相の変化(巻き込み、±π)。上端の帯は板の枠の影で、格子の"
                           "変調度が下限 %.2f を割る(ここにかかる窓は拒否する)。そのままの差は標本化モアレの雑音(平滑が 1 方向の"
                           "箱だけで、行ごとの補間の筋が出る)。同じ平滑を掛けると差は 20 倍しても暗く、縁と上端の帯にだけ残る。"
                           % MOD_MIN)
    gx, gy = slope_from_phase(ax_w), slope_from_phase(ay_w)
    mag = np.hypot(gx, gy)
    half, m = int(rec["rec_half"]), int(rec["rec_m"])
    boxes = [(cy - half, cy + half, cx - half, cx + half)]
    for (ny_, nx_) in rec["rec_null_centres"]:
        nyc, nxc = int(ny_) + R0 - r0, int(nx_) + C0 - c0
        boxes.append((nyc - half, nyc + half, nxc - half, nxc + half))
    vmax = float(np.percentile(mag[30:], 99.5))
    figs.save_grid("real_slopes_and_windows",
                   [gx, gy, _box_overlay(np.clip(mag, 0, vmax), boxes, vmax, [6] + [2] * (len(boxes) - 1)), real["mod"]],
                   ["傾き ∂w/∂x [rad]", "傾き ∂w/∂y [rad]", "|傾き| と窓(太枠 = 荷重、他 = 対照)", "格子の変調度"],
                   title="格子の位相 → 板の傾き(たわみが最大の駒)と、力を測る窓",
                   ncols=2, signed=[True, True, False, False],
                   vrange=[(-vmax, vmax), (-vmax, vmax), (0.0, vmax), (0.0, 0.4)],
                   caption="傾き = p Δφ / (4π h)。荷重点のまわりの窓(半幅 %d 画素 = %.0f mm、縁の %d 画素で仮想変位が"
                           "滑らかに 0 へ落ちる)で力を測り、同じ大きさの窓を荷重の無い所に %d つ置いて「見かけの力」の床を測る。"
                           % (half, half * PIXEL_M * 1e3, m, len(boxes) - 1))
    tw = (rec["rec_t"] >= 0.8e-3) & (rec["rec_t"] <= 3.0e-3)
    t_ms = rec["rec_t"][tw] * 1e3
    ser = [("ハンマー(均す前)", t_ms, rec["rec_hammer_raw"][tw]),
           ("ハンマー(σ = 6 駒で均した、外部の真値)", t_ms, rec["rec_hammer_smooth"][tw]),
           ("格子の鏡像から(VFM、荷重の窓)", t_ms, rec["rec_F"][tw])]
    for k, fn in enumerate(rec["rec_null_F"][:3]):
        ser.append(("荷重の無い窓 %d" % (k + 1), t_ms, fn[tw]))
    ser.append(("recolo(第 2 の実装)の峰", np.array([RECOLO["t_peak_ms"]]), np.array([RECOLO["peak_N"]])))
    kinds = ["line"] * (len(ser) - 1) + ["scatter"]
    colors = ["neutral", "reference", "emphasis"] + ["neutral"] * (len(ser) - 4) + ["right"]
    styles = ["dotted", "dashed", None] + [None] * (len(ser) - 4) + [None]
    figs.save_plot("real_force_vs_hammer", ser, xlabel="時刻 [ms](image_0150 = 0)", ylabel="力 [N]",
                   title="板の傾きだけから、ハンマーの力を読む(実データ、CC0)",
                   kinds=kinds, colors=colors, styles=styles, size=(820, 420),
                   caption="峰 %.1f N @ %.3f ms(ハンマー %.1f N @ %.3f ms、%+.1f %%)、相関 %.3f、力積 %+.1f %%。"
                           "荷重の無い窓の見かけの力は最大 %.1f N(2.2〜2.4 ms、たわみが最大の頃に出る系統の誤差)。"
                           % (sc["peak"], sc["t_peak"] * 1e3, sc["peak_h"], sc["t_peak_h"] * 1e3,
                              100 * (sc["peak"] / sc["peak_h"] - 1), sc["corr"],
                              100 * (sc["impulse"] / sc["impulse_h"] - 1), float(rec["rec_floor"])),
                   source=REAL_SOURCE)
    sizes = rec["rec_sizes"]
    figs.save_plot("real_window_size",
                   [("荷重の窓の峰(この解析)", sizes[:, 0] * PIXEL_M * 1e3, sizes[:, 1]),
                    ("ハンマー(均した)", np.array([30.0, 160.0]), np.full(2, sc["peak_h"])),
                    ("recolo の板全体の和(半幅 ≈ 150 mm)", np.array([150.0]), np.array([RECOLO["whole_plate_peak_N"]]))],
                   xlabel="窓の半幅 [mm]", ylabel="力の峰 [N]",
                   title="窓を大きくすると、力の峰が育つ(板全体では +15 %)",
                   kinds=["line", "line", "scatter"], colors=["emphasis", "reference", "wrong"],
                   styles=[None, "dashed", None], size=(620, 360), xlim=(30.0, 160.0), ylim=(330.0, 440.0),
                   caption="傾斜の幅を同じにして窓だけ広げた。縁に近い所の傾きの系統の誤差を拾うほど峰が上がり、データの"
                           "著者の recolo でも板全体を足すと %.0f N(+15 %%)になる。窓は荷重の無い対照の窓で選ぶ。"
                           % RECOLO["whole_plate_peak_N"], source=REAL_SOURCE)


if __name__ == "__main__":
    main()
