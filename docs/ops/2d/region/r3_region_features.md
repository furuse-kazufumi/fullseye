---
op: r3_region_features
dim: 2d
category: region
in: region
out: feature
halcon: region_features
examples: [gallery2d_region]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# r3_region_features — 2D `region` op

- **データ種**: `region` → `feature`
- **呼び出し**: `fullseye.apply(img, "r3_region_features", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `region_features`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

領域の形状特徴量を 1 つ返す（HALCON ``region_features`` の一部を実装）。

``a < 0.5`` なら正規化面積（前景画素数/全画素数）、``a >= 0.5`` なら真円度の逆数にあたるコンパクトネス ``P^2 / (4*pi*A)``（``P`` は 4 連結境界の周囲長。円で 1、正方形で約 1.27、細長いほど大きくなる）を返す。``b`` は未使用。領域が空なら 0.0。

## 詳しい使い方ガイド

- [gallery2d_region ファミリ ガイド](../guides/gallery2d_region.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_region](../../../../examples/gallery2d_region.py) — `py -3.11 examples/gallery2d_region.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`region`)

[reg_erode](reg_erode.md) · [reg_dilate](reg_dilate.md) · [reg_open](reg_open.md) · [reg_close](reg_close.md) · [fill_holes](fill_holes.md) · [select_largest](select_largest.md) · [remove_small](remove_small.md) · [invert_region](invert_region.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
