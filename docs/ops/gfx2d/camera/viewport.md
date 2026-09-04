---
op: viewport
dim: gfx2d
category: camera
in: rgb
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# viewport — GFX2D `camera` op

- **データ種**: `rgb` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.viewport(img, x, y, width, height, scale=1.0, interp='bilinear')` (または `opsgfx2d.get("viewport")`)

## 使い方

Crop the rectangle at ``(x, y, width, height)`` and resample it by ``scale``.

Accepts ``rgb`` or ``rgba`` (straight alpha; the crop is a copy, so no
premultiplication is involved) and returns the same channel count.

**Out-of-bounds raises**, unlike :func:`sprite_blit`, which clips. The
asymmetry is the point: a sprite leaving the screen is the normal case,
while a camera asking for rows the image does not have is arithmetic that
has already gone wrong somewhere upstream, and returning a partly black
frame would let it keep going.

``scale=1`` with integer bounds returns an exact sub-array copy — no
interpolation touches it.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](../post/bloom.md) · [vignette](../post/vignette.md) · [chromatic_aberration](../post/chromatic_aberration.md)

## 同カテゴリ(`camera`)

—

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
