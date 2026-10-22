---
op: simcal_identifiability
dim: simcal
category: check
in: calresult
out: calresult
examples: [poc_simcal_pixel_shift, poc_simcal_telecentric, poc_simcal_thin_film, simcal_checks_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# simcal_identifiability — SIMCAL `check` op

- **データ種**: `calresult` → `calresult`
- **呼び出し**: `import fullseye as fs; fs.ledger.simcal_identifiability(result=None, at=None, profile=True, level=0.95, threshold=None) -> 'dict'` (実装を直接呼ぶなら `import simcalcheck; simcalcheck.simcal_identifiability(result=None, at=None, profile=True, level=0.95, threshold=None) -> 'dict'`、台帳から引くなら `opssimcal.get("simcal_identifiability")`)

## 使い方

Fisher information, Cramér-Rao bound, correlations, collinearity and profile likelihood of every fitted knob.

Computed at the fit's end point (or at ``at`` = ``{knob: value}``, e.g. the true values of
a synthetic study, without touching the estimates). Returned in ``identifiability``:
``fisher`` (natural units), ``crlb`` (sqrt of the diagonal of its inverse — the smallest
standard deviation any unbiased estimator can have under the noise model), ``condition``
(of the Fisher matrix on the unit-scaled knobs; > 1e6 adds a warning), ``correlation``,
``gamma_full`` and ``confounded_groups`` (``sensitivity.mv_confounding``), and with
``profile=True`` a ``profile`` per knob: the likelihood-ratio interval where chi^2 stays
within chi^2_1(``level``) of its minimum (3.84 at 95 %), each other knob re-fitted at every
step (Raue et al. 2009). Knobs whose profile does not rise above the threshold on both sides
inside the range lose their point estimate: ``upper_only`` / ``lower_only`` (only one limit
exists) or ``undetermined``. Each profile keeps its ``trace`` (knob value, chi^2 rise) of the
evaluated points. No noise model: refused.

## 詳しい使い方ガイド

- [sim_to_real_calibration ファミリ ガイド](../guides/sim_to_real_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_simcal_pixel_shift](../../../../examples/poc_simcal_pixel_shift.py) — `py -3.11 examples/poc_simcal_pixel_shift.py`
- [poc_simcal_telecentric](../../../../examples/poc_simcal_telecentric.py) — `py -3.11 examples/poc_simcal_telecentric.py`
- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`
- [simcal_checks_tour](../../../../examples/simcal_checks_tour.py) — `py -3.11 examples/simcal_checks_tour.py`

## 型が繋がる次の op(`calresult` を入力に取れる)

[simcal_uncertainty](simcal_uncertainty.md) · [simcal_validate](simcal_validate.md) · [simcal_discrepancy](simcal_discrepancy.md) · [simcal_report](../report/simcal_report.md)

## 同カテゴリ(`check`)

[simcal_uncertainty](simcal_uncertainty.md) · [simcal_validate](simcal_validate.md) · [simcal_discrepancy](simcal_discrepancy.md)

---
*Provenance: simcalcheck.py — SIMCAL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
