---
op: raw_dead_pixel_mask
dim: gfx2d
category: isp
in: image2d
out: image2d
examples: [raw_to_display_isp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# raw_dead_pixel_mask — GFX2D `isp` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.raw_dead_pixel_mask(raw, threshold=0.1)` (実装を直接呼ぶなら `import gfx2d; gfx2d.raw_dead_pixel_mask(raw, threshold=0.1)`、台帳から引くなら `opsgfx2d.get("raw_dead_pixel_mask")`)

## 使い方

Where the dead (stuck / hot) pixels are: ``1.0`` at a pixel that differs
from **every one** of its 8 same-colour neighbours by more than *threshold*
in the same direction, ``0.0`` elsewhere. ``(H, W)`` float64.

"Every neighbour, same sign" is what separates a defect from an edge: at an
edge some same-colour neighbours are on the pixel's own side. The rule is
the one openISP documents for its DPC stage; here it is pattern-free
because same-colour neighbours are simply the pixels two steps away.

Ground truth: dead pixels planted in a smooth frame are recovered exactly
(no misses, no false alarms) while a hard edge produces none.
**Raises** ``ValueError``: bad *raw* or a *threshold* outside ``(0, 1]``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [raw_to_display_isp](../../../../examples/raw_to_display_isp.py) — `py -3.11 examples/raw_to_display_isp.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[shadow_cast_2d](../light/shadow_cast_2d.md) · [dither](../post/dither.md) · [raw_black_level](raw_black_level.md) · [raw_dead_pixel_correct](raw_dead_pixel_correct.md) · [lens_shading_gain](lens_shading_gain.md) · [lens_shading_correct](lens_shading_correct.md) · [raw_apply_gains](raw_apply_gains.md) · [raw_demosaic_bilinear](raw_demosaic_bilinear.md)

## 同カテゴリ(`isp`)

[raw_black_level](raw_black_level.md) · [raw_dead_pixel_correct](raw_dead_pixel_correct.md) · [lens_shading_gain](lens_shading_gain.md) · [lens_shading_correct](lens_shading_correct.md) · [awb_gains](awb_gains.md) · [rgb_apply_gains](rgb_apply_gains.md) · [raw_apply_gains](raw_apply_gains.md) · [raw_demosaic_bilinear](raw_demosaic_bilinear.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
