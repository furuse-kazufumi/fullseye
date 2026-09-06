---
op: blend
dim: shape2d
category: morph
in: image2d × image2d
out: image2d
examples: [image_morph]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blend — SHAPE2D `morph` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import imagemorph; imagemorph.blend(a, b, alpha)` (または `opsshape2d.get("blend")`)

## 使い方

クロスディゾルブ (1-alpha)·a + alpha·b(a,b は同 shape・[0,1])。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_morph](../../../../examples/image_morph.py) — `py -3.11 examples/image_morph.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[warp_tps_image](warp_tps_image.md) · [warp_piecewise_affine](warp_piecewise_affine.md) · [morph](morph.md) · [morph_sequence](morph_sequence.md)

## 同カテゴリ(`morph`)

[add_frame_corners](add_frame_corners.md) · [warp_tps_image](warp_tps_image.md) · [warp_piecewise_affine](warp_piecewise_affine.md) · [morph](morph.md) · [morph_sequence](morph_sequence.md)

---
*Provenance: imagemorph.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
