---
op: area_center
dim: 2d
category: features
in: region
out: match
halcon: area_center
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# area_center — 2D `features` op

- **データ種**: `region` → `match`
- **呼び出し**: `fullseye.apply(img, "area_center", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `area_center`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

領域の面積と重心を、解像度に依らない正規化済みの 3 成分ベクトル
(面積比 = 面積/画像画素数、正規化重心行、正規化重心列)として返す。1
スカラーでは (Area, Row, Column) を表せないため、``match`` ソート(1 次元
ベクトル、``ncc_locate`` と同じ形)で返す点が他の region 特徴 op と異なる。
領域が空のときは (0, 0.5, 0.5)(面積ゼロ・中心=画像中心)を返す fail-soft
仕様。HALCON の ``area_center``（Area and center of regions.）に相当。

``a``, ``b`` は未使用。

## 詳しい使い方ガイド

- [gallery2d_features ファミリ ガイド](../guides/gallery2d_features.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_features](../../../../examples/gallery2d_features.py) — `py -3.11 examples/gallery2d_features.py`

## 型が繋がる次の op(`match` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`features`)

[blob_count](blob_count.md) · [area_frac](area_frac.md) · [count_contours](count_contours.md) · [total_length](total_length.md) · [vol_count](vol_count.md) · [sk_euler](sk_euler.md) · [sk_entropy_feat](sk_entropy_feat.md) · [sk_blur_effect](sk_blur_effect.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
