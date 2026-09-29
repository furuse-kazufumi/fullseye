---
op: course_turnaround
dim: drive
category: course
in: 
out: table
examples: [poc_driving_school]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# course_turnaround — DRIVE `course` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.course_turnaround(width=3.5, bay_width=3.5, depth=5.0, entry=5.0, corner_radius=1.0, arc_pts=16, side='left')` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_turnaround(width=3.5, bay_width=3.5, depth=5.0, entry=5.0, corner_radius=1.0, arc_pts=16, side='left')`、台帳から引くなら `opsdrive.get("course_turnaround")`)

## 使い方

方向変換コース(T 字): 幅 w の道路(x ∈ [0, 2E + bay_width])の側方中央に車庫(道路沿いの幅 bay_width、
奥行 depth)、車庫口の両側に出入口部 E ずつ。

別表第三の図(3JH00000217784)そのもの: 道路(幅 A)の途中に車庫(幅 B × 奥行 C)が直角に付き、車庫口の両側の
道路が出入口部 D、車庫口の凹頂点 2 つがすみ切り E。図は上向きの道路の右側に車庫があるが、ここでは
``side="left"``(+y)を既定にし ``"right"`` で鏡映する。車は道路を進み、後退で車庫に入れ、来た方向へ出る
(exit = (0, 0, π); 反対側へ出るときは配置側で向きを選ぶ)。centerline は道路の軸 → 車庫の軸。
面積 = (2E + bay_width)·w + depth·bay_width + 2r²(1 − π/4)。
規格: A = 3.5, B = 3.5, C = 5, D ≥ 5, E = 1 → ``params["regulation"]``。

**Raises** ``ValueError``: 幅・車庫幅・奥行・E が正でない、r < 0、E < r または depth < r(すみ切りが辺に
収まらない)、arc_pts が 1 以上の整数でない、side が left/right でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](course_layout.md) · [course_occupancy](course_occupancy.md) · [course_contains](course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`course`)

[course_crank](course_crank.md) · [course_s_curve](course_s_curve.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_parallel_parking](course_parallel_parking.md) · [course_crossing](course_crossing.md) · [course_road](course_road.md) · [course_loop_bend](course_loop_bend.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
