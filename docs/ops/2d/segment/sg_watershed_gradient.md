---
op: sg_watershed_gradient
dim: 2d
category: segment
in: image
out: region
examples: [gallery2d_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# sg_watershed_gradient — 2D `segment` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "sg_watershed_gradient", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

勾配画像の h-minima マーカーからのウォーターシェッド分割の境界を返す（``skimage``、HALCON に対応オペレータなし）。

Sobel 勾配の大きさを正規化し、深さ ``h = 0.02 + a*0.3`` の h-minima 変換で生き残った領域極小をマーカーとして（``a`` が大きいほどマーカーが少なく・粗い分割になる）、その勾配画像に対するウォーターシェッドを計算する。``b`` は未使用。戻り値は集水域（catchment basin/物体）を分けるダムライン（境界）を表す region。

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

## 同カテゴリ(`segment`)

[sg_slic_superpixels](sg_slic_superpixels.md) · [sg_felzenszwalb](sg_felzenszwalb.md) · [sg_gmm_segment](sg_gmm_segment.md) · [sg_kmeans_intensity](sg_kmeans_intensity.md) · [sg_region_growing_seeded](sg_region_growing_seeded.md) · [sg_normalized_cut_2](sg_normalized_cut_2.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
