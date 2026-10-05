---
op: wheel_traction_curve
dim: drive
category: roverslip
in: scalar × table × any
out: table
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# wheel_traction_curve — DRIVE `roverslip` op

- **データ種**: `scalar × table × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.wheel_traction_curve(load, wheel, soil, slips=None) -> 'dict'` (実装を直接呼ぶなら `import roverslip; roverslip.wheel_traction_curve(load, wheel, soil, slips=None) -> 'dict'`、台帳から引くなら `opsdrive.get("wheel_traction_curve")`)

## 使い方

1 輪の荷重 ``load`` [N] を一定に保ったときの、滑り率ごとの沈下・牽引力・トルク(牽引–滑り曲線)。

``slips`` の既定は 0〜0.95 の 40 点。返り値 ``{"slip", "sinkage", "DP", "T", "DP_over_W", "efficiency"}``
(``efficiency`` = 牽引の仕事率 / 駆動の仕事率 = DP (1 − s) r / T、T ≤ 0 の点は 0)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md) · [slip_gp_fit](slip_gp_fit.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
