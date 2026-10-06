---
op: diabolo_state_sequence
dim: drive
category: diabolo
in: matrix × any × table
out: signal
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# diabolo_state_sequence — DRIVE `diabolo` op

- **データ種**: `matrix × any × table` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.diabolo_state_sequence(X, sticks, params: 'dict', *, flying_rule: 'str' = 'paper', mode0: 'str' = 'on_string') -> 'np.ndarray'` (実装を直接呼ぶなら `import diabolo; diabolo.diabolo_state_sequence(X, sticks, params: 'dict', *, flying_rule: 'str' = 'paper', mode0: 'str' = 'on_string') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("diabolo_state_sequence")`)

## 使い方

位置の列 X (N, 3) と棒 (N, 2, 3) から論文の状態遷移だけを回す(観測した軌跡の分類用、力学は解かない)。有限でない行は
直前の状態を保つ(追跡が見失ったコマ)。返り (N,) の状態名。**Raises** ``ValueError``: 形・長さ・綴り。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`diabolo`)

[diabolo_params](diabolo_params.md) · [diabolo_spheroid](diabolo_spheroid.md) · [spheroid_closest](spheroid_closest.md) · [diabolo_dynamics_step](diabolo_dynamics_step.md) · [diabolo_simulate](diabolo_simulate.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md) · [string_tension_from_sag](string_tension_from_sag.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
