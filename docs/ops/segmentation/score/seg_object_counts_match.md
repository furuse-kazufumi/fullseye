---
op: seg_object_counts_match
dim: segmentation
category: score
in: labels2d × labels2d
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# seg_object_counts_match — SEGMENTATION `score` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_object_counts_match(labels_pred, labels_true, *, background: 'int' = 0, min_overlap: 'float' = 0.5) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segeval; segeval.seg_object_counts_match(labels_pred, labels_true, *, background: 'int' = 0, min_overlap: 'float' = 0.5) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("seg_object_counts_match")`)

## 使い方

物体の個数の一致: 分裂・融合・欠落・偽・一致を、「主に重なる」辺の 2 部グラフの次数で数える。

真 i と予測 j(どちらも背景でない)の間に辺を置く条件 = 重なり n_ij ≥ ``min_overlap`` × min(|i|, |j|)
(小さい方がもう一方に主に入っている)。真の次数 d_i、予測の次数 e_j:
``missed`` = #{d_i = 0}、``false`` = #{e_j = 0}、``split`` = #{d_i ≥ 2}(1 つの真が複数の予測に割れた)、
``merged`` = #{e_j ≥ 2}(1 つの予測が複数の真を抱えた)、``matched`` = #{d_i = 1 かつ その相手の e_j = 1}。
``counts_match`` = 真と予測の個数が同じで全部が一致。min_overlap > 0.5 なら各予測は高々 1 つの真に「主に入る」が、
真が小さく予測が大きい辺もあるので融合は検出できる。
返り値: 上の数 + ``n_true`` / ``n_pred``、``edges``(真ラベル, 予測ラベル)の (m, 2)、``split_true`` / ``merged_pred`` /
``missed_true`` / ``false_pred``(ラベルの配列)、``min_overlap``。

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

[seg_confusion_table](seg_confusion_table.md) · [seg_dice_jaccard](seg_dice_jaccard.md) · [seg_boundary_f](seg_boundary_f.md) · [seg_hausdorff](seg_hausdorff.md) · [seg_mean_surface_distance](seg_mean_surface_distance.md) · [seg_under_over_segmentation](seg_under_over_segmentation.md) · [seg_score_card](seg_score_card.md)

---
*Provenance: segeval.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
