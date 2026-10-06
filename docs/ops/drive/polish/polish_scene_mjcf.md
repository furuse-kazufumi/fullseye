---
op: polish_scene_mjcf
dim: drive
category: polish
in: scalar
out: any
examples: [poc_polish_wipe_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# polish_scene_mjcf — DRIVE `polish` op

- **データ種**: `scalar` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.polish_scene_mjcf(radius: 'float' = 0.008, k_z: 'float' = 500.0, k_xy: 'float' = 20000.0, mass: 'float' = 0.2, friction: 'float' = 0.3, thickness: 'float' = 0.004, timestep: 'float' = 0.0005) -> 'str'` (実装を直接呼ぶなら `import polish; polish.polish_scene_mjcf(radius: 'float' = 0.008, k_z: 'float' = 500.0, k_xy: 'float' = 20000.0, mass: 'float' = 0.2, friction: 'float' = 0.3, thickness: 'float' = 0.004, timestep: 'float' = 0.0005) -> 'str'`、台帳から引くなら `opsdrive.get("polish_scene_mjcf")`)

## 使い方

平らな板(z = 0 の平面)の上で、円柱の工具(半径 ``radius``、厚さ ``thickness``、質量 ``mass``)を x・y・z の 3 本の直動の
関節で動かす MJCF。z は位置サーボ(ゲイン ``k_z`` [N/m] = 手首の押し付けのばね)、x・y は硬いサーボ ``k_xy``。重力あり。
ばねの閉形式: 工具の底が板に載っている時の法線力 N = m g + k_z (q_surface − q_cmd)(q_surface = 底が z = 0 に来る関節値)。
接触は硬めに(solref の時定数 = 4 × timestep、solimp 0.99)して、めり込みを ばねの縮みより十分小さくする(既定の柔らかい接触では
質量 0.05 kg・5 N で 0.7 mm めり込み、手首のばねと直列になって力が 6 % 小さく出た —— 実測)。摩擦の錐は角錐(pyramidal)。
楕円の錐 + impratio = 10 では、硬い手首(20 kN/m)で 0.1〜0.36 mm めり込んで力が 17 % 小さく出た(摩擦 0 でも同じ、実測)。
**Raises** ValueError: 数の検査。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_polish_wipe_measure](../../../../examples/poc_polish_wipe_measure.py) — `py -3.11 examples/poc_polish_wipe_measure.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`polish`)

[preston_pressure_kernel](preston_pressure_kernel.md) · [preston_removal_map](preston_removal_map.md) · [preston_track_profile](preston_track_profile.md) · [wipe_band_width](wipe_band_width.md) · [raster_wipe_area](raster_wipe_area.md) · [coat_image](coat_image.md) · [coat_thickness_from_image](coat_thickness_from_image.md) · [wipe_coverage](wipe_coverage.md)

---
*Provenance: polish.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
