---
op: wipe_coverage
dim: drive
category: polish
in: image2d × scalar
out: table
examples: [poc_polish_wipe_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# wipe_coverage — DRIVE `polish` op

- **データ種**: `image2d × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.wipe_coverage(image, res: 'float', threshold='otsu', coat=None, optical_depth: 'float' = 1.3862943611198906, bare: 'float' = 0.85, min_area: 'int' = 4) -> 'dict'` (実装を直接呼ぶなら `import polish; polish.wipe_coverage(image, res: 'float', threshold='otsu', coat=None, optical_depth: 'float' = 1.3862943611198906, bare: 'float' = 0.85, min_area: 'int' = 4) -> 'dict'`、台帳から引くなら `opsdrive.get("wipe_coverage")`)

## 使い方

拭けた所(明るい = 膜が消えた所)の面積を画像から読む。2 値化と連結成分は detect.segment_objects(Otsu が既定)。
返り ``area``(拭けた画素 × res² [m²])、``fraction``、``largest_area``、``n_regions``、``mask``、``threshold``(Otsu の
しきい値 = 拭けた側の最小と残った側の最大の中点で推定)、``coat`` を渡せば ``residual_at_threshold``(しきい値の明るさが意味する
残った膜の厚さ —— 読んだ帯は「除去 ≥ h0 − この厚さ」の所)。**Raises** ValueError: 画像の検査、res ≤ 0、拭けた所も残った所も
無い(しきい値が決まらない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_polish_wipe_measure](../../../../examples/poc_polish_wipe_measure.py) — `py -3.11 examples/poc_polish_wipe_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`polish`)

[preston_pressure_kernel](preston_pressure_kernel.md) · [preston_removal_map](preston_removal_map.md) · [preston_track_profile](preston_track_profile.md) · [wipe_band_width](wipe_band_width.md) · [raster_wipe_area](raster_wipe_area.md) · [coat_image](coat_image.md) · [coat_thickness_from_image](coat_thickness_from_image.md) · [band_width_profile](band_width_profile.md)

---
*Provenance: polish.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
