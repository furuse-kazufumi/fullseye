---
op: ray_box_ranges
dim: drive
category: lidar
in: points × points
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# ray_box_ranges — DRIVE `lidar` op

- **データ種**: `points × points` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.ray_box_ranges(origin, dirs, box) -> 'np.ndarray'` (実装を直接呼ぶなら `import lidarsim; lidarsim.ray_box_ranges(origin, dirs, box) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("ray_box_ranges")`)

## 使い方

原点 ``origin`` から方向 ``dirs (...,3)`` のレイが軸平行箱に入るまでの距離(slab 法)。

``box = (xmin, ymin, zmin, xmax, ymax, zmax)``。外れは ``inf``。原点が箱の内側なら前方で最初に
当たる面(出口)までの距離。距離は ``t·‖D‖``。``min < max`` でない箱は ``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`lidar`)

[lidar_spec](lidar_spec.md) · [lidar_scan](lidar_scan.md) · [ray_plane_range](ray_plane_range.md)

---
*Provenance: lidarsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
