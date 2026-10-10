---
op: long_params
dim: drive
category: long
in: 
out: table
examples: [poc_driving_longitudinal, poc_driving_town, poc_driving_traffic, poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# long_params — DRIVE `long` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.long_params(mass: 'float' = 1300.0, c_rr: 'float' = 0.012, cda: 'float' = 0.65, rho_air: 'float' = 1.2, a_drive_max: 'float' = 3.0, a_brake_max: 'float' = 6.0, reaction: 'float' = 0.75, mu: 'float' = 0.8, a_creep: 'float' = 0.3, g: 'float' = 9.80665) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivelong; drivelong.long_params(mass: 'float' = 1300.0, c_rr: 'float' = 0.012, cda: 'float' = 0.65, rho_air: 'float' = 1.2, a_drive_max: 'float' = 3.0, a_brake_max: 'float' = 6.0, reaction: 'float' = 0.75, mu: 'float' = 0.8, a_creep: 'float' = 0.3, g: 'float' = 9.80665) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("long_params")`)

## 使い方

縦の運動のパラメータ(既定値はすべて **仮定**。出典はモジュールの docstring)。

Parameters
----------
mass : 車両質量 [kg] (> 0)。空気抵抗の係数 k = ρ_air C_d A / (2 m) にだけ効く。
c_rr : 転がり抵抗係数(≥ 0、文献値 0.010〜0.015)
cda : C_d × 前面投影面積 [m²] (≥ 0。0 で空気抵抗なし)
rho_air : 空気密度 [kg/m³] (≥ 0)
a_drive_max, a_brake_max : 駆動・制動の上限 [m/s²] (> 0)。実際の上限はさらに μ g cos θ で頭打ち。
reaction : 反応時間(空走)[s] (≥ 0)
mu : 路面とタイヤの摩擦係数(> 0。乾燥 0.7〜0.8・湿潤 0.4〜0.6 —— 要確認)
a_creep : AT のクリープの駆動 [m/s²] (≥ 0。保持の間だけ)
g : 重力加速度 [m/s²] (> 0)

Returns
-------
dict : 引数と同じキー + ``k``(空気抵抗の係数 [1/m])。

**Raises** ``ValueError``: 非有限・範囲外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`
- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`
- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`
- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`long`)

[road_profile](road_profile.md) · [road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [long_energy_residual](long_energy_residual.md) · [stopping_distance_grade](stopping_distance_grade.md) · [stop_line_plan](stop_line_plan.md) · [plan_command](plan_command.md) · [hill_hold_brake_min](hill_hold_brake_min.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
