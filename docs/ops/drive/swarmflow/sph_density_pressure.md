---
op: sph_density_pressure
dim: drive
category: swarmflow
in: matrix × scalar
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# sph_density_pressure — DRIVE `swarmflow` op

- **データ種**: `matrix × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sph_density_pressure(points, h: 'float', mass: 'float' = 1.0, rho0: 'float' = 1.0, c: 'float' = 10.0, box=None) -> 'dict'` (実装を直接呼ぶなら `import swarmflow; swarmflow.sph_density_pressure(points, h: 'float', mass: 'float' = 1.0, rho0: 'float' = 1.0, c: 'float' = 10.0, box=None) -> 'dict'`、台帳から引くなら `opsdrive.get("sph_density_pressure")`)

## 使い方

点の集まりの SPH 密度 ρ_i = Σ_j m W(|x_i − x_j|, h)(自分を含む)と、弱圧縮の状態方程式 p = c² (ρ − ρ₀)。

格子の間隔 Δ で m = ρ₀ Δ² に置けば、内側の点の ρ は ρ₀ に近い(h = 1.3Δ で 0.3 % 以内 —— 門で数える)。

Args:
    points: (N, 2) の位置 [m]。
    h: 平滑化の長さ [m]。
    mass: 1 点の質量(群れでは 1 = 個体数の密度)。
    rho0: 静止の密度。
    c: 音速 [m/s] (圧力の硬さ)。
    box: 周期境界の箱 (Lx, Ly) か None。
Returns:
    dict: ``rho`` (N,)、``p`` (N,)、``n_neighbors`` (N,)(台の中の他の点の数)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`swarmflow`)

[sph_kernel](sph_kernel.md) · [swarm_simulate](swarm_simulate.md) · [swarm_render_overhead](swarm_render_overhead.md) · [swarm_field_from_tracks](swarm_field_from_tracks.md) · [swarm_field_from_piv](swarm_field_from_piv.md) · [potential_flow_cylinder](potential_flow_cylinder.md) · [velocity_deficit_map](velocity_deficit_map.md) · [stagnation_from_centerline](stagnation_from_centerline.md)

---
*Provenance: swarmflow.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
