---
op: circle_fit_known_radius
dim: drive
category: pegsim
in: matrix
out: table
examples: [poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# circle_fit_known_radius — DRIVE `pegsim` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.circle_fit_known_radius(points, r: 'float', iters: 'int' = 30) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.circle_fit_known_radius(points, r: 'float', iters: 'int' = 30) -> 'dict'`、台帳から引くなら `opsdrive.get("circle_fit_known_radius")`)

## 使い方

半径 r が既知の円を 2-D 点列 (row, col) に当てる(中心だけを Gauss-Newton で解く。部分弧でも安定)。

:func:`measure.fit_circle`(代数的、半径も未知)と同じ入出力の規約(``cy``・``cx``・``rms``)。ペグの断面のように半径が
図面で分かっている対象は、半径を固定したほうが短い弧でも中心が決まる(自由な当てはめは弧が短いと半径と中心が相殺する)。
**Raises** ``ValueError``: 点が 2 つ未満、非有限、r ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pegsim_insertion](../../../../examples/poc_pegsim_insertion.py) — `py -3.11 examples/poc_pegsim_insertion.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [cylinder_fit_known_radius](cylinder_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
