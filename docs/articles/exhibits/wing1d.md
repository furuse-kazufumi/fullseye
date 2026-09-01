<!-- tools/gen_wing1d_gallery.py が自動生成。記事 md への挿入候補であり、
     このファイル自体は記事ではない。数値はすべて生成時の実測値。 -->

# 信号・音響・1D ウィング — 展示キャプション原稿

生成元: `tools/gen_wing1d_gallery.py`(`py -3.11 tools/gen_wing1d_gallery.py`)。
画像はすべて Fullseye の `imagedraw` op と numpy 合成で描いており(matplotlib 不使用)、
図に焼いた数値は 1 つ残らずその場で op を呼んで得た実測値である。乱数は seed 固定、
掃引格子も固定なので再生成でバイト列が一致する(`--verify` で検査)。

束ね方は `tools/exhibit_tile.py` の 3 種に従う ―― **コマ送り GIF**(`flipbook`、
掃引と工程。各コマに工程名と `i/N` の進捗バーが焼いてあるので止めても意味が分かる)、
**タイル**(`contact_sheet`、同じ軸にパラメータ違いを当てた小さなプロットを束ねる)、
**原寸 1 枚**(主張そのもの・軸と数値が読めないと意味が無い図)。静止画の Markdown は
すべて **サムネイル表示 + クリックで原寸** の形で出してある。

## 1. 欠陥周波数は生スペクトルに無い

[![欠陥周波数は生スペクトルに無い](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing1d_defect_not_in_raw_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing1d_defect_not_in_raw.png)

*↑ **欠陥周波数は生スペクトルに無い** ―― 共振 3000 Hz を欠陥率 107 Hz で振幅変調した軸受信号(25600 Hz × 1 s、変調度 0.5)。上の生スペクトルは 107 Hz に 4.292e-16 しか無く、エネルギーは搬送波 1.000000 と側帯波 0.250000 / 0.250000(= m/2 ちょうど)に居る。下の包絡線スペクトルは同じ記録から 107.000000 Hz に振幅 0.499677 = 変調度そのものを返す(band_fraction 0.999853)。 使用 op: `synthesize_bearing_signal`, `spectrum`, `envelope_spectrum`。*

- PNG(原寸 1 枚): `docs/articles/assets/wing1d_defect_not_in_raw.png` (1120x800 px, 57 kB)
- サムネ(記事はこちらを表示): `docs/articles/assets/wing1d_defect_not_in_raw_thumb.jpg` (41 kB)
- 束ね方: still
- SHA-256: `7767132cd2edab83b38d3bca9e247c2cacd471e3fac0ca424971b1f6a93b2990`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "rate_hz": 25600.0,
  "duration_s": 1.0,
  "carrier_hz": 3000.0,
  "defect_hz": 107.0,
  "modulation": 0.5,
  "resolution_hz": 1.0,
  "raw_amplitude_at_defect": 4.2916623928040632e-16,
  "raw_amplitude_at_carrier": 0.9999999999999983,
  "raw_sideband_lower": 0.2499999999999956,
  "raw_sideband_upper": 0.24999999999999925,
  "envelope_peak_freq": 107.0,
  "envelope_peak_amplitude": 0.4996770222507938,
  "envelope_band_fraction": 0.999853069632174,
  "envelope_prominence": 10018.617709142389
}
```

</details>

## 2. スペクトルカートシスが復調帯域を選ぶ

![スペクトルカートシスが復調帯域を選ぶ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing1d_kurtosis_band.gif)

*↑ **スペクトルカートシスが復調帯域を選ぶ** ―― 共振の位置を人が知らないとき、どの帯域で復調するかを機械に決めさせる。STFT 平面(129 bin × 199 内側フレーム、全 203 フレームのうち)にスペクトル尖度を重ね、幅 800 Hz の復調帯域を掃引した。SK の最大は 3.1037 @ 2400 Hz(窓 64 = 2.50 ms、bin 400 Hz、推定器の標準偏差 0.1001)で、その帯域の band_fraction は 0.4495。**帯域選びが効いていることが数で出ている**: 掃引した 24 帯域のうち欠陥率を返すのは 9 本だけで、残り 15 本は 6〜428 Hz のもっともらしい別の数を返す(例外も NaN も出ない)。ピーク周波数だけでは区別できず、分けるのは band_fraction である ―― 当たりは 0.1732〜0.6830、外れは 0.1473〜0.1645。 使用 op: `synthesize_bearing_signal`, `stft`, `spectral_kurtosis`, `envelope_spectrum`。*

- GIF: `docs/articles/assets/media/wing1d_kurtosis_band.gif` (24 コマ, 1000x668 px, 2.00 MB, 220 ms/コマ・最終コマ 1400 ms)
- サムネ: `docs/articles/assets/thumbs/wing1d_kurtosis_band_thumb.jpg`
- 束ね方: gif
- SHA-256: `c5d99ab9b37c33e0120328c4517e86d94cfe66402e7f17b069af75a4752b0e90`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "sk_max_kurtosis": 3.1037019867062785,
  "sk_max_freq": 2400.0,
  "sk_win": 64,
  "sk_window_ms": 2.5,
  "sk_bin_hz": 400.0,
  "sk_frames": 1597,
  "sk_noise_sigma": 0.10009388204226968,
  "stft_bins": 129,
  "stft_interior_frames": 199,
  "stft_total_frames": 203,
  "band_width_hz": 800.0,
  "best_band_centre": 3034.782608695652,
  "best_band_fraction": 0.6829578565909229,
  "bands_total": 24,
  "bands_returning_defect_rate": 9,
  "bands_returning_something_else": 15,
  "miss_peak_freq_range": [
    6.0,
    428.0
  ],
  "hit_band_fraction_range": [
    0.17317467053263255,
    0.6829578565909229
  ],
  "miss_band_fraction_range": [
    0.14732009808588267,
    0.16450564153139283
  ],
  "sk_band_fraction": 0.4494574621219424,
  "sk_band_peak_freq": 107.0,
  "worst_band_fraction": 0.14732009808588267
}
```

