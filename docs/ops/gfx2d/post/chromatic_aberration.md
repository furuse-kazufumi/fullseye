---
op: chromatic_aberration
dim: gfx2d
category: post
in: rgb
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# chromatic_aberration — GFX2D `post` op

- **データ種**: `rgb` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.chromatic_aberration(rgb, strength=0.003, interp='bilinear')` (または `opsgfx2d.get("chromatic_aberration")`)

## 使い方

Scale the red and blue channels about the image centre, green fixed.

Lateral chromatic aberration: red is magnified by ``1 + strength``, blue by
``1 - strength``. ``strength=0`` samples the exact pixel centres and returns
the input to within 1e-15, which the suite checks.

Negative ``strength`` swaps which channel spreads outward — allowed, since
which way a real lens disperses depends on the glass.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](bloom.md) · [vignette](vignette.md) · [film_grain](film_grain.md)

## 同カテゴリ(`post`)

[bloom](bloom.md) · [vignette](vignette.md) · [film_grain](film_grain.md) · [color_lut](color_lut.md) · [color_grade](color_grade.md) · [dither](dither.md) · [palette_quantize](palette_quantize.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
