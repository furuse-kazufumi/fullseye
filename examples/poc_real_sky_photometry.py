# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写の深宇宙画像に既知の星を仕込んで測る —— 汚染は測定値と信頼度を同じ向きに嘘つかせる。

測光の合成 PoC(``poc_astro_photometry``)は、平坦な背景に星を置いて
「開口が拾う割合は ``1 - exp(-r²/2σ²)``」が厳密に出ることまで確かめました。
実写の空は**平坦ではありません**。ここでは Hubble Deep Field(NASA/STScI、
public domain)の**本物の背景**に、フラックスが分かっているガウシアン星を
仕込んで回収します。真値は自分で入れたので確実、背景だけが本物 ——
**合成では作れない要因だけを 1 つ入れ替える**設計です。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **実写の空は正規分布ではない**。頑健なばらつき(MAD 由来)は 1,474 e- なのに
   素の標準偏差は 6,698 e- —— **4.54 倍**。裾を作っているのは雑音ではなく
   分解できていない銀河。``std`` をノイズだと思って検出限界を引くと、
   **4.5 倍甘い数字**を出す。
2. **「背景」は 1 つの数字ではない**。64x64 のタイル 195 枚で背景の中央値は
   3,176 〜 8,448 e- に散る。大域の中央値 1 つで引くと、場所によって
   最大 5,272 e-(= 3.6σ)の系統誤差が残る。
3. ★★**空だと思った場所でも、開口には一定量が混入する**。16 bit 満量を
   65535 e- と決めて電子に直し、σ=1.5 px の星を仕込むと、局所背景が下位 30 %
   の「空」でも回収比は F=2,000 e- で **4.38 倍**、5,000 で 2.35、10,000 で
   1.68、30,000 で 1.22、100,000 で 1.058。★これは倍率ではなく**一定量の
   足し算**で、``1 + C/(F·frac)`` の形に乗る(C は開口 1 つあたりの混入量)。
   実測 C は **6,677 e-**(背景 3,504 e-/px x 実効 63.6 px のわずか 3.0 %)。
   このモデルは 5 点すべてで**最大ずれ 0.9 %** で当たる。★さらに「偏りが
   10 % を切るのは F = C/(0.10·frac) = **67,521 e-** から」と**先に予測して
   から**そこで測ると、回収比 1.086(予測 1.100、ずれ 1.2 %)。
   **汚染の量が分かれば、どこまで暗い星なら信じてよいかが計算できる**。
4. ★★**混んだ場所では桁が変わる**。上位 2 % の明るい領域に置くと回収比は
   341 倍(F=2,000)〜 7.80 倍(F=100,000)。環の中央値は隣の銀河を
   引ききれない —— 中央値は「外れ値に強い」のであって、
   **視野の半分が汚染されていたら中央値こそが汚染**。
5. ★★**信頼度も同じ向きに嘘をつく**。F=2,000 の「空」で op が返す SNR の
   中央値は 19.2。同じ背景から閉形式(CCD 方程式)で計算した予測は **4.2**。
   SNR は**測ったフラックス**から作られるので、混入で分子が膨らむと
   S/N まで一緒に膨らむ。**「よく測れている」と言っているのは、
   よく汚染されているから**。だから S/N を採否の門にすると、
   汚染された測定ほど通る。
6. **ゼロ点**。背景を引かずに開口の和を取ると、F=100,000 e- でも回収比が
   **3.3 倍**(背景 3,504 e-/px x 実効 63.6 px = 222,900 e- がそのまま乗る)。
   環による背景引きは効いている —— 効いてなお 3 節の混入が残る、という順序。
7. **飽和は 3 画素しかない**。実写だから飽和で壊れる、という筋書きは
   この画像では成り立たない(0.0003 %)。**思い込みは毎回数える**。

EXTEND: 自前の撮影に差し替えるなら :func:`load_sky` を置き換えます。電子への
換算 :data:`FULL_WELL_E` は撮像系のゲインに合わせてください —— ここを 1.0 の
ままにすると 5 節の SNR は**単位が合わないまま数字だけ出ます**(``aperture_photometry``
は落ちません)。真値の星を仕込む方式なので、真値が無い実写でも 1・2・6 節
(背景の性質とゼロ点)はそのまま測れます。

