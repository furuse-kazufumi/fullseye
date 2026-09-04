---
op: nine_slice
dim: gfx2d
category: sprite
in: rgba
out: rgba
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# nine_slice — GFX2D `sprite` op

- **データ種**: `rgba` → `rgba`
- **呼び出し**: `import gfx2d; gfx2d.nine_slice(sprite, left, right, top, bottom, out_height, out_width)` (または `opsgfx2d.get("nine_slice")`)

## 使い方

Stretch a frame to a new size without deforming its corners.

The four corners are copied **bit for bit**, the four edges are stretched
along one axis only, and the centre is stretched along both. This is the
standard way a UI panel grows: the border keeps its thickness at any size.

Stretching is nearest-neighbour on the interior spans, so an output the same
size as the input is the exact identity — no resampling blur creeps in when
a panel happens not to need stretching.

Raises ValueError: borders that meet or cross (``left + right >= width``),
an output smaller than the borders it must preserve.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba` を入力に取れる)

[premultiply](../composite/premultiply.md) · [alpha_composite](../composite/alpha_composite.md) · [sprite_blit](sprite_blit.md) · [sprite_transform](sprite_transform.md) · [sprite_sheet_slice](sprite_sheet_slice.md)

## 同カテゴリ(`sprite`)

[sprite_synthesize](sprite_synthesize.md) · [sprite_blit](sprite_blit.md) · [sprite_transform](sprite_transform.md) · [sprite_sheet_slice](sprite_sheet_slice.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
