---
op: fivebar_ik
dim: drive
category: puck
in: signal × table
out: any
examples: [poc_air_hockey_intercept]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# fivebar_ik — DRIVE `puck` op

- **データ種**: `signal × table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.fivebar_ik(E, link: 'dict', *, branch: 'str' = 'out')` (実装を直接呼ぶなら `import puck; puck.fivebar_ik(E, link: 'dict', *, branch: 'str' = 'out')`、台帳から引くなら `opsdrive.get("fivebar_ik")`)

## 使い方

逆運動学: 先端 E → (q₁, q₂)。腕 i の肘 = 円(Aᵢ, l₁) ∩ 円(E, l₂)、"out" は肘が外側(腕 1 は −y 側、腕 2 は +y 側)、
"in" はその逆。届かなければ ``None``(fail-closed)。FK∘IK = 恒等になる領域が作業域(:func:`fivebar_workspace`)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_air_hockey_intercept](../../../../examples/poc_air_hockey_intercept.py) — `py -3.11 examples/poc_air_hockey_intercept.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`puck`)

[puck_table](puck_table.md) · [puck_wall_bounce](puck_wall_bounce.md) · [puck_slide_predict](puck_slide_predict.md) · [puck_state_at](puck_state_at.md) · [puck_crossing_point](puck_crossing_point.md) · [puck_mirror_path](puck_mirror_path.md) · [puck_stop_distance](puck_stop_distance.md) · [puck_camera](puck_camera.md)

---
*Provenance: puck.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
