---
op: monogenic_orientation
dim: quat
category: riesz
in: qimage
out: image2d
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# monogenic_orientation — QUAT `riesz` op

- **データ種**: `qimage` → `image2d`
- **呼び出し**: `import quatimage; quatimage.monogenic_orientation(qimage, display: 'bool' = False) -> 'np.ndarray'` (または `opsquat.get("monogenic_orientation")`)

## 使い方

Local orientation ``atan2(R2, R1)`` of a monogenic signal. → (H, W).

Radians in ``[0, pi)``: an orientation is defined modulo ``pi`` (a grating at
10 degrees and one at 190 degrees are the same grating), and the value is
folded into that range rather than left in ``(-pi, pi]`` where the same
structure would read as two different numbers on either side of a contrast
reversal. ``display=True`` maps it to ``[0, 1]``.

**Continuous, not quantised** — the angle is read directly from two filters,
for any angle, where a steerable bank with ``K`` orientations interpolates
between its ``K``. Measured against eight grid-exact grating orientations the
error is at most **3.6e-15 rad**, including the obliques. (Whether that
buys anything downstream is a separate question, and the measured answer is
mostly *no* — see :func:`riesz_displacement`.)

**Where it is undefined, and the mask is not the one you expect.** The
orientation dies where the *Riesz vector* dies, which is at every
even-symmetric point — local phase 0 or pi, the crest of a bright or dark
line — and **the amplitude is at full strength there**. Measured on a 45-degree
grating, the worst orientation error over the whole frame is 0.2764 rad, at a
pixel where ``|R| = 6.8e-16`` and :func:`monogenic_amplitude` reads
``1.0000``. So masking on the amplitude does not protect you; mask on
``hypot(q[..., 1], q[..., 2])``, the Riesz magnitude. With that mask the
error over the same eight orientations is at most 3.6e-15 rad.

Where the Riesz vector is exactly zero, ``atan2(0, 0) = 0`` is returned —
a *value*, not a measurement.

**Raises** ``ValueError``: the input is not a valid quaternion field, or its
``k`` component is non-zero; *display* is not a bool.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[riesz_transform](riesz_transform.md) · [monogenic_signal](monogenic_signal.md)

## 同カテゴリ(`riesz`)

[riesz_transform](riesz_transform.md) · [monogenic_signal](monogenic_signal.md) · [monogenic_amplitude](monogenic_amplitude.md) · [monogenic_phase](monogenic_phase.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
