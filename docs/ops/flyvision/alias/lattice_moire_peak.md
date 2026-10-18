---
op: lattice_moire_peak
dim: flyvision
category: alias
in: signal × table
out: table
examples: [poc_moire_screen, poc_print_registration, poc_zebra_stripes_fly_eye]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# lattice_moire_peak — FLYVISION `alias` op

- **データ種**: `signal × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lattice_moire_peak(signal, lattice, fmax_cycles_per_deg=0.0, n_freq=48, window='hann')` (実装を直接呼ぶなら `import flyvision; flyvision.lattice_moire_peak(signal, lattice, fmax_cycles_per_deg=0.0, n_freq=48, window='hann')`、台帳から引くなら `opsflyvision.get("lattice_moire_peak")`)

## 使い方

How sharp the strongest low-frequency component of a sampled signal is —
the moire a lattice makes of a texture it cannot resolve.

Sampling a texture above the lattice's Nyquist limit does not lose it; it
folds it to a lower frequency. On a regular lattice the fold is a single
sharp peak — a false stripe the next stage reads as a real one — and on an
irregular arrangement the same energy spreads into a ring. This op measures
that difference as a number: the non-uniform discrete Fourier transform of
the ommatidial signal (mean removed, radially windowed) at the gnomonic
positions of the ommatidia, over a grid of ``n_freq x n_freq`` frequencies
up to *fmax_cycles_per_deg* (``0`` = the lattice's own hexagonal Nyquist
``1/(sqrt 3 dphi)``, the band the eye can represent), and the ratio of the
highest amplitude on that grid to the median amplitude.

signal:  ``(n,)`` ommatidial values (:func:`fly_view_plane_texture`).
lattice: the eye they were sampled on — any geometry; only directions are used.
fmax_cycles_per_deg: the half-width of the frequency grid, cycles/degree.
n_freq:  grid side, ``8 <= n_freq <= MAX_MOIRE_FREQ``.
window:  one of :data:`MOIRE_WINDOWS` — a radial Hann taper over the field
         (default: the field edge is a step and would leak everywhere).

Returns a dict ``{"peak_ratio", "peak_cycles_per_deg", "peak_amplitude",
"background_median", "nyquist_cycles_per_deg", "n_freq"}``.

Ground truth (pinned in the tests): a sinusoid just below Nyquist sampled on
the hexagonal eye gives a peak ratio above 30; the same sinusoid on a Vogel
eye of the same count and mean spacing gives a peak ratio at least 2.5x
smaller — the energy that was one peak is now a ring.

**Raises** ``ValueError``: a *signal* that is not ``(n,)`` for this lattice
(an empty *signal* is refused), non-finite entries, a constant signal (there
is no spectrum to rank — its ratio would be 0/0), a negative *fmax*, an
*n_freq* outside its range, an unknown *window*, and a malformed *lattice*.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_moire_screen](../../../../examples/poc_moire_screen.py) — `py -3.11 examples/poc_moire_screen.py`
- [poc_print_registration](../../../../examples/poc_print_registration.py) — `py -3.11 examples/poc_print_registration.py`
- [poc_zebra_stripes_fly_eye](../../../../examples/poc_zebra_stripes_fly_eye.py) — `py -3.11 examples/poc_zebra_stripes_fly_eye.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_matched_filter](../selfmotion/fly_matched_filter.md) · [fly_egomotion_from_flow](../selfmotion/fly_egomotion_from_flow.md) · [fly_eye_merge](../selfmotion/fly_eye_merge.md) · [fly_view_plane_texture](../stimulus/fly_view_plane_texture.md) · [fly_hex_resample](../sample/fly_hex_resample.md) · [fly_expansion_readout](../looming/fly_expansion_readout.md)

## 同カテゴリ(`alias`)

[sampling_alias_distance](sampling_alias_distance.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
