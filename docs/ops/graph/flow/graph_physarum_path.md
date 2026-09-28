---
op: graph_physarum_path
dim: graph
category: flow
in: matrix
out: table
examples: [poc_physarum_maze]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# graph_physarum_path — GRAPH `flow` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_physarum_path(lengths, source=0, sink=None, dt=0.1, max_iters=5000, tol=1e-06, frac=0.5)` (実装を直接呼ぶなら `import physarum_search; physarum_search.graph_physarum_path(lengths, source=0, sink=None, dt=0.1, max_iters=5000, tol=1e-06, frac=0.5)`、台帳から引くなら `opsgraph.get("graph_physarum_path")`)

## 使い方

Shortest path by the slime mould's tube dynamics (Tero et al. 2010) on a weighted graph.

``lengths`` is a symmetric ``(n, n)`` matrix of tube lengths (``0`` = no tube, diagonal 0).
A unit flow is pushed from ``source`` to ``sink`` (default ``n - 1``) through tubes of
conductance ``D_e``; the pressures solve the weighted Laplacian (Kirchhoff), the flow in a
tube is ``Q_e = D_e (p_u - p_v) / L_e``, and each tube adapts ``dD_e/dt = |Q_e| - D_e``
(explicit Euler, step ``dt``). Bonifaci, Mehlhorn and Varma (2012) prove that with a unique
shortest path the conductances converge to its indicator: ``D_e -> 1`` on it, ``0`` off it.
The path is read by following, from the source, the tube that carries the most flow out of
each node (a potential flow has no cycle); it must be at least ``frac`` of the thickest tube
all along, else the run is refused as not converged.

Returns ``conductance`` and ``flow`` (``(n, n)`` matrices, flow antisymmetric), ``path``
(node indices source → sink), ``path_length`` (sum of the tube lengths along it),
``flow_length`` = ``sum |Q_e| L_e`` (the length of the unit flow; it is ``>= path_length``
for every unit flow and equal only when all flow rides shortest paths), ``iters``,
``converged`` (max |dD| fell below ``tol``), ``history`` (max |dD| per iteration).

**Raises** ``ValueError``: matrix not square / symmetric / finite / non-negative, self-loops;
bad node indices or ``source == sink``; sink unreachable; ``dt`` outside (0, 1]; no path
survived the threshold (not converged).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_physarum_maze](../../../../examples/poc_physarum_maze.py) — `py -3.11 examples/poc_physarum_maze.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`flow`)

[physarum_route](physarum_route.md) · [graph_physarum_transport](graph_physarum_transport.md) · [physarum_transport_image](physarum_transport_image.md)

---
*Provenance: physarum_search.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
