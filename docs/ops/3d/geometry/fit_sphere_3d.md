---
op: fit_sphere_3d
dim: 3d
category: geometry
in: points
out: primitive
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fit_sphere_3d — 3D `geometry` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_sphere_3d(points)` (実装を直接呼ぶなら `import match3d; match3d.fit_sphere_3d(points)`、台帳から引くなら `ops3d.get("fit_sphere_3d")`)

## 使い方

点群 → 最小二乗球(代数フィット)。返り値 (center, radius)。配管/ボール計測に。

``|p|² = 2c·p + (r² − |c|²)`` を ``[2p, 1]`` の線形最小二乗(``lstsq``)で解く代数フィット
(幾何距離の最小化ではないので、球の一部しか見えていない・ノイズが大きいと半径が偏る)。
``(N,3)`` で 4 点未満は ValueError。``radius`` は ``sqrt(max(s + |c|², 0))`` で負は 0 に clamp。
点が同一平面上・共線だと ``lstsq`` の最小ノルム解が黙って返る(検証は無い。残差も返さないので
``|p − c| − r`` で確かめる)。
幾何距離で追い込むなら本 op の結果を初期値にして非線形最小二乗、外れ値には ``ransac_sphere``。
voxel からの検出は ``hough_sphere_3d``。

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
