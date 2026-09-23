---
op: lens_shading_correct
dim: gfx2d
category: isp
in: image2d × image2d
out: image2d
examples: [raw_to_display_isp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# lens_shading_correct — GFX2D `isp` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.lens_shading_correct(raw, gain)` (実装を直接呼ぶなら `import gfx2d; gfx2d.lens_shading_correct(raw, gain)`、台帳から引くなら `opsgfx2d.get("lens_shading_correct")`)

## 使い方

Multiply a frame by a lens-shading gain map and clip to ``[0, 1]``.
*raw* and *gain* must have the same shape; the gain must be finite and > 0.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [raw_to_display_isp](../../../../examples/raw_to_display_isp.py) — `py -3.11 examples/raw_to_display_isp.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[shadow_cast_2d](../light/shadow_cast_2d.md) · [dither](../post/dither.md) · [raw_black_level](raw_black_level.md) · [raw_dead_pixel_mask](raw_dead_pixel_mask.md) · [raw_dead_pixel_correct](raw_dead_pixel_correct.md) · [lens_shading_gain](lens_shading_gain.md) · [raw_apply_gains](raw_apply_gains.md) · [raw_demosaic_bilinear](raw_demosaic_bilinear.md)

## 同カテゴリ(`isp`)

[raw_black_level](raw_black_level.md) · [raw_dead_pixel_mask](raw_dead_pixel_mask.md) · [raw_dead_pixel_correct](raw_dead_pixel_correct.md) · [lens_shading_gain](lens_shading_gain.md) · [awb_gains](awb_gains.md) · [rgb_apply_gains](rgb_apply_gains.md) · [raw_apply_gains](raw_apply_gains.md) · [raw_demosaic_bilinear](raw_demosaic_bilinear.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
