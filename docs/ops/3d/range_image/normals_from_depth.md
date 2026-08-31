---
op: normals_from_depth
dim: 3d
category: range_image
in: depth
out: normals
examples: [range_image]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# normals_from_depth — 3D `range_image` op

- **データ種**: `depth` → `normals`
- **呼び出し**: `import range_image; range_image.normals_from_depth(depth, fx=None, fy=None, cx=None, cy=None, orient_to_camera=True)` (または `ops3d.get("normals_from_depth")`)

## 使い方

organized 深度 → 向き付き単位法線 (H,W,3)。隣接画素の 3D 点の外積(格子構造を利用、O(HW))。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [range_image](../../../../examples_3d/range_image.py) — `py -3.11 examples_3d/range_image.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[icp_point2plane](../refine/icp_point2plane.md) · [compute_fpfh](../feature_register/compute_fpfh.md) · [shot_descriptor](../feature_register/shot_descriptor.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [reflect](../optics/reflect.md) · [refract](../optics/refract.md) · [render_shaded](../render/render_shaded.md) · [phong_shade](../render/phong_shade.md)

## 同カテゴリ(`range_image`)

[depth_to_organized_points](depth_to_organized_points.md) · [occlusion_edges](occlusion_edges.md) · [bearing_angle_image](bearing_angle_image.md)

---
*Provenance: range_image.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
