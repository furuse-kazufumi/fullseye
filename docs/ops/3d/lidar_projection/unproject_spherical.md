---
op: unproject_spherical
dim: 3d
category: lidar_projection
in: image2d
out: points
examples: [lidar_projection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# unproject_spherical — 3D `lidar_projection` op

- **データ種**: `image2d` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.unproject_spherical(range_img, v_fov=(-25.0, 15.0)) -> 'np.ndarray'` (実装を直接呼ぶなら `import spherical_proj; spherical_proj.unproject_spherical(range_img, v_fov=(-25.0, 15.0)) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("unproject_spherical")`)

## 使い方

球面レンジ画像 → 3D 点 (M, 3)。range>0 のセルのみをビン中心角で逆投影。

:func:`project_spherical` の逆。行/列からビン**中心**の (elevation, azimuth) を復元し、
格納 range を slant distance として球面 → 直交座標へ戻す。空(全 0)なら (0, 3) を返す。

- ``range_img``: (v_res, h_res) の 2-D 配列(非 2-D・サイズ 0 は ``ValueError``)。``range > 0`` の
  セルだけを点にする(0 = 空セル、負値も無視)。
- ``v_fov``: 投影時と同じ (v_min, v_max) [度]。違う値を渡すと仰角がずれた点群になる(整合性は
  検査できない)。

列 c → 方位角 ``az = (c + 0.5) / h_res · 2π - π``、行 r → 仰角 ``el = v_min + ((v_res-1-r) + 0.5)
/ v_res · (v_max - v_min)``(度 → rad)とし、``x = r cos(el) cos(az)``、``y = r cos(el) sin(az)``、
``z = r sin(el)``。点の並びは ``np.nonzero`` の行優先順(行 0 から)。ビン中心へ戻すので元の点とは
最大でおよそ「半セル角 × range」ずれ、投影で捨てられた(同セルの奥・FOV 外の)点は戻らない。
往復すると点数は一般に減る。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lidar_projection](../../../../examples_3d/lidar_projection.py) — `py -3.11 examples_3d/lidar_projection.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`lidar_projection`)

[project_spherical](project_spherical.md) · [project_cylindrical](project_cylindrical.md)

---
*Provenance: spherical_proj.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
