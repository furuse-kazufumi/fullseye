---
op: graph_swap_symmetry
dim: graph
category: symmetry
in: matrix
out: table
examples: [graphinv_three_phyla, poc_connectome_lr_symmetry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# graph_swap_symmetry — GRAPH `symmetry` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_swap_symmetry(adj, pairs)` (実装を直接呼ぶなら `import graphinv; graphinv.graph_swap_symmetry(adj, pairs)`、台帳から引くなら `opsgraph.get("graph_swap_symmetry")`)

## 使い方

How much of the wiring survives exchanging node pairs (a left/right test).

``pairs`` is a sequence of ``(i, j)`` index pairs to exchange (each node in at most
one pair). The wiring is re-indexed by the exchange and compared with the original:
``jaccard = |E ∩ E'| / |E ∪ E'|`` over directed edges (self-loops removed). Returns
a dict with ``jaccard``, ``shared``, ``union``, ``edges``, and ``n_pairs``.

Identities: the identity pairing (or an empty ``pairs``) gives exactly 1.0; applying
the exchange twice recovers the original matrix exactly. For the C. elegans
hermaphrodite chemical connectome with its 98 named left/right pairs the measured
value is 0.470 — half the wiring is not mirrored.

**Raises** ``ValueError``: as :func:`graph_degree_summary`; an index out of range;
a node appearing in two pairs; a pair of a node with itself.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [graphinv_three_phyla](../../../../examples/graphinv_three_phyla.py) — `py -3.11 examples/graphinv_three_phyla.py`
- [poc_connectome_lr_symmetry](../../../../examples/poc_connectome_lr_symmetry.py) — `py -3.11 examples/poc_connectome_lr_symmetry.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`symmetry`)

—

---
*Provenance: graphinv.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
