---
op: peg_scene_mjcf
dim: drive
category: pegsim
in: table
out: any
examples: [poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# peg_scene_mjcf — DRIVE `pegsim` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.peg_scene_mjcf(kp=None, lg: 'float | None' = None, offsamples: 'int' = 4, timestep: 'float' = 0.0005) -> 'str'` (実装を直接呼ぶなら `import pegsim; pegsim.peg_scene_mjcf(kp=None, lg: 'float | None' = None, offsamples: 'int' = 4, timestep: 'float' = 0.0005) -> 'str'`、台帳から引くなら `opsdrive.get("peg_scene_mjcf")`)

## 使い方

場面の MJCF 文字列(mujoco 不要): 穴 = 内接面が半径 R の箱 n_seg 個の環 + 45° の面取りの環 + 口の面の襟 + 四角い枠、
位置制御の搬送台(x, y, z のスライド)に 6 つのばね関節の柔らかい手首、その先にペグ(円柱)。手首カメラは搬送台の 60 mm 後ろ・
20 mm 上から 45° 下向き、側面カメラは固定。

``lg`` = 先端から回転のコンプライアンス中心までの距離(None → 手首原点 = ペグ長、0 → 先端に中心 = RCC)。``offsamples`` は
MSAA(RGB 用 4、depth 用 0 で別にコンパイルする —— 深度はサンプル 0 の位置になる罠)。``<quality numslices="128">`` で円柱の
多角形近似を 0.0015 % に(既定 28 では半径が 0.04 mm 内側)。単位 m、口の面 z = 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pegsim_insertion](../../../../examples/poc_pegsim_insertion.py) — `py -3.11 examples/poc_pegsim_insertion.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
