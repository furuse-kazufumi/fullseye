---
op: cylinder_fit_known_radius
dim: drive
category: pegsim
in: points
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# cylinder_fit_known_radius — DRIVE `pegsim` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cylinder_fit_known_radius(points, r: 'float', axis_point, axis, iters: 'int' = 25) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.cylinder_fit_known_radius(points, r: 'float', axis_point, axis, iters: 'int' = 25) -> 'dict'`、台帳から引くなら `opsdrive.get("cylinder_fit_known_radius")`)

## 使い方

半径 r が既知の円柱を 3-D 点群 (N, 3) に当てる: 軸上の点(軸に垂直な 2 自由度)と軸の向き(2 自由度)を Gauss-Newton で。

初期値 ``axis_point``・``axis`` から出発し、残差 = 軸からの距離 − r。返り: ``axis_point``(3,)、``axis``(単位、入力の向きを保つ)、
``rms``、``n``。**Raises** ``ValueError``: 点が 5 未満、r ≤ 0、axis がゼロ。

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
