---
op: band_snr
dim: motionmag
category: temporal
in: video
out: table
examples: [motion_magnification]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# band_snr — MOTIONMAG `temporal` op

- **データ種**: `video` → `table`
- **呼び出し**: `import motionmag; motionmag.band_snr(video, f_lo, f_hi, fps) -> 'dict'` (または `opsmotionmag.get("band_snr")`)

## 使い方

Measure what a clip's temporal band contains, and what it costs -> ``dict``.

Every quantity is a measured mean-square power obtained from the per-pixel
temporal DFT (Parseval-normalised so that the bins of one pixel sum to that
pixel's mean square), averaged over pixels:

* ``static_power`` — the DC bin. The scene that is simply *there*.
* ``band_power`` — the bins inside ``[f_lo, f_hi]``. Coherent motion **plus**
  whatever noise happens to fall in the band.
* ``out_of_band_power`` / ``out_of_band_bins`` — everything else except DC.
  With broadband sensor noise this is the noise floor, and
  ``noise_power_per_bin`` is its per-bin density.
* ``noise_in_band`` = ``noise_power_per_bin * band_bins`` — how much of
  ``band_power`` is expected to be noise.
* ``motion_power`` = ``max(band_power - noise_in_band, 0)`` and
  ``motion_snr_db`` = ``10*log10(motion_power / noise_in_band)``.
* ``image_snr_db`` = ``10*log10(static_power / (band_power +
  out_of_band_power))`` — the static scene against everything that flickers.

**The two SNRs answer different questions and magnification moves only one
of them.** Scaling the in-band phase by ``alpha`` scales the in-band motion
*and* the in-band noise by the same factor, so the true motion SNR cannot
improve: magnification never makes a measurement more certain than the
recording was. What does change is ``image_snr_db``, because the temporal
fluctuation of the output frames grows like ``alpha^2`` while the static
scene does not.

**A caveat that matters when this is run on an already-magnified clip.**
``motion_snr_db`` here divides the in-band signal by a noise floor estimated
from the *out-of-band* bins, and magnification does not touch those. Applied
to a magnified video it therefore credits ``alpha^2`` more in-band power
against an unchanged noise estimate and reports an improvement that did not
occur — measured, ``+6.86 dB`` at ``alpha = 2`` on a clip whose true motion
SNR cannot have moved. :func:`motion_magnify` knows the gain and returns the
corrected figure as ``motion_snr_out_db``; use that one, not
``result["snr_out"]["motion_snr_db"]``.

``snr_clamped`` is True when a reported dB hit the ``[-100, +100]`` window
(a noiseless synthetic has zero out-of-band power, which is a division by
zero rather than an infinite SNR).

## 詳しい使い方ガイド

- [motion_magnification ファミリ ガイド](../guides/motion_magnification.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_magnification](../../../../examples/motion_magnification.py) — `py -3.11 examples/motion_magnification.py`

## 型が繋がる次の op(`table` を入力に取れる)

[complex_steerable_reconstruct](../decompose/complex_steerable_reconstruct.md)

## 同カテゴリ(`temporal`)

[temporal_bandpass](temporal_bandpass.md) · [temporal_band_power](temporal_band_power.md)

---
*Provenance: motionmag.py — MOTIONMAG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