</details>

## 3. 窓長を間違えると負の尖度が出る

![窓長を間違えると負の尖度が出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing1d_window_sweep.gif)

*↑ **窓長を間違えると負の尖度が出る** ―― 衝撃が 9.346 ms ごとに来る軸受信号(真の共振 3000 Hz)で窓長を 16 から 512 まで掃引した。窓が衝撃の間隔より長くなるとどのフレームにも衝撃が 1 個ずつ入り、その帯域は構成上「定常」に見える。窓 256(10.00 ms)で最大 SK は -0.1269 ―― 負の値を、共振から 9200 Hz 離れた 12200 Hz で報告する。例外は出ない。窓を掃引することはこの op の使い方の一部であって最適化ではない。 使用 op: `synthesize_bearing_signal`, `spectral_kurtosis`。*

- GIF: `docs/articles/assets/media/wing1d_window_sweep.gif` (22 コマ, 1000x668 px, 0.69 MB, 380 ms/コマ・最終コマ 1800 ms)
- サムネ: `docs/articles/assets/thumbs/wing1d_window_sweep_thumb.jpg`
- 束ね方: gif
- SHA-256: `507eb1647e166c69a178c59880d785e0ef0baca7523f32ed8c8d7b5b1f0815c2`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "impact_period_ms": 9.345794392523365,
  "true_resonance_hz": 3000.0,
  "table": [
    {
      "win": 16,
      "ms": 0.625,
      "max": 29.57722851209217,
      "at": 6400.0,
      "bin": 1600.0,
      "frames": 6397
    },
    {
      "win": 24,
      "ms": 0.9375,
      "max": 19.135220536597547,
      "at": 1066.6666666666667,
      "bin": 1066.6666666666667,
      "frames": 4263
    },
    {
      "win": 32,
      "ms": 1.25,
      "max": 12.854675024003651,
      "at": 1600.0,
      "bin": 800.0,
      "frames": 3197
    },
    {
      "win": 48,
      "ms": 1.875,
      "max": 7.878291532367296,
      "at": 533.3333333333334,
      "bin": 533.3333333333334,
      "frames": 2130
    },
    {
      "win": 64,
      "ms": 2.5,
      "max": 5.379627792794402,
      "at": 2000.0,
      "bin": 400.0,
      "frames": 1597
    },
    {
      "win": 96,
      "ms": 3.75,
      "max": 2.9401849728142526,
      "at": 2400.0,
      "bin": 266.6666666666667,
      "frames": 1063
    },
    {
      "win": 128,
      "ms": 5.0,
      "max": 1.660833522213224,
      "at": 1600.0,
      "bin": 200.0,
      "frames": 797
    },
    {
      "win": 192,
      "ms": 7.5,
      "max": 0.45085212215713133,
      "at": 8666.666666666668,
      "bin": 133.33333333333334,
      "frames": 530
    },
    {
      "win": 256,
      "ms": 10.0,
      "max": -0.12685129658601135,
      "at": 12200.0,
      "bin": 100.0,
      "frames": 397
    },
    {
      "win": 384,
      "ms": 15.0,
      "max": -0.5784282950393185,
      "at": 266.6666666666667,
      "bin": 66.66666666666667,
      "frames": 263
    },
    {
      "win": 512,
      "ms": 20.0,
      "max": -0.4994481614669002,
      "at": 800.0,
      "bin": 50.0,
      "frames": 197
    }
  ],
  "negative_windows": [
    {
      "win": 256,
      "ms": 10.0,
      "max": -0.12685129658601135,
      "at": 12200.0
    },
    {
      "win": 384,
      "ms": 15.0,
      "max": -0.5784282950393185,
      "at": 266.6666666666667
    },
    {
      "win": 512,
      "ms": 20.0,
      "max": -0.4994481614669002,
      "at": 800.0
    }
  ]
}
```

</details>

## 4. 次数比分析 — 角度領域で立場が逆転する

![次数比分析 — 角度領域で立場が逆転する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing1d_order_tracking.gif)

*↑ **次数比分析 — 角度領域で立場が逆転する** ―― 600 → 1800 rpm の走行記録(4 s、5000 Hz、次数 1.0 と 3.5、固定共振 400 Hz、計 79.9940 回転)を 1.2 s の窓で滑らせる。素朴なスペクトルでは次数 3.5 が 0.070203(真値 1.0 の 7 %)まで潰れ、−3 dB 幅は 66.50 Hz に広がる。角度領域に置き直すと同じ成分が 0.999371、幅 0 bin (0.00000 次数)。逆に 400 Hz の固定共振は次数軸では平均回転数で次数 20.00 へ散る(振幅 0.025386)。この逆転が診断そのもの。 使用 op: `synthesize_speed_ramp`, `spectrum`, `angular_resample`, `order_spectrum`。*

- GIF: `docs/articles/assets/media/wing1d_order_tracking.gif` (30 コマ, 1000x668 px, 1.08 MB, 220 ms/コマ・最終コマ 1400 ms)
- サムネ: `docs/articles/assets/thumbs/wing1d_order_tracking_thumb.jpg`
- 束ね方: gif
- SHA-256: `db0ab726f8e966c9517713b93d9f90a4d4bc6031dede54761c5e31fa685b1780`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "rpm_start": 600.0,
  "rpm_end": 1800.0,
  "duration_s": 4.0,
  "rate_hz": 5000.0,
  "total_revolutions": 79.9940001,
  "ordinary_order35_amp": 0.07020339787092662,
  "ordinary_order35_hz": 101.5,
  "ordinary_order35_width_hz": 66.5,
  "order_spectrum_order35_amp": 0.9993710550504145,
  "order_spectrum_order35_width": 0.0,
  "order_spectrum_order35_bins": 1,
  "resonance_order_at_mean_rpm": 20.00050001250031,
  "resonance_amp_in_order_domain": 0.025386071643316462,
  "window_s": 1.2,
  "frames": 30,
  "shaft_hz_first": 12.999500000000001,
  "shaft_hz_last": 26.9995
}
```

