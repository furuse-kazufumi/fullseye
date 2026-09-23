---
op: mosaic_tiles_sites
dim: printpath
category: npr
in: image2d
out: pairs
examples: [poc_beats_fringes_and_screens]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# mosaic_tiles_sites — PRINTPATH `npr` op

- **データ種**: `image2d` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.mosaic_tiles_sites(image, n_tiles=400, iterations=12, seed=0, weighted=True)` (実装を直接呼ぶなら `import printpath; printpath.mosaic_tiles_sites(image, n_tiles=400, iterations=12, seed=0, weighted=True)`、台帳から引くなら `opsprintpath.get("mosaic_tiles_sites")`)

## 使い方

Lloyd's iteration on an image — the tile centres of a mosaic.

Places *n_tiles* sites and moves each to the centroid of the pixels it owns,
weighted by local contrast when *weighted* (so detail gets smaller tiles).

★**Why this earns its place**: Lloyd's iteration is a **descent** — the
quantisation energy cannot increase — and that is a property of the algorithm,
not of the picture. The energy is *not* reported here on purpose: the existing
``stipple_energy`` measures it from the sites, so the monotonicity can be
checked by an op that did not produce them. Measuring your own descent with
your own number proves nothing.

Returns ``pairs``: the site coordinates (row, col).

**Raises** ``ValueError``: fewer than 4 tiles or more tiles than pixels;
negative iterations; a non-finite or oversized image.

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_beats_fringes_and_screens](../../../../examples/poc_beats_fringes_and_screens.py) — `py -3.11 examples/poc_beats_fringes_and_screens.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[stipple_energy](../stroke/stipple_energy.md) · [stroke_tour_closed](../stroke/stroke_tour_closed.md) · [mst_length](../stroke/mst_length.md) · [stroke_resample_closed](../stroke/stroke_resample_closed.md) · [stroke_tone_error](../stroke/stroke_tone_error.md) · [mosaic_tiles_render](mosaic_tiles_render.md)

## 同カテゴリ(`npr`)

[halftone_screen](halftone_screen.md) · [halftone_moire_period](halftone_moire_period.md) · [engrave_lines](engrave_lines.md) · [hatch_field](hatch_field.md) · [mosaic_tiles_render](mosaic_tiles_render.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
