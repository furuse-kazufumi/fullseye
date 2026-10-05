---
op: cutting_scene
dim: drive
category: cutting
in: any
out: table
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# cutting_scene — DRIVE `cutting` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cutting_scene(kind: 'str' = 'face', px_per_mm: 'float | None' = None, **overrides) -> 'dict'` (実装を直接呼ぶなら `import cutting; cutting.cutting_scene(kind: 'str' = 'face', px_per_mm: 'float | None' = None, **overrides) -> 'dict'`、台帳から引くなら `opsdrive.get("cutting_scene")`)

## 使い方

合成の場面の諸元(dict)。``kind="face"`` = 正面像(カメラは刃の面の法線方向)、``"edge"`` = 刃先方向の像。

正面像: 刃は食材より長く、食材の左右で刃先の直線が見える。食材の幅の中は食材に隠れる。キーは ``food_xc`` / ``food_w`` /
``food_h``(食材の中心・幅・高さ)、``blade_len`` / ``blade_h`` / ``tip_slant``(刃先の長さ・刃の高さ・先端の斜め部)。
刃先方向の像: 刃は細い帯に見え、片刃の平らな面と食材の端面の距離が切片の厚み。キーは ``food_top``、``blade_tb``(峰の厚み)、
``blade_hb``(片刃の切刃の高さ)、``blade_h``。

``px_per_mm`` を変えると画素の寸法 ``H`` / ``W`` / ``board_row``(z = 0 の行)が比例して変わる(mm の寸法は同じ)。
既定は正面像 8 px/mm(800×480)、刃先方向 20 px/mm(520×560)。知らないキーは ValueError(綴り壊しを黙って通さない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`cutting`)

[cutting_face_render](cutting_face_render.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [knife_edge_track](knife_edge_track.md) · [cut_depth_from_side](cut_depth_from_side.md) · [slice_thickness_profile](slice_thickness_profile.md) · [cut_surface_roughness](cut_surface_roughness.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
