---
op: knn_graph
dim: 3d
category: geodesic
in: points
out: graph
examples: [pcl_geodesic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# knn_graph — 3D `geodesic` op

- **データ種**: `points` → `graph`
- **呼び出し**: `import fullseye as fs; fs.ledger.knn_graph(points: numpy.ndarray, k: int = 8) -> Tuple[numpy.ndarray, numpy.ndarray]` (実装を直接呼ぶなら `import geodesic3d; geodesic3d.knn_graph(points: numpy.ndarray, k: int = 8) -> Tuple[numpy.ndarray, numpy.ndarray]`、台帳から引くなら `ops3d.get("knn_graph")`)

## 使い方

各点の k 近傍インデックスと Euclid 距離(自己を除く)。→ (idx (N,k) int, dist (N,k) float)。

``scipy.spatial.cKDTree`` で各点の k+1 近傍を引き、自分自身(距離 0)を除いた k 個を返す。
``idx[i, j]`` は点 i に j 番目に近い点の添字、``dist[i, j]`` はその Euclid 距離(座標の単位)で、
各行は距離の昇順。

- ``points``: (N,3) など任意次元の座標(float64 に変換)。形状の検証はしない。
- ``k``: 近傍数(既定 8)。``N-1`` を超える値は黙って ``N-1`` に切り詰める。
- N < 2 のときは例外を出さず、形 (N,0) の空配列を 2 つ返す。

罠: 座標が重複していると KD-tree が自己を列 0 に返さないことがある。その場合は行ごとに自己の
位置を探して除き、k+1 個の中に自己が無ければ最遠の 1 つを落とす(結果はやはり k 個)。
``geodesic_distances`` / ``farthest_point_sampling`` はこの結果を隣接行列(有向 CSR、
Dijkstra 側で無向化)にして測地距離の近似に使う。

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
