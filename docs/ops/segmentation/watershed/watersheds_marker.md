---
op: watersheds_marker
dim: segmentation
category: watershed
in: image2d × labels2d
out: labels2d
examples: [halcon_segmentation_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# watersheds_marker — SEGMENTATION `watershed` op

- **データ種**: `image2d × labels2d` → `labels2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.watersheds_marker(image, markers)` (実装を直接呼ぶなら `import segmentation; segmentation.watersheds_marker(image, markers)`、台帳から引くなら `opssegmentation.get("watersheds_marker")`)

## 使い方

マーカー制御 watershed 分割(watersheds_marker)。markers: int ラベル画像(0=未割当)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [halcon_segmentation_tour](../../../../examples/halcon_segmentation_tour.py) — `py -3.11 examples/halcon_segmentation_tour.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

[seg_confusion_table](../score/seg_confusion_table.md) · [seg_dice_jaccard](../score/seg_dice_jaccard.md) · [seg_boundary_f](../score/seg_boundary_f.md) · [seg_hausdorff](../score/seg_hausdorff.md) · [seg_mean_surface_distance](../score/seg_mean_surface_distance.md) · [seg_under_over_segmentation](../score/seg_under_over_segmentation.md) · [seg_object_counts_match](../score/seg_object_counts_match.md) · [seg_score_card](../score/seg_score_card.md)

## 同カテゴリ(`watershed`)

—

---
*Provenance: segmentation.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
