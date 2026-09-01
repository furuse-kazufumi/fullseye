---
op: temporal_band_power
dim: motionmag
category: temporal
in: video
out: image2d
examples: [motion_magnification]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# temporal_band_power — MOTIONMAG `temporal` op

- **データ種**: `video` → `image2d`
- **呼び出し**: `import motionmag; motionmag.temporal_band_power(video, f_lo, f_hi, fps) -> 'np.ndarray'` (または `opsmotionmag.get("temporal_band_power")`)

## 使い方

Per-pixel mean-square power inside a temporal band -> ``(H, W)`` map.

"Where in the frame is something moving at this frequency?" — a resonance
map. The value at a pixel is the mean over time of the squared band-passed
signal, so a pure sinusoid of amplitude ``a`` inside the band reads exactly
``a^2/2`` (Parseval; measured relative error ``3.08e-16`` for ``a = 0.3``).

This is an *analysis map*, not a displayable image: it is a power and is not
bounded by 1. Pixels with no in-band content read 0.

## 詳しい使い方ガイド

- [motion_magnification ファミリ ガイド](../guides/motion_magnification.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_magnification](../../../../examples/motion_magnification.py) — `py -3.11 examples/motion_magnification.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[complex_steerable_decompose](../decompose/complex_steerable_decompose.md)

## 同カテゴリ(`temporal`)

[temporal_bandpass](temporal_bandpass.md) · [band_snr](band_snr.md)

---
*Provenance: motionmag.py — MOTIONMAG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
