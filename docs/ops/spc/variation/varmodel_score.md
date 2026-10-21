---
op: varmodel_score
dim: spc
category: variation
in: image2d × table
out: table
examples: [poc_good_sample_variation_model, poc_patch_anomaly]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# varmodel_score — SPC `variation` op

- **データ種**: `image2d × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.varmodel_score(image, model, mask=None, align='check')` (実装を直接呼ぶなら `import varmodel; varmodel.varmodel_score(image, model, mask=None, align='check')`、台帳から引くなら `opsspc.get("varmodel_score")`)

## 使い方

Score one image against a ``varmodel_fit`` model: z map in sigmas, out-of-band map and a per-region explanation (``table``).

``z = (image - center) / spread`` on valid pixels (0 elsewhere); a pixel is out of band
when ``|z| > k``. Out-of-band pixels are grouped into 8-connected regions; each region
reports ``area``, ``peak_z`` (signed, the largest |z|), ``mean_abs_z``, ``polarity``
(``bright`` / ``dark`` / ``mixed``), ``centroid`` (row, col), ``bbox`` (r0, c0, r1, c1,
exclusive end) and ``peak_pos``; regions are sorted by |peak_z| (rounded to 1e-9, ties by
label order). Also returns ``z``, ``exceed``, ``valid`` (scored pixels, image grid), ``n_exceed``, ``n_valid``, ``k``, ``far``,
``expected_false`` = far * n_valid and ``count_pvalue`` = P(Binomial(n_valid, far) >=
n_exceed) — that p-value assumes independent pixels and is optimistic for spatially
correlated noise (reported, not used to decide).

Alignment: the image's translation against the model centre is measured as in
``varmodel_alignment`` and returned as ``offset``. ``align="check"`` REFUSES an image
displaced by more than the model's ``max_misalign_px``; ``align="translate"`` registers it
to the model by a Fourier shift, computes z in model coordinates and maps ``z`` /
``exceed`` back onto the image grid by the rounded offset (the wrapped border is invalid),
so the maps line up with masks drawn on the original image. ``mask`` is on the image grid.

Raises ``ValueError`` when ``image`` is empty / not 2-D / non-finite, its shape differs
from the model, ``model`` lacks the fitted keys, ``mask`` has the wrong shape, ``align`` is
unknown, or the image is misaligned (``check``) / displaced by more than a quarter of the
image (``translate``).

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

[varmodel_alignment](varmodel_alignment.md) · [varmodel_band_k](varmodel_band_k.md) · [varmodel_fit](varmodel_fit.md) · [varmodel_calibrate](varmodel_calibrate.md)

---
*Provenance: varmodel.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
