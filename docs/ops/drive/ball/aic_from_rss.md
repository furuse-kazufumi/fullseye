---
op: aic_from_rss
dim: drive
category: ball
in: 
out: scalar
examples: [poc_video_physics_consistency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# aic_from_rss — DRIVE `ball` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.aic_from_rss(rss: 'float', n: 'int', k: 'int') -> 'float'` (実装を直接呼ぶなら `import ballistics; ballistics.aic_from_rss(rss: 'float', n: 'int', k: 'int') -> 'float'`、台帳から引くなら `opsdrive.get("aic_from_rss")`)

## 使い方

最小二乗の残差平方和から赤池情報量規準 AIC = n ln(RSS/n) + 2k(ガウス雑音、分散は最尤で推定、定数項は落とす)。
同じデータに当てた模型どうしの**差**だけに意味がある(絶対値は尺度と n に依る)。n ≤ k・RSS ≤ 0・非有限は ValueError
(RSS = 0 は AIC = −∞ で、模型選択の問いが立たない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_video_physics_consistency](../../../../examples/poc_video_physics_consistency.py) — `py -3.11 examples/poc_video_physics_consistency.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