</details>

## 5. 軸受の幾何から欠陥周波数

![軸受の幾何から欠陥周波数](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing1d_bearing_geometry.gif)

*↑ **軸受の幾何から欠陥周波数** ―― 1800 rpm、ピッチ径 40 mm の軸受で、転動体数 → 接触角 → 転動体径の順に掃引した(36 フレーム)。BPFO は 84.0000 → 177.8261 Hz、BPFI は 126.0000 → 270.3260 Hz まで動く。全フレームで `BPFO + BPFI − N·f_r` の最大絶対値は 0.000e+00、`BPFO − N·FTF` は 0.000e+00 ―― float64 で厳密にゼロで、これは d と D を取り違えると即座に壊れる恒等式である。数表からではなく幾何から再導出しているので、こう書ける。 使用 op: `bearing_defect_frequencies`。*

- GIF: `docs/articles/assets/media/wing1d_bearing_geometry.gif` (36 コマ, 1000x668 px, 1.40 MB, 200 ms/コマ・最終コマ 1400 ms)
- サムネ: `docs/articles/assets/thumbs/wing1d_bearing_geometry_thumb.jpg`
- 束ね方: gif
- SHA-256: `d103e560a0874ab32633502199f072429b0e212941bcfd62da99b5403ed4e8c3`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "rpm": 1800.0,
  "pitch_diameter_mm": 40.0,
  "frames": 36,
  "first": {
    "n_elements": 7,
    "element_diameter": 8.0,
    "contact_angle_deg": 0.0,
    "ratio": 0.2,
    "shaft_hz": 30.0,
    "ftf_hz": 12.0,
    "bpfo_hz": 84.0,
    "bpfi_hz": 126.0,
    "bsf_hz": 72.0
  },
  "last": {
    "n_elements": 14,
    "element_diameter": 15.0,
    "contact_angle_deg": 40.0,
    "ratio": 0.28726666616961677,
    "shaft_hz": 30.0,
    "ftf_hz": 10.691000007455747,
    "bpfo_hz": 149.67400010438047,
    "bpfi_hz": 270.32599989561953,
    "bsf_hz": 36.69911450031176
  },
  "max_abs_identity_1": 0.0,
  "max_abs_identity_2": 0.0,
  "bpfo_range": [
    84.0,
    177.8261333890029
  ],
  "bpfi_range": [
    126.0,
    270.32599989561953
  ]
}
```

</details>

## 6. A 特性・C 特性の重み付け ―― 1 kHz は構成上ちょうど 0 dB

![A 特性・C 特性の重み付け ―― 1 kHz は構成上ちょうど 0 dB](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing1d_weighting_ac.gif)

*↑ **A 特性・C 特性の重み付け ―― 1 kHz は構成上ちょうど 0 dB** ―― 重み付け曲線は公表オフセット定数を足すのではなく**自身の 1 kHz 値で割って**作ってあるので、A(1000) も C(1000) も丸めではなく Python の float として厳密に 0.0 になる(実測 `== 0.0` は True / True)。純音を 34 点掃引して `equivalent_level` の重み付き差 `L_A − L_Z` を曲線値 `A(f)` と突き合わせると、最大差は 7.11e-15 dB(C 特性は 4.88e-15 dB)。振幅 1 の正弦の `L_eq(Z)` は閉形式 10log10(A²/2) = -3.010300 dB で、実測もその値。**ただしこれは音が bin 中心(記録に整数周期入る)にある場合の話**で、同じ音を 1 Hz ずらすと同じ差が 21.0 Hz で 2.86 dB まで開く(図の下段、赤い曲線)。矩形窓の漏れ込みが 1 kHz 付近では 0 dB で重み付けされるため、A 特性が急峻な低域ほど**実際より大きい値が返る**。例外も NaN も出ない。 使用 op: `weighting_response`, `apply_weighting`, `equivalent_level`。*

- GIF: `docs/articles/assets/media/wing1d_weighting_ac.gif` (34 コマ, 1000x668 px, 1.42 MB, 220 ms/コマ・最終コマ 1400 ms)
- サムネ: `docs/articles/assets/thumbs/wing1d_weighting_ac_thumb.jpg`
- 束ね方: gif
- SHA-256: `4a0d21838a07ff9682b8a19d68bc658780b48ef1cc35a660f07b7d1a5ad96872`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "a_at_1k": 0.0,
  "c_at_1k": 0.0,
  "a_at_1k_is_exact_zero": true,
  "c_at_1k_is_exact_zero": true,
  "leq_z_closed_form_db": -3.010299956639812,
  "leq_z_measured_range": [
    -3.010299956639841,
    -3.0102999566398
  ],
  "max_abs_a_mismatch_db": 7.105427357601002e-15,
  "max_abs_c_mismatch_db": 4.884981308350689e-15,
  "bin_hz": 2.0,
  "off_bin_offset_hz": 1.0,
  "off_bin_max_abs_a_mismatch_db": 2.860008933302616,
  "off_bin_worst_freq_hz": 21.0,
  "n_tones": 34,
  "rate_hz": 48000.0,
  "duration_s": 0.5,
  "sample_points": {
    "20.0": {
      "A": -50.39042947681086,
      "C": -6.218824484255237
    },
    "68.0": {
      "A": -24.957730538737856,
      "C": -0.7009469720092589
    },
    "228.0": {
      "A": -9.544886650342692,
      "C": -0.011744795957637682
    },
    "766.0": {
      "A": -0.9765777140127547,
      "C": 0.02141634305233592
    },
    "2584.0": {
      "A": 1.2696291823486323,
      "C": -0.3201711900758198
    },
    "8714.0": {
      "A": -1.6153870384934494,
      "C": -3.521450393344838
    }
  }
}
```

