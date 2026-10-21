---
op: patchdist_score
dim: spc
category: anomaly_patch
in: image2d × table
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# patchdist_score — SPC `anomaly_patch` op

- **データ種**: `image2d × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.patchdist_score(image, model, smooth=4.0)` (実装を直接呼ぶなら `import anomaly_patch; anomaly_patch.patchdist_score(image, model, smooth=4.0)`、台帳から引くなら `opsspc.get("patchdist_score")`)

## 使い方

Score one image against a per-position normal distribution: the Mahalanobis distance per patch (``table``).

``model`` comes from ``patchdist_fit``; ``image`` must have the training images' shape. The
grid of distances ``sqrt((x - mu)' P (x - mu))`` is interpolated (bilinear, between patch
centres) to the image size and smoothed by a Gaussian of ``smooth`` px (0 = no smoothing).
Returns ``map`` (H, W; higher = more anomalous), ``grid`` (the raw distances),
``image_score`` (the maximum of the smoothed map) and ``smooth``.

Raises ``ValueError`` for a model that is not a ``patchdist_fit`` result, a different image
shape, or a negative / non-finite ``smooth``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`anomaly_patch`)

[patch_features](patch_features.md) · [patchdist_fit](patchdist_fit.md) · [patchbank_fit](patchbank_fit.md) · [patchbank_score](patchbank_score.md)

---
*Provenance: anomaly_patch.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
