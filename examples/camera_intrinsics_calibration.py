# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""camera_intrinsics_calibration — 傾けた平面ターゲットの多視点から内部行列 K を推定(Zhang 法)。

    py -3.11 examples/camera_intrinsics_calibration.py

【この例が示すこと】
平面の格子(z=0)を自分で決めた K と各姿勢で投影し、その画素対応だけから K を Zhang 法で
推定し返す。板を視点間で傾けると K を厳密に回収でき、傾けない(正面平行ばかり)と退化して
fail-closed で止まることを示す。回収した K は estimate_distortion / undistort_image に渡せる。

EXTEND: 実写ではチェッカーボードの角点を視点ごとに (row, col) 画素で拾い image_points_list に
渡す(角点検出は fs.apply(img, "hx_find_caltab") / caltab.find_marks_and_pose)。object_points は
実測したミリ間隔の (x, y) 平面座標。歪みのあるレンズでは K だけでなく歪みも要る —— 直線群から
fs.estimate_distortion で係数を測り、点を undistort してから K を推定すると系統誤差が減る。
★再投影誤差が小さくても K が正しいとは限らない(poc_camera_calibration がその罠を扱う)。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402


def _project_plane(obj_xy, K, rvec, t):
    """平面点 (x,y,0) を K・姿勢(回転ベクトル rvec, 併進 t)で投影し (row, col) 画素で返す。"""
    R = fs.rodrigues(rvec)
    Rt = np.column_stack([R[:, 0], R[:, 1], t])          # z=0 平面なので R の 2 列 + t
    hom = np.column_stack([obj_xy, np.ones(len(obj_xy))])
    x = (K @ Rt @ hom.T).T
    uv = x[:, :2] / x[:, 2:3]                             # (x=col, y=row)
    return uv[:, ::-1]                                    # -> (row, col)


def main() -> int:
    K_true = fs.intrinsic_matrix(600.0, 600.0, 320.0, 240.0)
    gx, gy = np.meshgrid(np.arange(7), np.arange(6))
    obj = np.column_stack([gx.ravel().astype(float), gy.ravel().astype(float)])

    rng = np.random.default_rng(0)
    tilted = [_project_plane(obj, K_true, rng.uniform(-0.4, 0.4, 3),
                             [rng.uniform(-1, 1), rng.uniform(-1, 1), 8.0]) for _ in range(6)]
    res = fs.camera_calibration(obj, tilted)
    print("推定 K: fx=%.2f fy=%.2f cx=%.2f cy=%.2f (真 600 600 320 240)"
          % (res["fx"], res["fy"], res["cx"], res["cy"]))
    print("orientation_rank_ratio=%.3e  (大きいほど視点が K を拘束)" % res["orientation_rank_ratio"])
    for key, tru in [("fx", 600.0), ("fy", 600.0), ("cx", 320.0), ("cy", 240.0)]:
        assert abs(res[key] - tru) < 1.0

    # 板を傾けない(正面平行ばかり)と退化して fail-closed で止まる。
    flat = [_project_plane(obj, K_true, [0.0, 0.0, rng.uniform(-0.02, 0.02)],
                           [rng.uniform(-1, 1), rng.uniform(-1, 1), 8.0]) for _ in range(6)]
    try:
        fs.camera_calibration(obj, flat)
        print("退化検出: 鳴らなかった(想定外)")
        return 1
    except ValueError as e:
        print("退化検出(正面平行): fail-closed OK —", str(e)[:48], "...")

    # 視点が 3 未満も拒否。
    try:
        fs.camera_calibration(obj, tilted[:2])
        return 1
    except ValueError:
        print("視点 3 未満: fail-closed OK")

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
