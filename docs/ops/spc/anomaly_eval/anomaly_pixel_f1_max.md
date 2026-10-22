---
op: anomaly_pixel_f1_max
dim: spc
category: anomaly_eval
in: video × video
out: table
examples: [poc_patch_anomaly]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# anomaly_pixel_f1_max — SPC `anomaly_eval` op

- **データ種**: `video × video` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.anomaly_pixel_f1_max(scores, masks)` (実装を直接呼ぶなら `import anomeval; anomeval.anomaly_pixel_f1_max(scores, masks)`、台帳から引くなら `opsspc.get("anomaly_pixel_f1_max")`)

## 使い方

Best pixel-level F1 over all thresholds of anomaly score maps against defect masks (``table``).

``scores`` and ``masks`` are (n, H, W) (or lists / single 2-D maps); a pixel is predicted
defective when its score is >= the threshold. The F1 = 2TP / (2TP + FP + FN) is evaluated
exactly at every distinct score (sorted cumulative sums, no threshold grid); the highest
threshold wins a tie. Returns ``f1``, ``threshold``, ``precision`` and ``recall`` at the
maximum, ``n_pos`` and ``n_neg`` (pixels). It counts pixels, like the pixel AUROC, not
regions (see ``anomaly_pro``): a small defect weighs little however well it is found.

Raises ``ValueError`` on empty / mismatched / non-finite input, non-binary masks, or when
the masks contain no defect pixel or no good pixel.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_patch_anomaly](../../../../examples/poc_patch_anomaly.py) — `py -3.11 examples/poc_patch_anomaly.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`anomaly_eval`)

[anomaly_image_auroc](anomaly_image_auroc.md) · [anomaly_pixel_auroc](anomaly_pixel_auroc.md) · [anomaly_pro](anomaly_pro.md) · [anomaly_region_overlap](anomaly_region_overlap.md) · [anomaly_image_f1_max](anomaly_image_f1_max.md) · [anomaly_operating_point](anomaly_operating_point.md)

---
*Provenance: anomeval.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
