---
op: project_spherical
dim: 3d
category: lidar_projection
in: points
out: image2d
examples: [lidar_projection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# project_spherical — 3D `lidar_projection` op

- **データ種**: `points` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.project_spherical(points, h_res: 'int' = 1024, v_res: 'int' = 64, v_fov=(-25.0, 15.0)) -> 'np.ndarray'` (実装を直接呼ぶなら `import spherical_proj; spherical_proj.project_spherical(points, h_res: 'int' = 1024, v_res: 'int' = 64, v_fov=(-25.0, 15.0)) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("project_spherical")`)

## 使い方

回転式 LiDAR の球面レンジ画像へ投影 (v_res, h_res)。空セル=0, 近い点優先(最小 range)。

各点を方位角(列)× 仰角(行)ビンへ落とし、センサ原点からの range(slant distance)を書く。
v_fov=(v_min,v_max)[度] の仰角帯の外側、原点上(r=0)、非有限座標の点は落とす(honest drop)。
空/全 drop の場合は全ゼロ画像を返す(=何も見えていない、honest)。

- ``points``: (N,3)、センサ原点基準で x=前, y=左, z=上。非 (N,3) は ``ValueError``。
- ``h_res`` / ``v_res``: 列数(方位角 360° の等分)・行数(仰角帯の等分)。正でなければ ``ValueError``。
- ``v_fov``: (v_min, v_max) [度]。``v_min < v_max`` でなければ ``ValueError``。

列は ``floor((atan2(y,x) + π) / 2π · h_res)`` で、列 0 が真後ろ(-x)、``h_res//2`` が正面(+x)、
反時計回りに増える。行は ``(v_res-1) - floor((θ - v_min)/(v_max - v_min) · v_res)``(θ は仰角
[度])で、行 0 が帯の上端(θ=v_max)。画素値は slant range ``sqrt(x²+y²+z²)``(座標の単位)。
同じセルに複数点が落ちたら ``np.minimum.at`` で最小 range を残す(奥の点は失われる)。
逆変換は ``unproject_spherical``(同じ ``v_fov`` を渡す)。高さで層を切る変種が
``project_cylindrical``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lidar_projection](../../../../examples_3d/lidar_projection.py) — `py -3.11 examples_3d/lidar_projection.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`lidar_projection`)

[unproject_spherical](unproject_spherical.md) · [project_cylindrical](project_cylindrical.md)

---
*Provenance: spherical_proj.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
