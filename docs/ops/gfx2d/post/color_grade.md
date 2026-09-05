---
op: color_grade
dim: gfx2d
category: post
in: rgb × lut
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# color_grade — GFX2D `post` op

- **データ種**: `rgb × lut` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.color_grade(rgb, lut)` (または `opsgfx2d.get("color_grade")`)

## 使い方

Apply a 3-D colour LUT to an ``rgb`` image by trilinear interpolation.

``lut`` is ``(n, n, n, 3)`` indexed ``[r, g, b]`` — the layout
:func:`color_lut` produces. The identity LUT returns the input to within
float64 rounding (measured maximum 3.3e-16), which is what makes this
testable without a reference implementation: trilinear interpolation of a
coordinate function is that coordinate, exactly.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](bloom.md) · [vignette](vignette.md) · [chromatic_aberration](chromatic_aberration.md)

## 同カテゴリ(`post`)

[bloom](bloom.md) · [vignette](vignette.md) · [chromatic_aberration](chromatic_aberration.md) · [film_grain](film_grain.md) · [color_lut](color_lut.md) · [dither](dither.md) · [palette_quantize](palette_quantize.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
