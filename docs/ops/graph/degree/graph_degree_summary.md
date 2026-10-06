---
op: graph_degree_summary
dim: graph
category: degree
in: matrix
out: table
examples: [graphinv_three_phyla, poc_connectome_lr_symmetry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# graph_degree_summary — GRAPH `degree` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_degree_summary(adj)` (実装を直接呼ぶなら `import graphinv; graphinv.graph_degree_summary(adj)`、台帳から引くなら `opsgraph.get("graph_degree_summary")`)

## 使い方

Degrees, density and reciprocity of a directed wiring matrix.

``adj`` is a square matrix; entry ``(i, j) > 0`` means an edge ``i -> j``. Self-loops
are counted separately and excluded from the edge statistics. Returns a dict with
``n``, ``edges``, ``self_loops``, the ``in_degree`` / ``out_degree`` arrays,
``density`` (``edges / (n (n-1))``), and ``reciprocal_pairs`` (unordered pairs wired
in both directions).

The identity ``in_degree.sum() == out_degree.sum() == edges`` holds exactly for
any directed graph and is checked before returning (fail-closed — if it ever broke,
the matrix was not what the caller thought).

**Raises** ``ValueError``: non-square / empty / non-finite / negative input, or a
matrix over the node cap.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [graphinv_three_phyla](../../../../examples/graphinv_three_phyla.py) — `py -3.11 examples/graphinv_three_phyla.py`
- [poc_connectome_lr_symmetry](../../../../examples/poc_connectome_lr_symmetry.py) — `py -3.11 examples/poc_connectome_lr_symmetry.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`degree`)

—

---
*Provenance: graphinv.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
