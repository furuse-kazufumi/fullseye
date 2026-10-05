---
op: cut_depth_from_side
dim: drive
category: cutting
in: rgb × table × scalar × scalar
out: table
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# cut_depth_from_side — DRIVE `cutting` op

- **データ種**: `rgb × table × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cut_depth_from_side(image, track, px_per_mm: 'float', board_row: 'float', win: 'int' = 5) -> 'dict'` (実装を直接呼ぶなら `import cutting; cutting.cut_depth_from_side(image, track, px_per_mm: 'float', board_row: 'float', win: 'int' = 5) -> 'dict'`、台帳から引くなら `opsdrive.get("cut_depth_from_side")`)

## 使い方

正面像の食材の上面(彩度の縁、列ごと副画素 → 中央値)と刃先の直線から切り込み深さ(mm)。

深さ = 上面の z − 食材の幅の中央での刃先の z(:func:`knife_edge_track` の直線の内挿)。刃が曲がっていればそのまま誤差になる。
返り値: ``depth_mm``、``top_z_mm``、``edge_z_mm``、``food_cols``(左右)、``n_cols``、``centre_col``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_face_render](cutting_face_render.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [knife_edge_track](knife_edge_track.md) · [slice_thickness_profile](slice_thickness_profile.md) · [cut_surface_roughness](cut_surface_roughness.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
