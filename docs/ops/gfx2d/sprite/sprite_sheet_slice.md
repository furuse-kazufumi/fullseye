---
op: sprite_sheet_slice
dim: gfx2d
category: sprite
in: rgba
out: sprites
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# sprite_sheet_slice — GFX2D `sprite` op

- **データ種**: `rgba` → `sprites`
- **呼び出し**: `import gfx2d; gfx2d.sprite_sheet_slice(sheet, tile_height, tile_width, margin=0, spacing=0, count=None)` (または `opsgfx2d.get("sprite_sheet_slice")`)

## 使い方

Cut a sprite atlas into a list of equal ``rgba`` frames, row-major.

``margin`` is the border around the whole sheet, ``spacing`` the gap between
neighbouring cells — the two numbers that every atlas exporter writes and
that every hand-rolled slicer gets wrong by one.

Returns a ``list`` of ``(tile_height, tile_width, 4)`` arrays. With
``margin=spacing=0`` it is the exact inverse of :func:`tilemap_render`.

Raises ValueError: a sheet that does not contain a whole number of cells
(a partial cell means the margin/spacing are wrong, and silently dropping it
hides that), a ``count`` larger than the grid, more than
:data:`MAX_SPRITES` cells.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`sprites` を入力に取れる)

[tilemap_render](../tile/tilemap_render.md) · [parallax_layers](../tile/parallax_layers.md)

## 同カテゴリ(`sprite`)

[sprite_synthesize](sprite_synthesize.md) · [sprite_blit](sprite_blit.md) · [sprite_transform](sprite_transform.md) · [nine_slice](nine_slice.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
