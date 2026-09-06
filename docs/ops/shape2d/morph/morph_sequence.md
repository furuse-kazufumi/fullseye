---
op: morph_sequence
dim: shape2d
category: morph
in: image2d × image2d × pairs × pairs
out: images
examples: [image_morph]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# morph_sequence — SHAPE2D `morph` op

- **データ種**: `image2d × image2d × pairs × pairs` → `images`
- **呼び出し**: `import imagemorph; imagemorph.morph_sequence(imgA, imgB, ptsA, ptsB, n=7, method='affine', lam=0.0, with_corners=True)` (または `opsshape2d.get("morph_sequence")`)

## 使い方

alpha を 0→1 に n 段で振ったモーフ列(A から B へ滑らかに変わる各フレーム)。

返り値: 長さ n の list。先頭が A、末尾が B に一致する。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_morph](../../../../examples/image_morph.py) — `py -3.11 examples/image_morph.py`

## 型が繋がる次の op(`images` を入力に取れる)

—

## 同カテゴリ(`morph`)

[add_frame_corners](add_frame_corners.md) · [warp_tps_image](warp_tps_image.md) · [warp_piecewise_affine](warp_piecewise_affine.md) · [blend](blend.md) · [morph](morph.md)

---
*Provenance: imagemorph.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
