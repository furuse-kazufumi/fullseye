---
op: time_to_line_crossing
dim: drive
category: lateral
in: 
out: scalar
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# time_to_line_crossing — DRIVE `lateral` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.time_to_line_crossing(offset: 'float', heading_error: 'float', curvature: 'float', speed: 'float', *, line_offset: 'float', lane_curvature: 'float' = 0.0) -> 'float'` (実装を直接呼ぶなら `import drivelateral; drivelateral.time_to_line_crossing(offset: 'float', heading_error: 'float', curvature: 'float', speed: 'float', *, line_offset: 'float', lane_curvature: 'float' = 0.0) -> 'float'`、台帳から引くなら `opsdrive.get("time_to_line_crossing")`)

## 使い方

TLC: 車(の基準点)が今の曲率のまま円(または直線)を走るとして、車線の境界に届くまでの時間 [s]。

座標: 車線の中心線の上の点を原点、中心線の向きを +x、左を +y。車は (0, ``offset``)、中心線に対する向き
``heading_error``、曲率 ``curvature``(左が正)。境界は中心線から横 ``line_offset``(左が正)の線 —— 中心線が
曲率 ``lane_curvature`` の円なら、それと同心の円。届かなければ ``inf``。

**Raises** ``ValueError``: 非有限、v ≤ 0、車がすでに境界の外側(offset と line_offset の関係で判断)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [road_eval](../long/road_eval.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
