---
op: point_spectrum
dim: oned
category: signal
in: positions
out: table
examples: [poc_web_roll_periodicity]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# point_spectrum — ONED `signal` op

- **データ種**: `positions` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.point_spectrum(positions, extent=None, n_freq=2048, f_max=None, method='direct', weights=None, bins_per_period=8)` (実装を直接呼ぶなら `import dsp; dsp.point_spectrum(positions, extent=None, n_freq=2048, f_max=None, method='direct', weights=None, bins_per_period=8)`、台帳から引くなら `ops1d.get("point_spectrum")`)

## 使い方

Periodogram of **event positions** — defects, impacts, counts, arrivals.

:func:`spectrum` needs an evenly sampled signal, but a great deal of
industrial data arrives as a *list of positions*: where each defect was on
the web, when each particle was counted, at what angle each dent sits. The
usual workaround is to histogram the positions and FFT the histogram, which
works but hides two choices — bin width and record length — that decide the
answer. This operator makes both explicit and returns them.

*method* picks the estimator:

``"direct"``
    the point-process (Bartlett) periodogram
    ``|sum_j w_j exp(-2 pi i f x_j) - rate * integral|^2 / sum_j w_j``,
    evaluated at each requested frequency. **No binning at all**, so no bin
    width to choose and no aliasing from one. The subtracted term is the
    contribution a *uniform* process of the same rate would make; without it
    every spectrum peaks at f -> 0 simply because events exist.
``"binned"``
    histogram the positions, then ``rfft``, with the bin width set so the
    finest frequency asked for still gets ``bins_per_period`` samples per
    cycle. Cheaper for very many events, and the result is what a
    histogram-and-FFT pipeline would have produced.

**The frequency resolution is a property of the record, not of the method.**
Two periods closer than ``1/extent`` apart cannot be told apart by either
estimator, and the returned dict says so in ``resolution``: read it before
reading a peak, not after.

**A periodic train of events is a comb, not a line.** Its harmonics at
``k/period`` are as tall as the fundamental, so ``argmax`` of this spectrum
routinely returns ``period/k`` rather than the period. Measured on 93 events
(43 spaced 471.24 apart with 1.5 of jitter, plus 50 uniformly random) over a
record of 20000: the global maximum lands on ``58.90`` with ``direct`` (the
8th harmonic) and ``52.35`` with ``binned`` (the 9th), while the fundamental
is present and prominent in both — ``direct`` puts 0.947 of the maximum
power at ``1/471.24``, ``binned`` 0.379. Take the lowest frequency whose
first few harmonics *all* stand, rather than the tallest line — see
``examples/poc_web_roll_periodicity.py``, which is what this operator was
added for.

Returns a dict: ``freq`` (cycles per unit of *positions*), ``power``,
``resolution`` (``1/extent``), ``extent``, ``n_events``, ``method``, and
``bin_width`` (``None`` for ``"direct"``).

Fail-closed: fewer than two events raises ``ValueError`` — a periodogram of
one point is not a weak measurement, it is not a measurement.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_web_roll_periodicity](../../../../examples/poc_web_roll_periodicity.py) — `py -3.11 examples/poc_web_roll_periodicity.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [resample](resample.md) · [spectrum](spectrum.md) · [spectrogram](spectrogram.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
