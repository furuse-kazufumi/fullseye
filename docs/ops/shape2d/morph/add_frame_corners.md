---
op: add_frame_corners
dim: shape2d
category: morph
in: pairs
out: pairs
examples: [shape2d_morph_descriptor_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# add_frame_corners — SHAPE2D `morph` op

- **データ種**: `pairs` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.add_frame_corners(pts, shape)` (実装を直接呼ぶなら `import imagemorph; imagemorph.add_frame_corners(pts, shape)`、台帳から引くなら `opsshape2d.get("add_frame_corners")`)

## 使い方

点群に画像の四隅(+辺の中点)を固定点として足す。

ワープの三角形分割が画像全体を覆い、凸包の外側にできる穴を防ぐための定番処置。
src/dst の両方に同じ順序で足せば、四隅は「動かない対応点」として働く。

足す 8 点は画素中心座標 ``(x, y)`` で、``W-1`` / ``H-1`` を端とする:
``(0,0) (xm,0) (W-1,0) (0,ym) (W-1,ym) (0,H-1) (xm,H-1) (W-1,H-1)``
(``xm = (W-1)/2``、``ym = (H-1)/2``)。この順で末尾に連結する。

- ``pts``: ``(N, 2)`` の **(x, y)**(x = 列、y = 行)、有限。``(row, col)`` を渡すと
  x と y が入れ替わったまま通る(例外は出ない)。
- ``shape``: 画像の ``shape``(``(H, W)`` でも ``(H, W, C)`` でも先頭 2 つを使う)。
- 返り値: ``(N + 8, 2)`` float64。
- 元の点が既に枠上や枠外にあっても検査しない。枠外の対応点は Delaunay 分割で
  枠の三角形と交差し、ワープが歪む。

``morph`` / ``morph_sequence`` は ``with_corners=True`` で内部的にこれを両方の
点群に掛ける。``warp_piecewise_affine`` / ``warp_tps_image`` を直接呼ぶときは
自分で ``src`` と ``dst`` の両方に足すこと。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape2d_morph_descriptor_tour](../../../../examples/shape2d_morph_descriptor_tour.py) — `py -3.11 examples/shape2d_morph_descriptor_tour.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[elliptic_fourier](../descriptor/elliptic_fourier.md) · [fourier_smooth](../descriptor/fourier_smooth.md) · [warp_tps_image](warp_tps_image.md) · [warp_piecewise_affine](warp_piecewise_affine.md) · [morph](morph.md) · [morph_sequence](morph_sequence.md)

## 同カテゴリ(`morph`)

[warp_tps_image](warp_tps_image.md) · [warp_piecewise_affine](warp_piecewise_affine.md) · [blend](blend.md) · [morph](morph.md) · [morph_sequence](morph_sequence.md)

---
*Provenance: imagemorph.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
