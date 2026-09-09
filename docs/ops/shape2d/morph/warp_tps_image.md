---
op: warp_tps_image
dim: shape2d
category: morph
in: image2d × pairs × pairs
out: image2d
examples: [shape2d_morph_descriptor_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# warp_tps_image — SHAPE2D `morph` op

- **データ種**: `image2d × pairs × pairs` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.warp_tps_image(img, src_pts, dst_pts, lam=0.0, order=1)` (実装を直接呼ぶなら `import imagemorph; imagemorph.warp_tps_image(img, src_pts, dst_pts, lam=0.0, order=1)`、台帳から引くなら `opsshape2d.get("warp_tps_image")`)

## 使い方

薄板スプラインで img の src_pts を dst_pts へ動かす滑らかなワープ。

出力座標 → 入力座標の逆写像 TPS(dst→src)を当てはめ、出力全格子で評価して
サンプルする。lam=0 なら制御点上で厳密に対応(特徴が正しく着地)、lam>0 で
変形を平滑化。区分アフィンより滑らかだが、全画素×制御点のカーネル評価コスト。

引数・返り値は :func:`warp_piecewise_affine` と同じ。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape2d_morph_descriptor_tour](../../../../examples/shape2d_morph_descriptor_tour.py) — `py -3.11 examples/shape2d_morph_descriptor_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[warp_piecewise_affine](warp_piecewise_affine.md) · [blend](blend.md) · [morph](morph.md) · [morph_sequence](morph_sequence.md)

## 同カテゴリ(`morph`)

[add_frame_corners](add_frame_corners.md) · [warp_piecewise_affine](warp_piecewise_affine.md) · [blend](blend.md) · [morph](morph.md) · [morph_sequence](morph_sequence.md)

---
*Provenance: imagemorph.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
