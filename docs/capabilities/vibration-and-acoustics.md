---
id: vibration-and-acoustics
title: 振動と音から異常を診断する
title_en: Diagnose faults from vibration and sound
category: 波と信号
ops: [signal_features, envelope_spectrum, bearing_defect_frequencies, octave_spectrum, spectrum]
examples: [poc_bearing_diagnosis, poc_rail_corrugation]
version: 0.1.11
inputs: [signal]
pipeline: [bandpass, envelope, envelope_spectrum, find_peaks, bearing_defect_frequencies]
alternatives: [signal_features, octave_spectrum, spectrum, cepstrum, order_spectrum, rms]
limits: 弦(versine)で測る波状摩耗のように伝達関数が 0 になる波長は「欠陥なし」と出る(`poc_rail_corrugation`)。束ねても情報が増えない条件がある(`poc_machine_condition_fusion`)。
calibration: サンプル率 `rate` [Hz] を必ず渡す。軸受の特徴周波数は回転数 [rpm] と幾何から `bearing_defect_frequencies` が先に出す。
---

# 振動と音から異常を診断する

## できること

包絡スペクトル・ケプストラム・オクターブ帯域・軸受の特徴周波数など、回転機械の診断に使う量を出します。周波数は幾何から先に計算できるので、**どのピークを見るべきかを測る前に決められます**。

## What it does

Envelope spectra, cepstra, octave bands and the characteristic frequencies of a rolling-element bearing. The frequencies follow from the geometry, so which peak to look at is decided before measuring, not after.

## 向くところ / 向かないところ

**向く**: 予知保全、設備診断、周期のある欠陥。

**向かない**: ★弦(versine)で測る波状摩耗のように、**伝達関数が 0 になる波長**があると、そこは「欠陥なし」と出ます(`poc_rail_corrugation`)。★束ねても情報が増えない条件があります(`poc_machine_condition_fusion`)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

t = np.arange(4096) / 4096.0
x = np.sin(2 * np.pi * 120 * t) + 0.05 * np.random.default_rng(0).normal(size=t.size)
f, p = fs.spectrum(x, 4096.0)
print('主ピーク =', float(f[int(np.argmax(p))]), 'Hz')
```

## 推奨パイプライン

`bandpass` → `envelope` → `envelope_spectrum` → `find_peaks` → `bearing_defect_frequencies`

`bandpass` で共振帯を切り → `envelope` で包絡 → `envelope_spectrum` で包絡スペクトル → `find_peaks` で峰 → `bearing_defect_frequencies` の予測値と突き合わせる。

## 代替

要約統計は `signal_features`、帯域別は `octave_spectrum`、生スペクトルは `spectrum`、周期の族は `cepstrum`、回転次数は `order_spectrum`。

## 限界

弦(versine)で測る波状摩耗のように伝達関数が 0 になる波長は「欠陥なし」と出る(`poc_rail_corrugation`)。束ねても情報が増えない条件がある(`poc_machine_condition_fusion`)。

## 実寸校正

サンプル率 `rate` [Hz] を必ず渡す。軸受の特徴周波数は回転数 [rpm] と幾何から `bearing_defect_frequencies` が先に出す。

## 裏づけ

- op: `signal_features` / `envelope_spectrum` / `bearing_defect_frequencies` / `octave_spectrum` / `spectrum`
- 例: [`poc_bearing_diagnosis`](../../examples/poc_bearing_diagnosis.py)、[`poc_rail_corrugation`](../../examples/poc_rail_corrugation.py)
