---
op: percentile_level
dim: acoustics
category: level
in: signal
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# percentile_level — ACOUSTICS `level` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import acoustics; acoustics.percentile_level(x, rate, percentiles=(10.0, 50.0, 90.0), weighting='A', ref=1.0, window_s=0.125, floor_db=-200.0)` (または `opsacoustics.get("percentile_level")`)

## 使い方

Statistical levels: ``L_N`` is the level exceeded ``N`` % of the time.

The record is cut into non-overlapping blocks of ``window_s`` seconds, each
block's equivalent level is computed, and ``L_N`` is the ``(100-N)``-th
percentile of those levels. Non-overlapping rectangular blocks are used
rather than an exponential time weighting because the block length is then
exactly what the caller asked for and the statistic is exactly a percentile
of the returned ``levels`` array — an exponential average would make the
effective averaging time a function of the signal.

Returns a dict with one key per requested percentile (``"L10"``, ``"L50"``,
``"L90"``, formatted with ``%g``), plus ``levels`` (the per-block levels),
``times`` (block start times, s), ``n_blocks``, ``block_samples``,
``leq`` (the energy-equivalent level of the whole record), ``ref``,
``weighting``.

Note that ``L50`` is the *median* level and ``leq`` is the *energy* level;
they are different numbers whenever the signal is not stationary, and the
gap between them is itself the usual measure of how fluctuating a record is.

Measured on a two-level test signal (1 s at 16 kHz, first half a 1 kHz sine
of amplitude 1.0, second half the same at 0.1, Z-weighted, 0.125 s blocks,
8 blocks): ``L10 = -3.010300`` and ``L90 = -23.010300`` dB — exactly the two
constituent levels, **20.000000** dB apart, as they must be for a 50/50
split. ``L50 = -13.010300`` is the interpolated midpoint of the two clusters
and ``leq = -5.977386``, which is 17 dB above ``L90``: the energy level sits
near the loud half while the median sits between them. On a
constant-amplitude signal all three percentiles and ``leq`` agree to
3.6e-15 dB.

**Raises** ``ValueError``: everything :func:`_as_signal` refuses, a
percentile outside ``[0, 100]``, a non-positive ``window_s``, a ``window_s``
longer than the record (which would give one block and make every percentile
the same number while still looking like a statistic), ``ref <= 0``.

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

[octave_bands](octave_bands.md) · [octave_spectrum](octave_spectrum.md) · [weighting_response](weighting_response.md) · [apply_weighting](apply_weighting.md) · [equivalent_level](equivalent_level.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
