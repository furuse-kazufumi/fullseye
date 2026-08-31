---
op: knn_graph
dim: 3d
category: geodesic
in: points
out: graph
examples: [pcl_geodesic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# knn_graph — 3D `geodesic` op

- **データ種**: `points` → `graph`
- **呼び出し**: `import geodesic3d; geodesic3d.knn_graph(points: numpy.ndarray, k: int = 8) -> Tuple[numpy.ndarray, numpy.ndarray]` (または `ops3d.get("knn_graph")`)

## 使い方

各点の k 近傍インデックスと Euclid 距離(自己を除く)。→ (idx (N,k) int, dist (N,k) float)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pcl_geodesic](../../../../examples_3d/pcl_geodesic.py) — `py -3.11 examples_3d/pcl_geodesic.py`

## 型が繋がる次の op(`graph` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`geodesic`)

[geodesic_distances](geodesic_distances.md) · [geodesic_mesh](geodesic_mesh.md) · [farthest_point_sampling](farthest_point_sampling.md)

---
*Provenance: geodesic3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
