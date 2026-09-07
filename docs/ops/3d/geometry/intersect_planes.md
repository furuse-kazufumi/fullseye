---
op: intersect_planes
dim: 3d
category: geometry
in: primitive
out: primitive
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# intersect_planes — 3D `geometry` op

- **データ種**: `primitive` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.intersect_planes(p1, n1, p2, n2)` (実装を直接呼ぶなら `import match3d; match3d.intersect_planes(p1, n1, p2, n2)`、台帳から引くなら `ops3d.get("intersect_planes")`)

## 使い方

平面 ∩ 平面 → 直線(通過点, 方向)。平行なら None。

方向 ``d = n̂1 × n̂2`` を単位化し、``n̂1·p = n̂1·p1``、``n̂2·p = n̂2·p2``、``d·p = 0`` の 3×3 を
解いて通過点 ``p`` を求める(``d·p = 0`` なので **原点に最も近い点**)。返り値 ``(p(3,), d(3,))``。
``|n1 × n2| < 1e-9``(平行・同一面)なら **None**。
引数は数値 3 ベクトル(``np.cross`` と 3×3 の solve を使うので **3-D 専用**。2-D を渡すと
配列構築で失敗する)。次元の混在は ValueError。
用途: ``fit_plane_3d`` した 2 面の稜線、箱のエッジの抽出 → ``distance_point_line`` でエッジ
からの距離。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md) · [distance_line_line](distance_line_line.md) · [intersect_line_plane](intersect_line_plane.md)

## 同カテゴリ(`geometry`)

[line_from_2points](line_from_2points.md) · [plane_from_3points](plane_from_3points.md) · [angle_3points](angle_3points.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
