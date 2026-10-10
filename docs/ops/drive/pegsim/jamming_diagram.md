---
op: jamming_diagram
dim: drive
category: pegsim
in: table
out: table
examples: [poc_peg_failure_recovery, poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# jamming_diagram — DRIVE `pegsim` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.jamming_diagram(kp, depth: 'float', fx_over_fz: 'float | None' = None, m_over_rfz: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.jamming_diagram(kp, depth: 'float', fx_over_fz: 'float | None' = None, m_over_rfz: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("jamming_diagram")`)

## 使い方

かじり(jamming)の図(OCW p.34): 二点接触の深さ l [m] で、加える力の比 (F_x/F_z, M/(rF_z)) が進める領域の平行四辺形。

λ = l/(2rμ)。頂点は (−1/μ, 2λ+1), (1/μ, −1), (1/μ, −(2λ+1)), (−1/μ, 1)、縦軸の切片 ±λ、縦辺は F_x/F_z = ±1/μ。深さが増える
(λ が増える)と縦に広がり、かじりにくくなる。``fx_over_fz`` と ``m_over_rfz`` を与えると ``inside``(内側なら進む)と
``margin``(4 辺の不等式の最小の余裕、負なら外)も返す。
**Raises** ``ValueError``: l < 0、μ ≤ 0(摩擦なしは平行四辺形が無限に広い)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`
- [poc_pegsim_insertion](../../../../examples/poc_pegsim_insertion.py) — `py -3.11 examples/poc_pegsim_insertion.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md) · [cylinder_fit_known_radius](cylinder_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
