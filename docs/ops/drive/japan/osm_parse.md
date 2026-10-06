---
op: osm_parse
dim: drive
category: japan
in: any
out: table
examples: [poc_driving_japan_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# osm_parse — DRIVE `japan` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.osm_parse(source, *, origin=None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivejapan; drivejapan.osm_parse(source, *, origin=None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("osm_parse")`)

## 使い方

OSM XML(文字列かファイルパス)を読み、節点を局所平面座標 [m] に落とす。

返り値 ``{"origin": (lat0, lon0), "nodes": {id: {"xy": (x, y), "lat", "lon", "tags": {}}}, "ways": [{"id", "nodes": [id], "tags": {}}],
"bbox": (xmin, xmax, ymin, ymax)(``<bounds>`` があればそれ、無ければ節点の範囲), "n_nodes", "n_ways"}``。
origin が None なら ``<bounds>`` の中心(無ければ節点の平均)。``<nd ref>`` が未知の節点を指す way はその節点を落とす(件数を ``n_dangling`` に)。
**Raises** ``ValueError``: XML でない、``<osm>`` でない、節点が 1 つも無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md) · [latlon_to_local](latlon_to_local.md)

---
*Provenance: drivejapan.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
