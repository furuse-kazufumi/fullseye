---
op: coherence
dim: acoustics
category: dual
in: signal × signal
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# coherence — ACOUSTICS `dual` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import acoustics; acoustics.coherence(x, y, rate, win=None, hop=None, window='hann')` (または `opsacoustics.get("coherence")`)

## 使い方

Ordinary coherence: how much of ``y`` is linearly explained by ``x``.

``gamma**2(f) = |Pxy|**2 / (Pxx * Pyy)``, Welch-averaged. It is bounded in
``[0, 1]``, and it is the number that says whether a transfer function is
worth reading at a given frequency.

**A single frame makes it identically 1.0** — the Cauchy-Schwarz inequality
is an equality without averaging — so an unaveraged coherence is a perfect
score that carries no information at all. That case is refused, not returned.

``win`` defaults to the largest power of two leaving at least 8 frames,
capped at 1024; the value used is returned.

Returns a dict: ``freqs``, ``coherence``, ``n_frames``, ``win``, ``hop``,
``rate``, ``mean_coherence``, ``bias`` (the coherence a *pair of independent
noise records* would show with this many frames, ``1/n_frames`` — anything
at or below this is indistinguishable from nothing).

Measured at 16 kHz over 16384 samples, win = 1024, 31 frames:

=======================================  ==============  ========
case                                     mean coherence  min
=======================================  ==============  ========
y = 2.5 * x (noiseless)                  1.000000        1.0000
y = 0.8 * x delayed 37 samples           0.983003        0.9661
y = 2.5 x + independent noise, 0 dB SNR  0.509143        0.2219
y, x independent noise                   0.035640        0.0001
=======================================  ==============  ========

Row three against its closed form: for output noise the expected coherence
is ``SNR/(1+SNR)`` = 0.5000 at 0 dB, measured 0.5091. Row four against the
bias floor ``1/n_frames = 1/31 = 0.0323``, measured 0.0356 — which is why
``bias`` is returned: **an uncorrelated pair does not read zero**, and
reading 0.03 as "a little bit of coupling" is the mistake this number
prevents. Row two shows the other honest limit: a pure delay is a perfectly
linear system and still reads 0.983, not 1, because a delay of 37 samples
moves signal across the frame boundaries the estimator averages over.

**Raises** ``ValueError``: everything :func:`_as_signal` refuses on either
channel, unequal channel lengths, fewer than 2 frames, ``win`` longer than
the record, an unknown window.

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

[transfer_function](transfer_function.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
