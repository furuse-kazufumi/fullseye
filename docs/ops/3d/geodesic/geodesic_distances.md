---
op: geodesic_distances
dim: 3d
category: geodesic
in: points
out: measurement
examples: [geodesic_distance]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# geodesic_distances — 3D `geodesic` op

- **データ種**: `points` → `measurement`
- **呼び出し**: `import geodesic3d; geodesic3d.geodesic_distances(points: numpy.ndarray, source: int, k: int = 8) -> numpy.ndarray` (または `ops3d.get("geodesic_distances")`)

## 使い方

source から全点への測地距離(kNN グラフ上 Dijkstra)。→ (N,) float(不達は inf)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geodesic_distance](../../../../examples_3d/geodesic_distance.py) — `py -3.11 examples_3d/geodesic_distance.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`geodesic`)

[geodesic_mesh](geodesic_mesh.md) · [farthest_point_sampling](farthest_point_sampling.md) · [knn_graph](knn_graph.md)

---
*Provenance: geodesic3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
