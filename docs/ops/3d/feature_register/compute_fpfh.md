---
op: compute_fpfh
dim: 3d
category: feature_register
in: points × normals
out: descriptor
examples: [fpfh_correspondence]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# compute_fpfh — 3D `feature_register` op

- **データ種**: `points × normals` → `descriptor`
- **呼び出し**: `import feat_fpfh; feat_fpfh.compute_fpfh(points, normals, k=60, n_bins=11)` (または `ops3d.get("compute_fpfh")`)

## 使い方

FPFH 記述子 (N, 3*n_bins) を計算(Rusu 2009)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fpfh_correspondence](../../../../examples_3d/fpfh_correspondence.py) — `py -3.11 examples_3d/fpfh_correspondence.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`feature_register`)

[harris3d_keypoints](harris3d_keypoints.md) · [iss_keypoints](iss_keypoints.md) · [shot_descriptor](shot_descriptor.md) · [register_spin](register_spin.md) · [register_fpfh](register_fpfh.md) · [register_shot](register_shot.md)

---
*Provenance: feat_fpfh.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
