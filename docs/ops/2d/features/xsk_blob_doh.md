---
op: xsk_blob_doh
dim: 2d
category: features
in: image
out: feature
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# xsk_blob_doh — 2D `features` op

- **データ種**: `image` → `feature`
- **呼び出し**: `fullseye.apply(img, "xsk_blob_doh", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

ブロブ(斑点状構造)の検出数(LoG/DoG/DoH のいずれかで検出)。

skimage.feature の Laplacian of Gaussian(LoG)/ Difference of
Gaussian(DoG)/ Determinant of Hessian(DoH)のいずれか(このコードは
3 種を共通実装しており、どれを使うかは呼び出し元がどの op 名で
登録したか —— ``xsk_blob_log`` / ``xsk_blob_dog`` / ``xsk_blob_doh``
—— で決まる)を用いてブロブを検出し、その個数をそのまま返す
(feature 出力)。

``a`` が探索する最大スケール ``max_sigma`` を 5〜25 の範囲で振る
(大きいほど大きなブロブまで拾う)。``b`` が検出しきい値
``threshold`` を 0.02〜0.17 で振る(小さいほど弱いブロブまで拾い、
検出数が増えやすい)。3 手法は速度・精度が異なる(LoG が最も正確
だが遅く、DoH はエッジに強い一方、小さいブロブを苦手とする、等)。

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
