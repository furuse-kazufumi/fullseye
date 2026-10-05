---
op: band_width_profile
dim: drive
category: polish
in: image2d × scalar × scalar
out: table
examples: [poc_polish_wipe_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# band_width_profile — DRIVE `polish` op

- **データ種**: `image2d × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.band_width_profile(image, threshold: 'float', res: 'float', along: 'str' = 'x') -> 'dict'` (実装を直接呼ぶなら `import polish; polish.band_width_profile(image, threshold: 'float', res: 'float', along: 'str' = 'x') -> 'dict'`、台帳から引くなら `opsdrive.get("band_width_profile")`)

## 使い方

直線の一筆(``along`` の向き)で拭けた帯の幅を、帯に直交する線ごとに副画素で読む: しきい値を最初に越える所と最後に越える所を
隣の画素との線形補間で求め、その差 × res。返り ``widths``(線ごと、読めない線は NaN)、``centres``(帯の中心の位置 [m]、
地図の座標)、``valid``、``median``。帯が 1 本である前提(複数の帯は外側どうしの幅になる)。
**Raises** ValueError: 画像の検査、res ≤ 0、along が x / y でない、しきい値が非有限。

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
