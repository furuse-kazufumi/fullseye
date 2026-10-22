---
op: varmodel_calibrate
dim: spc
category: variation
in: table × video
out: table
examples: [poc_good_sample_variation_model]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# varmodel_calibrate — SPC `variation` op

- **データ種**: `table × video` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.varmodel_calibrate(model, good_images, far=None)` (実装を直接呼ぶなら `import varmodel; varmodel.varmodel_calibrate(model, good_images, far=None)`、台帳から引くなら `opsspc.get("varmodel_calibrate")`)

## 使い方

Re-derive the band half-width ``k`` from held-out good images, for data that break the normal assumption (``table``).

``model`` is a ``varmodel_fit`` table; ``good_images`` (m, H, W) are good samples that were
NOT used to fit it. Each is scored (``varmodel_score``, ``align="translate"``) and the
pooled |z| of all valid pixels gives the empirical (1 - far) quantile, which replaces ``k``
(``far`` defaults to the model's declared rate). Defects are never looked at: the threshold
still comes from the good distribution, only measured instead of assumed. Real images break
the per-pixel independent-normal model (residual misregistration, compression, lighting
drift); the closed-form k then under-states the false alarms and this is the honest fix.

Returns a copy of the model with ``k`` / ``lower`` / ``upper`` replaced and
``k_declared`` (the closed-form k), ``k_source`` = ``held-out quantile``,
``calibration_n_images``, ``calibration_n_pixels`` and ``calibration_far_declared_k``
(the false-alarm rate the closed-form k actually had on these good images).

Raises ``ValueError`` on an empty / malformed / non-finite set, a shape mismatch, a model
without the fitted keys, ``far`` outside its range, or fewer than 10/far calibration pixels
(the quantile would rest on fewer than 10 exceedances).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_good_sample_variation_model](../../../../examples/poc_good_sample_variation_model.py) — `py -3.11 examples/poc_good_sample_variation_model.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`variation`)

[varmodel_alignment](varmodel_alignment.md) · [varmodel_band_k](varmodel_band_k.md) · [varmodel_fit](varmodel_fit.md) · [varmodel_score](varmodel_score.md)

---
*Provenance: varmodel.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
