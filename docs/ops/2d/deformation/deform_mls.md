---
op: deform_mls
dim: 2d
category: deformation
in: image
out: image
examples: [gallery2d_geometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# deform_mls — 2D `deformation` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "deform_mls", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Moving-least-squares image deformation, affine variant (Schaefer 2006).

A 5x5 grid of control points ``p_i`` is displaced to
``q_i = p_i + amp*[sin(2 pi gx), cos(2 pi gy)]`` (gy, gx = normalised
control coordinates). For every destination pixel the weighted
least-squares affine map is re-solved with the weights
``w_i = 1/|p_i - v|^(2 alpha)``, so the warp is a *different* affine at every
pixel -- smooth, interpolating at the control points, and exact on affine
data. The backward map is obtained by solving the same MLS problem with the
roles of ``p`` and ``q`` swapped (the resampling formulation of the paper's
section 4), which is the exact inverse whenever the control data is affine
and a smooth approximation of it otherwise. ``a`` sets the amplitude
``amp = 0.12*a*min(H,W)``, ``b`` the falloff ``alpha = 0.5 + 1.5b`` (large
alpha = tightly local deformation). ``a = 0`` gives ``q = p``, hence the
identity (up to sub-pixel resampling error).

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

[deform_tps](deform_tps.md) · [deform_ffd](deform_ffd.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
