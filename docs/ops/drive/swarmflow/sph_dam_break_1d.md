---
op: sph_dam_break_1d
dim: drive
category: swarmflow
in: 
out: table
examples: [poc_swarm_obstacle_from_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# sph_dam_break_1d — DRIVE `swarmflow` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sph_dam_break_1d(h0: 'float' = 0.1, length: 'float' = 1.0, n_particles: 'int' = 400, t_end: 'float' = 0.2, g: 'float' = 9.81, kappa: 'float' = 1.3, alpha: 'float' = 0.3, n_out: 'int' = 5) -> 'dict'` (実装を直接呼ぶなら `import swarmflow; swarmflow.sph_dam_break_1d(h0: 'float' = 0.1, length: 'float' = 1.0, n_particles: 'int' = 400, t_end: 'float' = 0.2, g: 'float' = 9.81, kappa: 'float' = 1.3, alpha: 'float' = 0.3, n_out: 'int' = 5) -> 'dict'`、台帳から引くなら `opsdrive.get("sph_dam_break_1d")`)

## 使い方

1 次元 SPH の浅水方程式でダム崩壊(乾いた床)を解く(群れのゲートを開けたときの広がりの模型)。

水深 h_i = Σ_j m_j W(x_i − x_j, ℓ_ij)(1 次元の核、m = h₀ Δx)、加速度 du_i/dt = −g Σ_j m_j ∂W_ij/∂x_i(= −g ∂h/∂x、
運動量を保存する対称形)+ Monaghan の人工粘性。平滑化の長さは粒子ごとに ℓ_i = κ m/h_i(先端の薄い所で広がる)、
組には平均 ℓ_ij。左の壁(x = −length)は鏡像の粒子。真値は :func:`ritter_dam_break`(門で照らす)。

Returns:
    dict: ``t`` (K,)、``x`` (K, N)、``h`` (K, N)、``u`` (K, N)(各時刻の粒子)、``front`` (K,)(最も前の粒子)、
    ``mass``(全質量、保存)、``c0``。

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
