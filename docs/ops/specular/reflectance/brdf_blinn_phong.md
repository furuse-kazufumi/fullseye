---
op: brdf_blinn_phong
dim: specular
category: reflectance
in: normalmap
out: image2d
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# brdf_blinn_phong — SPECULAR `reflectance` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import specularity; specularity.brdf_blinn_phong(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0), shininess=32.0)` (または `opsspecular.get("brdf_blinn_phong")`)

## 使い方

Blinn's half-vector specular lobe. → (H, W) in [0, 1].

``max(n.h, 0) ** shininess`` where ``h`` is the unit bisector of the light
and view directions (Blinn 1977), zeroed wherever the surface faces away
from either. Exactly 1 where the normal *is* the half-vector — the mirror
condition — and it falls monotonically from there.

**Unnormalised on purpose.** The classical Blinn-Phong lobe does not
integrate to a fixed value; its peak is 1 and its energy grows as the
exponent shrinks. It is a shading model, useful because its peak location is
exact and because it is a *different* lobe shape from
:func:`brdf_microfacet` — a separation routine that only works on one of the
two is fitting the lobe, not the model. For an energy-consistent lobe use
:func:`brdf_microfacet`.

Reciprocal in light and view to machine precision (measured exactly 0.0
maximum difference in ``tests/test_specularity.py``), because the
half-vector is symmetric and the visibility test covers both sides.

**Raises** ``ValueError``: *normals* is not an ``(H, W, 3)`` field or
contains a zero-length normal; *light* / *view* are not non-zero 3-vectors;
*shininess* is negative, non-finite, a string or a bool; light and view are
exactly opposite.

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[polarization_render](../polarization/polarization_render.md)

## 同カテゴリ(`reflectance`)

[brdf_microfacet](brdf_microfacet.md) · [dichromatic_render](dichromatic_render.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
