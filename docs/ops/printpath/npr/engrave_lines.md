---
op: engrave_lines
dim: printpath
category: npr
in: image2d
out: image2d
examples: [poc_beats_fringes_and_screens]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# engrave_lines — PRINTPATH `npr` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.engrave_lines(image, spacing_px=6.0, angle_deg=0.0, gamma=1.0, max_width=0.95)` (実装を直接呼ぶなら `import printpath; printpath.engrave_lines(image, spacing_px=6.0, angle_deg=0.0, gamma=1.0, max_width=0.95)`、台帳から引くなら `opsprintpath.get("engrave_lines")`)

## 使い方

Copperplate engraving — parallel lines whose **width** carries the tone.

★**Why this earns its place**: while the lines do not touch, the ink coverage
of a ruling of width ``w`` and spacing ``d`` is exactly ``w / d``. So the width
needed for a target tone is **solved, not tuned**: ``w = (1 - tone) * d``. The
op therefore has a closed form to be graded against — blur the result and the
local mean must come back to the tone you asked for.

Parameters
----------
image : 2-D array in [0, 1]
spacing_px : float
    Line spacing. The finest tone step a ruling can hold is ``1 / spacing``.
angle_deg : float
gamma : float
    Tone shaping applied before solving for the width (``tone**gamma``).
max_width : float
    Widest line as a fraction of the spacing; 1.0 would make solid black and
    lose the ruling.

Returns an ``image2d``: 1 = paper, 0 = ink.

**Raises** ``ValueError``: spacing below 2 px (the ruling cannot be sampled);
``max_width`` outside (0, 1]; non-positive gamma; a non-finite or oversized image.

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_beats_fringes_and_screens](../../../../examples/poc_beats_fringes_and_screens.py) — `py -3.11 examples/poc_beats_fringes_and_screens.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[stipple_points_from_image](../stroke/stipple_points_from_image.md) · [stipple_energy](../stroke/stipple_energy.md) · [stroke_tone_error](../stroke/stroke_tone_error.md) · [halftone_screen](halftone_screen.md) · [hatch_field](hatch_field.md) · [mosaic_tiles_sites](mosaic_tiles_sites.md) · [mosaic_tiles_render](mosaic_tiles_render.md) · [print_layer_defect_map](../inspect/print_layer_defect_map.md)

## 同カテゴリ(`npr`)

[halftone_screen](halftone_screen.md) · [halftone_moire_period](halftone_moire_period.md) · [hatch_field](hatch_field.md) · [mosaic_tiles_sites](mosaic_tiles_sites.md) · [mosaic_tiles_render](mosaic_tiles_render.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
