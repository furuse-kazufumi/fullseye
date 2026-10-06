---
op: course_crank
dim: drive
category: course
in: 
out: table
examples: [poc_driving_school, poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# course_crank — DRIVE `course` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.course_crank(width=3.5, between=12.0, entry=4.0, corner_radius=1.0, arc_pts=16)` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_crank(width=3.5, between=12.0, entry=4.0, corner_radius=1.0, arc_pts=16)`、台帳から引くなら `opsdrive.get("course_crank")`)

## 使い方

屈折コース(クランク、Z 形): 進入 → 左 90° → B → 右 90° → 退出。

別表第三の図(3JH00000217782)の測り方に合わせる: 幅 A = w、曲角間の長さ B は一方の道の外壁から
向かいの道の内壁まで(= 中心線の曲角間距離)、出入口部 C は横断する帯の壁から出入口まで(中心線では
C + w/2)、すみ切り D は曲角部の **内側** の角(外側の角は正方形のまま)。中心線は
(0,0)→(C+w/2, 0)→(C+w/2, B)→(2C+w, B)、長さ L = 2C + w + B。面積 = w·L + 2r²(1 − π/4)
(導出はモジュール docstring)。規格(普通免許): A = 3.5, B = 12, C ≥ 4, D = 1 → ``params["regulation"]``。

**Raises** ``ValueError``: 幅・B・C が正でない、r < 0、C < r(すみ切りが出入口にはみ出る)、
B < w + r(2 つの角が重なる)、arc_pts が 1 以上の整数でない。

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

[course_s_curve](course_s_curve.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_parallel_parking](course_parallel_parking.md) · [course_crossing](course_crossing.md) · [course_road](course_road.md) · [course_loop_bend](course_loop_bend.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
