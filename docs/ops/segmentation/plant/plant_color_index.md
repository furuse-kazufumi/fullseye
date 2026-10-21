---
op: plant_color_index
dim: segmentation
category: plant
in: rgbimage
out: table
examples: [poc_leaf_disease_area, poc_weed_rice_ratio]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# plant_color_index — SEGMENTATION `plant` op

- **データ種**: `rgbimage` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.plant_color_index(rgb, *, index: 'str' = 'exg', dark_floor: 'float' = 0.02) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import cropweed; cropweed.plant_color_index(rgb, *, index: 'str' = 'exg', dark_floor: 'float' = 0.02) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("plant_color_index")`)

## 使い方

可視 3 バンドの植物の色指標(ExG・ExR・ExGR・CIVE・NGRDI・VEG)を画素ごとに計算する。

``rgb`` は (H, W, 3)。uint8 は 255 で割り、float は [0, 1] でなければ拒否する。``index`` は
``exg`` / ``exr`` / ``exgr`` / ``cive`` / ``ngrdi`` / ``veg``。ExG・ExR・ExGR・CIVE・VEG は色度座標
r = R/(R+G+B)・g・b に掛け、NGRDI だけは生の (G − R)/(G + R)。
明るさ(RGB の平均)が ``dark_floor`` 未満の画素は色度が雑音で決まるので **値を作らず NaN** にし、
``valid`` を False にする(VEG は r か b が 0、NGRDI は G + R が 0 の画素も外す)。
返す: ``index``(H, W の float、NaN は未定義)・``valid``(bool)・``name``・``formula``・
``vegetation_sign``(植物で大きくなる指標は +1、CIVE と ExR は −1)・``citation``・``n_invalid``・
``threshold_zero_is_boundary``(ExGR だけ True: 0 が植物と背景の境)。
空の入力・非有限値・範囲の外・未知の指標名・全画素が未定義のときは ``ValueError`` で拒否する。

呼び出し例: ``fs.ledger.plant_color_index(img, index="exgr")["index"] > 0`` で植物の画素。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_leaf_disease_area](../../../../examples/poc_leaf_disease_area.py) — `py -3.11 examples/poc_leaf_disease_area.py`
- [poc_weed_rice_ratio](../../../../examples/poc_weed_rice_ratio.py) — `py -3.11 examples/poc_weed_rice_ratio.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md) · [fisher_lda_score](../classify/fisher_lda_score.md)

## 同カテゴリ(`plant`)

[superpixel_color_texture_features](superpixel_color_texture_features.md) · [cover_ratio_grade](cover_ratio_grade.md)

---
*Provenance: cropweed.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
