---
op: specular_free_transform
dim: specular
category: dichromatic
in: rgbimage
out: rgbimage
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# specular_free_transform — SPECULAR `dichromatic` op

- **データ種**: `rgbimage` → `rgbimage`
- **呼び出し**: `import specularity; specularity.specular_free_transform(image_rgb, illuminant_rgb=(1.0, 1.0, 1.0))` (または `opsspecular.get("specular_free_transform")`)

## 使い方

Project out the illuminant direction: the part of the image a highlight cannot touch. → (H, W, 3).

``I - (I.G) G`` for the unit illuminant colour ``G``. Under the dichromatic
model the interface term is ``m_s * G``, so it lies entirely in the removed
direction and the result is **invariant to any specular term whatsoever** —
exactly, for any lobe shape, any strength, any spatial pattern. That is the
specular-invariant subspace of Mallick et al. (2005); this operator is the
projection itself, with no rotation into named channels, so it stays in RGB
and composes with the rest of the family.

Use it when the *shape* of the specular lobe is unknown or the surface is
textured — feature matching, edge detection and correlation all work in this
subspace without any of the assumptions
:func:`specular_diffuse_split` needs.

**This is a projection, not a picture.** The result loses one of three
degrees of freedom (its component along ``G`` is exactly zero everywhere)
and, for an image with negative values after black-level subtraction, keeps
them. It is not a displayable "highlight-removed photo" and does not claim
to be; for that, use :func:`specular_diffuse_split`.

**Raises** ``ValueError``: *image_rgb* is not a valid ``(H, W, 3)`` linear
RGB image (see :func:`specular_diffuse_split`); *illuminant_rgb* is not a
non-zero 3-vector.

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

[specular_diffuse_split](specular_diffuse_split.md) · [specular_coefficient_map](specular_coefficient_map.md) · [illuminant_from_dichromatic_planes](illuminant_from_dichromatic_planes.md)

## 同カテゴリ(`dichromatic`)

[specular_diffuse_split](specular_diffuse_split.md) · [specular_coefficient_map](specular_coefficient_map.md) · [illuminant_from_dichromatic_planes](illuminant_from_dichromatic_planes.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
