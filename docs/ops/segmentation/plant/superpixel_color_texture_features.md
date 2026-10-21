---
op: superpixel_color_texture_features
dim: segmentation
category: plant
in: rgbimage × labels2d
out: table
examples: [poc_weed_rice_ratio]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# superpixel_color_texture_features — SEGMENTATION `plant` op

- **データ種**: `rgbimage × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.superpixel_color_texture_features(rgb, labels, *, dark_floor: 'float' = 0.02, texture_sigma: 'float' = 1.0, min_size: 'int' = 4) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import cropweed; cropweed.superpixel_color_texture_features(rgb, labels, *, dark_floor: 'float' = 0.02, texture_sigma: 'float' = 1.0, min_size: 'int' = 4) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("superpixel_color_texture_features")`)

## 使い方

ラベル画像の領域ごとに、色(植物の色指標・色度)と肌理(勾配・向きの揃い)の特徴 10 個を出す。

``rgb`` は (H, W, 3)(``plant_color_index`` と同じ約束)、``labels`` は同じ大きさの整数画像
(0 は無視、1 以上が領域。超画素でも格子でもよい)。列は ``FEATURE_NAMES`` の順:
ExG・ExGR・CIVE の平均、色度 r・g の平均、明るさ(RGB の平均)の平均と標準偏差、
明るさの Gauss 勾配(σ = ``texture_sigma``)の大きさの平均、構造テンソルの向きの揃い
coherence = √((Jxx − Jyy)² + 4Jxy²)/(Jxx + Jyy)(領域で和をとったテンソル。1 = 一方向、0 = 等方)、
ExG の標準偏差。色の特徴は ``dark_floor`` 以上の明るさの画素だけで平均する。
画素数が ``min_size`` 未満の領域と、色度の決まる画素が 1 つも無い領域は **行を作らず**
``dropped_ids`` に理由つきで残す(平均を 0 や NaN で埋めない)。
返す: ``X``(N, 10)・``names``・``ids``(行ごとの領域番号)・``sizes``・``centroids``((N, 2) の [row, col])・
``dropped_ids``・``texture_sigma``。
空の入力・形の食い違い・負のラベル・残る領域が 0 のときは ``ValueError`` で拒否する。

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

[plant_color_index](plant_color_index.md) · [cover_ratio_grade](cover_ratio_grade.md)

---
*Provenance: cropweed.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
