---
op: plane_from_3points
dim: 3d
category: geometry
in: points
out: primitive
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# plane_from_3points — 3D `geometry` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import match3d; match3d.plane_from_3points(a, b, c)` (または `ops3d.get("plane_from_3points")`)

## 使い方

3 点 → 平面(通過点, 単位法線)。3 座標で面が定まる(2D/3D 共通)。

返り値 ``(a, n)``: ``a`` は 1 点目、``n = (b−a)×(c−a)`` を単位化したもの(向きは a→b→c の
右ねじ)。引数は数値の 2 または 3 ベクトル(それ以外・次元の混在は ValueError)。3 点が同一
直線上なら ``n`` は零ベクトルのまま返る(例外は出ない)。
2 次元の点を渡すと ``np.cross`` がスカラー(符号つき面積の 2 倍)を返すので、``n`` はベクトルで
なく ±1 のスカラーになる。2-D で線の法線が欲しい場合は ``line_from_2points`` の方向を 90°
回して使うこと。
後段: ``distance_point_plane`` / ``intersect_line_plane`` / ``intersect_planes`` /
``angle_between_planes`` にこの ``(a, n)`` を渡す。点群からは ``fit_plane_3d``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md) · [distance_line_line](distance_line_line.md) · [intersect_line_plane](intersect_line_plane.md)

## 同カテゴリ(`geometry`)

[line_from_2points](line_from_2points.md) · [angle_3points](angle_3points.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md) · [distance_line_line](distance_line_line.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
