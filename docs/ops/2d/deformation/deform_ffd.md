---
op: deform_ffd
dim: 2d
category: deformation
in: image
out: image
examples: [gallery2d_geometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# deform_ffd — 2D `deformation` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "deform_ffd", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Cubic B-spline free-form deformation (Rueckert et al., IEEE TMI 1999).

A coarse control lattice of ``n x n`` spans (``n = 2 + int(6b)``, one padding
ring on each side) carries a deterministic smooth displacement pattern
``phi[i,j] = amp * [sin(2 pi j/n), cos(2 pi i/n)]``; the dense displacement
at a pixel is the tensor product of the four uniform cubic B-spline basis
functions of its span coordinate with the surrounding 4x4 control
displacements, so a control point only ever moves the 4 spans it supports.
That field is used as the backward map and the image is bilinearly resampled.
``a`` sets the amplitude ``amp = 0.45*a*min(sy,sx)`` -- kept under the
``0.48*spacing`` injectivity bound of Choi & Lee (2000), so the deformation
stays a fold-free bijection -- and ``b`` the lattice resolution. ``a = 0``
gives a zero lattice, hence the identity (up to sub-pixel resampling error).

## 詳しい使い方ガイド

- [gallery2d_geometry ファミリ ガイド](../guides/gallery2d_geometry.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_geometry](../../../../examples/gallery2d_geometry.py) — `py -3.11 examples/gallery2d_geometry.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`deformation`)

[deform_tps](deform_tps.md) · [deform_mls](deform_mls.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
