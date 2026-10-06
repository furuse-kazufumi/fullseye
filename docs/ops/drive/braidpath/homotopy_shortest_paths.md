---
op: homotopy_shortest_paths
dim: drive
category: braidpath
in: image2d × any × any
out: table
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# homotopy_shortest_paths — DRIVE `braidpath` op

- **データ種**: `image2d × any × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.homotopy_shortest_paths(grid, start, goal, k=4, obstacles=None, angle=0.1, max_states=400000, max_cost=None)` (実装を直接呼ぶなら `import braidpath; braidpath.homotopy_shortest_paths(grid, start, goal, k=4, obstacles=None, angle=0.1, max_states=400000, max_cost=None)`、台帳から引くなら `opsdrive.get("homotopy_shortest_paths")`)

## 使い方

格子(True = 走れる、4 近傍)の上で、start から goal へのホモトピー類の違う最短経路を短い順に k 本。

状態 = (マス, 組紐の Dynnikov 座標)。障害物の点を動かない紐として、1 手ごとに交差の文字を足して座標を更新する
(座標は類の完全な不変量なので、同じ (マス, 座標) は 1 回しか開かない)。Dijkstra がこの「類で持ち上げた」格子を
費用の順に開くので、goal に新しい座標で着いた順が、類ごとの最短経路の短い順になる。

Parameters
----------
obstacles : 穴の代表の点 (M, 2)。省略すると :func:`grid_hole_points`(外周に触れない塞がりの成分ごとに 1 点)。
max_states / max_cost : 開く状態の数・費用の上限(類は無限にある —— 穴のまわりを何周でも回れる)。

Returns: dict ``paths``(各類の (L, 2) の (row, col) の列、短い順)、``costs``、``words``(障害物と合わせた組紐語)、
``keys``、``obstacles``、``states``(開いた状態の数)、``complete``(k 本そろったか)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_reduce](braid_reduce.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [dynnikov_act](dynnikov_act.md) · [braid_equivalent](braid_equivalent.md) · [homotopy_class_compare](homotopy_class_compare.md) · [pairwise_winding](pairwise_winding.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
