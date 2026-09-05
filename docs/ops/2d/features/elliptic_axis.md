---
op: elliptic_axis
dim: 2d
category: features
in: region
out: feature
halcon: elliptic_axis
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# elliptic_axis — 2D `features` op

- **データ種**: `region` → `feature`
- **呼び出し**: `fullseye.apply(img, "elliptic_axis", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `elliptic_axis`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

領域に等価な楕円（equivalent ellipse、慣性モーメントが一致する楕円）の長軸と短軸の比（アスペクト比）を返す。``skimage.measure.regionprops`` の ``axis_major_length``/``axis_minor_length`` から計算し、/10 でおおよそ [0,1] 程度のスケールに収める（正規化ではないため、非常に細長い領域では 1 を超えうる）。a, b は未使用。

HALCON の ``elliptic_axis``（等価楕円の長半径・短半径そのもの 2 つの長さを返す演算）とは異なり、この実装は長さではなく比（アニソメトリー、``anisometry`` と同じ metric）だけを 1 スカラーで返す近似。

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
