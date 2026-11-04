---
op: knn_graph_to_conn_graph
dim: reprconv
category: structure
in: graph
out: conn_graph
gpu: なし
examples: [poc_bga_ball_type_roundtrip, type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# knn_graph_to_conn_graph — REPRCONV `structure` op

- **データ種**: `graph` → `conn_graph`
- **呼び出し**: `import fullseye as fs; fs.ledger.knn_graph_to_conn_graph(graph, weight='inverse_distance', symmetric=True)` (実装を直接呼ぶなら `import reprconv; reprconv.knn_graph_to_conn_graph(graph, weight='inverse_distance', symmetric=True)`、台帳から引くなら `opsreprconv.get("knn_graph_to_conn_graph")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

k 近傍グラフ ``graph`` → 重みつき隣接行列 ``conn_graph (n, n)``。``graph`` 型の出口。

``knn_graph`` の返り ``(idx (n,k) int, dist (n,k) float)`` を、``conn_graph`` 族
(``graph_components`` / ``graph_laplacian_spectrum`` / ``graph_layout_spectral`` …)が
受ける n×n の ``W[i, j]`` = i → j の重みにする。``weight``:

* ``"inverse_distance"`` —— ``1 / dist``(近いほど強い。距離 0 の重複点は拒否する)
* ``"distance"`` —— ``dist`` そのもの(経路長として使う側向け)
* ``"binary"`` —— 1

``symmetric=True`` で ``W = max(W, Wᵀ)``(k 近傍は片想いがあるので、無向グラフとして
扱うなら対称化する)。対角は 0(``knn_graph`` は自分を除いている)。
n は ``conngraph.MAX_NODES``(4096)まで —— 密行列なので、それを超える点群は
先に ``farthest_point_sampling`` などで間引く。

Args:
    graph: ``(idx, dist)`` の 2-tuple(``knn_graph`` の返り)。
    weight: ``"inverse_distance"`` / ``"distance"`` / ``"binary"``。
    symmetric: True で対称化。
Returns:
    (n, n) float64。
Raises:
    ValueError: 2-tuple でない / 形が違う / 添字が範囲外 / 自己ループ / n が上限超え /
        ``inverse_distance`` で距離 0 / weight が不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_bga_ball_type_roundtrip](../../../../examples/poc_bga_ball_type_roundtrip.py) — `py -3.11 examples/poc_bga_ball_type_roundtrip.py`
- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`conn_graph` を入力に取れる)

—

## 同カテゴリ(`structure`)

[frame_axis](frame_axis.md) · [pointmap_to_points](pointmap_to_points.md) · [match_component](match_component.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