</details>

## 7. funct1d の解析真値

[![funct1d の解析真値](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing1d_funct1d_truth_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing1d_funct1d_truth.png)

*↑ **funct1d の解析真値** ―― 答えが先に分かっている入力だけで組んだ 1 枚。`derivate_funct_1d(sin)/dx` と cos の最大差は 1.008e-04(格子 dx = 0.024592、中心差分は 2 次なので残差は dx² で効く)。`zero_crossings_funct_1d` が返す 3 個の交差は、線形内挿すると 1.000000π, 2.000000π, 3.000000π ―― 整数倍からの最大ずれ 7.397e-08。減衰振動からは周期 0.199500 s(真値 0.200000)、半周期 0.100000 s(真値 0.100000)、時定数 0.406307 s(真値 0.4)、遅延 25 サンプル(真値 25、微分で白色化してから照合)が戻る。 使用 op: `derivate_funct_1d`, `integrate_funct_1d`, `zero_crossings_funct_1d`, `local_min_max_funct_1d`, `smooth_funct_1d_gauss`, `abs_funct_1d`, `get_pair_funct_1d`, `distance_funct_1d`, `match_funct_1d_trans`, `create_funct_1d_array`。*

- PNG(原寸 1 枚): `docs/articles/assets/wing1d_funct1d_truth.png` (1160x786 px, 78 kB)
- サムネ(記事はこちらを表示): `docs/articles/assets/wing1d_funct1d_truth_thumb.jpg` (60 kB)
- 束ね方: still
- SHA-256: `99ae8b3fff2af82965dbdb1341b2b9673d1f5a40917c214da746e2f2d26d0a27`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "derivative_max_error": 0.00010078909493371757,
  "dx": 0.024591723315771374,
  "zero_crossing_indices": [
    127,
    255,
    383
  ],
  "zero_crossing_x_over_pi": [
    0.9999999260312996,
    2.0,
    3.000000073968701
  ],
  "zero_crossing_max_deviation": 7.39687009421175e-08,
  "round_trip_max_error": 0.000151179880499952,
  "period_s": 0.1995,
  "period_true_s": 0.2,
  "half_period_s": 0.1,
  "half_period_true_s": 0.1,
  "tau_s": 0.40630736789098154,
  "tau_true_s": 0.4,
  "match_shift": 25,
  "match_shift_true": 25,
  "match_score": 0.7996386353789152,
  "n_peaks": 5,
  "n_zero_crossings": 8
}
```

</details>

## 8. 平滑化のトレードオフ

![平滑化のトレードオフ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing1d_smoothing_tradeoff.gif)

*↑ **平滑化のトレードオフ** ―― 減衰 5 Hz 振動 + N(0, 0.06) にガウス平滑を掛け、σ を 31 段掃引した。生の信号は真値 6 個の極大に対して 196 個を報告する(`local_min_max_funct_1d` は狭義不等式で、雑音モデルを持たない)。RMS 誤差は σ = 3.219 で最小の 0.021952(生の 2.73 倍良い)になり、そのときピーク高さは真値から -2.77 %。掛けすぎると σ = 40.0 で RMS 誤差が 0.249561 まで悪化し、ピークは -59.56 % なまる。雑音は減るが極値はなまる ―― 最小点はあるが、無料ではない。 使用 op: `smooth_funct_1d_gauss`, `local_min_max_funct_1d`。*

- GIF: `docs/articles/assets/media/wing1d_smoothing_tradeoff.gif` (32 コマ, 1000x668 px, 1.06 MB, 220 ms/コマ・最終コマ 1600 ms)
- サムネ: `docs/articles/assets/thumbs/wing1d_smoothing_tradeoff_thumb.jpg`
- 束ね方: gif
- SHA-256: `98a6eaff19a41a10f97d71410a577d5c54de58fd2574f66dc729f0aa38cd03da`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "true_maxima": 6,
  "true_peak": 0.8851703018329985,
  "raw_rmse": 0.05997372648665996,
  "raw_maxima": 196,
  "raw_peak": 0.9290455796778364,
  "best_sigma": 3.2189538239993025,
  "best_rmse": 0.021951581267836598,
  "best_peak": 0.8606477705412539,
  "best_maxima": 12,
  "best_gain": 2.7320914040271584,
  "best_peak_loss_pct": -2.77037438343376,
  "over_sigma": 39.99999999999999,
  "over_rmse": 0.24956077599878743,
  "over_peak": 0.3579369203167514,
  "over_peak_loss_pct": -59.562931610387224,
  "frames": 32
}
```

