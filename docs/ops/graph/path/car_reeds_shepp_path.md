---
op: car_reeds_shepp_path
dim: graph
category: path
in: matrix
out: table
examples: [poc_car_parking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# car_reeds_shepp_path — GRAPH `path` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.car_reeds_shepp_path(poses, radius=1.0, step=0.05)` (実装を直接呼ぶなら `import carpath; carpath.car_reeds_shepp_path(poses, radius=1.0, step=0.05)`、台帳から引くなら `opsgraph.get("car_reeds_shepp_path")`)

## 使い方

Shortest path of a car that may reverse, between two poses (Reeds and Shepp 1990), by closed form.

``poses`` is ``[[x, y, theta], [x', y', theta']]`` (start, goal). The car turns with minimum radius
``radius`` and may change gear. Reeds and Shepp proved the shortest path has at most five segments
drawn from 48 words (Sussmann and Tang 1991: 46 suffice); the 44 formulas used here (the 12 base
words of the paper expanded by time reversal, reflection and backwards reading, as in OMPL) generate
every candidate. Each candidate is verified by forward integration and discarded if it misses the
goal (counted in ``n_rejected``); the shortest survivor is the answer. Reversed segments carry
``gear = -1``.

Returns ``word`` (letters L/S/R; reversed segments are lower-case), ``length`` (metres, sum of
absolute segment lengths), ``segments`` ``[(kind, gear, length)]``, ``points`` ``(N, 3)`` poses
sampled every ``step`` metres, ``candidates`` ``[(word, length)]`` sorted, ``n_candidates``,
``n_rejected``, ``lower_bound`` (Euclidean distance), ``radius``.

**Raises** ``ValueError``: poses not ``(2, 3)`` finite; ``radius`` or ``step`` not positive; no word
reached the goal.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_car_parking](../../../../examples/poc_car_parking.py) — `py -3.11 examples/poc_car_parking.py`

## 型が繋がる次の op(`table` を入力に取れる)

[graph_edge_consensus](../population/graph_edge_consensus.md) · [graph_core_persistence](../population/graph_core_persistence.md) · [tree_morphometry](../tree/tree_morphometry.md) · [tree_sholl](../tree/tree_sholl.md) · [tree_run_length](../tree/tree_run_length.md)

## 同カテゴリ(`path`)

[car_dubins_path](car_dubins_path.md) · [car_hybrid_astar](car_hybrid_astar.md)

---
*Provenance: carpath.py — GRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
