---
op: alpha_composite_premul
dim: gfx2d
category: composite
in: rgba_premul × rgba_premul
out: rgba_premul
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# alpha_composite_premul — GFX2D `composite` op

- **データ種**: `rgba_premul × rgba_premul` → `rgba_premul`
- **呼び出し**: `import gfx2d; gfx2d.alpha_composite_premul(src, dst)` (または `opsgfx2d.get("alpha_composite_premul")`)

## 使い方

Porter–Duff **over** on premultiplied colour: ``src + dst*(1 - src.a)``.

This is the operator; :func:`alpha_composite` is this one with a conversion
on each side. Being affine in ``dst``, it is **exactly associative** —
``over(over(A, B), C) == over(A, over(B, C))`` to float64 rounding, which the
test suite checks as an equality rather than a tolerance.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba_premul` を入力に取れる)

[unpremultiply](unpremultiply.md)

## 同カテゴリ(`composite`)

[premultiply](premultiply.md) · [unpremultiply](unpremultiply.md) · [alpha_composite](alpha_composite.md) · [blend_mode](blend_mode.md) · [layer_stack](layer_stack.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
