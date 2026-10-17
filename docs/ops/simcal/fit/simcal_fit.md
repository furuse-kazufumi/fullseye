---
op: simcal_fit
dim: simcal
category: fit
in: simmodel
out: calresult
examples: [poc_simcal_thin_film, simcal_checks_tour, simcal_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# simcal_fit — SIMCAL `fit` op

- **データ種**: `simmodel` → `calresult`
- **呼び出し**: `import fullseye as fs; fs.ledger.simcal_fit(model=None, method='lm', n_starts=16, fix=None, threshold=10.0, allow_undetermined=False, seed=0) -> 'dict'` (実装を直接呼ぶなら `import simcal; simcal.simcal_fit(model=None, method='lm', n_starts=16, fix=None, threshold=10.0, allow_undetermined=False, seed=0) -> 'dict'`、台帳から引くなら `opssimcal.get("simcal_fit")`)

## 使い方

Fit the free knobs of an observed simmodel to its images (weighted least squares) -> ``calresult``.

Minimises chi^2 = sum over valid pixels of (observed − simulated)^2 / variance, the
variance coming from the noise model at the current prediction (re-weighted each
iteration: the quasi-likelihood estimating equation, unbiased for a signal-dependent
variance). Knobs live in u in [0, 1] (log knobs on a log axis).

Starting point: the initial knobs and ``n_starts`` Latin-hypercube points over the ranges are
scored by chi^2 and the best is used (the design's "start from the best point of the plan").
``method``: ``"lm"`` (Levenberg-Marquardt, Marquardt-scaled damping; a raw step that leaves
the range is not taken — its projection onto the range is tried, a knob on a range end whose
descent points outward is held there, and a point the forward model refuses rejects the step
and raises the damping, as in ``lensopt``), ``"nm"`` (Nelder-Mead; a point outside the range
scores the metric's worst value via ``metriccontract.value_or_worst``), ``"multistart"`` (LM
from the best ``n_starts // 4`` plan points, at least 2, ranked with
``metriccontract.best_of`` — for multi-modal problems such as thin-film fringe orders).
``fix`` = ``{knob: value}`` pins knobs for this fit.

**Refusal** (``metriccontract.MetricContractError``, a ``ValueError``) when, at the end
point, a knob has no influence (a full-range move changes chi^2 by less than 3.84), is
confounded with others (collinearity index gamma_K > ``threshold``,
``sensitivity.mv_confounding``), or sits within 1 % of a range end — the message names
the knobs, the reason and the combinations the data do fix. With
``allow_undetermined=True`` those knobs get **no value** (``undetermined`` holds the
reason, ``status`` = ``partial``) and ``determined_combos`` carries the combinations with
their values (a product of powers for log knobs). No noise model / no observed images:
refused.

## 詳しい使い方ガイド

- [sim_to_real_calibration ファミリ ガイド](../guides/sim_to_real_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`
- [simcal_checks_tour](../../../../examples/simcal_checks_tour.py) — `py -3.11 examples/simcal_checks_tour.py`
- [simcal_tour](../../../../examples/simcal_tour.py) — `py -3.11 examples/simcal_tour.py`

## 型が繋がる次の op(`calresult` を入力に取れる)

[simcal_identifiability](../check/simcal_identifiability.md) · [simcal_uncertainty](../check/simcal_uncertainty.md) · [simcal_validate](../check/simcal_validate.md) · [simcal_discrepancy](../check/simcal_discrepancy.md) · [simcal_report](../report/simcal_report.md)

## 同カテゴリ(`fit`)

[simcal_screen](simcal_screen.md)

---
*Provenance: simcal.py — SIMCAL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
