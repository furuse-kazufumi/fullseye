---
op: aabb
dim: 3d
category: bounds
in: points
out: primitive
examples: [hull_bounds]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# aabb — 3D `bounds` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.aabb(points)` (実装を直接呼ぶなら `import pcseg; pcseg.aabb(points)`、台帳から引くなら `ops3d.get("aabb")`)

## 使い方

Axis-aligned bounding box. Returns ``(min (3,), max (3,))``.

点群の各軸の最小値と最大値をそのまま返す(``P.min(0)``, ``P.max(0)``)。返り値は 2 つの (3,)
float64 配列で、順に ``(xmin, ymin, zmin)`` と ``(xmax, ymax, zmax)``(軸の並びは入力の列順)。
箱の大きさは ``max - min``、中心は ``(min + max) / 2``。単位は座標の単位。

- ``points``: (N,3) 以外の形状は ``ValueError``、空の点群も ``ValueError``(fail-closed)。
- NaN を含む点があると ``min`` / ``max`` が NaN になる(非有限の検査はしない)。

用途: voxel 化(``occupancy_grid`` / ``points_to_voxel`` の ``bounds``)の領域決め、
``obb``(PCA で向きを合わせた箱)との比較。軸に沿わない細長い物体では AABB は大きく余るので、
把持幅の推定には ``obb`` の ``extents`` を使う。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [hull_bounds](../../../../examples_3d/hull_bounds.py) — `py -3.11 examples_3d/hull_bounds.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [distance_segment_segment](../geometry/distance_segment_segment.md)

## 同カテゴリ(`bounds`)

[convex_hull](convex_hull.md) · [obb](obb.md) · [min_enclosing_sphere](min_enclosing_sphere.md)

---
*Provenance: pcseg.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
