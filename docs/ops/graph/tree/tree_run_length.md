---
op: tree_run_length
dim: graph
category: tree
in: table × signal
out: table
examples: [poc_skeleton_run_length_vs_voi]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# tree_run_length — GRAPH `tree` op

- **データ種**: `table × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tree_run_length(tree, labels, background=0, zero_labels=None)` (実装を直接呼ぶなら `import treemorph; treemorph.tree_run_length(tree, labels, background=0, zero_labels=None)`、台帳から引くなら `opsgraph.get("tree_run_length")`)

## 使い方

Expected run length (ERL) of a skeleton under a candidate labelling of its nodes.

``labels`` gives, for every node of the tree table, the candidate object it falls in.
A **run** is a maximal connected piece of the tree whose nodes all carry the same
label and that holds at least one edge; its length is the cable inside it (an edge
belongs to a run only if both ends share the label; a lone node between two cuts is
no run). Edges touching ``background`` belong to no run. Runs whose label is
in ``zero_labels`` (objects that also cover another skeleton — a merge) count as length
0, as in Januszewski et al. 2018: a merged run is not trustworthy anywhere.

``erl = sum(l_i^2) / L`` with ``L`` the whole cable — the run length a point drawn
uniformly along the skeleton finds itself in (points on cut or background edges find
length 0). Also returns ``run_lengths`` (one per run, merged runs already zeroed),
``runs``, ``max_run``, ``cable_length``, ``cut_edges`` (both ends labelled, differently),
``background_edges`` and ``merged_runs``.

Identities: ``erl == L`` when every node carries one non-background label;
``sum(run_lengths) + cut cable + background cable == L``; for any labelling with
``k`` runs and no lost cable, ``erl >= L / k`` (Cauchy-Schwarz) and ``erl <= max_run``;
a path of length ``L`` cut at ``m`` equally spaced points gives exactly ``L / (m + 1)``;
cut at ``m`` uniformly random points, ``E[erl] = 2L / (m + 2)`` (Dirichlet(1, .., 1)).

**Raises** ``ValueError``: not a tree table; ``labels`` not one integer per node,
non-finite or non-integer.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_skeleton_run_length_vs_voi](../../../../examples/poc_skeleton_run_length_vs_voi.py) — `py -3.11 examples/poc_skeleton_run_length_vs_voi.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [tree_morphometry](tree_morphometry.md) · [tree_sholl](tree_sholl.md)

## 同カテゴリ(`tree`)

[tree_from_swc](tree_from_swc.md) · [tree_morphometry](tree_morphometry.md) · [tree_sholl](tree_sholl.md)

---
*Provenance: treemorph.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
