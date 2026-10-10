---
op: physarum_route
dim: graph
category: flow
in: image2d
out: table
examples: [poc_physarum_maze]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# physarum_route — GRAPH `flow` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.physarum_route(cost, start=None, end=None, connectivity=4, dt=0.1, max_iters=5000, tol=1e-06, frac=0.5, snapshots=0)` (実装を直接呼ぶなら `import physarum_search; physarum_search.physarum_route(cost, start=None, end=None, connectivity=4, dt=0.1, max_iters=5000, tol=1e-06, frac=0.5, snapshots=0)`、台帳から引くなら `opsgraph.get("physarum_route")`)

## 使い方

Minimum-cost route through a cost image found by the slime mould's tube dynamics.

Every pixel is a node; neighbouring pixels (``connectivity`` 4 or 8) are joined by a tube of
length ``(c_u + c_v) / 2`` (times ``sqrt(2)`` on diagonals), so the length of a route equals
the sum of the pixel costs it visits minus half the cost of its two ends — the same quantity
``skimage.graph.route_through_array(..., geometric=False)`` minimises (it counts both ends
fully). ``start`` / ``end`` are ``(row, col)``; defaults are the top-left and bottom-right
corners. Dynamics and convergence as in :func:`graph_physarum_path`.

Returns ``conductance`` (an image: each pixel's thickest incident tube, 1 on the route
when converged), ``path`` (``(k, 2)`` pixel coordinates start → end), ``path_cost`` (sum of
the pixel costs along it, comparable to ``route_through_array``), ``route_length`` (sum
of the tube lengths), ``flow_length``, ``iters``, ``converged``, ``history``, and, with
``snapshots = m > 0``, ``snapshots`` (``m`` conductance images at evenly spaced
iterations, the last one final) for watching the tubes thicken, ``snapshot_iters`` and
``snapshot_cost`` = ``sum L_e D_e`` at those iterations (Bonifaci's Lyapunov function, which
never increases in continuous time).

**Raises** ``ValueError``: cost not a 2-D finite image of positive values; ``start`` / ``end``
outside the image or equal; ``connectivity`` not 4 or 8; and as :func:`graph_physarum_path`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_physarum_maze](../../../../examples/poc_physarum_maze.py) — `py -3.11 examples/poc_physarum_maze.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`flow`)

[graph_physarum_path](graph_physarum_path.md) · [graph_physarum_transport](graph_physarum_transport.md) · [physarum_transport_image](physarum_transport_image.md)

---
*Provenance: physarum_search.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