</details>

## 9. サンプリングとエイリアシング

![サンプリングとエイリアシング](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing1d_aliasing.gif)

*↑ **サンプリングとエイリアシング** ―― 300 Hz の純音は一度も変えず、サンプリング周波数だけを 1300 Hz から 340 Hz へ 31 段下げた(0.5 s 記録、bin 2 Hz)。fs = 596 Hz(Nyquist 298 Hz)から折り返しが始まり、最後は fs = 340 Hz で 40.00 Hz に振幅 1.000000 の線が立つ ―― 高さは満額のまま、周波数だけが嘘。全 31 段で実測ピークと折り返しの予測 |f − fs·k| の差は最大 0.000 Hz。Nyquist の線から右は、この記録に原理的に存在し得ない領域として焼いてある。 使用 op: `spectrum`。*

- GIF: `docs/articles/assets/media/wing1d_aliasing.gif` (31 コマ, 1000x668 px, 1.14 MB, 260 ms/コマ・最終コマ 1800 ms)
- サムネ: `docs/articles/assets/thumbs/wing1d_aliasing_thumb.jpg`
- 束ね方: gif
- SHA-256: `221239e2f9d4e21e0f353b38e8621bf18b7c046d8d8b24f15bd0aa8c46d38176`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "true_tone_hz": 300.0,
  "duration_s": 0.5,
  "rate_first": 1300.0,
  "rate_last": 340.0,
  "n_rates": 31,
  "first_alias_rate": 596.0,
  "first_alias_nyquist": 298.0,
  "max_abs_prediction_error_hz": 5.684341886080802e-14,
  "bin_resolution_hz": 2.0,
  "last": {
    "fs": 340.0,
    "nyquist": 170.0,
    "peak_hz": 40.0,
    "peak_amp": 1.0000000000000007,
    "expected": 40.0
  },
  "table": [
    {
      "fs": 1300.0,
      "nyquist": 650.0,
      "peak_hz": 300.0,
      "expected": 300.0,
      "peak_amp": 0.9999999999999993
    },
    {
      "fs": 1172.0,
      "nyquist": 586.0,
      "peak_hz": 300.0,
      "expected": 300.0,
      "peak_amp": 1.0000000000000013
    },
    {
      "fs": 1044.0,
      "nyquist": 522.0,
      "peak_hz": 300.0,
      "expected": 300.0,
      "peak_amp": 0.9999999999999993
    },
    {
      "fs": 916.0,
      "nyquist": 458.0,
      "peak_hz": 300.0,
      "expected": 300.0,
      "peak_amp": 0.9999999999999996
    },
    {
      "fs": 788.0,
      "nyquist": 394.0,
      "peak_hz": 300.00000000000006,
      "expected": 300.0,
      "peak_amp": 1.0000000000000002
    },
    {
      "fs": 660.0,
      "nyquist": 330.0,
      "peak_hz": 300.0,
      "expected": 300.0,
      "peak_amp": 0.999999999999999
    },
    {
      "fs": 532.0,
      "nyquist": 266.0,
      "peak_hz": 232.0,
      "expected": 232.0,
      "peak_amp": 1.0000000000000009
    },
    {
      "fs": 404.0,
      "nyquist": 202.0,
      "peak_hz": 104.0,
      "expected": 104.0,
      "peak_amp": 0.9999999999999986
    }
  ]
}
```

</details>

## 10. 1D プロファイルはどこから来るか

[![1D プロファイルはどこから来るか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing1d_profile_sources_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing1d_profile_sources.png)

*↑ **1D プロファイルはどこから来るか** ―― 2D 画像の測定線(実写真 coins、373 サンプル、最強エッジは添字 220.0)、3D ボリュームのプローブ(92 サンプル、壁厚 14.00 / 17.00 / 14.00 voxel)、センサー時系列(500 サンプル、rms 0.2687、スペクトル重心 387.0 Hz)。3 本とも素の 1-D float64 で届くので、`funct1d` はアダプタ無しでそのまま食える。1D ウィングに専用の型を作らなかったのはこのためで ―― 任意の実数 1-D はどの計器から来ても本当に正当なプロファイルであり、型を切ると接続を失うだけ。 使用 op: `line_profile`, `profile_stats`, `vol_profile_line`, `vol_wall_thickness`, `signal_features`, `create_funct_1d_array`, `num_points_funct_1d`, `x_range_funct_1d`, `y_range_funct_1d`, `zero_crossings_funct_1d`, `local_min_max_funct_1d`。*

- PNG(原寸 1 枚): `docs/articles/assets/wing1d_profile_sources.png` (1200x980 px, 176 kB)
- サムネ(記事はこちらを表示): `docs/articles/assets/wing1d_profile_sources_thumb.jpg` (85 kB)
- 束ね方: still
- SHA-256: `63ede6fea12f329925659543e61d942c94e337a620dc99ed0e22d1d8b852f328`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "image_source": "studio_assets/sample_images/coins.png (skimage coins, real photo)",
  "profile2d": {
    "n": 373,
    "min": 0.08627450980392157,
    "max": 0.9529411764705882,
    "mean": 0.54881984965568,
    "edge_at": 220.0
  },
  "profile3d": {
    "n": 92,
    "length_voxels": 91.0,
    "min": 0.08,
    "max": 0.83,
    "wall_thicknesses": [
      14.0,
      17.0,
      14.0
    ]
  },
  "sensor": {
    "n": 500,
    "rate_hz": 2000.0,
    "rms": 0.268716,
    "zcr": 0.366733,
    "crest_factor": 3.9493,
    "centroid_hz": 386.98,
    "peak_freq_hz": 300.0,
    "bandwidth_hz": 237.537
  },
  "funct1d": [
    {
      "name": "2D image, measurement line",
      "op": "measure.line_profile",
      "n": 373,
      "xr": [
        0.0,
        372.0
      ],
      "yr": [
        0.08627450980392157,
        0.9529411764705882
      ],
      "nzc": 0,
      "nmax": 92
    },
    {
      "name": "3D volume, probe line",
      "op": "volprobe.vol_profile_line",
      "n": 92,
      "xr": [
        0.0,
        91.0
      ],
      "yr": [
        0.08,
        0.83
      ],
      "nzc": 0,
      "nmax": 0
    },
    {
      "name": "sensor time series",
      "op": "acoustics.synthesize_bearing_signal",
      "n": 500,
      "xr": [
        0.0,
        499.0
      ],
      "yr": [
        -0.9770901925470433,
        1.0612360539292967
      ],
      "nzc": 183,
      "nmax": 112
    }
  ]
}
```

