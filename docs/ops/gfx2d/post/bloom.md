---
op: bloom
dim: gfx2d
category: post
in: rgb
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# bloom — GFX2D `post` op

- **データ種**: `rgb` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.bloom(rgb, threshold=0.8, sigma=4.0, intensity=0.6)` (または `opsgfx2d.get("bloom")`)

## 使い方

Bleed the bright parts of an image into their neighbourhood.

The classical three steps: isolate what is above ``threshold``, blur it by a
Gaussian of ``sigma``, add ``intensity`` times the result back, clip.

A *linear-light* operator: light spreading in a lens adds radiance. Running
it on sRGB-encoded values makes the halo too strong in the mid-tones —
``srgb_to_linear`` first, ``linear_to_srgb`` after.

Exact identities: ``intensity=0`` and ``threshold >= 1`` both return the
input bit for bit, and a black image stays black.

The added energy is *not* conserved by the clip at the end. The suite
measures both halves: on a centred bright blob the Gaussian preserves the
bright mass to **5.0e-16** relative, so everything lost after that is the
clip — on a random scene with a saturated square, 2.69 % of the pixels clip
and 1.65 % of the total energy is thrown away, and neither number is
returned to the caller.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [vignette](vignette.md) · [chromatic_aberration](chromatic_aberration.md) · [film_grain](film_grain.md)

## 同カテゴリ(`post`)

[vignette](vignette.md) · [chromatic_aberration](chromatic_aberration.md) · [film_grain](film_grain.md) · [color_lut](color_lut.md) · [color_grade](color_grade.md) · [dither](dither.md) · [palette_quantize](palette_quantize.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
