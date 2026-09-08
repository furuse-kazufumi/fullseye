---
op: spectrum
dim: oned
category: signal
in: signal
out: pairs
examples: [acoustic_condition_monitoring, poc_bearing_diagnosis, poc_gear_tooth_metrology, poc_machine_condition_fusion, poc_pipe_wall_loss, poc_recycling_sorting, poc_web_roll_periodicity]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# spectrum — ONED `signal` op

- **データ種**: `signal` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.spectrum(x, rate=1.0)` (実装を直接呼ぶなら `import dsp; dsp.spectrum(x, rate=1.0)`、台帳から引くなら `ops1d.get("spectrum")`)
- **台帳経由の戻り値**: `fullseye.ledger.spectrum(...)` は**宣言 out 型 `pairs` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.spectrum.raw(...)`、または `dsp.spectrum` を直接呼ぶ。

## 使い方

Raw one-sided magnitude spectrum -> ``(freqs, magnitude)`` (``np.fft.rfft``).

**Scaling convention — read this before comparing any number.** *One-sided*
describes the frequency axis, not the amplitude axis. ``rfft`` keeps only the
non-negative frequencies, so ``freqs`` runs from 0 to ``rate/2`` in
``len(x)//2 + 1`` bins — but ``magnitude`` is the **unnormalised**
``|rfft(x)|``. It is *not* an amplitude and it grows with ``len(x)``: the same
tone recorded twice as long comes back twice as tall. Nothing here divides by
``N``; the caller does, and the exact factor depends on the bin::

    freqs, mag = spectrum(x, rate)
    amp = mag * (2.0 / len(x))       # one-sided amplitude, bins 1 .. N/2-1
    amp[0] /= 2.0                    # DC has no mirror twin -> no factor 2
    if len(x) % 2 == 0:
        amp[-1] /= 2.0               # nor does the Nyquist bin of an even N

The factor is ``2/N`` and not ``1/N`` because a real sinusoid of amplitude
``A`` splits its energy over a positive and a negative frequency; ``rfft``
discards the negative half, so the surviving bin holds ``A*N/2``. DC and (for
even ``N``) Nyquist are their own mirror image and are *not* doubled —
applying ``2/N`` to them reports twice the true level.

Measured, so the convention can be checked rather than assumed. A unit sine
at a bin centre (``rate = 25600`` Hz, ``N = 25600``, 3000 Hz, amplitude
exactly 1.0): the returned ``mag`` at 3000 Hz is ``12799.999999999998``
(= ``N/2``), and ``mag * 2/N`` is ``0.9999999999999999``. A constant signal
of value 1.0 with ``N = 1024``: ``mag[0] = 1024.0``, so ``mag[0] * 1/N`` is
exactly ``1.0`` while ``mag[0] * 2/N`` would claim ``2.0``. Likewise
``cos(pi n)`` (amplitude 1.0 at Nyquist, ``N = 1024``): ``mag[-1] = 1024.0``,
``* 1/N`` = ``1.0``, ``* 2/N`` = ``2.0``.

Everything scale-*invariant* — where the peak is, the spectral centroid, the
bandwidth, a ratio between two bins — is unaffected by the convention, which
is why :func:`signal_features` can build on this directly. Everything
absolute (an amplitude in the signal's own units, a dB level) needs the
division above. :func:`acoustics.envelope_spectrum` and
:func:`acoustics.order_spectrum` already return calibrated one-sided
amplitudes (they apply their own ``2/N`` internally) — do **not** apply the
factor twice when comparing their output with this one.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`
- [poc_bearing_diagnosis](../../../../examples/poc_bearing_diagnosis.py) — `py -3.11 examples/poc_bearing_diagnosis.py`
- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`
- [poc_machine_condition_fusion](../../../../examples/poc_machine_condition_fusion.py) — `py -3.11 examples/poc_machine_condition_fusion.py`
- [poc_pipe_wall_loss](../../../../examples/poc_pipe_wall_loss.py) — `py -3.11 examples/poc_pipe_wall_loss.py`
- [poc_recycling_sorting](../../../../examples/poc_recycling_sorting.py) — `py -3.11 examples/poc_recycling_sorting.py`
- [poc_web_roll_periodicity](../../../../examples/poc_web_roll_periodicity.py) — `py -3.11 examples/poc_web_roll_periodicity.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [resample](resample.md) · [spectrogram](spectrogram.md) · [zero_crossing_rate](zero_crossing_rate.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
