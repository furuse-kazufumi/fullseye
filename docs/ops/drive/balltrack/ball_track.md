---
op: ball_track
dim: drive
category: balltrack
in: table
out: table
examples: [poc_ball_bounce, poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# ball_track — DRIVE `balltrack` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ball_track(detections, *, max_jump: 'float' = 40.0, min_score: 'float' = 0.0) -> 'dict'` (実装を直接呼ぶなら `import balltrack; balltrack.ball_track(detections, *, max_jump: 'float' = 40.0, min_score: 'float' = 0.0) -> 'dict'`、台帳から引くなら `opsdrive.get("ball_track")`)

## 使い方

コマごとの候補列 ``detections[k] = ball_detect(frame_k)`` を 1 本の軌跡に繋ぐ(等速予測に最も近い候補、``max_jump`` px 以内)。

返り値 ``{"frame" (N,), "col" (N,), "row" (N,), "radius" (N,), "found" (K,) bool}``(見つからないコマは飛ばす)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`balltrack`)

[ball_detect](ball_detect.md) · [kalman_ca](kalman_ca.md) · [triangulate_dlt](triangulate_dlt.md) · [track_triangulate](track_triangulate.md) · [bounce_detect](bounce_detect.md) · [marker_direction](marker_direction.md) · [spin_from_markers](spin_from_markers.md) · [spin_from_marker_sequence](spin_from_marker_sequence.md)

---
*Provenance: balltrack.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
