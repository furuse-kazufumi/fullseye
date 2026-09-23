---
op: raw_demosaic_bilinear
dim: gfx2d
category: isp
in: image2d
out: rgb
examples: [raw_to_display_isp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# raw_demosaic_bilinear — GFX2D `isp` op

- **データ種**: `image2d` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.raw_demosaic_bilinear(raw, pattern='RGGB')` (実装を直接呼ぶなら `import gfx2d; gfx2d.raw_demosaic_bilinear(raw, pattern='RGGB')`、台帳から引くなら `opsgfx2d.get("raw_demosaic_bilinear")`)

## 使い方

Bayer mosaic → ``(H, W, 3)`` RGB by bilinear interpolation, in NumPy.

Red and blue occupy one pixel in four, so a missing value is the mean of
the measured neighbours (``[[1,2,1],[2,4,2],[1,2,1]]/4`` on the masked
plane); green occupies two in four (``[[0,1,0],[1,4,1],[0,1,0]]/4``). The
border mirrors the **mosaic** two pixels out with a non-duplicating
reflection, which keeps the 2x2 phase, so a uniform field is exact up to the
edge. This is the same estimate the OpenCV bridge ``cfa_to_rgb`` makes with
``cv2.COLOR_Bayer*2RGB``, without the 8-bit round trip and without OpenCV.

Ground truth: three affine planes mosaicked and demosaicked come back to
1e-12 away from the border (a bilinear estimate of an affine field is the
field). Bilinear is the textbook baseline: it blurs colour edges into
zipper artefacts; edge-directed methods are not provided here.
**Raises** ``ValueError``: bad *raw* or *pattern*.

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
