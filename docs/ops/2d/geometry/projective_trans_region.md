---
op: projective_trans_region
dim: 2d
category: geometry
in: region
out: region
halcon: projective_trans_region
examples: [gallery2d_geometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# projective_trans_region — 2D `geometry` op

- **データ種**: `region` → `region`
- **呼び出し**: `fullseye.apply(img, "projective_trans_region", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `projective_trans_region`(意味・パラメータは HALCON リファレンスが参考になる)

![projective_trans_region: input → output](../../_fig/projective_trans_region.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![projective_trans_region: knob a sweep](../../_fig/projective_trans_region.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![projective_trans_region: knob b sweep](../../_fig/projective_trans_region.b.jpg)

**段階**(前置きの op → この op。左から順):

![projective_trans_region: stages](../../_fig/projective_trans_region.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![projective_trans_region: other inputs](../../_fig/projective_trans_region.inputs.jpg)

## 使い方

``projective_trans_image`` と同じ台形歪みを領域(2 値マスク)に適用する。
``out_sort`` が ``region`` のため ``build()`` が ``_rebinarise`` で包み、
補間で生じた小数値を ``>0.5`` で二値に戻してから返す(領域の {0,1} 契約を
壊さないための後処理)。HALCON の ``projective_trans_region``（Apply a
projective transformation to a region.）に相当。

``a`` が歪みの強さ、``b`` が非対称さを振る。両方が使われる。

## 詳しい使い方ガイド

- [gallery2d_geometry ファミリ ガイド](../guides/gallery2d_geometry.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
projective_trans_region 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_geometry](../../../../examples/gallery2d_geometry.py) — `py -3.11 examples/gallery2d_geometry.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`geometry`)

[rotate_img](rotate_img.md) · [rescale_img](rescale_img.md) · [affine_warp](affine_warp.md) · [sk_swirl](sk_swirl.md) · [mirror_image](mirror_image.md) · [transpose_region](transpose_region.md) · [rotate_image](rotate_image.md) · [zoom_image_factor](zoom_image_factor.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
