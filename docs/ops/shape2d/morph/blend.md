---
op: blend
dim: shape2d
category: morph
in: image2d × image2d
out: image2d
examples: [image_morph]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# blend — SHAPE2D `morph` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.blend(a, b, alpha)` (実装を直接呼ぶなら `import imagemorph; imagemorph.blend(a, b, alpha)`、台帳から引くなら `opsshape2d.get("blend")`)

## 使い方

クロスディゾルブ (1-alpha)·a + alpha·b(a,b は同 shape・[0,1])。

画素ごとの線形補間。対応点でのワープは**しない**ので、目や輪郭がずれた
2 枚では二重像になる ―― 特徴を 1 つに重ねたいなら ``morph``。

- ``a``, ``b``: ``(H, W)`` または ``(H, W, C)``、同じ形。float64 に変換する。
  **NaN は 0、+Inf は 1、-Inf は 0 に無言で置き換える**(例外は出ない)。
  値域の検査はせず、結果を ``[0, 1]`` にクリップするだけなので、0〜255 の
  画像を渡すと白飛びした絵が返る。
- ``alpha``: 合成比。``[0, 1]`` に**無言でクリップ**(0 で ``a``、1 で ``b``)。
- 返り値: 入力と同形の float64、``[0, 1]``。
- 失敗: ``ValueError``(次元が 2/3 でない、空、形の不一致)。

``morph_sequence`` の各フレームは、ワープ後の 2 枚をこれと同じ式で混ぜている。

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
