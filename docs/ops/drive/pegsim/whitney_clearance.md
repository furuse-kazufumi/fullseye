---
op: whitney_clearance
dim: drive
category: pegsim
in: table
out: table
examples: [poc_peg_failure_recovery, poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# whitney_clearance — DRIVE `pegsim` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.whitney_clearance(kp=None) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.whitney_clearance(kp=None) -> 'dict'`、台帳から引くなら `opsdrive.get("whitney_clearance")`)

## 使い方

Whitney の無次元 clearance と、そこから決まる境目: c = (D − d)/D、c_r = R − r、θ_m = √(2c)、面取りの許容ずれ、くさびの角。

返り: ``c``(clearance ratio、OCW p.11)、``c_r``(半径 clearance)、``theta_m``(小角の θ_m = √(2c)、p.9)、``theta_m_exact``
(arccos(d/D): 水平断面の楕円の長半径 r/cos θ が R に達する角 —— √(2c) はその 2 次の近似)、``eps_chamfer_max``
(W + c_r: 面取りが補正なしで救える初期横ずれ、導出)、``theta_wedge``(c/μ: 二点接触の始まりでこれより傾いていると
くさびが起こりうる、p.28。μ = 0 なら inf)。

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

[peg_params](peg_params.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md) · [cylinder_fit_known_radius](cylinder_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
