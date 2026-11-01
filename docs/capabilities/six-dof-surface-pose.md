---
id: six-dof-surface-pose
title: 既知の 3-D 部品を点群から 6 自由度で見つける
title_en: Locate a known 3-D part in a point cloud with six degrees of freedom
category: 見つける
ops: [depth_to_points, estimate_normals, fit_plane_ransac, euclidean_clusters, ppf_model, surface_match, icp_point2point_3d]
examples: [poc_registration_basin, poc_real_tless_6dof]
version: 0.8.1
inputs: [depth, points]
pipeline: [depth_to_points, estimate_normals, ransac_plane, icp_point2point_3d]
alternatives: [find_surface_pose, point_to_plane_icp, fpfh, register_cross]
limits: T-LESS の実機 subset では AR_MSSD 0.290。理想深度 0.880 から 0.590 落ち、Drost-CVPR10-3D-Only の公式 0.478、Vidal-Sensors18 の 0.575 に負ける。接触物体の cluster 結合、遮蔽、深度欠損、対称形状を別々に数える。
calibration: 深度とモデルの長さ単位を揃え、K と depth_scale を撮影フレームの値で読む。対称性を models_info.json から採点へ入れ、回転角だけで合否を決めない。
---

# 既知の 3-D 部品を点群から 6 自由度で見つける

## できること

既知の CAD・再構成モデルを実機の深度点群へ当て、モデル座標からカメラ座標への回転 R と並進 t を返します。深度を逆射影し、法線をカメラ向きに揃え、作業台を RANSAC で除き、物体 cluster ごとに Point Pair Features で大域探索して ICP で詰めます。

## What it does

Matches a known CAD or reconstructed model to a measured depth cloud and returns the rotation R and translation t from model coordinates to camera coordinates. The running pipeline back-projects depth, orients normals toward the camera, removes the table with RANSAC, votes with Point Pair Features per cluster, and refines with ICP.

## 向くところ / 向かないところ

**向く**: 形状が既知で、実寸の深度とカメラ内部行列があり、対象を空間的に分けられる場面。

**向かない**: 接触物体を距離 cluster だけで分ける場面、見える面が半分未満の場面、深度に返りが無い鏡面・黒色面。対称部品は生の回転角が大きくても同じ姿勢なので、MSSD/MSPD の対称性集合なしでは採点できません。

## 推奨パイプライン

`depth_to_points` → `estimate_normals` → `fit_plane_ransac` → `euclidean_clusters` → `ppf_model` → `surface_match` → `icp_point2point_3d`

モデルを再利用するなら `ppf_model` は対象ごとに 1 度だけ作り、各 cluster に `surface_match` を掛けます。1 回だけなら `find_surface_pose` が同じ 2 段をまとめます。

成熟度台帳が追跡する型付きの核は `depth_to_points` → `estimate_normals` → `ransac_plane` → `icp_point2point_3d` です。

## 代替

モデルを1回だけ当てるなら `find_surface_pose`、良い初期姿勢が既にあるなら `icp_point2point_3d` または `point_to_plane_icp`、局所特徴から対応を作るなら `fpfh` と `register_cross` を使います。PPF は初期姿勢なしの大域投票が必要な場面向けです。

## 限界

T-LESS の固定 10 instance subset では AR_MSSD / AR_MSPD が 0.290 / 0.320。理想 z-buffer 深度は 0.880 / 0.880 なので、合成だけでは 0.590 / 0.560 の低下が見えません。ICP を外すと 0.280 / 0.250、法線をカメラ向きに揃えないと 0.200 / 0.230 です。これは公式全 test と同じ標本ではないため、Drost/Vidal の leaderboard 値とは順位の参考として併記し、同条件の直接対決とは呼びません。

## 実寸校正

BOP の `depth_mm = depth_uint16 * depth_scale`、`cam_K`、モデルの mm を揃えます。MSSD は物体径 d に対する 0.05d..0.50d、MSPD は 5..50 px の recall を平均します。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

rng = np.random.default_rng(0)
directions = rng.normal(size=(80, 3))
directions /= np.linalg.norm(directions, axis=1, keepdims=True)
axes = np.array([40.0, 28.0, 20.0])
model_points = directions * axes
model_normals = model_points / axes**2
model_normals /= np.linalg.norm(model_normals, axis=1, keepdims=True)
points = model_points + np.array([10.0, -5.0, 600.0])
normals = model_normals.copy()
model = fs.ppf_model(model_points, model_normals, angle_bins=24)
pose = fs.surface_match(model, points, normals, ref_fraction=0.3, topk=6, seed=0)
print(pose["R"], pose["t"], pose["rmse"], pose["inlier_fraction"])
```

## 裏づけ

- 合成: [`poc_registration_basin`](../../examples/poc_registration_basin.py)
- 公開実測: [`poc_real_tless_6dof`](../../examples/poc_real_tless_6dof.py) — BOP T-LESS, CC BY 4.0
- 出典: Hodaň et al., T-LESS, WACV 2017, DOI 10.1109/WACV.2017.8。Hodaň et al., BOP Challenge 2020, DOI 10.1007/978-3-030-68223-0_12。
