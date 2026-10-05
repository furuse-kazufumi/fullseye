---
op: wedging_check
dim: drive
category: pegsim
in: table
out: table
examples: [poc_peg_insertion_tactile, poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# wedging_check — DRIVE `pegsim` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.wedging_check(kp, theta: 'float') -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.wedging_check(kp, theta: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("wedging_check")`)

## 使い方

二点接触が始まる時点の傾き θ [rad] で、くさび(wedging)が起こりうるか(OCW p.28: θ > c/μ)。

返り: ``possible``(θ > c/μ)、``theta_limit`` = c/μ、``l2``(その θ での二点接触の深さ、exact。θ ≥ θ_m_exact なら 0)、
``l2_over_d``、``lambda`` = l₂/(2rμ)、``possible_small_angle``(l₂/d < μ ⇔ λ < 1。小角では ``possible`` と同じ判定)。
μ = 0 なら摩擦円錐が無いので常に False。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`
- [poc_pegsim_insertion](../../../../examples/poc_pegsim_insertion.py) — `py -3.11 examples/poc_pegsim_insertion.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md) · [cylinder_fit_known_radius](cylinder_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
