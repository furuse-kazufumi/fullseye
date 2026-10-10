---
op: spc_mt_sn_ratio
dim: spc
category: mt
in: signal
out: table
examples: [poc_spc]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# spc_mt_sn_ratio — SPC `mt` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spc_mt_sn_ratio(md)` (実装を直接呼ぶなら `import spc; spc.spc_mt_sn_ratio(md)`、台帳から引くなら `opsspc.get("spc_mt_sn_ratio")`)

## 使い方

Larger-the-better SN ratio of abnormal-sample distances, in decibels.

MT-method item selection asks which features earn their place: run the unit
space with a subset of features, score the *abnormal* samples, and keep the
subset whose distances are largest. The figure of merit is the
larger-the-better signal-to-noise ratio

    eta = -10 log10( (1/n) sum_i 1 / MD_i^2 )

an inverse-square average, so one abnormal sample that the subset fails to
separate drags the whole score down — which is the behaviour wanted when the
cost of a miss dominates. The caller drives the subsets (classically by an
orthogonal array); this operator is the closed-form score for one subset.

``md`` is a 1-D array of distances for the abnormal samples. Returns a dict
with ``sn_ratio_db``, the ``harmonic_mean_md_sq`` it came from, and ``n``.

For a constant ``MD == d`` the sum collapses and ``eta == 20 log10(d)``
exactly — pinned in the tests, and the reason a subset that puts every
abnormal sample at distance 10 scores exactly 20 dB.

**Raises** ``ValueError``: an empty or non-1-D *md*, a non-positive entry (a
zero distance would divide by zero: an abnormal sample sitting exactly on the
unit-space centre means the subset separates nothing), or non-finite input.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_spc](../../../../examples/poc_spc.py) — `py -3.11 examples/poc_spc.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`mt`)

[spc_mt_unit_space](spc_mt_unit_space.md) · [spc_mt_distance](spc_mt_distance.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
