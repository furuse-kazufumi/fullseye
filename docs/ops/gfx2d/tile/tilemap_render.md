---
op: tilemap_render
dim: gfx2d
category: tile
in: sprites
out: rgba
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tilemap_render — GFX2D `tile` op

- **データ種**: `sprites` → `rgba`
- **呼び出し**: `import gfx2d; gfx2d.tilemap_render(tiles, indices, empty=-1)` (または `opsgfx2d.get("tilemap_render")`)

## 使い方

Paint a grid of tile indices into one ``rgba`` image.

``tiles`` is a list of equally sized ``rgba`` tiles (what
:func:`sprite_sheet_slice` returns) or an ``(N, th, tw, 4)`` array.
``indices`` is a 2-D **integer** array; a cell equal to ``empty`` is left
transparent. The result is ``(rows*th, cols*tw, 4)``.

Every cell is a copy, not a resample, so the output equals the tile exactly.

Raises ValueError: a float index array (a float "index" is a rounding waiting
to happen), an index outside the tile set, tiles of differing shapes, an
output past :data:`MAX_PIXELS`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba` を入力に取れる)

[premultiply](../composite/premultiply.md) · [alpha_composite](../composite/alpha_composite.md) · [sprite_blit](../sprite/sprite_blit.md) · [sprite_transform](../sprite/sprite_transform.md) · [sprite_sheet_slice](../sprite/sprite_sheet_slice.md) · [nine_slice](../sprite/nine_slice.md)

## 同カテゴリ(`tile`)

[parallax_layers](parallax_layers.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
