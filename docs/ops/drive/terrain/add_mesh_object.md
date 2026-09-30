---
op: add_mesh_object
dim: drive
category: terrain
in: table × table
out: scalar
examples: [poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# add_mesh_object — DRIVE `terrain` op

- **データ種**: `table × table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.add_mesh_object(world: 'dict', mesh: 'dict', x: 'float', y: 'float', yaw: 'float', *, name: 'str' = '', z: 'float' = 0.0) -> 'int'` (実装を直接呼ぶなら `import driveterrain; driveterrain.add_mesh_object(world: 'dict', mesh: 'dict', x: 'float', y: 'float', yaw: 'float', *, name: 'str' = '', z: 'float' = 0.0) -> 'int'`、台帳から引くなら `opsdrive.get("add_mesh_object")`)

## 使い方

手続き的なメッシュ(tree_mesh / pedestrian_mesh …、原点 = 底面中心)を姿勢に置いて世界に足す。

資産と同じ ``pose``/``dims`` を持たせるので :func:`driveworld.world_move` で動かせる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[road_eval](../long/road_eval.md) · [long_simulate](../long/long_simulate.md) · [stopping_distance_grade](../long/stopping_distance_grade.md) · [stop_line_plan](../long/stop_line_plan.md) · [hill_hold_brake_min](../long/hill_hold_brake_min.md) · [hill_start_rollback](../long/hill_start_rollback.md) · [hill_start_command](../long/hill_start_command.md)

## 同カテゴリ(`terrain`)

[perlin2](perlin2.md) · [fbm_params](fbm_params.md) · [fbm_height](fbm_height.md) · [fbm_gradient](fbm_gradient.md) · [radial_periodogram](radial_periodogram.md) · [spectral_slope](spectral_slope.md) · [course_distance](course_distance.md) · [terrain_params](terrain_params.md)

---
*Provenance: driveterrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
