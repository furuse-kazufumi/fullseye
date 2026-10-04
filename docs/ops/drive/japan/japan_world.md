---
op: japan_world
dim: drive
category: japan
in: table
out: table
examples: [poc_driving_japan_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# japan_world — DRIVE `japan` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.japan_world(graph: 'dict', *, step: 'float' = 0.5, kerb_height: 'float' = 0.15, kerb_width: 'float' = 0.3, ground_step: 'float' = 2.0, margin: 'float' = 6.0, buildings=None, props: 'bool' = True, pole_pitch: 'float' = 30.0, lines: 'bool' = True, tolerance_px: 'float' = 0.75, side: 'str' = 'left') -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivejapan; drivejapan.japan_world(graph: 'dict', *, step: 'float' = 0.5, kerb_height: 'float' = 0.15, kerb_width: 'float' = 0.3, ground_step: 'float' = 2.0, margin: 'float' = 6.0, buildings=None, props: 'bool' = True, pole_pitch: 'float' = 30.0, lines: 'bool' = True, tolerance_px: 'float' = 0.75, side: 'str' = 'left') -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("japan_world")`)

## 使い方

道路網から日本の町の 3-D 世界(driveworld 形式)を組む。

路面 = 全体の格子平面(z 0、ラベル 0)。道路の和集合の **穴** = 街区: 歩道の面(z = kerb_height、ラベル 15)と縁石の帯(ラベル 1)。
外側の縁にも縁石。車線の印(ラベル 9): 2 車線の両方向路は中央線を白の破線(5 m / 5 m)、4 車線以上は実線、車線境界は破線。交差点では
他の辺の半幅ぶん印を切る。``props`` なら節点の特徴に: 信号機(``traffic_signals``、進入する辺ごと、交差点の向こう側・左)、横断歩道
(``crossing``、進行方向に平行な 0.45 m の縞、ラベル 12)、一時停止(``stop`` / ``give_way``: 標識 + 停止線 + 「止まれ」、進入する辺ごと)、
踏切(``level_crossing``: 2 本のレール(ラベル 8)+ 踏切警標 + 停止線)。生活道路(residential / unclassified / living_street)の
通行側の縁に ``pole_pitch`` 間隔で電柱(ラベル 16)。``buildings`` = plateau_parse の建物の列なら押し出し柱(ラベル 14)。
返り値 = driveworld の世界 + ``{"graph", "roadmask", "loops", "signals": [{"node", "edge", "object", "pose"}], "stats": {...}}``。
**Raises** ``ValueError``: side が left/right 以外、kerb/step が不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_stats](japan_stats.md) · [latlon_to_local](latlon_to_local.md)

---
*Provenance: drivejapan.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
