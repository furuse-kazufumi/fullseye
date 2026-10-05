---
op: peg_tip_from_rgbd
dim: drive
category: pegsim
in: rgb × image2d × matrix
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# peg_tip_from_rgbd — DRIVE `pegsim` op

- **データ種**: `rgb × image2d × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.peg_tip_from_rgbd(rgb, depth, K, r_peg: 'float' = 0.005, peg_mask=None) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.peg_tip_from_rgbd(rgb, depth, K, r_peg: 'float' = 0.005, peg_mask=None) -> 'dict'`、台帳から引くなら `opsdrive.get("peg_tip_from_rgbd")`)

## 使い方

手首 RGB-D 1 枚からペグ先端の中心を 3-D(カメラ座標)で: ペグの画素 → depth の点群 → PCA の軸 → 既知半径の円柱当てはめ、
先端の軸方向は影の端(副画素、被覆率)を、投影した縁の円の端と一致させる模型で決める。

返り: ``tip_cam``(3,)、``axis``(先端 → 上、単位)、``rms_cyl``、``n_pts``、``uv``(先端の投影)、``delta_axial``。
正直に: 試作の 16 姿勢で軸方向の誤差 max 0.83 px(横方向 0.004 px)—— 影の端 1 画素の被覆率だけから軸方向を読む限界で、
目標 0.3 px は未達。**Raises** ``RuntimeError``: ペグが見えない(芯の画素 < 50)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
