---
op: pour_scene_mjcf
dim: drive
category: scoop
in: scalar × scalar × scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# pour_scene_mjcf — DRIVE `scoop` op

- **データ種**: `scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pour_scene_mjcf(L: 'float' = 0.06, B: 'float' = 0.04, h0: 'float' = 0.016, radius: 'float' = 0.002, *, wall: 'float' = 0.04, lip_height: 'float' = 0.15, mu_slide: 'float' = 0.16, mu_roll: 'float' = 0.09, density: 'float' = 2500.0, floor_mu: 'float' = 1.0, wall_mu: 'float' = 0.3, timestep: 'float' = 0.0015, contact_tc: 'float' = 0.006, solver_iterations: 'int' = 50, solver: 'str' = 'CG', cone: 'str' = 'elliptic', condim: 'int' = 6, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.pour_scene_mjcf(L: 'float' = 0.06, B: 'float' = 0.04, h0: 'float' = 0.016, radius: 'float' = 0.002, *, wall: 'float' = 0.04, lip_height: 'float' = 0.15, mu_slide: 'float' = 0.16, mu_roll: 'float' = 0.09, density: 'float' = 2500.0, floor_mu: 'float' = 1.0, wall_mu: 'float' = 0.3, timestep: 'float' = 0.0015, contact_tc: 'float' = 0.006, solver_iterations: 'int' = 50, solver: 'str' = 'CG', cone: 'str' = 'elliptic', condim: 'int' = 6, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("pour_scene_mjcf")`)

## 使い方

口の開いた樋(床の長さ ``L``、幅 ``B``、奥壁と側壁の高さ ``wall``)に深さ ``h0`` まで剛体球を格子で詰めた場面の MJCF
(**mujoco 不要**)。樋は mocap の body(``name="trough"``、原点 = 口の床の縁、高さ ``lip_height``)で、口を下げる向き
(y 軸まわりに −θ)に回すのは :func:`scoop_mujoco_pour` が毎歩 ``mocap_quat`` を書いて行う。床は粗く(滑り摩擦
``floor_mu``、底の層が床ごと滑り出さない —— granular の粗い台と同じ役)、側壁は ``wall_mu``。床の口の側(x < 0)が
開いていて、こぼれた球は落ちて地面(高さ 0)に届く。
返り: ``xml``, ``positions``, ``info``(L, B, h0, wall, radius, lip_height, mass_each, n, timestep, A_fill = L·h0)。
**Raises** ``ValueError``: ``h0 ≥ wall`` / ``contact_tc < 2 timestep`` / 球が 1 層も入らない / 綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
