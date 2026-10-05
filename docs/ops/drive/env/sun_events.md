---
op: sun_events
dim: drive
category: env
in: scalar × scalar × scalar × scalar × scalar
out: table
examples: [poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# sun_events — DRIVE `env` op

- **データ種**: `scalar × scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sun_events(year: 'int', month: 'int', day: 'int', lat: 'float', lon: 'float', tz_hours: 'float' = 9.0, *, h0: 'float' = -0.8333) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import driveenv; driveenv.sun_events(year: 'int', month: 'int', day: 'int', lat: 'float', lon: 'float', tz_hours: 'float' = 9.0, *, h0: 'float' = -0.8333) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("sun_events")`)

## 使い方

その日(地方の暦日)の日の出・南中・日の入りの時刻と、日の出入りの方位・南中の高度。

日の出入り = 太陽の中心の **幾何の** 高度が ``h0``(既定 −0.8333° = 大気差 34′ + 視半径 16′、上辺が地平線に接する)を
横切る時刻。``h0="naoj"`` で国立天文台 暦計算室の定義(太陽の上辺が視地平線、地平大気差 35′8″、視半径は距離から)。
南中 = 時角 0。どちらも sun_at を時刻について解く(二分法、1e-6 日 ≈ 0.1 秒まで)。

Returns
-------
dict : ``sunrise`` / ``transit`` / ``sunset``(タイムゾーンつき datetime、日の出入りが無ければ None)、
``sunrise_azimuth`` / ``sunset_azimuth``(度)、``transit_altitude``(度、大気差なしの幾何の高度と、``transit_altitude_apparent``)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [koschmieder](koschmieder.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md) · [road_row_distance](road_row_distance.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
