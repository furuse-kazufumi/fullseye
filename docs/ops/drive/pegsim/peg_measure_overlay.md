---
op: peg_measure_overlay
dim: drive
category: pegsim
in: rgb × matrix × matrix
out: rgb
examples: [poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# peg_measure_overlay — DRIVE `pegsim` op

- **データ種**: `rgb × matrix × matrix` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.peg_measure_overlay(rgb, truth_uv, est_uv, edge_uv=None, size: 'int' = 12, zoom: 'int' = 3, crop: 'int' = 40) -> 'np.ndarray'` (実装を直接呼ぶなら `import pegsim; pegsim.peg_measure_overlay(rgb, truth_uv, est_uv, edge_uv=None, size: 'int' = 12, zoom: 'int' = 3, crop: 'int' = 40) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("peg_measure_overlay")`)

## 使い方

計測の重ね図(numpy だけ): 真値 = 緑の大きな十字、推定 = 赤の小さな十字、円当てはめに使った縁の点 = 黄の点(imagedraw)。
右下に真値の重心まわり ``crop`` px 四方を ``zoom`` 倍にした拡大を貼る(副画素の一致を目で見るため)。

``rgb`` は (H, W, 3) uint8、``truth_uv``・``est_uv`` は (N, 2) の (u, v)。返りは同じ大きさの uint8。
**Raises** ``ValueError``: rgb の形が違う、点が無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pegsim_insertion](../../../../examples/poc_pegsim_insertion.py) — `py -3.11 examples/poc_pegsim_insertion.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_depth_decode](../carla/carla_depth_decode.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
