---
op: wheel_sinkage
dim: drive
category: roverslip
in: signal × table × any
out: signal
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# wheel_sinkage — DRIVE `roverslip` op

- **データ種**: `signal × table × any` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.wheel_sinkage(load, wheel, soil, slip=0.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import roverslip; roverslip.wheel_sinkage(load, wheel, soil, slip=0.0) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("wheel_sinkage")`)

## 使い方

1 輪の垂直荷重 ``load`` [N] を滑り率 ``slip`` で支える沈下 z [m] (F_z(z, s) = load の二分法)。

``load``・``slip`` は放送できる配列。車輪の半径まで沈んでも支えられない荷重は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md) · [slip_gp_fit](slip_gp_fit.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
