# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: モアレで位置合わせ —— 見えない 2 µm の格子 2 枚を重ねると、1 nm のずれが縞の位相で読める。

【問い】リソグラフィやナノインプリントでは、マスクとウェハを nm の精度で重ねる。カメラの分解能は µm なのに、
なぜ nm が読めるのか。答えは**ピッチの僅かに違う 2 枚の格子**(マスク p_m = 2.00 µm、ウェハ p_w = 2.04 µm)。
2 枚はどちらもカメラのぼけで潰れて見えないが、重ねると周期 P = p_m p_w / |Δp| = 102 µm の縞(モアレ)が現れ、
ウェハが δ 動くと縞は M = p_m / |Δp| = 50 倍の距離を動く。縞の位相をロックイン(既知の周波数での最小二乗)で
読むと、ずれは雑音の下限まで読める。新 op 8 本(`moirealign`、`opsoptics` の `moire_align`)を閉形式の真値で採点する。

  1. **拡大率の閉形式**: 縞の周期は網点のモアレ(``printpath.halftone_moire_period``)と同じ式で 102 µm、像から測った
     周期も同じ。★拡大率は**どちらが動くか**で違う: ウェハが動けば M = p_m/|Δp| = 50、マスクが動けば p_w/|Δp| = 51
     (よく書かれる「M = p_w/|Δp|」はマスクが動く場合の式)。門: 像から測った縞の移動量 / δ が 2 つとも 1e-3 以内。
  2. **1 nm ずつ動かす**: 直接の像(ウェハの格子だけ)はぼけで標準偏差 1e-5 の一様な灰色で、ずれは見えない。
     モアレは 1 nm の階段を 1 段ずつ読み分ける。比べ手 = 解像できる 20 µm の線のマークを相互相関 + 放物線の
     サブピクセル補間(``filters_freq.correlation_fft``)。門: モアレの誤差の RMS < 0.3 nm、階段 10 段すべて正しい向き。
  3. **雑音の下限(CRLB)と比べ手との差の内訳**: 白色雑音 σ を振った Monte-Carlo の標準偏差は ``moire_phase_crlb``
     (Rife & Boorstyn 1974 の位相の下限 × Hann の係数 1.5 × 基準像の雑音 2 倍)と 0.75〜1.35 倍。★比べ手との差を
     **内訳に分ける**(異常に良い数字は疑う): (a) 放物線補間の偏り(ずれに比例する、いわゆる peak locking)、
     (b) 同じ 20 µm の線を**同じ位相の読み方**で読んだ場合、(c) ピッチの差(2.04 µm 対 20 µm)と縞の振幅。
     ★所見: 誤差 RMS の差は約 90 倍(2 桁)だが、**その大半は放物線の偏り**(ずれを 17 % 小さく読む)で、偶然の誤差
     だけなら 0.08 対 0.2 nm の 2〜2.5 倍しか違わない。線のマークを位相で読むと相互相関より悪い(縁の高調波を捨てる)。
     差が開くのはカメラを粗くしたとき(画素 0.5 → 2 µm で相互相関は 2.3 倍悪化、モアレは揺れの範囲で変わらない)。
  4. **差動で共通の誤差を消す**: 逆向きのピッチ差の 2 対(A = (2.00, 2.04)、B = (2.04, 2.00))はずれで逆に、マーク全体の
     流れで同じ向きに動く。マーク全体が 300 nm 流れ、照明が 30 % 傾き、カメラの倍率を 2 % 間違えても、
     単一の対は 6 nm 狂い、差動は 0.3 nm 以内。★ずれへの換算はピッチだけで決まり、倍率の誤り 2 % は読みに入らない
     (相互相関は 2 % そのまま比例して狂う)。2 次元の 4 象限のマークで (dx, dy) を同時に読む。
  5. **折り返し(1 周期の不定性)**: δ と δ + p_w は同じ像 —— 印刷の版ずれ(poc_print_registration)と同じ不定性。
     差動の捕捉範囲は p_m p_w/(p_m + p_w) = 1.01 µm と半分に縮む。粗い相互相関で次数を決め(``fringe.absolute_phase``)、
     5 µm まで折り返さずに読む。
  6. **近接ギャップの Talbot 効果**: マスクとウェハの間のギャップでマスクの像が回折し、縞の振幅は Talbot 長
     2p²/λ = 14.5 µm で戻り、その半分で**符号が反転**する(``optics.angular_spectrum_propagate``)。基準像と測定像の
     間でギャップが反転を跨ぐと読みが半周期跳ぶ。振幅 0 の近くでは雑音が 1/振幅 で増える。

【外部真値】縞の周期と拡大率の閉形式、位相推定の Cramér–Rao 下限(Rife & Boorstyn, IEEE Trans. IT 20, 591 (1974))、
Talbot 長 2p²/λ(Lord Rayleigh 1881)。手法の出典: Takeda, Ina & Kobayashi, JOSA 72, 156 (1982)(FFT による縞解析)/
Li, Wu & Chou, Nano Lett. 6, 2626 (2006)(ナノインプリントのモアレ位置合わせ、重ね合わせ 20 nm 未満)/
Zhu, Hu, Yu et al., Opt. Express 21, 3463 (2013)(近接露光の 4 象限の格子と位相復調)/ Moon & Smith,
J. Vac. Sci. Technol. B 23, 2607 (2005)(ISPI: 空間位相で 1 nm 未満の検出能)/ Patorski, *Handbook of the Moiré
Fringe Technique* (1993)。【学習】0。【較正】0。

