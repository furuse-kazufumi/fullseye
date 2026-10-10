---
op: course_loop_bend
dim: drive
category: course
in: 
out: table
examples: [poc_driving_school, poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# course_loop_bend — DRIVE `course` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.course_loop_bend(radius=30.0, width=8.0, arc_pts=64)` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_loop_bend(radius=30.0, width=8.0, arc_pts=64)`、台帳から引くなら `opsdrive.get("course_loop_bend")`)

## 使い方

周回コースの端の半円(左へ 180° 回る): 進入 (0, 0, 0) → 中心 (0, R) の周りを回って退出 (0, 2R, π)。
多角形は外側の弧(半径 R + w/2)と内側の弧(R − w/2)で囲む環の半分。面積 = π R w(閉形式)、弧を
折線にした分だけ小さく、arc_pts を増やすと収束する。規格(周回コース): 幅 8 m 以上、おおむね長円形。

**Raises** ``ValueError``: R ≤ w/2(内側の弧が潰れる)、幅・半径が正でない、arc_pts が不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](course_layout.md) · [course_occupancy](course_occupancy.md) · [course_contains](course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`course`)

[course_crank](course_crank.md) · [course_s_curve](course_s_curve.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_parallel_parking](course_parallel_parking.md) · [course_crossing](course_crossing.md) · [course_road](course_road.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
