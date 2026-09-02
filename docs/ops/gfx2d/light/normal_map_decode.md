---
op: normal_map_decode
dim: gfx2d
category: light
in: rgb
out: normalmap
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# normal_map_decode — GFX2D `light` op

- **データ種**: `rgb` → `normalmap`
- **呼び出し**: `import gfx2d; gfx2d.normal_map_decode(rgb)` (または `opsgfx2d.get("normal_map_decode")`)

## 使い方

Tangent-space normal map ``rgb`` in ``[0, 1]`` to unit vectors ``(H, W, 3)``.

The usual encoding ``n = 2c - 1`` followed by normalisation. The result is
the ``normalmap`` sort the rest of the library already speaks, so a decoded
map can go straight into the 3-D normals family.

Raises ValueError: a pixel whose decoded vector has zero length (the encoded
colour was exactly mid-grey), because normalising it would silently invent a
direction.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[normal_map_shade](normal_map_shade.md)

## 同カテゴリ(`light`)

[radial_light](radial_light.md) · [light_mask](light_mask.md) · [normal_map_shade](normal_map_shade.md) · [shadow_cast_2d](shadow_cast_2d.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
