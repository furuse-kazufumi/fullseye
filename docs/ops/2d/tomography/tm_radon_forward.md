---
op: tm_radon_forward
dim: 2d
category: tomography
in: image
out: image
examples: [gallery2d_physics_alife_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tm_radon_forward — 2D `tomography` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "tm_radon_forward", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Forward Radon projection: treat ``v`` as a slice image and integrate it
along parallel rays to build a sinogram (rows = angles, cols = detector),
refit to the original HxW. ``a`` sets how many angles are acquired
(``n = round(H*a)`` clamped to 8..360 -- the sparse-view knob), ``b`` sets the
angular span (``span = 180*min(1, 0.5+b)`` deg: b < 0.5 is limited-angle CT,
b >= 0.5 -- including the default b = 0.5 -- is the full [0,180) span that
``tm_fbp_reconstruct`` / ``tm_sart_reconstruct`` / ``tm_backproject_unfiltered``
assume, so the natural chain forward -> inverse round-trips at default knobs).
Uses ``skimage.transform.radon`` when available, else the NumPy
rotate-and-sum Radon transform.

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

[tm_fbp_reconstruct](tm_fbp_reconstruct.md) · [tm_sart_reconstruct](tm_sart_reconstruct.md) · [tm_backproject_unfiltered](tm_backproject_unfiltered.md) · [tm_sinogram_denoise](tm_sinogram_denoise.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
