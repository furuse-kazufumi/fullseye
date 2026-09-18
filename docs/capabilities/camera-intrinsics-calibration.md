---
id: camera-intrinsics-calibration
title: 平面ターゲットの多視点から内部行列 K を推定する(Zhang 法)
title_en: Estimate the camera intrinsic matrix K from multiple planar views (Zhang)
category: 測る
ops: [camera_calibration, estimate_distortion, intrinsic_matrix, decompose_intrinsics]
examples: [camera_intrinsics_calibration]
version: 0.2.1
---

# 平面ターゲットの多視点から内部行列 K を推定する(Zhang 法)

## できること

チェッカーボードのような平面ターゲットを角度を変えて何枚か撮り、その角点の対応だけからカメラの内部行列 `K`(焦点距離 fx,fy・主点 cx,cy・skew)を推定します。`camera_calibration(object_points, image_points_list)` は Zhang 法(平面ホモグラフィから内部拘束を 2 本ずつ集めて解く)で `K` を返します。回収した `K` は歪み係数の推定(能力ノート `estimate-lens-distortion`)や `undistort_image`、PnP・三角測量にそのまま渡せます。`object_points` は平面上の `(x, y)` 座標、`image_points_list` は各視点の `(row, col)` 画素対応です。

大事なのは**この方法が保証しないこと**です。板を視点間で**傾けないと** `K` は定まりません(正面平行ばかりだと零空間が広がって退化する)。返り値の `orientation_rank_ratio` が視点の向きがどれだけ `K` を拘束しているか(大きいほど良い)を示します。そして**再投影誤差は配置の良し悪しを映しません** —— 焦点距離と板までの距離は画像上でほぼ同じ効果なので、両方を同じ割合で間違えても画素は動かない(この罠は PoC `poc_camera_calibration` が数値で詳しく扱います)。fail-closed: 視点が 3 未満、対応点数が合わない、退化配置、`K` が非有限/非正のときは `ValueError`(NaN を返さない)。

## What it does

`camera_calibration(object_points, image_points_list)` estimates the intrinsic matrix `K` (fx, fy, cx, cy, skew) from several views of a planar target seen at different tilts, by Zhang's method (two constraints per view collected from the plane homographies). `object_points` are `(x, y)` on the plane; `image_points_list` are the `(row, col)` correspondences per view. It returns `K` plus the per-view homographies, per-view reprojection RMS, and `orientation_rank_ratio` — how strongly the view orientations constrain `K`. The recovered `K` feeds `estimate_distortion`, `undistort_image`, PnP and triangulation. Two honest caveats it carries: the plane must be **tilted** between views or the intrinsics are unconstrained (a degeneracy the code detects and refuses), and **reprojection error does not reveal a bad view geometry** — focal length and target distance trade off almost invisibly in the image (the `poc_camera_calibration` example quantifies this). fail-closed on fewer than three views, mismatched point counts, degenerate orientation, or a non-finite / non-positive `K`.

## 向くところ / 向かないところ

**向く**: チェッカーボード等の平面ターゲットからの内部校正、PnP や三角測量・undistort の前段として `K` を用意する、校正セッションの配置(板の傾き)の良し悪しを `orientation_rank_ratio` で診断する。

**向かない**: ★**歪み係数は推定しません**(`K` のみ。放射・接線歪みは `estimate_distortion` で直線群から別途測る。歪みのあるレンズでは、点を undistort してから `K` を推定すると系統誤差が減る)。★**1〜2 視点や正面平行ばかりでは解けません**(退化。板を傾けて 3 枚以上)。★非平面ターゲット(3-D の校正体)はこの平面前提の外。★再投影誤差だけを合否基準にしないこと(小さくても `K` が正しいとは限らない)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

# 平面格子の (x, y)(ミリ等の実単位)と、各視点で撮った角点 (row, col)。
gx, gy = np.meshgrid(np.arange(7), np.arange(6))
obj = np.column_stack([gx.ravel().astype(float), gy.ravel().astype(float)])
views = [pts_view0, pts_view1, pts_view2, pts_view3]     # 各 (N, 2) の (row, col)、板を傾けて 3 枚以上
res = fs.camera_calibration(obj, views)
K = fs.intrinsic_matrix(res["fx"], res["fy"], res["cx"], res["cy"], res["skew"])
print(res["orientation_rank_ratio"])                     # 小さいなら板をもっと傾ける
```

## 裏づけ

- 実装: `calib.py`(`camera_calibration`。平面ホモグラフィ DLT → Zhang の内部拘束を SVD で解く。退化検出つき)
- 例: [`camera_intrinsics_calibration`](../../examples/camera_intrinsics_calibration.py)(傾けた多視点で K を厳密回収 / 正面平行は退化して fail-closed / 視点 3 未満も拒否)
- 試験: `tests/test_camera.py`(facade 経由で K 回収 / 退化・視点不足の fail-closed)、`tests/test_calib.py`(退化検出の切り分け)
- 来歴: Zhang, Z. (2000), *A flexible new technique for camera calibration*, IEEE TPAMI 22(11)—— `docs/REFERENCES.md`
