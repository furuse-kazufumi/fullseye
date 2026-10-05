---
op: polygon_offset
dim: drive
category: pegsym
in: matrix × scalar
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# polygon_offset — DRIVE `pegsym` op

- **データ種**: `matrix × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.polygon_offset(vertices, clearance: 'float') -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.polygon_offset(vertices, clearance: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("polygon_offset")`)

## 使い方

凸多角形の各辺を外へ ``clearance`` [m] ずらした多角形(角は尖ったまま = 穴の図面の作り方)。正多角形なら相似拡大で、向きと
対称は変わらない。返り ``vertices``・``normals``・``offsets``(n·x ≤ h)。**Raises** ValueError: 凸でない、clearance < 0 か有限でない、
ずらすと辺が消える(凹みを持つ角は無いので、ここでは起きない形だけを通す)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md) · [relative_yaw_from_images](relative_yaw_from_images.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
