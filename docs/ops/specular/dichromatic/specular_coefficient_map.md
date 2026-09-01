---
op: specular_coefficient_map
dim: specular
category: dichromatic
in: rgbimage
out: image2d
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# specular_coefficient_map — SPECULAR `dichromatic` op

- **データ種**: `rgbimage` → `image2d`
- **呼び出し**: `import specularity; specularity.specular_coefficient_map(image_rgb, illuminant_rgb=(1.0, 1.0, 1.0), body_rgb=None, max_rank_ratio=0.1, max_negative_frac=0.02)` (または `opsspecular.get("specular_coefficient_map")`)

## 使い方

The scalar interface (specular) coefficient of the dichromatic model. → (H, W).

The same decomposition as :func:`specular_diffuse_split`, returning the
scalar ``m_s(x)`` instead of the coloured image ``m_s(x) * G``. That scalar
is what an inspection routine thresholds: it is the amount of light the
surface reflected *as a mirror does*, in the units of the input radiance,
and it is zero wherever the surface behaved as a Lambertian body.

``specular_coefficient_map(...) * illuminant_unit`` equals the second return
value of :func:`specular_diffuse_split` exactly, by construction — the two
operators share one core.

Arguments, guards and honest limits are identical to
:func:`specular_diffuse_split` — including the fact that the two guards
bound gross violations only.

**Raises** ``ValueError``: exactly the same conditions as
:func:`specular_diffuse_split` (invalid image, invalid illuminant,
identically zero image, body colour parallel to the illuminant, either
guard firing, fewer than 3 pixels on the uniform-body route, invalid
*body_rgb*).

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

## 同カテゴリ(`dichromatic`)

[specular_diffuse_split](specular_diffuse_split.md) · [specular_free_transform](specular_free_transform.md) · [illuminant_from_dichromatic_planes](illuminant_from_dichromatic_planes.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
