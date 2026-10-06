---
op: cut_force_fit
dim: drive
category: cutting
in: signal × signal × scalar
out: table
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# cut_force_fit — DRIVE `cutting` op

- **データ種**: `signal × signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cut_force_fit(F_n, w_eff_mm, xi: 'float', min_w_mm: 'float' = 2.0) -> 'dict'` (実装を直接呼ぶなら `import cutting; cutting.cut_force_fit(F_n, w_eff_mm, xi: 'float', min_w_mm: 'float' = 2.0) -> 'dict'`、台帳から引くなら `opsdrive.get("cut_force_fit")`)

## 使い方

切断中の力の列 F(N)と切っている幅 w_eff(mm)から靱性 R(J/m²)を原点を通る最小二乗で出す。

模型: ``F = R · w_eff · g(ξ)``、g = 1/(1+ξ²)(:func:`cut_force_atkins` の slice_push、摩擦なし)。w_eff < ``min_w_mm`` の点
(入り始め)は使わない。★ 合成の真値を同じ模型で作るとこの当てはめは配管の検査にしかならず、摩擦の分は R に吸い込まれる
(返り値の ``model`` に書く)。返り値: ``R``、``rms_n``、``n``、``g``、``model``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_face_render](cutting_face_render.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [knife_edge_track](knife_edge_track.md) · [cut_depth_from_side](cut_depth_from_side.md) · [slice_thickness_profile](slice_thickness_profile.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
