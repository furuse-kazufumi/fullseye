---
op: cut_force_atkins
dim: drive
category: cutting
in: scalar × scalar
out: table
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# cut_force_atkins — DRIVE `cutting` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cut_force_atkins(R_j_per_m2: 'float', width_mm: 'float', xi: 'float' = 0.0, wedge_deg: 'float | None' = None, mu: 'float' = 0.0, model: 'str | None' = None) -> 'dict'` (実装を直接呼ぶなら `import cutting; cutting.cut_force_atkins(R_j_per_m2: 'float', width_mm: 'float', xi: 'float' = 0.0, wedge_deg: 'float | None' = None, mu: 'float' = 0.0, model: 'str | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("cut_force_atkins")`)

## 使い方

柔らかい固体の切断力の閉形式(尺度 = 靱性 R × 切っている幅 w、R と w の 1 次)。返り値 dict(N)。

``model="slice_push"``(既定、``wedge_deg`` なし): 摩擦なしの押し + 引き(Atkins 2016、Interface Focus 6:20160019 の
式 1.2〜1.4): ``V/(Rw) = 1/(1+ξ²)``、``H/(Rw) = ξ/(1+ξ²)``、``F_res/(Rw) = 1/√(1+ξ²)``。ξ = 刃に沿う速度 / 刃を横切る速度。
``model="wedge_friction"``(``wedge_deg`` を渡す、押しだけ ξ = 0): 弾性の切りくず + Coulomb 摩擦(Williams & Patel 2016、
Interface Focus 6:20150108 の式 2.6、μ = tan β): ``Fc/(b Gc) = 1 / ((1 − cos θ) + sin θ / tan(β + θ))``。θ は原文の工具角。
最小は θ + β = 90° で ``1/(1 − sin β)``。
★ 摩擦と刃角が入った slice/push の式は未読なので実装しない: ξ > 0 と ``wedge_deg`` / ``mu`` の同時指定は ValueError。

返り値: ``V``(押し)、``H``(引き、wedge_friction では nan)、``F_res``、``scale`` = R·w、wedge_friction では ``Fc_over_bGc``。

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
