# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""photon_timeresolved — 光子計数・時間分解 op(photoncount)を「単一光子距離計を
1 台仕立てる」筋で一巡する。

    py -3.11 examples/photon_timeresolved.py

【この例が解く問題】
単一光子検出器(SPAD)で 3 m 先の対象までの距離を測り、同じ装置で蛍光寿命も
出す。画素値ではなく**光子を 1 個ずつ数える**世界なので、雑音は調整項ではなく
√N であり、検出器はカウントするたびに一定時間目が見えなくなる。
(1) 光子統計: 期待光子数から Poisson 実現を作り、分散 = 平均(Fano = 1)と
    SNR = √N が成り立つことを確かめる。
(2) 分散安定化: Anscombe 変換で「分散 1」にし、代数逆変換が厳密逆であること、
    厳密不偏逆変換が平均バイアスを 1/49 に落とすことを確かめる。
(3) 検出器の非理想: デッドタイムで計数が落ちる量を出し、非麻痺型の補正が
    厳密逆であることを確かめる。麻痺型は**逆が存在しない**ことも数値で示す。
(4) 到達時刻ヒストグラム: 既知距離 3 m の dToF 波形を合成し、IRF(タイミング
    ジッタ)を畳み込み、背景光を除去して、ピーク幅と重心を計測する。
(5) 距離: ヒストグラム → 距離 d = c·t/2 を 4 つの推定量で出し、**ショット雑音が
    支配すると推定量の差はほとんど消える**ことを数値で示す。
(6) 画素配列: (H, W, T) ヒストグラム立方体を合成して深度マップに戻す。
(7) パイルアップ: 先頭光子 TCSPC の歪みを Coates 推定量で厳密に戻す。
(8) 寿命: 単一指数減衰から寿命を復元し、phasor が universal semicircle に
    乗ること、二成分だと**円の内側に落ちる**ことを確かめる。

【グラウンドトゥルース(数値で嘘を弾く)】
1. Poisson: Fano = 1、SNR = √λ。空画素率 = exp(-λ)。
2. Anscombe: 代数逆変換の往復が機械精度。var(A) は λ=100 で 1.000006、
   λ=1 では 0.717(=低カウントでは成り立たない、という正直な限界)。
3. デッドタイム: n·τ = 1 で m = n/2 ちょうど。apply→correct が機械精度。
   麻痺型は n = 1/τ で最大 1/(e·τ) を取り、その先は**減る**(単射でない)。
4. dToF: パルスは t = 2d/c に立つ。重心は雑音なしで機械精度。
5. 立方体: 雑音なしの重心が入力深度マップを機械精度で再現。
6. Coates: 先頭光子モデルの厳密逆(相対誤差 1e-13 未満)。
7. 寿命: 雑音なしの指数減衰で厳密。phasor は (g-1/2)²+s² = 1/4 の上。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import photoncount as P  # noqa: E402

C = P.SPEED_OF_LIGHT_M_S


