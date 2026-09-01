---
op: apply_weighting
dim: acoustics
category: level
in: signal
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# apply_weighting — ACOUSTICS `level` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import acoustics; acoustics.apply_weighting(x, rate, kind='A')` (または `opsacoustics.get("apply_weighting")`)

## 使い方

Apply an A / C / Z frequency weighting to a signal, zero-phase.

The weighting is applied as a real, even gain in the frequency domain, so it
introduces no phase distortion and no group delay — the result is aligned
sample-for-sample with the input, which a recursive filter implementation
would not be.

Measured: a 1 kHz sine at 16 kHz (16000 samples, exactly 1000 periods) is
returned **unchanged** by both A and C weighting — max absolute difference
1.078e-13 for A and 1.225e-13 for C — because both curves are exactly 0 dB
at 1 kHz by construction. A 100 Hz sine of amplitude 1.0 comes back with
amplitude **0.110373** under A weighting, against the closed form
``10**(-19.1428/20) = 0.110373``.

``kind="Z"`` returns a copy, unchanged.

**Raises** ``ValueError``: everything :func:`_as_signal` refuses, an unknown
``kind``, ``rate <= 0``.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[stft](../transform/stft.md) · [envelope_spectrum](../bearing/envelope_spectrum.md) · [spectral_kurtosis](../bearing/spectral_kurtosis.md) · [cepstrum](../bearing/cepstrum.md) · [angular_resample](../order/angular_resample.md) · [order_spectrum](../order/order_spectrum.md) · [octave_spectrum](octave_spectrum.md) · [weighting_response](weighting_response.md)

## 同カテゴリ(`level`)

[octave_bands](octave_bands.md) · [octave_spectrum](octave_spectrum.md) · [weighting_response](weighting_response.md) · [equivalent_level](equivalent_level.md) · [percentile_level](percentile_level.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
