---
op: displacement_series
dim: motionmag
category: measure
in: video
out: pairs
examples: [motion_magnification]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# displacement_series — MOTIONMAG `measure` op

- **データ種**: `video` → `pairs`
- **呼び出し**: `import motionmag; motionmag.displacement_series(video, f_lo, f_hi, fps, scales: 'int' = 4, orientations: 'int' = 4) -> 'np.ndarray'` (または `opsmotionmag.get("displacement_series")`)

## 使い方

Whole-frame displacement waveform -> ``(T, 2)`` array of ``(dx, dy)``.

The contrast-weighted spatial mean of :func:`phase_displacement`, i.e. the
rigid-body motion of the scene in pixels, one row per frame. This is the
trace to plot, or to feed to ``dsp.spectrum`` to read off the resonant
frequency — a vibration waveform recovered from a camera.

Weights are the same ``|z|^2`` contrast the field solve uses, restricted to
the pixels marked ``valid``, so blank regions do not drag the average
towards zero. A clip with no valid pixel anywhere (a constant image) returns
exact zeros rather than a division by zero.

Sub-pixel accuracy and its cliff inherit from :func:`phase_displacement`;
measured on the 64x64x64 / 8 px / 4 Hz synthetic, a true 0.5 px amplitude is
recovered as 0.50000000 px (6.7e-16 relative), and a true 0.001 px amplitude
as 0.00100000 px (8.7e-15).

## 詳しい使い方ガイド

- [motion_magnification ファミリ ガイド](../guides/motion_magnification.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_magnification](../../../../examples/motion_magnification.py) — `py -3.11 examples/motion_magnification.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`measure`)

[phase_displacement](phase_displacement.md)

---
*Provenance: motionmag.py — MOTIONMAG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
