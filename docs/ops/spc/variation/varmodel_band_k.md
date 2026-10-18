---
op: varmodel_band_k
dim: spc
category: variation
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# varmodel_band_k — SPC `variation` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.varmodel_band_k(n=20, far=0.001, spread='std', df_prior=None)` (実装を直接呼ぶなら `import varmodel; varmodel.varmodel_band_k(n=20, far=0.001, spread='std', df_prior=None)`、台帳から引くなら `opsspc.get("varmodel_band_k")`)

## 使い方

Half-width ``k`` (in spread units) of the tolerance band for a declared two-sided per-pixel false-alarm rate (``table``).

A new good pixel ``x`` is flagged when ``|x - center| > k * spread``. Under per-pixel
independent normal good samples:

  * ``std``: ``(x - mean)/(s * sqrt(1+1/n)) ~ t_{n-1}`` so ``k = t_{n-1}^-1(1 - far/2) * sqrt(1+1/n)``.
  * ``pooled``: one variance pooled over many pixels (degrees of freedom ``df_prior``; ``None``
    = infinite) → normal quantile.
  * ``moderated``: empirical-Bayes shrunk variance with ``df_prior`` = d0 prior degrees of
    freedom (Smyth 2004) → ``t_{n-1+d0}``.
  * ``mad``: median / MAD centre and spread → no closed form, but the ratio is a pivot, so k
    is a Monte-Carlo quantile that depends on (n, far) only (fixed seed; ``mc_far_rel_se`` is
    the relative standard error of the achieved rate). Needs ``n >= 5`` and ``far >= 1e-3``.

The threshold comes from the distribution, never from test defects. Returns ``k``, ``df``
(0 for ``mad``: no t quantile is involved),
``far``, ``n``, ``spread``, ``source``, ``mc_far_rel_se``.

Raises ``ValueError`` for ``n < 2`` (``mad``: ``n < 5``), ``far`` outside [1e-9, 0.5),
an unknown ``spread`` or a non-positive ``df_prior``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`variation`)

[varmodel_alignment](varmodel_alignment.md) · [varmodel_fit](varmodel_fit.md) · [varmodel_calibrate](varmodel_calibrate.md) · [varmodel_score](varmodel_score.md)

---
*Provenance: varmodel.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
