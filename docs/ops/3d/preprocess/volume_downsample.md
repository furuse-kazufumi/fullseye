---
op: volume_downsample
dim: 3d
category: preprocess
in: voxel
out: voxel
examples: [volume_downsampling]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# volume_downsample — 3D `preprocess` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import volops; volops.volume_downsample(vol, factor, mode='mean')` (または `ops3d.get("volume_downsample")`)

## 使い方

Block-pool a ``(D, H, W)`` volume by an integer *factor* per axis (data 間引き).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [volume_downsampling](../../../../examples_3d/volume_downsampling.py) — `py -3.11 examples_3d/volume_downsampling.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`preprocess`)

[statistical_outlier_removal](statistical_outlier_removal.md) · [radius_outlier_removal](radius_outlier_removal.md) · [voxel_grid_downsample](voxel_grid_downsample.md) · [mls_smooth](mls_smooth.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