</details>

## 11. 極値検出と照合

![極値検出と照合](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing1d_peak_match.gif)

*↑ **極値検出と照合** ―― 既知の 4 点(60, 150, 245, 330)に立てたガウスピークへ雑音を σ = 0 から 0.42 まで 30 段加えた。`local_min_max_funct_1d` は狭義不等式なので、生の波形では極大が 4 個から 132 個へ暴発する。σ = 3 のガウス平滑と高さ 0.45 の門を通すと最後まで 6 個([58, 149, 243, 254, 329, 337])に落ち着く。`match_funct_1d_trans` は同じ長さの窓とテンプレートを突き合わせるかぎり、30 段のうち 12 段(σ 0.159 まで)で 4 点すべて lag = 0 を厳密に返す。 使用 op: `smooth_funct_1d_gauss`, `local_min_max_funct_1d`, `match_funct_1d_trans`。*

- GIF: `docs/articles/assets/media/wing1d_peak_match.gif` (30 コマ, 1000x668 px, 1.45 MB, 240 ms/コマ・最終コマ 1600 ms)
- サムネ: `docs/articles/assets/thumbs/wing1d_peak_match_thumb.jpg`
- 束ね方: gif
- SHA-256: `d14889843693fa5a0da90e3affd43d08409e16fb91c4990499b22e06b9238139`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "true_centres": [
    60,
    150,
    245,
    330
  ],
  "peak_sigma_samples": 9.0,
  "template_length": 81,
  "n_frames": 30,
  "sigma_max": 0.42,
  "raw_maxima_first": 4,
  "raw_maxima_last": 132,
  "smoothed_maxima_last": 22,
  "accepted_last": 6,
  "positions_last": [
    58,
    149,
    243,
    254,
    329,
    337
  ],
  "exact_lag_levels": 12,
  "total_levels": 30,
  "exact_lag_up_to_sigma": 0.1593103448275862
}
```

</details>

## 12. 包絡線の端が切れると 76 % 間違う

![包絡線の端が切れると 76 % 間違う](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing1d_envelope_truncation.gif)

*↑ **包絡線の端が切れると 76 % 間違う** ―― 12 µm の走査(241 plane × 0.05 µm)の中で、表面を中央 6.0 µm から端の 0.30 µm まで 32 段歩かせた。中央では誤差 2.2e-14 µm。表面が 0.500 µm にあると `csi_peak_position` は 0.1190 µm を返す ―― 有限で、もっともらしく、76 % 間違っている。しかも包絡線の argmax は 241 plane 中の 2 番目、つまり**内部**なので「端に張り付いたら拒否」という素直な検査は発動しない(掃引の最悪点は 0.30 µm の 84 % で、そこでも argmax は plane 1)。中央値基準の端レベルが 0.0539 を超えた表面 2.69 µm から op は拒否に転じる(図の値は `max_edge_envelope=1.0` で強制的に取り出したもの)。 使用 op: `csi_signal_simulate`, `csi_envelope`, `csi_peak_position`。*

- GIF: `docs/articles/assets/media/wing1d_envelope_truncation.gif` (32 コマ, 1000x668 px, 1.43 MB, 240 ms/コマ・最終コマ 2000 ms)
- サムネ: `docs/articles/assets/thumbs/wing1d_envelope_truncation_thumb.jpg`
- 束ね方: gif
- SHA-256: `ce035df03e06ff0c2e1b5ce485f16e45782ef8613f1475b1371d1d93c74e3612`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "scan_planes": 241,
  "z_step_um": 0.05,
  "z_range_um": 12.0,
  "wavelength_um": 0.6,
  "n_frames": 32,
  "surface_first": 6.0,
  "surface_last": 0.3,
  "first_refusal_surface": 2.690323,
  "first_refusal_edge": 0.05392259854284297,
  "worst_surface": 0.3,
  "worst_returned": 0.04768769253057824,
  "worst_rel_pct": -84.10410248980725,
  "worst_argmax_plane": 1,
  "documented_surface": 0.5,
  "documented_returned": 0.11898968048241321,
  "documented_rel_pct": -76.20206390351736,
  "documented_edge": 0.636140666887029,
  "documented_argmax_plane": 2,
  "centred_error_um": 2.220446049250313e-14,
  "centred_edge": 0.0,
  "table": [
    {
      "surface": 6.0,
      "edge": 0.0,
      "returned": 6.000000000000022,
      "rel_pct": 3.7007434154171886e-13,
      "argmax": 120,
      "refused": false
    },
    {
      "surface": 5.080645,
      "edge": 0.0,
      "returned": 5.080647081606085,
      "rel_pct": 4.0971295686360194e-05,
      "argmax": 102,
      "refused": false
    },
    {
      "surface": 4.16129,
      "edge": 0.0,
      "returned": 4.161139025318186,
      "rel_pct": -0.0036280740302651357,
      "argmax": 83,
      "refused": false
    },
    {
      "surface": 3.241935,
      "edge": 0.0,
      "returned": 3.239315199806879,
      "rel_pct": -0.08080976926190077,
      "argmax": 65,
      "refused": false
    },
    {
      "surface": 2.322581,
      "edge": 0.06881176874572165,
      "returned": 2.31045038505397,
      "rel_pct": -0.522290285937501,
      "argmax": 46,
      "refused": true
    },
    {
      "surface": 1.403226,
      "edge": 0.3399177997568482,
      "returned": 1.359190567949887,
      "rel_pct": -3.1381567937105688,
      "argmax": 27,
      "refused": true
    },
    {
      "surface": 0.5,
      "edge": 0.636140666887029,
      "returned": 0.11898968048241321,
      "rel_pct": -76.20206390351736,
      "argmax": 2,
      "refused": true
    }
  ]
}
```

