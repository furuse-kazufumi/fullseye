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
- **呼び出し**: `import acoustics; acoustics.equivalent_level(x, rate, weighting='A', ref=1.0, floor_db=-200.0)` (または `opsacoustics.get("equivalent_level")`)

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

**Raises** ``ValueError``: everything :func:`_as_signal` refuses, an unknown
``weighting``, ``ref <= 0`` (a decibel needs a positive reference; a zero
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
