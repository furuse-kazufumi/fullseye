---
op: world_build
dim: drive
category: world
in: table
out: table
examples: [poc_driving_longitudinal, poc_driving_school, poc_driving_weather, poc_ttc_rss, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# world_build — DRIVE `world` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.world_build(course, *, props=(), kerb_height: 'float' = 0.15, kerb_width: 'float' = 0.3, lines: 'bool' = True, ground_margin: 'float' = 8.0, ground_step: 'float' = 4.0, joint_step: 'float' = 0.5, asset_root=None) -> 'dict'` (実装を直接呼ぶなら `import driveworld; driveworld.world_build(course, *, props=(), kerb_height: 'float' = 0.15, kerb_width: 'float' = 0.3, lines: 'bool' = True, ground_margin: 'float' = 8.0, ground_step: 'float' = 4.0, joint_step: 'float' = 0.5, asset_root=None) -> 'dict'`、台帳から引くなら `opsdrive.get("world_build")`)

## 使い方

コース(要素か layout)から世界を組む。

路面 = 全体を覆う平面(z = 0、ラベル 0)。各要素の多角形の縁に縁石(ラベル 1、継ぎ目の辺は除く)、
縁の内側 0.15 m に白線(ラベル 9)。坂道は斜面のメッシュ(ラベル 0)。交差点の ``signal_poses`` には信号機を立て
(初期状態 "red"、日本式: 向こう側の柱 + アームで車線上に横型 3 灯、roadjp)、``stop_lines`` に停止線、``crosswalks`` に横断歩道の縞。``props`` は ``(asset_name, x, y, yaw)`` か
``(asset_name, x, y, yaw[, dims[, paint]])`` の並び(paint = 車の車体色、:data:`CAR_PAINTS`)。返り値 = ``{"V","F","face_label","face_color","objects","bounds","course"}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`
- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`
- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_camera](world_camera.md) · [world_move](world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md) · [rss_longitudinal_opposite](../rss/rss_longitudinal_opposite.md)

## 同カテゴリ(`world`)

[world_camera](world_camera.md) · [load_asset](load_asset.md) · [world_move](world_move.md)

---
*Provenance: driveworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
