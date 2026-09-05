---
op: vol_count
dim: 2d
category: features
in: volume
out: feature
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# vol_count — 2D `features` op

- **データ種**: `volume` → `feature`
- **呼び出し**: `fullseye.apply(img, "vol_count", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

3D ボリューム中の連結成分（ブロブ）の個数を返す特徴量。対応する HALCON op は指定されていない。

``a``, ``b`` は未使用。しきい値は ``0.5`` に固定（``v > 0.5`` で二値化してから ``scipy.ndimage.label``）。連結性は scipy の既定構造要素（面で接する 6 近傍相当）で、稜・頂点だけで接する（26 近傍でしか繋がらない）ボクセルは別ブロブとして数えられる——2-D の ``_blob_count`` が HALCON パリティのため 8 連結を明示指定しているのとは対照的に、こちらは既定のまま連結性を明示していない。

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

[blob_count](blob_count.md) · [area_frac](area_frac.md) · [count_contours](count_contours.md) · [total_length](total_length.md) · [sk_euler](sk_euler.md) · [sk_entropy_feat](sk_entropy_feat.md) · [sk_blur_effect](sk_blur_effect.md) · [cv_cc_count](cv_cc_count.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
