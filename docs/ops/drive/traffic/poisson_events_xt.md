---
op: poisson_events_xt
dim: drive
category: traffic
in: any
out: any
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# poisson_events_xt — DRIVE `traffic` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.poisson_events_xt(rate_fn: 'Callable', x_max: 'float', t_max: 'float', *, rate_max: 'float', seed, n_grid=(201, 201)) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.poisson_events_xt(rate_fn: 'Callable', x_max: 'float', t_max: 'float', *, rate_max: 'float', seed, n_grid=(201, 201)) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("poisson_events_xt")`)

## 使い方

[0, x_max] × [0, t_max] の時空の非一様ポアソン過程(率 λ(x, t) [件/(m·s)])を thinning で 1 本引く。

停車中のバスのように、出現率が場所と時刻の両方に依る場合(λ(x, t) = bus_stop_rate(x) · [t < 発車] + base)。
率 rate_max の一様な候補(件数 ~ Poisson(rate_max · x_max · t_max)、位置・時刻は一様)を確率 λ/rate_max で残す。
件数 ~ Poisson(Λ)、Λ = ∫∫λ dx dt。``rate_fn(x, t)`` は同じ形の配列 2 つを受けて率を返す関数。
**引く前に** ``n_grid = (nx, nt)`` の格子で λ ≤ rate_max を確かめ、候補の所でも確かめる(超えれば ValueError)。

戻り値: (N, 2) の配列 [[x, t], ...] (時刻の昇順)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
