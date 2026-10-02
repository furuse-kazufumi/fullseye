---
op: seg_dice_jaccard
dim: segmentation
category: score
in: labels2d × labels2d
out: table
examples: [poc_am_thermal_to_ct, poc_segmentation_gauntlet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# seg_dice_jaccard — SEGMENTATION `score` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_dice_jaccard(labels_pred, labels_true, *, background: 'int' = 0, per_label: 'bool' = False) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segeval; segeval.seg_dice_jaccard(labels_pred, labels_true, *, background: 'int' = 0, per_label: 'bool' = False) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("seg_dice_jaccard")`)

## 使い方

Dice と Jaccard —— マスク(背景でない画素の和)で 1 組、``per_label`` なら真のラベルごとに最大重なりの相手と。

マスク: ``intersection`` = 両方とも背景でない画素数、``size_pred`` / ``size_true``、``union``。
Jaccard J = ∩/∪、Dice D = 2∩/(|P|+|T|)。両方空なら 1(何も無いと正しく言った)。恒等式 D = 2J/(1+J)(門)。
``per_label=True`` で ``labels``(背景でない真のラベル)、``per_dice`` / ``per_jaccard``(相手が無ければ 0)、
``mean_dice`` / ``mean_jaccard`` を足す。

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
- [poc_segmentation_gauntlet](../../../../examples/poc_segmentation_gauntlet.py) — `py -3.11 examples/poc_segmentation_gauntlet.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`score`)

[seg_confusion_table](seg_confusion_table.md) · [seg_boundary_f](seg_boundary_f.md) · [seg_hausdorff](seg_hausdorff.md) · [seg_mean_surface_distance](seg_mean_surface_distance.md) · [seg_under_over_segmentation](seg_under_over_segmentation.md) · [seg_object_counts_match](seg_object_counts_match.md) · [seg_score_card](seg_score_card.md)

---
*Provenance: segeval.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
