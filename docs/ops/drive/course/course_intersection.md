---
op: course_intersection
dim: drive
category: course
in: 
out: table
examples: [poc_driving_school]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# course_intersection — DRIVE `course` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.course_intersection(width=7.0, arm=20.0, corner_radius=3.0, arc_pts=16, stop_setback=1.0)` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_intersection(width=7.0, arm=20.0, corner_radius=3.0, arc_pts=16, stop_setback=1.0)`、台帳から引くなら `opsdrive.get("course_intersection")`)

## 使い方

幹線コースの十字交差点: 幅 w の道路 2 本が原点で直交、各腕の長さ ``arm``(交差部の縁から)、
凹頂点 4 つを半径 ``corner_radius`` で削る。

面積 = 2(2·arm + w)w − w² + 4r²(1 − π/4)。左側通行に合わせ、各流入路(東行 → 北行 → 西行 → 南行の順、
流入方向 yaw = 0, π/2, π, 3π/2)に **停止線 1 本**(``stop_lines`` (4, 2, 2): 流入車線 = 進行方向左半分
を横切る線分、すみ切りの終わりから ``stop_setback`` 手前)と **信号機 1 基**(``signal_poses`` (4, 3):
停止線の位置の左側 0.5 m 外、yaw = 流入車に向く向き = 流入方向 + π)。centerline は東西の道路軸。
規格: 幅 ≥ 7、すみ切り ≥ 3(警視庁 審査基準)→ ``params["regulation"]``。

**Raises** ``ValueError``: 幅・腕が正でない、r < 0、arm < r + stop_setback、arc_pts が不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](course_layout.md) · [course_occupancy](course_occupancy.md) · [course_contains](course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`course`)

[course_crank](course_crank.md) · [course_s_curve](course_s_curve.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_parallel_parking](course_parallel_parking.md) · [course_crossing](course_crossing.md) · [course_road](course_road.md) · [course_loop_bend](course_loop_bend.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
