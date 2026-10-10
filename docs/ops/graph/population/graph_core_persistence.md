---
op: graph_core_persistence
dim: graph
category: population
in: table
out: table
examples: [poc_worm_core_persists]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# graph_core_persistence — GRAPH `population` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_core_persistence(adjs, mode='in', weighted=False)` (実装を直接呼ぶなら `import graphinv; graphinv.graph_core_persistence(adjs, mode='in', weighted=False)`、台帳から引くなら `opsgraph.get("graph_core_persistence")`)

## 使い方

Which nodes sit in the innermost core of every individual — K wirings on one node order.

``adjs`` is a list of K square matrices or a table ``{name: matrix}`` on the **same**
node order (a node absent from an individual is a zero row and column). For each
individual the innermost core of :func:`graph_kcore` (same ``mode`` / ``weighted``) is
taken; ``appearances[v]`` counts the individuals whose innermost core contains v. An
individual whose innermost index is 0 (e.g. no edges) has no core and contributes
no member.
Following Yadav & Singh 2026, a node is **persistent** if it is in the core of all K,
**recurrent** if in 2 .. K−1, **transient** if in exactly 1, and **never** otherwise.

Returns a dict: ``k`` (K), ``n``, ``names``, ``membership`` (K, n) bool,
``appearances`` (n,), ``persistent`` / ``recurrent`` / ``transient`` / ``never`` (n,)
bool masks, ``n_persistent`` .. ``n_never``, ``kmax`` (K,) the innermost index per
individual, ``n_inner`` (K,), ``mode``, ``weighted``.

Identities: ``sum(n_inner) == sum(appearances)``; the four classes partition the
nodes; K identical inputs make every core node persistent and nothing recurrent or
transient; every persistent node is in every individual's innermost core.

**Raises** ``ValueError``: ``adjs`` not a list / table; fewer than 2 individuals;
matrices of different sizes; any refusal of :func:`graph_kcore`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_worm_core_persists](../../../../examples/poc_worm_core_persists.py) — `py -3.11 examples/poc_worm_core_persists.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](graph_edge_consensus.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`population`)

[graph_edge_consensus](graph_edge_consensus.md) · [graph_strength_growth](graph_strength_growth.md)

---
*Provenance: graphinv.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
