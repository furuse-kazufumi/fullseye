---
op: ritter_dam_break
dim: drive
category: swarmflow
in: signal × scalar × scalar
out: table
examples: [poc_swarm_obstacle_from_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# ritter_dam_break — DRIVE `swarmflow` op

- **データ種**: `signal × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ritter_dam_break(x, t: 'float', h0: 'float', g: 'float' = 9.81, particle_mass=None) -> 'dict'` (実装を直接呼ぶなら `import swarmflow; swarmflow.ritter_dam_break(x, t: 'float', h0: 'float', g: 'float' = 9.81, particle_mass=None) -> 'dict'`、台帳から引くなら `opsdrive.get("ritter_dam_break")`)

## 使い方

Ritter のダム崩壊解(浅水方程式、乾いた床、ダムは x = 0、水は x < 0)。

c₀ = √(g h₀)。x ≤ −c₀ t: h = h₀、u = 0 / −c₀ t < x < 2c₀ t: h = (2c₀ − x/t)²/(9g)、u = (2/3)(x/t + c₀) / x ≥ 2c₀ t: h = 0。

先端の近くは h ∝ (x_f − x)² で水がほとんど無い。先端から δ までの水の量は ∫₀^δ (s/t)²/(9g) ds = δ³/(27 g t²)(導出)。
粒子 1 個の量 m(1 次元の SPH なら h₀Δx)を与えると、**最も前の粒子の居場所**(先端から量 m/2 の所)
x_f − (27 g t² m/2)^{1/3} を ``lead_particle`` に返す —— 粒子法の先端は Ritter の先端より必ず遅れて見え、その遅れは
この式で読める(粒子を細かくすると m^{1/3} でしか縮まない)。

Returns:
    dict: ``h``・``u``(x と同じ形)、``front`` = 2c₀ t、``rarefaction_head`` = −c₀ t、``c0``、``lead_particle``(m を与えたとき)。

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
