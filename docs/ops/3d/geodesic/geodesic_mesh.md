---
op: geodesic_mesh
dim: 3d
category: geodesic
in: mesh
out: signal
examples: [pcl_geodesic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# geodesic_mesh — 3D `geodesic` op

- **データ種**: `mesh` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.geodesic_mesh(vertices: numpy.ndarray, faces: numpy.ndarray, source: int) -> numpy.ndarray` (実装を直接呼ぶなら `import geodesic3d; geodesic3d.geodesic_mesh(vertices: numpy.ndarray, faces: numpy.ndarray, source: int) -> numpy.ndarray`、台帳から引くなら `ops3d.get("geodesic_mesh")`)

## 使い方

三角メッシュのエッジグラフ上 Dijkstra で source から各頂点への測地距離。→ (V,) float。

各三角形の 3 辺 (0,1),(1,2),(2,0) を無向辺として集め、(min,max) で一意化してから辺長 = 両端
頂点の Euclid 距離を重みにした疎グラフを作り、``dijkstra(directed=False)`` で source からの
最短路長を返す。``d[source] = 0``、source と辺で繋がらない頂点は ``inf``。単位は頂点座標の単位。

- ``vertices``: (V,3) 頂点座標(float64 に変換)。``faces``: (M,3) 頂点添字(int に変換)。
- ``source``: 始点頂点の添字。
- ``faces`` が空のときは全頂点 ``inf``(source が範囲内ならそこだけ 0)を返し、例外は出さない。

実装上の要点: ``csr_matrix`` は同じ (i,j) を重複して渡すと重みを黙って加算するため、重複面・
非多様体・巻き順が不揃いなメッシュでも距離が膨らまないよう辺を一意化している。退化辺(i==j)は
捨てる。距離は辺に沿った折れ線長なので、粗いメッシュでは真の測地距離より長め(辺の走り方に
依存する異方性)になる。``voxel_to_mesh`` や ``convex_hull`` が返す (verts, faces) を
そのまま渡せる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pcl_geodesic](../../../../examples_3d/pcl_geodesic.py) — `py -3.11 examples_3d/pcl_geodesic.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`geodesic`)

[geodesic_distances](geodesic_distances.md) · [farthest_point_sampling](farthest_point_sampling.md) · [knn_graph](knn_graph.md)

---
*Provenance: geodesic3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
