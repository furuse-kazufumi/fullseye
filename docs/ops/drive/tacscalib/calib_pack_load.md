---
op: calib_pack_load
dim: drive
category: tacscalib
in: text × scalar × scalar
out: table
examples: [poc_tacscalib_sphere_lut]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# calib_pack_load — DRIVE `tacscalib` op

- **データ種**: `text × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.calib_pack_load(path: 'str', pitch_mm: 'float', ball_radius_mm: 'float') -> 'dict'` (実装を直接呼ぶなら `import tacscalib; tacscalib.calib_pack_load(path: 'str', pitch_mm: 'float', ball_radius_mm: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("calib_pack_load")`)

## 使い方

較正パック(npz)→ dict。キー ``f0``(背景 (H, W, 3) uint8)・``imgs``((N, H, W, 3))・``touch_center``((N, 2) = (列 x, 行 y))・
``touch_radius``((N,) px)を必須とし、中心は (行, 列) に並べ替えて ``centers`` で返す。

``pitch_mm`` [mm/px] と ``ball_radius_mm`` は呼び出し側が与える(パックの中に無い)。返り: ``f0``・``imgs``・``centers`` (N, 2)・
``radii`` (N,) [px]・``pitch``(m/px)・``pitch_mm``・``R_mm``・``R_px``(= 半径 / ピッチ)・``n``。
データ置き場は呼び出し側が環境変数(例 ``FULLSEYE_TAXIM_DATA``)から組む。

**Raises** ``ValueError``: キー欠落(綴り違いも)/ 形の不一致 / 画像 0 枚 / 中心が非有限 / 半径 ≤ 0 / pitch・球半径 ≤ 0。
``FileNotFoundError``: パスが無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacscalib`)

[sphere_normals_known](sphere_normals_known.md) · [lights_fit_from_sphere](lights_fit_from_sphere.md) · [membrane_predict_rgb](membrane_predict_rgb.md) · [gradient_lut_build](gradient_lut_build.md) · [gradient_lut_invert](gradient_lut_invert.md) · [normal_error_map](normal_error_map.md) · [sphere_cap_height](sphere_cap_height.md) · [field_position_sweep](field_position_sweep.md)

---
*Provenance: tacscalib.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
