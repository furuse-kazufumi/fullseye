---
op: slope_slip_curve
dim: drive
category: roverslip
in: signal × table × any × scalar
out: table
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# slope_slip_curve — DRIVE `roverslip` op

- **データ種**: `signal × table × any × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.slope_slip_curve(slopes_deg, wheel, soil, mass: 'float', n_wheels: 'int' = 6, gravity: 'float' = 3.72, s_min: 'float' = -0.9, s_max: 'float' = 0.99) -> 'dict'` (実装を直接呼ぶなら `import roverslip; roverslip.slope_slip_curve(slopes_deg, wheel, soil, mass: 'float', n_wheels: 'int' = 6, gravity: 'float' = 3.72, s_min: 'float' = -0.9, s_max: 'float' = 0.99) -> 'dict'`、台帳から引くなら `opsdrive.get("slope_slip_curve")`)

## 使い方

斜面の角(度、登りが正)ごとに、車体の重さを支えつつ斜面方向の重力成分を牽引力で釣り合わせる定常の滑り率。

1 輪あたり ``F_z = m g cos β / N``、必要な牽引力 ``m g sin β / N``。滑り率を [s_min, s_max] で二分法
(内側で沈下も二分法)。``s_max`` でも牽引力が足りない角は ``feasible = False``・``slip = nan``(立ち往生)、
下りで ``s_min`` でも止まれない角も同じ。既定の重力は火星 3.72 m/s²。
返り値 ``{"slope", "slip", "sinkage", "feasible", "max_slope"}``(``max_slope`` は登れる最大の角の内挿 [deg]、
範囲内に限界が無ければ nan)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md) · [slip_gp_fit](slip_gp_fit.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
