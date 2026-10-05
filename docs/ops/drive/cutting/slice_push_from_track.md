---
op: slice_push_from_track
dim: drive
category: cutting
in: scalar × signal × signal
out: scalar
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# slice_push_from_track — DRIVE `cutting` op

- **データ種**: `scalar × signal × signal` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.slice_push_from_track(theta_deg: 'float', x_mm, z_mm) -> 'float'` (実装を直接呼ぶなら `import cutting; cutting.slice_push_from_track(theta_deg: 'float', x_mm, z_mm) -> 'float'`、台帳から引くなら `opsdrive.get("slice_push_from_track")`)

## 使い方

刃の 1 点の軌跡 (x, z)(画像から)と刃先の傾き θ(画像から)で ξ を出す。速度は軌跡の直線当てはめの向き(ξ は比)。

押している区間だけを渡すこと。入り始め(手首が縮む途中)を混ぜると刃が指令より遅れて ξ が偏る —— 刃が食材の全幅を
切っている定常区間を使う(PoC で 0.63 → 0.57 = 真値に戻ることを確かめた)。

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
