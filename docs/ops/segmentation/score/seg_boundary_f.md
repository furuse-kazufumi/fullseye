---
op: seg_boundary_f
dim: segmentation
category: score
in: labels2d × labels2d
out: table
examples: [poc_am_thermal_to_ct, poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# seg_boundary_f — SEGMENTATION `score` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_boundary_f(labels_pred, labels_true, *, tau: 'float' = 2.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segeval; segeval.seg_boundary_f(labels_pred, labels_true, *, tau: 'float' = 2.0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("seg_boundary_f")`)

## 使い方

境界 F 値(許容距離 τ): 予測の境界画素のうち真の境界から τ 以内にあるものの割合 = ``precision``、逆が ``recall``。

F = 2PR/(P+R)。境界は :func:`_boundary` の規約(ラベルの割れ目、1 画素幅)なので、ラベルの番号や背景の区別によらない
(分割の形だけを見る)。距離は距離変換(ユークリッド、画素の中心)。τ = 0 で画素の一致。
両方の境界が空(どちらも 1 色)なら P = R = F = 1、片方だけ空なら 0。
返り値: ``f``、``precision``、``recall``、``tau``、``n_pred_boundary`` / ``n_true_boundary``、
``dist_pred_to_true`` / ``dist_true_to_pred``(境界画素ごとの距離)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [segmentation_scoring_and_worlds](../guides/segmentation_scoring_and_worlds.md) — 分割の採点と真値つき合成世界 — どの物差しがどの壊れ方に盲目か

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_am_thermal_to_ct](../../../../examples/poc_am_thermal_to_ct.py) — `py -3.11 examples/poc_am_thermal_to_ct.py`
- [poc_graph_hierarchy_segmentation](../../../../examples/poc_graph_hierarchy_segmentation.py) — `py -3.11 examples/poc_graph_hierarchy_segmentation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`score`)

[seg_confusion_table](seg_confusion_table.md) · [seg_dice_jaccard](seg_dice_jaccard.md) · [seg_hausdorff](seg_hausdorff.md) · [seg_mean_surface_distance](seg_mean_surface_distance.md) · [seg_under_over_segmentation](seg_under_over_segmentation.md) · [seg_object_counts_match](seg_object_counts_match.md) · [seg_score_card](seg_score_card.md)

---
*Provenance: segeval.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
