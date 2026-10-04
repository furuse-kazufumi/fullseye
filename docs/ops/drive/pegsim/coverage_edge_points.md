---
op: coverage_edge_points
dim: drive
category: pegsim
in: image2d × image2d × image2d
out: matrix
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# coverage_edge_points — DRIVE `pegsim` op

- **データ種**: `image2d × image2d × image2d` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.coverage_edge_points(gray, inside, outside, min_contrast: 'float' = 25.0, exclude=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import pegsim; pegsim.coverage_edge_points(gray, inside, outside, min_contrast: 'float' = 25.0, exclude=None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("coverage_edge_points")`)

## 使い方

反エイリアスされた境界の明るさ(被覆率)から副画素の縁の点 (u, v) を返す: inside 側の画素 p と 2 画素先が outside の対で、
縁の位置 = p から (−0.5 + f_p + f_q) 画素(f = その画素の inside 側の被覆率 = (I − I_out) / (I_in − I_out))。

4 軸方向(上下左右)の対を全部使う。``inside`` / ``outside`` は bool マスク(同じ形)、``gray`` は明るさ(float)。
``min_contrast`` 未満の対は捨て、``exclude`` のマスクに掛かる対も捨てる。返りは (N, 2) の (u, v)(列・行)。
**Raises** ``ValueError``: 形が違う、対が 1 つも無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
