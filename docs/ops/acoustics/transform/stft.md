---
op: stft
dim: acoustics
category: transform
in: signal
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# stft — ACOUSTICS `transform` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import acoustics; acoustics.stft(x, rate, win=256, hop=None, window='hann', nfft=None, scaling='none')` (または `opsacoustics.get("stft")`)

## 使い方

Short-time Fourier transform that keeps the phase and can be inverted.

:func:`dsp.spectrogram` returns magnitudes, which is all a display needs and
strictly less than an analysis needs: a magnitude spectrogram cannot be
turned back into a signal, so there is no path in :mod:`dsp` that filters or
modifies a signal in the time-frequency plane and comes back. This is that
path, and the test of it is that the round trip is exact.

Returns a dict (the transform plus everything :func:`istft` needs to undo
it):

``spectra``
    complex128 ``(n_freqs, n_frames)``, same orientation as
    :func:`dsp.spectrogram`.
``freqs``, ``times``
    bin centre frequencies in Hz and frame start times in seconds. Frame
    time 0.0 is the first *original* sample, so the leading pad does not
    shift the time axis.
``rate``, ``win``, ``hop``, ``nfft``, ``length``, ``pad_left``, ``scale``,
``scaling``, ``window``, ``window_values``
    the geometry, kept so the inverse needs no arguments.
``nola_min``
    the smallest value of the squared-window overlap sum over the original
    samples. Reconstruction divides by this sum, so a value of zero means
    some sample is not reconstructible; it is refused up front rather than
    producing a hole.
``interior``
    boolean mask over frames, true for the frames that lie **entirely inside
    the original signal**. The transform pads by a full window at each end so
    that inversion is exact, and the frames straddling that pad see part
    zeros — they are correct as coefficients but they are not representative,
    and any statistic averaged over *all* frames is therefore biased low.
    Measured on 16384 samples of unit-variance white noise, win = 1024,
    hop = 512: the ``"density"`` spectrum integrates to 0.9073 over all 35
    frames and to 0.9933 over the 31 interior ones (the signal's own variance
    is 0.9923). :func:`spectral_kurtosis` uses this mask for exactly that
    reason — a half-empty frame looks impulsive.

**Normalisation is explicit**, because a windowed spectrum has no single
natural amplitude and a plausible-looking dB number is the usual result of
leaving it implicit. ``scaling`` selects a real factor applied to every
coefficient, recorded as ``scale`` and divided out again by :func:`istft`:

* ``"none"`` (default) — the raw ``rfft`` of the windowed frame.
* ``"amplitude"`` — ``2 / sum(w)``. A sinusoid of amplitude ``A`` sitting on
  a bin centre then reads ``|Z| = A``. Measured on a 1 kHz, amplitude-0.7
  tone at 16 kHz with a 256-sample periodic Hann, over the interior frames:
  ``|Z|`` ranges 0.699999999999999 to 0.700000000000001.
  DC and Nyquist read twice their amplitude under this convention (they are
  not two-sided), which is the standard caveat and is not corrected for.
* ``"density"`` — ``sqrt(2 / (rate * sum(w**2)))``, so ``|Z|**2`` is a
  single-sided power spectral density in units^2/Hz. Measured on 16384
  samples of white noise at 16 kHz (win 1024, hop 512): the PSD integrates
  to 0.9933 over the interior frames against the record's own variance
  0.9923, and to 0.9073 if the pad frames are included — see ``interior``.

**Raises** ``ValueError``: non-1-D / non-finite / complex / masked input,
``rate <= 0``, a string or bool rate, ``hop`` outside ``[1, win]``,
``nfft < win``, an unknown window, an all-zero window, a transform over
:data:`MAX_STFT_ELEMENTS`, and a window/hop pair whose squared overlap sum
touches zero (NOLA violated — the round trip would be silently lossy).

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`

## 型が繋がる次の op(`table` を入力に取れる)

[istft](istft.md)

## 同カテゴリ(`transform`)

[istft](istft.md) · [stft_cola_check](stft_cola_check.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
