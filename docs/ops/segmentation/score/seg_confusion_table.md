---
op: seg_confusion_table
dim: segmentation
category: score
in: labels2d × labels2d
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# seg_confusion_table — SEGMENTATION `score` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_confusion_table(labels_pred, labels_true, *, background: 'int' = 0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segeval; segeval.seg_confusion_table(labels_pred, labels_true, *, background: 'int' = 0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("seg_confusion_table")`)

## 使い方

ラベル対応の分割表(行 = 真、列 = 予測)と、最大重なりによる対応・対応の一意性の印。

``table[i, j]`` = 真のラベル ``labels_true[i]`` と予測のラベル ``labels_pred[j]`` を同時に持つ画素数。
対応は **最大重なり**: 真 i の相手 = 背景でない列のうち ``table[i, :]`` が最大の列(``pred_of_true``、ラベル値、無ければ −1)、
予測 j の相手 = 背景でない行のうち最大の行(``true_of_pred``)。``mutual_true[i]`` = 真 i の相手が真 i を選び返す、
``mutual_pred[j]`` も同様。``claims[j]`` = 予測 j を相手に選んだ真の数。``unique_matching`` = 背景でない行・列がすべて相互に
選び合う(= 1 対 1 の全単射)。背景の行・列は表には残り、対応からは外す。
Hungarian(総和最大の割当)でなく argmax なので、1 つの大きな予測を複数の真が選ぶことがある —— それが ``claims`` ≥ 2 の印。

返り値: ``table``、``labels_true`` / ``labels_pred``(行・列のラベル値)、``row_sums`` / ``col_sums``、``pred_of_true`` /
``true_of_pred``、``mutual_true`` / ``mutual_pred``、``claims``、``unique_matching``、``n_true`` / ``n_pred``(背景を除く個数)、``n``。

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

[seg_dice_jaccard](seg_dice_jaccard.md) · [seg_boundary_f](seg_boundary_f.md) · [seg_hausdorff](seg_hausdorff.md) · [seg_mean_surface_distance](seg_mean_surface_distance.md) · [seg_under_over_segmentation](seg_under_over_segmentation.md) · [seg_object_counts_match](seg_object_counts_match.md) · [seg_score_card](seg_score_card.md)

---
*Provenance: segeval.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
