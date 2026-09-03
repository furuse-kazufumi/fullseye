---
op: sprite_synthesize
dim: gfx2d
category: sprite
in: 
out: rgba
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# sprite_synthesize — GFX2D `sprite` op

- **データ種**: `` → `rgba`
- **呼び出し**: `import gfx2d; gfx2d.sprite_synthesize(kind='disc', size=32, color='emphasis', thickness=0.25, scheme='okabe_ito')` (または `opsgfx2d.get("sprite_synthesize")`)

## 使い方

A deterministic anti-aliased test sprite, ``rgba`` ``(size, size, 4)``.

The entry point of the sprite sort: it needs no asset on disk, and because
the silhouette comes from an implicit equation the alpha channel *is* the
ground-truth coverage mask — which is the whole reason this family belongs
in a vision library.

``kind`` is ``"disc"``, ``"ring"``, ``"box"``, ``"diamond"`` or ``"star"``.
``color`` is a :mod:`palette` role name (default) or an explicit 3/4-tuple.
``thickness`` is the ring's wall as a fraction of the radius.

Coverage is computed by 4x4 regular supersampling, so alpha takes values on
the exact lattice ``k/16``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba` を入力に取れる)

[premultiply](../composite/premultiply.md) · [alpha_composite](../composite/alpha_composite.md) · [sprite_blit](sprite_blit.md) · [sprite_transform](sprite_transform.md) · [sprite_sheet_slice](sprite_sheet_slice.md) · [nine_slice](nine_slice.md)

## 同カテゴリ(`sprite`)

[sprite_blit](sprite_blit.md) · [sprite_transform](sprite_transform.md) · [sprite_sheet_slice](sprite_sheet_slice.md) · [nine_slice](nine_slice.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
