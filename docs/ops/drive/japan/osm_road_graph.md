---
op: osm_road_graph
dim: drive
category: japan
in: table
out: table
examples: [poc_driving_japan_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# osm_road_graph — DRIVE `japan` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.osm_road_graph(osm: 'dict', *, way_types: 'Sequence[str]' = ('motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link', 'unclassified', 'residential', 'living_street', 'service'), bbox=None, margin: 'float' = 0.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivejapan; drivejapan.osm_road_graph(osm: 'dict', *, way_types: 'Sequence[str]' = ('motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link', 'unclassified', 'residential', 'living_street', 'service'), bbox=None, margin: 'float' = 0.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("osm_road_graph")`)

## 使い方

OSM の読み込み結果から道路網を作る。

辺 = way の隣り合う節点の対 ``{"a", "b", "way", "highway", "width", "lanes", "width_from", "oneway", "length", "tags"}``。
節点 = ``{"xy", "degree", "features": [NODE_FEATURES の部分集合], "tags", "edges": [辺の索引]}``(辺に使われた節点だけ)。
``bbox`` = (xmin, xmax, ymin, ymax) を渡すと **両端が箱(+ margin)の外** の辺を落とす(片端だけ外の辺は残す = 箱の縁で道が切れる)。
``oneway`` は "yes" / "1" / "true" が順方向、"-1" / "reverse" は a, b を入れ替えて順方向にする。
**Raises** ``ValueError``: way_types に知らない種別、辺が 1 本も無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md) · [latlon_to_local](latlon_to_local.md)

---
*Provenance: drivejapan.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
