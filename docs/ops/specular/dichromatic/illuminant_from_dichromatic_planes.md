---
op: illuminant_from_dichromatic_planes
dim: specular
category: dichromatic
in: rgbimage × labels
out: vector
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# illuminant_from_dichromatic_planes — SPECULAR `dichromatic` op

- **データ種**: `rgbimage × labels` → `vector`
- **呼び出し**: `import specularity; specularity.illuminant_from_dichromatic_planes(image_rgb, labels, min_pixels=16, min_plane_ratio=1e-06, min_intersection_ratio=1e-06)` (または `opsspecular.get("illuminant_from_dichromatic_planes")`)

## 使い方

Recover the illuminant colour from two or more materials. → unit 3-vector.

Lee's construction (1986). Under the dichromatic model every pixel of one
material lies in the plane spanned by that material's body colour and the
illuminant colour, so each material contributes a plane through the origin
of RGB, and **all of those planes contain the illuminant direction**. Two
materials with different body colours therefore intersect in exactly one
line, and that line is the answer — a null-space computation, closed form.

*labels* is an ``(H, W)`` integer map naming the material at each pixel;
negative labels are ignored (background). Each material needs *min_pixels*
pixels **and genuine highlight variation**: a material seen with no specular
reflection at all has colours along a single ray, which defines no plane.
That is measured by the second-to-first singular ratio of its colour matrix
and rejected below *min_plane_ratio* rather than contributing an arbitrary
normal.

The returned direction is unit length with a positive component sum
(illuminant colours are positive; the null space fixes the line, not the
sign). On synthetic data with three known materials it reproduces the true
illuminant with a maximum component error of 4.4e-14 and an angular error
that rounds to 0.0 degrees (measured in ``tests/test_specularity.py``).

*min_intersection_ratio* guards the answer itself: if the plane normals are
nearly parallel — two materials whose body colours differ only in
brightness, which is the same material twice — the intersection is
ill-conditioned and the call raises instead of returning a direction picked
by rounding error.

**Raises** ``ValueError``: shape or dtype problems as in
:func:`specular_diffuse_split`; *labels* is not an ``(H, W)`` integer map
matching the image; more than :data:`MAX_MATERIALS` distinct labels; fewer
than two materials survive the *min_pixels* and *min_plane_ratio* tests; the
surviving planes do not intersect in a well-determined line.

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`vector` を入力に取れる)

—

## 同カテゴリ(`dichromatic`)

[specular_diffuse_split](specular_diffuse_split.md) · [specular_coefficient_map](specular_coefficient_map.md) · [specular_free_transform](specular_free_transform.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
