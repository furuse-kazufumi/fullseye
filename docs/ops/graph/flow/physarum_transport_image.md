---
op: physarum_transport_image
dim: graph
category: flow
in: image2d × image2d
out: table
examples: [poc_physarum_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# physarum_transport_image — GRAPH `flow` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.physarum_transport_image(a, b, connectivity=4, normalize=True, dt=0.1, max_iters=5000, tol=1e-06, gap_tol=1e-06, snapshots=0)` (実装を直接呼ぶなら `import physarum_search; physarum_search.physarum_transport_image(a, b, connectivity=4, normalize=True, dt=0.1, max_iters=5000, tol=1e-06, gap_tol=1e-06, snapshots=0)`、台帳から引くなら `opsgraph.get("physarum_transport_image")`)

## 使い方

Earth mover's distance between two mass images by the slime mould's tube dynamics.

Every pixel is a node; neighbouring pixels (``connectivity`` 4 or 8) are joined by a tube of
length 1 (``sqrt(2)`` on diagonals), so the ground metric is the grid path length (Manhattan
for 4, octile for 8). Mass ``a`` enters and mass ``b`` leaves: the supply is ``a - b`` after
both are scaled to unit mass (``normalize=True``; with ``False`` they must already carry the
same mass). Dynamics, convergence and the two-sided bound as in
:func:`graph_physarum_transport`; larger images run on the sparse Laplacian with conjugate
gradients.

Returns ``cost`` (the 1-Wasserstein distance estimate in pixel units, an upper bound),
``dual_bound`` (Kantorovich–Rubinstein lower bound), ``gap``, ``conductance`` (an image: each
pixel's thickest incident tube), ``flow_field`` (``(H, W, 2)``: the mean of the flow vectors
of the tubes at each pixel, in ``(row, col)`` units of mass per unit length, for drawing
arrows), ``potential`` (``(H, W)`` pressures), ``iters``, ``converged``, ``gap_converged``,
``history``, ``cost_history``, ``dual_history``, and with ``snapshots = m > 0`` also ``snapshots`` (``m``
conductance images at evenly spaced iterations, the last one final), ``snapshot_iters`` and
``snapshot_cost`` (``sum_e L_e |Q_e|`` at those iterations) for watching the tubes form.

**Raises** ``ValueError``: images not 2-D, finite, non-negative, of the same shape with at
least 2 rows and columns, or without mass; unequal masses when ``normalize=False``;
``connectivity`` not 4 or 8; ``snapshots < 0``; and as :func:`graph_physarum_transport`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_physarum_transport](../../../../examples/poc_physarum_transport.py) — `py -3.11 examples/poc_physarum_transport.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`flow`)

[graph_physarum_path](graph_physarum_path.md) · [physarum_route](physarum_route.md) · [graph_physarum_transport](graph_physarum_transport.md)

---
*Provenance: physarum_search.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
