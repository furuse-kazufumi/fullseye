---
op: register_cross
dim: 3d
category: fusion
in: any × any
out: pose
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# register_cross — 3D `fusion` op

- **データ種**: `any × any` → `pose`
- **呼び出し**: `import fuse3d; fuse3d.register_cross(src, src_kind, dst, dst_kind, method='fpfh', samples=15000, **kw)` (または `ops3d.get("register_cross")`)

## 使い方

異種構造間の剛体登録。両者を点群へ変換 → 登録器(fpfh=大回転/icp=要 coarse init)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [reprojection_error](../pose_estimation/reprojection_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md)

## 同カテゴリ(`fusion`)

[fuse_to_voxel](fuse_to_voxel.md)

---
*Provenance: fuse3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
