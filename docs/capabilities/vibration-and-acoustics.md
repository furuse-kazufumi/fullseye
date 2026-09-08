---
id: vibration-and-acoustics
title: 振動と音から異常を診断する
title_en: Diagnose faults from vibration and sound
category: 波と信号
ops: [signal_features, envelope_spectrum, bearing_defect_frequencies, octave_spectrum, spectrum]
examples: [poc_bearing_diagnosis, poc_rail_corrugation]
version: 0.1.11
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

## 裏づけ

- op: `signal_features` / `envelope_spectrum` / `bearing_defect_frequencies` / `octave_spectrum` / `spectrum`
- 例: [`poc_bearing_diagnosis`](../../examples/poc_bearing_diagnosis.py)、[`poc_rail_corrugation`](../../examples/poc_rail_corrugation.py)
