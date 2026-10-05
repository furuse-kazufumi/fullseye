---
op: insertion_episode_summary
dim: drive
category: pegfail
in: table
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# insertion_episode_summary — DRIVE `pegfail` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.insertion_episode_summary(ep) -> 'dict'` (実装を直接呼ぶなら `import pegfail; pegfail.insertion_episode_summary(ep) -> 'dict'`、台帳から引くなら `opsdrive.get("insertion_episode_summary")`)

## 使い方

1 走行の記録(:func:`pegfail_episode_run` の返り、または同じ鍵の dict)を要約: 注入クラス、最初に**検出**された失敗クラス、
検出の遅れ(真の失敗の始まり ``failing_onset_tick`` → 検出の刻、刻 = 10 ms)、回復の回数と成否、最終深さ・最大力。

``ep["rec"]`` は列 ``depth``・``cls_truth``・``detected``・``force`` を持つ dict。返り: ``injected``、``first_cls``、``first_cls_tick``、
``stall_onset_tick``(= 使った onset)、``latency_ticks``(nan なら検出なし)、``recoveries``、``success``、``status``、
``final_depth_mm``、``max_force_N``、``classes_seen``。

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
