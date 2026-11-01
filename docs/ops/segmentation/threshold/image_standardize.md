---
op: image_standardize
dim: segmentation
category: threshold
in: image2d
out: image2d
examples: [poc_threshold_transfer_after_normalization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# image_standardize — SEGMENTATION `threshold` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.image_standardize(image, method: 'str' = 'zscore', p_lo: 'float' = 1.0, p_hi: 'float' = 99.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import normalized_threshold; normalized_threshold.image_standardize(image, method: 'str' = 'zscore', p_lo: 'float' = 1.0, p_hi: 'float' = 99.0) -> 'np.ndarray'`、台帳から引くなら `opssegmentation.get("image_standardize")`)

## 使い方

画像全体を z-score・頑健 MAD・百分位のいずれかで零中心に標準化する。

``zscore`` は ``(x - mean) / population_std``。``robust`` は
``(x - median) / (1.4826 * MAD)`` で、正規分布の標準偏差と尺度を合わせる。
``percentile`` は *p_lo* / *p_hi* 分位点の中点を 0、両者を -1 / +1 に写す。
出力は常に ``float64`` であり、入力のクリップはしない。

Parameters
----------
image : array-like
    有限値だけからなる空でない 2-D 画像。値域は限定しない。
method : {'zscore', 'robust', 'percentile'}
    ``robust`` は外れ値が平均と標準偏差を動かす場合、``percentile`` は装置ごとの
    利得とオフセットを指定分位点で揃えたい場合に使う。
p_lo, p_hi : float
    ``percentile`` の百分位。``0 <= p_lo < p_hi <= 100``。ほかの方式では未使用。

Returns
-------
numpy.ndarray
    零中心の ``float64`` 画像。z-score は平均 0・母分散 1、robust は中央値 0・
    補正 MAD 1、percentile は指定分位点の中点 0。

Raises
------
ValueError
    標準偏差、``1.4826 * MAD``、または百分位幅が 0 の画像。定数画像を黙って
    0 除算せず、正規化後の単位が定義できないことを理由つきで拒否する。

**空入力と尺度 0 の入力は、標準化後の単位を定義できないため拒否する。**

References
----------
F. R. Hampel, "The Influence Curve and Its Role in Robust Estimation,"
*Journal of the American Statistical Association*, 69(346), 1974.
P. J. Rousseeuw and C. Croux, "Alternatives to the Median Absolute
Deviation," *Journal of the American Statistical Association*, 88(424), 1993.

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

## 型が繋がる次の op(`image2d` を入力に取れる)

[check_difference](../compare/check_difference.md) · [class_2dim_sup](../classify/class_2dim_sup.md) · [class_2dim_unsup](../classify/class_2dim_unsup.md) · [classify_image_class_lut](../classify/classify_image_class_lut.md) · [expand_gray](../grow/expand_gray.md) · [watersheds_marker](../watershed/watersheds_marker.md) · [snake_evolve](../contour/snake_evolve.md) · [gvf_field](../contour/gvf_field.md)

## 同カテゴリ(`threshold`)

[threshold_triangle](threshold_triangle.md) · [threshold_isodata](threshold_isodata.md) · [threshold_kittler](threshold_kittler.md) · [threshold_kapur](threshold_kapur.md) · [ptile_threshold](ptile_threshold.md) · [sigma_threshold](sigma_threshold.md)

---
*Provenance: normalized_threshold.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
