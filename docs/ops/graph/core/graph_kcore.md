---
op: graph_kcore
dim: graph
category: core
in: matrix
out: table
examples: [poc_worm_core_persists]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# graph_kcore — GRAPH `core` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_kcore(adj, mode='total', weighted=False)` (実装を直接呼ぶなら `import graphinv; graphinv.graph_kcore(adj, mode='total', weighted=False)`、台帳から引くなら `opsgraph.get("graph_kcore")`)

## 使い方

k-core (or weighted s-core) decomposition of a wiring matrix — every node's core index.

A k-core is the maximal subgraph in which every node has degree at least k (Seidman
1983); a node's **core index** is the largest k of a core it belongs to. ``mode`` picks
the degree: ``"in"`` (inputs a node receives), ``"out"``, ``"total"`` (in + out; a
reciprocal pair counts twice, as in :func:`conngraph.graph_rich_club`) or
``"undirected"`` (an edge in either direction counts once — this is what
``networkx.core_number`` computes on the symmetrised graph). With ``weighted=True`` the
degree is the **strength** (sum of weights, e.g. synapse counts) and the result is the
s-core of Eidsaa & Almaas 2013: the index is the running maximum of the minimum
strength during peeling, so it is a real number with the units of the weights.
Self-loops are dropped.

Returns a dict: ``core`` (n,) — the index per node (int for k-core, float for s-core);
``kmax`` — the innermost index; ``inner`` (n,) bool — nodes of the innermost core;
``n_inner``; ``levels`` — the distinct indices in increasing order and ``counts`` — how
many nodes have each (``sum(counts) == n``); ``mode``; ``weighted``.

Identities (the tests): a complete graph on n nodes has every index n−1; a tree 1;
a cycle 2; ``undirected`` agrees with ``networkx.core_number`` on random graphs;
the s-core of a 0/1 matrix equals the k-core; multiplying every weight by c multiplies
every s-core index by c; the innermost core is never empty and every one of its nodes
has at least ``kmax`` (weighted: strength) inside the core.

**Raises** ``ValueError``: as :func:`graph_degree_summary` (non-square, negative,
non-finite, string / bool / complex / masked input); ``mode`` not one of
in / out / total / undirected.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_worm_core_persists](../../../../examples/poc_worm_core_persists.py) — `py -3.11 examples/poc_worm_core_persists.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`core`)

[graph_rich_club_curve](graph_rich_club_curve.md)

---
*Provenance: graphinv.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
