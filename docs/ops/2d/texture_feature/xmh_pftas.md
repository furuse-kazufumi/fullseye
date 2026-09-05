---
op: xmh_pftas
dim: 2d
category: texture-feature
in: image
out: feature
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# xmh_pftas — 2D `texture-feature` op

- **データ種**: `image` → `feature`
- **呼び出し**: `fullseye.apply(img, "xmh_pftas", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

PFTAS(parameter-free threshold adjacency statistics、``mahotas.features.pftas``)54 次元特徴ベクトルの分散。隣接画素の濃淡関係をパラメータ無しの閾値で数えたヒストグラム群をまとめたテクスチャ特徴。

``a``, ``b`` は未使用。2026-09-02 実測: 54 次元の平均を使うと、正規化ヒストグラムの性質上ほぼ整数/54 の値しか取らず、12 通りの画像(4 サイズ x 3 内容)で相異なる値がわずか 2 個(事実上の定数)だった。分散にすると分布の広がりが残り画像ごとに変化するため、ここでは分散を採用している。

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

## 同カテゴリ(`texture-feature`)

—

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