★正直な限界: ここで出る 0.1 nm 級の数字は**白色雑音だけ**の世界の値。公表されている位置合わせの精度は 10〜30 nm
(Li ら 2006、Zhu ら 2013)で、実際はマークの非対称(エッチ・CMP)、ギャップとウェハの傾き、レジストの膜、照明の
斜入射などの**系統誤差**が決める。この PoC はその手前の「雑音の床」と「差動で消える誤差・消えない誤差」を示す。

EXTEND: 実機の像で使うなら、``moire_mark_read`` の区画(layout)を実際のマークの並びに合わせ、基準像を
「ずれ 0 と分かっている状態」で撮る(または差動の 2 対の対称性を使って基準を取る)。マークの非対称は
差動でも消えないので、180 度回したマークの対で測り、平均で打ち消すのが次の一手。2 枚の格子の相対回転は
縞を大きく傾けるので(``moire_magnification`` の twist_mrad)、``moire_phase(method="fft")`` の位相の地図の
傾きから回転も読める。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import filters_freq as FF  # noqa: E402
import moirealign as MA  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

PM, PW = 2.00, 2.04            # マスク・ウェハの格子のピッチ µm
PX = 0.5                       # 物体側の画素 µm
SHAPE = (256, 1024)            # 1 対のマークの像
SIGMA = 0.01                   # 白色雑音(平均の強度 0.25 の 4 %)
P_BAR = 20.0                   # 比べ手: 解像できる線のマークのピッチ µm

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def xcorr_shift_nm(meas, ref, pixel_um=PX):
    """比べ手: 相互相関(既存 ``filters_freq.correlation_fft``)の山を放物線で補間した x のずれ(nm)。"""
    c = FF.correlation_fft(meas - meas.mean(), ref - ref.mean())
    row = c[0]
    n = row.size
    k = int(np.argmax(row))
    a, b, cc = row[(k - 1) % n], row[k], row[(k + 1) % n]
    d = 0.5 * (a - cc) / (a - 2 * b + cc)
    kk = k if k <= n // 2 else k - n
    return (kk + d) * pixel_um * 1e3


def bar(shift_nm=0.0, seed=0, noise=SIGMA, pixel_um=PX, drift_nm=0.0, grad=0.0):
    return MA.moire_overlay_image(SHAPE, pixel_um, PM, P_BAR, shift_nm, with_mask=False, noise_sigma=noise, seed=seed,
                                  drift_nm=drift_nm, illum_gradient=grad)


def mark(shift_nm=0.0, seed=0, noise=SIGMA, layout="single", **kw):
    shape = kw.pop("shape", SHAPE if layout != "quad" else (1024, 1024))
    return MA.moire_overlay_image(shape, PX, PM, PW, shift_nm, layout=layout, noise_sigma=noise, seed=seed, **kw)


# --------------------------------------------------------------------------- #
def chapter_magnification():
    print("\n1. 拡大率の閉形式(どちらの格子が動くか)")
    mw = MA.moire_magnification(PM, PW, "wafer")
    mm = MA.moire_magnification(PM, PW, "mask")
    P = PM * PW / abs(PW - PM)
    gate("縞の周期 %.3f µm = p_m p_w/|Δp|(網点のモアレと同じ式)" % mw["moire_period_um"], abs(mw["moire_period_um"] / P - 1) < 1e-12)
    est = MA.moire_phase(mark(noise=0.0), None)
    NUMBERS["period_measured_um"] = est["period_px"] * PX
    gate("像の FFT の山から測った周期 %.3f µm(設計 %.1f µm、0.1 %% 以内)" % (est["period_px"] * PX, P),
         abs(est["period_px"] * PX / P - 1) < 1e-3)
    out = {}
    for mv, m in (("wafer", mw), ("mask", mm)):
        r0 = mark(noise=0.0, moving=mv)
        r1 = mark(100.0, noise=0.0, moving=mv)
        a = MA.moire_phase(r0, P / PX)
        b = MA.moire_phase(r1, P / PX)
        s = MA.moire_phase_to_shift(b["phase_rad"], a["phase_rad"], PM, PW, mv)
        meas_M = abs(s["fringe_shift_um"]) / 0.1
        out[mv] = meas_M
        NUMBERS["M_" + mv] = meas_M
        gate("%s が 100 nm 動くと縞は %.3f µm 動く: 測った M = %.3f(閉形式 %.3f、1e-3 以内)"
             % ("ウェハ" if mv == "wafer" else "マスク", abs(s["fringe_shift_um"]), meas_M, m["magnification"]),
             abs(meas_M / m["magnification"] - 1) < 1e-3)
    gate("★2 つの拡大率は区別できる(%.2f 対 %.2f、比 = p_w/p_m)" % (out["wafer"], out["mask"]),
         abs(out["mask"] / out["wafer"] - PW / PM) < 2e-3)
    return mw


