---
op: spectral_kurtosis
dim: acoustics
category: bearing
in: signal
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# spectral_kurtosis — ACOUSTICS `bearing` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import acoustics; acoustics.spectral_kurtosis(x, rate, win=None, hop=None, window='hann')` (または `opsacoustics.get("spectral_kurtosis")`)

## 使い方

Which frequency band is impulsive — i.e. where to demodulate.

:func:`envelope_spectrum` needs a band, and picking it by eye from a
spectrum picks the *loudest* band, which is usually a gear mesh or a line
harmonic rather than the bearing. Spectral kurtosis picks the *most
non-stationary* band instead: for each frequency bin it measures the
fourth-order behaviour of that bin's STFT coefficient across frames.

The normalisation is chosen so the two reference cases are exact:

* stationary **complex circular Gaussian** noise gives ``SK = 0``,
* a **pure tone** (constant magnitude in its bin) gives ``SK = -1``,
* a repetitive **transient** gives ``SK > 0``, and the larger it is the more
  concentrated in time the band's content is.

Measured over 8192 samples at 16 kHz at the default window (64, 509 interior
frames): white Gaussian noise gives a mean SK of **-0.0444** over the
interior bins, against the estimator's own standard deviation
``4/sqrt(509) = 0.1773``, so it is zero; and a 2 kHz tone gives **-1.0000**
in its bin. Both reference cases land on their closed forms.

**The answer is a band, and it depends on the window — measured, not
asserted.** The frame has to be *shorter than the gap between transients*,
or every frame contains one and the band looks perfectly stationary. On the
``mode="impulse"`` bearing signal (25.6 kHz, resonance 3000 Hz, impulses
every 9.35 ms, ring time constant 1.06 ms):

======  ==========  =======  ==========  =============
win     frame (ms)  max SK   at (Hz)     bin spacing
======  ==========  =======  ==========  =============
16      0.62        29.58    6400        1600 Hz
32      1.25        12.86    1600        800 Hz
64      2.50         5.38    2000        400 Hz
128     5.00         1.66    1600        200 Hz
256    10.00        -0.13   12200        100 Hz
======  ==========  =======  ==========  =============

The last row is the failure mode: at a 10 ms frame against a 9.35 ms impulse
spacing, every frame holds exactly one impulse, the band is stationary by
construction, and the operator reports a *negative* kurtosis at an unrelated
frequency. Nothing raises. So ``window_seconds`` is returned, to be compared
against the repetition period you expect, and sweeping ``win`` is part of
using this operator rather than an optimisation.

What survives the sweep is the *band*, not the bin. On the same signal with
``noise_sigma=0.05`` (the noiseless one is impulsive in every bin at once
and its top six bins differ by 0.03, which is itself worth knowing), the six
highest bins at ``win=64`` are 2000, 2400, 1600, 4000, 3600 and 1200 Hz —
bracketing the true 3000 Hz resonance without any of them being it. And that
is enough: feeding the band this operator returns straight into
:func:`envelope_spectrum` recovers the defect rate exactly — measured
**107.0000 Hz** from the 1600-2400 Hz band the operator chose by itself,
with no knowledge of the resonance.

**The band is returned, not left to the caller to assemble.** ``band_lo`` /
``band_hi`` are ``max_freq -+ bin_hz`` *clamped into the open interval*
``(0, rate/2)`` that :func:`envelope_spectrum` accepts, so
``envelope_spectrum(x, rate, sk["band_lo"], sk["band_hi"])`` is always a
legal call. Assembling the band by hand is not: ``freqs`` runs up to and
including Nyquist, so whenever the winning bin is the topmost interior one,
``max_freq + bin_hz`` lands exactly *on* Nyquist and ``envelope_spectrum``
refuses it — correctly, since no such band exists in the recording. Measured
on the ``mode="am"`` bearing signal (25600 Hz, 1 s, 3 kHz carrier, 107 Hz
defect, ``m = 0.5``), whose kurtosis maximum lands on the top interior bin
(12400 Hz, ``bin_hz`` 400):

===========================  =====================  ==============================
band handed to the consumer  value                  ``envelope_spectrum``
===========================  =====================  ==============================
``max_freq -+ bin_hz``       12000.0 - 12800.0 Hz   ``ValueError`` (12800 = Nyquist)
``band_lo`` / ``band_hi``    12000.0 - 12600.0 Hz   returns
===========================  =====================  ==============================

Returning is not the same as finding something, and this row is the honest
case: ``max_kurtosis`` is **-0.2725** against ``noise_sigma`` **0.1001**, so
there was never a band to find — an amplitude-modulated tone is stationary in
every bin, which is exactly what a negative SK says. Demodulating the band
anyway gives ``peak_freq`` **1.0000** Hz at ``band_fraction``
**5.080e-05**: nothing lives up there, and the returned diagnostics say so.
(The same signal over the known resonance, 2000-4000 Hz, gives ``peak_freq``
**107.0000** at ``band_fraction`` **0.9999**.) The contract this repair adds
is only that the handoff is *legal* — refusing to answer a well-posed call is
the caller's bug to hit, whereas judging the answer stays with
``max_kurtosis`` / ``noise_sigma`` / ``band_fraction``.

The clamp margin is **half a bin**: an edge cannot be placed more finely than
``bin_hz`` in the first place, and half a bin is the smallest offset that is
still a resolvable distance from the boundary — no epsilon, no rate-dependent
fudge. ``band_lo < band_hi`` always holds, because ``max_freq`` is by
construction an interior bin and therefore at least one full bin away from
both 0 and Nyquist.

``win`` defaults to the largest power of two that leaves at least 8 interior
frames, clamped to [16, 64] — short, for the reason in the table — and the
value used is returned. Fewer than 8 interior frames makes the fourth moment
meaningless and is refused.

DC and Nyquist bins are excluded from ``max_kurtosis`` / ``max_freq``: their
STFT coefficients are real, not complex circular, so the -2 normalisation is
the wrong one there and they read about -1 for noise. They are still present
in ``kurtosis`` with the same formula, and ``real_bins`` names them.

Returns a dict: ``freqs``, ``kurtosis``, ``max_kurtosis``, ``max_freq``,
``band_lo``, ``band_hi`` (the demodulation band, ready for
:func:`envelope_spectrum`), ``n_frames``, ``win``, ``hop``, ``real_bins``,
``window_seconds``, ``bin_hz``, ``noise_sigma`` (the estimator's own standard
deviation, ``4/sqrt(n_frames)`` — a peak below this is not a finding).

**Raises** ``ValueError``: everything :func:`stft` refuses, plus a signal too
short for 8 frames at the chosen window.

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

[envelope_spectrum](envelope_spectrum.md) · [bearing_defect_frequencies](bearing_defect_frequencies.md) · [cepstrum](cepstrum.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
