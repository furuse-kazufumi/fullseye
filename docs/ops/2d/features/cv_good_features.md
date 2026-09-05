---
op: cv_good_features
dim: 2d
category: features
in: image
out: feature
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# cv_good_features — 2D `features` op

- **データ種**: `image` → `feature`
- **呼び出し**: `fullseye.apply(img, "cv_good_features", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Shi-Tomasi 法による高品質コーナー検出(1 スカラー特徴量、OpenCV 実装)。cv_min_eigen と同じ最小固有値基準でコーナーらしさを評価し、非極大抑制と最小距離フィルタで間引いた上位のコーナーを検出する —— ここでは検出できた個数だけを返す(0 個なら 0)。

HALCON に直接対応するものは無い。実装は ``cv2.goodFeaturesToTrack(v, maxCorners=int(10+40*a), qualityLevel=0.01+0.1*b, minDistance=5)`` —— a は検出上限数を 10〜50 に、b は品質しきい値(最強コーナーに対する相対比。大きいほど厳しく絞り込まれ検出数が減る)を 0.01〜0.11 に振る。最小距離は 5 画素に固定。

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
