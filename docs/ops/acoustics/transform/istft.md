---
op: istft
dim: acoustics
category: transform
in: table
out: signal
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# istft — ACOUSTICS `transform` op

- **データ種**: `table` → `signal`
- **呼び出し**: `import acoustics; acoustics.istft(transform)` (または `opsacoustics.get("istft")`)

## 使い方

Invert :func:`stft` by weighted overlap-add — exactly.

Weighted overlap-add divides the synthesised sum by the overlap sum of the
*squared* window, which makes the reconstruction exact for any window and
hop satisfying NOLA, not only for the COLA pairs. :func:`stft` refuses the
NOLA violation up front, so if the transform was produced by it the inverse
cannot be lossy.

Measured round-trip error, ``max |x - istft(stft(x))|`` on 4096 samples of
white noise (float64, so 2.2e-16 is one ulp of the largest sample):

===============  ====  ====  =========  =========
window           win   hop   max error  nola_min
===============  ====  ====  =========  =========
hann             256   128   1.33e-15   0.5
hann             256   64    1.33e-15   1.5
hann             256   255   2.73e-12   2.27e-08
hamming          256   128   1.33e-15   0.5832
blackman         512   128   1.33e-15   1.206
flattop          256   64    1.33e-15   0.396
boxcar           256   128   8.88e-16   2.0
hann (nfft 512)  256   128   1.33e-15   0.5
===============  ====  ====  =========  =========

Read the third row's two columns together. ``hop = 255`` on a 256-sample
window overlaps by one sample, which breaks plain (unweighted) overlap-add
completely; weighted overlap-add still inverts it, but only to 2.7e-12
rather than 1.3e-15, because the squared-window overlap sum falls to
2.3e-08 and the reconstruction divides by it. NOLA is satisfied and the
result is four orders of magnitude less accurate than every other row —
which is why ``nola_min`` is *returned* and not merely checked. A NOLA
minimum that is small but positive is a conditioning warning, and there is
no threshold at which it stops being one, so no threshold is invented here.

**Raises** ``ValueError``: a dict missing any key :func:`stft` writes, a
``spectra`` whose shape disagrees with the recorded ``nfft`` / frame count,
or a non-complex ``spectra``.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[stft](stft.md) · [envelope_spectrum](../bearing/envelope_spectrum.md) · [spectral_kurtosis](../bearing/spectral_kurtosis.md) · [cepstrum](../bearing/cepstrum.md) · [angular_resample](../order/angular_resample.md) · [order_spectrum](../order/order_spectrum.md) · [octave_spectrum](../level/octave_spectrum.md) · [weighting_response](../level/weighting_response.md)

## 同カテゴリ(`transform`)

[stft](stft.md) · [stft_cola_check](stft_cola_check.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
