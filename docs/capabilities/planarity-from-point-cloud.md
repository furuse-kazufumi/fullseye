---
id: planarity-from-point-cloud
title: 3-D 点群から平面度を出す
title_en: Flatness of a surface from a 3-D point cloud
category: 測る
ops: [ransac_plane, fit_plane_3d, distance_point_plane, statistical_outlier_removal]
examples: [geometry_metrology, poc_bump_coplanarity, poc_scan_to_bim_asbuilt]
version: 0.2.0
inputs: [points]
pipeline: [statistical_outlier_removal, ransac_plane, fit_plane_3d, distance_point_plane]
alternatives: [fit_plane3, plane_segmentation, radius_outlier_removal, estimate_normals, surface_form_error]
limits: 平面度 PV は雑音の最大値統計で、完全に平らな面でも雑音だけで許容の 70 % を使う(RMS なら 2.03 mm 対 PV 4.89 mm)。最小二乗は外れ点 10 % で真値の 11 倍外れ、RANSAC は 45 % まで持って 55 % で別の面へ乗り換える。合わせ(ICP)は反りを吸って偽のへこみを作る。
calibration: 点群の座標系の単位(m / mm)を揃える。センサの測距雑音 σ を先に測り、PV は σ√(2 ln N) の床と比べて読む。
---

# 3-D 点群から平面度を出す

## できること

定盤・フランジ・基板・床など「平らであるべき面」の点群から、外れ点を除き、頑健に平面を当てはめ、各点の面からの距離で**平面度**(PV・RMS)を出します。距離は符号つきなので、反り(低次)と局所の凹凸(高次)を分けて読めます。

## What it does

From the point cloud of a nominally flat surface: remove outliers, fit a plane robustly, and read flatness (peak-to-valley and RMS) from the signed point-to-plane distances — so warp (low order) and local relief (high order) can be told apart.

## 向くところ / 向かないところ

**向く**: 1 枚の平面が点群の大半を占める場面。センサの測距雑音が既知のとき。

**向かない**: ★点群に他の面が混ざり、その割合が半分に近いとき(RANSAC は 55 % で家具へ乗り換える —— `poc_asbuilt_wall_deviation`)。★PV を 1 個の数字で合否にする場面 —— 雑音の最大値統計そのもので、点を増やすほど大きくなる(`poc_scan_to_bim_asbuilt`: 平らな床で 4.89 mm)。★合わせ(ICP)を先に掛けた点群 —— 剛体モードが反りを吸い、無傷の天井が +0.89 mrad 傾いて見える。

## 推奨パイプライン

`statistical_outlier_removal` → `ransac_plane` → `fit_plane_3d` → `distance_point_plane`

`statistical_outlier_removal` で孤立点を落とし → `ransac_plane(points, thresh)` で外れ点に強い平面と inlier マスク(`.raw` で 3 つ組)を取り → inlier だけを `fit_plane_3d` で最小二乗に(通過点・法線・残差 rms)→ 各点の**符号つき**距離は `(points − c) · n` で(`distance_point_plane` は点 1 個の**符号なし**距離)→ PV = max − min、RMS。反りを分けるなら距離場に 2 次曲面を当てて引く(`poc_bump_coplanarity`)。

## 代替

3 点だけなら `fit_plane3`、複数の面に分けるなら `plane_segmentation`、密度で外れを落とすなら `radius_outlier_removal`、局所の傾きは `estimate_normals`。高さ格子(depth)で持っているなら `surface_form_error` が 1 個の数で返す。

## 限界

- 最小二乗は外れ点 10 % で真値の 11 倍(66.3 mrad)、RANSAC は 45 % まで持ち 55 % で乗り換える(`poc_asbuilt_wall_deviation`)。
- PV は雑音の最大値統計 σ√(2 ln N) の床を持ち、点数で増える。RMS を併記する。
- 高次の反り(4 次のロブ)は 3 次では 1 µm も取れない —— 次数は物理から決める(`poc_bump_coplanarity`)。
- 中央 8 µm の低次不良は残差から 88 % 消え、検出数は変わらないのに見逃しだけ増える —— 「検出できている」は健全さの証拠にならない。

## 実寸校正

点群は座標系の単位のまま(m か mm かを揃える)。画素校正は無い。センサの雑音 σ は**平らな的**で先に測り、PV の床 σ√(2 ln N) と比べて読む。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

rng = np.random.default_rng(0)
xy = rng.uniform(-50, 50, (4000, 2))
z = 0.002 * xy[:, 0] + rng.normal(0, 0.02, 4000)          # 傾いた面 + 雑音 20 µm
pts = np.column_stack([xy, z])
pts[:40, 2] += 5.0                                        # 外れ点 1 %
clean = fs.ledger.statistical_outlier_removal(pts)
plane, inlier, info = fs.ledger.ransac_plane.raw(clean, thresh=0.06)   # 3σ
c, n, resid = fs.ledger.fit_plane_3d(clean[inlier])                     # inlier で最小二乗
d = (clean[inlier] - c) @ n                                              # 符号つき距離
print("PV", float(d.max() - d.min()), "RMS", float(np.sqrt((d ** 2).mean())), "inlier", info["inlier_ratio"])
print("1 点の距離", fs.ledger.distance_point_plane(pts[0], c, n))       # 符号なし、点 1 個
```

## 裏づけ

- op: `ransac_plane` / `fit_plane_3d`(当てはめ)、`distance_point_plane`(距離)、`statistical_outlier_removal`(外れ)
- 例: [`geometry_metrology`](../../examples_3d/geometry_metrology.py)、[`poc_bump_coplanarity`](../../examples/poc_bump_coplanarity.py)、[`poc_scan_to_bim_asbuilt`](../../examples/poc_scan_to_bim_asbuilt.py)
