---
op: drag_coefficient_sphere
dim: drive
category: ball
in: signal
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# drag_coefficient_sphere — DRIVE `ball` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.drag_coefficient_sphere(reynolds) -> 'np.ndarray'` (実装を直接呼ぶなら `import ballistics; ballistics.drag_coefficient_sphere(reynolds) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("drag_coefficient_sphere")`)

## 使い方

滑らかな球の抗力係数の経験式(Morrison 2013、Re ≲ 1e6): 24/Re + 2.6(Re/5)/(1 + (Re/5)^1.52) + 0.411(Re/263000)^−7.94/(1 + (Re/263000)^−8)
+ 0.25(Re/1e6)/(1 + Re/1e6)。卓球の球(Re ≈ 1〜5 × 10⁴)で ≈ 0.4〜0.5。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](flight_vacuum.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [restitution_from_apexes](restitution_from_apexes.md) · [restitution_from_intervals](restitution_from_intervals.md) · [fit_parabola](fit_parabola.md) · [flight_fit](flight_fit.md) · [fit_aero](fit_aero.md) · [fit_spin](fit_spin.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [bounce](bounce.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
