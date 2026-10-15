---
op: simcal_validate
dim: simcal
category: check
in: calresult × simmodel
out: calresult
examples: [simcal_checks_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# simcal_validate — SIMCAL `check` op

- **データ種**: `calresult × simmodel` → `calresult`
- **呼び出し**: `import fullseye as fs; fs.ledger.simcal_validate(result=None, holdout=None, locked=None, tau=None, dims=None, n_boot=200, seed=0) -> 'dict'` (実装を直接呼ぶなら `import simcalcheck; simcalcheck.simcal_validate(result=None, holdout=None, locked=None, tau=None, dims=None, n_boot=200, seed=0) -> 'dict'`、台帳から引くなら `opssimcal.get("simcal_validate")`)

## 使い方

Over-fitting gates on held-out images; any one failing rejects the calibration (the estimates are withdrawn).

``holdout`` (and ``locked``): observed simmodels of the same knobs (``simcal_observe`` with
``split='holdout'`` / ``'locked'``) or image lists for the fitted model's conditions.
Errors are reduced chi^2 (1 = the residuals are exactly the noise). Gates, each recorded in
``validation.gates`` with its value and limit:

1. ``beats_initial`` — holdout error at the estimate < holdout error at the initial knobs;
2. ``holdout_over_train`` — holdout / train <= 1 + tau, tau = the bootstrap 95 % relative
   spread of the train error over its pixels (``n_boot`` resamples) unless given;
3. ``beats_gain_offset`` — better than the initial simulation re-scaled by a fitted gain and
   offset only (the cheapest model that could explain the images);
4. ``estimate_plausible`` — every estimate inside its range, not within 1 % of an end, and
   within 3 sd of its prior when one is given;
5. ``knobs_within_dims`` — free knobs <= output directions above noise (``dims``, or computed
   from a Latin hypercube over the knobs with ``sensitivity.mv_residual_pca``).

``locked`` is scored **once** (``errors.locked``) and is not used by any gate; a result that
already carries a LOCKED score is refused (the ``robust.py`` discipline: the untouched number
is untouched only once).

## 詳しい使い方ガイド

- [sim_to_real_calibration ファミリ ガイド](../guides/sim_to_real_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [simcal_checks_tour](../../../../examples/simcal_checks_tour.py) — `py -3.11 examples/simcal_checks_tour.py`

## 型が繋がる次の op(`calresult` を入力に取れる)

[simcal_identifiability](simcal_identifiability.md) · [simcal_uncertainty](simcal_uncertainty.md) · [simcal_discrepancy](simcal_discrepancy.md) · [simcal_report](../report/simcal_report.md)

## 同カテゴリ(`check`)

[simcal_identifiability](simcal_identifiability.md) · [simcal_uncertainty](simcal_uncertainty.md) · [simcal_discrepancy](simcal_discrepancy.md)

---
*Provenance: simcalcheck.py — SIMCAL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
