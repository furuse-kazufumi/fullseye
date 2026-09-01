---
op: envelope_spectrum
dim: acoustics
category: bearing
in: signal
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# envelope_spectrum — ACOUSTICS `bearing` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import acoustics; acoustics.envelope_spectrum(x, rate, low, high, order=4, n_peaks=5)` (または `opsacoustics.get("envelope_spectrum")`)

## 使い方

Band-pass, demodulate, transform — where a bearing defect actually shows.

The three steps are each already available (``dsp.bandpass``,
``dsp.envelope``, ``numpy.fft``); what is not available anywhere in
:mod:`dsp` is the *composition*, and the composition is the diagnostic. The
raw spectrum of a defective bearing shows a resonance at some kHz and
nothing at the defect rate; the envelope of that resonance band, transformed,
shows the defect rate as a clean line.

``low`` / ``high`` are the demodulation band in Hz and are **required**,
not optional. Choosing the band is the analysis; a default would hide the
one decision that has to be made. :func:`spectral_kurtosis` finds a
candidate band when there is no prior knowledge of the resonance.

The envelope's mean is removed before the transform (otherwise a large DC
line dominates every plot), amplitudes are single-sided (``2/N``), and DC is
excluded from peak picking.

Returns a dict: ``freqs``, ``magnitude``, ``peak_freq``, ``peak_amplitude``,
``peak_freqs`` / ``peak_amplitudes`` (the ``n_peaks`` largest, descending),
``band``, ``envelope_mean``, ``resolution_hz``, plus two numbers that exist
because **this operator always returns a peak frequency, including when
there is nothing there**:

``peak_prominence``
    the peak divided by the median of the magnitude spectrum.
``band_fraction``
    the RMS of the band-passed signal divided by the RMS of the input — how
    much of the record actually lives in the demodulation band.

Found by adversarial audit and not repaired by an exception, because there
is nothing invalid to refuse: a **constant** signal band-passed over
100-2000 Hz has an envelope made of rounding error, and this operator dutifully
reported ``peak_freq = 8.0000 Hz``. Nothing raised, nothing was NaN, and
``8 Hz`` is a perfectly plausible number to write down. Measured, the four
cases separate on the returned numbers rather than on any invented
threshold:

================  ========  =========  ===========  =============
input             peak Hz   peak amp   prominence   band_fraction
================  ========  =========  ===========  =============
AM, defect 107    107.0000  4.997e-01     10018.6      9.999e-01
impulse + noise   107.0000  1.968e-01      9384.7      9.201e-01
white noise       128.0000  2.785e-02        365.2     3.745e-01
constant signal     8.0000  1.691e-12        173.0     1.995e-12
================  ========  =========  ===========  =============

No cut-off is imposed here: a defect that is genuinely 20 dB into the noise
is a real finding and refusing it would be worse than reporting it. The
numbers are returned so the caller can see the difference between row 1 and
row 4, which ``peak_freq`` alone does not show.

Measured on :func:`synthesize_bearing_signal` (25600 Hz, 1 s, 3 kHz carrier,
107 Hz defect, ``m = 0.5``) demodulated over 2000-4000 Hz: ``peak_freq =
107.000000`` Hz, ``peak_amplitude = 0.499677`` — the modulation depth
itself, because the analytic envelope of that signal is exactly
``1 + 0.5 cos(2 pi 107 t)``. The ordinary spectrum of the same signal has a
one-sided amplitude of **4.291662e-16** at 107 Hz: the defect rate is not
present as a frequency component at all, which is the entire point of the
operator.

**That number needs a scaling step that used to be missing from this
sentence.** ``dsp.spectrum`` returns the raw ``|rfft|``, not an amplitude —
the raw value in that bin is **5.493328e-12**, and the one-sided amplitude
above is ``mag * (2.0 / len(x))``, here ``2/25600 = 7.8125e-05``. This
operator and :func:`order_spectrum` apply that ``2/N`` *internally* and so
return amplitudes directly (carrier 3000 Hz: raw 12800, amplitude
1.000000; sidebands 2893 / 3107 Hz: raw 3200, amplitude 0.250000 = m/2).
The two conventions coexist in the library, so do not apply ``2/N`` twice
when comparing a ``dsp`` spectrum against one of these.

**Raises** ``ValueError``: everything :func:`_as_signal` and ``dsp.bandpass``
refuse (non-finite, complex, masked, non-1-D, a band edge outside
``(0, rate/2)``, a signal too short for zero-phase filtering), plus a
non-positive ``n_peaks``.

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

[bearing_defect_frequencies](bearing_defect_frequencies.md) · [spectral_kurtosis](spectral_kurtosis.md) · [cepstrum](cepstrum.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
