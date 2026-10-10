---
op: sun_at
dim: drive
category: env
in: any × scalar × scalar
out: table
examples: [poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# sun_at — DRIVE `env` op

- **データ種**: `any × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sun_at(when, lat: 'float', lon: 'float', *, refraction: 'bool' = True) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import driveenv; driveenv.sun_at(when, lat: 'float', lon: 'float', *, refraction: 'bool' = True) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("sun_at")`)

## 使い方

日時(タイムゾーンつき datetime かユリウス日)の太陽の高度・方位。式は :func:`geocam.sun_position`(NOAA の太陽位置の式
= Meeus "Astronomical Algorithms" 第 25 章の低精度版、NOAA の大気差)をそのまま使い、日時の受け方と地球–太陽の距離を足す。

Returns
-------
dict : ``elevation``(度、``refraction`` なら大気差つきの見かけ)、``elevation_geometric``、``azimuth``(北から時計回り 度)、
``declination``、``eq_time``(均時差 分)、``hour_angle``(度)、``jd``、``distance_au``、``semidiameter``(度)。

NOAA が述べる精度は、日の出入りの時刻で緯度 ±72° 以内 1 分以内(1800〜2100 年)。

**Raises** ``ValueError``: 素朴な datetime・範囲外の緯度経度。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [koschmieder](koschmieder.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md) · [road_row_distance](road_row_distance.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
