---
op: tac_shear_field
dim: 2d
category: tactile
in: image
out: image
examples: [sim2real_and_alife]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tac_shear_field — 2D `tactile` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "tac_shear_field", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

In-plane shear proxy from the 2-D structure tensor (Foerstner /
Bigun-Granlund orientation coherence). The tensor
``J = G_sigma(grad v * grad v^T)`` has eigenvalues l1 >= l2, and the
coherence ``(l1-l2)/(l1+l2) = sqrt((J11-J22)^2 + 4*J12^2) / (J11+J22)``
is 1 where the gel texture is stretched into a single dominant orientation
(as it is under tangential/shear load) and 0 where it is isotropic. The
result is additionally weighted by the tensor trace (gradient energy) so
that texture-free, un-contacted gel stays dark instead of amplifying noise
orientation. ``a`` = tensor integration sigma (0.6..4.6), ``b`` = output gain
(0.5..2.5). Output clipped to [0,1], HxW; a constant frame has zero gradient
energy and yields an all-zero shear field.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sim2real_and_alife](../../../../examples/sim2real_and_alife.py) — `py -3.11 examples/sim2real_and_alife.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`tactile`)

[tac_contact_mask](tac_contact_mask.md) · [tac_height_from_shading](tac_height_from_shading.md) · [tac_surface_normal](tac_surface_normal.md) · [tac_pressure_proxy](tac_pressure_proxy.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
