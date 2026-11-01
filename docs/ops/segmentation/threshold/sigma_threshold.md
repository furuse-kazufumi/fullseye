---
op: sigma_threshold
dim: segmentation
category: threshold
in: image2d
out: mask
examples: [poc_threshold_transfer_after_normalization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# sigma_threshold — SEGMENTATION `threshold` op

- **データ種**: `image2d` → `mask`
- **呼び出し**: `import fullseye as fs; fs.ledger.sigma_threshold(image, k: 'float' = 3.0, polarity: 'str' = 'bright', standardization: 'str' = 'none') -> 'np.ndarray'` (実装を直接呼ぶなら `import normalized_threshold; normalized_threshold.sigma_threshold(image, k: 'float' = 3.0, polarity: 'str' = 'bright', standardization: 'str' = 'none') -> 'np.ndarray'`、台帳から引くなら `opssegmentation.get("sigma_threshold")`)

## 使い方

標準化画像を *k* σで二値化し、必要なら先に頑健標準化する。

``bright`` は ``x > k``、``dark`` は ``x < -k``、``both`` は
``abs(x) > k``。*k* は生の輝度ではなく標準偏差単位なので、利得・オフセットが
異なる画像へ同じ値を移せる。生画像から直接使う場合は
``standardization='robust'`` を選ぶと、中央値と ``1.4826 * MAD`` で先に標準化する。

Parameters
----------
image : array-like
    有限値だけからなる空でない 2-D 画像。``standardization='none'`` では既に零中心・
    σ単位であることを呼び出し側が保証する。
k : float
    正の有限値。検査で試す典型的な起点は 2〜5 σだが、用途に応じて範囲外も許す。
polarity : {'bright', 'dark', 'both'}
    明欠陥、暗欠陥、または両側の外れを選ぶ。
standardization : {'none', 'robust'}
    ``robust`` は :func:`image_standardize` の MAD 方式を内部で適用する。

Returns
-------
numpy.ndarray
    条件を満たす画素が ``True`` の 2-D マスク。

**空入力は σ単位を検査できないため拒否し、空マスクへ黙って落とさない。**

Notes
-----
標準正規雑音の片側誤検出率は ``0.5 * erfc(k / sqrt(2))``、両側は
``erfc(k / sqrt(2))``。これは独立画素を仮定した期待値である。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [graph_hierarchy_and_thresholds](../guides/graph_hierarchy_and_thresholds.md) — グラフ・階層・閾値の定理でつくる分割 — 何が厳密で、どこで割れ方が倒れるか

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_threshold_transfer_after_normalization](../../../../examples/poc_threshold_transfer_after_normalization.py) — `py -3.11 examples/poc_threshold_transfer_after_normalization.py`

## 型が繋がる次の op(`mask` を入力に取れる)

[class_2dim_sup](../classify/class_2dim_sup.md) · [expand_gray](../grow/expand_gray.md) · [chan_vese_energy](../contour/chan_vese_energy.md) · [chan_vese_evolve](../contour/chan_vese_evolve.md) · [morph_chan_vese](../contour/morph_chan_vese.md) · [morph_geodesic_ac](../contour/morph_geodesic_ac.md) · [level_set_reinit](../contour/level_set_reinit.md) · [drle_evolve](../contour/drle_evolve.md)

## 同カテゴリ(`threshold`)

[threshold_triangle](threshold_triangle.md) · [threshold_isodata](threshold_isodata.md) · [threshold_kittler](threshold_kittler.md) · [threshold_kapur](threshold_kapur.md) · [ptile_threshold](ptile_threshold.md) · [image_standardize](image_standardize.md)

---
*Provenance: normalized_threshold.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
