---
op: slice_thickness_profile
dim: drive
category: cutting
in: rgb × scalar × scalar
out: table
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# slice_thickness_profile — DRIVE `cutting` op

- **データ種**: `rgb × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.slice_thickness_profile(image, px_per_mm: 'float', board_row: 'float', z_band=None, win: 'int' = 4) -> 'dict'` (実装を直接呼ぶなら `import cutting; cutting.slice_thickness_profile(image, px_per_mm: 'float', board_row: 'float', z_band=None, win: 'int' = 4) -> 'dict'`、台帳から引くなら `opsdrive.get("slice_thickness_profile")`)

## 使い方

刃先方向の像で、行ごとに「食材の端面」と「刃の平らな面」の副画素位置を出し、差 = 切片の厚み(mm)。

各画素を 3 色(背景・食材・刃)の割合に**線形分解**する(彩度 R − B と輝度の 2 チャンネル + 和 = 1)。背景の割合は端面で
1 → 0 に落ちる純粋な段、刃の割合は刃の面で 0 → 1 に上がる純粋な段なので、それぞれの窓の中の和が縁の位置になる(被覆率法)。
ぼけは割合の和を変えないので、窓をぼけの推定(端面の段の 2 次モーメント σ)に合わせて ±(3σ + 1) px に広げれば偏らない。
切片が窓より薄くても、2 つの段は別々の割合なので干渉しない。参照の色は行ごとに局所で取る(照明の左右勾配に追従)。
刃の判定は「刃の輝度が背景と食材の間のどこにあるか」の比で行い、明るさの倍率(gain)に依らない。

端面と刃の面はそれぞれ直線に乗るはず: 1.5 px より外れた行を外し、外れが 3 割を超えたら ValueError(黙って間違えない)。
``z_band``: (z_lo, z_hi) mm で使う行を絞る(片刃の切刃部を外すのに使う)。返り値: ``z_mm``、``thickness_mm``(行ごと)、
``mean_mm``、``lean_deg``(刃の面の鉛直からの傾き、atan2)、``face_line``、``end_line``、``n_rows``、``n_rejected``、``blur_px``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_face_render](cutting_face_render.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [knife_edge_track](knife_edge_track.md) · [cut_depth_from_side](cut_depth_from_side.md) · [cut_surface_roughness](cut_surface_roughness.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
