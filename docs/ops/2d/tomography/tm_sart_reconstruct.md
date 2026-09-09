---
op: tm_sart_reconstruct
dim: 2d
category: tomography
in: image
out: image
examples: [gallery2d_physics_alife_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# tm_sart_reconstruct — 2D `tomography` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "tm_sart_reconstruct", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tm_sart_reconstruct: input → output](../../_fig/tm_sart_reconstruct.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tm_sart_reconstruct: knob a sweep](../../_fig/tm_sart_reconstruct.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tm_sart_reconstruct: knob b sweep](../../_fig/tm_sart_reconstruct.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tm_sart_reconstruct: other inputs](../../_fig/tm_sart_reconstruct.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

Algebraic reconstruction: run a few SART/SIRT sweeps on the input
sinogram (rows = angles). ``a`` sets the iteration count
(``round(1+a*4)`` -> 1..5), ``b`` sets the relaxation factor
(``0.05 + b*0.35``). Uses ``skimage.transform.iradon_sart`` when available,
else a self-contained NumPy SIRT (project -> residual -> weighted
back-projection) loop. Output refit to HxW.

## 詳しい使い方ガイド

- [gallery2d_physics_alife_3d ファミリ ガイド](../guides/gallery2d_physics_alife_3d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
tm_sart_reconstruct 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_physics_alife_3d](../../../../examples/gallery2d_physics_alife_3d.py) — `py -3.11 examples/gallery2d_physics_alife_3d.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`tomography`)

[tm_radon_forward](tm_radon_forward.md) · [tm_fbp_reconstruct](tm_fbp_reconstruct.md) · [tm_backproject_unfiltered](tm_backproject_unfiltered.md) · [tm_sinogram_denoise](tm_sinogram_denoise.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