def chapter_steps():
    print("\n2. 1 nm ずつ動かす(直接の像・相互相関・モアレ)")
    direct = bar(noise=0.0)
    direct_fine = MA.moire_overlay_image(SHAPE, PX, PM, PW, 0.0, with_mask=False)
    NUMBERS["direct_std"] = float(direct_fine.std())
    gate("ウェハの 2.04 µm の格子だけを撮った像は一様な灰色(標準偏差 %.1e、平均 %.3f)—— ずれは見えない"
         % (direct_fine.std(), direct_fine.mean()), direct_fine.std() < 1e-4)
    steps = np.arange(0.0, 11.0, 1.0)
    rm, rx = [], []
    ref_m = mark(seed=100)
    ref_b = bar(seed=100)
    for i, d in enumerate(steps):
        rm.append(MA.moire_mark_read(mark(d, seed=200 + i), ref_m, PX, PM, PW, "single")["shift_x_nm"])
        rx.append(xcorr_shift_nm(bar(d, seed=200 + i), ref_b))
    rm, rx = np.array(rm), np.array(rx)
    em, ex = rm - steps, rx - steps
    NUMBERS.update({"steps_rms_moire": float(np.sqrt(np.mean(em ** 2))), "steps_rms_xcorr": float(np.sqrt(np.mean(ex ** 2)))})
    gate("モアレ: 1 nm の階段 11 段の誤差 RMS %.3f nm(< 0.3 nm)" % NUMBERS["steps_rms_moire"], NUMBERS["steps_rms_moire"] < 0.3)
    gate("モアレ: 10 段すべて正しい向きに 1 nm ± 0.5 nm 進む", bool(np.all(np.abs(np.diff(rm) - 1.0) < 0.5)),
         "段差 %s" % np.array2string(np.diff(rm), precision=2))
    slope_x = float(np.polyfit(steps, rx, 1)[0])
    NUMBERS["steps_slope_xcorr"] = slope_x
    gate("相互相関 + 放物線: 階段の向きは追える(誤り %d / 10)が、傾き %.3f —— ずれを %.0f %% 小さく読み、誤差 RMS %.2f nm(モアレの %.0f 倍)"
         % (int(np.sum(np.diff(rx) <= 0)), slope_x, 100 * (1 - slope_x), NUMBERS["steps_rms_xcorr"],
            NUMBERS["steps_rms_xcorr"] / NUMBERS["steps_rms_moire"]),
         NUMBERS["steps_rms_xcorr"] > 3 * NUMBERS["steps_rms_moire"] and slope_x < 0.95)
    return steps, rm, rx, direct


def chapter_crlb():
    print("\n3. 雑音の下限(CRLB)と、比べ手との差の内訳")
    n_mc = 12 if REDUCED else 40
    rows = []
    for sg in (0.003, 0.01, 0.03):
        ref0 = MA.moire_overlay_image(SHAPE, PX, PM, PW)
        amp = MA.moire_phase(ref0, None)["amplitude"]
        errs = []
        for k in range(n_mc):
            ref = mark(seed=1000 + k, noise=sg)
            d = 7.0
            errs.append(MA.moire_mark_read(mark(d, seed=5000 + k, noise=sg), ref, PX, PM, PW, "single")["shift_x_nm"] - d)
        sd = float(np.std(errs, ddof=1))
        lb = MA.moire_phase_crlb(sg, amp, SHAPE[0], SHAPE[1], PM, PW)["shift_std_nm"]
        rows.append((sg, sd, lb))
        print("   σ = %.3f: Monte-Carlo %.4f nm、下限 %.4f nm(比 %.2f)" % (sg, sd, lb, sd / lb))
    ratios = [r[1] / r[2] for r in rows]
    NUMBERS["crlb_ratio_min"], NUMBERS["crlb_ratio_max"] = min(ratios), max(ratios)
    gate("Monte-Carlo の標準偏差 / 閉形式の下限 = %.2f〜%.2f(%d 回、0.75〜1.35 —— 下限に乗っている)" % (min(ratios), max(ratios), n_mc),
         all(0.75 <= r <= 1.35 for r in ratios))
    gate("標準偏差は σ に比例(σ を 10 倍で %.1f 倍)" % (rows[2][1] / rows[0][1]), 6.0 < rows[2][1] / rows[0][1] < 15.0)
    # 比べ手の内訳(σ = SIGMA)
    bias, rnd, ph_bar = [], [], []
    ref_bar_clean = bar(noise=0.0)
    amp_bar = MA.moire_phase(ref_bar_clean, P_BAR / PX)["amplitude"]
    for k in range(n_mc):
        d = 40.0
        rb = bar(seed=7000 + k)
        mb = bar(d, seed=8000 + k)
        rnd.append(xcorr_shift_nm(mb, rb) - d)
        a = MA.moire_phase(rb, P_BAR / PX)
        b = MA.moire_phase(mb, P_BAR / PX)
        # ウェハの線だけの像の位相は −2πδ/p_bar(格子の項 exp(i2π(x − δ)/p) を +1/p で復調)
        ph_bar.append(-math.remainder(b["phase_rad"] - a["phase_rad"], 2 * math.pi) / (2 * math.pi) * P_BAR * 1e3 - d)
    slope = []
    for d in (10.0, 20.0, 40.0, 80.0):
        slope.append((xcorr_shift_nm(bar(d, noise=0.0), ref_bar_clean) - d) / d)
    NUMBERS.update({"xcorr_bias_slope": float(np.mean(slope)), "xcorr_rms_40": float(np.sqrt(np.mean(np.square(rnd)))),
                    "xcorr_std_40": float(np.std(rnd, ddof=1)), "bar_phase_std": float(np.std(ph_bar, ddof=1)),
                    "moire_std_sigma": rows[1][1], "amp_bar": amp_bar})
    gate("比べ手の内訳 (a): 放物線補間の偏り = ずれの %.1f %%(雑音なしで 10〜80 nm、どこでも同じ割合)"
         % (100 * NUMBERS["xcorr_bias_slope"]), abs(np.std(slope)) < 0.02 and abs(NUMBERS["xcorr_bias_slope"]) > 0.05)
    gate("比べ手の誤差 RMS(δ = 40 nm)%.2f nm のうち偶然の分は %.2f nm —— 大半は偏り"
         % (NUMBERS["xcorr_rms_40"], NUMBERS["xcorr_std_40"]), NUMBERS["xcorr_std_40"] < NUMBERS["xcorr_rms_40"])
    NUMBERS["random_gain"] = NUMBERS["xcorr_std_40"] / rows[1][1]
    gate("★内訳 (b): 偏りを除いた偶然の分だけなら、モアレ %.3f nm 対 相互相関 %.3f nm で %.1f 倍しか違わない"
         % (rows[1][1], NUMBERS["xcorr_std_40"], NUMBERS["random_gain"]), 1.0 < NUMBERS["random_gain"] < 10.0)
    gate("内訳 (b'): 同じ 20 µm の線を位相(基本波だけ)で読むと %.3f nm —— 縁の高調波まで使う相互相関(%.3f nm)より悪い"
         % (NUMBERS["bar_phase_std"], NUMBERS["xcorr_std_40"]), NUMBERS["bar_phase_std"] > NUMBERS["xcorr_std_40"])
    pred = (P_BAR / PW) * (0.2018 / amp_bar)
    gate("内訳 (c): 線の位相 / モアレ = %.2f 倍 ≈ ピッチの比 %.1f × 振幅の比 %.2f = %.2f(±35 %%)"
         % (NUMBERS["bar_phase_std"] / rows[1][1], P_BAR / PW, 0.2018 / amp_bar, pred),
         abs(NUMBERS["bar_phase_std"] / rows[1][1] / pred - 1) < 0.35)
    NUMBERS["gain_total"] = NUMBERS["xcorr_rms_40"] / rows[1][1]
    gate("同じ雑音・同じ画素数で、誤差 RMS はモアレが相互相関 + 放物線の %.0f 倍(%.1f 桁)小さい —— ★ただしその大半は放物線の偏り"
         % (NUMBERS["gain_total"], math.log10(NUMBERS["gain_total"])), NUMBERS["gain_total"] > 10.0)
    # カメラの分解能を落とす(画素数は同じ): モアレの読みは変わらず、相互相関は悪くなる
    res = []
    for px, blur in ((0.5, 1.5), (2.0, 4.0)):
        em, eb = [], []
        for k in range(24):                                 # 予算に依らず 24 回(標準偏差の比を 6 回で比べると揺れる)
            r = MA.moire_overlay_image(SHAPE, px, PM, PW, 0.0, noise_sigma=SIGMA, seed=9000 + k, blur_sigma_um=blur)
            m = MA.moire_overlay_image(SHAPE, px, PM, PW, 7.0, noise_sigma=SIGMA, seed=9500 + k, blur_sigma_um=blur)
            em.append(MA.moire_mark_read(m, r, px, PM, PW, "single")["shift_x_nm"])
            rb = MA.moire_overlay_image(SHAPE, px, PM, P_BAR, 0.0, noise_sigma=SIGMA, seed=9000 + k, blur_sigma_um=blur, with_mask=False)
            mb = MA.moire_overlay_image(SHAPE, px, PM, P_BAR, 7.0, noise_sigma=SIGMA, seed=9500 + k, blur_sigma_um=blur, with_mask=False)
            eb.append(xcorr_shift_nm(mb, rb, px))
        res.append((float(np.std(em, ddof=1)), float(np.std(eb, ddof=1))))
    NUMBERS.update({"lowres_moire": res[1][0], "lowres_xcorr": res[1][1]})
    gate("カメラを粗くする(画素 0.5 → 2 µm、ぼけ 1.5 → 4 µm、画素数は同じ): モアレの偶然の誤差 %.3f → %.3f nm(縞の周期が"
         "画素より十分長い限り変わらない)、相互相関 %.3f → %.3f nm"
         % (res[0][0], res[1][0], res[0][1], res[1][1]),
         0.6 < res[1][0] / res[0][0] < 1.6 and res[1][1] / res[0][1] > 1.3)
    return rows


