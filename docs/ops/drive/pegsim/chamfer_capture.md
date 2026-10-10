---
op: chamfer_capture
dim: drive
category: pegsim
in: table
out: table
examples: [poc_peg_failure_recovery, poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# chamfer_capture — DRIVE `pegsim` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.chamfer_capture(kp, eps0: 'float') -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.chamfer_capture(kp, eps0: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("chamfer_capture")`)

## 使い方

初期の横ずれ ε₀ [m] を面取りが補正なしで吸収できるか: |ε₀| ≤ W + c_r(先端の縁が面取り面の上に着地する条件、導出)。

返り: ``captured``、``eps_max`` = W + c_r、``margin`` = eps_max − |ε₀|。既定の寸法では 1.2 mm。
傾き θ₀ があると先端の縁の投影が動くが、θ₀ ≤ 3° では無視できる(試作の格子で ε₀ = 2, 3 mm が補正なしで失敗した根拠)。

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

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md) · [cylinder_fit_known_radius](cylinder_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
