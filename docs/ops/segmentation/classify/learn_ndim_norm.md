---
op: learn_ndim_norm
dim: segmentation
category: classify
in: matrix
out: table
examples: [halcon_segmentation_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# learn_ndim_norm — SEGMENTATION `classify` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.learn_ndim_norm(features_fg, features_bg=None)` (実装を直接呼ぶなら `import segmentation; segmentation.learn_ndim_norm(features_fg, features_bg=None)`、台帳から引くなら `opssegmentation.get("learn_ndim_norm")`)

## 使い方

特徴ベクトル群から正規分布クラス(平均・共分散)を学習(learn_ndim_norm)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [halcon_segmentation_tour](../../../../examples/halcon_segmentation_tour.py) — `py -3.11 examples/halcon_segmentation_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](class_ndim_norm.md)

## 同カテゴリ(`classify`)

[class_2dim_sup](class_2dim_sup.md) · [class_2dim_unsup](class_2dim_unsup.md) · [class_ndim_norm](class_ndim_norm.md) · [classify_image_class_lut](classify_image_class_lut.md)

---
*Provenance: segmentation.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
