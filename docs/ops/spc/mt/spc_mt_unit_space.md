---
op: spc_mt_unit_space
dim: spc
category: mt
in: matrix
out: table
examples: [poc_mt_hidden_fault, poc_spc]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# spc_mt_unit_space — SPC `mt` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spc_mt_unit_space(data)` (実装を直接呼ぶなら `import spc; spc.spc_mt_unit_space(data)`、台帳から引くなら `opsspc.get("spc_mt_unit_space")`)

## 使い方

Build an MT-method unit space from known-good observations.

``data`` is a 2-D array of shape ``(n, p)`` — ``n`` observations of ``p``
features, **all of which must be normal product**. The unit space is the
triple ``(mean, std, inv_corr)``: per-feature mean and ddof=1 standard
deviation, and the inverse of the correlation matrix of the standardised
data. Feed it to :func:`spc_mt_distance` to score new observations.

Returns a dict with ``mean``, ``std``, ``corr`` and ``inv_corr`` arrays, the
unit space's own ``md`` per row, ``md_sq_mean``, the exact expected value
``md_sq_mean_exact = (n-1)/n``, the counts ``n`` and ``p``, how many features
had no spread (``flat_features``), and whether the correlation matrix was
singular enough to need a pseudo-inverse (``pseudo_inverse``).

The mean of ``md**2`` over the unit space equals ``(n-1)/n`` exactly — the
quantitative form of "a unit space averages a distance of one". It reaches 1
only as ``n`` grows; the deficit is exactly ``1/n``.

**Raises** ``ValueError``: a non-2-D / empty *data*, fewer than two
observations (no spread to standardise by), zero features, or non-finite
input.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_mt_hidden_fault](../../../../examples/poc_mt_hidden_fault.py) — `py -3.11 examples/poc_mt_hidden_fault.py`
- [poc_spc](../../../../examples/poc_spc.py) — `py -3.11 examples/poc_spc.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`mt`)

[spc_mt_distance](spc_mt_distance.md) · [spc_mt_sn_ratio](spc_mt_sn_ratio.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
