---
op: insertion_failure_table
dim: drive
category: pegfail
in: 
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# insertion_failure_table — DRIVE `pegfail` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.insertion_failure_table() -> 'list'` (実装を直接呼ぶなら `import pegfail; pegfail.insertion_failure_table() -> 'list'`、台帳から引くなら `opsdrive.get("insertion_failure_table")`)

## 使い方

失敗分類表(データ): 各行 = {``cls``, ``when``(欄 → 許す値の集合、``"*"`` = 何でも), ``recovery``, ``basis``}。

行の根拠(``basis``)は Whitney 1982(OCW スライドの頁)か接触形成の幾何。順番に意味は無い —— 署名に当たる行は **高々 1 行**
(:func:`insertion_failure_validate` が全ペアで確かめる)。回復プリミティブの語彙は :func:`insertion_recovery_primitive`。

表(接触 / 深さの帯 / 進み / くさび / かじり / ずれ → クラス → 回復):
  * none|plate, above|mouth, stalled, *, *, large → ``missed_hole`` → lift_recentre(先端が面取りに乗れない |ε₀| > W + c_r、導出 (4))
  * chamfer, above|mouth, *, *, *, small → ``chamfer_sliding`` → continue(面取り通過は正常な過程、OCW p.26)
  * plate, above|mouth, advancing, *, *, * → ``nominal`` → continue(板に触れたがまだ進んでいる = 柔らかい接触の過渡)
  * chamfer|one_point|two_point|floor, *, *, *, *, large → ``wrong_hole`` → lift_reapproach(接触はあるが治具の目標穴から W + c_r 以上離れている)
  * one_point, mouth|hole, advancing, *, *, small → ``nominal`` → continue(一点接触で進む、p.26)
  * two_point, hole, advancing, *, *, small → ``nominal`` → continue(二点接触で進む = 平行四辺形の中、p.34)
  * two_point, hole, stalled, over, *, small → ``wedging`` → retract_reduce_tilt(θ > c/μ、p.28)
  * two_point, hole, stalled, below, outside, small → ``jamming`` → steer_force(力の比が平行四辺形の外、p.34)
  * one_point, mouth|hole, stalled, *, outside, small → ``jamming`` → steer_force(一点接触の摩擦限界 |F_x/F_z| > 1/μ = 縦の辺)
  * floor, hole, *, *, *, small → ``blocked_hole`` → lift_abort(底に届く前に硬い物に当たった)
  * floor, bottom, *, *, *, small → ``seated`` → stop(底着 = 完了)
  * none, *, advancing, *, *, * → ``nominal`` → continue(空中で降下中)
当たらない例(わざと unknown): plate・stalled・small(面取りの内側で板に乗って止まるのは幾何的に不可能 = 計測の矛盾)、
two_point・stalled・below・inside(Whitney なら滑るはずの停滞 = 模型の外)、none・stalled・small(押していないのに止まる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegfail`)

[insertion_failure_validate](insertion_failure_validate.md) · [insertion_signature](insertion_signature.md) · [insertion_failure_classify](insertion_failure_classify.md) · [insertion_recovery_primitive](insertion_recovery_primitive.md) · [jamming_parallelogram_planar](jamming_parallelogram_planar.md) · [jamming_force_check](jamming_force_check.md) · [wedging_risk](wedging_risk.md) · [insertion_stall_detect](insertion_stall_detect.md)

---
*Provenance: pegfail.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
