---
id: tof-camera
title: 同じ3次元場面を間接ToFと直接ToFで測る
title_en: Measuring one 3-D scene with indirect and direct time of flight
category: 測る
ops: [itof_capture, itof_phase_amplitude, itof_noise_budget, itof_unwrap_multifreq, itof_unwrap_error_rate, itof_multipath_separate, itof_flying_pixel_mask, itof_wiggling_correct, tof_multipath_phase, dtof_cube_simulate, dtof_cube_depth, spad_deadtime_apply]
examples: [poc_tof_camera]
version: 0.7.0
inputs: [depth]
pipeline: [itof_capture, itof_phase_amplitude, itof_unwrap_multifreq]
alternatives: [dtof_cube_simulate, dtof_cube_depth]
limits: 解析的な平面場面。間接方式は位相折返し・多経路・混合画素、直接方式は時間ビン・pile-up・光子欠乏を受ける。遮蔽面の奥は両方式とも測れない。
calibration: 間接方式は変調周波数・位相段・電子数・背景光、直接方式は時間ビン・応答幅・光子数・デッドタイムを実測値に合わせる。
---

# 同じ3次元場面を間接ToFと直接ToFで測る

## できること

`poc_tof_camera` は箱を積んだ荷台、二面コーナー、光沢面、透明板、細い柱、暗明市松を一つの解析的な距離場に置きます。最初の面と二つの光路を真値として保持し、20/80/100 MHz・4相の連続波方式と、光子到着ヒストグラム方式を同じ画素で比較します。

## What it does

The runnable example compares phase-based continuous-wave ranging and photon-arrival histograms on one analytic inspection scene. It scores ambiguity, noise, harmonic wiggling, multipath, mixed edge pixels, time-bin resolution, pile-up, reflectivity and box-volume errors against closed forms.

## 向くところ / 向かないところ

**向く**: 変調周波数や時間ビンの選定、コーナー・透明体・細線の誤差の説明、体積測定方式の比較。

**向かない**: 曲面メッシュ、波長依存、偏光、散乱、回折、回路の全状態を含む製品評価。

## 推奨パイプライン

間接方式は `itof_capture` → `itof_phase_amplitude` → `itof_unwrap_multifreq`、直接方式は `dtof_cube_simulate` → `dtof_cube_depth`。多経路は `tof_multipath_phase` と `itof_multipath_separate`、混合画素は `itof_flying_pixel_mask` で診断します。

## 代替

単一画素の直接方式だけなら `tcspc_simulate` と `dtof_depth`、二経路の位相偏りだけなら `tof_multipath_phase` を使います。

## 限界

- 場面は解析的な平面群で、透明板は二つの返りとして扱います。
- 間接方式の暗部の偏りは、このPoCではセンサ非線形でなく雑音だけです。
- 直接方式の理想モデルは反射率による系統偏りを持ちません。実モデルではpile-upが早い側へ寄せます。
- どちらも遮蔽面の奥や光が戻らない面を復元しません。

## 実寸校正

間接方式は変調周波数と位相段を周波数基準へ、電子数と背景光を暗明の平面へ合わせます。直接方式は時間ビンと固定遅延を既知距離の平面へ、応答幅とデッドタイムを時間ヒストグラムへ合わせます。

## 最初の 1 本

```python
import numpy as np
import itof

truth = np.full((20, 50), 1.2)
raw = itof.itof_capture(truth, frequencies_hz=(20e6, 80e6, 100e6), noise=False)
phase = itof.itof_phase_amplitude(raw)
depth = itof.itof_unwrap_multifreq(phase, max_range_m=5.0)["depth"]
print(float(np.max(np.abs(depth - truth))))
```

走らせるには `py -3.11 examples/poc_tof_camera.py` を使います。
