---
op: polygon_fit_check
dim: drive
category: pegsym
in: matrix × matrix
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# polygon_fit_check — DRIVE `pegsym` op

- **データ種**: `matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.polygon_fit_check(peg_points, hole_vertices) -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.polygon_fit_check(peg_points, hole_vertices) -> 'dict'`、台帳から引くなら `opsdrive.get("polygon_fit_check")`)

## 使い方

点群(ペグの頂点、または傾けたペグの射影した頂点)を**平行移動だけで**凸多角形の穴に入れられるか —— 余裕 m を最大にする線形計画
max m s.t. n_j·(p + t) ≤ h_j − m(全点・全辺)を、3 本の制約が等号になる頂点の列挙で厳密に解く(辺は高々十数本、組はまとめて解く)。
返り ``fit``(m ≥ 0)、``margin`` [m] (負なら最小の食い込み)、``t``(最適な平行移動 (2,))、``active``(等号の辺の番号)。
**Raises** ValueError: 点群が (N ≥ 1, 2) でない・有限でない、穴が凸多角形でない、穴の法線が全方向を囲まない(有界でない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md) · [relative_yaw_from_images](relative_yaw_from_images.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
