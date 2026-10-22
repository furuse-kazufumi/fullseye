---
op: anomaly_pro
dim: spc
category: anomaly_eval
in: video × video
out: table
examples: [anomaly_eval_metrics, poc_good_sample_variation_model, poc_patch_anomaly]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# anomaly_pro — SPC `anomaly_eval` op

- **データ種**: `video × video` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.anomaly_pro(scores, masks, fpr_max=0.3)` (実装を直接呼ぶなら `import anomeval; anomeval.anomaly_pro(scores, masks, fpr_max=0.3)`、台帳から引くなら `opsspc.get("anomaly_pro")`)

## 使い方

Per-region overlap (PRO) curve and its normalised area AUPRO up to ``fpr_max`` (``table``).

Definition (Bergmann et al., CVPR 2020): at a threshold t, every 8-connected defect region
C of every mask scores ``|{score >= t} ∩ C| / |C|``; PRO(t) is the mean over all regions,
so a small defect weighs as much as a large one. FPR(t) is the fraction of all good pixels
with score >= t. The curve is evaluated exactly at every distinct score (sorted cumulative
sums, no threshold grid), starts at (0, 0), is integrated by the trapezoid rule up to
``fpr_max`` (the customary 0.3; linear interpolation at the cut) and divided by ``fpr_max``
→ ``aupro`` in [0, 1]. Returns ``aupro``, ``fpr`` / ``pro`` (the curve up to the cut),
``n_regions``, ``fpr_max``.

Raises ``ValueError`` on empty / mismatched / non-finite input, non-binary masks, no defect
region, no good pixel, or ``fpr_max`` outside (0, 1].

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [anomaly_eval_metrics](../../../../examples/anomaly_eval_metrics.py) — `py -3.11 examples/anomaly_eval_metrics.py`
- [poc_good_sample_variation_model](../../../../examples/poc_good_sample_variation_model.py) — `py -3.11 examples/poc_good_sample_variation_model.py`
- [poc_patch_anomaly](../../../../examples/poc_patch_anomaly.py) — `py -3.11 examples/poc_patch_anomaly.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`anomaly_eval`)

[anomaly_image_auroc](anomaly_image_auroc.md) · [anomaly_pixel_auroc](anomaly_pixel_auroc.md) · [anomaly_region_overlap](anomaly_region_overlap.md) · [anomaly_pixel_f1_max](anomaly_pixel_f1_max.md) · [anomaly_image_f1_max](anomaly_image_f1_max.md) · [anomaly_operating_point](anomaly_operating_point.md)

---
*Provenance: anomeval.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
