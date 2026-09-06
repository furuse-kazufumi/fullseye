---
op: aug_barrel
dim: 2d
category: augmentation
in: image
out: image
examples: [gallery2d_color_artistic, sim2real_and_alife]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# aug_barrel — 2D `augmentation` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "aug_barrel", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![aug_barrel: input → output](../../_fig/aug_barrel.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![aug_barrel: knob a sweep](../../_fig/aug_barrel.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![aug_barrel: knob b sweep](../../_fig/aug_barrel.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![aug_barrel: other inputs](../../_fig/aug_barrel.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

Radial lens distortion using the standard polynomial model
``r_src = r*(1 + k*r^2)`` on normalised radius ``r`` (1 = image corner):
BARREL (straight lines bow outwards) when ``b < 0.5``, PINCUSHION when
``b >= 0.5``, with ``k = 0.6*a`` (a=0 -> undistorted). The destination grid is
inverse-mapped and resampled bilinearly with ``ndimage.map_coordinates``
(``mode="reflect"``), so no pixel is left undefined. Output keeps HxW.

## 詳しい使い方ガイド

- [gallery2d_color_artistic ファミリ ガイド](../guides/gallery2d_color_artistic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
aug_barrel 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_color_artistic](../../../../examples/gallery2d_color_artistic.py) — `py -3.11 examples/gallery2d_color_artistic.py`
- [sim2real_and_alife](../../../../examples/sim2real_and_alife.py) — `py -3.11 examples/sim2real_and_alife.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`augmentation`)

[aug_shot_noise](aug_shot_noise.md) · [aug_read_noise](aug_read_noise.md) · [aug_fixed_pattern](aug_fixed_pattern.md) · [aug_motion_blur](aug_motion_blur.md) · [aug_vignette](aug_vignette.md) · [aug_chromatic](aug_chromatic.md) · [aug_rolling_shutter](aug_rolling_shutter.md) · [aug_jpeg_blocks](aug_jpeg_blocks.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
