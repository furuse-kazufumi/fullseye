---
op: camera_world_to_cv
dim: drive
category: pegsim
in: matrix
out: table
examples: [poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# camera_world_to_cv — DRIVE `pegsim` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.camera_world_to_cv(cam_xmat, cam_xpos) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.camera_world_to_cv(cam_xmat, cam_xpos) -> 'dict'`、台帳から引くなら `opsdrive.get("camera_world_to_cv")`)

## 使い方

MuJoCo のカメラ姿勢(``d.cam_xmat`` 3×3 = 世界でのカメラ軸、``d.cam_xpos``)を OpenCV / Fullseye の外部パラメータに:
X_cv = R X_w + t、R = diag(1, −1, −1) Rwcᵀ、t = −R p(MuJoCo は −Z を見て +Y が上、OpenCV は +Z 前で +Y 下)。

返り: ``R``(3×3)、``t``(3,)、``R_cam_to_world`` = Rᵀ。numpy だけ(mujoco 不要)。**Raises** ``ValueError``: 形が違う、R が回転でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pegsim_insertion](../../../../examples/poc_pegsim_insertion.py) — `py -3.11 examples/poc_pegsim_insertion.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
