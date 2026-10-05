---
op: car_hybrid_astar
dim: graph
category: path
in: image2d × matrix
out: table
examples: [poc_car_parking, poc_driving_school]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# car_hybrid_astar — GRAPH `path` op

- **データ種**: `image2d × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.car_hybrid_astar(occupancy, poses, radius=1.0, cell=1.0, step=None, n_theta=72, allow_reverse=True, footprint=None, clearance=0.0, reverse_penalty=0.0, switch_penalty=0.0, steer_penalty=0.0, shot_every=None, max_expansions=200000, return_tree=False)` (実装を直接呼ぶなら `import carpath; carpath.car_hybrid_astar(occupancy, poses, radius=1.0, cell=1.0, step=None, n_theta=72, allow_reverse=True, footprint=None, clearance=0.0, reverse_penalty=0.0, switch_penalty=0.0, steer_penalty=0.0, shot_every=None, max_expansions=200000, return_tree=False)`、台帳から引くなら `opsgraph.get("car_hybrid_astar")`)

## 使い方

Hybrid A* (Dolgov, Thrun, Montemerlo and Diebel 2010): a car's path through an occupancy grid.

``occupancy`` is a 2-D grid (``> 0.5`` = obstacle); cell ``(row, col)`` covers metres
``x in [col*cell, (col+1)*cell)``, ``y in [row*cell, (row+1)*cell)``. ``poses`` is
``[[x, y, theta], [x', y', theta']]`` (start, goal) in metres/radians. The car has minimum turning
radius ``radius``; ``footprint=(length, width, rear_offset)`` is a rectangle in rear-axle coordinates
(``None`` = point car with ``clearance`` metres kept from obstacles). Motion primitives are
{left, straight, right} × {forward, reverse if ``allow_reverse``} arcs of ``step`` metres (default
``1.01·sqrt(2)·cell``, so each primitive leaves its cell); states are pruned per discrete cell
``(col, row, theta bin of 2π/n_theta)``. Cost = path length + ``reverse_penalty``·(reversed length)
+ ``switch_penalty`` per gear change + ``steer_penalty`` per steering change (all default 0, so the
cost is the geometric length). The heuristic is the obstacle-free Reeds–Shepp length (Dubins when
reversing is disallowed), admissible because every penalty is non-negative. At the start node, and then
every ``shot_every`` expansions (default ``None`` = adaptive: a node with cost-to-go ``h`` tries when the
expansion count is a multiple of ``ceil(h / step)``, so nodes near the goal try every time, as in the
paper), the shortest analytic path from the node to the goal is collision-checked, and the search ends
when that shot is free. On an obstacle-free grid the first shot succeeds and the result equals the
Reeds–Shepp (Dubins) length exactly; with obstacles the result is never below it (``lower_bound``).
Cell pruning makes Hybrid A* an approximation of the optimum among all feasible paths, as in the paper.

Returns ``points`` ``(N, 3)`` poses along the path (start, tree part, analytic shot to the goal),
``length`` (metres), ``cost``, ``lower_bound`` (Reeds–Shepp/Dubins length start→goal),
``segments`` ``[(kind, gear, length)]`` of the whole path, ``n_expanded``, ``n_generated``,
``closed_by_shot`` (``True`` when the analytic expansion ended the search; ``False`` when the goal cell
itself was popped), ``shot_from`` (pose where the shot started), ``tree`` (``(K, 3)`` expanded poses,
only when ``return_tree``).

**Raises** ``ValueError``: grid not 2-D or empty; poses not ``(2, 3)`` finite, outside the grid or in
collision; ``radius``/``cell``/``step`` not positive, ``n_theta < 4``, negative penalties; the goal is
unreachable (open set exhausted) or ``max_expansions`` was hit (reported, never a partial path).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_car_parking](../../../../examples/poc_car_parking.py) — `py -3.11 examples/poc_car_parking.py`
- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`path`)

[car_dubins_path](car_dubins_path.md) · [car_reeds_shepp_path](car_reeds_shepp_path.md)

---
*Provenance: carpath.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