def main():
    ok = True

    # ------------------------------------------------------------------ #
    # 1) 光子統計: 分散 = 平均、SNR = √N                                   #
    # ------------------------------------------------------------------ #
    scene = np.ones((512, 512))
    counts = P.photon_sample(scene, photons_per_unit=100.0, seed=0)
    st = P.photon_statistics(counts)
    print("1) 光子統計(平均 100 光子/画素、512x512):")
    print(f"   平均={st['mean']:.4f}  分散={st['variance']:.4f}  "
          f"Fano={st['fano_factor']:.6f}(Poisson なら 1)")
    print(f"   SNR: 理論 √N={st['snr_poisson']:.4f}  実測={st['snr_measured']:.4f}"
          f"  空画素率={st['zero_fraction']:.6f}")
    assert abs(st["fano_factor"] - 1.0) < 0.02          # 7σ 帯
    assert abs(st["snr_measured"] - st["snr_poisson"]) < 0.1
    err = P.photon_uncertainty(counts)
    assert np.allclose(err, np.sqrt(counts))            # 誤差棒は √N そのもの
    # 露光を 1/100 にすると SNR は 1/10 にしか落ちない(√ の効き)
    dim = P.photon_statistics(P.photon_sample(scene, 1.0, seed=0))
    print(f"   露光 1/100 → SNR {st['snr_measured']:.2f} → "
          f"{dim['snr_measured']:.2f}(√100=10 倍の劣化)")
    assert abs(st["snr_measured"] / dim["snr_measured"] - 10.0) < 0.5

    # ------------------------------------------------------------------ #
    # 2) 分散安定化: Anscombe                                             #
    # ------------------------------------------------------------------ #
    a = P.anscombe_transform(counts)
    back = P.anscombe_inverse(a)
    print("2) Anscombe: var(A)=%.6f(目標 1)  代数逆変換の最大誤差=%.2e"
          % (float(a.var()), float(np.abs(back - counts).max())))
    assert abs(float(a.var()) - 1.0) < 0.02
    assert np.allclose(back, counts, rtol=1e-12, atol=1e-9)
    faint = P.anscombe_transform(P.photon_sample(scene, 1.0, seed=3))
    print(f"   1 光子/画素では var(A)={float(faint.var()):.4f} "
          f"— 「分散 1」は 4 光子以上でしか成り立たない(正直な限界)")
    assert float(faint.var()) < 0.80
    # 不偏逆変換: 理想的にデノイズされた値 D = E[A(X)] に当てたときのバイアス
    from scipy.special import gammaln
    lam = 1.0
    k = np.arange(0, 60, dtype=np.float64)
    pmf = np.exp(k * np.log(lam) - lam - gammaln(k + 1.0))
    D = np.array([[float((pmf * 2.0 * np.sqrt(k + 0.375)).sum())]])
    b_alg = float(P.anscombe_inverse(D, mode="algebraic")[0, 0]) - lam
    b_unb = float(P.anscombe_inverse(D, mode="unbiased")[0, 0]) - lam
    print(f"   λ=1 のバイアス: 代数逆 {b_alg:+.6f} / 厳密不偏逆 {b_unb:+.6f} "
          f"({abs(b_alg / b_unb):.0f} 倍改善)")
    assert abs(b_unb) < abs(b_alg) / 10.0

    # ------------------------------------------------------------------ #
    # 3) 検出器の非理想: デッドタイム                                      #
    # ------------------------------------------------------------------ #
    tau_ns = 50.0
    tau = tau_ns * 1e-9
    rates = np.array([1e5, 1e6, 5e6, 1.0 / tau])
    meas = P.spad_deadtime_apply(rates, tau_ns)
    corr = P.spad_deadtime_correct(meas, tau_ns)
    print(f"3) デッドタイム(τ={tau_ns:.0f} ns、飽和 {1.0 / tau / 1e6:.0f} MHz):")
    for n, m in zip(rates, meas):
        print(f"   真 {n / 1e6:7.2f} MHz → 実測 {m / 1e6:7.2f} MHz "
              f"(損失 {100 * (1 - m / n):5.1f}%)")
    assert abs(meas[-1] - rates[-1] / 2.0) < 1e-6       # n·τ=1 でちょうど半分
    assert np.allclose(corr, rates, rtol=1e-12)         # 補正は厳密逆
    par = P.spad_deadtime_apply(np.array([0.5, 1.0, 2.0, 4.0]) / tau, tau_ns,
                                paralyzable=True)
    print(f"   麻痺型: 最大 {par[1] / 1e6:.2f} MHz(理論 1/(e·τ)="
          f"{1.0 / (np.e * tau) / 1e6:.2f})→ その先は減る = 逆が一意でない")
    assert abs(par[1] - 1.0 / (np.e * tau)) < 1.0
    assert par[1] > par[2] > par[3]                     # 単射でない

    # ------------------------------------------------------------------ #
    # 4) 到達時刻ヒストグラム(TCSPC / dToF)                              #
    # ------------------------------------------------------------------ #
    d_true, bins, bin_ps, irf_ps = 3.0, 256, 100.0, 500.0
    rng_m = C * bins * bin_ps * 1e-12 / 2.0
    clean = P.tcspc_simulate(d_true, bins=bins, bin_ps=bin_ps,
                             signal_photons=1000.0, ambient_photons=0.0,
                             irf_fwhm_ps=irf_ps, noise=False)
    t0 = 2.0 * d_true / C * 1e12
    s_clean = P.tcspc_stats(clean, bin_ps)
    print(f"4) TCSPC({bins} bin x {bin_ps:.0f} ps → 一意測距範囲 {rng_m:.2f} m、"
          f"1 bin = {C * bin_ps * 1e-12 / 2 * 100:.2f} cm):")
    print(f"   重心 実測 {s_clean['centroid_ps']:.6f} ps / 理論 2d/c = "
          f"{t0:.6f} ps(差 {s_clean['centroid_ps'] - t0:+.2e})")
    assert abs(s_clean["centroid_ps"] - t0) < 1e-9
    # IRF(ジッタ)の畳み込み: 幅は二乗和で足される
    wider = P.tcspc_irf_convolve(clean, bin_ps, 500.0)
    w_fwhm = P.tcspc_stats(wider, bin_ps)["fwhm_ps"]
    quad = float(np.hypot(s_clean["fwhm_ps"], 500.0))
    print(f"   IRF 追加畳み込み: FWHM {s_clean['fwhm_ps']:.1f} ps → {w_fwhm:.1f} ps"
          f"(幅は二乗和で足される: √({s_clean['fwhm_ps']:.1f}²+500²)="
          f"{quad:.1f} ps)")
    assert w_fwhm > s_clean["fwhm_ps"]
    assert abs(w_fwhm - quad) / quad < 0.02
    # 屋外 = 背景光まみれ。中央値で床を推定して引く
    noisy = P.tcspc_simulate(d_true, bins=bins, bin_ps=bin_ps,
                             signal_photons=300.0, ambient_photons=1500.0,
                             irf_fwhm_ps=irf_ps, seed=0)
    s_noisy = P.tcspc_stats(noisy, bin_ps)
    cleaned = P.tcspc_background_subtract(noisy, "median")
    print(f"   背景光あり: 総 {s_noisy['total_counts']:.0f} 光子 / 床 "
          f"{s_noisy['background_per_bin']:.1f} 光子/bin / SBR "
          f"{s_noisy['sbr']:.2f} → 除去後の総 {cleaned.sum():.0f} 光子")
    assert cleaned.sum() < noisy.sum()                  # 引き算(足し算でない)
    assert s_noisy["background_per_bin"] > 0.0

    # ------------------------------------------------------------------ #
    # 5) 距離: 4 つの推定量と、雑音下でのその差の消滅                      #
    # ------------------------------------------------------------------ #
    print("5) 距離 d = c·t/2(真値 %.4f m):" % d_true)
    modes = ("peak", "centroid", "parabolic", "gaussian")
    e_clean = {m: abs(P.dtof_depth(clean, bin_ps, m) - d_true) for m in modes}
    e_noisy = {m: abs(P.dtof_depth(noisy, bin_ps, m,
                                   subtract_background=(m == "centroid"))
                      - d_true) for m in modes}
    for m in modes:
        print(f"   {m:<10} 雑音なし誤差 {e_clean[m] * 1000:9.5f} mm   "
              f"ショット雑音下 {e_noisy[m] * 1000:8.2f} mm")
    assert e_clean["centroid"] < e_clean["gaussian"] < e_clean["peak"]
    assert e_clean["gaussian"] < 1e-6                   # 3 桁の差が付く
    assert e_noisy["gaussian"] < e_noisy["centroid"]    # 雑音下では重心が崩れる
    print("   → 雑音なしでは 3 桁の差が付くが、ショット雑音下では peak と "
          "gaussian の差は 1.5 倍以内(重心だけは背景で崩れる)")
    print("     = 推定量を凝る前に光子を増やすべき、という結論")
    # 系遅延(offset)は「引く」向き。正の offset は近くなる
    shifted = P.dtof_depth(clean, bin_ps, "gaussian", offset_ps=1000.0)
    print(f"   系遅延 +1000 ps を較正 → {shifted:.4f} m "
          f"(差 {shifted - P.dtof_depth(clean, bin_ps, 'gaussian'):+.4f} m)")
    assert shifted < d_true

    # ------------------------------------------------------------------ #
    # 6) SPAD 配列: (H, W, T) ヒストグラム立方体 → 深度マップ              #
    # ------------------------------------------------------------------ #
    h, w = 32, 32
    depth_gt = 1.0 + 2.0 * np.linspace(0.0, 1.0, w)[None, :] * np.ones((h, 1))
    refl = np.linspace(0.3, 1.0, w)[None, :] * np.ones((h, 1))
    cube0 = P.dtof_cube_simulate(depth_gt, bins=bins, bin_ps=bin_ps,
                                 reflectivity=refl, signal_photons=1000.0,
                                 ambient_photons=0.0, irf_fwhm_ps=irf_ps,
                                 noise=False)
    cube = P.dtof_cube_simulate(depth_gt, bins=bins, bin_ps=bin_ps,
                                reflectivity=refl, signal_photons=20.0,
                                ambient_photons=5.0, irf_fwhm_ps=irf_ps, seed=0)
    rms0 = float(np.sqrt(((P.dtof_cube_depth(cube0, bin_ps, "centroid")
                           - depth_gt) ** 2).mean()))
    got = P.dtof_cube_depth(cube, bin_ps, "gaussian")
    e = np.abs(got - depth_gt)
    rms = float(np.sqrt((e ** 2).mean()))
    med, out = float(np.median(e)), float((e > 0.1).mean())
    print(f"6) SPAD 配列 {h}x{w}x{bins}(傾いた平面 1.0-3.0 m、反射率 0.3-1.0):")
    print(f"   雑音なしの深度 RMS 誤差 = {rms0:.3e} m(機械精度)")
    print(f"   20 光子/画素 x 反射率 + 背景 5 → 実際は 1 画素 {cube.sum(-1).min():.0f}"
          f"-{cube.sum(-1).max():.0f} 光子")
    print(f"   誤差: 中央値 {med * 1000:.1f} mm / RMS {rms * 1000:.1f} mm / "
          f"10 cm 超の外れ値 {out * 100:.1f}%  非有限画素 "
          f"{int((~np.isfinite(got)).sum())} 個")
    print("   → RMS が中央値の 11 倍なのは、暗い列(反射率 0.3 = 4-6 光子)の "
          "外れ値が支配しているから。平均値だけ見ると誤解する典型例")
    assert rms0 < 1e-12
    assert med < 0.03 and out < 0.06 and np.isfinite(got).all()

    # ------------------------------------------------------------------ #
    # 7) パイルアップ: 先頭光子 TCSPC の歪みを Coates で厳密に戻す         #
    # ------------------------------------------------------------------ #
    cycles = 200000
    lam_true = P.tcspc_simulate(d_true, bins=bins, bin_ps=bin_ps,
                                signal_photons=0.6, ambient_photons=0.2,
                                irf_fwhm_ps=irf_ps, noise=False)
    prior = np.concatenate(([0.0], np.cumsum(lam_true)[:-1]))
    piled = cycles * np.exp(-prior) * (1.0 - np.exp(-lam_true))
    fixed = P.tcspc_coates_correct(piled, cycles)
    truth = cycles * lam_true
    rel = float((np.abs(fixed - truth) / np.maximum(truth, 1e-12)).max())
    d_piled = P.dtof_depth(piled, bin_ps, "centroid", subtract_background=True)
    d_fixed = P.dtof_depth(fixed, bin_ps, "centroid", subtract_background=True)
    print(f"7) パイルアップ({cycles} 励起サイクル、先頭光子のみ記録):")
    print(f"   最終 bin の測定値は真値の {piled[-1] / truth[-1] * 100:.1f}% しかない")
    print(f"   Coates 補正の最大相対誤差 = {rel:.2e}(厳密逆)")
    print(f"   距離: 歪んだまま {d_piled:.4f} m → 補正後 {d_fixed:.4f} m "
          f"(真値 {d_true:.4f} m)")
    assert rel < 1e-12
    assert d_piled < d_true                             # 早い側に偏る
    assert abs(d_fixed - d_true) < abs(d_piled - d_true) / 5.0

    # ------------------------------------------------------------------ #
    # 8) 蛍光寿命: 指数フィットと phasor                                   #
    # ------------------------------------------------------------------ #
    tau_ps, n_b, dt_b = 2000.0, 1024, 25.0
    edges = np.arange(n_b + 1, dtype=np.float64) * dt_b
    integ = tau_ps * (np.exp(-edges[:-1] / tau_ps) - np.exp(-edges[1:] / tau_ps))
    decay = 20000.0 * integ / integ.sum()
    fit = P.lifetime_fit(decay, dt_b, background=0.0, min_counts=0.0)
    ph = P.lifetime_phasor(decay, dt_b)
    wt = ph["omega_per_ps"] * tau_ps
    print(f"8) 蛍光寿命(真値 {tau_ps:.0f} ps、{n_b} bin x {dt_b:.0f} ps):")
    print(f"   指数フィット {fit['lifetime_ps']:.6f} ps  R²={fit['r_squared']:.12f}"
          f"  使用 bin {fit['n_bins_used']}")
    print(f"   phasor g={ph['g']:.6f}(理論 {1 / (1 + wt ** 2):.6f}) "
          f"s={ph['s']:.6f}(理論 {wt / (1 + wt ** 2):.6f})")
    print(f"   τ_φ={ph['tau_phi_ps']:.2f} ps  τ_m={ph['tau_m_ps']:.2f} ps  "
          f"円からのずれ={ph['semicircle_residual']:+.2e}")
    assert abs(fit["lifetime_ps"] - tau_ps) / tau_ps < 1e-9    # 雑音なしは厳密
    assert abs(ph["g"] - 1.0 / (1.0 + wt ** 2)) < 2e-4
    assert abs(ph["semicircle_residual"]) < 1e-4               # 円の上
    # 二成分にすると円の内側へ落ちる = 単一指数の仮定が破れたことの検出
    def _decay(t_ps, total):
        i = t_ps * (np.exp(-edges[:-1] / t_ps) - np.exp(-edges[1:] / t_ps))
        return total * i / i.sum()
    two = _decay(500.0, 1e4) + _decay(4000.0, 1e4)
    ph2 = P.lifetime_phasor(two, dt_b)
    fit2 = P.lifetime_fit(two, dt_b, background=0.0, min_counts=0.0)
    print(f"   二成分(500 + 4000 ps): 指数フィットは {fit2['lifetime_ps']:.0f} ps "
          f"と 1 つの数を返すが、phasor のずれ={ph2['semicircle_residual']:+.4f} "
          f"= 円の内側 → 単一指数ではないと分かる")
    assert ph2["semicircle_residual"] < -0.05

    print("PASS: photoncount 17 op すべてが閉形式のグラウンドトゥルースと一致")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
