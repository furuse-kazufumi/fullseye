---
op: deform_tps
dim: 2d
category: deformation
in: image
out: image
examples: [gallery2d_geometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# deform_tps — 2D `deformation` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "deform_tps", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Thin-plate-spline warp over a 5x5 control grid (Bookstein, TPAMI 1989).

The 3x3 interior control points are displaced by the deterministic smooth
field ``d = amp * [sin(2 pi f gx), cos(2 pi f gy)]`` (gy, gx = the control
point's normalised coordinates), the 16 border control points are pinned so
the frame stays anchored. The backward map is the TPS interpolant fitted
from the *displaced* control points back to the original ones -- the unique
minimum-bending-energy interpolant, i.e. the surface a thin metal plate
would take -- and it is evaluated at every destination pixel before bilinear
resampling. ``a`` sets the amplitude ``amp = 0.15*a*min(H,W)``, ``b`` the
spatial frequency ``f = 0.5 + 1.5b``. ``a = 0`` leaves the control points
where they are, so the solved map is the identity (up to sub-pixel resampling error).

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

[deform_ffd](deform_ffd.md) · [deform_mls](deform_mls.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
