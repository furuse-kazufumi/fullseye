---
op: course_loop
dim: drive
category: course
in: 
out: table
examples: [poc_driving_school, poc_ttc_rss, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# course_loop — DRIVE `course` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.course_loop(straight=80.0, radius=30.0, width=8.0, arc_pts=64, overlap=0.05)` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_loop(straight=80.0, radius=30.0, width=8.0, arc_pts=64, overlap=0.05)`、台帳から引くなら `opsdrive.get("course_loop")`)

## 使い方

周回コース(長円形): 直線 2 本 + 半円 2 つを原点中心に置いた ``{"elements": [...], "placements": [...]}``
を返す(そのまま :func:`course_layout` に渡す)。反時計回りに、南の直線(東行き, y = −R)→ 東の半円 → 北の直線
(西行き, y = +R)→ 西の半円。直線は両端を ``overlap`` だけ半円に食い込ませる(3-D 化で継ぎ目に縁石が
立たないための重なり; 面積の和はその分だけ二重に数える)。規格(普通免許): 80 m 以上の直線走行部分、幅 8 m 以上。

**Raises** ``ValueError``: 直線が正でない、半円の条件(course_loop_bend)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](course_layout.md) · [course_occupancy](course_occupancy.md) · [course_contains](course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`course`)

[course_crank](course_crank.md) · [course_s_curve](course_s_curve.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_parallel_parking](course_parallel_parking.md) · [course_crossing](course_crossing.md) · [course_road](course_road.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
