---
op: geodesic_distances
dim: 3d
category: geodesic
in: points
out: signal
examples: [geodesic_distance]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# geodesic_distances — 3D `geodesic` op

- **データ種**: `points` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.geodesic_distances(points: numpy.ndarray, source: int, k: int = 8) -> numpy.ndarray` (実装を直接呼ぶなら `import geodesic3d; geodesic3d.geodesic_distances(points: numpy.ndarray, source: int, k: int = 8) -> numpy.ndarray`、台帳から引くなら `ops3d.get("geodesic_distances")`)

## 使い方

source から全点への測地距離(kNN グラフ上 Dijkstra)。→ (N,) float(不達は inf)。

``knn_graph(points, k)`` で作った k 近傍グラフ(辺の重み = 点間の Euclid 距離 = 弦長)を
``directed=False`` で無向化し、``scipy.sparse.csgraph.dijkstra`` で単一始点最短路を解く。
``d[i]`` は source から点 i までのグラフ上の経路長で ``d[source] = 0``、source と繋がっていない
連結成分の点は ``inf``。単位は座標の単位そのまま。

- ``points``: (N,3) の点群(float64 に変換)。
- ``source``: 始点の添字(0..N-1 の整数。範囲外は scipy 側で例外)。
- ``k``: 近傍数(既定 8)。小さいとグラフが分断されて ``inf`` が増え、大きいと離れた面どうしを
  直結する「近道」が生まれて曲面に沿わない距離になる(薄い板の表裏、折り返した面など)。

精度: 辺が弦長なので弧をわずかに過小評価する一方、経路のジグザグが過大評価を生む(モジュール
docstring の Bernstein らの挟み込み評価を参照)。三角メッシュがあるなら近傍数に依存しない
``geodesic_mesh`` を使う。この距離で均等に間引くには ``farthest_point_sampling``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geodesic_distance](../../../../examples_3d/geodesic_distance.py) — `py -3.11 examples_3d/geodesic_distance.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`geodesic`)

[geodesic_mesh](geodesic_mesh.md) · [farthest_point_sampling](farthest_point_sampling.md) · [knn_graph](knn_graph.md)

---
*Provenance: geodesic3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
