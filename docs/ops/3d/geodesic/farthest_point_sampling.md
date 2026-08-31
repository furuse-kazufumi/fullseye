---
op: farthest_point_sampling
dim: 3d
category: geodesic
in: points
out: keypoints
examples: [geodesic_distance, pointcloud_downsampling]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# farthest_point_sampling — 3D `geodesic` op

- **データ種**: `points` → `keypoints`
- **呼び出し**: `import geodesic3d; geodesic3d.farthest_point_sampling(points: numpy.ndarray, n: int, k: int = 8, start: int = 0) -> numpy.ndarray` (または `ops3d.get("farthest_point_sampling")`)

## 使い方

測地距離での最遠点サンプリング(均等間引き)。→ 選択インデックス列 (n,) int。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geodesic_distance](../../../../examples_3d/geodesic_distance.py) — `py -3.11 examples_3d/geodesic_distance.py`
- [pointcloud_downsampling](../../../../examples_3d/pointcloud_downsampling.py) — `py -3.11 examples_3d/pointcloud_downsampling.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`geodesic`)

[geodesic_distances](geodesic_distances.md) · [geodesic_mesh](geodesic_mesh.md) · [knn_graph](knn_graph.md)

---
*Provenance: geodesic3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
