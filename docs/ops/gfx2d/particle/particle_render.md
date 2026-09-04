---
op: particle_render
dim: gfx2d
category: particle
in: table
out: rgba
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# particle_render — GFX2D `particle` op

- **データ種**: `table` → `rgba`
- **呼び出し**: `import gfx2d; gfx2d.particle_render(state, height, width, mode='add', fade=True)` (または `opsgfx2d.get("particle_render")`)

## 使い方

Splat a particle state into an ``rgba`` image.

Each particle is a radially symmetric ``(1 - (r/R)^2)^2`` kernel of radius
``size``, weighted by its alpha and, when ``fade`` is set, by the remaining
fraction of its life ``(1 - age/life)``. Particles past their lifetime
contribute nothing.

``mode`` is ``"add"`` (premultiplied additive — what a spark does; the
result is clipped at 1 and the clipped energy is *not* returned) or
``"over"`` (each particle composited in array order, which is what a soft
smoke puff does).

Pure function of the state: no randomness enters here, so two calls on the
same state produce identical bytes.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba` を入力に取れる)

[premultiply](../composite/premultiply.md) · [alpha_composite](../composite/alpha_composite.md) · [sprite_blit](../sprite/sprite_blit.md) · [sprite_transform](../sprite/sprite_transform.md) · [sprite_sheet_slice](../sprite/sprite_sheet_slice.md) · [nine_slice](../sprite/nine_slice.md)

## 同カテゴリ(`particle`)

[particle_emit](particle_emit.md) · [particle_step](particle_step.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
