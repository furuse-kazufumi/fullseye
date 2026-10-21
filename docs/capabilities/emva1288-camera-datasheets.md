---
id: emva1288-camera-datasheets
title: カメラのデータシートの数を EMVA 1288 の手順で測り直し、カメラの中の前処理がその数をどれだけ動かすかを見る(Linear と General)
title_en: Re-measure a camera's datasheet numbers with the EMVA 1288 procedure, and see how much in-camera processing moves them (Linear and General)
category: 測る
ops: [emva_pair_statistics, emva_photon_transfer, emva_quantum_efficiency, emva_spatial_nonuniformity, emva_highpass, emva_spectrogram, emva_ptc_linearity_check, emva_bspline_regression, emva_noise_whiteness, emva_filter_distortion, emva_general_sensitivity, emva_general_nonuniformity, emva_general_relative_qe]
examples: [poc_emva1288_sensor, poc_emva1288_in_camera_processing]
version: 0.6.1
---

# カメラのデータシートの数を EMVA 1288 の手順で測り直し、カメラの中の前処理がその数をどれだけ動かすかを見る(Linear と General)

## できること

画像センサ・カメラのデータシートの量子効率 η・システムゲイン K・暗雑音・飽和容量・最大 SNR・ダイナミックレンジ・DSNU・PRNU は、
EMVA 1288 Release 4.0 の手順で測った数です。ここではその手順を op にし、**値を仕込んだ合成センサ**で手順そのものを確かめます。
式は Release 4.0 Linear / General(2021-06-16、無償で公開されている本文)から写し、docstring に節と式の番号を書いてあります。

PoC の主図は 640 × 480 の暗画像・平坦画像・飽和像を等倍で並べます。行 1 DN・列 1.5 DN・画素 4 DN の固定模様と、仕込んだ 9 個の欠陥画素を、集計値だけでなく画像上でも確認できます。

- **Linear**(`sensorchar`、19 op): 同じ露光の 2 枚から平均と時間分散(式 16・18)、photon transfer の傾きで K(式 50)、応答の傾きで
  η(式 49・52)、暗画像から σ_d(式 53)、暗電流(7.1 節)、列・行・画素の空間分散と DSNU・PRNU(式 33〜42・65〜67)、
  欠陥画素のヒストグラム(式 73〜81)。8.1 節の**高域フィルタ**(照明のむらを除く)、8.6 節の**スペクトログラム**(式 70〜72)、
  総合 SNR(式 68・69)、SNR の逆関数(式 25)、光子数(式 3・4)、photon transfer の**直線性の検査**(式 51)まで。
- **General**(`sensorgeneral`、3 op): 線形でないカメラ(圧伸・対数・HDR・カメラの中の前処理)を、特性曲線の 3 次 B-スプライン
  (式 44〜49)の傾きで**入力(光子)の単位**へ戻して測ります(式 9・10)。η と K は「測れない」と報告し、入力 SNR・絶対感度しきい値・
  DR・光子単位の暗雑音(式 50・51)・DSNU / PRNU(式 55〜59)・相対量子効率(式 73・74)を出します。
