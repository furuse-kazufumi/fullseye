---
op: shadow_cast_2d
dim: gfx2d
category: light
in: image2d
out: image2d
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# shadow_cast_2d — GFX2D `light` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import gfx2d; gfx2d.shadow_cast_2d(occluder, x, y, steps=None, softness=0.0)` (または `opsgfx2d.get("shadow_cast_2d")`)

## 使い方

Visibility of every pixel from a point light at ``(x, y)``, as ``image2d``.

Ray-marches the segment from each pixel to the light, sampling ``occluder``
(2-D, ``[0, 1]``, 1 = fully blocking) at ``steps`` points with nearest
lookup, and returns ``1 - max(occluder along the ray)``. For a binary
occluder that is exactly 0 or 1 — no tolerance involved.

The sample **excludes** the pixel itself, so an occluder is lit on its own
light-facing surface and casts behind itself.

``softness > 0`` blurs the visibility map by that sigma afterwards, which is
a penumbra-shaped lie rather than a penumbra: a real one widens with
distance from the occluder. It is offered because it looks right and named
so it cannot be mistaken for physics.

``steps`` defaults to the image diagonal, which samples about once per
pixel. **An occluder thinner than the step spacing can be missed**; that is
the honest limit of a fixed-step march and the reason ``steps`` is an
argument.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[dither](../post/dither.md)

## 同カテゴリ(`light`)

[radial_light](radial_light.md) · [light_mask](light_mask.md) · [normal_map_decode](normal_map_decode.md) · [normal_map_shade](normal_map_shade.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
