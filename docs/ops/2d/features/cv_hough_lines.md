---
op: cv_hough_lines
dim: 2d
category: features
in: image
out: feature
halcon: hough_lines
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# cv_hough_lines — 2D `features` op

- **データ種**: `image` → `feature`
- **呼び出し**: `fullseye.apply(img, "cv_hough_lines", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `hough_lines`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

確率的 Hough 変換による直線(線分)検出(1 スカラー特徴量、OpenCV 実装)。まず Canny でエッジ画像を作り、そこから直線状に並ぶエッジ画素の集合を投票方式で探して線分として検出する —— ここでは検出できた線分の本数だけを返す(0 本なら 0)。

HALCON の `hough_lines`(Detect lines in edge images with the help of the Hough transform and returns it in HNF.)に相当(近似。線のパラメータではなく本数のみ)。実装は ``cv2.HoughLinesP(Canny(_u8(v),50,150), 1, pi/180, threshold=int(20+40*a), minLineLength=int(10+20*b), maxLineGap=5)`` —— a は投票数のしきい値(直線と認める最低票数)を 20〜60 に、b は最小線分長を 10〜30 に振る。Canny の内部しきい値(50, 150)と maxLineGap(5)は固定。

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
