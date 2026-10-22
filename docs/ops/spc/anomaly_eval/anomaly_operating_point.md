---
op: anomaly_operating_point
dim: spc
category: anomaly_eval
in: signal × signal
out: table
examples: [poc_patch_anomaly]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# anomaly_operating_point — SPC `anomaly_eval` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.anomaly_operating_point(scores, labels, recall=0.95, confidence=0.95)` (実装を直接呼ぶなら `import anomeval; anomeval.anomaly_operating_point(scores, labels, recall=0.95, confidence=0.95)`、台帳から引くなら `opsspc.get("anomaly_operating_point")`)

## 使い方

Pick the highest threshold whose defect recall is guaranteed to be at least ``recall`` at ``confidence`` (``table``).

``scores`` (1-D, higher = more anomalous) and ``labels`` (1 / True = defective) are image
scores of a held-out set that was NOT used to fit the detector. Detecting k of the n
defective images, the exact one-sided Clopper–Pearson lower limit of the recall at level
``confidence`` is computed; the smallest k whose limit reaches ``recall`` fixes the threshold
at the k-th highest defect score (>= rule: the highest threshold that still carries the
guarantee, so the fewest false alarms). The guarantee holds for defects drawn like the
held-out ones; it is a statement about a sample, not about every future defect. Returns
``threshold``, ``recall_observed``, ``recall_lower`` (the limit), ``detected``, ``n_pos``,
``n_neg``, ``fpr`` (fraction of good images at or above the threshold), ``fpr_upper`` (its
one-sided Clopper–Pearson upper limit at the same level) and ``n_required`` (the smallest
number of defective images for which the guarantee is attainable at all:
ceil(ln(1 - confidence) / ln(recall))).

Raises ``ValueError`` when the guarantee is unattainable with so few defective images
(``n_pos < n_required``): it never returns a threshold it cannot back. Also on empty /
mismatched / non-finite input, non-binary labels, no good or no defective image, or
``recall`` / ``confidence`` outside (0, 1).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_patch_anomaly](../../../../examples/poc_patch_anomaly.py) — `py -3.11 examples/poc_patch_anomaly.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`anomaly_eval`)

[anomaly_image_auroc](anomaly_image_auroc.md) · [anomaly_pixel_auroc](anomaly_pixel_auroc.md) · [anomaly_pro](anomaly_pro.md) · [anomaly_region_overlap](anomaly_region_overlap.md) · [anomaly_pixel_f1_max](anomaly_pixel_f1_max.md) · [anomaly_image_f1_max](anomaly_image_f1_max.md)

---
*Provenance: anomeval.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
