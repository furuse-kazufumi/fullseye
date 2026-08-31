---
op: depth_to_organized_points
dim: 3d
category: range_image
in: depth
out: pointmap
examples: [range_image]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# depth_to_organized_points — 3D `range_image` op

- **データ種**: `depth` → `pointmap`
- **呼び出し**: `import range_image; range_image.depth_to_organized_points(depth, fx=None, fy=None, cx=None, cy=None)` (または `ops3d.get("depth_to_organized_points")`)

## 使い方

organized 深度画像 → 格子整列 3D 点 (H,W,3)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [range_image](../../../../examples_3d/range_image.py) — `py -3.11 examples_3d/range_image.py`

## 型が繋がる次の op(`pointmap` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`range_image`)

[normals_from_depth](normals_from_depth.md) · [occlusion_edges](occlusion_edges.md) · [bearing_angle_image](bearing_angle_image.md)

---
*Provenance: range_image.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
