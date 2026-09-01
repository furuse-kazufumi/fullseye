---
op: quat_color_rotate
dim: quat
category: color
in: qimage
out: qimage
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# quat_color_rotate — QUAT `color` op

- **データ種**: `qimage` → `qimage`
- **呼び出し**: `import quatimage; quatimage.quat_color_rotate(qimage, axis_rgb, angle_rad) -> 'np.ndarray'` (または `opsquat.get("quat_color_rotate")`)

## 使い方

Rotate every pixel's colour about an RGB axis: ``q x conj(q)``. → (H, W, 4).

The operation a complex pixel cannot express. ``axis_rgb`` is a direction in
RGB space and ``angle_rad`` the rotation about it; the rotor
``q = cos(a/2) + sin(a/2) * axis`` is built with
``pose_quat.axis_angle_to_quat`` and the conjugation is applied to the vector
part of every pixel, leaving the scalar part untouched (a conjugation cannot
move it).

Exactness and what it is worth
------------------------------
The conjugation is applied through the ``3x3`` matrix from
``pose_quat.quat_to_hom_mat3d`` rather than by two per-pixel Hamilton
products, because for a ``(512, 512)`` image that is 500k quaternion
multiplications versus one ``einsum``. The two are the *same map*, measured:
against per-pixel ``pose_quat.quat_rotate_point_3d`` the agreement is
``4.44e-16``, the round trip ``rotate(rotate(q, ax, a), ax, -a)`` returns
``q`` to ``2.22e-16``, and the colour magnitude is preserved to ``2.22e-16``.

The matrix identity is also the honest limit of the *capability* claim.
``SO(3)`` and the unit quaternions are isomorphic, so **a 3x3 orthogonal
colour matrix does exactly this and nothing is lost by using one** — measured
against an explicit ``Rz(30 deg)``, the agreement is ``2.22e-16``. What a
quaternion buys is 4 numbers instead of 9, exact closure under composition,
and ``slerp``. Measured over 100,000 random small rotations composed in
sequence, the quaternion (renormalised each step, 4 divisions) drifts from
unit norm by **0.0** while the matrix (composed by multiplication, not
re-orthonormalised) drifts to ``|R^T R - I| = 4.33e-14``.

**That advantage is real but it is nearly nothing, and an earlier revision of
this file oversold it by four orders of magnitude.** The same measurement
then read ``4.4e-10`` for the matrix, which looked like a decisive argument
for quaternions. It was not an argument about quaternions at all: it was the
``pose_quat`` defect described below, feeding a slightly non-orthogonal
matrix into every one of the 100,000 steps. With that fixed the honest figure
is ``4.33e-14``, i.e. ordinary rounding over 100k products. The lesson is the
repository's own: a number that flatters the thing you are building is the
one to re-measure first.

What a *channelwise* pipeline — three independent scalar filters, which is
what running the complex ops on R, G and B separately means — cannot do is
this operation at all: it never mixes channels, so it cannot turn red towards
green. Pure red rotated 90 degrees about the blue axis comes back as
``(-2.2e-16, 1.0, 0.0)``; no per-channel gain can put anything in the green
channel, because it starts at zero. That is the comparison in
``tests/test_quatimage.py``, and it is the one that is decisive.

Two traps in the rotor, both refused here regardless of the dependency
---------------------------------------------------------------------
``pose_quat`` used to normalise as ``n / (norm + 1e-12)``. A **zero axis**
then returned ``[cos(a/2), 0, 0, 0]``, which ``quat_to_hom_mat3d``
re-normalised to the identity: a rotation request silently became a no-op.
Worse, at ``angle_rad = pi`` that same path produced ``[0, 0, 0, 0]``, whose
normalisation was ``0/(0+1e-12) = 0`` and whose matrix was again the identity
— a *180-degree* colour rotation silently becoming a copy. Both were reported
and **have since been fixed in** ``pose_quat`` **itself** (zero length now
raises; ``axis_angle_to_quat(0, 0, 1, pi)`` now returns exactly
``[0, 0, 0, 1]`` with norm 1, where it used to return norm 0.9999999999990).

This operator nevertheless keeps both of its own guards —
:func:`_require_direction` on the axis, and an explicit unit-norm assertion
on the finished rotor (tolerance :data:`_UNIT_TOL`). A check that only holds
while a dependency behaves is not a check, and the caller of this module
should get this module's error message. A genuine pi rotation still works:
pure red about the blue axis gives ``(-1.0, 1.2e-16, 0.0)``.

**Raises** ``ValueError``: *qimage* is not a valid ``(H, W, 4)`` field;
*axis_rgb* is not a finite non-zero 3-vector; *angle_rad* is not a finite
real scalar; the constructed rotor is not unit norm.

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

## 同カテゴリ(`color`)

[quat_color_filter](quat_color_filter.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
