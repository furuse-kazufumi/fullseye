---
op: xcv_watershed_markers
dim: 2d
category: segmentation
in: image
out: region
halcon: watersheds
examples: [gallery2d_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# xcv_watershed_markers — 2D `segmentation` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "xcv_watershed_markers", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `watersheds`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

マーカー制御ウォーターシェッドによる境界線抽出。

HALCON の ``watersheds``(ウォーターシェッドと分水嶺盆地を抽出する)に
相当するが、ここでは盆地のラベルではなく **分水嶺の境界線** だけを
region として返す(近似)。

手順は古典的な OpenCV レシピ: Otsu 二値化 -> 膨張で「確実な背景」推定
-> 距離変換のしきい値で「確実な前景」推定 -> 両者の差分を「不明」領域
とし、確実な前景の連結成分をマーカーに ``cv2.watershed`` を実行。

``a`` が確実な前景を決めるしきい値を距離変換最大値の 30%〜70% の範囲
で振る(大きいほど前景マーカーが小さく・保守的になり、過分割/過統合
の傾向が変わる)。``b`` は未使用。

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

[threshold](threshold.md) · [otsu](otsu.md) · [canny](canny.md) · [adaptive_gauss_thresh](adaptive_gauss_thresh.md) · [sk_otsu](sk_otsu.md) · [sk_li](sk_li.md) · [sk_yen](sk_yen.md) · [sk_sauvola](sk_sauvola.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
