---
op: seg_hausdorff
dim: segmentation
category: score
in: labels2d × labels2d
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# seg_hausdorff — SEGMENTATION `score` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_hausdorff(labels_pred, labels_true, *, percentile: 'float' = 95.0) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import segeval; segeval.seg_hausdorff(labels_pred, labels_true, *, percentile: 'float' = 95.0) -> 'Dict[str, float]'`、台帳から引くなら `opssegmentation.get("seg_hausdorff")`)

## 使い方

境界画素の集合の間の Hausdorff 距離 = max(max 予測→真, max 真→予測)と、その ``percentile`` 版(HD95 など)。

境界は :func:`_boundary` の規約。どちらかの境界が空(1 色の画像)なら測るものが無いので ValueError。
返り値: ``hausdorff``、``hausdorff_percentile``、``percentile``、``directed_pred_to_true`` / ``directed_true_to_pred``(各最大)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [segmentation_scoring_and_worlds](../guides/segmentation_scoring_and_worlds.md) — 分割の採点と真値つき合成世界 — どの物差しがどの壊れ方に盲目か

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`score`)

[seg_confusion_table](seg_confusion_table.md) · [seg_dice_jaccard](seg_dice_jaccard.md) · [seg_boundary_f](seg_boundary_f.md) · [seg_mean_surface_distance](seg_mean_surface_distance.md) · [seg_under_over_segmentation](seg_under_over_segmentation.md) · [seg_object_counts_match](seg_object_counts_match.md) · [seg_score_card](seg_score_card.md)

---
*Provenance: segeval.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