</details>

## 13. 欠陥周波数が出てくるまで(工程)

![欠陥周波数が出てくるまで(工程)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing1d_envelope_flow.gif)

*↑ **欠陥周波数が出てくるまで(工程)** ―― 幾何から出した外輪通過周波数 BPFO = 108.0000 Hz でわざと鳴らした軸受記録を、7 工程で診断まで持っていく。生スペクトルでは欠陥率の振幅は 1.19e-02 しか無く、目立つのは 3024 Hz の構造共振(0.1175)。スペクトル尖度(窓 64、最大 4.5956 @ 2000 Hz)が復調帯域 1600–2400 Hz を選び(真の共振 3000 Hz より 1000 Hz 低い ―― SK が返すのは帯域であって線ではない)、帯域通過 → 包絡線 → 変換で 108.0000 Hz。それが幾何の BPFO 108.0000 Hz と 0.0000 % で一致する。**正直な内訳**: この帯域の band_fraction は 0.2250 で、同じ帯域に通した白色雑音の 0.2348 と区別がつかない。分けるのは突出度のほうで、30582 対 2666 である(共振をまたぐ 2600–3400 Hz を人が選べば band_fraction は 0.8368 まで上がる)。`dsp.bandpass` + `dsp.envelope` + rfft で手組みした結果と op の返りは 0.0e+00 で一致した(作り直していない証拠)。 使用 op: `bearing_defect_frequencies`, `synthesize_bearing_signal`, `spectrum`, `spectral_kurtosis`, `bandpass`, `envelope`, `envelope_spectrum`。*

