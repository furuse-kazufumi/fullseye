---
op: tree_sholl
dim: graph
category: tree
in: table
out: table
examples: [poc_swc_tree_truth, poc_worm_neurites_grow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# tree_sholl — GRAPH `tree` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tree_sholl(tree, radii=None, n_radii=50, plane=None, center=None)` (実装を直接呼ぶなら `import treemorph; treemorph.tree_sholl(tree, radii=None, n_radii=50, plane=None, center=None)`、台帳から引くなら `opsgraph.get("tree_sholl")`)

## 使い方

Sholl analysis: segments crossing spheres (3-D) or circles (a projection) around the root.

``radii`` are the shell radii (ascending, positive); if omitted, ``n_radii`` shells at
the mid-points of equal steps up to the largest distance from the centre (never exactly
on a node's distance). A shell passing exactly through a node is ambiguous under
rounding — a rotation may move that node by one ulp to either side. ``plane=None`` measures in 3-D;
``plane="xy" | "xz" | "yz"`` drops the third axis first — what a single image sees.
``center`` defaults to the root position.

A segment (parent-child) crosses radius ``r`` when its end points lie strictly on
opposite sides of ``r`` (the endpoint rule). Returns ``radii``, ``crossings`` (int array),
``max_crossings``, ``radius_at_max`` and ``integral`` — the exact area under the whole
continuous Sholl curve, computed from the segments' intervals (independent of where
the shells are placed).

Identities: in 3-D the crossings are invariant, integer for integer, under any rotation
about the centre; and ``integral`` equals ``sum |d_child - d_parent|`` (the tests also
check that the mid-point sum of the sampled crossings converges to it — a second
implementation).

**Raises** ``ValueError``: not a tree table; ``plane`` not one of None/xy/xz/yz;
radii not 1-D, not finite, not positive or not strictly increasing; ``n_radii < 1``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_swc_tree_truth](../../../../examples/poc_swc_tree_truth.py) — `py -3.11 examples/poc_swc_tree_truth.py`
- [poc_worm_neurites_grow](../../../../examples/poc_worm_neurites_grow.py) — `py -3.11 examples/poc_worm_neurites_grow.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](tree_morphometry.md) · [tree_run_length](tree_run_length.md)

## 同カテゴリ(`tree`)

[tree_from_swc](tree_from_swc.md) · [tree_morphometry](tree_morphometry.md) · [tree_run_length](tree_run_length.md)

---
*Provenance: treemorph.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
