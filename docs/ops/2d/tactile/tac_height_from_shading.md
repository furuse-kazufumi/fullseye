---
op: tac_height_from_shading
dim: 2d
category: tactile
in: image
out: image
examples: [sim2real_and_alife]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tac_height_from_shading — 2D `tactile` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "tac_height_from_shading", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

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

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sim2real_and_alife](../../../../examples/sim2real_and_alife.py) — `py -3.11 examples/sim2real_and_alife.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`tactile`)

[tac_contact_mask](tac_contact_mask.md) · [tac_surface_normal](tac_surface_normal.md) · [tac_pressure_proxy](tac_pressure_proxy.md) · [tac_shear_field](tac_shear_field.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
