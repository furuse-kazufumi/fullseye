---
op: radial_light
dim: gfx2d
category: light
in: 
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# radial_light — GFX2D `light` op

- **データ種**: `なし` → `rgb`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import gfx2d; gfx2d.radial_light(height, width, x, y, radius, intensity=1.0, falloff='smooth', color='emphasis', scheme='okabe_ito')` (または `opsgfx2d.get("radial_light")`)

## 使い方

A radial light map, ``rgb`` ``(H, W, 3)``, centred on ``(x, y)``.

``falloff``:

* ``"smooth"`` — ``(1 - t^2)^2``, compactly supported: exactly zero at and
  beyond ``radius``. The default, because a light that ends somewhere is the
  only kind you can budget.
* ``"linear"`` — ``1 - t``, also compact.
* ``"inverse_square"`` — ``1 / (1 + (3t)^2)``, the physical law softened at
  the origin. **Not** compactly supported: it is 10 % of peak at the nominal
  radius and never reaches zero, so a scene full of these never gets dark.

The value at the centre is exactly ``intensity * color``. This is a
*linear-light* quantity: add lights together, then encode once.

With ``intensity > 1`` the result leaves ``[0, 1]`` — deliberately, because a
light map is not a picture. :func:`light_mask` accepts it; the operators that
take an ``rgb`` *image* reject it with the documented range error rather than
clipping a light budget behind your back.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](light_mask.md) · [normal_map_decode](normal_map_decode.md) · [bloom](../post/bloom.md) · [vignette](../post/vignette.md) · [chromatic_aberration](../post/chromatic_aberration.md)

## 同カテゴリ(`light`)

[light_mask](light_mask.md) · [normal_map_decode](normal_map_decode.md) · [normal_map_shade](normal_map_shade.md) · [shadow_cast_2d](shadow_cast_2d.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
