---
id: reuse-computation-results
title: 同じ入力の検証・近傍探索・変換核を一度だけ計算する
title_en: Reuse validation, neighbourhoods and transform kernels
category: 組み立てる
ops: [curvature_descriptors, HankelPlan, piv_outlier_mask_stream, monogenic_metrics, grid_axes, polarization_analyze, PreparedVolProbe, prepare_vol_probe, unpack_lsb]
examples: [perf_pointcloud_descriptors, perf_monogenic_metrics, perf_prepared_volume_probe, perf_polarization_analyze, perf_hankel_plan_and_piv_stream]
version: 0.7.2
inputs: [points, polsweep, volumes, flow, packed_bytes]
pipeline: [polarization_separate]
alternatives: [curvature_descriptors, HankelPlan, piv_outlier_mask_stream, monogenic_metrics, grid_axes, polarization_analyze, prepare_vol_probe, unpack_lsb]
limits: 合成結果を返す op は単独結果より保持量が増える。stream と low_memory はピークメモリを抑えるが、入力自体はメモリ上に必要。
calibration: 数値の単位や較正は元の op と同じ。曲率は点群の長さ単位、体積プローブは spacing、偏光は検光子角度を正しく渡す。
---

# 同じ入力の検証・近傍探索・変換核を一度だけ計算する

## できること

同じ入力から複数の量を得るとき、共通する高価な処理を一度にまとめます。`curvature_descriptors` は一度の近傍探索と曲面当てはめから主曲率・平均曲率・Gauss 曲率・shape index・curvedness を返します。`monogenic_metrics` と `polarization_analyze` は入力検証や正弦波当てはめを共有します。`HankelPlan` と `PreparedVolProbe` は変換核や spline 係数を複数回の呼び出しで再利用します。

メモリが制約になる場合は、`piv_outlier_mask_stream` が halo を含む行ブロックだけを処理し、`unpack_lsb(..., method="low_memory")` が bit 配列への8倍展開を避けます。`grid_axes` は密な `(nx, ny, nz, 3)` 座標格子を作らず、voxel 中心の1-D軸3本を返します。

## What it does

Avoid repeated work when several results share validation, fitting, neighbourhood search, interpolation coefficients, or a transform kernel. Composite calls return numerically equivalent results from one shared pass; prepared objects reuse immutable state; streaming and low-memory variants bound temporary allocations.

## 向くところ / 向かないところ

**向く**: 同じ点群から複数の曲率量を作る、同じ体積へ多数の線プローブを当てる、同じ次数・標本数で Hankel 変換を繰り返す、偏光の分離・DoLP・Stokes を全部使う、巨大な PIV 場や packed pixel を限られたメモリで処理する場合。

**向かない**: 結果を一つしか使わない一回限りの処理では、複合結果や準備オブジェクトを保持する利点がありません。`grid_axes` は軸入力を受ける SDF primitive 用で、任意の dense-grid op の代用品ではありません。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

y, x = np.mgrid[-1:1:9j, -1:1:9j]
points = np.column_stack((x.ravel(), y.ravel(), (0.2 * (x*x + y*y)).ravel()))
d = fs.curvature_descriptors(points, k=12, include_normals=True)
assert set(d) == {"k1", "k2", "mean", "gaussian", "shape_index", "curvedness", "normals"}
assert d["mean"].shape == (81,) and d["normals"].shape == (81, 3)
print(float(np.median(d["curvedness"])))
```

## 推奨パイプライン

`polarization_separate`

偏光分離だけが必要なら小さい単一結果の op を使います。分離・DoLP・Stokes をすべて使う場合は `polarization_analyze` に置き換えます。ほかの入力種別では下記の対応する prepared / composite / streaming op を選びます。

## 代替

反復する Hankel 変換には `HankelPlan`、大きな流れ場には `piv_outlier_mask_stream`、monogenic の三量には `monogenic_metrics`、密な座標格子を避けるには `grid_axes`、偏光の四結果には `polarization_analyze`、反復する体積プローブには `prepare_vol_probe`、packed pixel の一時配列を抑えるには `unpack_lsb` の `low_memory` を使います。

## 限界

合成 op は返した全配列を呼び出し側が保持します。一つの量しか使わない場合は個別 op の方が保持量は少なくなります。`piv_outlier_mask_stream` の `chunk` は出力行数で、境界を正しく計算するため上下1行の halo を内部で足します。`unpack_lsb` の `low_memory` は PFNC の LSB-packed 1〜16 bit 整数向けで、grouped、符号付き、色・3-D形式を解釈しません。`PreparedVolProbe` の spline 係数は order ごとに体積より大きな padded 配列を保持するため、繰り返しが少ない場合には不利です。

## 実寸校正

高速化は較正を変更しません。曲率の単位は入力点群の長さの逆数です。体積プローブでは `spacing=(sz, sy, sx)` を渡すと距離と勾配が実寸になります。偏光では `angles_deg` の順序と実際の検光子角を一致させます。Hankel 変換では `r` と `r_max` を同じ物理単位で指定します。packed pixel は機器の PFNC pixel format から `bits` と packing 規約を確認します。

## 裏づけ

- op: `curvature_descriptors` / `HankelPlan` / `piv_outlier_mask_stream` / `monogenic_metrics` / `grid_axes` / `polarization_analyze` / `PreparedVolProbe` / `prepare_vol_probe` / `unpack_lsb`
- 例: [`perf_pointcloud_descriptors`](../../examples/perf_pointcloud_descriptors.py)、[`perf_monogenic_metrics`](../../examples/perf_monogenic_metrics.py)、[`perf_prepared_volume_probe`](../../examples/perf_prepared_volume_probe.py)、[`perf_polarization_analyze`](../../examples/perf_polarization_analyze.py)、[`perf_hankel_plan_and_piv_stream`](../../examples/perf_hankel_plan_and_piv_stream.py)
- 試験: `tests/test_perf_batch20_2026_10_20.py`〜`tests/test_perf_batch29_2026_10_20.py`
