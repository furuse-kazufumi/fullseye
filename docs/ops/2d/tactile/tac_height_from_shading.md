---
op: tac_height_from_shading
dim: 2d
category: tactile
in: image
out: image
examples: [sim2real_and_alife]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tac_height_from_shading — 2D `tactile` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "tac_height_from_shading", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tac_height_from_shading: input → output](../../_fig/tac_height_from_shading.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*出力は viridis 風の疑似カラー(暗い紫 = 小、黄 = 大)。距離・位相・向き・深度のような「量の場」を読むため。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tac_height_from_shading: knob a sweep](../../_fig/tac_height_from_shading.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tac_height_from_shading: knob b sweep](../../_fig/tac_height_from_shading.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tac_height_from_shading: other inputs](../../_fig/tac_height_from_shading.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

Height/relief map by Poisson integration of the shading gradients -- the
integration stage of GelSight depth reconstruction (and of photometric
stereo): the image gradients are read as surface slopes ``p = gain*gx``,
``q = gain*gy`` and the Poisson equation ``lap(h) = div(p,q)`` is solved
spectrally, ``h_hat = div_hat / lap_hat`` with the discrete Laplacian symbol
``2cos(2*pi*u/W)+2cos(2*pi*v/H)-4`` and the (undetermined) DC mode pinned to
zero. ``a`` = gradient gain (0.25..4.25x), ``b`` = pre-smoothing sigma of the
gradient field (0..3). Output is min-max normalised to [0,1] and refit to
HxW; a constant frame integrates to a flat (all-zero) relief.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
tac_height_from_shading 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sim2real_and_alife](../../../../examples/sim2real_and_alife.py) — `py -3.11 examples/sim2real_and_alife.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`tactile`)

[tac_contact_mask](tac_contact_mask.md) · [tac_surface_normal](tac_surface_normal.md) · [tac_pressure_proxy](tac_pressure_proxy.md) · [tac_shear_field](tac_shear_field.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
