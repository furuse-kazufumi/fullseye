---
op: doe_lhs
dim: multivar
category: plan
in: 
out: design
examples: [doe_plan_tour, multivar_inspection_tour, sensitivity_tour, simcal_checks_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# doe_lhs — MULTIVAR `plan` op

- **データ種**: `なし` → `design`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.doe_lhs(n=10, factors=3, seed=0, maximin=0, centered=False) -> 'dict'` (実装を直接呼ぶなら `import doe; doe.doe_lhs(n=10, factors=3, seed=0, maximin=0, centered=False) -> 'dict'`、台帳から引くなら `opsmultivar.get("doe_lhs")`)

## 使い方

Latin hypercube design (McKay, Beckman & Conover 1979) -> ``design``.

Each factor's range is cut into ``n`` equal strata and every stratum holds
exactly one run, so each factor is sampled evenly however many factors there
are (a random design of the same size leaves strata empty). Construction
(McKay et al. 1979, section 2): for factor j draw an independent random
permutation ``pi_j`` of ``0..n-1`` and put run i at
``u_ij = (pi_j(i) + U_ij) / n`` with ``U_ij ~ Uniform[0, 1)`` (``centered=True``
uses the stratum mid-point, ``U = 1/2``). Coded value = ``2u - 1``.

``maximin=m`` (m >= 2) draws m independent hypercubes and keeps the one with the
largest smallest inter-point distance (each candidate is still a Latin hypercube,
so the stratum property is never traded away); ``0`` or ``1`` = one plain draw.

Parameters: ``n`` runs (2..1e6), ``factors`` (int or factor list, see module
docstring), ``seed`` (int, reproducible), ``maximin`` (0..1000 candidates),
``centered``.

Returns a ``design`` whose ``meta`` holds ``strata_ok`` (every factor has one
point per stratum — the defining property, checked on the returned matrix) and
``min_distance`` (in the unit cube).

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [doe_plan_tour](../../../../examples/doe_plan_tour.py) — `py -3.11 examples/doe_plan_tour.py`
- [multivar_inspection_tour](../../../../examples/multivar_inspection_tour.py) — `py -3.11 examples/multivar_inspection_tour.py`
- [sensitivity_tour](../../../../examples/sensitivity_tour.py) — `py -3.11 examples/sensitivity_tour.py`
- [simcal_checks_tour](../../../../examples/simcal_checks_tour.py) — `py -3.11 examples/simcal_checks_tour.py`

## 型が繋がる次の op(`design` を入力に取れる)

[doe_decode](../coding/doe_decode.md) · [rsm_fit](../analysis/rsm_fit.md) · [doe_main_effects](../analysis/doe_main_effects.md) · [sens_morris](../sensitivity/sens_morris.md) · [sens_sobol](../sensitivity/sens_sobol.md)

## 同カテゴリ(`plan`)

[doe_orthogonal_array](doe_orthogonal_array.md) · [doe_fractional_factorial](doe_fractional_factorial.md) · [doe_central_composite](doe_central_composite.md) · [doe_box_behnken](doe_box_behnken.md)

---
*Provenance: doe.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
