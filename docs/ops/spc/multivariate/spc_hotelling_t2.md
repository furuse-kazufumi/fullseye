---
op: spc_hotelling_t2
dim: spc
category: multivariate
in: matrix
out: table
gpu: なし
examples: [poc_spc]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# spc_hotelling_t2 — SPC `multivariate` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spc_hotelling_t2(data, alpha=0.0027, mean=None, cov=None)` (実装を直接呼ぶなら `import spc; spc.spc_hotelling_t2(data, alpha=0.0027, mean=None, cov=None)`、台帳から引くなら `opsspc.get("spc_hotelling_t2")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Multivariate SPC by Hotelling's T² with the control limit of the phase being charted.

``data`` is a 2-D array of shape ``(m, p)`` — ``m`` observations of ``p``
correlated features. Each row's statistic is::

    T^2_i = (x_i - mu)' S^-1 (x_i - mu)

The control limit depends on where ``mu`` and ``S`` come from, and the op
picks it from what you pass:

* **Phase I (default, neither ``mean`` nor ``cov``)** — ``mu`` and ``S`` are
  the sample mean and ``ddof=1`` covariance of the *same* rows. Then
  ``m T^2_i / (m-1)^2`` follows ``Beta(p/2, (m-p-1)/2)`` exactly (Gnanadesikan
  & Kettenring 1972; Tracy, Young & Mason 1992), so::

      UCL = (m-1)^2 / m * Beta_{1-alpha}(p/2, (m-p-1)/2)

  In phase I ``T^2_i <= (m-1)^2/m`` holds for every row whatever the data, so
  the phase-II F limit (which exceeds that bound for small ``m``) can never
  alarm there. Needs ``m >= p + 2``.
* **Known parameters (both ``mean`` and ``cov``)** — the in-control mean and
  covariance are taken as known (a specification, or estimates from a very
  large reference). Then ``T^2 ~ chi^2_p`` and ``UCL = chi^2_{p, 1-alpha}``,
  independent of how many rows are charted (one row is enough).
* **Phase II with estimated parameters** — if ``mean`` / ``cov`` were estimated
  from a separate in-control reference of ``n`` rows and new rows are charted
  against them, the exact limit is
  ``p (n+1)(n-1) / (n (n-p)) * F_{1-alpha}(p, n-p)`` with ``n`` the size of the
  *reference*, not of the charted data. This op treats passed parameters as
  known (chi-square limit, the ``n -> inf`` limit of that F form); for a small
  reference compute the F limit with your ``n`` and compare ``t2`` against it.

Passing only one of ``mean`` / ``cov`` is refused: no standard control limit
exists for a half-known parameter set.

At false-alarm rate ``alpha`` (default 0.0027, the 3-sigma-equivalent). Returns
a dict with the per-row ``t2`` array, the ``ucl``, the ``phase`` used
(``"phase_I"`` / ``"known"``), the integer indices ``out_of_control``, and
boolean ``in_control``. The mean row (``x == mu``) has ``T^2 == 0`` (pinned in
the tests).

**Raises** ``ValueError``: a non-2-D / empty *data*, fewer than ``p+2``
observations in phase I, only one of ``mean`` / ``cov``, ``alpha`` outside
``(0, 1)``, a singular covariance, or non-finite / mislabelled input.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_spc](../../../../examples/poc_spc.py) — `py -3.11 examples/poc_spc.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`multivariate`)

—

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
