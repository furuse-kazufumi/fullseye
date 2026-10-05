---
op: cutting_face_render
dim: drive
category: cutting
in: table × scalar × scalar × scalar
out: rgb
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# cutting_face_render — DRIVE `cutting` op

- **データ種**: `table × scalar × scalar × scalar` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.cutting_face_render(scene, heel_x: 'float', heel_z: 'float', theta_deg: 'float', gain: 'float' = 1.0, gradient: 'float' = 0.0, blur_px: 'float' = 0.0, noise: 'float' = 0.0, seed: 'int' = 0, food_visible: 'bool' = True)` (実装を直接呼ぶなら `import cutting; cutting.cutting_face_render(scene, heel_x: 'float', heel_z: 'float', theta_deg: 'float', gain: 'float' = 1.0, gradient: 'float' = 0.0, blur_px: 'float' = 0.0, noise: 'float' = 0.0, seed: 'int' = 0, food_visible: 'bool' = True)`、台帳から引くなら `opsdrive.get("cutting_face_render")`)

## 使い方

正面像(RGB、(H, W, 3) float)。壁 → まな板 → 刃 → 食材(手前)の順に、被覆率の解析描画で重ねる。

``heel_x`` / ``heel_z`` は刃の根元の刃先(mm)、``theta_deg`` は刃先の傾き。カメラは ``gain``(明るさの倍率)、``gradient``
(左右の照明勾配、全幅で ±gradient/2)、``blur_px``(ガウスぼけの σ)、``noise``(加法の正規雑音の σ)。
刃の面積は副列 8 本で縦方向を厳密に積分する(多角形の面積と 2e-4 以内、PoC の門)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_depth_decode](../carla/carla_depth_decode.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [knife_edge_track](knife_edge_track.md) · [cut_depth_from_side](cut_depth_from_side.md) · [slice_thickness_profile](slice_thickness_profile.md) · [cut_surface_roughness](cut_surface_roughness.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
