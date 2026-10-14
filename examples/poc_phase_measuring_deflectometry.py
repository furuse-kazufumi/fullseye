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

【真値】仕込んだ面の高さは解析式で、勾配も解析的に既知(順方向の描画にもその解析値を渡す)。深さの真値は
同じ物差し(中心と環の差)を真の高さに当てた値。【学習】0。【較正】0(装置の幾何は既知とする)。

★正直に書いておくこと:
  * 合成です。カメラはピンホール + 薄レンズのぼけ、画面は平らで輝度は角度に依らない。画面の画素の格子と
    液晶の階調の非線形(Wu ら 2015 の主な誤差源)は入れていません。装置の幾何(距離・角度)は既知としていて、
    実機ではこの較正が精度の大半を決めます(3(a) の 2 % はその感度)。
  * 拡散成分は「画面の平均輝度を一様に足す」近似、裏面は平らで表と平行です。
  * 積分(Frankot–Chellappa)は周期境界なので、視野の縁のうねりは歪みます。深さは局所の物差しで測ります。

出典: Knauer, Kaminski & Häusler, Proc. SPIE 5457, 366 (2004) / Wu ら, Opt. Eng. 54(6), 064103 (2015) /
Frankot & Chellappa, IEEE PAMI 10(4), 439 (1988) / Wang, Cossairt & Willomitzer, Optica 12 (2025)。

走らせ方: ``py -3.11 examples/poc_phase_measuring_deflectometry.py``(図は ``FULLSEYE_FIGURE_DIR`` か
既定の ``out/figures/<PoC 名>/``)。
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

    elapsed = time.time() - t0
    check(elapsed < 120.0, "所要時間(CI の上限に余裕を残す)", "%.1f 秒" % elapsed)

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


if __name__ == "__main__":
    main()
