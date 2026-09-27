---
op: graph_degree_preserving_null
dim: graph
category: null
in: matrix
out: table
examples: [graphinv_three_phyla]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# graph_degree_preserving_null — GRAPH `null` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_degree_preserving_null(adj, n_samples=20, swaps_per_edge=5, seed=0)` (実装を直接呼ぶなら `import graphinv; graphinv.graph_degree_preserving_null(adj, n_samples=20, swaps_per_edge=5, seed=0)`、台帳から引くなら `opsgraph.get("graph_degree_preserving_null")`)

## 使い方

Compare 3-cycles and reciprocity against a degree-preserving null model.

Each null sample rewires the graph by ``swaps_per_edge * |E|`` edge swaps that keep
every node's in- and out-degree **exactly** (Maslov & Sneppen 2002). The sample's
degree sequences are checked against the original before it is used — a null that
drifted would make every ratio a lie, so this fails closed.

Returns a dict with the observed ``cycles3`` and ``reciprocal_pairs``, the null
``*_null_mean`` / ``*_null_sd``, the ``*_ratio`` (observed / null mean) and ``*_z``,
plus ``n_samples`` and ``swaps``. Ratios are what let graphs of different size be
compared; raw counts cannot.

**Raises** ``ValueError``: as :func:`graph_degree_summary`; ``n_samples < 2``
(no spread to estimate); ``swaps_per_edge < 1``; a graph with fewer than 2 edges
(nothing to swap).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [graphinv_three_phyla](../../../../examples/graphinv_three_phyla.py) — `py -3.11 examples/graphinv_three_phyla.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`null`)

—

---
*Provenance: graphinv.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
