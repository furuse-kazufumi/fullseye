---
op: puck_pinhole_camera
dim: drive
category: puck
in: table × scalar × scalar × signal
out: table
examples: [poc_air_hockey_intercept]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# puck_pinhole_camera — DRIVE `puck` op

- **データ種**: `table × scalar × scalar × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.puck_pinhole_camera(table: 'dict', height: 'float', fovy_deg: 'float', shape) -> 'dict'` (実装を直接呼ぶなら `import puck; puck.puck_pinhole_camera(table: 'dict', height: 'float', fovy_deg: 'float', shape) -> 'dict'`、台帳から引くなら `opsdrive.get("puck_pinhole_camera")`)

## 使い方

真上の針穴カメラ(位置 (0, 0, h)、−z を見る、up = +y、MuJoCo のカメラ規約)をホモグラフィに: col = W/2 + f x/h、
row = H/2 − f y/h、f = (H/2)/tan(fovy/2)。パック上面の高さ(≈ 0.02 m)は無視(視差 h に対して 1 % 強、残差は門で測る)。
``shape`` = (H, W)。返り値は :func:`puck_camera` と同じ形。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_air_hockey_intercept](../../../../examples/poc_air_hockey_intercept.py) — `py -3.11 examples/poc_air_hockey_intercept.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`puck`)

[puck_table](puck_table.md) · [puck_wall_bounce](puck_wall_bounce.md) · [puck_slide_predict](puck_slide_predict.md) · [puck_state_at](puck_state_at.md) · [puck_crossing_point](puck_crossing_point.md) · [puck_mirror_path](puck_mirror_path.md) · [puck_stop_distance](puck_stop_distance.md) · [puck_camera](puck_camera.md)

---
*Provenance: puck.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
