---
op: cover_ratio_grade
dim: segmentation
category: plant
in: signal
out: table
examples: [poc_weed_rice_ratio]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# cover_ratio_grade — SEGMENTATION `plant` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cover_ratio_grade(fraction, *, edges: 'Sequence[float]' = (0.05, 0.25, 0.5)) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import cropweed; cropweed.cover_ratio_grade(fraction, *, edges: 'Sequence[float]' = (0.05, 0.25, 0.5)) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("cover_ratio_grade")`)

## 使い方

被度(面積の割合 0..1)を、**宣言した境** ``edges`` で段階 0..len(edges) に分ける。

段階 k は edges[k−1] <= f < edges[k] (境ちょうどは上の段階)。既定の境 (0.05, 0.25, 0.50) は
植生調査の被度階級(Braun-Blanquet の 5 % / 25 % / 50 %)から借りたもので、4 段階
(0 少ない / 1 中程度 / 2 多い / 3 甚大)になる。注釈の分布から決めたものではない。
``fraction`` はスカラーか 1-D の配列。返す: ``grade``(int の配列)・``edges``・
``margin``(最も近い境までの距離。小さいほど判定が脆い)・``n_grades``・``counts``(段階ごとの数)。
空の入力・非有限値・[0, 1] の外・境が (0, 1) の中で狭義単調増加でないときは ``ValueError`` で拒否する。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_weed_rice_ratio](../../../../examples/poc_weed_rice_ratio.py) — `py -3.11 examples/poc_weed_rice_ratio.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md) · [fisher_lda_score](../classify/fisher_lda_score.md)

## 同カテゴリ(`plant`)

[plant_color_index](plant_color_index.md) · [superpixel_color_texture_features](superpixel_color_texture_features.md)

---
*Provenance: cropweed.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
