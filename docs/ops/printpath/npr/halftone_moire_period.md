---
op: halftone_moire_period
dim: printpath
category: npr
in: 
out: table
examples: [poc_beats_fringes_and_screens, poc_moire_screen, poc_print_registration]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# halftone_moire_period — PRINTPATH `npr` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.halftone_moire_period(lpi_a=60.0, angle_a_deg=45.0, lpi_b=60.0, angle_b_deg=75.0, pixel_um=25.4)` (実装を直接呼ぶなら `import printpath; printpath.halftone_moire_period(lpi_a=60.0, angle_a_deg=45.0, lpi_b=60.0, angle_b_deg=75.0, pixel_um=25.4)`、台帳から引くなら `opsprintpath.get("halftone_moire_period")`)

## 使い方

The beat between two halftone screens — period and direction, in closed form.

Each screen is a frequency **vector** ``f (cos t, sin t)``; where two screens
overlap the visible moiré is the difference vector, so its period is
``1 / |f_a - f_b|`` and its direction is that of the difference. For equal
rulings the magnitude reduces to ``2 f sin(dt / 2)``, which is why the beat
period grows without bound as the angle difference goes to zero — two plates
at nearly the same angle give a huge, very visible moiré.

★**Why this earns its place**: the prediction is available **before** any
screen is drawn, and :func:`halftone_screen` plus an FFT can measure the beat
out of the picture. Two independent routes to one number.

Returns a ``table``: ``period_px``, ``angle_deg``, ``freq_cycles_per_px``.

**Raises** ``ValueError``: non-positive ruling or pitch; two screens that are
identical in both ruling and angle (the difference vanishes — there is no
beat, and returning ``inf`` silently would be worse than saying so).

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_beats_fringes_and_screens](../../../../examples/poc_beats_fringes_and_screens.py) — `py -3.11 examples/poc_beats_fringes_and_screens.py`
- [poc_moire_screen](../../../../examples/poc_moire_screen.py) — `py -3.11 examples/poc_moire_screen.py`
- [poc_print_registration](../../../../examples/poc_print_registration.py) — `py -3.11 examples/poc_print_registration.py`

## 型が繋がる次の op(`table` を入力に取れる)

[gcode_write](../gcode/gcode_write.md) · [gcode_extrusion_volume](../gcode/gcode_extrusion_volume.md) · [gcode_time_estimate](../gcode/gcode_time_estimate.md) · [gcode_layer_image](../gcode/gcode_layer_image.md) · [contours_to_gcode](../slice/contours_to_gcode.md)

## 同カテゴリ(`npr`)

[halftone_screen](halftone_screen.md) · [engrave_lines](engrave_lines.md) · [hatch_field](hatch_field.md) · [mosaic_tiles_sites](mosaic_tiles_sites.md) · [mosaic_tiles_render](mosaic_tiles_render.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
