---
op: magnus_lift_coefficient
dim: drive
category: ball
in: signal
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# magnus_lift_coefficient — DRIVE `ball` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.magnus_lift_coefficient(spin_ratio) -> 'np.ndarray'` (実装を直接呼ぶなら `import ballistics; ballistics.magnus_lift_coefficient(spin_ratio) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("magnus_lift_coefficient")`)

## 使い方

スピン比 S = rω/|v| から揚力係数 C_L = 1 / (2 + 1/S)(S → 0 で 0、S → ∞ で 0.5。球の文献で広く使われる経験式)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](flight_vacuum.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md) · [restitution_from_apexes](restitution_from_apexes.md) · [restitution_from_intervals](restitution_from_intervals.md) · [fit_parabola](fit_parabola.md) · [flight_fit](flight_fit.md) · [fit_aero](fit_aero.md) · [fit_spin](fit_spin.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md) · [bounce](bounce.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