def chapter_differential():
    print("\n4. 差動で共通の誤差を消す")
    ref = mark(layout="differential", seed=11)
    d = 25.0
    cases = [("流れ 300 nm", dict(drift_nm=300.0)),
             ("照明の傾き 30 %", dict(illum_gradient=0.3)),
             ("両方", dict(drift_nm=300.0, illum_gradient=0.3))]
    rows = []
    for label, kw in cases:
        r = MA.moire_mark_read(mark(d, seed=12, layout="differential", **kw), ref, PX, PM, PW, "differential")
        rows.append((label, r["single_x_nm"] - d, r["shift_x_nm"] - d, r["drift_x_nm"]))
        print("   %s: 単一の対 %+.3f nm、差動 %+.3f nm、推定した流れ %.1f nm" % (label, rows[-1][1], rows[-1][2], r["drift_x_nm"]))
    # 同じ差動を手で: 2 つの区画の位相を moire_phase で読み、moire_differential_shift に渡す(moire_mark_read の中身)
    P = 1.0 / abs(1 / PM - 1 / PW) / PX
    img = mark(d, seed=12, layout="differential", drift_nm=300.0)
    h, w = img.shape
    pa, pb = (MA.moire_phase(img, P, 1, (4, h // 2 - 4, 4, w - 4))["phase_rad"],
              MA.moire_phase(img, P, 1, (h // 2 + 4, h - 4, 4, w - 4))["phase_rad"])
    ra, rb = (MA.moire_phase(ref, P, 1, (4, h // 2 - 4, 4, w - 4))["phase_rad"],
              MA.moire_phase(ref, P, 1, (h // 2 + 4, h - 4, 4, w - 4))["phase_rad"])
    by_hand = MA.moire_differential_shift(pa, pb, ra, rb, PM, PW)
    gate("区画の位相を moire_phase で読み moire_differential_shift に渡すと %.4f nm(moire_mark_read と 1e-9 で同じ)"
         % by_hand["shift_nm"], abs(by_hand["shift_nm"] - (rows[0][2] + d)) < 1e-9)
    NUMBERS["single_err_drift"] = rows[0][1]
    NUMBERS["diff_err_drift"] = rows[2][2]
    gate("流れ 300 nm: 単一の対は 300/M = %.2f nm 狂う(実測 %+.2f)" % (300.0 / 50.0, rows[0][1]), abs(abs(rows[0][1]) - 6.0) < 0.5)
    gate("差動はどの場合も 0.3 nm 以内(最大 %.3f nm)。流れも %.1f nm と読めるが、流れは M 倍されないので 50 倍粗い(±20 nm)"
         % (max(abs(r[2]) for r in rows), rows[0][3]),
         max(abs(r[2]) for r in rows) < 0.3 and abs(rows[0][3] - 300.0) < 20.0)
    # カメラの倍率の誤り: 読み手は pixel_um を 2 % 大きく思い込んでいる(= 実際の画素は 0.5 µm)
    rm = MA.moire_mark_read(mark(d, seed=12, layout="differential"), ref, PX * 1.02, PM, PW, "differential")
    rb = xcorr_shift_nm(bar(d, seed=12), bar(seed=11), PX * 1.02)
    rb0 = xcorr_shift_nm(bar(d, seed=12), bar(seed=11), PX)
    NUMBERS["scale_err_moire"] = rm["shift_x_nm"] - d
    NUMBERS["scale_ratio_xcorr"] = rb / rb0
    gate("カメラの倍率を 2 %% 間違えても差動の読みは %+.3f nm(換算はピッチだけで決まる)、相互相関は %.3f 倍に狂う"
         % (NUMBERS["scale_err_moire"], NUMBERS["scale_ratio_xcorr"]),
         abs(NUMBERS["scale_err_moire"]) < 0.3 and abs(NUMBERS["scale_ratio_xcorr"] - 1.02) < 1e-9)
    # 2 次元の 4 象限
    q0 = mark(layout="quad", seed=21)
    q1 = mark((12.0, -25.0), layout="quad", seed=22, drift_nm=(200.0, -100.0), illum_gradient=0.2)
    q = MA.moire_mark_read(q1, q0, PX, PM, PW, "quad")
    NUMBERS.update({"quad_dx": q["shift_x_nm"], "quad_dy": q["shift_y_nm"]})
    gate("4 象限のマーク: (dx, dy) = (%.2f, %.2f) nm(真値 (12, −25)、流れ (200, −100) nm と照明の傾き込みで 0.3 nm 以内)"
         % (q["shift_x_nm"], q["shift_y_nm"]), abs(q["shift_x_nm"] - 12.0) < 0.3 and abs(q["shift_y_nm"] + 25.0) < 0.3)
    # Takeda の FFT 法: ロックインと同じ位相、位相の地図の傾きから倍率の誤りが見える
    img = mark(d, seed=12, layout="single", noise=0.0)
    P = 1.0 / abs(1 / PM - 1 / PW) / PX
    lk = MA.moire_phase(img, P * 1.02)
    ft = MA.moire_phase(img, P * 1.02, method="fft")
    NUMBERS["fft_period_ratio"] = ft["period_fit_px"] / (P * 1.02)
    gate("Takeda の FFT 法: 位相の地図の傾きは、思い込んだ周期の %.4f 倍(本当は 1/1.02 = 0.9804)—— 倍率の誤りが見える"
         % NUMBERS["fft_period_ratio"], abs(NUMBERS["fft_period_ratio"] - 1 / 1.02) < 2e-3,
         "ロックインとの位相差 %.1e rad" % abs(math.remainder(lk["phase_rad"] - ft["phase_rad"], 2 * math.pi)))
    return rows, q0, q1


def chapter_ambiguity():
    print("\n5. 折り返し(1 周期の不定性)と、粗い読みでの次数の決定")
    true = np.linspace(0.0, 5000.0, 26 if REDUCED else 51)
    ref = mark(layout="differential", seed=31)
    ref_b = bar(seed=31)
    single, diff, absolute = [], [], []
    for i, d in enumerate(true):
        img = mark(d, layout="differential", seed=400 + i)
        r = MA.moire_mark_read(img, ref, PX, PM, PW, "differential")
        single.append(r["single_x_nm"])
        diff.append(r["shift_x_nm"])
        coarse = xcorr_shift_nm(bar(d, seed=400 + i), ref_b)
        # 差動の位相差を、粗い読みで次数づけする(差動の捕捉範囲 1.01 µm の半分 = 505 nm より粗い読みが良ければよい)
        amb = r["ambiguity_nm"]
        absolute.append(r["shift_x_nm"] + amb * round((coarse - r["shift_x_nm"]) / amb))
    single, diff, absolute = map(np.array, (single, diff, absolute))
    same = MA.moire_mark_read(mark(300.0, seed=1, noise=0.0), mark(noise=0.0), PX, PM, PW, "single")["shift_x_nm"]
    same2 = MA.moire_mark_read(mark(300.0 + PW * 1e3, seed=1, noise=0.0), mark(noise=0.0), PX, PM, PW, "single")["shift_x_nm"]
    gate("δ = 300 nm と 300 + 2040 nm は同じ読み(%.3f / %.3f nm)—— 単一の対の捕捉範囲 = p_w" % (same, same2),
         abs(same - same2) < 0.01 and abs(same - 300.0) < 0.05)
    gate("差動の読みは 1009.9 nm ごとに折り返す(5 µm までの鋸歯の最大 %.0f nm)" % np.max(np.abs(diff)), np.max(np.abs(diff)) <= 505.0 + 1.0)
    err = absolute - true
    NUMBERS["abs_rms"] = float(np.sqrt(np.mean(err ** 2)))
    gate("粗い相互相関で次数を決めると 0〜5 µm を折り返さずに読む(誤差 RMS %.3f nm、%d 点すべて)" % (NUMBERS["abs_rms"], len(true)),
         NUMBERS["abs_rms"] < 0.3)
    # 次数の決定を ``fringe.absolute_phase`` で(単一の対)
    P = 1.0 / abs(1 / PM - 1 / PW) / PX
    pa = MA.moire_phase(mark(seed=4), P)["phase_rad"]
    pb = MA.moire_phase(mark(2340.0, seed=3), P)["phase_rad"]
    wrapped = MA.moire_phase_to_shift(pb, pa, PM, PW)
    a = MA.moire_phase_to_shift(pb, pa, PM, PW, coarse_shift_nm=2300.0)
    gate("``fringe.absolute_phase`` で次数 %d を決め、%.1f nm と折り返した読みを %.2f nm に戻す(真値 2340、粗い値 2300 nm)"
         % (a["order"], wrapped["shift_nm"], a["shift_nm"]),
         a["order"] == 1 and abs(a["shift_nm"] - 2340.0) < 0.5 and abs(wrapped["shift_nm"] - 300.0) < 0.5)
    return true, single, diff, absolute


def chapter_talbot():
    print("\n6. 近接ギャップの Talbot 効果")
    zt = MA.moire_talbot_gap(PM, 0.55, 0.0)["talbot_length_um"]
    half = MA.moire_talbot_gap(PM, 0.55, zt / 2)
    full = MA.moire_talbot_gap(PM, 0.55, zt)
    NUMBERS.update({"talbot_um": zt, "contrast_half": half["contrast_ratio"], "contrast_full": full["contrast_ratio"]})
    gate("Talbot 長 2p²/λ = %.2f µm で縞の振幅が戻る(比 %.4f、近軸でない厳密な伝搬なので 1 %% 以内のずれ)" % (zt, full["contrast_ratio"]),
         abs(full["contrast_ratio"] - 1) < 0.01)
    gate("その半分 %.2f µm で符号が反転(比 %.4f、位相 π = 縞が半周期ずれる)" % (zt / 2, half["contrast_ratio"]),
         half["contrast_ratio"] < -0.99 and abs(half["phase_rad"] - math.pi) < 1e-9)
    gaps = np.linspace(0.0, 32.0, 65 if not REDUCED else 33)
    ca = np.array([MA.moire_talbot_gap(PM, 0.55, g)["contrast_ratio"] for g in gaps])
    cb = np.array([MA.moire_talbot_gap(PW, 0.55, g)["contrast_ratio"] for g in gaps])
    # 像の上で: ギャップを入れた像の縞の振幅は比どおり
    g = 4.0
    amp0 = MA.moire_phase(mark(noise=0.0), None)["amplitude"]
    ampg = MA.moire_phase(mark(noise=0.0, gap_um=g, wavelength_um=0.55), None)["amplitude"]
    cg = MA.moire_talbot_gap(PM, 0.55, g)["contrast_ratio"]
    gate("像の縞の振幅はギャップ %.0f µm で %.3f 倍(``moire_talbot_gap`` の |比| %.3f と 2 %% 以内)" % (g, ampg / amp0, abs(cg)),
         abs(ampg / amp0 / abs(cg) - 1) < 0.02)
    # 基準像と測定像の間でギャップが反転を跨ぐと、読みが半周期跳ぶ
    r_ref = mark(noise=0.0, gap_um=2.0, wavelength_um=0.55)
    r_same = MA.moire_mark_read(mark(30.0, noise=0.0, gap_um=2.0, wavelength_um=0.55), r_ref, PX, PM, PW, "single")["shift_x_nm"]
    r_flip = MA.moire_mark_read(mark(30.0, noise=0.0, gap_um=6.0, wavelength_um=0.55), r_ref, PX, PM, PW, "single")["shift_x_nm"]
    NUMBERS.update({"gap_same": r_same, "gap_flip": r_flip})
    gate("ギャップが同じなら読みは正しい(%.2f nm)、2 → 6 µm と反転を跨ぐと %.0f nm(半周期 = p_w/2 = 1020 nm 跳ぶ)"
         % (r_same, r_flip), abs(r_same - 30.0) < 0.1 and abs(abs(r_flip - 30.0) - PW * 500.0) < 1.0)
    return gaps, ca, cb, zt


def _dark_fringe_col(img, near, half):
    """縞の暗い所(列の平均の最小)を near ± half の窓で探し、放物線で画素より細かく。"""
    prof = img.mean(axis=0)
    lo, hi = max(1, int(near - half)), min(prof.size - 2, int(near + half))
    k = lo + int(np.argmin(prof[lo:hi + 1]))
    a, b, c = prof[k - 1], prof[k], prof[k + 1]
    den = a - 2 * b + c
    return k + (0.5 * (a - c) / den if den != 0 else 0.0)


def differential_panel(delta_nm=400.0, shape=(124, 1024), sep=8):
    """差動のマークを 2 段(上 = 対 A、下 = 対 B)に分け、同じずれで縞が**逆向き**に流れるのを矢印で示す(RGB)。

    各段は ずれ δ のときの像。破線 = ずれ 0 のときの暗い縞の位置、矢印 = その縞が δ で動いた先。
    """
    import fullseye as fs
    import imagedraw
    P = PM * PW / abs(PW - PM) / PX
    bands, labels = [], []
    for pair, (pm, pw) in (("A", (PM, PW)), ("B", (PW, PM))):
        z = MA.moire_overlay_image(shape, PX, pm, pw, 0.0)
        m = MA.moire_overlay_image(shape, PX, pm, pw, delta_nm)
        c0 = _dark_fringe_col(z, shape[1] / 2, P / 2)
        mm = MA.moire_magnification(pm, pw)
        expect = c0 + mm["fringe_direction"] * mm["magnification"] * delta_nm * 1e-3 / PX
        c1 = _dark_fringe_col(m, expect, P / 4)
        rgb = np.repeat(np.clip(m / 0.5, 0, 1)[..., None], 3, axis=2)
        h = shape[0]
        rgb = np.asarray(fs.draw_line(rgb, (c0, 4), (c0, h - 5), color=(0.0, 0.45, 0.70), width=2,
                                      style=imagedraw.DrawStyle(line_style="dashed")))
        rgb = np.asarray(fs.draw_line(rgb, (c1, 4), (c1, h - 5), color=(0.84, 0.37, 0.0), width=2))
        rgb = np.asarray(fs.arrow(rgb, (c0, h * 0.62), (c1, h * 0.62), color="wrong", width=4, head_len=16.0,
                                  head_width=14.0))
        lab = "対 %s(マスク %.2f / ウェハ %.2f µm): 縞は %s %.1f µm" % (
            pair, pm, pw, "←" if c1 < c0 else "→", abs(c1 - c0) * PX)
        rgb = np.asarray(fs.text_box(rgb, lab, (8, 6), anchor="lt", font_size=13))
        bands.append(rgb)
        labels.append((pair, (c1 - c0) * PX))
    line = np.ones((sep, shape[1], 3))
    line[sep // 2 - 1:sep // 2 + 1] = (0.85, 0.37, 0.0)       # A と B の境目(細い橙の線)
    return np.vstack([bands[0], line, bands[1]]), labels


def differential_bars(rows):
    """条件ごとに「単一の対」と「差動」の |誤差| を横並びの棒で(値を棒に印字)。"""
    import fullseye as fs
    w, h = 720, 400
    img = np.ones((h, w, 3))
    names = [r[0] for r in rows]
    single = np.array([abs(r[1]) for r in rows])
    diff = np.array([abs(r[2]) for r in rows])
    top = float(np.ceil(single.max() * 1.6))                 # 上に凡例の置き場を空ける(棒と値に重ねない)
    rect = (72, 56, w - 96, h - 140)
    ax = fs.axes_transform(rect, (-0.5, len(rows) - 0.5), (0.0, top))
    yt = fs.nice_ticks(0.0, top, 5)
    img = np.asarray(fs.grid_lines(img, ax, xticks=[], yticks=yt, alpha=0.25))
    img = np.asarray(fs.axes_frame(img, ax, width=1))
    img = np.asarray(fs.ticks(img, ax, xticks=[], yticks=yt, tick_len=5, font_size=11))
    xs = np.arange(len(rows), dtype=float)
    for off, vals, col, idx in ((-0.19, single, "wrong", 1), (0.19, diff, "emphasis", 2)):
        img = np.asarray(fs.plot_series(img, ax, xs + off, vals, kind="bar", color=col, baseline=0.0,
                                        bar_width=0.33))
        for x, v, r in zip(xs + off, vals, rows):
            px, py = fs.data_to_pixel(ax, x, v)
            img = np.asarray(fs.text_box(img, "%+.2f nm" % r[idx], (float(px), float(py) - 4), anchor="cb",
                                         font_size=12))
    for x, nm in zip(xs, names):
        px, _ = fs.data_to_pixel(ax, x, 0.0)
        img = np.asarray(fs.text_box(img, nm, (float(px), rect[1] + rect[3] + 8), anchor="ct", font_size=12))
    img = np.asarray(fs.legend_box(img, [("wrong", "単一の対(A だけ)"), ("emphasis", "差動の 2 対")],
                                   (rect[0] + rect[2] - 6, rect[1] + 6), anchor="rt", markers=True,
                                   font_size=12, swatch=12, pad=6))
    img = np.asarray(fs.text_box(img, "差動で共通の誤差が消える(単一 %.1f nm → 差動 %.2f nm)" % (rows[0][1], rows[0][2]),
                                 (10, 8), anchor="lt", font_size=13))
    img = np.asarray(fs.text_box(img, "|誤差| [nm](棒の上の数は符号つきの誤差)", (10, h - 10), anchor="lb",
                                 font_size=11))
    return img


def make_figures(mw, steps_data, crlb_rows, diff_data, amb, tal):
    steps, rm, rx, direct = steps_data
    clean = mark(noise=0.0)
    single = mark()
    q0, q1 = diff_data[1], diff_data[2]
    dpanel, dlabels = differential_panel(600.0)
    NUMBERS["panel_shift_a_um"], NUMBERS["panel_shift_b_um"] = dlabels[0][1], dlabels[1][1]
    figs.save_grid("marks", [direct, MA.moire_overlay_image(SHAPE, PX, PM, PW, 0.0, with_mask=False, noise_sigma=SIGMA),
                             single, dpanel],
                   captions=["比べ手: 20 µm の線(直接の像)", "ウェハの 2.04 µm の格子だけ(ぼけで消え、平均 0.5 の灰色)",
                             "マスク 2.00 + ウェハ 2.04 µm(モアレ 102 µm)",
                             "差動: 上 A・下 B、ずれ 600 nm で縞は逆向きに流れる"],
                   gray=[True, True, True, False], vrange=[(0.0, 1.0), (0.0, 1.0), (0.0, 0.5), None],
                   title="見えない格子 2 枚を重ねると、縞が現れる",
                   caption="(a)〜(c) は同じカメラ(画素 0.5 µm、ぼけ σ 1.5 µm)と同じ雑音(σ 0.01)。2 µm の格子はカメラでは消えるが、"
                           "2 枚の積の差の周波数(1/2.00 − 1/2.04 /µm)だけが残る。(d) は雑音なしの差動のマーク: 橙の線が A と B の境目、"
                           "青の破線 = ずれ 0 の暗い縞、橙の実線と矢印 = ウェハを 600 nm 動かした後の同じ縞(A は %+.1f µm、B は %+.1f µm)。"
                           "像全体が流れると両方が同じ向きに動くので、差を取ればずれだけが残る。"
                           % (NUMBERS["panel_shift_a_um"], NUMBERS["panel_shift_b_um"]))
    figs.save_plot("one_nm_steps", [("真値", steps, steps), ("モアレの位相", steps, rm), ("相互相関 + 放物線", steps, rx)],
                   xlabel="与えたずれ [nm]", ylabel="読んだずれ [nm]", styles=["dashed", None, None],
                   colors=["reference", "emphasis", "wrong"], kinds=["line", "line", "line"],
                   title="1 nm ずつ: モアレは誤差 %.2f nm、相互相関は %.1f nm" % (NUMBERS["steps_rms_moire"], NUMBERS["steps_rms_xcorr"]),
                   caption="同じ雑音・同じ画素数。相互相関は 20 µm の線のマークで、放物線補間の偏り(ずれに比例)と雑音が乗る。")
    # GIF: ずれを 51 nm ずつ 40 コマで p_w(2.04 µm)ぶん動かす —— 縞は 1 周期(102 µm)流れて元に戻る
    n = 24 if REDUCED else 40
    frames = []
    for k in range(n):
        d = PW * 1e3 * k / n
        m = MA.moire_overlay_image((96, 512), PX, PM, PW, d)
        b = MA.moire_overlay_image((96, 512), PX, PM, P_BAR, d, with_mask=False) * 0.25 / 0.5
        frames.append(np.vstack([b, np.full((8, 512), 0.0), m]))
    figs.save_gif("fringe_flow", frames, fps=10.0,
                  caption="上: 20 µm の線を直接撮った像、下: モアレ。ずれを 1 コマ %.0f nm ずつ、計 2.04 µm(ウェハのピッチ 1 つ)動かす。"
                          "線は 0.1 画素ずつしか動かず見えないが、縞は 1 コマ 2.55 µm(5 画素)流れ、1 周して元に戻る(= 折り返し)。"
                          % (PW * 1e3 / n))
    sg = np.array([r[0] for r in crlb_rows])
    figs.save_plot("crlb", [("Monte-Carlo の標準偏差", sg, np.array([r[1] for r in crlb_rows])),
                            ("下限(moire_phase_crlb)", sg, np.array([r[2] for r in crlb_rows]))],
                   xlabel="雑音 σ(平均の強度 0.25)", ylabel="ずれの標準偏差 [nm]", kinds=["scatter", "line"],
                   colors=["emphasis", "reference"], styles=[None, "dashed"],
                   title="モアレの読みは雑音の下限に乗る(比 %.2f〜%.2f)" % (NUMBERS["crlb_ratio_min"], NUMBERS["crlb_ratio_max"]),
                   caption="下限 = Rife & Boorstyn の位相の下限 × Hann の係数 1.5 × 基準像の雑音で 2 倍、を p/(2π) で nm に。")
    figs.save("differential", differential_bars(diff_data[0]),
              caption="逆向きのピッチ差の 2 対は、ずれでは逆に、マーク全体の流れでは同じ向きに縞が動く。差を取ると流れが消える。"
                      "照明の傾きは単一の対でも小さい(0.6 nm)が、それも差動で 0.02 nm に。")
    figs.save_grid("quad_mark", [q0[::2, ::2], q1[::2, ::2]], captions=["基準(ずれ 0)", "(dx, dy) = (12, −25) nm、流れ (200, −100) nm"],
                   gray=True, vrange=(0.0, 0.5), title="2 次元の 4 象限のマーク(2 画素ごとに表示)",
                   caption="左上 A_x、右上 B_x、左下 A_y、右下 B_y。読み = (%.2f, %.2f) nm。" % (NUMBERS["quad_dx"], NUMBERS["quad_dy"]))
    true, single, diffr, absolute = amb
    figs.save_plot("ambiguity", [("真値", true, true), ("単一の対(2.04 µm で折り返す)", true, single),
                                 ("差動(1.01 µm で折り返す)", true, diffr), ("粗い相互相関で次数を決めた差動", true, absolute)],
                   xlabel="与えたずれ [nm]", ylabel="読んだずれ [nm]", styles=["dashed", None, None, "dotted"],
                   kinds=["line", "scatter", "scatter", "line"],
                   colors=["reference", "wrong", "neutral", "emphasis"],
                   title="縞の位相は 1 周期で折り返す —— 粗い読みで次数を決める",
                   caption="印刷の版ずれと同じ不定性。差動は捕捉範囲が p_m p_w/(p_m+p_w) と半分になる。")
    gaps, ca, cb, zt = tal
    figs.save_plot("talbot_gap", [("マスク 2.00 µm", gaps, ca), ("マスク 2.04 µm", gaps, cb), ("0", gaps, 0 * gaps)],
                   xlabel="マスクとウェハのギャップ [µm](λ = 0.55 µm)", ylabel="縞の振幅(接触時との比、符号つき)",
                   styles=[None, None, "dashed"], colors=["emphasis", "neutral", "reference"],
                   title="Talbot 効果: 振幅は 2p²/λ = %.1f µm で戻り、その半分で符号が反転" % zt,
                   caption="符号が反転すると縞は半周期ずれる。基準像と測定像のあいだに反転を跨ぐと読みが p/2 跳ぶ。2 対のピッチは Talbot 長が違うので、"
                           "差動でもギャップの影響は消えきらない。")


def main():
    t0 = time.time()
    print("PoC モアレで位置合わせ(予算 %s)" % ("reduced" if REDUCED else "full"))
    mw = chapter_magnification()
    steps = chapter_steps()
    crlb = chapter_crlb()
    diff = chapter_differential()
    amb = chapter_ambiguity()
    tal = chapter_talbot()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(mw, steps, crlb, diff, amb, tal)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
