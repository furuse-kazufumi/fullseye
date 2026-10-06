---
op: slip_cvar
dim: drive
category: roverslip
in: table × signal × scalar
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# slip_cvar — DRIVE `roverslip` op

- **データ種**: `table × signal × scalar` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.slip_cvar(model, slopes, alpha: 'float' = 0.9, sign: 'float' = 1.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import roverslip; roverslip.slip_cvar(model, slopes, alpha: 'float' = 0.9, sign: 'float' = 1.0) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("slip_cvar")`)

## 使い方

滑り率の CVaR_α(上側 1 − α の尾の条件付き期待値)。``sign = −1`` で −s の CVaR(下りの空走・横滑りの大きさ)。

ガウス過程は閉形式 ``μ + σ φ(Φ⁻¹(α)) / (1 − α)``(α = 0 で平均、σ は観測の予測分布)。分位点回帰は
``(1/(1 − α)) ∫_α^{q_max} Q(u) du`` を当てはめた段で台形則に、``q_max`` より上の尾は最上段の値で埋める
(尾を細く見積もる向きの近似 —— 段の外の分布は分からない)。返り値 (n,)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
