---
op: graph_cycle3
dim: graph
category: motif
in: matrix
out: table
examples: [graphinv_three_phyla]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# graph_cycle3 — GRAPH `motif` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_cycle3(adj)` (実装を直接呼ぶなら `import graphinv; graphinv.graph_cycle3(adj)`、台帳から引くなら `opsgraph.get("graph_cycle3")`)

## 使い方

Number of directed 3-cycles ``i -> j -> k -> i`` as ``tr(B^3) / 3``.

Each cycle is counted once (the trace visits it from each of its three starting
nodes). Self-loops are removed first. Returns a dict with ``cycles3`` and ``n``.

A second, independent implementation (brute-force enumeration) agrees exactly on
small graphs — pinned in the tests, because a single implementation of a counting
formula cannot catch its own off-by-three.

**Raises** ``ValueError``: as :func:`graph_degree_summary`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [graphinv_three_phyla](../../../../examples/graphinv_three_phyla.py) — `py -3.11 examples/graphinv_three_phyla.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`motif`)

—

---
*Provenance: graphinv.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
