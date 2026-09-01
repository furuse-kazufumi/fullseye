---
op: quaternion_to_rgb
dim: quat
category: convert
in: qimage
out: rgbimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# quaternion_to_rgb — QUAT `convert` op

- **データ種**: `qimage` → `rgbimage`
- **呼び出し**: `import quatimage; quatimage.quaternion_to_rgb(qimage, allow_scalar: 'bool' = False) -> 'np.ndarray'` (または `opsquat.get("quaternion_to_rgb")`)

## 使い方

Vector part of a quaternion image, as linear RGB. → (H, W, 3).

The inverse of :func:`rgb_to_quaternion` — and, by default, a *checked*
inverse. A quaternion image that picked up a scalar component somewhere (a
Hamilton product with a non-pure quaternion, a monogenic signal handed here
by mistake) is **refused** rather than silently truncated, because dropping
the ``w`` component is exactly the kind of loss that produces a plausible
picture from the wrong data. Pass ``allow_scalar=True`` to opt in to the
truncation when it is what you meant.

The tolerance is relative to the field's own peak modulus
(:data:`_MONOGENIC_K_TOL`, 1e-9): a quaternion image that really is pure
carries ``|w|`` at the 1e-17 level after a round trip through two FFTs, and
anything with a meaningful scalar part is many orders above that. Nothing
real lives in between.

**Raises** ``ValueError``: *qimage* is not a finite ``(H, W, 4)`` array; or
it has a non-negligible scalar part and ``allow_scalar`` is False.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`rgbimage` を入力に取れる)

[rgb_to_quaternion](rgb_to_quaternion.md)

## 同カテゴリ(`convert`)

[rgb_to_quaternion](rgb_to_quaternion.md) · [quat_norm](quat_norm.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
