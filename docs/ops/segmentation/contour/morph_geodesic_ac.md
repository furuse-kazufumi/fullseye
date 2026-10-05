---
op: morph_geodesic_ac
dim: segmentation
category: contour
in: image2d × mask
out: table
examples: [poc_active_contours]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# morph_geodesic_ac — SEGMENTATION `contour` op

- **データ種**: `image2d × mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.morph_geodesic_ac(gimage, init, *, n_iter: 'int' = 100, smoothing: 'int' = 1, threshold='auto', balloon: 'float' = 0.0, phase: 'int' = 0, record_every: 'int' = 0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segcontour; segcontour.morph_geodesic_ac(gimage, init, *, n_iter: 'int' = 100, smoothing: 'int' = 1, threshold='auto', balloon: 'float' = 0.0, phase: 'int' = 0, record_every: 'int' = 0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("morph_geodesic_ac")`)

## 使い方

形態学的な測地的 active contour(Márquez-Neila ら 2014 の MorphGAC)。``gimage`` = 縁で小さい画像(``edge_stop_g`` の g)。

1 反復 = 風船段(balloon > 0 で 3×3 の膨張、< 0 で収縮を g > threshold/|balloon| の画素にだけ)+ 引力段
(∇g · ∇u > 0 の画素を内側、< 0 を外側 = g の谷へ輪郭を引く)+ 平滑段(曲率の作用素を ``smoothing`` 回、交互)。
``threshold="auto"`` は g の 40 % 点(skimage と同じ)。**落とし穴(実測)**: 背景が厳密に平坦だと g ≡ 1 の画素が 40 % を
超え、閾値 = 1 で「g > 1/|balloon|」の画素が無くなり風船が一度も働かない(輪郭は初期のまま止まる)。ぼかしの裾で g が
1 − 10⁻¹³ になる画像では偶然働く。平坦な合成画像では閾値を数で与えること。``phase`` は ``morph_chan_vese`` と同じ。
返り値: ``mask``、``threshold``、``history``、``n_iter``、``n_changed``(反復ごと)。

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

[snake_evolve](snake_evolve.md) · [gvf_field](gvf_field.md) · [chan_vese_energy](chan_vese_energy.md) · [chan_vese_evolve](chan_vese_evolve.md) · [morph_chan_vese](morph_chan_vese.md) · [edge_stop_g](edge_stop_g.md) · [level_set_reinit](level_set_reinit.md) · [drle_evolve](drle_evolve.md)

---
*Provenance: segcontour.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
