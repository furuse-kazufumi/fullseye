---
op: osm_route
dim: drive
category: japan
in: table
out: table
examples: [poc_driving_japan_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# osm_route — DRIVE `japan` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.osm_route(graph: 'dict', src: 'int', dst: 'int', *, side: 'str' = 'left', step: 'float' = 0.5, lane_offset=None, signal_setback: 'float' = 1.0, crossing_setback: 'float' = 3.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivejapan; drivejapan.osm_route(graph: 'dict', src: 'int', dst: 'int', *, side: 'str' = 'left', step: 'float' = 0.5, lane_offset=None, signal_setback: 'float' = 1.0, crossing_setback: 'float' = 3.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("osm_route")`)

## 使い方

2 節点間の最短路(Dijkstra、一方通行を守る)を車線中心の折線にし、停止線を弧長で並べる。

車線中心 = 辺の中心線を通行側(side)へ **幅/4**(両方向路)か 0(一方通行)だけ寄せた線(``lane_offset`` で上書き)。節点では隣り合う
法線の平均で継ぐ(マイター)。停止線(drivetown.town_run が読む形 ``{"s", "x", "y", "yaw", "kind", "node", "element"}``):
``traffic_signals`` の節点 = "intersection"(交差する道の半幅 = 交差点の縁、の signal_setback 手前。同じ道の続きは数えない)、``stop`` / ``give_way`` = "stop_sign"(同じ位置)、
``level_crossing`` = "crossing"(crossing_setback 手前、``crossing_zone`` = レールの前後 1.5 m)。経路の最初の節点は飛ばす。
返り値 ``{"kind": "route", "nodes", "edges", "polyline": (K,2), "cum": (K,), "length", "stop_lines", "side", "waypoints": (n,3) 節点の
車線中心, "crosswalks": [s]}``。
**Raises** ``ValueError``: 節点が無い、到達不能、side が不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md) · [latlon_to_local](latlon_to_local.md)

---
*Provenance: drivejapan.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
