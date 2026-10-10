---
op: tree_from_swc
dim: graph
category: tree
in: text
out: table
examples: [poc_skeleton_run_length_vs_voi, poc_swc_tree_truth, poc_worm_neurites_grow, poc_worm_synapses_vs_neurites]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# tree_from_swc — GRAPH `tree` op

- **データ種**: `text` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tree_from_swc(swc)` (実装を直接呼ぶなら `import treemorph; treemorph.tree_from_swc(swc)`、台帳から引くなら `opsgraph.get("tree_from_swc")`)

## 使い方

Parse an SWC text (or a path to a ``.swc`` file) into a checked tree table.

Returns a dict with ``id`` (n,), ``type`` (n,), ``xyz`` (n, 3), ``radius`` (n,),
``parent_index`` (n,; -1 for the root, otherwise the row of the parent) and ``root``
(row of the root). Rows keep the file order. Comment lines (``#``) and blank lines
are skipped.

**Raises** ``ValueError``: not a string; a data line with fewer than 7 fields or
unparsable numbers; no nodes; duplicate ids; zero or more than one root
(parent == -1); a parent id that is not smaller than its child's; a parent id that
does not exist; non-finite coordinates or radius; a negative radius; more than
``MAX_TREE_NODES`` nodes.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_skeleton_run_length_vs_voi](../../../../examples/poc_skeleton_run_length_vs_voi.py) — `py -3.11 examples/poc_skeleton_run_length_vs_voi.py`
- [poc_swc_tree_truth](../../../../examples/poc_swc_tree_truth.py) — `py -3.11 examples/poc_swc_tree_truth.py`
- [poc_worm_neurites_grow](../../../../examples/poc_worm_neurites_grow.py) — `py -3.11 examples/poc_worm_neurites_grow.py`
- [poc_worm_synapses_vs_neurites](../../../../examples/poc_worm_synapses_vs_neurites.py) — `py -3.11 examples/poc_worm_synapses_vs_neurites.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](tree_morphometry.md) · [tree_sholl](tree_sholl.md) · [tree_run_length](tree_run_length.md)

## 同カテゴリ(`tree`)

[tree_morphometry](tree_morphometry.md) · [tree_sholl](tree_sholl.md) · [tree_run_length](tree_run_length.md)

---
*Provenance: treemorph.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
