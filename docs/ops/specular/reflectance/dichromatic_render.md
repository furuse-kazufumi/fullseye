---
op: dichromatic_render
dim: specular
category: reflectance
in: normalmap
out: rgbimage
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# dichromatic_render — SPECULAR `reflectance` op

- **データ種**: `normalmap` → `rgbimage`
- **呼び出し**: `import specularity; specularity.dichromatic_render(normals, albedo_rgb=(0.8, 0.55, 0.35), light=(0.3, 0.2, 1.0), illuminant_rgb=(1.0, 1.0, 1.0), view=(0.0, 0.0, 1.0), specular=0.25, model='blinn_phong', shininess=32.0, roughness=0.3, f0=0.04, ambient=0.0)` (または `opsspecular.get("dichromatic_render")`)

## 使い方

Forward dichromatic model: render a known highlight so a separation can be checked against it. → (H, W, 3).

``I = albedo_rgb * max(n.l, 0) + specular * lobe(n) * illuminant_unit``, the
body term coming straight from :func:`photometric.render_lambertian` (called,
not re-implemented, so the two modules cannot drift apart in convention) and
the interface term carrying the **illuminant** colour, which is what makes
the image obey the dichromatic model exactly.

*albedo_rgb* may be a single ``(3,)`` colour — the single-material case that
:func:`specular_diffuse_split` handles without help — or an ``(H, W, 3)``
map, which is the textured case that needs ``body_rgb`` passed to the split.

*model* selects the lobe: ``"blinn_phong"`` (*shininess*) or
``"microfacet"`` (*roughness*, *f0*). Both are available on purpose: the
separation operators must be blind to the lobe shape, and swapping the model
is how that is tested rather than asserted.

**This is a shading model, not light transport.** No interreflection, no
cast shadow, no subsurface term, no occlusion between pixels — the same
boundary :mod:`visiondesign` draws. Its purpose is a synthetic image whose
decomposition is known exactly.

**Raises** ``ValueError``: geometry problems as in
:func:`brdf_blinn_phong`; *albedo_rgb* is neither ``(3,)`` nor
``(H, W, 3)``; *specular* or *ambient* is negative, non-finite, a string or
a bool; *model* is not in :data:`BRDF_MODELS`.

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

[specular_diffuse_split](../dichromatic/specular_diffuse_split.md) · [specular_coefficient_map](../dichromatic/specular_coefficient_map.md) · [specular_free_transform](../dichromatic/specular_free_transform.md) · [illuminant_from_dichromatic_planes](../dichromatic/illuminant_from_dichromatic_planes.md)

## 同カテゴリ(`reflectance`)

[brdf_blinn_phong](brdf_blinn_phong.md) · [brdf_microfacet](brdf_microfacet.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
