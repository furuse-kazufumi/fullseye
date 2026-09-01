---
op: riesz_displacement_series
dim: quat
category: motion
in: video
out: pairs
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# riesz_displacement_series — QUAT `motion` op

- **データ種**: `video` → `pairs`
- **呼び出し**: `import quatimage; quatimage.riesz_displacement_series(video, f_lo, f_hi, fps, scales: 'int' = 4) -> 'np.ndarray'` (または `opsquat.get("riesz_displacement_series")`)

## 使い方

Whole-frame displacement waveform from the monogenic phase. → (T, 2).

The contrast-weighted spatial mean of :func:`riesz_displacement`: the
rigid-body motion of the scene in pixels, one ``(dx, dy)`` row per frame.
The ``(n, 2)`` layout is the shared 1-D convention (``dsp.spectrum``,
``funct1d``, ``opsoptics``'s MTF curves), so the trace can be handed to
``dsp.spectrum`` to read off a resonant frequency without any repacking.

Weights are the ``|z|^2`` contrast the field solve uses, restricted to the
pixels marked ``valid``, so blank regions do not drag the average towards
zero. A clip with no valid pixel anywhere (a constant image) returns exact
zeros rather than dividing by zero.

Accuracy, the ``J0`` cliff and the multi-orientation failure all inherit from
:func:`riesz_displacement` — read its head-to-head table before trusting a
number from here. On a single-grating 64x64x64 / 8 px / 4 Hz clip a true
0.5 px amplitude is recovered as **0.50000000000000 px** (2.2e-16 relative);
on the two-grating ``motionmag.synthesize_translation`` default the same
0.5 px comes back 13.0 % low, with nothing to signal it.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`motion`)

[riesz_motion_magnify](riesz_motion_magnify.md) · [riesz_displacement](riesz_displacement.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
