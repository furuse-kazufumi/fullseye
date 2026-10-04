---
op: insertion_signature
dim: drive
category: pegfail
in: table × table
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# insertion_signature — DRIVE `pegfail` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.insertion_signature(obs, kp=None, stall=None, lateral_tol: 'float' = 0.0) -> 'dict'` (実装を直接呼ぶなら `import pegfail; pegfail.insertion_signature(obs, kp=None, stall=None, lateral_tol: 'float' = 0.0) -> 'dict'`、台帳から引くなら `opsdrive.get("insertion_signature")`)

## 使い方

連続の観測を表の語彙の署名に離散化する。

``obs``: ``contact_kind``(``"none"|"plate"|"chamfer"|"one_point"|"two_point"|"floor"``)、``depth`` [m] (口の面から、負は空中)、
``stalled``(bool、:func:`insertion_stall_detect`)、``theta_onset``(二点接触が始まった時の傾き [rad]、無ければ ``tilt``)、
``fx_over_fz``・``m_over_rfz``(先端の力の比、F_z ≤ 0 なら None)、``depth_l``(Whitney の l = 最狭部からの深さ、省略時 depth − W)、
``offset`` [m] (先端の穴中心からの面内ずれ)。欄の境目: zone は depth < 0 → above、< W → mouth、< hole_depth − 1 mm → hole、
それ以上 → bottom。wedge は θ_onset > c/μ → over。jam は two_point なら :func:`jamming_force_check` の ``inside``、one_point なら
|F_x/F_z| ≤ 1/μ、それ以外・力が無い → na。offset は |ε| > W + c_r → large(:func:`pegsim.chamfer_capture`)。
**Raises** ``ValueError``: 未知の contact_kind、depth が無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegfail`)

[insertion_failure_table](insertion_failure_table.md) · [insertion_failure_validate](insertion_failure_validate.md) · [insertion_failure_classify](insertion_failure_classify.md) · [insertion_recovery_primitive](insertion_recovery_primitive.md) · [jamming_parallelogram_planar](jamming_parallelogram_planar.md) · [jamming_force_check](jamming_force_check.md) · [wedging_risk](wedging_risk.md) · [insertion_stall_detect](insertion_stall_detect.md)

---
*Provenance: pegfail.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
