---
op: course_s_curve
dim: drive
category: course
in: 
out: table
examples: [poc_driving_school, poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# course_s_curve — DRIVE `course` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.course_s_curve(width=3.5, radius_outer=7.5, arc_fraction=0.375, entry=4.0, arc_pts=48)` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_s_curve(width=3.5, radius_outer=7.5, arc_fraction=0.375, entry=4.0, arc_pts=48)`、台帳から引くなら `opsdrive.get("course_s_curve")`)

## 使い方

曲線コース(S 字): 直線 E → 左弧(中心角 2π·f)→ 右弧(同じ)→ 直線 E。

外径 R_o = ``radius_outer``、内径 R_i = R_o − w、中心線の半径 R_c = (R_o + R_i)/2。2 つの弧は共通接線点で
曲率の向きが反転する。多角形は中心線の標本点を法線方向に ±w/2 ずらして作る(弧の標本点は外円・内円の
上に厳密に乗る)。面積 = 2πf(R_o² − R_i²) + 2Ew。規格: A = 3.5, B = 7.5, C = 3/8 → ``params["regulation"]``。

**Raises** ``ValueError``: 幅・外径が正でない、R_o ≤ w(内径が 0 以下)、arc_fraction ∉ (0, 1)、E < 0、
arc_pts が 1 以上の整数でない。

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

[course_crank](course_crank.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_parallel_parking](course_parallel_parking.md) · [course_crossing](course_crossing.md) · [course_road](course_road.md) · [course_loop_bend](course_loop_bend.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
