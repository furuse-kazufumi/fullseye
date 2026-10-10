---
op: rss_params
dim: drive
category: rss
in: 
out: table
examples: [poc_ttc_rss]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# rss_params — DRIVE `rss` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.rss_params(rho: 'float' = 1.0, accel_max: 'float' = 3.5, brake_min: 'float' = 4.0, brake_max: 'float' = 8.0, brake_min_correct: 'float' = 3.0, lat_accel_max: 'float' = 0.2, lat_brake_min: 'float' = 0.8, lat_margin: 'float' = 0.1, min_distance: 'float' = 0.0, v_max_accel: 'Optional[float]' = None) -> 'Dict[str, Optional[float]]'` (実装を直接呼ぶなら `import rsssafety; rsssafety.rss_params(rho: 'float' = 1.0, accel_max: 'float' = 3.5, brake_min: 'float' = 4.0, brake_max: 'float' = 8.0, brake_min_correct: 'float' = 3.0, lat_accel_max: 'float' = 0.2, lat_brake_min: 'float' = 0.8, lat_margin: 'float' = 0.1, min_distance: 'float' = 0.0, v_max_accel: 'Optional[float]' = None) -> 'Dict[str, Optional[float]]'`、台帳から引くなら `opsdrive.get("rss_params")`)

## 使い方

RSS パラメータの dict を作る(既定 = ad-rss-lib の公表表、ρ は ego の 1 s)。

ad-rss-lib ``doc/ad_rss/Appendix-ParameterDiscussion.md`` の "conservative starting point":
ρ_ego = 1 s(他車は ``rss_params(rho=2.0)``)、a_accel_max = 3.5、a_brake_min = 4、a_brake_max = 8、
a_brake_min_correct = 3、a^lat_brake_min = 0.8、a^lat_accel_max = 0.2、δ^lat_min(μ)= 0.1 m。

Parameters
----------
rho : 応答時間 [s] (≥ 0)
accel_max : 応答時間中の最大加速度 [m/s²] (≥ 0)
brake_min : 応答後に最低限かける減速度の大きさ [m/s²] (> 0)
brake_max : 先行車が急ブレーキでかけうる最大減速度の大きさ [m/s²] (> 0、brake_min ≤ brake_max)
brake_min_correct : 正しい車線を走る車が対向に対してかける最低減速度の大きさ(> 0、≤ brake_min)
lat_accel_max : 横方向の最大加速度 [m/s²] (≥ 0)
lat_brake_min : 横方向の最低減速度の大きさ [m/s²] (> 0)
lat_margin : 横方向の揺らぎ余裕 μ [m] (≥ 0)
min_distance : 縦方向に停止後も残す最小間隔 [m] (≥ 0。lib の ``min_longitudinal_safety_distance``)
v_max_accel : 応答時間中の加速で到達しうる最大速度 [m/s] (None = 制限なし。lib の ``max_speed_on_acceleration``)

Returns
-------
dict : キー名は引数名と同じ。値は float(v_max_accel だけ None を許す)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](rss_longitudinal_same.md)

## 同カテゴリ(`rss`)

[rss_stopping_distance](rss_stopping_distance.md) · [rss_longitudinal_same](rss_longitudinal_same.md) · [rss_longitudinal_opposite](rss_longitudinal_opposite.md) · [rss_lateral](rss_lateral.md) · [rss_longitudinal_check](rss_longitudinal_check.md) · [rss_lateral_check](rss_lateral_check.md) · [rss_worst_case_gap](rss_worst_case_gap.md) · [rss_worst_case_gap_opposite](rss_worst_case_gap_opposite.md)

---
*Provenance: rsssafety.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
