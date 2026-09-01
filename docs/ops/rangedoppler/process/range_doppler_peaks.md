---
op: range_doppler_peaks
dim: rangedoppler
category: process
in: image2d
out: table
examples: [fmcw_range_doppler]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# range_doppler_peaks — RANGEDOPPLER `process` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import rangedoppler; rangedoppler.range_doppler_peaks(rdmap, range_bin_m=1.0, velocity_bin_ms=1.0, n_peaks=1, min_fraction=0.1, doppler_shifted=True)` (または `opsrangedoppler.get("range_doppler_peaks")`)

## 使い方

Detections from a range-Doppler map: bin indices back to metres and m/s.

Finds strict local maxima of the 2-D magnitude map — greater than all eight
neighbours, **cyclically** along the Doppler axis (velocity really is
periodic in the FFT: the fastest receding bin is adjacent to the fastest
approaching one) and **openly** along the range axis (a cell in the first or
last range bin competes only against the neighbours that exist, so a target
in the last bin is a detection, not a discard) — keeps those at least
*min_fraction* of the global maximum, and returns the strongest *n_peaks*.

Range bin 0 is reported like any other. In a real receiver it is the
transmitter-leakage / DC bin rather than a target, but suppressing it here
would be a silent policy applied to somebody else's data; threshold it
yourself if you want it gone.

Index -> physical value, closed form and the exact inverse of
:func:`fmcw_beat_simulate`:

  * ``range_m = j * range_bin_m``, with ``range_bin_m = c*f_s/(2*S*N_s)``
    from :func:`fmcw_design`;
  * ``velocity_ms = (i - n_doppler//2) * velocity_bin_ms`` when
    *doppler_shifted* (the layout :func:`range_doppler_map` produces), or
    ``i`` wrapped into ``[-N_c/2, N_c/2)`` when the map is unshifted.

The bin widths are **required parameters with placeholder defaults of 1.0**,
which means the default output is in bins, not metres. That is deliberate:
inventing a default waveform here would let a caller read metres off a map
that was never that waveform's.

Returns a ``dict`` with ``peaks`` (a list of per-detection dicts holding
``range_m``, ``velocity_ms``, ``magnitude``, ``range_bin``, ``doppler_bin``),
``n_found``, ``max_magnitude`` and ``noise_floor`` (the median of the map).

**Raises** ``ValueError``: a non-2-D, complex, negative, or non-finite map; a
map whose maximum is 0 (an all-zero map has no cell to detect and returning
cell (0,0) — which is what ``argmax`` does — would be a fabricated
detection); a non-positive bin width; *n_peaks* < 1; a *min_fraction*
outside ``[0, 1]``.

## 詳しい使い方ガイド

- [fmcw_range_doppler ファミリ ガイド](../guides/fmcw_range_doppler.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fmcw_range_doppler](../../../../examples/fmcw_range_doppler.py) — `py -3.11 examples/fmcw_range_doppler.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`process`)

[fmcw_window_apply](fmcw_window_apply.md) · [range_doppler_map](range_doppler_map.md) · [fmcw_range_profile](fmcw_range_profile.md)

---
*Provenance: rangedoppler.py — RANGEDOPPLER operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
