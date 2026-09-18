---
op: raw_black_level
dim: gfx2d
category: isp
in: image2d
out: image2d
examples: [raw_to_display_isp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# raw_black_level — GFX2D `isp` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.raw_black_level(raw, offsets, white=1.0, pattern='RGGB')` (実装を直接呼ぶなら `import gfx2d; gfx2d.raw_black_level(raw, offsets, white=1.0, pattern='RGGB')`、台帳から引くなら `opsgfx2d.get("raw_black_level")`)

## 使い方

Black-level compensation on a Bayer frame: ``(raw - offset) / (white - offset)``
per colour channel, clipped to ``[0, 1]``.

A sensor's dark output is not zero (pedestal + dark current); every later
stage that multiplies (gains, CCM) would scale that pedestal into a colour
cast, so this runs **first**. *offsets* is a scalar, 3 values ``(R, G, B)``
or 4 values ``(R, G1, G2, B)`` in the same ``[0, 1]`` units as *raw*; *white*
is the saturation level, so a pixel at *white* maps to exactly 1.

Ground truth: a frame built as ``offset + k * signal`` comes back as
``k * signal / (white - offset)`` to 1e-15; a pixel at the offset maps to 0.
**Raises** ``ValueError``: non-finite input, an offset ``>= white``, or an
unknown *pattern*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [raw_to_display_isp](../../../../examples/raw_to_display_isp.py) — `py -3.11 examples/raw_to_display_isp.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[shadow_cast_2d](../light/shadow_cast_2d.md) · [dither](../post/dither.md) · [raw_dead_pixel_mask](raw_dead_pixel_mask.md) · [raw_dead_pixel_correct](raw_dead_pixel_correct.md) · [lens_shading_gain](lens_shading_gain.md) · [lens_shading_correct](lens_shading_correct.md) · [raw_apply_gains](raw_apply_gains.md) · [raw_demosaic_bilinear](raw_demosaic_bilinear.md)

## 同カテゴリ(`isp`)

[raw_dead_pixel_mask](raw_dead_pixel_mask.md) · [raw_dead_pixel_correct](raw_dead_pixel_correct.md) · [lens_shading_gain](lens_shading_gain.md) · [lens_shading_correct](lens_shading_correct.md) · [awb_gains](awb_gains.md) · [rgb_apply_gains](rgb_apply_gains.md) · [raw_apply_gains](raw_apply_gains.md) · [raw_demosaic_bilinear](raw_demosaic_bilinear.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
