---
op: light_mask
dim: gfx2d
category: light
in: rgb × rgb
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# light_mask — GFX2D `light` op

- **データ種**: `rgb × rgb` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.light_mask(base, light, ambient=0.0)` (または `opsgfx2d.get("light_mask")`)

## 使い方

Modulate an ``rgb`` image by an ``rgb`` light map: ``base * (ambient + light)``.

``ambient`` is the light that reaches everything; ``ambient=1`` with a black
light map returns the base **exactly**, which is the identity the test suite
pins.

The product is clipped to ``[0, 1]``; the clipped amount is not returned.
Both arguments should be in the same encoding — mixing an sRGB base with a
linear light map is the second silent-error trap of this family, and the
only defence is that both arguments are named.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [normal_map_decode](normal_map_decode.md) · [bloom](../post/bloom.md) · [vignette](../post/vignette.md) · [chromatic_aberration](../post/chromatic_aberration.md) · [film_grain](../post/film_grain.md)

## 同カテゴリ(`light`)

[radial_light](radial_light.md) · [normal_map_decode](normal_map_decode.md) · [normal_map_shade](normal_map_shade.md) · [shadow_cast_2d](shadow_cast_2d.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
