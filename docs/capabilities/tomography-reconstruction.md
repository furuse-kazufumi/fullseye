---
id: tomography-reconstruction
title: 投影から断面を再構成する(CT)
title_en: Reconstruct slices from projections (CT)
category: 形にする
ops: [radon_transform, fbp_volume, ring_artifact_remove, marching_cubes]
examples: [poc_ct_fidelity, poc_ct_void_morphology]
version: 0.1.11
inputs: [image2d, sinostack]
pipeline: [radon_transform, ring_artifact_remove, beam_hardening_correct, fbp_volume, vol_rle_components, vol_rle_volume]
alternatives: [marching_cubes, radon_volume, sinogram_center_of_rotation, ring_artifact_apply]
limits: iso-value を 1 段変えるだけでボイド体積・肉厚の合否が反転する(`poc_ct_void_morphology`)。投影数を減らすとフィルタ無し逆投影と 24 本で並び 12 本で逆転(`poc_ct_fidelity`)。
calibration: 体積はボクセルピッチの **3 乗**。ピッチは既知寸法のファントムを再構成して実測する(公称ピッチで 1 % ずれると体積 3 %)。
---

# 投影から断面を再構成する(CT)

## できること

平行ビームの順投影(サイノグラム)と、フィルタ補正逆投影による再構成、リングアーチファクトやビームハードニングの付与と補正を行います。再構成した体積はそのまま等値面としてメッシュ化できます。

## What it does

Forward parallel-beam projection to a sinogram, filtered back-projection to a slice or a volume, and the injection and correction of ring artefacts and beam hardening. The reconstructed volume can be turned straight into a mesh.

## 向くところ / 向かないところ

**向く**: 投影数・雑音・アーチファクトが結果をどこで壊すかを、真値つきで詰めること。

**向かない**: ★**閾値(iso-value)を 1 段変えるだけでボイド体積や肉厚の合否が反転します**。1 つの数字で合否を出す前に、`poc_ct_void_morphology` が測っている「合否 1 個の数字は寿命に効く形に盲目」を読んでください。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

sl = np.zeros((64, 64)); sl[24:40, 24:40] = 1.0
sino = fs.ledger.radon_transform(sl, np.linspace(0, 180, 120, endpoint=False))
print('サイノグラム', np.asarray(sino).shape)
```

## 推奨パイプライン

`radon_transform` → `ring_artifact_remove` → `beam_hardening_correct` → `fbp_volume` → `vol_rle_components` → `vol_rle_volume`

`radon_transform` で順投影(真値つきの検証用)→ `ring_artifact_remove` / `beam_hardening_correct` でサイノグラムを補正 → `fbp_volume` で再構成 → `vol_rle_components` → `vol_rle_volume` で領域の体積。

## 代替

等値面は `marching_cubes`、3-D の順投影は `radon_volume`、回転中心のずれは `sinogram_center_of_rotation`。

## 限界

iso-value を 1 段変えるだけでボイド体積・肉厚の合否が反転する(`poc_ct_void_morphology`)。投影数を減らすとフィルタ無し逆投影と 24 本で並び 12 本で逆転(`poc_ct_fidelity`)。

## 実寸校正

体積はボクセルピッチの **3 乗**。ピッチは既知寸法のファントムを再構成して実測する(公称ピッチで 1 % ずれると体積 3 %)。

## 裏づけ

- op: `radon_transform` / `fbp_volume` / `ring_artifact_remove` / `marching_cubes`
- 例: [`poc_ct_fidelity`](../../examples/poc_ct_fidelity.py)、[`poc_ct_void_morphology`](../../examples/poc_ct_void_morphology.py)
