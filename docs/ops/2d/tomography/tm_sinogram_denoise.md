---
op: tm_sinogram_denoise
dim: 2d
category: tomography
in: image
out: image
examples: [gallery2d_physics_alife_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tm_sinogram_denoise — 2D `tomography` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "tm_sinogram_denoise", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Smooth the input sinogram along the ANGLE direction (rows). Neighbouring
projection angles view almost the same object, so angle-direction smoothing
is a genuine consistency prior that suppresses per-angle detector noise while
preserving the sinusoidal traces. ``a`` sets the angle-axis Gaussian sigma
(``a*4``), ``b`` adds a gentle detector-axis sigma (``b*1.5``). Output stays
a same-shape sinogram in [0,1].

## 詳しい使い方ガイド

- [gallery2d_physics_alife_3d ファミリ ガイド](../guides/gallery2d_physics_alife_3d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_physics_alife_3d](../../../../examples/gallery2d_physics_alife_3d.py) — `py -3.11 examples/gallery2d_physics_alife_3d.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`tomography`)

[tm_radon_forward](tm_radon_forward.md) · [tm_fbp_reconstruct](tm_fbp_reconstruct.md) · [tm_sart_reconstruct](tm_sart_reconstruct.md) · [tm_backproject_unfiltered](tm_backproject_unfiltered.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
