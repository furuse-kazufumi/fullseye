---
id: camera-calibration
title: 画素を実寸に結びつける(カメラ校正)
title_en: Tie pixels to real-world units (camera calibration)
category: 測る
ops: [camera_calibration, find_marks_and_pose, create_caltab, find_caltab, image_points_to_world_plane, hand_eye_calibration]
examples: [poc_camera_calibration, lens_calibration_loop_demo]
version: 0.2.1
---

# 画素を実寸に結びつける(カメラ校正)

## できること

校正板を撮った複数枚の画像から、カメラの内部パラメータ(焦点距離 `fx`/`fy`、主点 `cx`/`cy`)と、板の 6 自由度の姿勢を求めます。求まった値を使うと、画像上の点や輪郭を**ワールド平面(z=0)の実寸**へ写せます。ロボットの手先とカメラの関係(ハンドアイ)も、運動の対から `AX = XB` として解けます。

## What it does

Recover a camera's intrinsics (`fx`, `fy`, `cx`, `cy`) and the 6-DoF pose of a planar target from several views of a calibration plate, using Zhang's method. With those in hand, image points and XLD contours map to real-world units on the z=0 plane. Hand-eye calibration (`AX = XB`, Tsai-Lenz) solves the rigid transform between a robot flange and the camera from pairs of motions.

## 向くところ / 向かないところ

**向く**: 平面の校正板を**傾きを変えて 3 枚以上**撮れる状況。板の格子間隔を実測できる場合(印刷や貼り付けの伸びが 0.3 % あれば焦点距離も 0.3 % ずれます)。平面上に置いた対象の寸法を mm で読みたい場合。

**向かない**: ★**歪みのあるレンズの最終的な K を求める用途**。`camera_calibration` は閉形式で、レンズ歪みを推定しません —— `k1 = -0.18` のレンズでは傾き 5 度で `fx` を 41 % 誤ります(初期値としては使えます)。★また**再投影誤差が小さいことは、校正が正しい証拠になりません**: 板の傾きを 32 度から 2 度に変えても再投影 RMS は 1.00 倍のままで、`fx` の誤差だけが 281 倍になります(`poc_camera_calibration` の実測)。配置の良し悪しは `orientation_rank_ratio` で見てください。平面 1 枚では `fx`/`fy` の比を検証できません(Zhang 2000)。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

K = {"fx": 500.0, "fy": 500.0, "cx": 128.0, "cy": 128.0}
board = fs.ledger.create_caltab(7, 7, 10.0)           # 7x7 の板、10 mm ピッチ

pose = np.eye(4)
pose[:3, :3] = np.array([[1, 0, 0], [0, 0.98, -0.2], [0, 0.2, 0.98]])
pose[:3, 3] = [0.0, 0.0, 600.0]

sim = fs.ledger.sim_caltab(board, K, pose, 256)        # 板の見え方を合成
found = fs.ledger.find_marks_and_pose(sim["image"], K, board)

print(found["n_marks"])          # 49
print(found["reproj_rms"])       # 0.1 px 未満
print(found["pose"][:3, 3])      # ≈ [0, 0, 600] —— 板までの距離 [mm]
```

## 裏づけ

- op: `camera_calibration`(Zhang 法の内部行列)、`find_marks_and_pose`(板の 6-DoF 姿勢)、`create_caltab` / `find_caltab`(校正板の生成と検出)、`image_points_to_world_plane`(画素 → mm)、`hand_eye_calibration`(AX=XB)
- 例: [`poc_camera_calibration`](../../examples/poc_camera_calibration.py)(「再投影誤差 0.05 px は何も保証しない」を章立てで実測)、[`lens_calibration_loop_demo`](../../examples/lens_calibration_loop_demo.py)
- 使い方ガイド: [`camera_calibration`](../ops/calib/guides/camera_calibration.md)
- 台帳に載せなかった実装とその理由: [`MATURITY_INTERNAL.md`](../MATURITY_INTERNAL.md)
