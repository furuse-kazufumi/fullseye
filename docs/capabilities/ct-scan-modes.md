---
id: ct-scan-modes
title: コーンビーム・ヘリカル・ラミノグラフィを 1 つの幾何で再構成する(工業用 CT)
title_en: Reconstruct cone-beam, helical and laminography scans on one geometry (industrial CT)
category: 形にする
ops: [ct_scan_geometry, ellipsoid_projections, fdk_reconstruct, sirt_reconstruct, tv_reconstruct]
examples: [ct_scan_modes]
version: 0.8.1
inputs: [ctgeometry, projstack]
pipeline: [ct_scan_geometry, ellipsoid_projections, fdk_reconstruct, vol_rle_components, vol_rle_volume]
alternatives: [sirt_reconstruct, os_sart_reconstruct, tv_reconstruct, ct_forward_project, ct_adjoint_project]
limits: FDK は中央面でだけ厳密で、コーン角が増えると Feldkamp アーチファクトが増える(`test_feldkamp_artifact_grows_with_cone_angle`)。ヘリカルは近似の重み付き FDK で、Katsevich の厳密解ではない。ラミノグラフィとトモシンセシスは軸のまわりの周波数を測っていないので、深さ方向の分解能はフィルタでは戻らない。TV は対象が区分的に一定という仮定で埋めるので、残差が小さいことは真値の証拠にならない。
calibration: 線源・検出器距離(`dso`, `dsd`)と検出器ピッチは幾何の値がそのまま振幅に効く。既知寸法のファントムを再構成してボクセルピッチを実測する。回転中心のずれは `offset_u` で与える。
---

# コーンビーム・ヘリカル・ラミノグラフィを 1 つの幾何で再構成する(工業用 CT)

## できること

線源と検出器の位置を view ごとに持つ 1 つの記述(`ct_scan_geometry`)から、コーンビーム、ヘリカル、ラミノグラフィ、ファンビーム(等間隔・等角)、ショートスキャン、検出器オフセット、トモシンセシス、少数ビュー、制限角を同じ投影と逆投影の核で再構成します。楕円体の閉形式の投影(`ellipsoid_projections`)を真値に使うので、再構成の誤差を投影器の誤差と分けて測れます。GPU があれば `device="auto"` で GPU に載ります。

## What it does

One description of a scan (`ct_scan_geometry`), holding the source and detector per view, drives cone-beam, helical, laminography, fan (flat and equiangular), short-scan, offset-detector, tomosynthesis, few-view and limited-angle reconstruction on the same projector and back-projector. The closed-form projections of ellipsoids (`ellipsoid_projections`) are the ground truth, so reconstruction error can be measured apart from projector error. With a GPU, `device="auto"` runs there.

## 向くところ / 向かないところ

**向く**: スキャン方式や視点数の選択が再構成の誤差をどれだけ動かすかを、真値つきで比べること。

**向かない**: 実機の幾何校正そのもの。ここで使う幾何は与えられた値を信じます。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

geom = fs.ct_scan_geometry('cone', n_views=30, n_u=32, n_v=32, vol_shape=16)
proj = fs.ellipsoid_projections(geom, device='cpu')
vol = fs.fdk_reconstruct(proj, geom, device='cpu')
print('再構成', np.asarray(vol).shape)
```

## 推奨パイプライン

`ct_scan_geometry` → `ellipsoid_projections` → `fdk_reconstruct` → `vol_rle_components` → `vol_rle_volume`

`ct_scan_geometry` で方式を決め、実機の投影か `ellipsoid_projections` の真値を `fdk_reconstruct` に渡します。再構成した後は既存の 3-D 族がそのまま使えます。

## 代替

式の無い方式(トモシンセシス・少数ビュー・制限角)は `sirt_reconstruct`、`os_sart_reconstruct`、`tv_reconstruct`。自作の解法には `ct_forward_project` と `ct_adjoint_project`。

## 限界

FDK は中央面でだけ厳密で、コーン角が増えると Feldkamp アーチファクトが増えます。ヘリカルは近似の重み付き FDK で、Katsevich の厳密解ではありません。ラミノグラフィとトモシンセシスは軸のまわりの周波数を測っていないので、深さ方向の分解能はフィルタでは戻りません。TV は区分的に一定という仮定で埋めるので、残差が小さいことは真値の証拠になりません。

## 実寸校正

線源・検出器距離(`dso`, `dsd`)と検出器ピッチは幾何の値がそのまま振幅に効きます。既知寸法のファントムを再構成してボクセルピッチを実測してください。回転中心のずれは `offset_u` で与えます。

## 裏づけ

- op: `ct_scan_geometry` / `ellipsoid_projections` / `fdk_reconstruct` / `sirt_reconstruct` / `tv_reconstruct`
- 例: [`ct_scan_modes`](../../examples/ct_scan_modes.py)
- 実測: [`gpu_ct_2026-11-02`](../perf/gpu_ct_2026-11-02.md)
