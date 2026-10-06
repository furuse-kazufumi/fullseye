---
op: lateral_wobble
dim: drive
category: traffic
in: 
out: signal
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# lateral_wobble — DRIVE `traffic` op

- **データ種**: `なし` → `signal`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.lateral_wobble(n: 'int', dt: 'float', *, theta: 'float', sigma: 'float', seed: 'Optional[int]', x0: 'Optional[float]' = None) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.lateral_wobble(n: 'int', dt: 'float', *, theta: 'float', sigma: 'float', seed: 'Optional[int]', x0: 'Optional[float]' = None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("lateral_wobble")`)

## 使い方

Ornstein–Uhlenbeck 過程 dX = −θ X dt + σ dW の厳密離散化(長さ n の列、刻み dt)。

    x_{k+1} = x_k e^{−θ dt} + σ sqrt((1 − e^{−2θ dt}) / (2θ)) ξ_k,   ξ_k ~ N(0, 1) 独立

遷移分布が厳密なので dt に依らず定常分散 σ²/(2θ)、自己相関 corr(x_k, x_{k+j}) = e^{−θ j dt}(門は長い系列の標本で、
許容幅は AR(1) の標本誤差から決める)。``x0`` = None なら定常分布 N(0, σ²/(2θ)) から引く(最初から定常)。
``seed`` は ``np.random.default_rng(seed)``(None も可だが非決定的)。

**Raises** ``ValueError``: n < 1、dt ≤ 0、θ ≤ 0、σ < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md) · [occlusion_reveal_distance](occlusion_reveal_distance.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
