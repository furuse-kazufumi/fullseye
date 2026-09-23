---
op: hatch_field
dim: printpath
category: npr
in: image2d
out: image2d
examples: [poc_beats_fringes_and_screens]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# hatch_field — PRINTPATH `npr` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.hatch_field(image, spacing_px=8.0, sigma=2.0, levels=3, cross_deg=90.0)` (実装を直接呼ぶなら `import printpath; printpath.hatch_field(image, spacing_px=8.0, sigma=2.0, levels=3, cross_deg=90.0)`、台帳から引くなら `opsprintpath.get("hatch_field")`)

## 使い方

Cross-hatching that **follows the picture** — direction from the structure tensor.

The stroke direction is the local structure orientation (the existing
``structure_tensor_orientation``: strokes run *along* edges, not across them),
and the number of superposed hatch layers comes from the tone — one layer for
a light grey, up to *levels* for a dark one, each rotated by *cross_deg*.

★**Why this earns its place**: the direction is checkable against a picture
whose orientation is known by construction (a sine grating at 30° must give
strokes at 30°), and the tone is checkable by blurring the result. The usual
NPR routine offers neither.

Returns an ``image2d``: 1 = paper, 0 = ink.

**Raises** ``ValueError``: spacing below 2 px; levels below 1; non-positive
sigma; a non-finite or oversized image.

Limits: a single orientation per pixel, so crossings and junctions (where the
structure tensor is isotropic) get an arbitrary but locally smooth direction —
the coherence, not the orientation, is what says whether to trust it.

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_beats_fringes_and_screens](../../../../examples/poc_beats_fringes_and_screens.py) — `py -3.11 examples/poc_beats_fringes_and_screens.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[stipple_points_from_image](../stroke/stipple_points_from_image.md) · [stipple_energy](../stroke/stipple_energy.md) · [stroke_tone_error](../stroke/stroke_tone_error.md) · [halftone_screen](halftone_screen.md) · [engrave_lines](engrave_lines.md) · [mosaic_tiles_sites](mosaic_tiles_sites.md) · [mosaic_tiles_render](mosaic_tiles_render.md) · [print_layer_defect_map](../inspect/print_layer_defect_map.md)

## 同カテゴリ(`npr`)

[halftone_screen](halftone_screen.md) · [halftone_moire_period](halftone_moire_period.md) · [engrave_lines](engrave_lines.md) · [mosaic_tiles_sites](mosaic_tiles_sites.md) · [mosaic_tiles_render](mosaic_tiles_render.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
