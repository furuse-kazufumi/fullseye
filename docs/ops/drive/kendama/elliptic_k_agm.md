---
op: elliptic_k_agm
dim: drive
category: kendama
in: 
out: scalar
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# elliptic_k_agm — DRIVE `kendama` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.elliptic_k_agm(k) -> 'float'` (実装を直接呼ぶなら `import kendama; kendama.elliptic_k_agm(k) -> 'float'`、台帳から引くなら `opsdrive.get("elliptic_k_agm")`)

## 使い方

第 1 種完全楕円積分 K(k) = ∫₀^{π/2} dφ / √(1 − k² sin² φ) を算術幾何平均で: K(k) = π / (2·AGM(1, √(1 − k²)))。
|k| < 1(それ以外は ValueError)。門: K(0) = π/2、K(0.5) = 1.685750354812596(公表値、パラメータ m = k² = 0.25)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md) · [swing_up_apex](swing_up_apex.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
