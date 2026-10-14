---
id: periodic-defects-in-1d-signals
title: 1-D 信号の周期欠陥を見つける
title_en: Periodic defects in a 1-D signal
category: 波と信号
ops: [spectrum, find_peaks, peak_subbin, envelope, cepstrum]
examples: [poc_web_roll_periodicity, poc_rail_corrugation, poc_bearing_diagnosis]
version: 0.2.0
inputs: [signal]
pipeline: [smooth_funct_1d_gauss, bandpass, spectrum, find_peaks, peak_subbin, envelope, local_min_max_funct_1d]
alternatives: [cepstrum, envelope_spectrum, order_spectrum, signal_features, zero_crossings_funct_1d, point_spectrum]
limits: スペクトルの峰は周期の**存在**を言うだけで位置は言わない(位置は包絡の極値から)。ケプストラムは周期の族が 1 つのときだけ効く(`poc_web_roll_periodicity` §3 で使えなかった)。弦(versine)測定は伝達関数が 0 になる波長を「欠陥なし」と出す。
calibration: 標本間隔(`rate` [Hz] か 1 標本あたりの長さ [mm])を必ず渡す —— 周期 [mm] や周波数 [Hz] はそこから決まる。副ビン `peak_subbin` の精度はビン幅の 1/10 程度。
---

# 1-D 信号の周期欠陥を見つける

## できること

ロール起因の周期むら、レールの波状摩耗、軸受の欠陥のように**同じ間隔で繰り返す**欠陥を、1-D の系列(断面・時系列・走査線)から見つけます。周期は `spectrum` の峰、峰の正確な周波数は `peak_subbin`、欠陥がどこにあるかは `envelope` の極値、という役割分担です。

## What it does

Roll-driven periodic marks, rail corrugation, bearing faults: defects that repeat at a fixed interval in a 1-D series. `spectrum` says *whether* there is a period, `peak_subbin` refines *which*, and the extrema of `envelope` say *where*.

## 向くところ / 向かないところ

**向く**: 周期が既知の候補(ロール径・歯数・軸受幾何)から先に計算できるとき —— どの峰を見るかを測る前に決められる。

**向かない**: ★周期の族が複数重なる場面のケプストラム(`fs.cepstrum` は周期の族が 1 つのときの道具)。★周期が信号長の 1/3 より長いとき(峰が分解しない)。★弦で測る波状摩耗のように**測り方そのものが特定の波長を消す**場合(`poc_rail_corrugation`)。

## 推奨パイプライン

`smooth_funct_1d_gauss` → `bandpass` → `spectrum` → `find_peaks` → `peak_subbin` → `envelope` → `local_min_max_funct_1d`

`smooth_funct_1d_gauss` で標本雑音を落とし → `bandpass` で候補の周期帯だけ残し → `spectrum`(片側振幅)→ `find_peaks` で峰の index → `peak_subbin` で副ビン補間した周波数 → `envelope` で時間(位置)領域の包絡 → `local_min_max_funct_1d` で欠陥の位置(極大)を表にする。

## 代替

周期の族を 1 つだけ探すなら `cepstrum`。回転機械は `envelope_spectrum` / `order_spectrum`(回転次数)。要約は `signal_features`、周期の粗い当たりは `zero_crossings_funct_1d`。点列(欠陥の位置だけ)から周期を出すなら `point_spectrum`。

## 限界

- スペクトルの峰は周期の存在を言うだけで、どの位置にあるかは言わない。
- 標本間隔が違う 2 本の信号の周波数は直接比べられない(単位を揃える)。
- ケプストラムは複数の周期族で壊れる(`poc_web_roll_periodicity` の §3)。
- `find_peaks` の高さ閾値は雑音床から決める(中央値の k 倍)。

## 実寸校正

**標本間隔**が校正。時系列なら `rate` [Hz]、走査線なら 1 標本あたりの長さ [mm](画像から取った断面なら `mm_per_px_from_reference` の mm/px がそれ)。周期 [mm] = 1 / 空間周波数 [1/mm]。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

x = np.arange(4096) * 0.5                              # 0.5 mm 間隔の走査線
s = 0.02 * np.sin(2 * np.pi * x / 37.0) + 0.005 * np.random.default_rng(0).normal(size=x.size)
f, m = fs.ledger.spectrum.raw(s, rate=1.0 / 0.5)       # 空間周波数 [1/mm](台帳経由は (N,2) の pairs)
i = int(np.argmax(m[1:]) + 1)
f_hat = f[i] + (fs.ledger.peak_subbin(m, i) - i) * (f[1] - f[0])
print("周期 [mm]", 1.0 / f_hat)                          # 37.0 に近い
```

## 裏づけ

- op: `spectrum` / `find_peaks` / `peak_subbin`(周期)、`envelope` / `local_min_max_funct_1d`(位置)、`cepstrum`(族)
- 例: [`poc_web_roll_periodicity`](../../examples/poc_web_roll_periodicity.py)、[`poc_rail_corrugation`](../../examples/poc_rail_corrugation.py)、[`poc_bearing_diagnosis`](../../examples/poc_bearing_diagnosis.py)
