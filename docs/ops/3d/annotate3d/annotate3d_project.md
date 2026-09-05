---
op: annotate3d_project
dim: 3d
category: annotate3d
in: points
out: table
examples: [annotate3d_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# annotate3d_project — 3D `annotate3d` op

- **データ種**: `points` → `table`
- **呼び出し**: `import annotate3d; annotate3d.annotate3d_project(points, pose, K, depth=None, shape=None, occlusion_tol=0.01)` (または `ops3d.get("annotate3d_project")`)

## 使い方

table(dict)を返す: 3-D 点の画素座標・前方距離・画像内/遮蔽の判定(:func:`project_anchors`)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate3d_figure](../../../../examples_3d/annotate3d_figure.py) — `py -3.11 examples_3d/annotate3d_figure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`annotate3d`)

[annotate3d_arrow](annotate3d_arrow.md) · [annotate3d_label](annotate3d_label.md) · [annotate3d_scale_bar](annotate3d_scale_bar.md) · [annotate3d_axes](annotate3d_axes.md) · [annotate3d_bbox](annotate3d_bbox.md) · [annotate3d_measure](annotate3d_measure.md)

---
*Provenance: annotate3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