出典: Hubble Deep Field(NASA/STScI、public domain)、``scikit-image`` 同梱。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import realdata                                                  # noqa: E402

#: 点像の広がり[px]と開口・環の半径[px]
PSF_SIGMA, R_APER, R_IN, R_OUT = 1.5, 4.5, 8.0, 12.0

#: 開口が拾う割合(閉形式)。r = 3σ なので 1 - exp(-4.5) = 0.9889
APER_FRAC = 1.0 - np.exp(-R_APER ** 2 / (2 * PSF_SIGMA ** 2))

#: 画素値 1.0 を何電子と見なすか。**ここを 1.0 にすると SNR の単位が壊れる**
FULL_WELL_E = 65535.0

#: 仕込む星の数(空 / 混雑 それぞれ)
N_PER_GROUP = 40

#: 仕込むフラックス[e-]
FLUXES = (2e3, 5e3, 1e4, 3e4, 1e5)


def load_sky():
    """実写の深宇宙画像を**電子**に直して返す。無ければ fail-closed。"""
    return realdata.load_gray("hubble_deep_field") * FULL_WELL_E


def robust_sigma(a):
    """MAD 由来の頑健なばらつき(外れ値 = 天体に引きずられない)。"""
    return float(1.4826 * np.median(np.abs(a - np.median(a))))


def pick_positions(sky, rng):
    """局所背景の下位 30 %(空)と上位 2 %(混雑)から同数ずつ選ぶ。"""
    H, W = sky.shape
    loc = ndi.median_filter(sky, size=25)
    inner = loc[20:H - 20, 20:W - 20]
    lo, hi = np.quantile(loc, 0.30), np.quantile(loc, 0.98)
    empty = np.argwhere(inner <= lo) + 20
    crowd = np.argwhere(inner >= hi) + 20
    sel_e = empty[rng.choice(len(empty), N_PER_GROUP, replace=False)]
    sel_c = crowd[rng.choice(len(crowd), N_PER_GROUP, replace=False)]
    return sel_e, sel_c, float(lo), float(hi)


def inject(sky, centres, flux):
    """ガウシアン星を**局所の窓だけ**に足す(全画面の格子を毎回作らない)。"""
    out = sky.copy()
    rad = int(np.ceil(6 * PSF_SIGMA))
    dy, dx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
    kern = flux * np.exp(-(dy ** 2 + dx ** 2) / (2 * PSF_SIGMA ** 2)) \
        / (2 * np.pi * PSF_SIGMA ** 2)
    for r, c in centres:
        r, c = int(r), int(c)
        out[r - rad:r + rad + 1, c - rad:c + rad + 1] += kern
    return out


def measure(scene, centres):
    """``aperture_photometry`` で測る。返すのは ``(flux, snr)``。"""
    res = fs.aperture_photometry(
        scene, [(float(r), float(c)) for r, c in centres],
        r_aperture=R_APER, r_inner=R_IN, r_outer=R_OUT, gain=1.0)
    return (np.array([d["flux"] for d in res], np.float64),
            np.array([d["snr"] for d in res], np.float64))


