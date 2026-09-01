---
op: ellipse_phantom
dim: tomography
category: forward
in: 
out: image2d
examples: [tomography_reconstruct]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# ellipse_phantom — TOMOGRAPHY `forward` op

- **データ種**: `` → `image2d`
- **呼び出し**: `import tomography; tomography.ellipse_phantom(size=256, ellipses=None, supersample=4)` (または `opstomography.get("ellipse_phantom")`)

## 使い方

Rasterise a sum of uniform ellipses onto a *size* x *size* slice.

The default is :data:`SHEPP_LOGAN`. The normalised square ``[-1, 1]^2`` maps
onto the grid, so ``x = (col - (size-1)/2) / (size/2)``; the same mapping is
used by :func:`ellipse_sinogram`, which is what makes the two comparable
without a fudge factor.

*supersample* is the anti-aliasing factor: each pixel is the mean of
``supersample^2`` sub-samples, so an edge pixel carries its true area
fraction. This is not cosmetic — a hard 0/1 rasterisation projects to a
sinogram that disagrees with the closed form by **0.276 % interior RMS** of
the peak, against **0.073 %** anti-aliased (measured), and the
difference is entirely the partial-volume edge.

:param size: side of the square grid, ``2 .. 16384``.
:param ellipses: ``(N, 6)`` rows ``(x0, y0, a, b, phi_deg, rho)`` in
    normalised coordinates; ``None`` -> :data:`SHEPP_LOGAN`.
:param supersample: anti-alias factor per axis, ``1 .. 16``.
:returns: ``(size, size)`` float64 image; the Shepp-Logan default spans
    ``[0.0, 1.0]``.
:raises ValueError: on a non-int size, a degenerate ellipse, or a grid over
    :data:`MAX_IMAGE_ELEMENTS`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [tomography_reconstruct](../../../../examples/tomography_reconstruct.py) — `py -3.11 examples/tomography_reconstruct.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[radon_transform](radon_transform.md)

## 同カテゴリ(`forward`)

[ellipse_sinogram](ellipse_sinogram.md) · [radon_transform](radon_transform.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
