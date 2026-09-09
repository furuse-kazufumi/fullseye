---
op: obb
dim: 3d
category: bounds
in: points
out: primitive
examples: [hull_bounds]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# obb — 3D `bounds` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.obb(points) -> 'dict'` (実装を直接呼ぶなら `import pcseg; pcseg.obb(points) -> 'dict'`、台帳から引くなら `ops3d.get("obb")`)

## 使い方

Oriented bounding box by PCA.

Returns ``{center, axes (3,3 columns = box axes), extents (3, half-widths),
corners (8,3)}``. The tight-fitting box a manipulator uses to reason about an
object's size and grasp width once it has been segmented out.

手順: 重心 ``c`` を引いた点群の SVD(``full_matrices=False``)で主軸 ``axes``(列 = 特異値の降順、
第 1 列が最も広がる方向)を取り、点を主軸座標に写して各軸の min/max から半幅 ``extents`` と
箱中心 ``center``(重心とは一般に異なる)を求める。``corners`` は ``center + (±extents) @ axes.T``
の 8 点で、符号の組合せは ``meshgrid([-1,1],[-1,1],[-1,1])`` の順。

- ``points``: (N,3) 以外は ``ValueError``、2 点未満も ``ValueError``。
- PCA の主軸は「最小体積の箱」を保証しない(点の分布に沿うだけ)。主軸の符号は SVD の任意性で
  決まり、点の分布が等方に近い(特異値が縮退する)と軸の向きは不安定になる。
- ``extents`` は半幅なので辺長は ``2 * extents``。単位は座標の単位。

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

[convex_hull](convex_hull.md) · [aabb](aabb.md) · [min_enclosing_sphere](min_enclosing_sphere.md)

---
*Provenance: pcseg.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
