---
op: seg_under_over_segmentation
dim: segmentation
category: score
in: labels2d × labels2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# seg_under_over_segmentation — SEGMENTATION `score` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_under_over_segmentation(labels_pred, labels_true, *, background: 'int' = 0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segeval; segeval.seg_under_over_segmentation(labels_pred, labels_true, *, background: 'int' = 0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("seg_under_over_segmentation")`)

## 使い方

過分割・未分割の数を、分割表の多数決の多重度で数える(Levine & Nazif 流: 領域の数で)。

各予測(背景以外)を、最も重なる真(背景も候補)に帰属させる。真 i に帰属した予測の数 k_i が ``pieces_per_true``、
``over`` = Σ max(k_i − 1, 0)(1 つの真が何個に割れたか)。各真を最も重なる予測に帰属させ、予測 j に帰属した真の数 m_j が
``objects_per_pred``、``under`` = Σ max(m_j − 1, 0)(1 つの予測が何個の真を抱えたか)。
背景に帰属した予測は ``spurious``(偽)、背景に帰属した真は ``missed``(欠落)に数える。
返り値: ``over``、``under``、``spurious``、``missed``、``labels_true`` / ``pieces_per_true``、``labels_pred`` / ``objects_per_pred``、
``over_segmented_true``(k ≥ 2 の真のラベル)、``under_segmented_pred``(m ≥ 2 の予測のラベル)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [segmentation_scoring_and_worlds](../guides/segmentation_scoring_and_worlds.md) — 分割の採点と真値つき合成世界 — どの物差しがどの壊れ方に盲目か

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_graph_hierarchy_segmentation](../../../../examples/poc_graph_hierarchy_segmentation.py) — `py -3.11 examples/poc_graph_hierarchy_segmentation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`score`)

[seg_confusion_table](seg_confusion_table.md) · [seg_dice_jaccard](seg_dice_jaccard.md) · [seg_boundary_f](seg_boundary_f.md) · [seg_hausdorff](seg_hausdorff.md) · [seg_mean_surface_distance](seg_mean_surface_distance.md) · [seg_object_counts_match](seg_object_counts_match.md) · [seg_score_card](seg_score_card.md)

---
*Provenance: segeval.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
