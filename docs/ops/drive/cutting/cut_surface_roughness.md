---
op: cut_surface_roughness
dim: drive
category: cutting
in: rgb × scalar × scalar × signal
out: table
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# cut_surface_roughness — DRIVE `cutting` op

- **データ種**: `rgb × scalar × scalar × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cut_surface_roughness(image, px_per_mm: 'float', board_row: 'float', z_band, n_sampling: 'int' = 5) -> 'dict'` (実装を直接呼ぶなら `import cutting; cutting.cut_surface_roughness(image, px_per_mm: 'float', board_row: 'float', z_band, n_sampling: 'int' = 5) -> 'dict'`、台帳から引くなら `opsdrive.get("cut_surface_roughness")`)

## 使い方

切った後の端面のシルエット(行ごと副画素)を断面とみなし、最小二乗の直線を引いて ISO 4287 のパラメータ(µm)を出す。

パラメータは ``roughness.profile_params``(Ra / Rq / Rz / Rt …)をそのまま呼ぶ。断面は行の高さ 1 px で平均されるので、
正弦の凹凸は箱型の閉形式 ``sinc(πΔ/λ)``(Δ = 1 px)倍に弱まる。平らな面でも測りの床(雑音と肌理による Rq)が残るので、
比べるときは床を二乗で引く。Rz は雑音の山に引っ張られる(床の扱いは Rq でだけ意味がある)。
返り値: ``profile_um``(行ごとの偏差)、``z_mm``、``params``、``dz_um``(標本間隔)、``n_rows``。

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
