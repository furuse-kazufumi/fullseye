---
op: hue_saturation
dim: gfx2d
category: isp
in: rgb
out: rgb
examples: [raw_to_display_isp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# hue_saturation — GFX2D `isp` op

- **データ種**: `rgb` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.hue_saturation(rgb, hue_deg=0.0, saturation=1.0)` (実装を直接呼ぶなら `import gfx2d; gfx2d.hue_saturation(rgb, hue_deg=0.0, saturation=1.0)`、台帳から引くなら `opsgfx2d.get("hue_saturation")`)

## 使い方

Rotate the hue by *hue_deg* and scale the saturation by *saturation*,
in BT.601 YCbCr: luma is kept, the chroma vector ``(Cb, Cr)`` is rotated and
scaled. Output clipped to ``[0, 1]``.

Ground truth: ``hue_deg=0, saturation=1`` is the identity to 1e-15;
rotating by ``+t`` then ``-t`` returns the input; ``saturation=0`` gives a
grey image whose value is the BT.601 luma of the input. A hue rotation is
**not** a channel permutation (120 degrees does not swap R->G->B exactly),
because the RGB cube is not a cylinder around the grey axis — said here so
nobody tests for it.
**Raises** ``ValueError``: non-finite *hue_deg*, or *saturation* < 0.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [raw_to_display_isp](../../../../examples/raw_to_display_isp.py) — `py -3.11 examples/raw_to_display_isp.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](../post/bloom.md) · [vignette](../post/vignette.md) · [chromatic_aberration](../post/chromatic_aberration.md)

## 同カテゴリ(`isp`)

[raw_black_level](raw_black_level.md) · [raw_dead_pixel_mask](raw_dead_pixel_mask.md) · [raw_dead_pixel_correct](raw_dead_pixel_correct.md) · [lens_shading_gain](lens_shading_gain.md) · [lens_shading_correct](lens_shading_correct.md) · [awb_gains](awb_gains.md) · [rgb_apply_gains](rgb_apply_gains.md) · [raw_apply_gains](raw_apply_gains.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
