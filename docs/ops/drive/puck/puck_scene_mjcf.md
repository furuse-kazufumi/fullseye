---
op: puck_scene_mjcf
dim: drive
category: puck
in: table
out: any
examples: [poc_air_hockey_intercept]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# puck_scene_mjcf — DRIVE `puck` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.puck_scene_mjcf(table: 'dict', *, cam_height: 'float' = 1.5, fovy: 'float' = 50.0, offwidth: 'int' = 1024, offheight: 'int' = 768) -> 'str'` (実装を直接呼ぶなら `import puck; puck.puck_scene_mjcf(table: 'dict', *, cam_height: 'float' = 1.5, fovy: 'float' = 50.0, offwidth: 'int' = 1024, offheight: 'int' = 768) -> 'str'`、台帳から引くなら `opsdrive.get("puck_scene_mjcf")`)

## 使い方

自前の最小 MJCF(Coulomb 版、mujoco 不要): 摩擦のある平面に円柱のパック(自由関節)、4 枚の壁(箱)、真上カメラ。
Challenge の台は粘性減衰なので、Coulomb の等減速を MuJoCo で確かめるにはこちらを使う。壁の反発は軟接触で e は測る。

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
