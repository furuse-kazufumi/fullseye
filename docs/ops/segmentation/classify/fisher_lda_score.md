---
op: fisher_lda_score
dim: segmentation
category: classify
in: table × matrix
out: table
examples: [poc_weed_rice_ratio]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# fisher_lda_score — SEGMENTATION `classify` op

- **データ種**: `table × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fisher_lda_score(model, X) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import cropweed; cropweed.fisher_lda_score(model, X) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("fisher_lda_score")`)

## 使い方

``fisher_lda_fit`` の学習済みの判別で特徴を採点する(score > 0 をクラス 1 とする)。

``model`` は ``fisher_lda_fit`` の返り、``X`` は (N, D) の特徴(dict の ``X`` も可)。標準化は学習時の
平均と尺度を使う。返す: ``score``(N)・``label``(0/1。**score がちょうど 0 はクラス 0**、宣言した規則)・
``margin``(|score| / ‖w‖ = 標準化空間で境界までの距離)・``n1``(クラス 1 と判定した数)。
空の入力・列数の食い違い・非有限値・学習済みの判別でない ``model`` は ``ValueError`` で拒否する。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_weed_rice_ratio](../../../../examples/poc_weed_rice_ratio.py) — `py -3.11 examples/poc_weed_rice_ratio.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](class_ndim_norm.md)

## 同カテゴリ(`classify`)

[class_2dim_sup](class_2dim_sup.md) · [class_2dim_unsup](class_2dim_unsup.md) · [learn_ndim_norm](learn_ndim_norm.md) · [class_ndim_norm](class_ndim_norm.md) · [classify_image_class_lut](classify_image_class_lut.md) · [fisher_lda_fit](fisher_lda_fit.md)

---
*Provenance: cropweed.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
