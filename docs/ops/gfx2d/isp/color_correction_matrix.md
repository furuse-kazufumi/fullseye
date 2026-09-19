---
op: color_correction_matrix
dim: gfx2d
category: isp
in: rgb × matrix
out: rgb
examples: [raw_to_display_isp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# color_correction_matrix — GFX2D `isp` op

- **データ種**: `rgb × matrix` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.color_correction_matrix(rgb, ccm, normalize_rows=True)` (実装を直接呼ぶなら `import gfx2d; gfx2d.color_correction_matrix(rgb, ccm, normalize_rows=True)`、台帳から引くなら `opsgfx2d.get("color_correction_matrix")`)

## 使い方

Apply a 3x3 colour-correction matrix: ``out = rgb @ ccm.T`` per pixel,
clipped to ``[0, 1]``.

The CCM maps the sensor's spectral response onto the display primaries. With
*normalize_rows* (default) every row is divided by its sum so that **white
stays white** (``[1, 1, 1] -> [1, 1, 1]``) — the constraint most calibration
procedures impose; pass ``False`` to apply the matrix as given.

Ground truth: the identity matrix is the exact identity; a normalised matrix
maps every grey ``[v, v, v]`` to itself to 1e-15.
**Raises** ``ValueError``: *ccm* is not a finite 3x3, or a row sums to 0
when normalising.

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
