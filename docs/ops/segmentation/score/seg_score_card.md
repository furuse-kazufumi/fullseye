---
op: seg_score_card
dim: segmentation
category: score
in: labels2d × labels2d
out: table
examples: [poc_segmentation_gauntlet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# seg_score_card — SEGMENTATION `score` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_score_card(labels_pred, labels_true, *, background: 'int' = 0, tau: 'float' = 2.0, min_overlap: 'float' = 0.5) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import segeval; segeval.seg_score_card(labels_pred, labels_true, *, background: 'int' = 0, tau: 'float' = 2.0, min_overlap: 'float' = 0.5) -> 'Dict[str, float]'`、台帳から引くなら `opssegmentation.get("seg_score_card")`)

## 使い方

全部の物差しを 1 枚に: Dice・Jaccard(マスク)、VI・split・merge、Rand・ARI(``segcompare``)、境界 F(τ)、
Hausdorff・HD95・ASSD(境界が無ければ NaN)、過分割・未分割、分裂・融合・欠落・偽・一致、個数。

``segcompare`` には a = 真、b = 予測で渡す(split = 予測が真を切った量、merge = 予測が真を貼った量)。
値は float か int の平らな dict(表にそのまま並ぶ)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [segmentation_scoring_and_worlds](../guides/segmentation_scoring_and_worlds.md) — 分割の採点と真値つき合成世界 — どの物差しがどの壊れ方に盲目か

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_segmentation_gauntlet](../../../../examples/poc_segmentation_gauntlet.py) — `py -3.11 examples/poc_segmentation_gauntlet.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`score`)

[seg_confusion_table](seg_confusion_table.md) · [seg_dice_jaccard](seg_dice_jaccard.md) · [seg_boundary_f](seg_boundary_f.md) · [seg_hausdorff](seg_hausdorff.md) · [seg_mean_surface_distance](seg_mean_surface_distance.md) · [seg_under_over_segmentation](seg_under_over_segmentation.md) · [seg_object_counts_match](seg_object_counts_match.md)

---
*Provenance: segeval.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
