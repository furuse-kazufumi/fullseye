---
op: synthesize_bearing_signal
dim: acoustics
category: synthesis
in: 
out: signal
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# synthesize_bearing_signal — ACOUSTICS `synthesis` op

- **データ種**: `` → `signal`
- **呼び出し**: `import acoustics; acoustics.synthesize_bearing_signal(rate=25600.0, duration=1.0, carrier_hz=3000.0, defect_hz=107.0, modulation=0.5, mode='am', damping=0.05, noise_sigma=0.0, seed=None)` (または `opsacoustics.get("synthesize_bearing_signal")`)

## 使い方

A resonance amplitude-modulated at a known defect rate — the ground truth.

This is the whole reason envelope analysis exists, built forwards so the
answer is known before the measurement. A spall on a bearing race does not
radiate at the defect rate; it strikes a structure that rings at a much
higher resonance, once per defect passage. What reaches the microphone is a
**carrier at the resonance, modulated at the defect rate**, and the defect
rate itself is not present in the signal as a frequency component at all.

``mode="am"`` gives the exactly analysable case,
``x(t) = (1 + m cos(2 pi f_d t)) sin(2 pi f_c t)``. Its analytic envelope is
exactly ``1 + m cos(2 pi f_d t)`` for ``m < 1``, so the single-sided envelope
spectrum has a line of amplitude **exactly m** at ``f_d`` and nothing else.
Measured with ``m = 0.5``: :func:`envelope_spectrum` returns a peak at
107.000000 Hz of amplitude 0.499677 (the 0.06 % shortfall is the band-pass
filter rolling off across the two sidebands, not the demodulation).

``mode="impulse"`` gives the physically shaped case: an impulse train at
``f_d``, each impulse ringing down as ``exp(-2 pi zeta f_c t) sin(2 pi f_c
t)``. The envelope spectrum then shows ``f_d`` **and its harmonics**, which
is what a real record looks like. Measured with ``f_d = 107`` Hz: the
envelope-spectrum peak is at 107.000000 Hz and the harmonics at 214 and
321 Hz carry 0.6542 and 0.4748 of the fundamental's amplitude.

In am mode the raw spectrum has **nothing** at ``f_d``: measured, the raw
single-sided amplitude at 107 Hz is 4.3e-16, while the carrier reads
1.000000 and each sideband at 2893 and 3107 Hz reads 0.250000 — exactly
``m/2``, as amplitude modulation requires. In impulse mode the raw amplitude
at 107 Hz is 0.01165, not zero (an impulse train is not a pure product), but
still 18x below what the envelope spectrum recovers from the same record.

**Raises** ``ValueError``: any non-real / non-finite / string / bool scalar,
``rate <= 0``, ``duration <= 0``, ``modulation`` outside ``[0, 1)`` in am
mode (at ``m >= 1`` the envelope is ``|1 + m cos|``, which folds and puts
energy at ``2 f_d`` — a rectified envelope, not the modulation), ``damping``
outside ``(0, 1)``, a total length over :data:`MAX_SAMPLES`, and — the one
that matters — **any requested frequency at or above Nyquist, including the
upper modulation sideband** ``f_c + f_d``. An aliased carrier would come
back as a plausible signal at the wrong frequency with no error.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[stft](../transform/stft.md) · [envelope_spectrum](../bearing/envelope_spectrum.md) · [spectral_kurtosis](../bearing/spectral_kurtosis.md) · [cepstrum](../bearing/cepstrum.md) · [angular_resample](../order/angular_resample.md) · [order_spectrum](../order/order_spectrum.md) · [octave_spectrum](../level/octave_spectrum.md) · [weighting_response](../level/weighting_response.md)

## 同カテゴリ(`synthesis`)

[synthesize_speed_ramp](synthesize_speed_ramp.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
