---
op: transfer_function
dim: acoustics
category: dual
in: signal × signal
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# transfer_function — ACOUSTICS `dual` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import acoustics; acoustics.transfer_function(x, y, rate, win=None, hop=None, window='hann', estimator='h1', ref=1.0, floor_db=-200.0)` (または `opsacoustics.get("transfer_function")`)

## 使い方

Estimate ``H(f)`` with ``x`` in and ``y`` out, with its coherence.

``estimator``:

* ``"h1"`` — ``Pxy / Pxx``. Unbiased when the noise is on the **output**.
  The usual default and the right one for a driven test.
* ``"h2"`` — ``Pyy / conj(Pxy)``. Unbiased when the noise is on the
  **input**. It over-estimates the magnitude wherever H1 under-estimates it,
  so the two together bracket the truth, and ``|H1/H2| = gamma**2`` exactly —
  an identity worth checking rather than a coincidence.

Returns a dict: ``freqs``, ``response`` (complex), ``magnitude``,
``magnitude_db`` (relative to ``ref``), ``phase_rad``, ``coherence``,
``estimator``, ``n_frames``, ``win``, ``hop``, ``rate``.

Measured at 16 kHz over 16384 samples, win = 1024, 31 frames, white input:

* ``y = 2.5 * x``: ``mean |H| = 2.5000000000``, max deviation from 2.5 over
  all bins **1.78e-15**, mean ``|phase|`` 2.7e-17, mean coherence
  1.0000000000.
* ``y = 0.8 * x[n-37]``: the phase is a straight line in frequency of slope
  ``-2 pi * 37 / 16000`` s. A least-squares fit to the unwrapped phase over
  200-7000 Hz gives a group delay of **37.000004 samples** against a true 37
  (error 4.3e-06 samples), and ``mean |H| = 0.792220`` over the same bins
  against a true 0.8 (max deviation 0.050).
* ``y = 2.5 * x + n`` with output noise at 0 dB SNR: H1 gives
  ``mean |H| = 2.523390`` — 0.94 % from the truth — while H2 gives
  **5.043020**, a factor of 2.0 too large, exactly as the theory predicts
  when the noise sits on the output. And ``|H1/H2|`` equals the coherence
  pointwise to **5.6e-16** (both mean 0.509143), which is the identity worth
  knowing: the ratio of the two estimators *is* the coherence.

That third row is why the coherence is returned with the response. The H2
number is off by 100 % and there is nothing about 5.04 that looks wrong.

**Raises** ``ValueError``: everything :func:`coherence` refuses, plus an
unknown ``estimator`` and ``ref <= 0``.

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

## 同カテゴリ(`dual`)

[coherence](coherence.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
