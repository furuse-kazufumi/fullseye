---
op: fmcw_design
dim: rangedoppler
category: design
in: 
out: table
examples: [fmcw_range_doppler]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# fmcw_design — RANGEDOPPLER `design` op

- **データ種**: `` → `table`
- **呼び出し**: `import rangedoppler; rangedoppler.fmcw_design(n_samples=64, n_chirps=32, sample_rate_hz=10000000.0, slope_hz_per_s=20000000000000.0, chirp_period_s=5e-05, wavelength_m=0.0038934, n_antennas=1, element_spacing_m=None)` (または `opsrangedoppler.get("fmcw_design")`)

## 使い方

Bin widths, resolutions and aliasing limits of an FMCW configuration.

The paper answer to "will this waveform see what I care about?", with no data
and no simulation — the stance :mod:`visiondesign` takes for optics. Every
number is closed form:

==============================  ============================================
quantity                        formula
==============================  ============================================
swept bandwidth                 ``B = S * N_s / f_s``
range bin / resolution          ``dR = c / (2B) = c*f_s / (2*S*N_s)``
max unambiguous range           ``R_max = c*f_s / (2S)`` (``= N_s * dR``)
beat frequency per metre        ``2S/c``
velocity bin / resolution       ``dv = lambda / (2*N_c*T_c)``
max unambiguous velocity        ``v_max = lambda / (4*T_c)`` (``= N_c*dv/2``)
Doppler phase per (m/s)         ``4*pi*T_c / lambda`` rad per chirp
coherent processing interval    ``N_c * T_c``
max unambiguous angle           ``asin(lambda / (2d))``
angular resolution (boresight)  ``0.886 * lambda / (N_a * d)``
==============================  ============================================

The two "max" figures are **hard aliasing limits**, and they are the same
numbers :func:`fmcw_beat_simulate` refuses to cross. The angular resolution
is the 3 dB beamwidth of a uniform linear array at boresight (Van Trees 2002,
§2.4); it widens as ``1/cos(theta)`` off boresight, which this does not report
because it is a function, not a number.

``cube_elements`` and ``cube_mebibytes`` are included because "small input,
huge allocation" is the failure mode of this family: the cube grows as
``N_a * N_c * N_s`` and complex128 is 16 bytes a sample.

Returns a ``dict``. Raises ``ValueError`` on a non-positive or non-finite
parameter, a wavelength over :data:`MAX_WAVELENGTH_M`, or a count outside its
cap.

>>> d = fmcw_design()
>>> round(d["range_bin_m"], 6), round(d["max_unambiguous_velocity_ms"], 6)
(1.171064, 19.467)

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

## 同カテゴリ(`design`)

—

---
*Provenance: rangedoppler.py — RANGEDOPPLER operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
