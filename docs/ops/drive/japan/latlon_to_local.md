---
op: latlon_to_local
dim: drive
category: japan
in: any × any
out: any
examples: [poc_driving_japan_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# latlon_to_local — DRIVE `japan` op

- **データ種**: `any × any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.latlon_to_local(lat, lon, origin) -> 'Tuple[np.ndarray, np.ndarray]'` (実装を直接呼ぶなら `import drivejapan; drivejapan.latlon_to_local(lat, lon, origin) -> 'Tuple[np.ndarray, np.ndarray]'`、台帳から引くなら `opsdrive.get("latlon_to_local")`)

## 使い方

緯度経度 [deg] → 原点 origin = (lat0, lon0) まわりの等距円筒近似の平面座標 (x 東, y 北) [m]。

x = R cos(lat0) Δλ、y = R Δφ(R = 6378137 m)。1 km 四方で 1e-5 の歪み(cos の変化)なので町 1 つには十分。配列可。
**Raises** ``ValueError``: 緯度経度が範囲外・非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md)

---
*Provenance: drivejapan.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
