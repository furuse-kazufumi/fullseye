---
op: sphere_normals_known
dim: drive
category: tacscalib
in: any × any × scalar × scalar
out: table
examples: [poc_tacscalib_sphere_lut]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# sphere_normals_known — DRIVE `tacscalib` op

- **データ種**: `any × any × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sphere_normals_known(shape, centre, a_px: 'float', R_px: 'float', inner: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import tacscalib; tacscalib.sphere_normals_known(shape, centre, a_px: 'float', R_px: 'float', inner: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsdrive.get("sphere_normals_known")`)

## 使い方

既知球の押し込み: 接触円(中心 ``centre`` = (行, 列)、半径 ``a_px``)の内側で法線を閉形式で返す。

n = (−dx, −dy, √(R² − r²))/R(dx = 列 − 中心の列、dy = 行 − 中心の行)。マスクは r < inner · min(a, R)(較正手順と同じく
a と R の小さい方まで)。外側は (0, 0, 1)。返り: ``normals`` (H, W, 3)、``mask`` (H, W) bool、``r`` (H, W) [px]、
``theta``(傾き角 = atan2(r, √(R² − r²))、マスク外 0)。
**Raises** ``ValueError``: shape・centre の形、a・R ≤ 0、inner が 0 < inner ≤ 1 の外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacscalib`)

[calib_pack_load](calib_pack_load.md) · [lights_fit_from_sphere](lights_fit_from_sphere.md) · [membrane_predict_rgb](membrane_predict_rgb.md) · [gradient_lut_build](gradient_lut_build.md) · [gradient_lut_invert](gradient_lut_invert.md) · [normal_error_map](normal_error_map.md) · [sphere_cap_height](sphere_cap_height.md) · [field_position_sweep](field_position_sweep.md)

---
*Provenance: tacscalib.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
