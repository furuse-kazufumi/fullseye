---
op: anomaly_region_overlap
dim: spc
category: anomaly_eval
in: video × video
out: table
examples: [anomaly_eval_metrics, poc_good_sample_variation_model, poc_patch_anomaly]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# anomaly_region_overlap — SPC `anomaly_eval` op

- **データ種**: `video × video` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.anomaly_region_overlap(predicted, masks, min_overlap=0.5)` (実装を直接呼ぶなら `import anomeval; anomeval.anomaly_region_overlap(predicted, masks, min_overlap=0.5)`、台帳から引くなら `opsspc.get("anomaly_region_overlap")`)

## 使い方

Per-region overlap of a binary defect prediction with the ground-truth regions at one operating point (``table``).

``predicted`` and ``masks`` are binary (n, H, W) (or 2-D). For every 8-connected
ground-truth region C: ``overlap = |predicted ∩ C| / |C|``; a region counts as detected
when ``overlap >= min_overlap``. Returns ``overlap`` (per region, in mask order),
``pro`` (their mean = one point of the PRO curve), ``detected_fraction``, ``hit_any``
(fraction of regions touched by at least one predicted pixel), ``fpr`` (predicted good
pixels / good pixels), ``n_regions``, ``min_overlap``.

Raises ``ValueError`` on empty / mismatched / non-binary input, no ground-truth region, or
``min_overlap`` outside (0, 1].

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

[anomaly_image_auroc](anomaly_image_auroc.md) · [anomaly_pixel_auroc](anomaly_pixel_auroc.md) · [anomaly_pro](anomaly_pro.md) · [anomaly_pixel_f1_max](anomaly_pixel_f1_max.md) · [anomaly_image_f1_max](anomaly_image_f1_max.md) · [anomaly_operating_point](anomaly_operating_point.md)

---
*Provenance: anomeval.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
