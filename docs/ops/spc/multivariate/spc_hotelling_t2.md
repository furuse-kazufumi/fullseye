---
op: spc_hotelling_t2
dim: spc
category: multivariate
in: matrix
out: table
examples: [poc_spc]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# spc_hotelling_t2 — SPC `multivariate` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spc_hotelling_t2(data, alpha=0.0027, mean=None, cov=None)` (実装を直接呼ぶなら `import spc; spc.spc_hotelling_t2(data, alpha=0.0027, mean=None, cov=None)`、台帳から引くなら `opsspc.get("spc_hotelling_t2")`)

## 使い方

Multivariate SPC by Hotelling's T² with an F-distributed control limit.

``data`` is a 2-D array of shape ``(m, p)`` — ``m`` observations of ``p``
correlated features. With the sample mean vector ``mu`` and covariance ``S``
(unless passed in explicitly), each row's statistic is::

    T^2_i = (x_i - mu)' S^-1 (x_i - mu)

charted against the phase-II control limit::

    UCL = p (m+1)(m-1) / (m (m-p)) * F_{alpha, p, m-p}

at false-alarm rate ``alpha`` (default 0.0027, the 3-sigma-equivalent). Returns
a dict with the per-row ``t2`` array, the ``ucl``, the integer indices
``out_of_control``, and ``in_control``. The mean row (``x == mu``) has
``T^2 == 0`` (pinned in the tests).

**Raises** ``ValueError``: a non-2-D / empty *data*, fewer observations than
features plus one (covariance not invertible), ``alpha`` outside ``(0, 1)``, a
singular covariance, or non-finite / mislabelled input.

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
