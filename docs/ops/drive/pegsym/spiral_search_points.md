---
op: spiral_search_points
dim: drive
category: pegsym
in: scalar × scalar × scalar
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# spiral_search_points — DRIVE `pegsym` op

- **データ種**: `scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spiral_search_points(pitch: 'float', step: 'float', r_max: 'float', centre=(0.0, 0.0)) -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.spiral_search_points(pitch: 'float', step: 'float', r_max: 'float', centre=(0.0, 0.0)) -> 'dict'`、台帳から引くなら `opsdrive.get("spiral_search_points")`)

## 使い方

横ずれの探索点: Archimedes のらせん r = p φ/(2π) を弧長 ``step`` [m] ごとに(中心から)、半径 ``r_max`` まで。隣の巻きとの間隔 =
``pitch``。面取りが捕まえる半径を c とすると、p ≤ 2c かつ step ≤ 2c で抜けなく覆う(隣の巻きの間の点の最悪の距離 √((p/2)² + (s/2)²)
≤ c が十分条件、``worst_gap`` で返す)。返り ``points``(N, 2)、``worst_gap``、``n``。
**Raises** ValueError: pitch・step・r_max ≤ 0、点が 200,000 を超える。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
