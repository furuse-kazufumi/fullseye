---
op: sun_bloom_fit
dim: geocam
category: sun
in: image2d
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# sun_bloom_fit — GEOCAM `sun` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sun_bloom_fit(image, threshold=0.97, ignore_top_rows=0, min_area=30, max_area_frac=0.15, min_rim_fraction=0.3)` (実装を直接呼ぶなら `import geocam; geocam.sun_bloom_fit(image, threshold=0.97, ignore_top_rows=0, min_area=30, max_area_frac=0.15, min_rim_fraction=0.3)`、台帳から引くなら `opsgeocam.get("sun_bloom_fit")`)

## 使い方

実写の太陽 = センサを飽和させる**ブルーム**(円盤より大きい、露出で大きさが変わる、画像の縁や文字の帯で切れる)。
最大の飽和塊の**縁**に円を当てて中心を返す → table。重心は塊が切れると切れた側の反対へ偏る(実測 15 px)ので、
切れた縁(画像の外周と ``ignore_top_rows`` の帯に触れる画素)を捨てた残りの弧に代数的最小二乗(Kåsa 1976)で円を当てる。

``sun_pixel_position`` は「詰まった小さな円盤」を前提にした合成向けの門で、実写の道路カメラでは局名の白い
文字・標識・白い車を太陽と読む(Fintraffic 天候カメラで 24/24 が誤検出、2026-09-21)。この op は**太陽と決めない**:
円の中心と半径・残差・切れの有無を返し、太陽かどうかは時刻どおりに動くかで決める
(``camera_orientation_from_sun_candidates``)。

Args:
    image: (H, W) float、0〜1。
    threshold: 飽和とみなす絶対値。
    ignore_top_rows: 上端の何行を無視するか(局名などの文字の帯)。
    min_area: 塊の最小画素数。
    max_area_frac: 塊の最大面積(画像に対する比)—— 空全体が飛んだ写真を拒む。
    min_rim_fraction: 切れていない縁が円周の何割以上要るか(これ未満は「切れすぎ」で ValueError)。
Returns:
    table: ``u`` / ``v``(円の中心)/ ``r``(半径 px)/ ``rms_px``(縁の半径残差)/ ``area``(塊の画素数)/
    ``clipped``(1 = 縁のどこかが切れている)/ ``rim_fraction`` / ``centroid_u`` / ``centroid_v``(比較用の重心)。

## 詳しい使い方ガイド

- [geocam ファミリ ガイド](../guides/geocam.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[render_skyline_view](../skyline/render_skyline_view.md) · [camera_orientation_from_skyline](../orientation/camera_orientation_from_skyline.md)

## 同カテゴリ(`sun`)

[sun_position](sun_position.md) · [sun_pixel_position](sun_pixel_position.md) · [camera_orientation_from_sun](camera_orientation_from_sun.md) · [camera_orientation_from_sun_candidates](camera_orientation_from_sun_candidates.md)

---
*Provenance: geocam.py — GEOCAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