- GIF: `docs/articles/assets/media/wing1d_envelope_flow.gif` (7 コマ, 940x522 px, 0.18 MB, 1500 ms/コマ・最終コマ 3000 ms)
- サムネ: `docs/articles/assets/thumbs/wing1d_envelope_flow_thumb.jpg`
- 束ね方: gif
- SHA-256: `b437cde7351aeaac59a4aed6f0a757a0cdd6f5d019d1a97f7ab392e2c141dc04`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "rpm": 1800.0,
  "n_elements": 9,
  "element_diameter_mm": 8.0,
  "pitch_diameter_mm": 40.0,
  "bpfo_hz": 108.0,
  "bpfi_hz": 162.0,
  "ftf_hz": 12.0,
  "bsf_hz": 72.0,
  "synth_defect_hz": 108.0,
  "carrier_hz": 3000.0,
  "rate_hz": 25600.0,
  "duration_s": 1.0,
  "raw_amplitude_at_defect": 0.011914549427139143,
  "raw_peak_amplitude": 0.11751702164005307,
  "raw_peak_hz": 3024.0,
  "sk_max_kurtosis": 4.595572911742822,
  "sk_max_freq": 2000.0,
  "sk_bin_hz": 400.0,
  "sk_win": 64,
  "band_low_hz": 1600.0,
  "band_high_hz": 2400.0,
  "envelope_peak_freq": 108.0,
  "envelope_peak_amplitude": 0.04283185557071618,
  "envelope_band_fraction": 0.22500945540780717,
  "envelope_prominence": 30581.617076490267,
  "envelope_resolution_hz": 1.0,
  "control_band_fraction": 0.23476298878207671,
  "control_prominence": 2665.7791158181667,
  "control_peak_freq": 335.0,
  "resonance_band": [
    2600.0,
    3400.0
  ],
  "resonance_band_fraction": 0.8367515281311655,
  "resonance_band_peak_freq": 108.0,
  "resonance_band_peak_amplitude": 0.19825734899498038,
  "resonance_band_prominence": 11164.842724089745,
  "manual_vs_operator_max_abs_diff": 0.0,
  "closest_rate_name": "BPFO",
  "closest_rate_hz": 108.0,
  "closest_rate_error_pct": 0.0,
  "steps": 7
}
```

</details>

## 14. 分数オクターブ帯域 ―― 偶数分数には 1 kHz 帯域が無い

[![分数オクターブ帯域 ―― 偶数分数には 1 kHz 帯域が無い](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing1d_octave_family_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing1d_octave_family.png)

*↑ **分数オクターブ帯域 ―― 偶数分数には 1 kHz 帯域が無い** ―― 振幅 0.7 の 1000 Hz 純音を、1/1・1/2・1/3・1/6・1/12・1/24 オクターブで測った 6 枚。帯域レベルはどの分数でも閉形式 10log10(A²/2) = -6.108339 dB を返す(最大差 0.0e+00 dB)。違うのは**どの帯域が**それを報告するかで、fraction が奇数 [1, 3] では 1000.000 Hz ちょうどを中心とする帯域があるが、偶数 [2, 6, 12, 24] では指数のオフセットにより 1000 Hz が帯域**端**になり、同じエネルギーが 1188.50 Hz, 944.06 Hz, 971.63 Hz, 1014.50 Hz を中心とする半端な帯域から報告される。定義であって不具合ではないが、「1 kHz でのレベル」を引用するときに知っていないと嘘になる。空の帯域は −inf ではなく床(−200 dB)に落ちる。 使用 op: `octave_bands`, `octave_spectrum`。*

- PNG(タイル): `docs/articles/assets/wing1d_octave_family.png` (1458x868 px, 54 kB, 6 パネル / 3 列)
- サムネ(記事はこちらを表示): `docs/articles/assets/wing1d_octave_family_thumb.jpg` (47 kB)
- 束ね方: sheet
- SHA-256: `986bd447a3a01fe7fb0ead8a50aea99bec869fb81a57752a74916f0ae4c83c72`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "tone_hz": 1000.0,
  "tone_amplitude": 0.7,
  "rate_hz": 48000.0,
  "duration_s": 0.5,
  "closed_form_db": -6.108339156354676,
  "max_abs_diff_from_closed_db": 0.0,
  "fractions_with_exact_1k": [
    1,
    3
  ],
  "fractions_without_exact_1k": [
    2,
    6,
    12,
    24
  ],
  "table": [
    {
      "fraction": 1,
      "n_bands": 10,
      "max_level": -6.108339156354676,
      "max_center": 1000.0,
      "exact_1k": true,
      "diff_from_closed": 0.0,
      "clamped": 9,
      "total_level": -6.108339156354676,
      "nominal_at_max": 1000.0,
      "bandwidth_at_max": 704.5917602386166
    },
    {
      "fraction": 2,
      "n_bands": 20,
      "max_level": -6.108339156354676,
      "max_center": 1188.5022274370185,
      "exact_1k": false,
      "diff_from_closed": 0.0,
      "clamped": 19,
      "total_level": -6.108339156354676,
      "nominal_at_max": 1190.0,
      "bandwidth_at_max": 412.53754462275447
    },
    {
      "fraction": 3,
      "n_bands": 30,
      "max_level": -6.108339156354676,
      "max_center": 1000.0,
      "exact_1k": true,
      "diff_from_closed": 0.0,
      "clamped": 29,
      "total_level": -6.108339156354676,
      "nominal_at_max": 1000.0,
      "bandwidth_at_max": 230.76751616821775
    },
    {
      "fraction": 6,
      "n_bands": 59,
      "max_level": -6.108339156354676,
      "max_center": 944.0608762859234,
      "exact_1k": false,
      "diff_from_closed": 0.0,
      "clamped": 58,
      "total_level": -6.108339156354676,
      "nominal_at_max": 944.0,
      "bandwidth_at_max": 108.74906186625446
    },
    {
      "fraction": 12,
      "n_bands": 118,
      "max_level": -6.108339156354676,
      "max_center": 971.6279515771062,
      "exact_1k": false,
      "diff_from_closed": 0.0,
      "clamped": 117,
      "total_level": -6.108339156354676,
      "nominal_at_max": 972.0,
      "bandwidth_at_max": 55.939123714076686
    },
    {
      "fraction": 24,
      "n_bands": 237,
      "max_level": -6.108339156354676,
      "max_center": 1014.4952080687361,
      "exact_1k": false,
      "diff_from_closed": 0.0,
      "clamped": 236,
      "total_level": -6.108339156354676,
      "nominal_at_max": 1010.0,
      "bandwidth_at_max": 29.200527194428332
    }
  ]
}
```

</details>
