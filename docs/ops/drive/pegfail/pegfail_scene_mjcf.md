---
op: pegfail_scene_mjcf
dim: drive
category: pegfail
in: table
out: any
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# pegfail_scene_mjcf — DRIVE `pegfail` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.pegfail_scene_mjcf(kp=None, lg: 'float | None' = None, blocked_depth: 'float | None' = None, decoy_xy=None, offsamples: 'int' = 4) -> 'str'` (実装を直接呼ぶなら `import pegfail; pegfail.pegfail_scene_mjcf(kp=None, lg: 'float | None' = None, blocked_depth: 'float | None' = None, decoy_xy=None, offsamples: 'int' = 4) -> 'str'`、台帳から引くなら `opsdrive.get("pegfail_scene_mjcf")`)

## 使い方

失敗注入つきの場面の MJCF 文字列(mujoco 不要): pegsim.peg_scene_mjcf を ElementTree で読み、(i) 手首の力・トルクセンサ
(site ``peg_top`` = 手首原点、子 body と親の相互作用力)、(ii) ``blocked_depth`` [m] なら穴の中にその深さを上面とする栓(円柱)、
(iii) ``decoy_xy`` なら囮の穴(壁・面取り・襟を複製して平行移動、名前に ``decoy_`` を付ける。四角い枠は囮と重なるので外す)。
**Raises** ``ValueError``: 栓の深さが穴の外、囮が目標穴と重なる(中心距離 < 2(R + W) + 1 mm)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`pegfail`)

[insertion_failure_table](insertion_failure_table.md) · [insertion_failure_validate](insertion_failure_validate.md) · [insertion_signature](insertion_signature.md) · [insertion_failure_classify](insertion_failure_classify.md) · [insertion_recovery_primitive](insertion_recovery_primitive.md) · [jamming_parallelogram_planar](jamming_parallelogram_planar.md) · [jamming_force_check](jamming_force_check.md) · [wedging_risk](wedging_risk.md)

---
*Provenance: pegfail.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
