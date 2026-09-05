---
op: sprite_transform
dim: gfx2d
category: sprite
in: rgba
out: rgba
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# sprite_transform — GFX2D `sprite` op

- **データ種**: `rgba` → `rgba`
- **呼び出し**: `import gfx2d; gfx2d.sprite_transform(sprite, angle_deg=0.0, scale=1.0, interp='bilinear', out_shape=None)` (または `opsgfx2d.get("sprite_transform")`)

## 使い方

Rotate and/or scale an ``rgba`` sprite about its centre.

A **positive** ``angle_deg`` turns the sprite clockwise on screen, because
the row axis points down. ``interp`` is ``"nearest"``, ``"bilinear"`` or
``"bicubic"`` (a cubic spline; it overshoots, and the overshoot is clipped
back into the premultiplied range).

The resampling happens in **premultiplied** space and the result is
converted back. Interpolating straight colour instead mixes in the colour of
fully transparent pixels — usually black, and invisible in the alpha channel
— which shows up as a dark fringe. Measured on a white disc whose
transparent region is black, composited over mid-grey: the straight-space
result differs from this one by up to **0.203** and by **0.048** on average
over the pixels it changes (rotations of 13, 37 and 45 degrees; the maximum
was 0.197, 0.203, 0.156).

Exact where it can be: ``angle_deg=0, scale=1`` returns the input bit for
bit, and a multiple of 90 degrees with ``interp="nearest"`` permutes the
alpha channel exactly (colour matches to 1.2e-16, the cost of the
premultiply round trip). Everything else costs interpolation: the measured
round trip of ``+37`` then ``-37`` degrees, bilinear, is a mean alpha error
of **0.0150** with a maximum of **0.8125** at the one pixel where the edge
crosses a sample.

``out_shape`` is ``(height, width)``; the default is the bounding box of the
transformed sprite, rounded up.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba` を入力に取れる)

[premultiply](../composite/premultiply.md) · [alpha_composite](../composite/alpha_composite.md) · [sprite_blit](sprite_blit.md) · [sprite_sheet_slice](sprite_sheet_slice.md) · [nine_slice](nine_slice.md)

## 同カテゴリ(`sprite`)

[sprite_synthesize](sprite_synthesize.md) · [sprite_blit](sprite_blit.md) · [sprite_sheet_slice](sprite_sheet_slice.md) · [nine_slice](nine_slice.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
