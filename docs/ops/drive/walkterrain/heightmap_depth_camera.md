---
op: heightmap_depth_camera
dim: drive
category: walkterrain
in: depth × pose × matrix
out: depth
gpu: なし
examples: [heightmap_depth_camera_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.2.0  # fullseye lib version this note was generated for
---

# heightmap_depth_camera — DRIVE `walkterrain` op

- **データ種**: `depth × pose × matrix` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.heightmap_depth_camera(heights, pose, K, cell: 'float' = 0.05, origin=(0.0, 0.0), *, width=None, height=None, step=None, near: 'float' = 0.1, max_range: 'float' = 10.0, disparity_sigma: 'float' = 0.0, baseline: 'float' = 0.05, seed: 'int' = 0)` (実装を直接呼ぶなら `import terrain; terrain.heightmap_depth_camera(heights, pose, K, cell: 'float' = 0.05, origin=(0.0, 0.0), *, width=None, height=None, step=None, near: 'float' = 0.1, max_range: 'float' = 10.0, disparity_sigma: 'float' = 0.0, baseline: 'float' = 0.05, seed: 'int' = 0)`、台帳から引くなら `opsdrive.get("heightmap_depth_camera")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

高さ図(標高図・DEM)を、ピンホールの深度カメラで直接撮る(光線を一定の刻みで高さの上に進める)。

画素ごとに光線を ``step`` 刻みで進め、光線が高さの面の下へ入った刻みで、前の刻みとの間を一次で補間して
交点を取り、**光軸方向の深度 z**(:func:`camera.depth_to_points` が受ける量)を返す。高さはセルの中心の値の
双一次補間(:func:`terrain.elevation_map` と同じ並び: ``heights[i, j]`` はセルの中心
(``origin[0]`` + (j + ½)·cell, ``origin[1]`` + (i + ½)·cell))。セルの中心が張る範囲の外と、``nan`` の
セル(観測していない)に触れる所には面が無い。

* **カメラの向きの決まりは 1 つ**: :mod:`camera` と同じ OpenCV の軸(x 右・y 下・z 前)。``pose`` は
  world→camera の ``(R, t)``(X_cam = R·X_world + t、:func:`camera.project_points` と同じ)か 4×4。画素の
  中心は整数の座標(``u = c``, ``v = r``)。返した深度を :func:`camera.depth_to_points` に渡し、
  ``Rᵀ (X_cam − t)`` で世界へ戻せば元の面の上に乗る(往復)。render3d / world_camera の OpenGL の軸
  (y 上・−z 前)とは ``(x, y, z)_here = (x, −y, −z)_render3d``。
* **刻み**: ``step`` は既定 cell/2、cell より大きい値は断る。刻みより短い弦で光線が横切る細い突起
  (1 セル幅の壁を浅い角度でかすめる所など)は飛び越しうる。交点の補間の誤差は刻みの 2 乗で縮む(平面では 0)。
* **雑音**: ステレオ・構造化光の誤差の伝播と同じ形 ``σ_z = z²·σ_d / (f·b)``(``acceptance_scan`` の
  ``triangulation`` と同じ則。f = K[0, 0] [px]、``baseline`` b [m]、``disparity_sigma`` σ_d [px])。
  既定 σ_d = 0(雑音なし = 厳密)。``seed`` で決定的。
* 当たらない画素・面の下から始まる光線・深度が [``near``, ``max_range``] の外の画素は ``nan``(両端は含み、
  範囲は雑音を足す前の深度で判定する)。最初の標本 ``near`` が面上なら深度 ``near`` の当たりにする。
  面の下から始まる光線(カメラが地面の中)と、地図の外から面の高さより下で入ってくる光線(地図の側面)も
  ``nan``(側面は面ではない)。

Parameters
----------
heights : (ny, nx) array
    高さ図 [m] (``nan`` = 観測していない穴、Inf は ValueError)。
pose : (R, t) or (4, 4)
    world→camera。4×4 は ndarray でも入れ子の list でもよい(最後の行は (0, 0, 0, 1))。
K : (3, 3)
    内部行列(``camera.intrinsic_matrix``)。形は ``[[fx, s, cx], [0, fy, cy], [0, 0, 1]]``。
cell, origin
    セルの大きさと、格子の左下の角 (xmin, ymin)(``elevation_map`` の extent の (xmin, ymin))。
width, height : int or None
    画像の大きさ(整数の画素。10.7 のような値は断る)。None なら主点から (2·cx + 1, 2·cy + 1)(整数でなければ断る)。

Returns
-------
depth : (height, width) float64
    光軸方向の深度 [m]、当たらない所は ``nan``。

**Raises** ``ValueError``: 形・値の誤り(高さに Inf、pose が回転でない、K が pinhole の形でない、step > cell、
near ≥ max_range、画像が 4e6 画素を超える 等)。

空の入力(``heights`` が 0 要素)は ValueError で拒否する。

English: renders a height map / DEM directly with a pinhole depth camera by marching each pixel ray at a
fixed step over the bilinear height surface and refining the crossing linearly; returns depth along the
optical axis (OpenCV axes, world->camera pose as in camera.project_points), NaN where nothing is hit.
Optional stereo noise sigma_z = z^2 sigma_d / (f b). The inverse of depth_to_points -> elevation_map.

呼び出し例::

    import numpy as np
    import terrain
    R = np.array([[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]])   # 真下を向く(z 前 = 世界の −z)
    C = np.array([1.0, 1.0, 2.0])                                         # 高さ 2 m のカメラ
    K = np.array([[100.0, 0.0, 31.5], [0.0, 100.0, 23.5], [0.0, 0.0, 1.0]])
    d = terrain.heightmap_depth_camera(np.zeros((40, 40)), (R, -R @ C), K)  # 2 m 四方の平らな床
    assert d.shape == (48, 64) and np.allclose(d, 2.0)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [heightmap_depth_camera_tour](../../../../examples/heightmap_depth_camera_tour.py) — `py -3.11 examples/heightmap_depth_camera_tour.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`walkterrain`)

[elevation_map](elevation_map.md) · [fill_gaps](fill_gaps.md) · [elevation_traversability](elevation_traversability.md) · [foothold_score](foothold_score.md) · [ground_surface](ground_surface.md) · [ground_plane](ground_plane.md) · [detect_obstacles](detect_obstacles.md) · [fuse_elevation](fuse_elevation.md)

---
*Provenance: terrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
