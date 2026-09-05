---
op: xmh_majority
dim: 2d
category: region-morphology
in: region
out: region
examples: [gallery2d_region]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# xmh_majority — 2D `region-morphology` op

- **データ種**: `region` → `region`
- **呼び出し**: `fullseye.apply(img, "xmh_majority", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

多数決フィルタ(``mahotas.majority_filter``)。二値領域に対し、正方近傍内で 1 が過半数を占める画素だけを 1 に残す平滑化。孤立ノイズの除去や領域境界のギザギザ均しに使う。

``a`` は窓サイズ(``2*int(1+a*4)+1`` で 3〜17 の奇数)を振る。``b`` は未使用。

## 詳しい使い方ガイド

- [gallery2d_region ファミリ ガイド](../guides/gallery2d_region.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_region](../../../../examples/gallery2d_region.py) — `py -3.11 examples/gallery2d_region.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`region-morphology`)

—

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
