---
op: stick_radius_modelfree
dim: drive
category: tacslip
in: matrix × matrix
out: table
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# stick_radius_modelfree — DRIVE `tacslip` op

- **データ種**: `matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.stick_radius_modelfree(pts_c, u_px, rel: 'float' = 0.08, abs_px: 'float' = 0.05) -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.stick_radius_modelfree(pts_c, u_px, rel: 'float' = 0.08, abs_px: 'float' = 0.05) -> 'dict'`、台帳から引くなら `opsdrive.get("stick_radius_modelfree")`)

## 使い方

模型なしの固着半径: 中心からの距離順に、内側 6 点の中央値 δ̂ から |ux − δ̂| が rel·|δ̂| + abs_px を超える最初の点と、その手前の点の中点の
半径 ``c_px``(分解能 = マーカー間隔)。``core_px`` = δ̂。pts_c は中心相対 (M, 2) [px]、u_px は (M, 2) [px]。**Raises** ValueError: 点が 6 個未満。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
