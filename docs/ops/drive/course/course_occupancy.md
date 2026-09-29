---
op: course_occupancy
dim: drive
category: course
in: table
out: image2d
examples: [poc_driving_school]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# course_occupancy — DRIVE `course` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.course_occupancy(course, cell: 'float' = 0.25, margin: 'float' = 2.0)` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_occupancy(course, cell: 'float' = 0.25, margin: 'float' = 2.0)`、台帳から引くなら `opsdrive.get("course_occupancy")`)
- **台帳経由の戻り値**: `fullseye.ledger.course_occupancy(...)` は**宣言 out 型 `image2d` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.course_occupancy.raw(...)`、または `drivecourse.course_occupancy` を直接呼ぶ。

## 使い方

コース(要素または配置)を占有格子 ``(occ bool [row = y, col = x], extent)`` に落とす。

**走れる領域の外 = True(障害物)**。格子は bounds を ``margin`` だけ広げた範囲を ``cell`` で覆い、
各 cell の中心で偶奇判定する。``extent = (xmin, xmax, ymin, ymax)`` は格子がちょうど覆う範囲
(xmax = xmin + nx·cell)、row 0 = ymin。占有率は cell → 0 で 1 − 面積/格子面積 に収束する(門)。

**Raises** ``ValueError``: cell ≤ 0、margin < 0、course の形が悪い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md)

## 同カテゴリ(`course`)

[course_crank](course_crank.md) · [course_s_curve](course_s_curve.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_parallel_parking](course_parallel_parking.md) · [course_crossing](course_crossing.md) · [course_road](course_road.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
