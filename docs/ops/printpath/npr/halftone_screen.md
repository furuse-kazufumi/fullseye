---
op: halftone_screen
dim: printpath
category: npr
in: image2d
out: image2d
examples: [poc_beats_fringes_and_screens, poc_print_registration]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# halftone_screen — PRINTPATH `npr` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.halftone_screen(image, lpi=60.0, angle_deg=45.0, pixel_um=25.4, sharpness=8.0)` (実装を直接呼ぶなら `import printpath; printpath.halftone_screen(image, lpi=60.0, angle_deg=45.0, pixel_um=25.4, sharpness=8.0)`、台帳から引くなら `opsprintpath.get("halftone_screen")`)

## 使い方

A classic rotated halftone screen — dots whose area carries the tone.

Thresholds the image against a rotated periodic spot function (the product of
two shifted cosines, the classical round-dot screen). *lpi* is lines per inch
and *pixel_um* the pixel pitch, so the screen frequency in pixels follows the
printing convention rather than a bare "period in pixels".

★**Why this earns its place**: two screens at different angles beat against
one another, and the **period and direction of that moiré are a closed form**
(:func:`halftone_moire_period`) that can be predicted *before* anything is
drawn and then measured out of the image. That is why newspaper printing puts
the plates at 15°/45°/75° — the beat is pushed to a frequency the eye does not
resolve — and this op lets that be shown as numbers, not folklore.

Parameters
----------
image : 2-D array in [0, 1]
    Tone; 0 prints solid, 1 prints blank (the ink is ``1 - image``).
lpi : float
    Screen ruling, lines per inch. Newspapers use 65-85, magazines 133-175.
angle_deg : float
    Screen angle. The classical set is K 45°, M 75°, C 15°, Y 0°.
pixel_um : float
    Pixel pitch in micrometres (25.4 um = 1000 dpi).
sharpness : float
    Edge hardness of the dot; large values give a hard threshold.

Returns an ``image2d``: 1 = paper, 0 = ink.

**Raises** ``ValueError``: non-positive lpi, pixel pitch or sharpness; a screen
period below 2 px (it would alias — reported, never silently drawn); a
non-finite or oversized image.

Limits: this is a *screen*, not a printer. Dot gain, ink spread and
registration error are not modelled, so measured ink is the geometric
coverage and will read lighter than a real press.

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_beats_fringes_and_screens](../../../../examples/poc_beats_fringes_and_screens.py) — `py -3.11 examples/poc_beats_fringes_and_screens.py`
- [poc_print_registration](../../../../examples/poc_print_registration.py) — `py -3.11 examples/poc_print_registration.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[stipple_points_from_image](../stroke/stipple_points_from_image.md) · [stipple_energy](../stroke/stipple_energy.md) · [stroke_tone_error](../stroke/stroke_tone_error.md) · [engrave_lines](engrave_lines.md) · [hatch_field](hatch_field.md) · [mosaic_tiles_sites](mosaic_tiles_sites.md) · [mosaic_tiles_render](mosaic_tiles_render.md) · [print_layer_defect_map](../inspect/print_layer_defect_map.md)

## 同カテゴリ(`npr`)

[halftone_moire_period](halftone_moire_period.md) · [engrave_lines](engrave_lines.md) · [hatch_field](hatch_field.md) · [mosaic_tiles_sites](mosaic_tiles_sites.md) · [mosaic_tiles_render](mosaic_tiles_render.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
