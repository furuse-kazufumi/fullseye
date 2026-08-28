---
op: intersect_line_plane
dim: 3d
category: geometry
in: primitive
out: position
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# intersect_line_plane — 3D `geometry` op

- **データ種**: `primitive` → `position`
- **呼び出し**: `import match3d; match3d.intersect_line_plane(line_pt, d, plane_pt, n)` (または `ops3d.get("intersect_line_plane")`)

## 使い方

直線 ∩ 平面 → 点(平行なら None)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_peak_newton](../refine/refine_peak_newton.md) · [refine_translation_lk](../refine/refine_translation_lk.md) · [refine_lm](../refine/refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`geometry`)

[line_from_2points](line_from_2points.md) · [plane_from_3points](plane_from_3points.md) · [angle_3points](angle_3points.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
