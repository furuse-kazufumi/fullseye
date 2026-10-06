---
op: insertion_failure_validate
dim: drive
category: pegfail
in: table
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# insertion_failure_validate — DRIVE `pegfail` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.insertion_failure_validate(table=None) -> 'dict'` (実装を直接呼ぶなら `import pegfail; pegfail.insertion_failure_validate(table=None) -> 'dict'`、台帳から引くなら `opsdrive.get("insertion_failure_validate")`)

## 使い方

表を検証する(fail-closed): 欄の語彙・クラス名・回復名の綴り、**全ペアの排他**(2 行が同じ署名に当たり得ないか = 全欄で
許す集合が交わる行の組が無い)、**到達性**(unknown 以外の全クラスに ≥ 1 行)。

返り: ``n_rows``、``classes_covered``、``classes_missing``、``n_signatures``(語彙の直積の大きさ)、``n_covered``(どれかの行に
当たる署名の数)、``coverage``、``overlaps``(交わる行の組 —— 空でなければ下の ValueError)。
**Raises** ``ValueError``: 綴り違い・交わる行・届かないクラス。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegfail`)

[insertion_failure_table](insertion_failure_table.md) · [insertion_signature](insertion_signature.md) · [insertion_failure_classify](insertion_failure_classify.md) · [insertion_recovery_primitive](insertion_recovery_primitive.md) · [jamming_parallelogram_planar](jamming_parallelogram_planar.md) · [jamming_force_check](jamming_force_check.md) · [wedging_risk](wedging_risk.md) · [insertion_stall_detect](insertion_stall_detect.md)

---
*Provenance: pegfail.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
