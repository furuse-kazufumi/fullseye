---
op: vignette
dim: gfx2d
category: post
in: rgb
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# vignette — GFX2D `post` op

- **データ種**: `rgb` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.vignette(rgb, strength=0.6, radius=1.0, power=2.0)` (または `opsgfx2d.get("vignette")`)

## 使い方

Darken towards the corners: ``out = rgb * (1 - strength * t**power)``.

``t`` is the distance from the geometric centre ``((h-1)/2, (w-1)/2)``
divided by ``radius`` times the half-diagonal, clipped at 1. The factor at
``t = 0`` is exactly 1, so ``strength=0`` is the exact identity and — for an
**odd-sized** image, where a pixel actually sits on the centre — that pixel
is returned untouched. An even-sized image has no centre pixel: its four
innermost pixels are 0.707 px out and are already attenuated, which is
geometry rather than a rounding error.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](bloom.md) · [chromatic_aberration](chromatic_aberration.md) · [film_grain](film_grain.md)

## 同カテゴリ(`post`)

[bloom](bloom.md) · [chromatic_aberration](chromatic_aberration.md) · [film_grain](film_grain.md) · [color_lut](color_lut.md) · [color_grade](color_grade.md) · [dither](dither.md) · [palette_quantize](palette_quantize.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
