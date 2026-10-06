---
op: osm_synthetic
dim: drive
category: japan
in: 
out: any
examples: [poc_driving_japan_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# osm_synthetic — DRIVE `japan` op

- **データ種**: `なし` → `any`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.osm_synthetic(kind: 'str' = 'grid', *, origin=(35.6716, 139.765), n: 'int' = 3, pitch: 'float' = 80.0) -> 'str'` (実装を直接呼ぶなら `import drivejapan; drivejapan.osm_synthetic(kind: 'str' = 'grid', *, origin=(35.6716, 139.765), n: 'int' = 3, pitch: 'float' = 80.0) -> 'str'`、台帳から引くなら `opsdrive.get("osm_synthetic")`)

## 使い方

テストと fuzz 用の最小の OSM XML(本物と同じ要素: bounds / node / way / tag)。

"grid" = n × n の格子(東西 = primary、lanes=2、南北 = residential、幅は既定)。中央の交差点に ``highway=traffic_signals``、
東の縁の中段(T 字路)に ``highway=stop``、西の辺の途中に ``highway=crossing``、南の辺の途中に ``railway=level_crossing``。
"line" = 東西 1 本の residential(長さ pitch × (n − 1))。**Raises** ``ValueError``: kind が未知、n < 2、pitch ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`japan`)

[osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md) · [latlon_to_local](latlon_to_local.md)

---
*Provenance: drivejapan.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
