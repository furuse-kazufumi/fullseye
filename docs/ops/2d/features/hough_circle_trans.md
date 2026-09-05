---
op: hough_circle_trans
dim: 2d
category: features
in: image
out: image
halcon: hough_circle_trans
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# hough_circle_trans — 2D `features` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "hough_circle_trans", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `hough_circle_trans`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

円検出のための Hough 変換。エッジマスクに対して半径 4〜19(3 刻み)の
円テンプレート群で ``skimage.transform.hough_circle`` を計算し、全半径での
最大応答を [0,1] に正規化して返す。HALCON の ``hough_circle_trans``
（Return the Hough-Transform for circles with a given radius.）に相当
(HALCON は半径を明示指定するが、ここでは固定レンジを総当たりする近似)。

``a`` がエッジ抽出の閾値を振る。``b`` は未使用 ―― 探索する半径レンジは
コード側に固定されており、``b`` で半径を選ぶことはできない。

## 詳しい使い方ガイド

- [gallery2d_features ファミリ ガイド](../guides/gallery2d_features.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_features](../../../../examples/gallery2d_features.py) — `py -3.11 examples/gallery2d_features.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`features`)

[blob_count](blob_count.md) · [area_frac](area_frac.md) · [count_contours](count_contours.md) · [total_length](total_length.md) · [vol_count](vol_count.md) · [sk_euler](sk_euler.md) · [sk_entropy_feat](sk_entropy_feat.md) · [sk_blur_effect](sk_blur_effect.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
