---
op: film_grain
dim: gfx2d
category: post
in: rgb
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# film_grain — GFX2D `post` op

- **データ種**: `rgb` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.film_grain(rgb, sigma=0.03, seed=0, monochrome=True)` (または `opsgfx2d.get("film_grain")`)

## 使い方

Add zero-mean Gaussian grain, deterministically from ``seed``.

``monochrome`` adds the same noise to all three channels (what film grain
does — the silver halide crystal is not coloured); set it false for sensor
read noise, which is per-channel.

``sigma=0`` returns the input bit for bit. The clip at ``[0, 1]`` biases the
mean wherever the image is already near an end of the range; the suite
measures the shift (2.4e-4 on a mid-grey image at sigma=0.03, 1.0e-4 on a
half-black half-white one) rather than claiming it is zero.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](bloom.md) · [vignette](vignette.md) · [chromatic_aberration](chromatic_aberration.md)

## 同カテゴリ(`post`)

[bloom](bloom.md) · [vignette](vignette.md) · [chromatic_aberration](chromatic_aberration.md) · [color_lut](color_lut.md) · [color_grade](color_grade.md) · [dither](dither.md) · [palette_quantize](palette_quantize.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
