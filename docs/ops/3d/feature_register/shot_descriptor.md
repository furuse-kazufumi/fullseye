---
op: shot_descriptor
dim: 3d
category: feature_register
in: points × normals
out: descriptor
examples: [feature_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# shot_descriptor — 3D `feature_register` op

- **データ種**: `points × normals` → `descriptor`
- **呼び出し**: `import feat_shot; feat_shot.shot_descriptor(points, normals, kp_idx, tree, radius, n_azim=8, n_elev=2, n_rad=2, n_cos=11)` (または `ops3d.get("shot_descriptor")`)

## 使い方

SHOT 記述子(Tombari 2010)。各キーポイントに LRF を張り、球状支持を

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [feature_register](../../../../examples_3d/feature_register.py) — `py -3.11 examples_3d/feature_register.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`feature_register`)

[harris3d_keypoints](harris3d_keypoints.md) · [iss_keypoints](iss_keypoints.md) · [compute_fpfh](compute_fpfh.md) · [register_spin](register_spin.md) · [register_fpfh](register_fpfh.md) · [register_shot](register_shot.md)

---
*Provenance: feat_shot.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
