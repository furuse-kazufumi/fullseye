---
op: anomaly_image_f1_max
dim: spc
category: anomaly_eval
in: signal × signal
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# anomaly_image_f1_max — SPC `anomaly_eval` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.anomaly_image_f1_max(scores, labels)` (実装を直接呼ぶなら `import anomeval; anomeval.anomaly_image_f1_max(scores, labels)`、台帳から引くなら `opsspc.get("anomaly_image_f1_max")`)

## 使い方

Best image-level F1 over all thresholds from one anomaly score per image and a good/defective label (``table``).

``scores`` is a 1-D array (higher = more anomalous), ``labels`` the same length with 1 /
True = defective; an image is predicted defective when its score is >= the threshold.
Exact at every distinct score; the highest threshold wins a tie. Returns ``f1``,
``threshold``, ``precision``, ``recall``, ``n_pos`` and ``n_neg`` (images).

Raises ``ValueError`` on empty / mismatched / non-finite input, non-binary labels, or when
all images carry the same label.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`anomaly_eval`)

[anomaly_image_auroc](anomaly_image_auroc.md) · [anomaly_pixel_auroc](anomaly_pixel_auroc.md) · [anomaly_pro](anomaly_pro.md) · [anomaly_region_overlap](anomaly_region_overlap.md) · [anomaly_pixel_f1_max](anomaly_pixel_f1_max.md) · [anomaly_operating_point](anomaly_operating_point.md)

---
*Provenance: anomeval.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
