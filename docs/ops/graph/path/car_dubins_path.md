---
op: car_dubins_path
dim: graph
category: path
in: matrix
out: table
examples: [poc_car_parking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# car_dubins_path — GRAPH `path` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.car_dubins_path(poses, radius=1.0, step=0.05)` (実装を直接呼ぶなら `import carpath; carpath.car_dubins_path(poses, radius=1.0, step=0.05)`、台帳から引くなら `opsgraph.get("car_dubins_path")`)

## 使い方

Shortest forward-only path of a car between two poses (Dubins 1957) by the six closed-form words.

``poses`` is ``[[x, y, theta], [x', y', theta']]`` (start, goal; theta in radians, counter-clockwise
from the x axis). The car turns with minimum radius ``radius`` and never reverses. Dubins proved the
shortest path is one of LSL, RSR, LSR, RSL, RLR, LRL (arcs of maximal curvature and straights); each
word's three segment lengths are closed-form (Shkel and Lumelsky 2001). Every candidate is verified
by forward integration to the goal and discarded if it misses (fail-closed against formula slips;
the count is returned as ``n_rejected``), and the shortest survivor is the answer.

Returns ``word``, ``length`` (metres), ``segments`` ``[(kind, gear, length)]`` (kind L/S/R, gear +1),
``points`` ``(N, 3)`` poses sampled every ``step`` metres along the path (start and goal included),
``candidates`` ``[(word, length)]`` for all verified words in increasing length, ``n_rejected``,
``lower_bound`` (the Euclidean distance, never exceeded), ``radius``.

**Raises** ``ValueError``: poses not ``(2, 3)`` finite; ``radius`` or ``step`` not positive; no word
reaches the goal (cannot happen for finite poses; reported rather than guessed).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_car_parking](../../../../examples/poc_car_parking.py) — `py -3.11 examples/poc_car_parking.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`path`)

[car_reeds_shepp_path](car_reeds_shepp_path.md) · [car_hybrid_astar](car_hybrid_astar.md)

---
*Provenance: carpath.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
