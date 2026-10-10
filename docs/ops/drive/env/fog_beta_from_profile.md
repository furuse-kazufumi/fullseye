---
op: fog_beta_from_profile
dim: drive
category: env
in: any × any × scalar × scalar × scalar
out: table
examples: [poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# fog_beta_from_profile — DRIVE `env` op

- **データ種**: `any × any × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fog_beta_from_profile(rows, luminance, horizon_row: 'float', focal: 'float', cam_height: 'float', pitch: 'float' = 0.0, *, method: 'str' = 'fit', slant: 'bool' = True, beta_range=(0.0001, 0.5), n_grid: 'int' = 400) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import driveenv; driveenv.fog_beta_from_profile(rows, luminance, horizon_row: 'float', focal: 'float', cam_height: 'float', pitch: 'float' = 0.0, *, method: 'str' = 'fit', slant: 'bool' = True, beta_range=(0.0001, 0.5), n_grid: 'int' = 400) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("fog_beta_from_profile")`)

## 使い方

路面の縦の輝度の曲線から霧の減衰係数 β を測る(Hautière ら 2006 の考え方)。

``method="fit"``(既定): 各行の路面までの距離(:func:`road_row_distance`、``slant=True`` で視線の長さ √(d² + H²))に
Koschmieder L = L_h + (L₀ − L_h) e^{−β r} を当てる(β は対数格子 + 黄金分割、各 β で L₀・L_h は線形最小二乗)。
``method="inflection"``: 曲線を 5 行の移動平均で均し、2 階差分が符号を変える行 v_i から β = 2 (v_i − v_h)/λ
(λ = f H / cos²α。距離を λ/(v − v_h) と近似したときの厳密な変曲点: L = L_h + (L₀ − L_h) e^{−βλ/u} の 2 階微分は u = βλ/2 で 0)。
返り値にはどちらも入る: ``beta``(選んだ方)・``beta_fit``・``beta_inflection``(見つからなければ nan)・``L0``・``L_h``・
``rms``・``mor``(2.996/β)。

**Raises** ``ValueError``: 長さ違い・地平線より下の点が 5 未満・method が不正。

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
