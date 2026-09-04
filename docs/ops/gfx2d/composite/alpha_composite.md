---
op: alpha_composite
dim: gfx2d
category: composite
in: rgba × rgba
out: rgba
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# alpha_composite — GFX2D `composite` op

- **データ種**: `rgba × rgba` → `rgba`
- **呼び出し**: `import gfx2d; gfx2d.alpha_composite(src, dst)` (または `opsgfx2d.get("alpha_composite")`)

## 使い方

Porter–Duff **over** on straight-alpha ``rgba`` (Porter & Duff 1984).

``a_o = a_s + a_d (1 - a_s)`` and
``C_o = (C_s a_s + C_d a_d (1 - a_s)) / a_o``, with ``C_o = 0`` where
``a_o == 0``.

Both arguments must be straight-alpha and the **same shape** — this family
never broadcasts, because a broadcast image is a silently wrong picture. Use
:func:`sprite_blit` to place something smaller.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba` を入力に取れる)

[premultiply](premultiply.md) · [sprite_blit](../sprite/sprite_blit.md) · [sprite_transform](../sprite/sprite_transform.md) · [sprite_sheet_slice](../sprite/sprite_sheet_slice.md) · [nine_slice](../sprite/nine_slice.md)

## 同カテゴリ(`composite`)

[premultiply](premultiply.md) · [unpremultiply](unpremultiply.md) · [alpha_composite_premul](alpha_composite_premul.md) · [blend_mode](blend_mode.md) · [layer_stack](layer_stack.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
