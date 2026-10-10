---
op: stagnation_from_centerline
dim: drive
category: swarmflow
in: table
out: table
examples: [poc_swarm_obstacle_from_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# stagnation_from_centerline — DRIVE `swarmflow` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.stagnation_from_centerline(field, speed=None, d_range=(0.04, 0.6), min_points: 'int' = 4, n_iter: 'int' = 80) -> 'dict'` (実装を直接呼ぶなら `import swarmflow; swarmflow.stagnation_from_centerline(field, speed=None, d_range=(0.04, 0.6), min_points: 'int' = 4, n_iter: 'int' = 80) -> 'dict'`、台帳から引くなら `opsdrive.get("stagnation_from_centerline")`)

## 使い方

中心線の欠損を直線化して、上流の衝突点(よどみ点)・障害物の中心・半径を読む(実装 1、上流の点だけ)。

1. 欠損(3 × 3 の平均)が ``d_range`` の上限を超える格子のうち、最も上流のものを「衝突点のそば」とする。
2. その少し上流の列(4 列)で、欠損が最大の行を放物線で副格子に求め、平均を中心線 y_c とする
   (上流の欠損 R²(Δx² − Δy²)/(Δx² + Δy²)² は Δy = 0 で最大)。
3. y_c の高さで欠損を行の間の 1 次補間で取り、衝突点のそばより上流で ``d_range`` の中にある格子で
   1/√d = (x_c − x)/R を重みつき最小二乗で引く(速さの雑音 σ_d は 1/√d では σ_d/(2d^{3/2}) に増えるので、
   重み d^{3/2} —— 欠損の小さい遠くの点は雑音で暴れる): R = −1/傾き、x_c = 切片 × R。よどみ点 = (x_c − R, y_c)。
4. ``speed`` を与えないときは、上流の端の u を閉形式で割り戻して U を推定し直し、3 を繰り返す(U の変化が 1e-9 未満になるか ``n_iter`` 回まで。収束は 1 次で、R = 0.6・端までの距離 3 の場で約 30 回)。
   上流の端も 1/r² で欠けているので(R = 0.6、距離 3 で 4 %)、端の中央値をそのまま U にすると直線が曲がる。

Returns:
    dict: ``stagnation`` (x, y)、``center`` (x, y)、``radius``、``n_used``、``rms_residual``(1/√d の当てはめの残差)、
    ``speed``、``ok``(点が足りて傾きが負なら True)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_swarm_obstacle_from_flow](../../../../examples/poc_swarm_obstacle_from_flow.py) — `py -3.11 examples/poc_swarm_obstacle_from_flow.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`swarmflow`)

[sph_kernel](sph_kernel.md) · [sph_density_pressure](sph_density_pressure.md) · [swarm_simulate](swarm_simulate.md) · [swarm_render_overhead](swarm_render_overhead.md) · [swarm_field_from_tracks](swarm_field_from_tracks.md) · [swarm_field_from_piv](swarm_field_from_piv.md) · [potential_flow_cylinder](potential_flow_cylinder.md) · [velocity_deficit_map](velocity_deficit_map.md)

---
*Provenance: swarmflow.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
