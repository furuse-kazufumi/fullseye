---
op: scatter_offroad
dim: drive
category: terrain
in: table
out: points
examples: [poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# scatter_offroad — DRIVE `terrain` op

- **データ種**: `table` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.scatter_offroad(course, bounds, n: 'int' = 60, r_min: 'float' = 4.0, margin: 'float' = 3.0, seed: 'int' = 0, max_tries: 'int' = 20000) -> 'np.ndarray'` (実装を直接呼ぶなら `import driveterrain; driveterrain.scatter_offroad(course, bounds, n: 'int' = 60, r_min: 'float' = 4.0, margin: 'float' = 3.0, seed: 'int' = 0, max_tries: 'int' = 20000) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("scatter_offroad")`)

## 使い方

道の外に物を撒く(dart throwing): 各点はコースから ``margin`` 以上、互いに ``r_min`` 以上離れる。

返り値 (n', 3) = (x, y, yaw)。``max_tries`` で n に届かなければあるだけ返す(n' ≤ n)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`points` を入力に取れる)

[course_contains](../course/course_contains.md) · [ray_plane_range](../lidar/ray_plane_range.md) · [ray_box_ranges](../lidar/ray_box_ranges.md) · [course_distance](course_distance.md) · [mesh_signed_volume](mesh_signed_volume.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`terrain`)

[perlin2](perlin2.md) · [fbm_params](fbm_params.md) · [fbm_height](fbm_height.md) · [fbm_gradient](fbm_gradient.md) · [radial_periodogram](radial_periodogram.md) · [spectral_slope](spectral_slope.md) · [course_distance](course_distance.md) · [terrain_params](terrain_params.md)

---
*Provenance: driveterrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
