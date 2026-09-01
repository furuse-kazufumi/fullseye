---
op: brdf_microfacet
dim: specular
category: reflectance
in: normalmap
out: image2d
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# brdf_microfacet — SPECULAR `reflectance` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import specularity; specularity.brdf_microfacet(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0), roughness=0.3, f0=0.04)` (または `opsspecular.get("brdf_microfacet")`)

## 使い方

GGX / Trowbridge-Reitz microfacet specular BRDF. → (H, W), units 1/sr.

``f_s = D * G * F / (4 (n.l) (n.v))`` with

* ``D`` the Trowbridge-Reitz (1975) / GGX normal distribution,
  ``a^2 / (pi * ((n.h)^2 (a^2 - 1) + 1)^2)`` for ``a = roughness^2``, which
  integrates to 1 against ``(n.h) dw`` over the hemisphere — measured by
  20000-point midpoint quadrature in ``tests/test_specularity.py`` at
  relative errors 3.2e-07, 6.3e-08 and 4.0e-09 for roughness 0.2, 0.3 and
  0.6, all of it quadrature error (the 200000-point rule gives 3.2e-09,
  6.3e-10, 4.0e-11, exactly the 100x a midpoint rule predicts);
* ``G`` the separable Smith (1967) masking-shadowing term with the GGX
  lambda;
* ``F`` Schlick's (1994) Fresnel approximation,
  ``f0 + (1 - f0) (1 - v.h)^5``. *f0* is the normal-incidence reflectance:
  about 0.04 for common dielectrics, 0.5 to 1.0 for metals. When the exact
  Fresnel curve matters, use ``match3d.fresnel_reflectance`` instead — this
  is the approximation the microfacet literature specifies, and it is named
  rather than hidden.

Exact ground truth it reproduces: at normal incidence with light, view and
normal aligned, every geometric factor is 1 and the value collapses to
``f0 / (4 pi roughness^4)`` in closed form — reproduced **bit for bit** at
roughness 0.3, 0.5 and 1.0 and to 3.3e-16 relative at roughness 0.1, which
took rewriting the GGX denominator to avoid a cancellation (see the comment
at the code; the textbook arrangement was off by 2.2e-13 relative at the
peak). The lobe is reciprocal in light and view to machine precision
(measured 1.7e-16), and its maximum sits at the half-vector.

``roughness`` is the perceptual parameter, squared once to reach the GGX
``alpha`` — the convention that makes a linear slider feel linear. A
perfectly smooth surface (``roughness = 0``) is a delta function, not a
finite BRDF, so it is refused rather than returned as an infinity.

**Raises** ``ValueError``: geometry problems as in
:func:`brdf_blinn_phong`; *roughness* outside ``(0, 1]``; *f0* outside
``[0, 1]``.

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

[brdf_blinn_phong](brdf_blinn_phong.md) · [dichromatic_render](dichromatic_render.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
