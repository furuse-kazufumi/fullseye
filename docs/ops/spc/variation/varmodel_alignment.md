---
op: varmodel_alignment
dim: spc
category: variation
in: video
out: table
examples: [poc_good_sample_variation_model]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# varmodel_alignment — SPC `variation` op

- **データ種**: `video` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.varmodel_alignment(stack, max_misalign_px=0.5)` (実装を直接呼ぶなら `import varmodel; varmodel.varmodel_alignment(stack, max_misalign_px=0.5)`、台帳から引くなら `opsspc.get("varmodel_alignment")`)

## 使い方

Translation offset of every good sample against the typical position of the stack, and the margin to the tolerance (``table``).

Each image of ``stack`` (n, H, W) is phase-correlated (``filters_freq.phase_correlation_fft``)
against a reference built from the stack itself (the most typical sample, then the
registered mean); the integer peak is refined to 1/20 px by an upsampled DFT
(Guizar-Sicairos et al. 2008). Offsets are relative to the median offset, so a common
shift of every sample is not a misalignment. Returns ``offset`` (n, 2) = (row, col) in px
(positive = the sample sits further down / right than the typical one), ``abs_offset`` (n,) = the larger of the two, ``margin_px``
= ``max_misalign_px - abs_offset`` (negative = this sample breaks the tolerance), ``ok``
(all margins >= 0), ``worst`` (index of the most shifted sample) and ``psr`` (peak-to-
sidelobe ratio of the correlation), ``shift_sd_px`` (Cramér–Rao lower bound of the offset's
spread: noise variance over the structural gradient energy of the registered mean; the
window makes the real spread a few times larger) and
``observable``. A featureless or pure-noise stack has no structure, so its offsets cannot be
measured (``observable=False``, offsets reported as 0, ``shift_sd_px`` capped at the image
size) — and for the
same reason a shift cannot fatten its band, so such a stack is not refused.

Why it matters: a per-pixel spread learned from a misaligned stack is inflated wherever the
image has gradient (edges), so the tolerance band gets fatter and real defects there are missed.

Raises ``ValueError`` on an empty stack, a stack that is not (n, H, W) / a list of equal
2-D images, non-finite values, or ``max_misalign_px`` <= 0.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_good_sample_variation_model](../../../../examples/poc_good_sample_variation_model.py) — `py -3.11 examples/poc_good_sample_variation_model.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`variation`)

[varmodel_band_k](varmodel_band_k.md) · [varmodel_fit](varmodel_fit.md) · [varmodel_calibrate](varmodel_calibrate.md) · [varmodel_score](varmodel_score.md)

---
*Provenance: varmodel.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
