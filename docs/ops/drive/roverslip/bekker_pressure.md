---
op: bekker_pressure
dim: drive
category: roverslip
in: signal × scalar × any
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# bekker_pressure — DRIVE `roverslip` op

- **データ種**: `signal × scalar × any` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.bekker_pressure(sinkage, width, soil) -> 'np.ndarray'` (実装を直接呼ぶなら `import roverslip; roverslip.bekker_pressure(sinkage, width, soil) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("bekker_pressure")`)

## 使い方

Bekker の圧力–沈下 ``p = (k_c / b + k_φ) zⁿ`` [kPa]。``sinkage`` [m] はスカラーか配列(≥ 0)、``width`` = b [m]。

返りは ``sinkage`` と同じ形の配列(スカラーなら 0 次元)。z = 0 で 0、z について単調に増える。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`roverslip`)

[bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md) · [slip_gp_fit](slip_gp_fit.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
