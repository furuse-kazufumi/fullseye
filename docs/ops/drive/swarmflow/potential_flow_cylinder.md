---
op: potential_flow_cylinder
dim: drive
category: swarmflow
in: signal × signal × any
out: table
examples: [poc_swarm_obstacle_from_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# potential_flow_cylinder — DRIVE `swarmflow` op

- **データ種**: `signal × signal × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.potential_flow_cylinder(x, y, cylinder, speed: 'float' = 1.0, grid: 'bool' = False) -> 'dict'` (実装を直接呼ぶなら `import swarmflow; swarmflow.potential_flow_cylinder(x, y, cylinder, speed: 'float' = 1.0, grid: 'bool' = False) -> 'dict'`、台帳から引くなら `opsdrive.get("potential_flow_cylinder")`)

## 使い方

円柱まわりのポテンシャル流(閉形式)。u − i v = U (1 − R²/(z − z_c)²)、円の内側は NaN。

``grid=True`` なら ``x``・``y`` を格子の軸(1 次元、行 = y の順)とみなし、速度場の dict(module の規約)を返す。
既定の ``grid=False`` は要素ごと(同じ形に broadcast)に ``u``・``v``・``inside`` を返す —— 軸か点の列かを形で
推し量らない(同じ長さの 1 次元の x と y はどちらにも読めて、点の列が黙って格子になる)。どちらにも ``stagnation``(上流の衝突点
(x_c − R, y_c))と ``rear_stagnation`` と ``surface_speed_max``(= 2U)を付ける。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_swarm_obstacle_from_flow](../../../../examples/poc_swarm_obstacle_from_flow.py) — `py -3.11 examples/poc_swarm_obstacle_from_flow.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`swarmflow`)

[sph_kernel](sph_kernel.md) · [sph_density_pressure](sph_density_pressure.md) · [swarm_simulate](swarm_simulate.md) · [swarm_render_overhead](swarm_render_overhead.md) · [swarm_field_from_tracks](swarm_field_from_tracks.md) · [swarm_field_from_piv](swarm_field_from_piv.md) · [velocity_deficit_map](velocity_deficit_map.md) · [stagnation_from_centerline](stagnation_from_centerline.md)

---
*Provenance: swarmflow.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
