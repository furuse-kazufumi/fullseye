---
op: unpremultiply
dim: gfx2d
category: composite
in: rgba_premul
out: rgba
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# unpremultiply — GFX2D `composite` op

- **データ種**: `rgba_premul` → `rgba`
- **呼び出し**: `import gfx2d; gfx2d.unpremultiply(rgba_premul)` (または `opsgfx2d.get("unpremultiply")`)

## 使い方

**Premultiplied** ``rgba`` back to straight alpha: ``(C/A, A)``.

Pixels with ``alpha == 0`` come back as transparent black (see
:func:`premultiply` on why that is the only defensible answer).

Raises ValueError: if the input is not premultiplied, detected as
``colour > alpha`` at some pixel.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba` を入力に取れる)

[premultiply](premultiply.md) · [alpha_composite](alpha_composite.md) · [sprite_blit](../sprite/sprite_blit.md) · [sprite_transform](../sprite/sprite_transform.md) · [sprite_sheet_slice](../sprite/sprite_sheet_slice.md) · [nine_slice](../sprite/nine_slice.md)

## 同カテゴリ(`composite`)

[premultiply](premultiply.md) · [alpha_composite](alpha_composite.md) · [alpha_composite_premul](alpha_composite_premul.md) · [blend_mode](blend_mode.md) · [layer_stack](layer_stack.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
