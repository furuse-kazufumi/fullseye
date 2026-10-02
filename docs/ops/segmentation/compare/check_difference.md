---
op: check_difference
dim: segmentation
category: compare
in: image2d × image2d
out: mask
examples: [halcon_segmentation_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# check_difference — SEGMENTATION `compare` op

- **データ種**: `image2d × image2d` → `mask`
- **呼び出し**: `import fullseye as fs; fs.ledger.check_difference(image, ref_image, tol=0.1)` (実装を直接呼ぶなら `import segmentation; segmentation.check_difference(image, ref_image, tol=0.1)`、台帳から引くなら `opssegmentation.get("check_difference")`)

## 使い方

基準画像との差が tol を超える画素を領域として返す(check_difference)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [halcon_segmentation_tour](../../../../examples/halcon_segmentation_tour.py) — `py -3.11 examples/halcon_segmentation_tour.py`

## 型が繋がる次の op(`mask` を入力に取れる)

[class_2dim_sup](../classify/class_2dim_sup.md) · [expand_gray](../grow/expand_gray.md) · [chan_vese_energy](../contour/chan_vese_energy.md) · [chan_vese_evolve](../contour/chan_vese_evolve.md) · [morph_chan_vese](../contour/morph_chan_vese.md) · [morph_geodesic_ac](../contour/morph_geodesic_ac.md) · [level_set_reinit](../contour/level_set_reinit.md) · [drle_evolve](../contour/drle_evolve.md)

## 同カテゴリ(`compare`)

—

---
*Provenance: segmentation.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
