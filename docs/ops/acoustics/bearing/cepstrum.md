---
op: cepstrum
dim: acoustics
category: bearing
in: signal
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cepstrum — ACOUSTICS `bearing` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import acoustics; acoustics.cepstrum(x, rate, mode='real', floor_ratio=1e-12, min_quefrency=0.0)` (または `opsacoustics.get("cepstrum")`)

## 使い方

The spectrum of the log spectrum — periodic structure *in frequency*.

A harmonic family or a family of modulation sidebands is periodic along the
frequency axis, so it collapses to a single line along the cepstrum's
quefrency axis (in seconds). Two things this finds that a spectrum does not:
an **echo** at delay ``tau`` (a rahmonic at ``q = tau``) and a **sideband
family** spaced ``df`` apart (a rahmonic at ``q = 1/df``). The second is the
bearing case — sidebands around a gear mesh spaced at the shaft rate.

``mode``:

* ``"real"`` — ``irfft(log|X|)``, the standard real cepstrum. Discards phase,
  so it cannot be inverted; nothing here pretends otherwise.
* ``"power"`` — ``irfft(log|X|**2) = 2 * real``, kept because the two
  conventions differ by exactly a factor of two and mixing them silently
  halves or doubles every amplitude a caller compares against a reference.

``log(0)`` is handled by flooring the magnitude at ``floor_ratio`` times its
own maximum (default 1e-12, i.e. -240 dB) rather than letting ``-inf`` enter
the inverse transform, where it would make the entire cepstrum NaN. The
number of floored bins is returned as ``floored_bins`` — a large count means
the signal is band-limited and the cepstrum is dominated by the flooring, not
by the signal.

``min_quefrency`` (seconds) excludes the low-quefrency region from the peak
search. This is not cosmetic. The first few bins carry the **spectral
envelope** — the overall shape of the spectrum, which is large and has
nothing to do with periodic structure — and they dominate. Measured on an AM
tone with sidebands 50 Hz apart, the five largest cepstral values sit at
0.000125, 0.00025, 0.000375, 0.000625 and 0.001 s, i.e. all of them are the
envelope, and the default peak search returns 0.000125 s rather than the
1/50 = 0.02 s a reader would expect. Excluding the envelope is the standard
practice ("liftering") and is the caller's decision, so it is an argument
with a visible default of 0.

Returns a dict: ``quefrency`` (s), ``cepstrum``, ``rate``, ``mode``,
``floored_bins``, ``min_quefrency``, ``peak_quefrency``, ``peak_amplitude``,
``peak_rate_hz`` (``1/peak_quefrency`` — the sideband spacing or repetition
rate the rahmonic corresponds to). The peak is taken over
``min_quefrency < q < n/(2*rate)``; the cepstrum is symmetric past that.

Measured ground truths:

* **Echo.** White noise at 8 kHz plus 0.6 times itself delayed by 200
  samples: ``peak_quefrency = 0.025000`` s, peak index exactly **200**, and
  ``floored_bins = 0``.
* **A periodic family of lines.** A 50 Hz impulse train convolved with a
  random 64-tap FIR (so the spectrum is broadband with lines every 50 Hz):
  peak at ``0.020000`` s = **50.00 Hz** exactly, with
  ``min_quefrency=0.002``.
* **What it looks like when the fundamental is not the largest.** The
  ``mode="impulse"`` bearing signal repeats every 1/107 s, and the largest
  rahmonic above 2 ms is at 0.037383 s — which is ``4/107``, the *fourth*
  rahmonic, not the first. A cepstrum reports a **family**, and reading only
  its maximum gives an answer that is off by an exact integer factor and
  looks entirely reasonable.
* **Where it stops working.** An AM tone has three spectral lines and
  nothing else; every other bin is floored, the log spectrum is mostly the
  floor, and there is no 1/50 s rahmonic to find at all. Cepstral sideband
  analysis needs a *broadband* signal — a gear mesh, not a tone.

``mode="power"`` is exactly twice ``mode="real"`` (measured max difference
0.000e+00).

**Raises** ``ValueError``: everything :func:`_as_signal` refuses, an unknown
``mode``, ``floor_ratio`` outside ``(0, 1)``, a negative ``min_quefrency``, a
``min_quefrency`` at or past the half-length of the record (nothing would be
left to search), an identically zero signal, and a signal shorter than 4
samples.

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

## 同カテゴリ(`bearing`)

[envelope_spectrum](envelope_spectrum.md) · [bearing_defect_frequencies](bearing_defect_frequencies.md) · [spectral_kurtosis](spectral_kurtosis.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
