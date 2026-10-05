---
op: peg_synthetic_rgbd
dim: drive
category: pegsim
in: table
out: table
examples: [poc_peg_failure_recovery, poc_peg_insertion_tactile, poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# peg_synthetic_rgbd — DRIVE `pegsim` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.peg_synthetic_rgbd(kp=None, tip_xyz=(0.002, 0.001, 0.01), axis=(0.0, 0.0, 1.0), width: 'int' = 320, height: 'int' = 240, supersample: 'int' = 4, cam_pos=(-0.06, 0.0, 0.07), fovy_deg: 'float' = 40.0) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.peg_synthetic_rgbd(kp=None, tip_xyz=(0.002, 0.001, 0.01), axis=(0.0, 0.0, 1.0), width: 'int' = 320, height: 'int' = 240, supersample: 'int' = 4, cam_pos=(-0.06, 0.0, 0.07), fovy_deg: 'float' = 40.0) -> 'dict'`、台帳から引くなら `opsdrive.get("peg_synthetic_rgbd")`)

## 使い方

真値つきの合成 RGB-D(numpy だけ、mujoco 不要): 板 z = 0(灰)、穴の円盤(半径 R + W、黒、4 mm 下の面)、ペグ(半径 r の円柱 +
先端の円盤、橙)を手首カメラ(45° 下向き、MJCF と同じ向き)から解析的にレイキャストする。

深度は**画素中心**の +Z 距離(実物の RGB-D と Fullseye の規約)、色は ``supersample``² 倍の超標本の平均(反エイリアス = 被覆率)。
計測(:func:`peg_offset_from_rgbd`)の門を mujoco 無しで立てるための入力で、MuJoCo の描画の代わりではない(影・照明・面取りの
斜面は描かない)。返り: ``rgb``(H, W, 3) uint8、``depth``(H, W)、``K``、``R``・``t``(世界 → カメラ)、``R_cam_to_world``、
``tip``・``axis``(真値)、``uv_tip``・``uv_hole``(真値の投影)。**Raises** ``ValueError``: axis がゼロ、大きさが小さすぎる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`
- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`
- [poc_pegsim_insertion](../../../../examples/poc_pegsim_insertion.py) — `py -3.11 examples/poc_pegsim_insertion.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
