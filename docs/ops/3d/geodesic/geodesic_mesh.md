---
op: geodesic_mesh
dim: 3d
category: geodesic
in: mesh
out: measurement
examples: [pcl_geodesic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# geodesic_mesh — 3D `geodesic` op

- **データ種**: `mesh` → `measurement`
- **呼び出し**: `import geodesic3d; geodesic3d.geodesic_mesh(vertices: numpy.ndarray, faces: numpy.ndarray, source: int) -> numpy.ndarray` (または `ops3d.get("geodesic_mesh")`)

## 使い方

三角メッシュのエッジグラフ上 Dijkstra で source から各頂点への測地距離。→ (V,) float。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pcl_geodesic](../../../../examples_3d/pcl_geodesic.py) — `py -3.11 examples_3d/pcl_geodesic.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`geodesic`)

[geodesic_distances](geodesic_distances.md) · [farthest_point_sampling](farthest_point_sampling.md) · [knn_graph](knn_graph.md)

---
*Provenance: geodesic3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
