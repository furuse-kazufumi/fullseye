---
op: otsu
dim: 2d
category: segmentation
in: image
out: region
halcon: binary_threshold
examples: [ct_inspection, gallery2d_segmentation, quickstart, segment_and_classify]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# otsu — 2D `segmentation` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "otsu", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `binary_threshold`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

大津の判別分析法（Otsu's method）による自動しきい値処理。HALCON の ``binary_threshold``（Segment an image using binary thresholding.）に相当。

``a``, ``b`` は未使用（しきい値は入力から自動で決まる）。``[0,1]`` を 256 ビンのヒストグラムに分け、クラス間分散 ``ω(1-ω)`` を最大化するしきい値を全探索して選び、それより大きい画素を前景とする。前景・背景 2 クラスの分離を仮定するため、ヒストグラムが単峰（1 山）の画像では意図しない位置で切れることがある。

## 詳しい使い方ガイド

- [gallery2d_segmentation ファミリ ガイド](../guides/gallery2d_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_inspection](../../../../examples/ct_inspection.py) — `py -3.11 examples/ct_inspection.py`
- [gallery2d_segmentation](../../../../examples/gallery2d_segmentation.py) — `py -3.11 examples/gallery2d_segmentation.py`
- [quickstart](../../../../examples/quickstart.py) — `py -3.11 examples/quickstart.py`
- [segment_and_classify](../../../../examples/segment_and_classify.py) — `py -3.11 examples/segment_and_classify.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`segmentation`)

[threshold](threshold.md) · [canny](canny.md) · [adaptive_gauss_thresh](adaptive_gauss_thresh.md) · [sk_otsu](sk_otsu.md) · [sk_li](sk_li.md) · [sk_yen](sk_yen.md) · [sk_sauvola](sk_sauvola.md) · [sk_niblack](sk_niblack.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
