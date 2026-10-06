---
op: jamming_force_check
dim: drive
category: pegfail
in: table × scalar × scalar × scalar
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# jamming_force_check — DRIVE `pegfail` op

- **データ種**: `table × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.jamming_force_check(kp, depth: 'float', fx_over_fz: 'float', m_over_rfz: 'float', tol: 'float' = 0.0, side: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import pegfail; pegfail.jamming_force_check(kp, depth: 'float', fx_over_fz: 'float', m_over_rfz: 'float', tol: 'float' = 0.0, side: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("jamming_force_check")`)

## 使い方

計測した先端の力の比 (F_x/F_z, M/(rF_z)) が Whitney の平行四辺形の内側か(pegsim.jamming_diagram を包み、どの辺に近いか・
どちらの斜辺が今の接触配置に効くかを足す)。

**規約**(:func:`jamming_parallelogram_planar` の導出で固定): e_x は「先端が触れている壁から反対側の口の縁へ」向かう水平単位
ベクトル、F_x はその向きの成分、F_z は押し込み(下向き)正、M = M⃗·(e_x × e_z)(x 右・z 上の平面で反時計回り正)。この規約で
今の配置に効く斜辺は切片 −λ の線(``side=-1``)。``side=+1`` は鏡像、``side=0`` は両方(平行四辺形の全体)。
``tol`` は内側判定の余裕(負なら厳しく)。返り: ``inside``、``margin``(4 辺の最小余裕、負なら外)、``edge``(最小余裕の辺の名)、
``margins``(dict)、``lambda``、``active_line``。**Raises** ``ValueError``: 力の比が有限でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegfail`)

[insertion_failure_table](insertion_failure_table.md) · [insertion_failure_validate](insertion_failure_validate.md) · [insertion_signature](insertion_signature.md) · [insertion_failure_classify](insertion_failure_classify.md) · [insertion_recovery_primitive](insertion_recovery_primitive.md) · [jamming_parallelogram_planar](jamming_parallelogram_planar.md) · [wedging_risk](wedging_risk.md) · [insertion_stall_detect](insertion_stall_detect.md)

---
*Provenance: pegfail.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
