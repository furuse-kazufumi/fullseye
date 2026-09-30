---
op: env_params
dim: drive
category: env
in: 
out: table
examples: [poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# env_params — DRIVE `env` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.env_params(when=None, lat: 'float' = 35.6581, lon: 'float' = 139.7414, *, sun=None, cloud: 'float' = 0.0, fog_mor: 'Optional[float]' = None, rain: 'float' = 0.0, headlamps: 'str' = 'off', north_yaw: 'float' = 90.0, lamp_luminance: 'float' = 10000.0, exposure: 'Optional[float]' = None, max_gain: 'float' = 1.0, glare_model: 'str' = 'stiles_holladay', fog_layer: 'float' = 100.0, seed: 'int' = 0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import driveenv; driveenv.env_params(when=None, lat: 'float' = 35.6581, lon: 'float' = 139.7414, *, sun=None, cloud: 'float' = 0.0, fog_mor: 'Optional[float]' = None, rain: 'float' = 0.0, headlamps: 'str' = 'off', north_yaw: 'float' = 90.0, lamp_luminance: 'float' = 10000.0, exposure: 'Optional[float]' = None, max_gain: 'float' = 1.0, glare_model: 'str' = 'stiles_holladay', fog_layer: 'float' = 100.0, seed: 'int' = 0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("env_params")`)

## 使い方

描画の条件をまとめる(:func:`env_render` に渡す)。

``when`` + 緯度経度(既定 = 東京の暦計算室の代表点)から太陽を出す。``sun=(elevation, azimuth)`` で直接与えてもよい。
``fog_mor`` = 気象光学距離 [m] (None で霧なし)、``rain`` ∈ [0, 1] (0 = 乾き。濡れた路面・雨筋の強さ)、
``headlamps`` ∈ {"off", "low", "high"}、``exposure`` = 固定の露出(輝度 → 画素値の倍率。None で自動)、
``max_gain`` = 自動露出の倍率の上限(暗い夜に雑に明るくしない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [koschmieder](koschmieder.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
