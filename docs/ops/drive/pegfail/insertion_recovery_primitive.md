---
op: insertion_recovery_primitive
dim: drive
category: pegfail
in: any
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# insertion_recovery_primitive — DRIVE `pegfail` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.insertion_recovery_primitive(name: 'str') -> 'dict'` (実装を直接呼ぶなら `import pegfail; pegfail.insertion_recovery_primitive(name: 'str') -> 'dict'`、台帳から引くなら `opsdrive.get("insertion_recovery_primitive")`)

## 使い方

回復プリミティブの表(クラス → 動作の記述)。``name`` は表の ``recovery`` の語。

``lift_recentre``: 先端を板の上 6 mm まで上げ、手首 RGB-D で (dx, dy) を測って搬送台を寄せ(≤ 6 回)、再降下。
``lift_reapproach``: 口の上 10 mm まで上げ、治具の目標座標へ搬送台を戻し、カメラで寄せて再降下。
``retract_reduce_tilt``: 4 mm 退避し、手首ヒンジの角度を測って把持の傾きをその分戻し(θ → 0)、再降下(p.28 の θ ≤ c/μ へ)。
``steer_force``: 平行四辺形の余裕を線形模型で見て、搬送台の横移動 0.5 mm(F_x と M = L_g F_x が一緒に動く)と手首の回転 0.5°
(M だけが k_r Δ 動く)の組 3 × 3 から余裕が最大の組を選び、進むまで ≤ 6 歩(Whitney p.34: 力の比を図の中へ)。
``lift_abort``: 退避して終了(障害物は押しても取れない)。``continue``: 何もしない。``stop``: 完了。
**Raises** ``ValueError``: 未知の名(綴り壊しは fail-closed)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegfail`)

[insertion_failure_table](insertion_failure_table.md) · [insertion_failure_validate](insertion_failure_validate.md) · [insertion_signature](insertion_signature.md) · [insertion_failure_classify](insertion_failure_classify.md) · [jamming_parallelogram_planar](jamming_parallelogram_planar.md) · [jamming_force_check](jamming_force_check.md) · [wedging_risk](wedging_risk.md) · [insertion_stall_detect](insertion_stall_detect.md)

---
*Provenance: pegfail.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
