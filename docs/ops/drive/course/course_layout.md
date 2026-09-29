---
op: course_layout
dim: drive
category: course
in: table × table
out: table
examples: [poc_driving_school, poc_ttc_rss, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# course_layout — DRIVE `course` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.course_layout(elements, placements)` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_layout(elements, placements)`、台帳から引くなら `opsdrive.get("course_layout")`)

## 使い方

複数の要素を剛体運動 ``(x, y, yaw)`` で配置して 1 つの dict にする。

各要素の polygon / centerline / rails / stop_lines は点として、entry / exit / signal_poses は姿勢として
(yaw も回す)変換する。``profile``(坂道の (s, z))は要素の局所弧長なのでそのまま。返り値は
``{"kind": "layout", "elements": [変換済み要素(各々 "placement" を持つ)], "polygon": None,
"bounds": (xmin, xmax, ymin, ymax), "placements": [...]}``。内外判定は要素の和(``course_contains`` /
``course_occupancy``)。要素の重なりは和として扱う。

**Raises** ``ValueError``: 要素が空・要素と配置の数が違う・要素が dict でない・配置が 3 要素で有限でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_occupancy](course_occupancy.md) · [course_contains](course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md) · [rss_longitudinal_opposite](../rss/rss_longitudinal_opposite.md)

## 同カテゴリ(`course`)

[course_crank](course_crank.md) · [course_s_curve](course_s_curve.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_parallel_parking](course_parallel_parking.md) · [course_crossing](course_crossing.md) · [course_road](course_road.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
