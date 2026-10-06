---
op: peg_offset_from_rgbd
dim: drive
category: pegsim
in: rgb × image2d × matrix × matrix
out: table
examples: [poc_peg_failure_recovery, poc_peg_insertion_tactile, poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# peg_offset_from_rgbd — DRIVE `pegsim` op

- **データ種**: `rgb × image2d × matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.peg_offset_from_rgbd(rgb, depth, K, R_cam_to_world, r_peg: 'float' = 0.005, hole_radius: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.peg_offset_from_rgbd(rgb, depth, K, R_cam_to_world, r_peg: 'float' = 0.005, hole_radius: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("peg_offset_from_rgbd")`)

## 使い方

手首 RGB-D 1 枚から、穴中心に対するペグ先端の相対ずれ (dx, dy) [m] を世界(搬送台)座標で —— 視覚サーボの観測量。

``R_cam_to_world`` はカメラ座標のベクトルを世界へ回す 3×3(hand-eye)。ずれは板の平面内の成分、``height`` は先端の板からの高さ。
``hole_radius`` を与えると穴の円を既知半径で当てる(:func:`hole_centre_from_rgbd`)。
返り: ``hole``・``tip``(各計測の dict)、``dx``・``dy``・``height``。試作(16 姿勢): |dx|, |dy| の最大 0.010 mm。

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
