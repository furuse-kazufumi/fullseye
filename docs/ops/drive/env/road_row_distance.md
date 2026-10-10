---
op: road_row_distance
dim: drive
category: env
in: any × scalar × scalar × scalar
out: any
examples: [poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# road_row_distance — DRIVE `env` op

- **データ種**: `any × scalar × scalar × scalar` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.road_row_distance(rows, horizon_row: 'float', focal: 'float', cam_height: 'float', pitch: 'float' = 0.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import driveenv; driveenv.road_row_distance(rows, horizon_row: 'float', focal: 'float', cam_height: 'float', pitch: 'float' = 0.0) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("road_row_distance")`)

## 使い方

平らな路面の上の行 → カメラから路面の点までの水平距離(厳密)。地平線より上の行は ``inf``。

俯角 α(下向き +、ラジアン)のピンホール: 地平線の行 v_h = c_y − f tan α、路面の水平距離 d の点の行は
v − v_h = f H (1 + tan²α) / (d + H tan α) —— よって d = λ/(v − v_h) − H tan α、λ = f H / cos²α
(Hautière ら 2006 の λ/(v − v_h) は第 1 項だけの形)。行は下向きが +。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [koschmieder](koschmieder.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
