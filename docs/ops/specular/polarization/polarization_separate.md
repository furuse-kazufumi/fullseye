---
op: polarization_separate
dim: specular
category: polarization
in: polsweep
out: image2d
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# polarization_separate — SPECULAR `polarization` op

- **データ種**: `polsweep` → `image2d`
- **呼び出し**: `import specularity; specularity.polarization_separate(images, angles_deg=(0.0, 45.0, 90.0, 135.0), max_violation_frac=0.0)` (または `opsspecular.get("polarization_separate")`)

## 使い方

Split a polariser sweep into its unpolarised and linearly polarised radiance. → (diffuse, specular), both (H, W).

Fitting ``I(t) = 0.5 (S0 + S1 cos 2t + S2 sin 2t)`` per pixel gives
``I_min`` and ``I_max`` in closed form, and the classical separation
(Wolff & Boult 1991; Nayar, Fang & Boult 1997) reads

    ``diffuse  = 2 * I_min``   (the unpolarised radiance)
    ``specular = I_max - I_min`` (the linearly polarised radiance)

with ``diffuse + specular = I_min + I_max`` = the total scene radiance, so
nothing is lost or invented. Round-tripping
:func:`polarization_render` through this operator returns the inputs with a
maximum absolute error of 3.9e-16 for the four angles of a
division-of-focal-plane sensor and 4.4e-16 for a bare three-angle sweep
(measured in ``tests/test_specularity.py``).

**Read the names as shorthand.** What is recovered exactly is the
unpolarised and polarised parts. Calling them diffuse and specular assumes
diffuse reflection is unpolarised and specular reflection is fully linearly
polarised — true near Brewster's angle for a dielectric, **false at normal
incidence**, where the specular reflection is unpolarised and this operator
returns all of it as "diffuse", and unreliable for metals. The polarisation
route is complementary to the colour route
(:func:`specular_diffuse_split`), not a replacement: it needs no illuminant
colour and works on textured, multi-material surfaces, but it needs a
favourable geometry.

*max_violation_frac* is the fraction of pixels allowed to fit a negative
minimum radiance before the call fails. The default 0 is fail-closed: a
negative fitted minimum means the modulation exceeded the mean, which no
analyser can produce, and it usually means the frames and *angles_deg* are
out of order. Raise it to clamp sensor-noise-level violations to zero as a
deliberate, recorded choice.

**Raises** ``ValueError``: *images* is not an ``(N, H, W)`` stack of at
least 3 frames, or exceeds :data:`MAX_LIGHTS` / :data:`MAX_STACK_ELEMENTS`;
*angles_deg* does not match the frame count or leaves the fit
rank-deficient (two angles equal modulo 180); more than
*max_violation_frac* of the pixels fit a negative minimum.

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[polarization_render](polarization_render.md)

## 同カテゴリ(`polarization`)

[polarization_render](polarization_render.md) · [polarization_dolp_map](polarization_dolp_map.md) · [polarization_stokes](polarization_stokes.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
