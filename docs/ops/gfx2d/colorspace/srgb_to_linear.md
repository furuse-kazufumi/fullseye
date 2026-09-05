---
op: srgb_to_linear
dim: gfx2d
category: colorspace
in: rgb
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# srgb_to_linear — GFX2D `colorspace` op

- **データ種**: `rgb` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.srgb_to_linear(img)` (または `opsgfx2d.get("srgb_to_linear")`)

## 使い方

sRGB-encoded values to linear light (IEC 61966-2-1).

An alpha channel, if present, is **not** transformed — coverage is already
linear. Accepts ``(H, W)``, ``(H, W, 1|3|4)``.

Use this before anything that adds or scales light (:func:`radial_light`,
:func:`light_mask`, :func:`normal_map_shade`, :func:`bloom`) if the input
came out of an image file. Skipping it does not raise: it makes highlights
bloom too early and shadows too dark, by the amount quoted in the module
docstring.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[linear_to_srgb](linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](../post/bloom.md) · [vignette](../post/vignette.md) · [chromatic_aberration](../post/chromatic_aberration.md) · [film_grain](../post/film_grain.md)

## 同カテゴリ(`colorspace`)

[linear_to_srgb](linear_to_srgb.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
