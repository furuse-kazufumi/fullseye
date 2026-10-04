---
op: osm_road_mask
dim: drive
category: japan
in: table
out: table
examples: [poc_driving_japan_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# osm_road_mask — DRIVE `japan` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.osm_road_mask(graph: 'dict', *, step: 'float' = 0.5, margin: 'float' = 6.0, bbox=None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivejapan; drivejapan.osm_road_mask(graph: 'dict', *, step: 'float' = 0.5, margin: 'float' = 6.0, bbox=None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("osm_road_mask")`)

## 使い方

辺を幅つきの線分(端は丸)として描いた **道路の和集合** の 2 値画像。

画素 (r, c) の中心 = (xmin + (c + ½) step, ymin + (r + ½) step)、行は y の増える向き(数学座標。表示で上下を返す)。
返り値 ``{"mask": (H, W) bool, "xmin", "ymin", "step", "shape", "area_m2": 画素数 × step²}``。
**Raises** ``ValueError``: step ≤ 0、画像が 4e7 画素を超える(step を粗く)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md) · [latlon_to_local](latlon_to_local.md)

---
*Provenance: drivejapan.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
