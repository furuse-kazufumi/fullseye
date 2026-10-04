---
op: insertion_failure_presets
dim: drive
category: pegfail
in: table
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# insertion_failure_presets — DRIVE `pegfail` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.insertion_failure_presets(kp=None) -> 'dict'` (実装を直接呼ぶなら `import pegfail; pegfail.insertion_failure_presets(kp=None) -> 'dict'`、台帳から引くなら `opsdrive.get("insertion_failure_presets")`)

## 使い方

注入する失敗の既定(各クラス → :func:`pegfail_episode_run` の引数)。数は Whitney の境目から:
missed_hole = ε₀ 2.5 mm(> W + c_r = 1.2 mm)/ wedging = μ 0.8・θ₀ 4.5°(c/μ = 2.76°)/ jamming = θ₀ 3°(μ = 0.3 ではくさびに
ならない 7.35° の下)で先端が 4 mm 入ってから搬送台の横目標を傾きの側へ +3.0 mm ずらして保持(手首ばね 600 N/m → F_x ≤ 1.8 N、
ヒンジは先端から 40 mm なので M/(rF_z) が平行四辺形の斜辺を越える。実測: −3.0 mm(反対側)では滑って入る、+1.6 mm では
止まるが比は内側 = unknown)/ blocked_hole = 深さ 6 mm に栓 / wrong_hole = 26 mm 横の囮の穴へ向かう / nominal = ε₀ 0.5 mm・θ₀ 1.5°。

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
