---
op: world_camera
dim: drive
category: world
in: table × matrix × matrix
out: table
examples: [poc_ball_bounce, poc_driving_longitudinal, poc_driving_school, poc_kendama, poc_table_tennis_spin, poc_ttc_rss, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# world_camera — DRIVE `world` op

- **データ種**: `table × matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.world_camera(world: 'dict', pose, K, width: 'int' = 640, height: 'int' = 400, *, light=(0.3, -0.5, 0.8), ambient: 'float' = 0.35, sky=(0.62, 0.75, 0.92), ego=None) -> 'dict'` (実装を直接呼ぶなら `import driveworld; driveworld.world_camera(world: 'dict', pose, K, width: 'int' = 640, height: 'int' = 400, *, light=(0.3, -0.5, 0.8), ambient: 'float' = 0.35, sky=(0.62, 0.75, 0.92), ego=None) -> 'dict'`、台帳から引くなら `opsdrive.get("world_camera")`)

## 使い方

世界をカメラで撮る: ``{"color" (H,W,3), "label" (H,W) int(−1 = 空), "depth" (H,W), "face" (H,W), "shade" (H,W)}``。

render3d.render_mesh(attributes=True) の三角形 id から面の色・ラベルを引き、色は Lambert
(``ambient + (1−ambient)·max(n·l, 0)``、n は render3d のカメラ系法線を世界系に戻さず、光をカメラ系で与える)。
``ego=(V, F, color)`` を渡すと自車のメッシュも一緒に描く(世界には足さない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`
- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`
- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](world_build.md) · [world_move](world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md) · [rss_longitudinal_opposite](../rss/rss_longitudinal_opposite.md)

## 同カテゴリ(`world`)

[world_build](world_build.md) · [load_asset](load_asset.md) · [world_move](world_move.md)

---
*Provenance: driveworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
