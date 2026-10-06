---
op: cutting_edge_render
dim: drive
category: cutting
in: table × any × scalar × scalar × scalar
out: rgb
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# cutting_edge_render — DRIVE `cutting` op

- **データ種**: `table × any × scalar × scalar × scalar` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.cutting_edge_render(scene, end_face, cut_y_top: 'float', lean_deg: 'float', edge_z: 'float', blade: 'bool' = True, gain: 'float' = 1.0, gradient: 'float' = 0.0, blur_px: 'float' = 0.0, noise: 'float' = 0.0, seed: 'int' = 0)` (実装を直接呼ぶなら `import cutting; cutting.cutting_edge_render(scene, end_face, cut_y_top: 'float', lean_deg: 'float', edge_z: 'float', blade: 'bool' = True, gain: 'float' = 1.0, gradient: 'float' = 0.0, blur_px: 'float' = 0.0, noise: 'float' = 0.0, seed: 'int' = 0)`、台帳から引くなら `opsdrive.get("cutting_edge_render")`)

## 使い方

刃先方向の像(RGB)。暗い背景・食材(右側が本体)・刃(片刃、平らな面が切片側)。

``end_face`` は食材の端面 y(z)(mm): 数なら平らな面、``{"z_mm", "y_mm"}`` か (N, 2) の配列なら標本を線形補間(前の切断面の
粗さを持たせる)。``cut_y_top`` は切断面(= 刃の平らな面)が食材の上面と交わる y、``lean_deg`` は刃の傾き(鉛直から、+ で下ほど
本体側 = 下ほど切片が厚い)、``edge_z`` は刃先の高さ。端面は行ごとに縦 8 副行で被覆率を積分する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_depth_decode](../carla/carla_depth_decode.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_face_render](cutting_face_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [knife_edge_track](knife_edge_track.md) · [cut_depth_from_side](cut_depth_from_side.md) · [slice_thickness_profile](slice_thickness_profile.md) · [cut_surface_roughness](cut_surface_roughness.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
