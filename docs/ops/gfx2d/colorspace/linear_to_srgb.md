---
op: linear_to_srgb
dim: gfx2d
category: colorspace
in: rgb
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# linear_to_srgb — GFX2D `colorspace` op

- **データ種**: `rgb` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.linear_to_srgb(img)` (または `opsgfx2d.get("linear_to_srgb")`)

## 使い方

Linear light back to sRGB encoding. Exact inverse of :func:`srgb_to_linear`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](srgb_to_linear.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](../post/bloom.md) · [vignette](../post/vignette.md) · [chromatic_aberration](../post/chromatic_aberration.md) · [film_grain](../post/film_grain.md)

## 同カテゴリ(`colorspace`)

[srgb_to_linear](srgb_to_linear.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
