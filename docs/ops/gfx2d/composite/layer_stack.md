---
op: layer_stack
dim: gfx2d
category: composite
in: table
out: rgba
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# layer_stack — GFX2D `composite` op

- **データ種**: `table` → `rgba`
- **呼び出し**: `import gfx2d; gfx2d.layer_stack(layers)` (または `opsgfx2d.get("layer_stack")`)

## 使い方

Composite a z-ordered list of ``rgba`` layers, bottom first.

Each layer is a dict:

``{"image": rgba, "mode": str = "normal", "opacity": float = 1.0}``

and the W3C rule for a blend mode against a *partially transparent* backdrop
is used — the blend function is weighted by the backdrop's own alpha,
``Cs' = (1 - a_b) Cs + a_b B(Cb, Cs)`` — so a layer over empty space keeps
its own colour whatever the mode. The result is straight-alpha ``rgba``.

All layers must share one shape; see :func:`alpha_composite` on why.

Raises ValueError: empty list, more than :data:`MAX_LAYERS`, a non-dict
entry, an unknown key, mismatched shapes.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba` を入力に取れる)

[premultiply](premultiply.md) · [alpha_composite](alpha_composite.md) · [sprite_blit](../sprite/sprite_blit.md) · [sprite_transform](../sprite/sprite_transform.md) · [sprite_sheet_slice](../sprite/sprite_sheet_slice.md) · [nine_slice](../sprite/nine_slice.md)

## 同カテゴリ(`composite`)

[premultiply](premultiply.md) · [unpremultiply](unpremultiply.md) · [alpha_composite](alpha_composite.md) · [alpha_composite_premul](alpha_composite_premul.md) · [blend_mode](blend_mode.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
