---
op: xmh_zernike
dim: 2d
category: texture/shape-feature
in: image
out: feature
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# xmh_zernike — 2D `texture/shape-feature` op

- **データ種**: `image` → `feature`
- **呼び出し**: `fullseye.apply(img, "xmh_zernike", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

ツェルニケモーメント(Zernike moments、``mahotas.features.zernike_moments``)の総和。単位円に写した画像の回転不変な形状/濃淡分布の特徴を 1 個の実数に潰して返す。

半径は画像の短辺の半分に固定。``a`` は次数(degree、6〜12 の整数)を振る —— 次数を上げるほど高次のモーメントまで加算され値が変わる。``b`` は未使用。モーメント成分ごとの符号や大きさの分布は総和で相殺・情報が失われるため、形状の指紋として使うには弱い。個々の成分が要る場合は ``mahotas.features.zernike_moments`` を直接呼ぶこと。

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

## 同カテゴリ(`texture/shape-feature`)

—

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
