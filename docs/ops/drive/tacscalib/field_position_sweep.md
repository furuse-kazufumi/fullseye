---
op: field_position_sweep
dim: drive
category: tacscalib
in: matrix × signal × any
out: table
examples: [poc_tacscalib_sphere_lut]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# field_position_sweep — DRIVE `tacscalib` op

- **データ種**: `matrix × signal × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.field_position_sweep(centres, errors, image_shape) -> 'dict'` (実装を直接呼ぶなら `import tacscalib; tacscalib.field_position_sweep(centres, errors, image_shape) -> 'dict'`、台帳から引くなら `opsdrive.get("field_position_sweep")`)

## 使い方

誤差の位置依存: 各画像の接触中心 (行, 列) と誤差(中央値など)を画像中心からの距離に対して並べ、最小二乗の傾き
[誤差 / 100 px] と Spearman の順位相関(同順位は平均順位)を返す(numpy だけ)。
返り: ``dist_px``・``err``・``slope_per_100px``・``intercept``・``spearman``・``n``。
**Raises** ``ValueError``: 3 組未満 / 形の不一致 / 非有限 / image_shape の形。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacscalib`)

[calib_pack_load](calib_pack_load.md) · [sphere_normals_known](sphere_normals_known.md) · [lights_fit_from_sphere](lights_fit_from_sphere.md) · [membrane_predict_rgb](membrane_predict_rgb.md) · [gradient_lut_build](gradient_lut_build.md) · [gradient_lut_invert](gradient_lut_invert.md) · [normal_error_map](normal_error_map.md) · [sphere_cap_height](sphere_cap_height.md)

---
*Provenance: tacscalib.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
