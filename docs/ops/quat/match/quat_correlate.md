---
op: quat_correlate
dim: quat
category: match
in: qimage × qimage
out: qimage
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# quat_correlate — QUAT `match` op

- **データ種**: `qimage × qimage` → `qimage`
- **呼び出し**: `import quatimage; quatimage.quat_correlate(qimage, template) -> 'np.ndarray'` (または `opsquat.get("quat_correlate")`)

## 使い方

Quaternion cross-correlation ``sum_s conj(a(s)) * b(s+t)``. → (H, W, 4).

Colour template matching that keeps the **colour geometry**, not just the
colour magnitude. The scalar part of the result is
``sum (a_R b_R + a_G b_G + a_B b_B)`` — exactly the sum of the three
per-channel correlations, i.e. what a channelwise pipeline computes and all
it computes. The *vector* part is ``-sum (a x b)``, the accumulated colour
cross-product, and it is zero exactly when the two colour fields are
parallel. So the same call answers "how well does it match?" (scalar part)
**and** "in what way does the colour fail to line up?" (vector part).

Measured on a 32x32 patch whose colours lie in the red-green plane, matched
against a copy of itself rotated about the blue axis. The scalar part is
``cos(angle)`` times the self-correlation, exactly, and
``atan2(|vector|, scalar)`` returns the rotation angle:

===========  ==================  =================  ==================
rotation     scalar/self ratio   ``cos(angle)``     angle recovered
===========  ==================  =================  ==================
0 deg        1.000000            1.000000           0.000000 deg
30 deg       0.866025            0.866025           30.000000 deg
90 deg       0.000000            0.000000           90.000000 deg
===========  ==================  =================  ==================

with the vector direction at ``(0.000, 0.000, -1.000)`` — the **negative** of
the rotation axis, because the conjugate sits on the left of the product. A
channelwise pipeline has no term that can produce any of that: the
cross-products are *cross*-channel products, and three independent channel
correlations never form them. (Verified in the same test: the scalar part
equals the summed per-channel correlation to 0.0 exactly, so the channelwise
baseline recovers the scalar part and nothing else.)

**The exact reading needs the colours to lie in the plane orthogonal to the
rotation axis, and the docstring says so because the general case is
biased.** For a colour field with a component along the axis, the vector part
picks up terms in ``a_z`` and the recovered angle is wrong: measured on a
uniform-random colour patch rotated 30 degrees about blue, the same formula
returns **22.524 degrees** on an axis of ``(0.247, 0.419, -0.874)`` instead
of ``(0, 0, -1)``. That is a quiet wrong number, it is inherent to summing
per-pixel cross products, and it is not detectable from the result — so the
precondition is part of the contract.

Both inputs must be pure quaternion images for any of the above to hold; a
non-zero scalar part is not refused (it is algebraically fine) but it
contributes to both parts and the colour interpretation stops applying.

**The correlation is circular** (computed with FFTs, like
``filters_freq``'s family): a template near the border wraps around. Pad the
inputs if that matters. Shapes must match exactly; a smaller template must be
zero-padded into the image's shape by the caller, because silently choosing
a padding origin would move the peak.

**Raises** ``ValueError``: either input is not a valid ``(H, W, 4)`` field,
or the two shapes differ.

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

## 同カテゴリ(`match`)

—

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
