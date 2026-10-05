---
op: cutting_episode_synth
dim: drive
category: cutting
in: 
out: table
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# cutting_episode_synth — DRIVE `cutting` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.cutting_episode_synth(R: 'float' = 400.0, theta_deg: 'float' = 4.0, vx: 'float' = 6.0, vz: 'float' = 4.0, k_wrist: 'float' = 4.0, dt: 'float' = 0.1, n_frames: 'int' = 40, heel_x0: 'float' = 12.0, edge_start: 'float' = 27.0, scene=None) -> 'dict'` (実装を直接呼ぶなら `import cutting; cutting.cutting_episode_synth(R: 'float' = 400.0, theta_deg: 'float' = 4.0, vx: 'float' = 6.0, vz: 'float' = 4.0, k_wrist: 'float' = 4.0, dt: 'float' = 0.1, n_frames: 'int' = 40, heel_x0: 'float' = 12.0, edge_start: 'float' = 27.0, scene=None) -> 'dict'`、台帳から引くなら `opsdrive.get("cutting_episode_synth")`)

## 使い方

閉形式の運動で切断の 1 回分を作る(準静的、剛塑性の食材 + 縦だけ柔らかい手首)。返り値 dict(列は numpy 配列)。

指令: 刃の根元を (vx, −vz) mm/s で動かす(``k_wrist`` N/mm)。食材は切れ始めるまで動かず、切れている間の押し力は
``R · w_eff · 1/(1+ξ²)``(:func:`cut_force_atkins` の slice_push)。刃は「指令 + F/k」の高さに止まり、切った所は戻らない。
刃先の最下点(食材の幅の中)がまな板の 0.3 mm 上に来たら止める。
返り値: ``t``、``heel_x``、``heel_z_cmd``、``heel_z``、``edge_z_c``(食材中央での刃先の高さの真値)、``F``(押し力の真値)、
``w_eff``、``xi``、``params``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_face_render](cutting_face_render.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [knife_edge_track](knife_edge_track.md) · [cut_depth_from_side](cut_depth_from_side.md) · [slice_thickness_profile](slice_thickness_profile.md) · [cut_surface_roughness](cut_surface_roughness.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
