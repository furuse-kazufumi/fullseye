---
op: graph_strength_growth
dim: graph
category: population
in: matrix × matrix
out: table
examples: [poc_worm_synapses_vs_neurites]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# graph_strength_growth — GRAPH `population` op

- **データ種**: `matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_strength_growth(a, b, hub_fraction=0.1)` (実装を直接呼ぶなら `import graphinv; graphinv.graph_strength_growth(a, b, hub_fraction=0.1)`、台帳から引くなら `opsgraph.get("graph_strength_growth")`)

## 使い方

Where the new synapses went — one wiring matrix ``a`` (earlier) against ``b`` (later).

Both are weight matrices (synapse counts) on the **same** node order; self-loops are
dropped. With ``S = sum`` of each matrix and ``dS = S_b - S_a``:

  * per node: ``in_a``, ``out_a``, ``in_b``, ``out_b`` (strengths), ``degree_a`` (number of
    partners, in + out, presence ``> 0``), ``gain_in = in_b - in_a``, ``gain_out``.
    Identity: ``gain_in.sum() == gain_out.sum() == dS`` (every synapse has one pre and one post).
  * ``strengthened`` / ``weakened`` (weight change on edges present in both), ``added``
    (weight of edges only in ``b``), ``lost`` (weight of edges only in ``a``);
    ``strengthened - weakened + added - lost == dS``.
  * ``rho_in`` / ``rho_out`` — Spearman rank correlation of ``degree_a`` with ``gain_in`` /
    ``gain_out`` over nodes with ``degree_a > 0`` (0.0 with fewer than 3 such nodes or no
    variance); ``n_ranked``.
  * hubs = the top ``hub_fraction`` of ranked nodes by ``degree_a`` (at least 1):
    ``hub_share_in_a`` (their share of ``S_a`` as post-synaptic partners), ``hub_share_gain_in``
    (their share of ``dS`` arriving as inputs), and the same for outputs. If new synapses were
    spread in proportion to existing strength, the two shares would be equal — the gap is
    what "hubs grow disproportionately" means in numbers.

**Raises** ``ValueError``: either matrix not square / non-finite / negative / a string or
masked array; shapes differ; ``hub_fraction`` outside ``(0, 1]``; ``dS == 0`` is allowed
(shares of the gain are then 0).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_worm_synapses_vs_neurites](../../../../examples/poc_worm_synapses_vs_neurites.py) — `py -3.11 examples/poc_worm_synapses_vs_neurites.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](graph_edge_consensus.md) · [graph_core_persistence](graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`population`)

[graph_edge_consensus](graph_edge_consensus.md) · [graph_core_persistence](graph_core_persistence.md)

---
*Provenance: graphinv.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
