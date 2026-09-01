---
op: temporal_bandpass
dim: motionmag
category: temporal
in: video
out: video
examples: [motion_magnification]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# temporal_bandpass — MOTIONMAG `temporal` op

- **データ種**: `video` → `video`
- **呼び出し**: `import motionmag; motionmag.temporal_bandpass(video, f_lo, f_hi, fps) -> 'np.ndarray'` (または `opsmotionmag.get("temporal_bandpass")`)

## 使い方

Ideal temporal band-pass of every pixel's time series -> ``(T, H, W)``.

Each pixel is transformed along time, every DFT bin whose frequency lies
outside ``[f_lo, f_hi]`` (in Hz, magnitude, DC always excluded) is zeroed,
and the result is transformed back. Frequency-selective where
``videops.moving_average`` and ``videops.spatiotemporal_gaussian`` are
low-pass; this is the filter isolating "what is happening at 4 Hz".

Exact for a component sitting on a bin: with ``T`` frames at ``fps``, a
sinusoid at ``k*fps/T`` Hz passes with gain 1 and everything else in the band
passes untouched. Measured on a bin-centred 4 Hz unit sinusoid in a 64-frame
32 fps clip that also carries a DC offset of 0.5 and a 12 Hz component of
amplitude 0.3, the recovered waveform matches the 4 Hz term alone to
``max|err| = 4.36e-15``.

A brick-wall filter rings in time; that is the price of an exact pass-band
and it is the same choice the 2012 Eulerian magnification paper makes. The
output is zero-mean along time by construction.

## 詳しい使い方ガイド

- [motion_magnification ファミリ ガイド](../guides/motion_magnification.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_magnification](../../../../examples/motion_magnification.py) — `py -3.11 examples/motion_magnification.py`

## 型が繋がる次の op(`video` を入力に取れる)

[temporal_band_power](temporal_band_power.md) · [band_snr](band_snr.md) · [motion_magnify](../magnify/motion_magnify.md) · [phase_displacement](../measure/phase_displacement.md) · [displacement_series](../measure/displacement_series.md)

## 同カテゴリ(`temporal`)

[temporal_band_power](temporal_band_power.md) · [band_snr](band_snr.md)

---
*Provenance: motionmag.py — MOTIONMAG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
