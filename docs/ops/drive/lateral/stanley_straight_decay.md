---
op: stanley_straight_decay
dim: drive
category: lateral
in: 
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# stanley_straight_decay — DRIVE `lateral` op

- **データ種**: `なし` → `signal`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.stanley_straight_decay(e0: 'float', t, *, gain: 'float', speed: 'float', softening: 'float' = 0.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivelateral; drivelateral.stanley_straight_decay(e0: 'float', t, *, gain: 'float', speed: 'float', softening: 'float' = 0.0) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("stanley_straight_decay")`)

## 使い方

直線の経路で Stanley(切らない)の前車軸の横ずれ e(t) の閉形式。

ė = −v k e / √(a² + k² e²)、a = k_s + v。F(e) = √(a² + k²e²) − a ln((a + √(a² + k²e²))/(k|e|)) は
dF/dt = −v k(一定)。F(e(t)) = F(e₀) − v k t を |e| ∈ (0, |e₀|] の二分法(F は |e| に単調増加)で解く。
小さい e では e ≈ e₀' e^{−k t v/a}(指数)、大きい e では |e| がほぼ v t で減る(直線)。

**Raises** ``ValueError``: k ≤ 0、v ≤ 0、k_s < 0、t < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
