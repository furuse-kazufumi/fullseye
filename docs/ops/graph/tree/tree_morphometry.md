---
op: tree_morphometry
dim: graph
category: tree
in: table
out: table
examples: [poc_swc_tree_truth, poc_worm_neurites_grow, poc_worm_synapses_vs_neurites]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# tree_morphometry — GRAPH `tree` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tree_morphometry(tree)` (実装を直接呼ぶなら `import treemorph; treemorph.tree_morphometry(tree)`、台帳から引くなら `opsgraph.get("tree_morphometry")`)

## 使い方

Counts and lengths of a tree table (from :func:`tree_from_swc`).

Returns ``nodes``, ``edges``, ``bifurcations`` (nodes with two or more children),
``tips`` (nodes with no child), ``cable_length`` (sum of segment lengths),
``max_path_length`` (longest root-to-node path along the tree) and ``max_radial``
(largest straight distance from the root).

Identities (checked inside, fail-closed): ``nodes == edges + 1``, and
``tips == 1 + sum(children - 1)`` over the nodes that have children — tips are counted
from the child counts directly, the right side from the branching nodes, so a bug in
either count breaks the equality. A root with one child is not a tip.

**Raises** ``ValueError``: not a tree table (see :func:`tree_from_swc`).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_swc_tree_truth](../../../../examples/poc_swc_tree_truth.py) — `py -3.11 examples/poc_swc_tree_truth.py`
- [poc_worm_neurites_grow](../../../../examples/poc_worm_neurites_grow.py) — `py -3.11 examples/poc_worm_neurites_grow.py`
- [poc_worm_synapses_vs_neurites](../../../../examples/poc_worm_synapses_vs_neurites.py) — `py -3.11 examples/poc_worm_synapses_vs_neurites.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_sholl](tree_sholl.md) · [tree_run_length](tree_run_length.md)

## 同カテゴリ(`tree`)

[tree_from_swc](tree_from_swc.md) · [tree_sholl](tree_sholl.md) · [tree_run_length](tree_run_length.md)

---
*Provenance: treemorph.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
