---
op: raw_apply_gains
dim: gfx2d
category: isp
in: image2d × vector
out: image2d
examples: [raw_to_display_isp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# raw_apply_gains — GFX2D `isp` op

- **データ種**: `image2d × vector` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.raw_apply_gains(raw, gains, pattern='RGGB')` (実装を直接呼ぶなら `import gfx2d; gfx2d.raw_apply_gains(raw, gains, pattern='RGGB')`、台帳から引くなら `opsgfx2d.get("raw_apply_gains")`)

## 使い方

Multiply a Bayer frame by per-channel gains (3 values ``R, G, B`` or 4
values ``R, G1, G2, B``) and clip to ``[0, 1]`` — white balance applied
**before** demosaicing, which is where a real ISP does it (interpolating
unbalanced channels smears the cast across colours).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [raw_to_display_isp](../../../../examples/raw_to_display_isp.py) — `py -3.11 examples/raw_to_display_isp.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[shadow_cast_2d](../light/shadow_cast_2d.md) · [dither](../post/dither.md) · [raw_black_level](raw_black_level.md) · [raw_dead_pixel_mask](raw_dead_pixel_mask.md) · [raw_dead_pixel_correct](raw_dead_pixel_correct.md) · [lens_shading_gain](lens_shading_gain.md) · [lens_shading_correct](lens_shading_correct.md) · [raw_demosaic_bilinear](raw_demosaic_bilinear.md)

## 同カテゴリ(`isp`)

[raw_black_level](raw_black_level.md) · [raw_dead_pixel_mask](raw_dead_pixel_mask.md) · [raw_dead_pixel_correct](raw_dead_pixel_correct.md) · [lens_shading_gain](lens_shading_gain.md) · [lens_shading_correct](lens_shading_correct.md) · [awb_gains](awb_gains.md) · [rgb_apply_gains](rgb_apply_gains.md) · [raw_demosaic_bilinear](raw_demosaic_bilinear.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
