---
op: raster_wipe_area
dim: drive
category: polish
in: scalar × scalar × scalar × scalar
out: table
examples: [poc_polish_wipe_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# raster_wipe_area — DRIVE `polish` op

- **データ種**: `scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.raster_wipe_area(radius: 'float', length: 'float', pitch: 'float', n_strokes: 'int', centre=(0.0, 0.0), step=None) -> 'dict'` (実装を直接呼ぶなら `import polish; polish.raster_wipe_area(radius: 'float', length: 'float', pitch: 'float', n_strokes: 'int', centre=(0.0, 0.0), step=None) -> 'dict'`、台帳から引くなら `opsdrive.get("raster_wipe_area")`)

## 使い方

半径 ``radius`` の工具で、長さ ``length`` の平行な一筆(+x へ、間隔 ``pitch`` で +y へ並べ、一筆ごとに持ち上げて戻る)を
``n_strokes`` 本引いた時、工具が触れた面積の閉形式: (2a + (N − 1) min(s, 2a)) L + N π a² − (N − 1) lens(s)。
返り ``area``、``rect_area``、``disc_union_area``、``lens``、``overlap_saving``(N 本の和 − 面積)、``path``((M, 2)、NaN で
区切った軌跡、``step`` があれば各一筆をその刻みの点列に)。**Raises** ValueError: 数の検査、n_strokes < 1、面積が溢れる、
一筆の点が 1e6 を超える。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_polish_wipe_measure](../../../../examples/poc_polish_wipe_measure.py) — `py -3.11 examples/poc_polish_wipe_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`polish`)

[preston_pressure_kernel](preston_pressure_kernel.md) · [preston_removal_map](preston_removal_map.md) · [preston_track_profile](preston_track_profile.md) · [wipe_band_width](wipe_band_width.md) · [coat_image](coat_image.md) · [coat_thickness_from_image](coat_thickness_from_image.md) · [wipe_coverage](wipe_coverage.md) · [band_width_profile](band_width_profile.md)

---
*Provenance: polish.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
