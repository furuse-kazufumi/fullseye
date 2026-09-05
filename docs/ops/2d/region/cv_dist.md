---
op: cv_dist
dim: 2d
category: region
in: region
out: image
halcon: distance_transform
examples: [gallery2d_region]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# cv_dist — 2D `region` op

- **データ種**: `region` → `image`
- **呼び出し**: `fullseye.apply(img, "cv_dist", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `distance_transform`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

距離変換(distance transform、OpenCV 実装、L2/ユークリッド近似)。前景領域の各画素について、最も近い背景画素までの距離を計算し、画像として返す —— 領域の「太さ」や中心線抽出の下処理に使う。

HALCON の `distance_transform`(Compute the distance transformation of a region.)に相当。実装は ``cv2.distanceTransform(_u8(binm(v)), DIST_L2, maskSize=3)`` を正規化したもの(cv2 は float32 で返すが、契約に合わせて float64 化 —— 2026-09-03 実測でベンチマーク済み)。maskSize=3 は 3x3 近傍での近似計算(厳密なユークリッド距離ではなく高速近似)。a, b は未使用。

## 詳しい使い方ガイド

- [gallery2d_region ファミリ ガイド](../guides/gallery2d_region.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_region](../../../../examples/gallery2d_region.py) — `py -3.11 examples/gallery2d_region.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`region`)

[reg_erode](reg_erode.md) · [reg_dilate](reg_dilate.md) · [reg_open](reg_open.md) · [reg_close](reg_close.md) · [fill_holes](fill_holes.md) · [select_largest](select_largest.md) · [remove_small](remove_small.md) · [invert_region](invert_region.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
