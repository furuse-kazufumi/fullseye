---
op: graph_rich_club_curve
dim: graph
category: core
in: matrix
out: table
examples: [poc_worm_core_persists]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# graph_rich_club_curve — GRAPH `core` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_rich_club_curve(adj, mode='total', n_null=20, swaps_per_edge=5, seed=0)` (実装を直接呼ぶなら `import graphinv; graphinv.graph_rich_club_curve(adj, mode='total', n_null=20, swaps_per_edge=5, seed=0)`、台帳から引くなら `opsgraph.get("graph_rich_club_curve")`)

## 使い方

Rich-club coefficient φ(k) for every k, against the degree-preserving null.

φ(k) is the directed density of the subgraph spanned by the nodes whose degree exceeds
k: ``edges among them / (r (r − 1))``, ``r`` = their number (Colizza et al. 2006; the
same formula as :func:`conngraph.graph_rich_club`, here for all k at once). ``mode``
is the degree used to rank nodes: ``"total"`` (in + out), ``"in"`` or ``"out"`` (Yadav
& Singh 2026 rank by in- and out-degree separately). A rising φ(k) alone means little —
high-degree nodes are dense in any graph — so φ is divided by its mean over ``n_null``
rewirings that keep every node's in- and out-degree exactly (Maslov & Sneppen 2002;
every sample is checked, fail-closed). ``ratio > 1`` is the rich-club regime; Towlson
et al. 2013 call it significant where ``ratio > 1 + sd``.

Returns a dict: ``k`` (all integers 0 .. max degree − 1), ``count`` (nodes with degree
> k), ``phi``, ``null_mean``, ``null_sd``, ``ratio`` (nan where the null mean is 0),
``z`` (nan where the null sd is 0 -- e.g. a complete graph, where no swap changes phi),
``regime`` (bool: ratio > 1 + null sd of the ratio), ``n_null``, ``mode``.

Identities: ``phi[k] == conngraph.graph_rich_club(adj, k)`` for every k with
``mode="total"``; a complete graph has ``phi == 1`` and ``ratio == 1`` everywhere
(no swap can change it); a rewired sample of the graph itself has ratio ≈ 1.

**Raises** ``ValueError``: as :func:`graph_degree_preserving_null` (non-square,
negative, ... ; ``n_null < 2``; ``swaps_per_edge < 1``; fewer than 2 edges);
``mode`` not in / out / total.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_worm_core_persists](../../../../examples/poc_worm_core_persists.py) — `py -3.11 examples/poc_worm_core_persists.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`core`)

[graph_kcore](graph_kcore.md)

---
*Provenance: graphinv.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
