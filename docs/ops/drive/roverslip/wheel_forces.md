---
op: wheel_forces
dim: drive
category: roverslip
in: signal × signal × table × any
out: table
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# wheel_forces — DRIVE `roverslip` op

- **データ種**: `signal × signal × table × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.wheel_forces(sinkage, slip, wheel, soil, n_quad: 'int' = 96) -> 'dict'` (実装を直接呼ぶなら `import roverslip; roverslip.wheel_forces(sinkage, slip, wheel, soil, n_quad: 'int' = 96) -> 'dict'`、台帳から引くなら `opsdrive.get("wheel_forces")`)

## 使い方

沈下 z [m] と滑り率 s で、剛な車輪が土から受ける力(Wong–Reece の応力分布の数値積分)。

返り値 ``{"Fz", "DP", "T", "theta_f", "theta_m", "theta_r"}``: 垂直力 [N]、牽引力(drawbar pull、前向き正)[N]、
駆動トルク [N·m]、角 [rad]。``sinkage``・``slip`` はスカラーか同じ形に放送できる配列(0 ≤ z < r、−1 < s < 1)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md) · [slip_gp_fit](slip_gp_fit.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
