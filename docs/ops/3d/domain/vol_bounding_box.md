---
op: vol_bounding_box
dim: 3d
category: domain
in: voxel
out: primitive
examples: [rle_region_efficiency, roi_domain_boundary]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# vol_bounding_box — 3D `domain` op

- **データ種**: `voxel` → `primitive`
- **呼び出し**: `import volops; volops.vol_bounding_box(domain, margin=0)` (または `ops3d.get("vol_bounding_box")`)

## 使い方

Tight axis-aligned bounding box of a mask's foreground, in voxel indices.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rle_region_efficiency](../../../../examples_3d/rle_region_efficiency.py) — `py -3.11 examples_3d/rle_region_efficiency.py`
- [roi_domain_boundary](../../../../examples_3d/roi_domain_boundary.py) — `py -3.11 examples_3d/roi_domain_boundary.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`domain`)

[vol_reduce_domain](vol_reduce_domain.md) · [vol_crop_domain](vol_crop_domain.md) · [vol_uncrop](vol_uncrop.md) · [vol_tiled_map](vol_tiled_map.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
