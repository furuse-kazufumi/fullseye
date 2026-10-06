---
op: homotopy_class_compare
dim: drive
category: braidpath
in: any × any
out: table
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# homotopy_class_compare — DRIVE `braidpath` op

- **データ種**: `any × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.homotopy_class_compare(traj_a, traj_b, obstacles=None, angle=0.1, tol=1e-09, jitter='auto')` (実装を直接呼ぶなら `import braidpath; braidpath.homotopy_class_compare(traj_a, traj_b, obstacles=None, angle=0.1, tol=1e-09, jitter='auto')`、台帳から引くなら `opsdrive.get("homotopy_class_compare")`)

## 使い方

始点と終点が同じ 2 つの経路族(複数エージェントの計画)が、同じホモトピー類か。

衝突せずに(エージェント同士も障害物の点とも重ならずに)始点と終点を止めたまま連続に変形できる ⇔ 組紐が等しい。
組紐は :func:`braid_from_trajectories`、比較は Dynnikov 座標。射影の角度に依らない(門で複数の角度を振る)。

Returns: dict ``same``、``word_a`` / ``word_b``、``key_a`` / ``key_b``、``quotient``(a b⁻¹ を簡約した語 —— 空なら同じ類、
空でなければ「どう回り方が違うか」の語)、``endpoint_error``(始点・終点の最大のずれ)。
Raises: ValueError(台数が違う、始点か終点が ``tol`` より離れている、衝突)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_reduce](braid_reduce.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [dynnikov_act](dynnikov_act.md) · [braid_equivalent](braid_equivalent.md) · [pairwise_winding](pairwise_winding.md) · [homotopy_shortest_paths](homotopy_shortest_paths.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
