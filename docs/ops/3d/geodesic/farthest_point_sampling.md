---
op: farthest_point_sampling
dim: 3d
category: geodesic
in: points
out: indices
examples: [geodesic_distance, pointcloud_downsampling]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# farthest_point_sampling — 3D `geodesic` op

- **データ種**: `points` → `indices`
- **呼び出し**: `import geodesic3d; geodesic3d.farthest_point_sampling(points: numpy.ndarray, n: int, k: int = 8, start: int = 0) -> numpy.ndarray` (または `ops3d.get("farthest_point_sampling")`)

## 使い方

測地距離での最遠点サンプリング(均等間引き)。→ 選択インデックス列 (n,) int。

``start`` を最初の代表点にし、「既に選んだ点集合への測地距離が最大の点」を 1 つずつ追加する
貪欲法(FPS)。距離は ``knn_graph(points, k)`` の無向 kNN グラフ上の Dijkstra で測り、既選択
集合への距離は各代表点の単源距離の要素ごと最小 ``mind`` として保持、代表点を 1 つ足すたびに
``mind = min(mind, d_new)`` で更新する。代表点 1 つにつき Dijkstra 1 回なので計算量は n 回分の
単源最短路。乱数は使わず決定的。

- ``points``: (N,3) 点群。``n``: 欲しい点数。``N`` を超えると ``N`` に、負なら 0 に丸める
  (0 なら空配列)。
- ``k``: kNN グラフの近傍数(既定 8)。``start``: 最初の代表点(``start % N`` で範囲内に折り返す)。
- 返り値は選んだ順の添字列(先頭が ``start``)。``points[idx]`` で代表点群になる。

罠: グラフが複数の連結成分に分かれていると、不達の点は距離 ``inf`` なので未到達の成分が先に
選ばれる(argmax が ``inf`` を拾う)。「離れた塊から先に取る」挙動になるので、成分ごとに
均等に間引きたいなら ``euclidean_cluster`` 等で分けてから使う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geodesic_distance](../../../../examples_3d/geodesic_distance.py) — `py -3.11 examples_3d/geodesic_distance.py`
- [pointcloud_downsampling](../../../../examples_3d/pointcloud_downsampling.py) — `py -3.11 examples_3d/pointcloud_downsampling.py`

## 型が繋がる次の op(`indices` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`geodesic`)

[geodesic_distances](geodesic_distances.md) · [geodesic_mesh](geodesic_mesh.md) · [knn_graph](knn_graph.md)

---
*Provenance: geodesic3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
