---
op: adaptive_gauss_thresh
dim: 2d
category: segmentation
in: image
out: region
halcon: local_threshold
examples: [gallery2d_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# adaptive_gauss_thresh — 2D `segmentation` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "adaptive_gauss_thresh", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `local_threshold`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

ガウシアン平滑化した局所平均を基準にした適応的しきい値処理。HALCON の ``local_threshold``（Segment an image using local thresholding.）に相当。

``a`` が基準を作るガウシアンの σ を ``1.0〜4.0`` に、``b`` がオフセットを ``-0.15〜+0.15``（``(b-0.5)*0.3``）に振る。``v > gaussian_filter(v, σ) + offset`` を満たす画素を前景にする。照明ムラがある画像で大域しきい値（``_threshold``/``_otsu``）より安定する。近い op に ``_dyn_threshold`` があるが、そちらは箱型平均（``uniform_filter``）を基準にし、オフセット幅も異なる（``±0.2``）——同じ「適応的しきい値」でも基準の平滑化方式とパラメータ範囲が違う別実装。

## 詳しい使い方ガイド

- [gallery2d_segmentation ファミリ ガイド](../guides/gallery2d_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_segmentation](../../../../examples/gallery2d_segmentation.py) — `py -3.11 examples/gallery2d_segmentation.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`segmentation`)

[threshold](threshold.md) · [otsu](otsu.md) · [canny](canny.md) · [sk_otsu](sk_otsu.md) · [sk_li](sk_li.md) · [sk_yen](sk_yen.md) · [sk_sauvola](sk_sauvola.md) · [sk_niblack](sk_niblack.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
