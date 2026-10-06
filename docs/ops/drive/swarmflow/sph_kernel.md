---
op: sph_kernel
dim: drive
category: swarmflow
in: signal × scalar
out: signal
examples: [poc_swarm_obstacle_from_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# sph_kernel — DRIVE `swarmflow` op

- **データ種**: `signal × scalar` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.sph_kernel(r, h: 'float', dim: 'int' = 2, derivative: 'bool' = False) -> 'np.ndarray'` (実装を直接呼ぶなら `import swarmflow; swarmflow.sph_kernel(r, h: 'float', dim: 'int' = 2, derivative: 'bool' = False) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("sph_kernel")`)

## 使い方

3 次スプライン核 W(r, h)(M4、台の半径 2h)。``derivative=True`` で dW/dr(r の向きの微分、0 以下)。

W = σ_d [1 − 1.5 q² + 0.75 q³] (0 ≤ q < 1)、σ_d · 0.25 (2 − q)³(1 ≤ q < 2)、0(q ≥ 2)、q = r/h。
σ_1 = 2/(3h)、σ_2 = 10/(7π h²)、σ_3 = 1/(π h³)。この定数で ∫ W dV = 1(恒等式。門で数値の求積と照らす)。

Args:
    r: 距離の配列(0 以上、形は任意)。
    h: 平滑化の長さ(> 0)。
    dim: 1、2、3。
    derivative: True で dW/dr を返す。
Returns:
    r と同じ形の配列。
Raises:
    ValueError: h ≤ 0、dim が 1〜3 でない、r に負・非有限がある。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_swarm_obstacle_from_flow](../../../../examples/poc_swarm_obstacle_from_flow.py) — `py -3.11 examples/poc_swarm_obstacle_from_flow.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`swarmflow`)

[sph_density_pressure](sph_density_pressure.md) · [swarm_simulate](swarm_simulate.md) · [swarm_render_overhead](swarm_render_overhead.md) · [swarm_field_from_tracks](swarm_field_from_tracks.md) · [swarm_field_from_piv](swarm_field_from_piv.md) · [potential_flow_cylinder](potential_flow_cylinder.md) · [velocity_deficit_map](velocity_deficit_map.md) · [stagnation_from_centerline](stagnation_from_centerline.md)

---
*Provenance: swarmflow.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
