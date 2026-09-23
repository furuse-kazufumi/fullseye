---
op: mosaic_tiles_render
dim: printpath
category: npr
in: image2d × pairs
out: image2d
examples: [poc_beats_fringes_and_screens]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# mosaic_tiles_render — PRINTPATH `npr` op

- **データ種**: `image2d × pairs` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.mosaic_tiles_render(image, sites)` (実装を直接呼ぶなら `import printpath; printpath.mosaic_tiles_render(image, sites)`、台帳から引くなら `opsprintpath.get("mosaic_tiles_render")`)

## 使い方

Paint each Voronoi cell with the **mean** of the pixels it owns.

★**Why the mean and not something prettier**: for a fixed partition the mean
is the ``L2``-optimal constant — no other value lowers the squared error
inside the cell. The tile colour is therefore a solution, not a taste, and any
alternative can be *shown* to be worse by evaluating the same sum.

Returns an ``image2d``: the mosaic.

**Raises** ``ValueError``: sites not (N, 2) with N >= 1; sites outside the
image; a non-finite or oversized image.

Limits: cells are convex polygons, so this does not imitate the irregular
tesserae of real mosaic and never runs a single tile along an edge the way a
mosaicist would.

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_beats_fringes_and_screens](../../../../examples/poc_beats_fringes_and_screens.py) — `py -3.11 examples/poc_beats_fringes_and_screens.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[stipple_points_from_image](../stroke/stipple_points_from_image.md) · [stipple_energy](../stroke/stipple_energy.md) · [stroke_tone_error](../stroke/stroke_tone_error.md) · [halftone_screen](halftone_screen.md) · [engrave_lines](engrave_lines.md) · [hatch_field](hatch_field.md) · [mosaic_tiles_sites](mosaic_tiles_sites.md) · [print_layer_defect_map](../inspect/print_layer_defect_map.md)

## 同カテゴリ(`npr`)

[halftone_screen](halftone_screen.md) · [halftone_moire_period](halftone_moire_period.md) · [engrave_lines](engrave_lines.md) · [hatch_field](hatch_field.md) · [mosaic_tiles_sites](mosaic_tiles_sites.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
