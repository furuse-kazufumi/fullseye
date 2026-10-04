---
op: wedging_risk
dim: drive
category: pegfail
in: table × scalar
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# wedging_risk — DRIVE `pegfail` op

- **データ種**: `table × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.wedging_risk(kp, theta: 'float', margin_deg: 'float' = 0.5) -> 'dict'` (実装を直接呼ぶなら `import pegfail; pegfail.wedging_risk(kp, theta: 'float', margin_deg: 'float' = 0.5) -> 'dict'`、台帳から引くなら `opsdrive.get("wedging_risk")`)

## 使い方

傾き θ [rad] のくさびの危険度: 境目 c/μ(OCW p.28)に対する比 θ/(c/μ) と、余裕 ``margin_deg`` を見た 3 段(``safe`` /
``near`` / ``over``)。pegsim.wedging_check を包み、``theta_limit_deg``・``headroom_deg`` = c/μ − θ を度で足す。
μ = 0 では境目が inf で常に safe。**Raises** ``ValueError``: θ < 0、margin_deg < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegfail`)

[insertion_failure_table](insertion_failure_table.md) · [insertion_failure_validate](insertion_failure_validate.md) · [insertion_signature](insertion_signature.md) · [insertion_failure_classify](insertion_failure_classify.md) · [insertion_recovery_primitive](insertion_recovery_primitive.md) · [jamming_parallelogram_planar](jamming_parallelogram_planar.md) · [jamming_force_check](jamming_force_check.md) · [insertion_stall_detect](insertion_stall_detect.md)

---
*Provenance: pegfail.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
