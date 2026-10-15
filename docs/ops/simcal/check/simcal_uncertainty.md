---
op: simcal_uncertainty
dim: simcal
category: check
in: calresult
out: calresult
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# simcal_uncertainty — SIMCAL `check` op

- **データ種**: `calresult` → `calresult`
- **呼び出し**: `import fullseye as fs; fs.ledger.simcal_uncertainty(result=None, method='laplace', n_boot=40, level=0.95, seed=0) -> 'dict'` (実装を直接呼ぶなら `import simcalcheck; simcalcheck.simcal_uncertainty(result=None, method='laplace', n_boot=40, level=0.95, seed=0) -> 'dict'`、台帳から引くなら `opssimcal.get("simcal_uncertainty")`)

## 使い方

Standard deviations and intervals of the determined knobs: Laplace (inverse Fisher) or parametric bootstrap.

Only knobs that kept a point estimate are covered; knobs without one are held at the end
point (the intervals are conditional on them — stated in ``note``). ``laplace``: covariance
= inverse of J^T W J at the estimate on the unit-scaled knobs, intervals u ± z sd mapped back
through each knob's scale (a log knob gets an asymmetric interval), ``std`` by the delta
method. ``bootstrap``: ``n_boot`` refits to the fitted prediction plus Gaussian noise of the
noise model's variance (Efron 1979), percentile intervals at ``level``. A result with no
point estimate is refused. Under a model discrepancy both are optimistic
(``simcal_discrepancy`` says so).

## 詳しい使い方ガイド

- [sim_to_real_calibration ファミリ ガイド](../guides/sim_to_real_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`calresult` を入力に取れる)

[simcal_identifiability](simcal_identifiability.md) · [simcal_validate](simcal_validate.md) · [simcal_discrepancy](simcal_discrepancy.md) · [simcal_report](../report/simcal_report.md)

## 同カテゴリ(`check`)

[simcal_identifiability](simcal_identifiability.md) · [simcal_validate](simcal_validate.md) · [simcal_discrepancy](simcal_discrepancy.md)

---
*Provenance: simcalcheck.py — SIMCAL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
