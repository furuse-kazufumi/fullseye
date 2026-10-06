---
op: classify_image_class_lut
dim: segmentation
category: classify
in: image2d × signal
out: labels2d
examples: [halcon_segmentation_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# classify_image_class_lut — SEGMENTATION `classify` op

- **データ種**: `image2d × signal` → `labels2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.classify_image_class_lut(image, lut)` (実装を直接呼ぶなら `import segmentation; segmentation.classify_image_class_lut(image, lut)`、台帳から引くなら `opssegmentation.get("classify_image_class_lut")`)

## 使い方

グレー LUT による画素分類(閾値/ラベル LUT)(classify_image_class_lut)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [halcon_segmentation_tour](../../../../examples/halcon_segmentation_tour.py) — `py -3.11 examples/halcon_segmentation_tour.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

[watersheds_marker](../watershed/watersheds_marker.md) · [seg_confusion_table](../score/seg_confusion_table.md) · [seg_dice_jaccard](../score/seg_dice_jaccard.md) · [seg_boundary_f](../score/seg_boundary_f.md) · [seg_hausdorff](../score/seg_hausdorff.md) · [seg_mean_surface_distance](../score/seg_mean_surface_distance.md) · [seg_under_over_segmentation](../score/seg_under_over_segmentation.md) · [seg_object_counts_match](../score/seg_object_counts_match.md)

## 同カテゴリ(`classify`)

[class_2dim_sup](class_2dim_sup.md) · [class_2dim_unsup](class_2dim_unsup.md) · [learn_ndim_norm](learn_ndim_norm.md) · [class_ndim_norm](class_ndim_norm.md)

---
*Provenance: segmentation.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
