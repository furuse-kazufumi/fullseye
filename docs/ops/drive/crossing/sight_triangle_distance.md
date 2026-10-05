---
op: sight_triangle_distance
dim: drive
category: crossing
in: 
out: scalar
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# sight_triangle_distance — DRIVE `crossing` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sight_triangle_distance(eye_offset: 'float', eye_distance: 'float', corner_offset: 'float', corner_distance: 'float') -> 'float'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.sight_triangle_distance(eye_offset: 'float', eye_distance: 'float', corner_offset: 'float', corner_distance: 'float') -> 'float'`、台帳から引くなら `opsdrive.get("sight_triangle_distance")`)

## 使い方

角の建物があるとき、線路の上でどこまで見えるか(見通しの三角形)。

線路 = x 軸(y = 0)、道路の中心 = x = 0。目 = (eye_offset, −eye_distance)、建物の角 = (corner_offset, −corner_distance)、
建物は x ≥ corner_offset かつ y ≤ −corner_distance を占める(角の向こうの側、corner_offset > eye_offset)。
返り値 = 見える線路の上の最も遠い点の x(道路の中心から)。corner_distance ≥ eye_distance(建物が目より線路寄りに
出ていない)なら遮らず ∞。左側は x を反転して同じ式を使う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`crossing`)

[crossing_timing_check](crossing_timing_check.md) · [crossing_gate_state](crossing_gate_state.md) · [crossing_lamp_signal](crossing_lamp_signal.md) · [lamp_pair_phase](lamp_pair_phase.md) · [crossing_clear_time](crossing_clear_time.md) · [exit_room_check](exit_room_check.md) · [crossing_stop_check](crossing_stop_check.md) · [track_sight_distance](track_sight_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
