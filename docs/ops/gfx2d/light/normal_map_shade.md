---
op: normal_map_shade
dim: gfx2d
category: light
in: normalmap
out: rgb
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# normal_map_shade — GFX2D `light` op

- **データ種**: `normalmap` → `rgb`
- **呼び出し**: `import gfx2d; gfx2d.normal_map_shade(normals, light_dir=(0.0, 0.0, 1.0), ambient=0.1, diffuse='reference', specular=0.0, shininess=32.0, view_dir=(0.0, 0.0, 1.0), scheme='okabe_ito')` (または `opsgfx2d.get("normal_map_shade")`)

## 使い方

Shade a 2-D normal map with one directional light (Lambert + Blinn 1977).

``normals`` is a ``normalmap``: ``(H, W, 3)`` **unit** vectors, as
:func:`normal_map_decode` returns. Non-unit input raises rather than being
normalised for you — a normal map that is not normalised is usually a map
that was never decoded, and quietly fixing it hides the mistake.

``out = diffuse * (ambient + max(n·l, 0)) + specular * max(n·h, 0)^shininess``
with ``h`` the normalised halfway vector between light and view.

Directions are ``(x, y, z)`` with **+x right, +y down, +z out of the
screen** — the same handedness as the pixel grid, so a light at
``(0, -1, 1)`` comes from above the screen. Getting the sign of y wrong
flips the perceived relief (bumps become dents) without raising anything;
that is the one thing to check on first render.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](../colorspace/srgb_to_linear.md) · [linear_to_srgb](../colorspace/linear_to_srgb.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](light_mask.md) · [normal_map_decode](normal_map_decode.md) · [bloom](../post/bloom.md) · [vignette](../post/vignette.md) · [chromatic_aberration](../post/chromatic_aberration.md)

## 同カテゴリ(`light`)

[radial_light](radial_light.md) · [light_mask](light_mask.md) · [normal_map_decode](normal_map_decode.md) · [shadow_cast_2d](shadow_cast_2d.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
