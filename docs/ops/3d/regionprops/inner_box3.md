---
op: inner_box3
dim: 3d
category: regionprops
in: voxel
out: primitive
examples: [inner_box_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# inner_box3 — 3D `regionprops` op

- **データ種**: `voxel` → `primitive`
- **呼び出し**: `import regionprops3d; regionprops3d.inner_box3(vol) -> 'dict'` (または `ops3d.get("inner_box3")`)

## 使い方

二値ボクセル領域に完全に内接する最大の軸平行ボックス(2-D ``inner_rectangle1`` の

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [inner_box_inspection](../../../../examples_3d/inner_box_inspection.py) — `py -3.11 examples_3d/inner_box_inspection.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`regionprops`)

[label_components](label_components.md) · [region_props](region_props.md) · [largest_component](largest_component.md) · [filter_by_volume](filter_by_volume.md) · [vol_label](vol_label.md) · [vol_region_props](vol_region_props.md)

---
*Provenance: regionprops3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
