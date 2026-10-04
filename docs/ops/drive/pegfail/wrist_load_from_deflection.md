---
op: wrist_load_from_deflection
dim: drive
category: pegfail
in: table × signal × signal × signal × signal × signal
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# wrist_load_from_deflection — DRIVE `pegfail` op

- **データ種**: `table × signal × signal × signal × signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.wrist_load_from_deflection(kp, q_slide, q_hinge, q_hinge_rest, tip_xyz, axis, lg: 'float | None' = None, peg_mass: 'float' = 0.04, com_from_tip: 'float | None' = None, gravity: 'float' = 9.81) -> 'dict'` (実装を直接呼ぶなら `import pegfail; pegfail.wrist_load_from_deflection(kp, q_slide, q_hinge, q_hinge_rest, tip_xyz, axis, lg: 'float | None' = None, peg_mass: 'float' = 0.04, com_from_tip: 'float | None' = None, gravity: 'float' = 9.81) -> 'dict'`、台帳から引くなら `opsdrive.get("wrist_load_from_deflection")`)

## 使い方

手首ばねのたわみから、支持(+ 重力)がペグに加える荷重を先端まわりで(numpy だけ): F⃗ = −k_t q_slide − m g ẑ、
M⃗_tip = −k_r (q_hinge − rest) + (p_hinge − p_tip) × F⃗_spring + (p_com − p_tip) × F⃗_g。

``q_slide`` = (wx, wy, wz) [m] (搬送台に対する手首の並進、搬送台は回らないので世界軸)、``q_hinge`` = (wrx, wry, wrz) [rad]、
``q_hinge_rest`` = ばねの静止角(把持の傾き)、``lg`` = 先端からヒンジまで(None → ペグ長)、``com_from_tip`` = 重心の先端からの
距離(None → 既定のペグ 0.03 kg @ L/2 + 頭 0.01 kg @ L + 3 mm の重心)。ヒンジ 3 軸のトルクはヒンジの軸が世界軸に揃う
小角(手首の回りは 5° 以下)の近似で世界ベクトルとして足す。返り: ``F``(3,)、``M_tip``(3,)、``F_spring``、``M_hinge``。
**Raises** ``ValueError``: 形が違う、軸がゼロ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegfail`)

[insertion_failure_table](insertion_failure_table.md) · [insertion_failure_validate](insertion_failure_validate.md) · [insertion_signature](insertion_signature.md) · [insertion_failure_classify](insertion_failure_classify.md) · [insertion_recovery_primitive](insertion_recovery_primitive.md) · [jamming_parallelogram_planar](jamming_parallelogram_planar.md) · [jamming_force_check](jamming_force_check.md) · [wedging_risk](wedging_risk.md)

---
*Provenance: pegfail.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
