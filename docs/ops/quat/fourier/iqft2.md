---
op: iqft2
dim: quat
category: fourier
in: qimage
out: qimage
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# iqft2 — QUAT `fourier` op

- **データ種**: `qimage` → `qimage`
- **呼び出し**: `import quatimage; quatimage.iqft2(spectrum, side, mu=None) -> 'np.ndarray'` (または `opsquat.get("iqft2")`)

## 使い方

Inverse quaternion Fourier transform of a **centred** spectrum. → (H, W, 4).

The exact inverse of :func:`qft2` **for the same side and the same mu**:
measured round-trip error ``2.22e-15`` for both sides on a standard-normal
``(32, 32, 4)`` field. The kernel is ``exp(+mu * 2*pi*(...))`` applied on the
side named, and the ``1/(H*W)`` normalisation is carried here, as in
``numpy.fft.ifft2``.

**Using the wrong side does not raise.** ``iqft2(qft2(q, "left"), "right")``
returns a finite, plausible quaternion image that is simply not ``q``:
measured ``max|err| = 1.113`` on a random colour image whose own range is
``0.9994`` (another seed: 1.063 against 1.0), and — the dangerous case — only ``0.054`` against a range of
``1.076`` on a grey-axis-dominated one, which is small enough to survive a
look at the picture. The ``side`` argument is required at both ends for
exactly this reason, and the two calls must agree: nothing in the data
records which transform produced it, so nothing downstream can catch the
mismatch for you.

**Raises** ``ValueError``: *spectrum* is not a valid ``(H, W, 4)`` field;
*side* is not ``'left'`` / ``'right'``; *mu* is not a finite non-zero
3-vector.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`qimage` を入力に取れる)

[quaternion_to_rgb](../convert/quaternion_to_rgb.md) · [quat_norm](../convert/quat_norm.md) · [quat_conjugate_image](../algebra/quat_conjugate_image.md) · [quat_normalize_image](../algebra/quat_normalize_image.md) · [quat_image_multiply](../algebra/quat_image_multiply.md) · [monogenic_amplitude](../riesz/monogenic_amplitude.md) · [monogenic_phase](../riesz/monogenic_phase.md) · [monogenic_orientation](../riesz/monogenic_orientation.md)

## 同カテゴリ(`fourier`)

[qft2](qft2.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
