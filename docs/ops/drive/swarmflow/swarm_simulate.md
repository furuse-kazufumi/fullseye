---
op: swarm_simulate
dim: drive
category: swarmflow
in: 
out: table
examples: [poc_swarm_obstacle_from_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# swarm_simulate — DRIVE `swarmflow` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.swarm_simulate(obstacle=None, speed: 'float' = 1.0, box=(8.0, 5.0), spacing: 'float' = 0.15, h_factor: 'float' = 1.3, tau: 'float' = 0.1, c: 'float' = 10.0, alpha: 'float' = 0.5, t_warm: 'float' = 2.0, n_frames: 'int' = 20, frame_dt: 'float' = 0.06, noise: 'float' = 0.0, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import swarmflow; swarmflow.swarm_simulate(obstacle=None, speed: 'float' = 1.0, box=(8.0, 5.0), spacing: 'float' = 0.15, h_factor: 'float' = 1.3, tau: 'float' = 0.1, c: 'float' = 10.0, alpha: 'float' = 0.5, t_warm: 'float' = 2.0, n_frames: 'int' = 20, frame_dt: 'float' = 0.06, noise: 'float' = 0.0, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("swarm_simulate")`)

## 使い方

障害物のある周期の流路を流れる群れ(SPH の弱圧縮流体として動く個体)。障害物は個体には「ぶつかる壁」として効くだけ。

個体 i の加速度 = (U e_x − v_i)/τ(自由流の速さへ戻る)− Σ_j m (p_i/ρ_i² + p_j/ρ_j²) ∇W_ij(圧力 = 押し合い)
− Σ_j m Π_ij ∇W_ij(Monaghan の人工粘性、近づく組だけ)+ 揺らぎ(標準偏差 ``noise`` [m/s²] の白色)。
壁: 円の内側に入った個体は表面へ戻し、内向きの速度だけ消す(滑る壁)。周期境界(x も y も)。積分は symplectic Euler、
刻みは CFL 0.25 h/(c + U)。U τ ≪ R・c ≫ U のとき定常の流れは円柱まわりのポテンシャル流に近い(module docstring の導出)。

Args:
    obstacle: (xc, yc, R) [m] か None(障害物なし)。
    speed: 自由流の速さ U [m/s]。
    box: 流路の大きさ (Lx, Ly) [m]、中心が原点。
    spacing: 初期の格子の間隔 [m] (個体の間隔)。
    h_factor: h = h_factor × spacing。
    tau: 速さへ戻る時定数 [s]。
    c: 音速 [m/s] (押し合いの硬さ)。
    alpha: 人工粘性の係数。
    t_warm: 記録の前に流す時間 [s] (定常に近づける)。
    n_frames: 記録するコマ数(≥ 2)。
    frame_dt: コマの間隔 [s]。
    noise: 加速度の揺らぎ [m/s²]。
    seed: 乱数の種。
Returns:
    dict: ``frames`` (T, N, 2) 位置 [m] (箱の中へ折り返し済み)、``velocities`` (T, N, 2)、``t`` (T,)、``box``、
    ``obstacle``、``h``、``dt``、``rho0``、``density_range``(記録の間の ρ/ρ₀ の 1〜99 % 点)、``n_agents``、
    ``t_total``(流した時間)、``t_wake_reenters``(障害物の後ろの空洞が箱の右端から左端へ回り込み始める時刻
    (Lx/2 − x_c − R)/U。これより長く流すと、上流の端に空洞の個体が入ってきて自由流が汚れる)。

★障害物の後ろには個体の入らない空洞が長く伸びる(押し合いの圧力は引っ張らないほど弱く、抵抗で U に戻るだけなので
横から埋まらない)。俯瞰の映像では障害物の所の「穴」と空洞そのものが見える —— 速度だけで推定するという主張は、
推定がこの穴を使わない(速度場の欠測として捨てる)という意味で、映像に障害物の手がかりが無いという意味ではない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_swarm_obstacle_from_flow](../../../../examples/poc_swarm_obstacle_from_flow.py) — `py -3.11 examples/poc_swarm_obstacle_from_flow.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`swarmflow`)

[sph_kernel](sph_kernel.md) · [sph_density_pressure](sph_density_pressure.md) · [swarm_render_overhead](swarm_render_overhead.md) · [swarm_field_from_tracks](swarm_field_from_tracks.md) · [swarm_field_from_piv](swarm_field_from_piv.md) · [potential_flow_cylinder](potential_flow_cylinder.md) · [velocity_deficit_map](velocity_deficit_map.md) · [stagnation_from_centerline](stagnation_from_centerline.md)

---
*Provenance: swarmflow.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
