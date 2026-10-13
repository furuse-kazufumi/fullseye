---
id: gw-interferometer-quantum-noise-and-matched-filter
title: 干渉計の共振器・量子雑音の予算・色つき雑音の中の既知波形を閉形式で設計する(重力波望遠鏡の式を検査装置の干渉計・振動計・AE に)
title_en: Cavity optics, the quantum-noise budget and a known waveform in coloured noise, in closed form (the gravitational-wave detector's equations for inspection interferometers, vibrometers and AE)
category: 波と信号
ops: [fabry_perot_response, cavity_strain_transfer, michelson_dc_readout, pdh_error_signal, quantum_noise_budget, psd_welch, whiten_by_psd, chirp_newtonian, chirp_mass_from_track, matched_filter_snr, optimal_snr, coincidence_delay]
examples: [poc_gw_detector_pseudo_simulation]
version: 0.6.1
---

# 干渉計の共振器・量子雑音の予算・色つき雑音の中の既知波形を閉形式で設計する(重力波望遠鏡の式を検査装置の干渉計・振動計・AE に)

## できること

重力波望遠鏡は km 級の Michelson 干渉計の両腕に Fabry-Perot 共振器を置き、腕の長さの差を光量で読む装置です。その設計の式は、検査装置のエタロン(波長フィルタ)・レーザー共振器・白色干渉計・振動計の式と同じで、Fullseye にはこれまで共振器そのものと量子雑音の予算、そして**雑音の PSD で割る整合フィルタ**が 1 本もありませんでした。この回は 12 本を 2 つの台帳に足しました。

光学側(`opsoptics` の `cavity`): `fabry_perot_response` は鏡の透過率と長さから FSR・フィネス・線幅・極・循環光量を閉形式で返し(aLIGO の公表設計値で F ≈ 445、極 ≈ 42 Hz)、`cavity_strain_transfer` は単極 × 往復伝搬の sinc の伝達関数、`michelson_dc_readout` は暗縞からのオフセットで読む光量・感度・散射雑音限界(φ₀ → 0 で (1/2L)√(ħcλ/πP))、`pdh_error_signal` は Pound-Drever-Hall の誤差信号(反対称、傾きは Black 2001 の式 15)、`quantum_noise_budget` は Kimble ら 2001 の通常干渉計の散射・輻射圧・標準量子限界(恒等式 散射 × 輻射圧 = SQL²/2、総和は K = 1 で SQL に触れる)です。

信号側(`ops1d` の `matched`): `psd_welch` → `whiten_by_psd`(色つきガウス雑音を分散 1 の平らな雑音へ)→ `matched_filter_snr`(⟨d|h⟩/σ、位相で最大化)と `optimal_snr`、`chirp_newtonian`(ニュートン近似のインスパイラル)と `chirp_mass_from_track`(f^{−8/3} の直線からチャープ質量)、`coincidence_delay`(2 検出器の到達時間差)。

PoC は GW150914 の公開データ(GWOSC)でこの手順を通し、PRL 116, 061102 図 1 の公表曲線と相関 0.96 / 0.94、数値相対論の波形の整合フィルタで SNR H1 19.0 / L1 13.1(公表 ≈ 20 / 13)、L1 が 7.1 ms 先(公表 6.9 ms)を再現します。第二実装 gwinc 0.6.2(信号再利用鏡を外した aLIGO)との比は 8 周波数で 0.96〜1.12 です。

## What it does

Twelve ops in two ledgers. Optics (`opsoptics`, category `cavity`): `fabry_perot_response` (FSR, finesse, linewidth, pole and power gain from mirror transmittances; the public aLIGO design values give F ≈ 445 and a 42 Hz pole), `cavity_strain_transfer` (single pole times the round-trip sinc), `michelson_dc_readout` (DC-readout power, strain slope and the shot-noise limit (1/2L)√(ħcλ/πP)), `pdh_error_signal` (Pound-Drever-Hall, antisymmetric, slope of Black 2001 eq. 15) and `quantum_noise_budget` (Kimble et al. 2001: shot, radiation pressure and the SQL, with the identity shot × rp = SQL²/2). Signals (`ops1d`, category `matched`): `psd_welch`, `whiten_by_psd`, `matched_filter_snr`, `optimal_snr`, `chirp_newtonian`, `chirp_mass_from_track`, `coincidence_delay`. The PoC runs the pipeline on the public GW150914 data and reproduces the published figure (correlation 0.96 / 0.94), the SNRs 19.0 / 13.1 against ≈ 20 / 13 and the 7 ms arrival delay; the second implementation gwinc agrees within 4–12 %.

## 向くところ / 向かないところ

**向く**: エタロン・レーザー共振器・共振器長ロック(PDH)の設計、干渉計測の散射雑音限界と光量の最適点、振動計・AE・超音波の「色つき雑音の中の既知波形」の検出(白色化が効くのは波形が雑音の色を跨ぐとき —— 狭帯域のトーンでは利得が無く、広帯域のチャープ・減衰振動では素の相関の 2 倍)。

**向かない**: ★量子雑音は**通常の干渉計**(信号再利用なし、スクイーズなし)です。aLIGO の設計感度曲線は信号再利用と熱雑音を含むので、20 Hz と 500 Hz 以上で形が違います(PoC が比を表で出します)。チャープはニュートン近似で、合体・リングダウンを含みません(GW150914 の SNR は数値相対論の波形の半分以下)。`chirp_mass_from_track` は式 1 の積分形なので、GW150914 級の重い系では 1 周期に周波数が 7 % 上がる帯域で 20 % ほど高めに出ます(PRL が「≈ 30 M☉」と書いた理由)。整合フィルタは FFT の循環なので、端は `taper_s` で落とし、折り返し領域は 0 にしてあります。

## 最初の 1 本

```python
import numpy as np
import cavityoptics, gwsearch

# aLIGO の腕(公表設計値): フィネス ≈ 445、極 ≈ 42 Hz。量子雑音は散射 × 輻射圧 = SQL²/2。
r = cavityoptics.fabry_perot_response(3994.5, 1064.0, itm_transmittance=0.014, etm_transmittance=5e-6)
q = cavityoptics.quantum_noise_budget(5200.0, 40.0, 3994.5, 1064.0, itm_transmittance=0.014)
print("フィネス %.0f 極 %.1f Hz、恒等式の残差 %.1e" % (r["finesse"], r["pole_hz"],
      abs(q["shot"] ** 2 * q["radiation_pressure"] ** 2 / (q["sql"] ** 4 / 4) - 1).max()))

# 色つき雑音に埋めたチャープを、PSD で白色化した整合フィルタが埋めた高さどおりに拾う
rng = np.random.default_rng(0); fs = 4096.0
x = np.cumsum(rng.standard_normal(int(16 * fs))) * 1e-3            # 1/f² の雑音
psd = gwsearch.psd_welch(x, fs, 4.0)
h = gwsearch.chirp_newtonian(36.0, 29.0, fs, 1.0)
sigma = gwsearch.optimal_snr(h, psd, fs, f_low_hz=None)
x[20000:20000 + h.size] += h * (20.0 / sigma)
snr = gwsearch.matched_filter_snr(x, h, psd, fs, f_low_hz=None, taper_s=0.5)
print("山 %.1f(埋めた高さ 20)、時刻 %d(埋めた %d)" % (snr.max(), snr.argmax(), 20000 + np.abs(h).argmax()))
```
