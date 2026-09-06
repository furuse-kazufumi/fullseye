---
op: smallest_box3
dim: 3d
category: geometry
in: points
out: primitive
examples: [oriented_bounding_box]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# smallest_box3 — 3D `geometry` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import measure3d; measure3d.smallest_box3(points) -> 'dict'` (または `ops3d.get("smallest_box3")`)

## 使い方

Near-minimum-volume oriented bounding box (the 3-D ``smallest_rectangle2``).

Found by multi-start local refinement: seed the orientation from every convex-
hull face normal (the O'Rourke *case a* candidates — a box face flush with a
hull face), from the PCA axes, and from a fixed set of deterministic random
frames, then polish each by coordinate descent and keep the least-volume result.
This is **exact for box-like objects** (a rotated cuboid is recovered to machine
precision) and, unlike a PCA box (``fit_box3`` / ``pcseg.obb``), reaches the true
minimum on shapes whose optimum has no face flush with a hull face — e.g. a
regular tetrahedron, where the PCA / hull-face box is ~2x too large.

Honest limit: this is not a *proof* of global minimality for every convex shape.
The exact guarantee needs O'Rourke's full *case b* (two box faces each flush with
a hull **edge**), which is not enumerated here; local refinement drives seeds into
that regime instead. Empirically the result is at or below a dense brute-force
rotation search, but a pathological shape could leave a small gap.

Returns ``center`` (``cd/cr/cc``), ``axes`` (3, 3 — unit ROW vectors), sorted
half-extents ``l1 >= l2 >= l3``, full ``size``, ``volume``, and ``corners``
(8, 3). Deterministic (fixed random seeds). Raises ``ValueError`` on < 4 points
or a coplanar/degenerate set (no 3-D hull).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [oriented_bounding_box](../../../../examples_3d/oriented_bounding_box.py) — `py -3.11 examples_3d/oriented_bounding_box.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md) · [distance_line_line](distance_line_line.md) · [intersect_line_plane](intersect_line_plane.md)

## 同カテゴリ(`geometry`)

[line_from_2points](line_from_2points.md) · [plane_from_3points](plane_from_3points.md) · [angle_3points](angle_3points.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md)

---
*Provenance: measure3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
