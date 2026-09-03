---
op: blend_mode
dim: gfx2d
category: composite
in: rgb × rgb
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# blend_mode — GFX2D `composite` op

- **データ種**: `rgb × rgb` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.blend_mode(base, top, mode='normal', opacity=1.0)` (または `opsgfx2d.get("blend_mode")`)

## 使い方

Blend two opaque ``rgb`` images with a named mode (W3C Level 1).

With an opaque backdrop the specification reduces to a lerp,
``Co = (1 - opacity)*Cb + opacity*B(Cb, Cs)``, so ``opacity=0`` returns the
backdrop **exactly** and ``mode="normal", opacity=1`` returns the source
exactly. Both identities are checked bit-for-bit in the test suite.

Named ``blend_mode`` and not ``blend`` because :func:`imagemorph.blend`
already owns that name for a two-image cross-fade; two functions called
``blend`` with different signatures is exactly the kind of collision this
library's naming test exists to prevent.

Raises ValueError: unknown mode, mismatched shapes, opacity outside
``[0, 1]``, values outside ``[0, 1]``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](../post/bloom.md) · [vignette](../post/vignette.md) · [chromatic_aberration](../post/chromatic_aberration.md) · [film_grain](../post/film_grain.md)

## 同カテゴリ(`composite`)

[premultiply](premultiply.md) · [unpremultiply](unpremultiply.md) · [alpha_composite](alpha_composite.md) · [alpha_composite_premul](alpha_composite_premul.md) · [layer_stack](layer_stack.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
