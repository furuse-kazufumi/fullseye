---
op: equivalent_level
dim: acoustics
category: level
in: signal
out: measurement
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# equivalent_level — ACOUSTICS `level` op

- **データ種**: `signal` → `measurement`
- **呼び出し**: `import acoustics; acoustics.equivalent_level(x, rate, weighting='A', ref=1.0, floor_db=-200.0, window='none')` (または `opsacoustics.get("equivalent_level")`)

## 使い方

The energy-equivalent level of a record, in dB relative to ``ref``.

``L_eq = 10 log10(mean(x_w**2) / ref**2)`` where ``x_w`` is the signal after
the chosen weighting. Returns a plain float.

**The reference is yours to supply.** The default ``ref=1.0`` means dB
relative to one unit of the signal's own units; it is not dB SPL, because
this library never sees your calibration. Pass ``ref=20e-6`` for pascals.

Measured: a 1 kHz sine of amplitude 1.0 at 16 kHz over exactly 1000 periods
gives ``L_eq = -3.010300`` dB with Z weighting, against the closed form
``10*log10(1/2) = -3.010300`` (difference 2.2e-15 dB), and the **same** value
under A weighting (difference 8.9e-16 dB), because A is 0 dB at 1 kHz.
Doubling the amplitude adds 6.020600 dB. Silence returns -200.0.

Silence returns ``floor_db`` (default -200) rather than ``-inf``; an ``-inf``
in a list of levels destroys every average taken over it afterwards.

**A weighted level is only as good as the weighting, and the weighting has a
leakage limit this operator inherits in full.** A pure tone that is not a
whole number of periods in the record comes back **too loud** — measured
**+7.7986 dB** at 31.5 Hz (a nominal one-third-octave centre) over 0.5 s at
48 kHz, and up to **+17.2116 dB** at 20.5 Hz — with no exception, no NaN and
no warning. ``weighting="Z"`` is exempt (it does no filtering) and ``"C"`` is
nearly so (+0.0493 dB on the same tone); it is ``"A"``, whose curve spans
about 40 dB across the audio band, that is exposed.

``window="hann"`` is the opt-in remedy: the record is multiplied by a Hann
window and the mean square divided by the window's own mean square, which
suppresses the leakage almost entirely — the 31.5 Hz error goes from
**+7.7986** to **+0.0534** dB and the 20.5 Hz error from **+17.2116** to
**+0.1841** — while costing about **0.15 dB** on records that were exact
before. It is **not** the default, and must not be used when a transient's
level is the point: a window makes the answer depend on *where in the
record the sound happened*. Measured on a 50 ms burst inside a 0.5 s record
(Z weighting, so only the window acts; unwindowed all three are -13.0103 dB
as they must be): at the start **-36.0587**, at the centre **-8.8218**, at
the end **-36.0587** — a 27 dB spread produced by nothing but position.
Use ``"hann"`` for a stationary tonal record, which is exactly the case the
leakage ruins, and ``"none"`` (the default, an honest energy average) for
everything else. The full measurement is in :func:`apply_weighting`.

**Raises** ``ValueError``: everything :func:`_as_signal` refuses, an unknown
``weighting`` or ``window``, ``ref <= 0`` (a decibel needs a positive reference; a zero
reference makes every level ``+inf`` and a negative one makes the ratio
negative), ``rate <= 0``.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`level`)

[octave_bands](octave_bands.md) · [octave_spectrum](octave_spectrum.md) · [weighting_response](weighting_response.md) · [apply_weighting](apply_weighting.md) · [percentile_level](percentile_level.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
