---
op: hill_hold_brake_min
dim: drive
category: long
in: scalar
out: scalar
examples: [poc_driving_longitudinal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# hill_hold_brake_min — DRIVE `long` op

- **データ種**: `scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.hill_hold_brake_min(theta: 'float', c_rr: 'float' = 0.012, a_creep: 'float' = 0.0, g: 'float' = 9.80665) -> 'float'` (実装を直接呼ぶなら `import drivelong; drivelong.hill_hold_brake_min(theta: 'float', c_rr: 'float' = 0.012, a_creep: 'float' = 0.0, g: 'float' = 9.80665) -> 'float'`、台帳から引くなら `opsdrive.get("hill_hold_brake_min")`)

## 使い方

坂で止まっていられる最小の制動 [m/s²] = max(0, |a_creep − g sin θ| − c_rr g cos θ)(静止摩擦のつり合い)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`long`)

[long_params](long_params.md) · [road_profile](road_profile.md) · [road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [long_energy_residual](long_energy_residual.md) · [stopping_distance_grade](stopping_distance_grade.md) · [stop_line_plan](stop_line_plan.md) · [plan_command](plan_command.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
