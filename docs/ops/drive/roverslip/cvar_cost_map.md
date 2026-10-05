---
op: cvar_cost_map
dim: drive
category: roverslip
in: image2d × scalar × any
out: table
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# cvar_cost_map — DRIVE `roverslip` op

- **データ種**: `image2d × scalar × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cvar_cost_map(dtm, cell: 'float', model, alpha: 'float' = 0.9, speed: 'float' = 0.05, s_max: 'float' = 0.9, soil_map=None, extrapolate: 'bool' = False) -> 'dict'` (実装を直接呼ぶなら `import roverslip; roverslip.cvar_cost_map(dtm, cell: 'float', model, alpha: 'float' = 0.9, speed: 'float' = 0.05, s_max: 'float' = 0.9, soil_map=None, extrapolate: 'bool' = False) -> 'dict'`、台帳から引くなら `opsdrive.get("cvar_cost_map")`)

## 使い方

数値標高(DTM)から、8 近傍の辺ごとの所要時間 [s] を、辺の傾き(進む向きの符号つき)の滑りの CVaR_α で割り引いて作る。

``dtm`` (H, W) [m]、``cell`` [m]。辺 (i, j) → 近傍 k の傾き ``θ = atan2(Δz, 水平距離)``、悲観的な滑り
``ρ = CVaR_α(s(θ))``(θ ≥ 0)/ ``CVaR_α(−s(θ))``(θ < 0)、所要時間 ``L / (v (1 − ρ))``、``L`` は 3-D の辺の長さ。
``ρ ≥ s_max`` と範囲外は inf。``extrapolate = False``(既定)では、模型を当てはめたデータの角の範囲
(``x_range``)の外の傾きの辺も inf(分からない斜面は通らない)—— ガウス過程はデータの外で事前の平均に戻るので、
外挿させると急斜面ほど「滑らない」と答える(門の罠)。``alpha = 0`` なら平均の滑り(リスクに中立)。``model`` は 1 個か、``soil_map``
(H, W の整数 0..K−1)と組で K 個の list。返り値 ``{"cost": (8, H, W), "risk_slip": (8, H, W), "pitch": (8, H, W) [deg],
"offsets": (8, 2), "worst_slip": (H, W) 8 方向の ρ の最大, "alpha", "cell"}``。横方向の傾き(横転・横滑り)は入れない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
