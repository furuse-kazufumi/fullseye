---
op: fit_line_3d
dim: 3d
category: geometry
in: points
out: primitive
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fit_line_3d — 3D `geometry` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_line_3d(points)` (実装を直接呼ぶなら `import match3d; match3d.fit_line_3d(points)`、台帳から引くなら `ops3d.get("fit_line_3d")`)

## 使い方

点群 → 最小二乗直線(通過点=重心, 方向=最大主軸)。返り値 (point, direction)。

``(N,3)`` の点群(数値・列数 3 でなければ ValueError、2 点未満も ValueError)の重心 ``c`` と
散布行列 ``(P−c)ᵀ(P−c)`` の最大固有値の固有ベクトルを返す(直交距離の二乗和を最小化する直線。
z=f(x) 型の回帰ではない)。``direction`` は単位ベクトルで **符号は任意**(``eigh`` 次第。向きを
揃えるなら ``(P[-1] − P[0]) @ direction`` の符号で反転)。
2 点だけなら 2 点を通る直線。点が平面状に広がっていると最大軸は「最も長い方向」になるだけで
直線とは限らない(残差は返さないので ``distance_point_line`` で確かめる)。外れ値に弱い
(ロバストには ``ransac_line``)。3-D 専用(2-D 点は ValueError)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md) · [distance_line_line](distance_line_line.md) · [distance_segment_segment](distance_segment_segment.md)

## 同カテゴリ(`geometry`)

[line_from_2points](line_from_2points.md) · [plane_from_3points](plane_from_3points.md) · [angle_3points](angle_3points.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
