---
op: projective_trans_image
dim: 2d
category: geometry
in: image
out: image
halcon: projective_trans_image
examples: [gallery2d_geometry, poc_water_level]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# projective_trans_image — 2D `geometry` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "projective_trans_image", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `projective_trans_image`(意味・パラメータは HALCON リファレンスが参考になる)

![projective_trans_image: input → output](../../_fig/projective_trans_image.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![projective_trans_image: knob a sweep](../../_fig/projective_trans_image.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![projective_trans_image: knob b sweep](../../_fig/projective_trans_image.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![projective_trans_image: other inputs](../../_fig/projective_trans_image.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

透視(射影)変換(``cv2.warpPerspective``)。4 隅のうち上 2 隅を
``d=0.06+0.12*a`` の比率で内側に寄せることで台形(パースがかかった)歪みを
作る。枠外は反射で埋める。HALCON の ``projective_trans_image``（Apply a
projective transformation to an image.）に相当(HALCON は任意のホモグラフィ
行列を渡せるが、ここでは台形歪み 1 パターンに限定した近似)。

``a`` が歪みの強さを、``b`` が左右の非対称さ(どちら側をより歪ませるか)を
振る。両方が使われる。

## 詳しい使い方ガイド

- [gallery2d_geometry ファミリ ガイド](../guides/gallery2d_geometry.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
projective_trans_image 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_geometry](../../../../examples/gallery2d_geometry.py) — `py -3.11 examples/gallery2d_geometry.py`
- [poc_water_level](../../../../examples/poc_water_level.py) — `py -3.11 examples/poc_water_level.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`geometry`)

[rotate_img](rotate_img.md) · [rescale_img](rescale_img.md) · [affine_warp](affine_warp.md) · [sk_swirl](sk_swirl.md) · [mirror_image](mirror_image.md) · [transpose_region](transpose_region.md) · [rotate_image](rotate_image.md) · [zoom_image_factor](zoom_image_factor.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
