---
op: lidar_spec
dim: drive
category: lidar
in: 
out: table
examples: [poc_driving_school]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# lidar_spec — DRIVE `lidar` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.lidar_spec(n_beams: 'int' = 32, v_fov_deg=(-25.0, 15.0), azimuth_res_deg: 'float' = 0.2, range_max: 'float' = 60.0, range_min: 'float' = 0.5, noise_std: 'float' = 0.0) -> 'dict'` (実装を直接呼ぶなら `import lidarsim; lidarsim.lidar_spec(n_beams: 'int' = 32, v_fov_deg=(-25.0, 15.0), azimuth_res_deg: 'float' = 0.2, range_max: 'float' = 60.0, range_min: 'float' = 0.5, noise_std: 'float' = 0.0) -> 'dict'`、台帳から引くなら `opsdrive.get("lidar_spec")`)

## 使い方

回転式 LiDAR の仕様 dict を作る(既定は 32 beam・仰角 −25…+15°・方位 0.2° = 1800 列)。

- ``n_beams``: レーザ層の数(≥ 1)。仰角帯 ``v_fov_deg=(v_min, v_max)`` [度] を等分し、行 0 が
  上端 ``v_max`` 側(:mod:`spherical_proj` と同じ)。``v_min < v_max``、いずれも [−90, 90] の中。
- ``azimuth_res_deg``: 方位角の刻み [度] (> 0)。360° を割り切る値でなければ ``ValueError``
  (等間隔の 1 周が前提。0.2 → 1800 列、0.1 → 3600 列)。
- ``range_min`` / ``range_max`` [m]: 測距範囲(``0 ≤ range_min < range_max < ∞``)。外の最近接は無返答。
- ``noise_std`` [m]: range 方向のガウスノイズの標準偏差(≥ 0、0 = 完全決定的)。

返り値の dict: ``n_beams, n_az, v_fov_deg, azimuth_res_deg, range_min, range_max, noise_std,
elevations (n_beams,) [rad, 行 0 = 上端], azimuths (n_az,) [rad, 列 0 = −π 側の中心]``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lidar`)

[lidar_scan](lidar_scan.md) · [ray_plane_range](ray_plane_range.md) · [ray_box_ranges](ray_box_ranges.md)

---
*Provenance: lidarsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