- ★★**前処理が数をどれだけ動かすか**。線形な前処理(デジタルゲイン・雑音除去・輪郭強調・時間方向の再帰フィルタ)は閉形式で予測できます
  (`emva_filter_distortion`: S = Σw²/(Σw)² · α²/(2 − α) とおくと K' = (Σw) S K、η' = η/S、SNR' = SNR/√S)。例では、3 × 3 の平均を 3 割
  混ぜるだけで η が **+83 %**(0.45 → 0.825、まだ 1 以下でもっともらしい)、時間の雑音除去 α = 0.8 で **+87 %**、輪郭強調で −53 %。
  規格の式 51 はどれも見逃します(photon transfer は直線のまま傾きだけが寝る)。
- ★**見破る道具**。`emva_noise_whiteness` は Linear 1.2 節の前提 3(時間雑音は画素どうし・画像どうしで独立)を直接確かめます —— 2 枚の差の
  隣の画素との相関(雑音除去で正、輪郭強調で負)と、1 枚おきの画像との相関(時間の雑音除去で 1 − α)。**規格が定義した数ではありません**
  (規格は前提を書くが、確かめ方の数を決めていない)。

## What it does

The PoC's lead figure places 640 x 480 dark, flat and saturated frames at native scale, making the 1 DN row, 1.5 DN column and 4 DN pixel fixed pattern—and nine planted defective pixels—visible before reporting aggregate metrics.

The EMVA 1288 Release 4.0 procedure behind camera datasheet numbers, as operators: the Linear model (photon transfer, responsivity,
dark noise, dark current, column/row/pixel nonuniformity, defect-pixel histograms, the section 8.1 highpass filter, the section 8.6
spectrograms, total SNR, the inverse SNR, photon counts and the equation 51 linearity check) and the General model for non-linear
cameras (a cubic B-spline of the characteristic curve whose slope refers output noise back to the input, giving input SNR, sensitivity
threshold, dynamic range, dark noise in photons, DSNU / PRNU and relative quantum efficiency, while reporting η and K as not measurable).
Closed forms predict how linear in-camera processing (digital gain, denoising, sharpening, recursive temporal filtering) moves the Linear
numbers, and a whiteness check tests assumption 3 directly; the check is this library's, not a number defined by the standard.

## 向くところ / 向かないところ

- 例はすべて**合成センサ**です(実機の画像ではない)。前処理はどれも単純化した代表で、実機の中身は分かりません。
- 本文の食い違いを 5 か所見つけ、実装は導き直した式に従っています(どれも門で確かめた): General 式 (49) の外側の枝の符号、式 (48) の
  1/Δμ_p、Linear 付録 C.5 式 (86)(87) の 0.92 / 0.64(Parseval では 0.96 / 0.80)、式 (51) の「平均」と印刷された和、General 式 (74) の
  光子数の比の向き(各波長の光子数を揃えれば害は無い)。
- **式 51 は画素数が要ります**。2 枚の差の分散の揺れ √(2/NM) が局所の傾きを揺らすので、128 × 160 の線形なセンサは 6 回中 1〜3 回、3 % を
  越えて「線形でない」と判定されました(512 × 640 では 0 回)。
- General の B-スプラインは本文どおり [0, μ_p.sat] を 6〜8 等分します。曲がりがその幅よりずっと狭いカメラ(暗い側で急な sqrt の圧伸など)では
  暗い所の傾き R_d が 8〜23 % 外れます。本文の逆回帰(6.8 節)の μ_p.min は 2 万画素の合成で ±5 % 揺れるので、照合用に局所の
  log-log 補間 `mu_p_min_local`(規格の手順ではない)も返します。
- **General は空間・時間の雑音除去の嘘を消しません**。η と K を報告しなくなるだけで、入力 SNR は真値の 1/√S 倍に膨らんだままです
  (時間の雑音除去は General の前提 3 も破る)。欠陥画素の補正(工場の地図)はどの検査にも掛かりません。
- 8.1 節の高域フィルタの端の扱いは本文に無いので、平滑化が定義されない端 9 画素を捨てます(その帯の欠陥画素は数えられない)。
  白い模様の分散も 0.9885 倍になりますが、4.0 の本文は補正を書いていないので補正しません。
- ISO 24942 は発行された本文を読んでいないので、それと同じとは書きません。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

rng = np.random.default_rng(0)


def shot(mu_p, blend=0.0):                     # η 0.45・K 0.25 DN/e⁻・暗雑音 6 e⁻・12 bit。blend > 0 で 3×3 の平均を混ぜる
    y = np.clip(np.round(0.25 * (rng.poisson(0.45 * mu_p, (256, 256)) + rng.normal(0, 6, (256, 256))) + 64), 0, 4095)
    box = sum(np.roll(np.roll(y, i, 0), j, 1) for i in (-1, 0, 1) for j in (-1, 0, 1)) / 9.0
    return np.round((1 - blend) * y + blend * box)


for blend in (0.0, 0.3):
    mp = np.linspace(0.0, 30000.0, 50)
    st = [fs.ledger.emva_pair_statistics(shot(m, blend), shot(m, blend)) for m in mp]
    mu = np.array([s["mu"] for s in st])
    var = np.array([s["var_temporal"] for s in st])
    ptc = fs.ledger.emva_photon_transfer(mu[1:], var[1:], mu[0], var[0], float(mu[-1]))
    qe = fs.ledger.emva_quantum_efficiency(mp[1:], mu[1:], mu[0], float(mu[-1]), ptc["K"])
    white = fs.ledger.emva_noise_whiteness(shot(8000, blend), shot(8000, blend))
    print("blend %.1f: K %.3f η %.3f 白い %s" % (blend, ptc["K"], qe["eta"], white["white"]))
# blend 0.0: K 0.249 η 0.451 白い True
# blend 0.3: K 0.136 η 0.826 白い False

w = np.full((3, 3), 0.3 / 9)
w[1, 1] += 0.7
print(round(fs.ledger.emva_filter_distortion(w)["eta_factor"], 3))   # 1.829(η が何倍に見えるかの閉形式)
```

## 裏づけ

- op(Linear): `emva_pair_statistics` / `emva_photon_transfer` / `emva_quantum_efficiency` / `emva_linearity_error` / `emva_snr_curve` /
  `emva_sensitivity_threshold` / `emva_dynamic_range` / `emva_dark_current` / `emva_spatial_nonuniformity` / `emva_defect_pixels` /
  `emva_highpass` / `emva_spectrogram` / `emva_total_snr` / `emva_exposure_for_snr` / `emva_photon_exposure` / `emva_bspline_regression` /
  `emva_ptc_linearity_check` / `emva_noise_whiteness` / `emva_filter_distortion`
- op(General): `emva_general_sensitivity` / `emva_general_nonuniformity` / `emva_general_relative_qe`
- 例: [`poc_emva1288_sensor`](../../examples/poc_emva1288_sensor.py) —— 仕込んだ η・K・σ_d・暗電流・DSNU・PRNU を規格の手順で取り戻す。
  規格 5 節の模擬カメラ(照明が端へ 3 % 落ちる)で PRNU はフィルタなし 0.831 % → 8.1 節の高域フィルタで 0.497 %(仕込み 0.5 %)、
  スペクトログラムで正弦の振幅 1.46 / 1.50 DN(仕込み 1.5)。
- 例: [`poc_emva1288_in_camera_processing`](../../examples/poc_emva1288_in_camera_processing.py) —— 同じセンサに前処理を 6 つ:
  η はゲイン ×2 で 0 %・雑音除去で +83 %・輪郭強調で −53 %・時間の雑音除去で +87 %・欠陥補正で 0 %(DSNU −10 %、欠陥 29 → 0 個)・
  対数の圧伸で +156 %(η > 1 で絶対感度しきい値の op が拒む)。閉形式の予測と K・η・σ_d は 3 % 以内。式 51 が見破るのは圧伸だけ、
  前提 3 の検査は雑音除去・輪郭強調・時間の雑音除去を見破る。General は圧伸の後ろのセンサの入力 SNR を 5 %、PRNU を 5 % で取り戻す。
- 一次資料: EMVA Standard 1288, Release 4.0 Linear と Release 4.0 General(European Machine Vision Association, 2021-06-16)。
