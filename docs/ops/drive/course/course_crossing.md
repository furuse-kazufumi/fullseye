---
op: course_crossing
dim: drive
category: course
in: 
out: table
examples: [poc_driving_school]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# course_crossing — DRIVE `course` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.course_crossing(width=7.0, gauge=1.1, rail_outer=0.75, approach=6.0, stop_setback=0.5)` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_crossing(width=7.0, gauge=1.1, rail_outer=0.75, approach=6.0, stop_setback=0.5)`、台帳から引くなら `opsdrive.get("course_crossing")`)

## 使い方

踏切: 幅 w の道路(x 軸沿い)を線路が直角に横切る。踏切面(軌間 + レール外側 2 つ = 2.6 m)の両側に
``approach`` の直線。``rails`` (2, 2, 2) はレール 2 本の線分(x = L/2 ± gauge/2、道路幅いっぱい)、
``crossing_zone`` = (x0, x1) 踏切面、``stop_lines`` (1, 2, 2) は踏切面の ``stop_setback`` 手前の左車線。
多角形は矩形(レールはメタデータ)。規格: 軌間 1.1、レール外側 0.75 → ``params["regulation"]``。
面積 = w·(2(rail_outer + gauge/2) + 2·approach)。

**Raises** ``ValueError``: 幅・軌間・approach が正でない、rail_outer < 0、stop_setback < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](course_layout.md) · [course_occupancy](course_occupancy.md) · [course_contains](course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`course`)

[course_crank](course_crank.md) · [course_s_curve](course_s_curve.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_parallel_parking](course_parallel_parking.md) · [course_road](course_road.md) · [course_loop_bend](course_loop_bend.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
