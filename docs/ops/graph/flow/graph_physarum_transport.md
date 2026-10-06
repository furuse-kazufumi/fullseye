---
op: graph_physarum_transport
dim: graph
category: flow
in: matrix × signal
out: table
examples: [poc_physarum_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# graph_physarum_transport — GRAPH `flow` op

- **データ種**: `matrix × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_physarum_transport(lengths, supply, dt=0.1, max_iters=5000, tol=1e-06, gap_tol=1e-06)` (実装を直接呼ぶなら `import physarum_search; physarum_search.graph_physarum_transport(lengths, supply, dt=0.1, max_iters=5000, tol=1e-06, gap_tol=1e-06)`、台帳から引くなら `opsgraph.get("graph_physarum_transport")`)

## 使い方

L1 optimal transport (the Beckmann problem) on a weighted graph by the slime mould's tube dynamics.

``lengths`` is a symmetric ``(n, n)`` matrix of tube lengths (``0`` = no tube, diagonal 0) and
``supply`` an ``(n,)`` vector that sums to 0: mass enters at the nodes with ``supply > 0`` and
leaves where it is ``< 0``. The pressures solve the weighted Laplacian with this right-hand
side (Kirchhoff), each tube carries ``Q_e = D_e (p_u - p_v) / L_e`` and adapts
``dD_e/dt = |Q_e| - D_e`` (explicit Euler, step ``dt``). Bonifaci (2017) and Facca,
Karrenbauer, Kolev and Mehlhorn (2020) prove that the flow converges to a minimiser of
``sum_e L_e |q_e|`` under flow conservation, i.e. to the 1-Wasserstein distance between
``supply+`` and ``supply-`` in the graph metric (Facca, Cardin and Putti 2018 for the
continuum). With one unit source and one sink this is :func:`graph_physarum_path`.

Returns ``cost`` = ``sum_e L_e |Q_e|`` (the transport cost of the current flow: an upper bound
on the distance), ``dual_bound`` = ``supply . p'`` with ``p'`` the pressure scaled to be
1-Lipschitz along every tube (Kantorovich–Rubinstein: a lower bound on the distance at any
iteration, no external solver needed), ``gap`` = ``cost - dual_bound`` (0 at the optimum;
it closes like ``tol / dt`` divided by the smallest non-zero flow, because the scaling is
set by the tube whose conductance still lags its flow the most),
``conductance`` and ``flow`` (``(n, n)`` matrices, flow antisymmetric; the net outflow of
every node equals its supply), ``potential`` (``(n,)`` pressures, 0 at one node per connected
component), ``iters``, ``converged`` (max |dD| fell below ``tol``), ``gap_converged`` (the
run stopped because ``gap <= gap_tol * cost``: the cost is certified within ``gap_tol`` of the
optimum; when several flows are optimal the conductances keep wandering while the pressures
settle, so this is the stop that fires; the gap is checked every 10 iterations), ``history``,
``cost_history`` and ``dual_history`` (``(k, 2)``: iteration and lower bound at each check).

**Raises** ``ValueError``: matrix not square / symmetric / finite / non-negative, self-loops,
no edge; ``supply`` not an ``(n,)`` finite numeric vector, all zero, not summing to 0
(relative ``1e-9``) or unbalanced inside a connected component (mass with nowhere to go);
``dt`` outside (0, 1]; ``max_iters < 1``; ``tol < 0``; ``gap_tol < 0``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_physarum_transport](../../../../examples/poc_physarum_transport.py) — `py -3.11 examples/poc_physarum_transport.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`flow`)

[graph_physarum_path](graph_physarum_path.md) · [physarum_route](physarum_route.md) · [physarum_transport_image](physarum_transport_image.md)

---
*Provenance: physarum_search.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