def main() -> None:
    t0 = time.perf_counter()
    rng = np.random.default_rng(11)
    sky = load_sky()
    H, W = sky.shape
    bg = float(np.median(sky))
    sig = robust_sigma(sky)
    area = np.pi * R_APER ** 2

    print("実写の深宇宙画像(Hubble Deep Field、%dx%d)を %.0f e- 満量で電子に直す"
          % (H, W, FULL_WELL_E))
    print("  背景 %.1f e-/px  開口の実効画素 %.1f  開口が拾う理論比 %.4f"
          % (bg, area, APER_FRAC))

    # --- 1 ---------------------------------------------------------------- #
    std = float(sky.std())
    print("\n1. 実写の空は正規分布ではない")
    print("   頑健なばらつき(MAD 由来)%.1f e-  /  素の標準偏差 %.1f e-  = %.2f 倍"
          % (sig, std, std / sig))
    assert std > 3.0 * sig, (std, sig)

    # --- 2 ---------------------------------------------------------------- #
    bs = 64
    tiles = [sky[r:r + bs, c:c + bs]
             for r in range(0, H - bs, bs) for c in range(0, W - bs, bs)]
    meds = np.array([np.median(t) for t in tiles])
    spread = float(meds.max() - meds.min())
    print("\n2. 「背景」は 1 つの数字ではない")
    print("   %dx%d タイル %d 枚の背景中央値 %.1f 〜 %.1f e-(散らばり %.1f)"
          % (bs, bs, len(meds), meds.min(), meds.max(), meds.std()))
    print("   大域の中央値 1 つで引くと最大 %.1f e-(= %.1f σ)の系統誤差"
          % (spread, spread / sig))
    assert spread > 2.0 * sig, (spread, sig)

    # --- 3, 4, 5 ----------------------------------------------------------- #
    sel_e, sel_c, lo, hi = pick_positions(sky, rng)
    allc = np.vstack([sel_e, sel_c])
    print("\n3-5. 既知の星を仕込んで回収する(空 %d 個 / 混雑 %d 個)"
          % (N_PER_GROUP, N_PER_GROUP))
    print("     空 = 局所背景 <= %.0f e-、混雑 = >= %.0f e-" % (lo, hi))
    print("     真F[e-]   回収比 空   回収比 混雑    SNR 空   閉形式の予測 SNR")
    rows = []
    for F in FLUXES:
        scene = inject(sky, allc, F)
        flux, snr = measure(scene, allc)
        r_e = float(np.median(flux[:N_PER_GROUP] / (F * APER_FRAC)))
        r_c = float(np.median(flux[N_PER_GROUP:] / (F * APER_FRAC)))
        s_e = float(np.median(snr[:N_PER_GROUP]))
        pred = float(F * APER_FRAC / np.sqrt(F * APER_FRAC + area * bg))
        rows.append((F, r_e, r_c, s_e, pred))
        print("     %8.0f  %+9.3f   %+10.3f   %7.1f   %11.1f"
              % (F, r_e, r_c, s_e, pred))

    # 一定量の混入モデル: 回収比 = 1 + C/(F*frac)。C を当てはめて予測を確かめる
    Fs = np.array([r[0] for r in rows])
    ratio = np.array([r[1] for r in rows])
    C = float(np.median((ratio - 1.0) * Fs * APER_FRAC))
    pred_ratio = 1.0 + C / (Fs * APER_FRAC)
    err = np.abs(pred_ratio - ratio) / ratio
    print("     一定量の混入モデル: 開口 1 つあたり C = %.0f e-"
          "(背景 %.1f e-/px x 実効 %.1f px の %.1f %%)"
          % (C, bg, area, 100 * C / (bg * area)))
    print("     予測 " + " / ".join("%.3f" % p for p in pred_ratio))
    print("     実測 " + " / ".join("%.3f" % p for p in ratio)
          + "   最大ずれ %.1f %%" % (100 * err.max()))
    assert ratio[0] > 3.0 and ratio[-1] > 1.02, ratio
    assert err.max() < 0.25, (pred_ratio, ratio, err)
    crowd = np.array([r[2] for r in rows])
    assert crowd[0] > 50.0 and crowd[-1] > 3.0, crowd
    meas_snr = np.array([r[3] for r in rows])
    pred_snr = np.array([r[4] for r in rows])
    assert meas_snr[0] > 3.0 * pred_snr[0], (meas_snr[0], pred_snr[0])

    # 崖: 空領域の偏りが 10 % を切るフラックスを、C から先に予測してから測る
    f_pred = C / (0.10 * APER_FRAC)
    scene = inject(sky, sel_e, f_pred)
    flux, _snr = measure(scene, sel_e)
    r_at = float(np.median(flux / (f_pred * APER_FRAC)))
    print("\n   崖の予測: 偏りが 10 %% を切るのは F = C/(0.10 x frac) = %.0f e- から。"
          % f_pred)
    print("   そこで実測すると回収比 %.3f(予測 1.100、ずれ %.1f %%)"
          % (r_at, 100 * abs(r_at - 1.10) / 1.10))
    assert abs(r_at - 1.10) < 0.20 * 1.10, r_at

    # --- 6 ---------------------------------------------------------------- #
    F = FLUXES[-1]
    scene = inject(sky, sel_e, F)
    raw = []
    for r, c in sel_e:
        r, c = int(r), int(c)
        yy, xx = np.mgrid[r - 5:r + 6, c - 5:c + 6]
        m = (yy - r) ** 2 + (xx - c) ** 2 <= R_APER ** 2
        raw.append(scene[r - 5:r + 6, c - 5:c + 6][m].sum())
    r_raw = float(np.median(np.asarray(raw) / (F * APER_FRAC)))
    print("\n6. ゼロ点(背景を引かない開口の和)")
    print("   回収比 %.1f 倍(背景 %.1f e-/px x 実効 %.1f px = %.0f e- が乗る)"
          % (r_raw, bg, area, bg * area))
    assert r_raw > 2.0, r_raw

    # --- 7 ---------------------------------------------------------------- #
    sat = int((sky >= 0.999 * FULL_WELL_E).sum())
    print("\n7. 飽和は %d 画素(%.4f %%)—— この画像では飽和は問題にならない"
          % (sat, 100.0 * sat / sky.size))
    assert sat < 0.001 * sky.size, sat

    # --- 図 ---------------------------------------------------------------- #
    def show(a):
        v = np.clip(np.asarray(a, np.float64) / FULL_WELL_E, 0, 1)
        return v

    scene_hi = inject(sky, allc, FLUXES[-1])
    figs.save_grid(
        "scene",
        [show(sky), show(scene_hi),
         show(ndi.median_filter(sky, size=25))],
        ["実写(Hubble Deep Field)", "既知の星 %d 個を仕込んだ" % len(allc),
         "局所背景(25 px 中央値)"],
        title="背景だけ本物、星は自分で仕込む", ncols=3,
        caption="実写の空は平坦ではない。頑健 σ %.0f e- に対し素の std は %.0f e-。"
                % (sig, std))

    figs.save_plot(
        "recovery",
        [("空(局所背景 下位 30 %)", list(Fs), list(ratio)),
         ("混雑(上位 2 %)", list(Fs), [r[2] for r in rows]),
         ("一定量の混入モデル", list(Fs), list(pred_ratio))],
        xlabel="仕込んだフラックス [e-]", ylabel="回収比(真値 = 1.0)",
        title="暗い星ほど明るく測れる(混入は一定量だから)",
        caption="開口 1 つあたり C = %.0f e- の足し算として説明できる。" % C)

    figs.save_plot(
        "snr_lies",
        [("op が返す SNR", list(Fs), list(meas_snr)),
         ("同じ背景からの閉形式", list(Fs), list(pred_snr))],
        xlabel="仕込んだフラックス [e-]", ylabel="S/N",
        title="信頼度も同じ向きに嘘をつく",
        caption="SNR は測ったフラックスから作るので、混入で分子が膨らむと "
                "S/N も膨らむ(F=%.0f で %.1f 対 %.1f)。"
                % (Fs[0], meas_snr[0], pred_snr[0]))

    figs.save_table(
        "recovery_table",
        ["真F [e-]", "空", "混雑", "SNR 空", "予測 SNR"],
        [["%.0f" % f, "%.3f" % a, "%.2f" % b, "%.1f" % c, "%.1f" % d]
         for f, a, b, c, d in rows],
        title="回収比と S/N", col_w=110,
        caption="混雑側は桁が変わる。中央値は「外れ値に強い」のであって、"
                "視野の半分が汚染されていたら中央値こそが汚染。")

    print("\n所見")
    print("  * 実写の空の std は頑健 σ の %.2f 倍。std をノイズと思うと "
          "検出限界を %.1f 倍甘く出す。" % (std / sig, std / sig))
    print("  * 背景は 1 つの数字ではない(タイル間で %.1f e- = %.1f σ)。"
          % (spread, spread / sig))
    print("  * 空でも開口 1 つあたり %.0f e- 混入する。回収比 %.3f(F=%.0f)"
          "〜 %.3f(F=%.0f)は 1 + C/(F·frac) で最大ずれ %.1f %%。"
          % (C, ratio[0], Fs[0], ratio[-1], Fs[-1], 100 * err.max()))
    print("  * 混雑側は %.1f 倍 〜 %.1f 倍。" % (crowd[0], crowd[-1]))
    print("  * SNR も同じ向きに嘘をつく(%.1f 対 閉形式 %.1f)。"
          % (meas_snr[0], pred_snr[0]))
    print("  * ゼロ点(背景を引かない)は %.1f 倍。飽和は %d 画素。" % (r_raw, sat))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
