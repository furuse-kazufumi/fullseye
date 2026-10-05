---
op: knife_edge_track
dim: drive
category: cutting
in: rgb
out: table
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# knife_edge_track — DRIVE `cutting` op

- **データ種**: `rgb` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.knife_edge_track(image, board_row: 'float | None' = None, win: 'int' = 6, reject_px: 'float' = 1.0, method: 'str' = 'coverage') -> 'dict'` (実装を直接呼ぶなら `import cutting; cutting.knife_edge_track(image, board_row: 'float | None' = None, win: 'int' = 6, reject_px: 'float' = 1.0, method: 'str' = 'coverage') -> 'dict'`、台帳から引くなら `opsdrive.get("knife_edge_track")`)

## 使い方

正面像から刃先の直線・峰・先端を出す(規則のみ)。

手順: 輝度の縦の段が「暗 → 明」(刃 → 壁)になる行を列ごとに拾う → 食材の列(彩度の規則)と周辺 3 px を除く → 被覆率法で
副画素に(窓はぼけの推定に合わせて広げる)→ 全最小二乗の直線(``measure.fit_line`` と同じ定式)→ 残差 > ``reject_px`` を外して
当て直す。上側の境界(峰と先端の斜め線)も同じく拾い、峰の直線から外れた右側の連続部分 = 斜め線、刃先線との交点 = 先端。
食材に隠れた列(``occluded_cols``)の刃先は、両側から当てた 1 本の直線の内挿になる。

``method``: ``"coverage"``(既定)か ``"gradient"``(微分の重心、比較用)。返り値: ``angle_deg``(x 右・z 上の反時計回り、
atan2)、``line``(row = cy + (col − cx)·dy/dx の全最小二乗)、``slope``、``offset``、``tip_rc``(先端、見つからなければ None)、
``n_points``、``rms_px``、``cols_used``、``occluded_cols``。刃が写っていなければ ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_face_render](cutting_face_render.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [cut_depth_from_side](cut_depth_from_side.md) · [slice_thickness_profile](slice_thickness_profile.md) · [cut_surface_roughness](cut_surface_roughness.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
