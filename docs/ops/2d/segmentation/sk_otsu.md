---
op: sk_otsu
dim: 2d
category: segmentation
in: image
out: region
halcon: binary_threshold
examples: [gallery2d_segmentation, poc_cell_counting, poc_fresco_craquelure, poc_leaf_disease_area, poc_nuclei_ploidy, poc_vegetation_cover]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# sk_otsu — 2D `segmentation` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "sk_otsu", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `binary_threshold`(意味・パラメータは HALCON リファレンスが参考になる)

![sk_otsu: input → output](../../_fig/sk_otsu.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![sk_otsu: other inputs](../../_fig/sk_otsu.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

大津の判別分析法(Otsu's method)による大域しきい値二値化。クラス間分散を最大化するしきい値を自動で選び、画像全体を前景/背景に二分する。

HALCON の `binary_threshold`(Segment an image using binary thresholding.)に相当。実装は ``v > filters.threshold_otsu(v)`` —— a, b は未使用(しきい値は完全自動)。双峰性(2 山)のヒストグラムを持つ画像で最もうまく働き、コントラストが低い/単峰の画像では境界がずれやすい。

## 詳しい使い方ガイド

- [gallery2d_segmentation ファミリ ガイド](../guides/gallery2d_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
sk_otsu 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_segmentation](../../../../examples/gallery2d_segmentation.py) — `py -3.11 examples/gallery2d_segmentation.py`
- [poc_cell_counting](../../../../examples/poc_cell_counting.py) — `py -3.11 examples/poc_cell_counting.py`
- [poc_fresco_craquelure](../../../../examples/poc_fresco_craquelure.py) — `py -3.11 examples/poc_fresco_craquelure.py`
- [poc_leaf_disease_area](../../../../examples/poc_leaf_disease_area.py) — `py -3.11 examples/poc_leaf_disease_area.py`
- [poc_nuclei_ploidy](../../../../examples/poc_nuclei_ploidy.py) — `py -3.11 examples/poc_nuclei_ploidy.py`
- [poc_vegetation_cover](../../../../examples/poc_vegetation_cover.py) — `py -3.11 examples/poc_vegetation_cover.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`segmentation`)

[threshold](threshold.md) · [otsu](otsu.md) · [canny](canny.md) · [adaptive_gauss_thresh](adaptive_gauss_thresh.md) · [sk_li](sk_li.md) · [sk_yen](sk_yen.md) · [sk_sauvola](sk_sauvola.md) · [sk_niblack](sk_niblack.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
