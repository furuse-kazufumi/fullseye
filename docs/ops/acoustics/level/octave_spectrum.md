---
op: octave_spectrum
dim: acoustics
category: level
in: signal
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# octave_spectrum — ACOUSTICS `level` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import acoustics; acoustics.octave_spectrum(x, rate, fraction=3, f_min=22.0, f_max=None, ref=1.0, weighting='Z', floor_db=-200.0)` (または `opsacoustics.get("octave_spectrum")`)

## 使い方

Band levels in dB, summed over fractional-octave bands by Parseval.

Energy is accumulated from the single-sided periodogram into the bands
:func:`octave_bands` defines, so the band powers sum to the signal's
mean-square exactly (up to the bins outside the requested range). That
identity is the test: measured on 16384 samples of white noise at 16 kHz
over 22 Hz - 8 kHz at 1/3 octave, the band powers sum to **0.996367** of
``mean(x**2)`` while ``total_power`` (which counts every FFT bin) comes to
**1.000000** of it. The 0.36 % difference is exactly the bins outside the
requested range, and returning both numbers is what makes that visible
instead of leaving a reader to wonder where the energy went.

**The reference is explicit and there is no implicit 20 uPa.** ``ref`` is an
amplitude in the same units as the signal, and the default 1.0 means "dB
relative to one unit of whatever you passed in". This library never sees a
microphone calibration, so a number labelled dB SPL would be a fabrication;
pass ``ref=20e-6`` when the signal really is pascals and the result really is
dB SPL.

``weighting`` applies :func:`apply_weighting` first (``"Z"`` = none).

Returns a dict: ``centers``, ``nominal``, ``lower``, ``upper``, ``levels``
(dB), ``powers`` (mean-square), ``total_level``, ``total_power``,
``clamped`` (bool mask of bands floored at ``floor_db``), ``ref``,
``weighting``, ``fraction``, ``resolution_hz``, ``narrow_bands`` (how many
FFT bins landed in each band — a band with 0 or 1 is under-resolved and the
level is not trustworthy).

Measured exactness: a 1 kHz sine of amplitude 0.7 at 16 kHz over exactly
1000 periods, ``ref=1.0``, gives the 1 kHz band level
**-6.1083391564** dB against the closed form
``10*log10(0.7**2/2) = -6.1083391564`` dB — the difference is
**0.000e+00**. 25 of the 26 bands are at the floor, and ``total_level``
equals the band level to the digit shown, because there is nothing else in
the record.

**Raises** ``ValueError``: everything :func:`_as_signal` and
:func:`octave_bands` refuse, ``ref <= 0`` (a dB with a zero or negative
reference is not a number), an unknown ``weighting``, and an ``f_max`` above
Nyquist.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md)

## 同カテゴリ(`level`)

[octave_bands](octave_bands.md) · [weighting_response](weighting_response.md) · [apply_weighting](apply_weighting.md) · [equivalent_level](equivalent_level.md) · [percentile_level](percentile_level.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
