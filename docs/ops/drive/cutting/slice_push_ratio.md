---
op: slice_push_ratio
dim: drive
category: cutting
in: scalar × scalar × scalar
out: scalar
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# slice_push_ratio — DRIVE `cutting` op

- **データ種**: `scalar × scalar × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.slice_push_ratio(theta_deg: 'float', vx: 'float', vz: 'float') -> 'float'` (実装を直接呼ぶなら `import cutting; cutting.slice_push_ratio(theta_deg: 'float', vx: 'float', vz: 'float') -> 'float'`、台帳から引くなら `opsdrive.get("slice_push_ratio")`)

## 使い方

刃先の傾き θ(x-z、反時計回り)と刃の速度 (vx, −vz)(vz > 0 で下へ)から slice/push 比 ξ。

刃先方向 u = (cos θ, sin θ)、法線 n = (−sin θ, cos θ) として ξ = |v·u| / |v·n|。vx = 0 なら ξ = tan|θ|(Atkins 2016 の本文
「傾けた刃を縦に動かすと ξ = tan i」)に戻る。刃が自分の刃先に沿って動く(押しが無い)と ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_face_render](cutting_face_render.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [knife_edge_track](knife_edge_track.md) · [cut_depth_from_side](cut_depth_from_side.md) · [slice_thickness_profile](slice_thickness_profile.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
