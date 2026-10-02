---
op: course_road
dim: drive
category: course
in: 
out: table
examples: [poc_driving_longitudinal, poc_driving_school, poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# course_road — DRIVE `course` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.course_road(length=20.0, width=7.0)` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_road(length=20.0, width=7.0)`、台帳から引くなら `opsdrive.get("course_road")`)

## 使い方

連絡路(幹線の一部): 幅 w・長さ L の直線。課題コースの出口を周回コースへ戻す・幹線を延ばすための要素。
規格(幹線コース): 幅 7 m 以上、周回コースと連絡すること。面積 = w·L。

**Raises** ``ValueError``: 長さ・幅が正でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`
- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](course_layout.md) · [course_occupancy](course_occupancy.md) · [course_contains](course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`course`)

[course_crank](course_crank.md) · [course_s_curve](course_s_curve.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_parallel_parking](course_parallel_parking.md) · [course_crossing](course_crossing.md) · [course_loop_bend](course_loop_bend.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
