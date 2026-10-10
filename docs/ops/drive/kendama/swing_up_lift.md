---
op: swing_up_lift
dim: drive
category: kendama
in: table
out: scalar
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# swing_up_lift — DRIVE `kendama` op

- **データ種**: `table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.swing_up_lift(kp: 'dict', *, apex_above_cup: 'float' = None, T_lift: 'float' = 0.15, g: 'float' = None) -> 'float'` (実装を直接呼ぶなら `import kendama; kendama.swing_up_lift(kp: 'dict', *, apex_above_cup: 'float' = None, T_lift: 'float' = 0.15, g: 'float' = None) -> 'float'`、台帳から引くなら `opsdrive.get("swing_up_lift")`)

## 使い方

振り上げ(bang)の持ち上げ量を閉形式で: 玉の頂点が受ける皿の中心の ``apex_above_cup`` 上に来る lift(:func:`swing_up_apex` の逆)。
頂点 − lift − cup_z = tie_z + lift/2 − L + 2 lift²/(g T²) − lift − cup_z = A を lift の 2 次方程式として正の根。
既定 A = max(h_c + 0.9 r_b, (top_offset − cup_z) + r_b + 0.035): 玉の下端がけん玉のいちばん高い所を 35 mm 越える頂点
(:func:`catch_plan_staged` の hold は玉がそこを越えるまで皿を寄せない。越えている時間 ≈ 2√(2·0.03/g) = 0.17 s で皿を
横へ 10 cm 戻す)。減速の加速度 4·lift/T² が g を超えないと玉は飛ばない(ValueError)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
