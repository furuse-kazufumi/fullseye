---
op: sun_illuminance
dim: drive
category: env
in: scalar
out: table
examples: [poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# sun_illuminance — DRIVE `env` op

- **データ種**: `scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sun_illuminance(elevation: 'float', cloud: 'float' = 0.0) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import driveenv; driveenv.sun_illuminance(elevation: 'float', cloud: 'float' = 0.0) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("sun_illuminance")`)

## 使い方

晴天(雲量 ``cloud`` ∈ [0, 1])の太陽の照度 [lx]: ``direct_normal``(太陽に正対する面)・``diffuse``(水平面の散乱)・``air_mass``。

直達 = 1361 W/m² × 0.7^{AM^0.678}(Meinel)× 105 lm/W × (1 − cloud)、AM = Kasten & Young 1989
1 / (sin h + 0.50572 (h + 6.07995°)^{−1.6364})。散乱 = 薄明の表(高度 ≤ 0)/ 400 + 16000 sin h(高度 > 0)に
雲で (1 + 0.5 cloud) を掛ける —— 仮定(モジュールの docstring)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [koschmieder](koschmieder.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md) · [road_row_distance](road_row_distance.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
