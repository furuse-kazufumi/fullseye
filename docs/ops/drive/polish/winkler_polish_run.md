---
op: winkler_polish_run
dim: drive
category: polish
in: image2d × scalar × scalar × scalar × scalar × scalar
out: table
examples: [poc_polish_wipe_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# winkler_polish_run — DRIVE `polish` op

- **データ種**: `image2d × scalar × scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.winkler_polish_run(z, pressure: 'float', k_w: 'float', k_p: 'float', speed: 'float', duration: 'float', dt=None, n_record: 'int' = 50) -> 'dict'` (実装を直接呼ぶなら `import polish; polish.winkler_polish_run(z, pressure: 'float', k_w: 'float', k_p: 'float', speed: 'float', duration: 'float', dt=None, n_record: 'int' = 50) -> 'dict'`、台帳から引くなら `opsdrive.get("winkler_polish_run")`)

## 使い方

弾性床(Winkler)のパッドを平均圧 ``pressure`` で押し、相対速度 ``speed`` で磨いた時の表面の高さ図 ``z`` の時間発展。
各刻みでパッドの面の高さ z_t を Σ k_w max(0, z − z_t) = N p̄ から解き(当たっている所だけが圧を受ける)、Preston の式で
z ← z − k_p v k_w max(0, z − z_t) Δt(陽解法、c Δt ≤ 0.01、c = k_p k_w v)。
返り ``z``(最後)、``t``・``rms``(平均からのずれの rms、形の除去なし)・``mean``・``contact``(当たっている割合)を
``n_record`` 点、``rate_full_contact`` = c(全面が当たる間 rms は exp(−c t) で減る —— 導出、この関数は使わない)、``dt``、
``steps``。**Raises** ValueError: z の検査、数の検査、c Δt > 0.01。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_polish_wipe_measure](../../../../examples/poc_polish_wipe_measure.py) — `py -3.11 examples/poc_polish_wipe_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`polish`)

[preston_pressure_kernel](preston_pressure_kernel.md) · [preston_removal_map](preston_removal_map.md) · [preston_track_profile](preston_track_profile.md) · [wipe_band_width](wipe_band_width.md) · [raster_wipe_area](raster_wipe_area.md) · [coat_image](coat_image.md) · [coat_thickness_from_image](coat_thickness_from_image.md) · [wipe_coverage](wipe_coverage.md)

---
*Provenance: polish.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
