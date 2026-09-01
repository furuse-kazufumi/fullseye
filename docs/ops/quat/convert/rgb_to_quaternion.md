---
op: rgb_to_quaternion
dim: quat
category: convert
in: rgbimage
out: qimage
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# rgb_to_quaternion — QUAT `convert` op

- **データ種**: `rgbimage` → `qimage`
- **呼び出し**: `import quatimage; quatimage.rgb_to_quaternion(image_rgb) -> 'np.ndarray'` (または `opsquat.get("rgb_to_quaternion")`)

## 使い方

Embed a colour image as pure quaternions ``0 + R i + G j + B k``. → (H, W, 4).

Sangwine's 1996 encoding, and the entry point of the whole colour half of
this module: once a pixel is a quaternion, ``q x conj(q)`` rotates its colour
and :func:`qft2` transforms the three channels as **one** hypercomplex signal
instead of three unrelated real ones.

The scalar (``w``) component is set to exactly zero — a *pure* quaternion —
because that is what makes the conjugation a 3-D rotation. Values are not
clamped: linear RGB after black-level subtraction legitimately goes negative,
and clipping it would change the colour direction, which is the quantity
every operator downstream reads.

**Raises** ``ValueError``: *image_rgb* is not a finite ``(H, W, 3)`` numeric
array, is complex / bool / string-typed / masked, or exceeds
:data:`MAX_PIXELS`.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`qimage` を入力に取れる)

[quaternion_to_rgb](quaternion_to_rgb.md) · [quat_norm](quat_norm.md) · [quat_conjugate_image](../algebra/quat_conjugate_image.md) · [quat_normalize_image](../algebra/quat_normalize_image.md) · [quat_image_multiply](../algebra/quat_image_multiply.md) · [monogenic_amplitude](../riesz/monogenic_amplitude.md) · [monogenic_phase](../riesz/monogenic_phase.md) · [monogenic_orientation](../riesz/monogenic_orientation.md)

## 同カテゴリ(`convert`)

[quaternion_to_rgb](quaternion_to_rgb.md) · [quat_norm](quat_norm.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
