---
op: parallax_layers
dim: gfx2d
category: tile
in: sprites
out: rgba
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# parallax_layers — GFX2D `tile` op

- **データ種**: `sprites` → `rgba`
- **呼び出し**: `import gfx2d; gfx2d.parallax_layers(layers, camera_x, factors, camera_y=0.0, factors_y=None)` (または `opsgfx2d.get("parallax_layers")`)

## 使い方

Scroll a set of ``rgba`` layers at different rates and composite them.

``layers[0]`` is the farthest layer and is drawn first. Each layer is
shifted by ``-round(camera_x * factors[i])`` columns (and rows, if
``factors_y`` is given) and **wraps** — a parallax backdrop is a loop, and
wrapping is what makes it one.

Shifts are rounded to whole pixels, so the scroll is a pure permutation: a
single layer shifted by exactly its own width comes back with its alpha
channel bit-identical and its colour identical wherever ``alpha > 0``. (The
colour of *fully transparent* pixels is not preserved — compositing goes
through :func:`premultiply`, which zeroes it by definition. That is the
documented cost of the premultiplied round trip, not a bug in the scroll.)

Sub-pixel scrolling would resample every frame and accumulate blur, which is
why it is not offered here — put the fractional part in
:func:`sprite_transform` if you need it.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba` を入力に取れる)

[premultiply](../composite/premultiply.md) · [alpha_composite](../composite/alpha_composite.md) · [sprite_blit](../sprite/sprite_blit.md) · [sprite_transform](../sprite/sprite_transform.md) · [sprite_sheet_slice](../sprite/sprite_sheet_slice.md) · [nine_slice](../sprite/nine_slice.md)

## 同カテゴリ(`tile`)

[tilemap_render](tilemap_render.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
