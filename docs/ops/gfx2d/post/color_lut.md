---
op: color_lut
dim: gfx2d
category: post
in: 
out: lut
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# color_lut — GFX2D `post` op

- **データ種**: `` → `lut`
- **呼び出し**: `import gfx2d; gfx2d.color_lut(size=17, gain=(1.0, 1.0, 1.0), lift=(0.0, 0.0, 0.0), gamma=(1.0, 1.0, 1.0), saturation=1.0)` (または `opsgfx2d.get("color_lut")`)

## 使い方

Build a 3-D colour LUT, ``(n, n, n, 3)`` indexed ``[r, g, b]``.

``out = clip(lift + gain * in**gamma)`` per channel, then saturation is
applied about the Rec. 709 luma. With all defaults this is the **identity
LUT**, and because trilinear interpolation is exact for a function that is
linear in each variable, :func:`color_grade` with the identity LUT is the
identity to float64 rounding (measured maximum 3.3e-16 at size 17 and
2.2e-16 at size 2) — the property the suite uses to prove the interpolation
itself is right before testing any grade.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`lut` を入力に取れる)

[color_grade](color_grade.md)

## 同カテゴリ(`post`)

[bloom](bloom.md) · [vignette](vignette.md) · [chromatic_aberration](chromatic_aberration.md) · [film_grain](film_grain.md) · [color_grade](color_grade.md) · [dither](dither.md) · [palette_quantize](palette_quantize.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
