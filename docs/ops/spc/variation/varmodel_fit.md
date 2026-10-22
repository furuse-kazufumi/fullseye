---
op: varmodel_fit
dim: spc
category: variation
in: video
out: table
examples: [poc_good_sample_variation_model, poc_patch_anomaly]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# varmodel_fit — SPC `variation` op

- **データ種**: `video` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.varmodel_fit(stack, spread='moderated', far=0.001, align='check', max_misalign_px=0.5, spread_floor=0.0, mask=None, *, chunk=262144)` (実装を直接呼ぶなら `import varmodel; varmodel.varmodel_fit(stack, spread='moderated', far=0.001, align='check', max_misalign_px=0.5, spread_floor=0.0, mask=None, *, chunk=262144)`、台帳から引くなら `opsspc.get("varmodel_fit")`)

## 使い方

Learn a per-pixel variation model (centre, spread, band half-width k) from a stack of good samples (``table``).

``stack`` is (n, H, W) or a list of equal 2-D images, all good. ``spread`` chooses the
estimator (``SPREADS``): ``std`` (mean / per-pixel sample std, needs n >= 3), ``pooled``
(mean / one std for all valid pixels — few samples, homoscedastic noise), ``moderated``
(mean / empirical-Bayes shrinkage of every pixel's variance toward a prior estimated from
all pixels, Smyth 2004 — few samples, heteroscedastic noise; the default) or ``mad``
(median / 1.4826 MAD — robust to a few defective images hidden in the "good" set, needs
n >= 5). ``far`` is the declared two-sided per-pixel false-alarm rate; ``k`` follows from it
(see ``varmodel_band_k``) and is never tuned on defects.

Alignment: ``align="check"`` measures every sample's translation (``varmodel_alignment``)
and REFUSES the stack if any exceeds ``max_misalign_px``; ``align="translate"`` registers the
samples to the median by a Fourier shift (all-pass, so white noise keeps its variance),
re-checks the residual against ``max_misalign_px`` and marks the wrapped border invalid.
A stack without structure (``alignment["observable"]`` False) is neither refused nor shifted;
its band is then only an intensity threshold on the overall variation. Stochastic textures,
whose every sample shows a different pattern, are therefore not a variation-model problem
(on DAGM 2007 Class1 it scores at chance — see the PoC).

``spread_floor`` (>= 0, image units) lower-bounds the spread (8-bit data has pixels whose
good samples are all equal); any remaining zero spread is refused. ``mask`` (H, W) bool
limits the inspected area. Returns ``center``, ``spread``, ``k``, ``far``, ``n``, ``df``,
``spread_kind``, ``lower`` / ``upper`` (the band), ``valid`` (bool), ``n_floored``,
``d0`` / ``s0`` (the prior's degrees of freedom and scale: 0 for std / mad; for pooled and a
fully pooled moderated prior d0 = valid pixels x (n - 1)), ``k_source``,
``mc_far_rel_se`` and ``alignment`` (the offset report, after registration if any).

Raises ``ValueError`` on an empty / malformed / non-finite stack, too few samples, an
unknown ``spread`` / ``align``, ``far`` outside its range, a misaligned stack, a mask of the
wrong shape, or zero spread left after the floor.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_good_sample_variation_model](../../../../examples/poc_good_sample_variation_model.py) — `py -3.11 examples/poc_good_sample_variation_model.py`
- [poc_patch_anomaly](../../../../examples/poc_patch_anomaly.py) — `py -3.11 examples/poc_patch_anomaly.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`variation`)

[varmodel_alignment](varmodel_alignment.md) · [varmodel_band_k](varmodel_band_k.md) · [varmodel_calibrate](varmodel_calibrate.md) · [varmodel_score](varmodel_score.md)

---
*Provenance: varmodel.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
