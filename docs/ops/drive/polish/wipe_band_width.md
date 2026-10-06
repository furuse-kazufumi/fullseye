---
op: wipe_band_width
dim: drive
category: polish
in: scalar × scalar × scalar × scalar
out: table
examples: [poc_polish_wipe_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# wipe_band_width — DRIVE `polish` op

- **データ種**: `scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.wipe_band_width(force: 'float', radius: 'float', k_p: 'float', coat: 'float', kind: 'str' = 'flat', estar=None) -> 'dict'` (実装を直接呼ぶなら `import polish; polish.wipe_band_width(force: 'float', radius: 'float', k_p: 'float', coat: 'float', kind: 'str' = 'flat', estar=None) -> 'dict'`、台帳から引くなら `opsdrive.get("wipe_band_width")`)

## 使い方

厚さ ``coat`` の膜を回らない工具の直線の一筆で拭いた時、膜が消える帯の幅(閉形式)。返り ``width``(0 なら拭けない)、
``half_width``、``force_min``(帯ができ始める力)、``centre_depth``(中心の除去の深さ)、``a``(接触半径)。
平板: D = 2 a k_p p、半幅 a √(1 − (h0/D)²)、F_min = π a h0/(2 k_p)。Hertz: D = k_p E* a²/R、半幅 √(a² − h0 R/(k_p E*))、
F_min = (4E*/3R)(h0 R/(k_p E*))^{3/2}。速さに依らない(回らない時)。**Raises** ValueError: 数の検査。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_polish_wipe_measure](../../../../examples/poc_polish_wipe_measure.py) — `py -3.11 examples/poc_polish_wipe_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`polish`)

[preston_pressure_kernel](preston_pressure_kernel.md) · [preston_removal_map](preston_removal_map.md) · [preston_track_profile](preston_track_profile.md) · [raster_wipe_area](raster_wipe_area.md) · [coat_image](coat_image.md) · [coat_thickness_from_image](coat_thickness_from_image.md) · [wipe_coverage](wipe_coverage.md) · [band_width_profile](band_width_profile.md)

---
*Provenance: polish.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
