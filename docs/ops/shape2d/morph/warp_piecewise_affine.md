---
op: warp_piecewise_affine
dim: shape2d
category: morph
in: image2d × pairs × pairs
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# warp_piecewise_affine — SHAPE2D `morph` op

- **データ種**: `image2d × pairs × pairs` → `image2d`
- **呼び出し**: `import imagemorph; imagemorph.warp_piecewise_affine(img, src_pts, dst_pts, order=1)` (または `opsshape2d.get("warp_piecewise_affine")`)

## 使い方

img の src_pts にある内容を dst_pts へ動かす区分アフィンワープ。

dst_pts を Delaunay 三角形分割し、各出力画素が属す三角形の重心座標を求め、
同じ重心座標で src_pts 側の対応三角形へ写して逆写像サンプルする。凸包の外側
(三角形に属さない画素)は恒等(元位置)でサンプルするため、四隅を対応点に含める
(:func:`add_frame_corners`)と穴なく画像全体を覆える。

引数:
    img: (H,W) か (H,W,C)、[0,1]。
    src_pts, dst_pts: (K,2) の (x,y)。同数・同順の対応点。
    order: 補間次数(1=バイリニア)。

返り値: img と同 shape・[0,1] の float64。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[warp_tps_image](warp_tps_image.md) · [blend](blend.md) · [morph](morph.md) · [morph_sequence](morph_sequence.md)

## 同カテゴリ(`morph`)

[add_frame_corners](add_frame_corners.md) · [warp_tps_image](warp_tps_image.md) · [blend](blend.md) · [morph](morph.md) · [morph_sequence](morph_sequence.md)

---
*Provenance: imagemorph.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
