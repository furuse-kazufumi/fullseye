---
op: area_center_xld
dim: 2d
category: features
in: contour
out: feature
halcon: area_center_xld
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# area_center_xld — 2D `features` op

- **データ種**: `contour` → `feature`
- **呼び出し**: `fullseye.apply(img, "area_center_xld", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `area_center_xld`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

最大の点数を持つ輪郭 1 本について、シューレース公式(靴紐公式)で
多角形面積を求め、画像の全画素数で正規化して返す。HALCON の
``area_center_xld``（Area and center of gravity (centroid) of contours and
polygons.）は面積に加えて重心も返す演算子だが、この代役では面積のみを
返す(重心情報は失われる近似 ―― ``feature`` ソートが 1 スカラーである
契約上の制約)。

``a``, ``b`` は未使用。輪郭が無ければ 0 を返す。

## 詳しい使い方ガイド

- [gallery2d_features ファミリ ガイド](../guides/gallery2d_features.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_features](../../../../examples/gallery2d_features.py) — `py -3.11 examples/gallery2d_features.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`features`)

[blob_count](blob_count.md) · [area_frac](area_frac.md) · [count_contours](count_contours.md) · [total_length](total_length.md) · [vol_count](vol_count.md) · [sk_euler](sk_euler.md) · [sk_entropy_feat](sk_entropy_feat.md) · [sk_blur_effect](sk_blur_effect.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
