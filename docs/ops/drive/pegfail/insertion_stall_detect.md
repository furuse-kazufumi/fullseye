---
op: insertion_stall_detect
dim: drive
category: pegfail
in: signal
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# insertion_stall_detect — DRIVE `pegfail` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.insertion_stall_detect(depth, window: 'int' = 30, min_advance: 'float' = 5e-05, arm_advance: 'float' = 0.0005) -> 'dict'` (実装を直接呼ぶなら `import pegfail; pegfail.insertion_stall_detect(depth, window: 'int' = 30, min_advance: 'float' = 5e-05, arm_advance: 'float' = 0.0005) -> 'dict'`、台帳から引くなら `opsdrive.get("insertion_stall_detect")`)

## 使い方

深さの時系列 [m] から停滞を検出する(各刻 i で depth[i] − depth[i − window] < min_advance なら stalled)。

降下が始まる前(構えている間)は深さが一定で、素朴な検出器は鳴る —— ``arm_advance`` だけ進んでから **武装**する(onset はそれ以後の
最初の stalled)。返り: ``stalled``(bool の列、同じ長さ)、``onset``(最初の停滞の添字、無ければ −1)、``armed_at``(武装した添字、
−1 なら武装せず = 一度も進まなかった)、``n_stalled``。単調降下(速度 ≥ min_advance/window)では鳴らない(門)。
**Raises** ``ValueError``: window < 1、min_advance ≤ 0、系列が空。

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
