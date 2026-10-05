---
op: course_parallel_parking
dim: drive
category: course
in: 
out: table
examples: [poc_driving_school]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# course_parallel_parking — DRIVE `course` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.course_parallel_parking(car_length=4.5, car_width=1.8, extra=3.0, road_width=7.0, approach=5.0, side='left')` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_parallel_parking(car_length=4.5, car_width=1.8, extra=3.0, road_width=7.0, approach=5.0, side='left')`、台帳から引くなら `opsdrive.get("course_parallel_parking")`)

## 使い方

縦列駐車: 幅 ``road_width`` の道路(x ∈ [0, 2·approach + bay_length])の路側に、長さ car_length + extra
(既定 7.5 m)× 幅 car_width の車室。**法令に数値なし(通達の別添は図)** —— 既定は慣行値。

左側通行に合わせ ``side="left"``(+y)が既定、``"right"`` で鏡映。``bay`` = (x0, x1, y0, y1)。
面積 = 道路 + 車室(すみ切りなし)。

**Raises** ``ValueError``: 寸法が正でない、extra < 0、side が left/right でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](course_layout.md) · [course_occupancy](course_occupancy.md) · [course_contains](course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`course`)

[course_crank](course_crank.md) · [course_s_curve](course_s_curve.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_crossing](course_crossing.md) · [course_road](course_road.md) · [course_loop_bend](course_loop_bend.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
