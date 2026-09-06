---
op: aug_cutout
dim: 2d
category: augmentation
in: image
out: image
examples: [gallery2d_color_artistic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# aug_cutout — 2D `augmentation` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "aug_cutout", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![aug_cutout: input → output](../../_fig/aug_cutout.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![aug_cutout: knob a sweep](../../_fig/aug_cutout.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![aug_cutout: knob b sweep](../../_fig/aug_cutout.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![aug_cutout: other inputs](../../_fig/aug_cutout.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

Cutout / random-erasing occlusion (DeVries & Taylor 2017; Zhong et al.
2020): a square patch of side ``max(1, a*min(H,W))`` is erased from the
image, forcing a pipeline to survive partial occlusion instead of relying on
one salient blob. ``b`` selects the (deterministic, seeded-from-b) patch
position AND the fill value: b <= 0.5 -> black (0.0), b > 0.5 -> mid-gray
(0.5). The patch is always fully inside the frame.

## 詳しい使い方ガイド

- [gallery2d_color_artistic ファミリ ガイド](../guides/gallery2d_color_artistic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
aug_cutout 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_color_artistic](../../../../examples/gallery2d_color_artistic.py) — `py -3.11 examples/gallery2d_color_artistic.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`augmentation`)

[aug_shot_noise](aug_shot_noise.md) · [aug_read_noise](aug_read_noise.md) · [aug_fixed_pattern](aug_fixed_pattern.md) · [aug_motion_blur](aug_motion_blur.md) · [aug_vignette](aug_vignette.md) · [aug_chromatic](aug_chromatic.md) · [aug_rolling_shutter](aug_rolling_shutter.md) · [aug_jpeg_blocks](aug_jpeg_blocks.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
