---
op: fit_circle_3d
dim: 3d
category: geometry
in: points
out: primitive
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fit_circle_3d — 3D `geometry` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_circle_3d(points)` (実装を直接呼ぶなら `import match3d; match3d.fit_circle_3d(points)`、台帳から引くなら `ops3d.get("fit_circle_3d")`)

## 使い方

点群 → 3D 円(平面フィット → 面内で 2D 円フィット)。返り値 (center, radius, normal)。

``fit_plane_3d`` で面 ``(c, n)`` を取り、面内の正規直交基底 ``(e1, e2)`` に点を射影して 2-D の
代数円フィット(``|q|² = 2·cc·q + k`` の ``lstsq``)を解き、中心を 3-D に戻す。``(N,3)`` で
3 点未満は ValueError(3 点なら面は厳密、円は 3 点を通る)。
``center`` は面上の 3-D 点、``radius`` は float(負の根は 0 に clamp)、``normal`` は面の単位法線
(符号任意)。円弧の一部だけ・面から外れた点が多いと半径が偏る(代数フィットの性質。面内残差は
返さない)。
用途: 穴・フランジ・リングの中心と径、``distance_point_line`` で軸からの偏心。

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
