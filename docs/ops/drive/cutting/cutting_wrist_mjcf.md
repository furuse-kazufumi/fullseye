---
op: cutting_wrist_mjcf
dim: drive
category: cutting
in: table × scalar
out: any
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# cutting_wrist_mjcf — DRIVE `cutting` op

- **データ種**: `table × scalar` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.cutting_wrist_mjcf(scene=None, theta_deg: 'float' = 4.0, k_n_per_mm: 'float' = 4.0, damping: 'float' = 25.0, mass: 'float' = 0.15) -> 'str'` (実装を直接呼ぶなら `import cutting; cutting.cutting_wrist_mjcf(scene=None, theta_deg: 'float' = 4.0, k_n_per_mm: 'float' = 4.0, damping: 'float' = 25.0, mass: 'float' = 0.15) -> 'str'`、台帳から引くなら `opsdrive.get("cutting_wrist_mjcf")`)

## 使い方

柔らかい手首の刃の場面(MJCF 文字列、mujoco 不要)。刃は縦のスライド関節(ばね ``k``・減衰)1 本、食材と板は見た目だけ。

カメラ ``face`` は正射影で、画素の寸法と ``board_row`` が :func:`cutting_face_render` と同じになるよう置く。画像の中心は
画素中心で数えて ((H−1)/2, (W−1)/2)(H/2 と書くと 0.5 px ずれる)。関節の摩擦損失は硬くしてある(既定の柔らかい摩擦損失は
速度に比例する粘性のように振る舞い、切断力が 1 桁小さく出る)。食材の抵抗は走行中に関節の摩擦損失として毎歩書き換える
(:func:`cutting_mujoco_wrist`)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_face_render](cutting_face_render.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [knife_edge_track](knife_edge_track.md) · [cut_depth_from_side](cut_depth_from_side.md) · [slice_thickness_profile](slice_thickness_profile.md) · [cut_surface_roughness](cut_surface_roughness.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
