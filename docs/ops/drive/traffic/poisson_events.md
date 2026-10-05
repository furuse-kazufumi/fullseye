---
op: poisson_events
dim: drive
category: traffic
in: any
out: signal
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# poisson_events — DRIVE `traffic` op

- **データ種**: `any` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.poisson_events(rate_fn: 'Callable', x_max: 'float', *, rate_max: 'float', seed, n_grid: 'int' = 2001) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.poisson_events(rate_fn: 'Callable', x_max: 'float', *, rate_max: 'float', seed, n_grid: 'int' = 2001) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("poisson_events")`)

## 使い方

[0, x_max] の非一様ポアソン過程を thinning(Lewis & Shedler 1979)で 1 本引く(昇順の位置の配列)。

率 rate_max の一様ポアソン過程の候補を引き、各候補 x を確率 λ(x)/rate_max で残す。残った点は率 λ の非一様
ポアソン過程 → 件数 N ~ Poisson(Λ)、Λ = ∫₀^{x_max} λ(x) dx(門: 多数の試行で平均 = 分散 = Λ、位置の分布 = λ/Λ)。
``rate_fn`` は numpy 配列を受けて同じ形の率を返す関数。**引く前に** ``n_grid`` 点の等間隔格子で λ ≤ rate_max を確かめ、
引いた候補の所でも確かめる。どちらかで超えれば ValueError(fail-closed。上限を守らないと thinning は静かに少なく数える)。
``seed`` は int か ``np.random.Generator``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
