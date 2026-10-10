---
op: expand_gray
dim: segmentation
category: grow
in: image2d × mask
out: mask
examples: [halcon_segmentation_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# expand_gray — SEGMENTATION `grow` op

- **データ種**: `image2d × mask` → `mask`
- **呼び出し**: `import fullseye as fs; fs.ledger.expand_gray(image, seed_region, tol=0.05)` (実装を直接呼ぶなら `import segmentation; segmentation.expand_gray(image, seed_region, tol=0.05)`、台帳から引くなら `opssegmentation.get("expand_gray")`)

## 使い方

seed から gray 類似(|Δ|<tol)で領域を膨張(expand_gray)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [halcon_segmentation_tour](../../../../examples/halcon_segmentation_tour.py) — `py -3.11 examples/halcon_segmentation_tour.py`

## 型が繋がる次の op(`mask` を入力に取れる)

[class_2dim_sup](../classify/class_2dim_sup.md) · [chan_vese_energy](../contour/chan_vese_energy.md) · [chan_vese_evolve](../contour/chan_vese_evolve.md) · [morph_chan_vese](../contour/morph_chan_vese.md) · [morph_geodesic_ac](../contour/morph_geodesic_ac.md) · [level_set_reinit](../contour/level_set_reinit.md) · [drle_evolve](../contour/drle_evolve.md) · [curvature_flow](../contour/curvature_flow.md)

## 同カテゴリ(`grow`)

[regiongrowing_n](regiongrowing_n.md)

---
*Provenance: segmentation.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
