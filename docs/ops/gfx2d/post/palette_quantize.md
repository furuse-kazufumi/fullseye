---
op: palette_quantize
dim: gfx2d
category: post
in: rgb
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# palette_quantize — GFX2D `post` op

- **データ種**: `rgb` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.palette_quantize(rgb, colors=None, scheme='okabe_ito')` (または `opsgfx2d.get("palette_quantize")`)

## 使い方

Map every pixel to its nearest palette colour in Euclidean RGB.

``colors`` is an ``(K, 3)`` array or a list of :mod:`palette` role names;
the default is the whole Okabe–Ito set plus black and white, so the result
stays legible under a colour vision deficiency.

The search is exhaustive, so the assignment is **optimal for this metric**
and each pixel's error equals its distance to the nearest palette entry —
there is no approximation to bound. The suite checks optimality by brute
force and checks that an image whose colours already lie in the palette
comes back unchanged, bit for bit.

Euclidean distance in (possibly sRGB-encoded) RGB is not perceptual
distance. That is a documented choice, not an oversight: a perceptual metric
needs a colour-appearance model this module does not own, and quantising in
an unstated space would be worse than quantising in a stated one.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](bloom.md) · [vignette](vignette.md) · [chromatic_aberration](chromatic_aberration.md)

## 同カテゴリ(`post`)

[bloom](bloom.md) · [vignette](vignette.md) · [chromatic_aberration](chromatic_aberration.md) · [film_grain](film_grain.md) · [color_lut](color_lut.md) · [color_grade](color_grade.md) · [dither](dither.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
