---
op: edge_stop_g
dim: segmentation
category: contour
in: image2d
out: table
examples: [poc_active_contours]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# edge_stop_g — SEGMENTATION `contour` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.edge_stop_g(image, *, sigma: 'float' = 1.0, k: 'float' = 1.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segcontour; segcontour.edge_stop_g(image, *, sigma: 'float' = 1.0, k: 'float' = 1.0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("edge_stop_g")`)

## 使い方

エッジ停止関数 g = 1 / (1 + |∇(G_σ * I)|² / k²)(Caselles–Kimmel–Sapiro 1997 の p = 2 の形)。

``sigma`` = ガウスの標準偏差(0 なら平滑化なしの中心差分)、``k`` = 勾配の尺度(k = 1 で g = 1/(1 + |∇G_σ*I|²))。
画像の値域に依存する: Li ら 2010 の配布例は 0〜255 の画像で k = 1 なので、[0, 1] の画像なら k = 1/255 が同じ挙動。
返り値: ``g``(0 < g ≤ 1、平坦で 1)、``grad_mag``、``g_min`` / ``g_max``、``sigma``、``k``。
門: g ∈ (0, 1] —— 分母 ≥ 1、平坦な画像で g ≡ 1(勾配 0)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [active_contours_and_level_sets](../guides/active_contours_and_level_sets.md) — 変分・動的輪郭とレベルセット — どの輪郭がどこで止まり、何を保証するか

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_active_contours](../../../../examples/poc_active_contours.py) — `py -3.11 examples/poc_active_contours.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`contour`)

[snake_evolve](snake_evolve.md) · [gvf_field](gvf_field.md) · [chan_vese_energy](chan_vese_energy.md) · [chan_vese_evolve](chan_vese_evolve.md) · [morph_chan_vese](morph_chan_vese.md) · [morph_geodesic_ac](morph_geodesic_ac.md) · [level_set_reinit](level_set_reinit.md) · [drle_evolve](drle_evolve.md)

---
*Provenance: segcontour.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
