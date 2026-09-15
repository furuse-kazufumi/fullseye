---
id: beamforming-and-range-doppler
title: 配列で方向を測り、距離と速度を分ける
title_en: Beamform for direction, separate range from velocity
category: 波と信号
ops: [beamform_delay_sum, beamform_doa, range_doppler_map, range_doppler_peaks]
examples: [poc_multibeam_bathymetry, poc_bev_sensor_fusion]
version: 0.1.11
inputs: [beatcube]
pipeline: [beamform_doa, range_doppler_map, range_doppler_peaks]
alternatives: [beamform_delay_sum]
limits: 語彙は電波レーダ向け。音響は `eta = 1/c` で読み替え、`beamform_doa` の距離・速度はパルス測深機に対応物が無い。素子スナップショット 1 枚を渡す口が無く立方体へ水増しが要る(`poc_multibeam_bathymetry` §11)。
calibration: 画素校正は無い。距離 [m] と速度 [m/s] は搬送波周波数・チャープ帯域・サンプル率から op が出すので、その 3 つを実機の設定値で渡す。
---

# 配列で方向を測り、距離と速度を分ける

## できること

素子配列の受信からビームを立てて到来角を出し、FMCW の受信から距離-速度面を作って検出を距離 [m] と速度 [m/s] に戻します。

## What it does

Form beams from an array snapshot to get directions of arrival, and build a range-Doppler map from an FMCW return, mapping detections back to metres and metres per second.

## 向くところ / 向かないところ

**向く**: レーダ、ソナー、音源探査。**角度・距離・速度の規約**を真値つきで詰めること。

**向かない**: ★語彙は電波レーダ向けです。音響へ読み替えるときは屈折率でなく速度で考える必要があり(`eta = 1/c`)、`beamform_doa` の距離・速度はパルス測深機には対応物がありません。★素子スナップショット 1 枚を渡す口が無く、立方体へ**水増し**が要ります(`poc_multibeam_bathymetry` §11)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

n = 16
steer = np.deg2rad(20.0)
x = np.exp(1j * np.pi * np.arange(n) * np.sin(steer))     # λ/2 間隔
print('素子数 =', x.size, '/ 指向を立てる角度 [deg] =', np.rad2deg(steer))
```

## 推奨パイプライン

`beamform_doa` → `range_doppler_map` → `range_doppler_peaks`

`beamform_doa` でビートキューブから到来角を出し → `range_doppler_map` で距離-速度面を作り → `range_doppler_peaks` で検出を距離 [m]・速度 [m/s] に戻す。

## 代替

1 方向に指向を立てた時系列だけ欲しいなら `beamform_delay_sum`(signal を返す)。

## 限界

語彙は電波レーダ向け。音響は `eta = 1/c` で読み替え、`beamform_doa` の距離・速度はパルス測深機に対応物が無い。素子スナップショット 1 枚を渡す口が無く立方体へ水増しが要る(`poc_multibeam_bathymetry` §11)。

## 実寸校正

画素校正は無い。距離 [m] と速度 [m/s] は搬送波周波数・チャープ帯域・サンプル率から op が出すので、その 3 つを実機の設定値で渡す。

## 裏づけ

- op: `beamform_delay_sum` / `beamform_doa` / `range_doppler_map` / `range_doppler_peaks`
- 例: [`poc_multibeam_bathymetry`](../../examples/poc_multibeam_bathymetry.py)、[`poc_bev_sensor_fusion`](../../examples/poc_bev_sensor_fusion.py)
