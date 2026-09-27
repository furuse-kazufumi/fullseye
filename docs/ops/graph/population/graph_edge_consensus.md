---
op: graph_edge_consensus
dim: graph
category: population
in: table
out: table
examples: [poc_connectome_across_decades, poc_connectome_across_worms]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# graph_edge_consensus — GRAPH `population` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_edge_consensus(adjs, ordered=False, n_null=0, swaps_per_edge=5, seed=0)` (実装を直接呼ぶなら `import graphinv; graphinv.graph_edge_consensus(adjs, ordered=False, n_null=0, swaps_per_edge=5, seed=0)`、台帳から引くなら `opsgraph.get("graph_edge_consensus")`)

## 使い方

How many individuals share each connection — K wiring matrices on one node order.

``adjs`` is either a list of K square matrices or a table ``{name: matrix}`` (its
insertion order is the individual order), all on the **same** node order (align
the cell names first; a node absent from an individual is a zero row and column).
Weights (synapse counts) are kept for the synapse shares; presence is ``> 0``.
Self-loops are dropped.

Returns a dict with:

  * ``k`` (K), ``n``, ``names``, ``edges_per_individual`` and ``union`` (edges
    seen in at least one individual)
  * ``occupancy_hist`` — ``h[c]`` = number of edges present in exactly ``c``
    individuals, ``c = 0..K`` (``h[0]`` is always 0: only the union is counted)
  * ``jaccard`` — the K x K pairwise overlap ``|Ei ∩ Ej| / |Ei ∪ Ej|``
  * ``synapse_share`` — for each ``c``, the fraction of all synapses (summed over
    individuals) on edges of occupancy ``c`` (with a 0/1 input: the edge share)
  * with ``ordered=True`` (individuals listed in developmental order): the union is
    split by its presence pattern along the order into ``stable`` (present in all),
    ``added`` (absent, then present to the end: ``0..01..1``), ``lost``
    (``1..10..0``) and ``flicker`` (anything else). The four sum to ``union``.
  * with ``n_null >= 2``: every individual is rewired **independently** by
    degree-preserving swaps (each node's in/out degree kept exactly, checked per
    sample, fail-closed) and the occupancy histogram is re-counted. Reports
    ``occupancy_null_mean`` / ``occupancy_null_sd`` per ``c`` and
    ``shared_all_ratio`` (edges present in all K, observed over the null mean; inf
    when the null never shares one, so ``shared_all_null_max`` is reported too):
    the chance level of "the same connection in every animal" given only each
    animal's degrees.

Identities (the tests are built on these, not on fitted numbers):
``sum_c c * h[c] == sum_i |E_i|``; ``sum_c h[c] == union``; K identical inputs give
``h[K] == union`` and every Jaccard == 1; the Jaccard matrix is symmetric with a unit
diagonal; ``stable + added + lost + flicker == union``; ``synapse_share`` sums to 1.

**Raises** ``ValueError``: ``adjs`` not a list / table; fewer than 2 individuals;
matrices of different sizes; any refusal of :func:`graph_degree_summary`
(non-square, negative, non-finite, string / bool / complex / masked input); an
individual with no edges; ``n_null`` equal to 1 (no spread) or negative;
``swaps_per_edge < 1``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_connectome_across_decades](../../../../examples/poc_connectome_across_decades.py) — `py -3.11 examples/poc_connectome_across_decades.py`
- [poc_connectome_across_worms](../../../../examples/poc_connectome_across_worms.py) — `py -3.11 examples/poc_connectome_across_worms.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`population`)

—

---
*Provenance: graphinv.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
