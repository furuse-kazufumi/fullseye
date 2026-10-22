---
op: patchdist_fit
dim: spc
category: anomaly_patch
in: video
out: table
examples: [poc_patch_anomaly]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# patchdist_fit — SPC `anomaly_patch` op

- **データ種**: `video` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.patchdist_fit(stack, patch=8, stride=4, scales=(1.0, 2.0, 4.0), groups=('gradient', 'gabor', 'lbp'), n_orient=4, shrinkage='auto', n_dims=None, seed=0, ridge=1e-06, pool='position')` (実装を直接呼ぶなら `import anomaly_patch; anomaly_patch.patchdist_fit(stack, patch=8, stride=4, scales=(1.0, 2.0, 4.0), groups=('gradient', 'gabor', 'lbp'), n_orient=4, shrinkage='auto', n_dims=None, seed=0, ridge=1e-06, pool='position')`、台帳から引くなら `opsspc.get("patchdist_fit")`)

## 使い方

Learn a normal distribution of the patch feature at every grid position from good images (``table``).

``stack`` is (n, H, W) or (n, H, W, 3) of good images, n >= 2, registered well enough that a
grid cell sees the same content. The feature is ``patch_features`` (same parameters). At
every cell the mean and the covariance (maximum likelihood, divided by n) of the D-dimensional
feature are estimated; n <= D makes the covariance singular, so the **shrinkage toward
tr(S)/D * I is declared**: ``"auto"`` is the Ledoit–Wolf analytic intensity per position,
a number in (0, 1] fixes it, ``"none"`` (or 0) is accepted only when n - 1 >= D and the
covariance is positive definite and otherwise refused. ``n_dims`` keeps a seeded random subset of the
D dimensions (the memory trick of the original method), ``ridge`` (relative to the median
variance, applied unless ``shrinkage="none"``) is a numerical floor against exactly constant
channels. ``pool="position"`` (default) estimates one distribution per grid cell, right when
the content is registered; ``pool="global"`` estimates ONE distribution from the patches of
all cells and images (n * gh * gw samples, overlapping patches are not independent), right
for a stationary texture whose content at a cell differs from image to image and which has
far more samples than dimensions.

Returns the model: per-position ``mean`` and ``precision`` (inverse of the shrunk
covariance), ``shrinkage_map`` and its mean ``shrinkage_mean``, ``n_train``, ``dim``,
``dims`` (kept channels), the feature parameters and ``image_shape``. Pass it to
``patchdist_score``.

Raises ``ValueError`` for fewer than two images, a singular covariance with
``shrinkage="none"``, a constant feature that stays singular, or invalid parameters.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_patch_anomaly](../../../../examples/poc_patch_anomaly.py) — `py -3.11 examples/poc_patch_anomaly.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`anomaly_patch`)

[patch_features](patch_features.md) · [patchdist_score](patchdist_score.md) · [patchbank_fit](patchbank_fit.md) · [patchbank_score](patchbank_score.md)

---
*Provenance: anomaly_patch.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
