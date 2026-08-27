# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 動いた物体の 3-D シーンフローを剛体運動 + 密フィールドに分解 (scene_flow3d).

現実の問題(平たく言うと): デプスカメラや LiDAR が「同じ物体の 2 時刻の点群」を撮った。
物体はフレーム間で少し動いた(回って・ずれた)。知りたいのは 3 つ:
  (1) 物体は全体としてどう動いたか(1 個の剛体運動 R, t)。
  (2) 各点は 3-D 空間でどこへ動いたか(密な変位フィールド = シーンフロー)。
  (3) 剛体運動で説明しきれない「変形」は残っているか(残差)。

手法(3 つの op を鎖でつなぐ):
  frame0 の点群を **既知の剛体変換 (R_gt, t_gt)** で動かして frame1 を作る(GT を握る)。
    -> rigid_flow  : frame0 -> frame1 の単一剛体運動 (R, t) を ICP 風に復元。
    -> residual_flow: 復元した (R, t) を差し引いた残差フロー。真に剛体なら ~0 に潰れる。
    -> smooth_flow : 最近傍フローを近傍平均で正則化した密な変位フィールド。

真値チェック(GT / beat-the-null): frame1 を既知の (R_gt, t_gt) から作るので、
  * 回転誤差 = 復元 R と真の R の測地角。目標 < 1 度。
  * 並進誤差 = 復元 t と真の t の差(ボクセル=格子間隔 1.0 単位で測る)。目標 < 1 voxel。
  * smooth_flow の EPE(End-Point Error, 各点の推定変位と真変位の平均距離)< 許容。
  * residual は剛体部で ~0(格子間隔に対して極小)。
  beat-the-null: 「動いていない」と仮定した **ゼロフロー**の EPE は変位の大きさそのもの。
  真の手法がこの null を明確に下回ることを assert する(ただ小さいのではなく null に勝つ)。

限界(honest): 最近傍対応は変位が局所点間隔より十分小さい前提で正しい。本例は
運動を格子間隔より小さく設計してあるので対応は正しく張れる。大変位ではこの前提が
崩れ、smooth_flow の EPE は悪化しうる(scene_flow3d のモジュール docstring 参照)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# examples_3d/ の 1 つ上(リポジトリ直下)に本体モジュールがある。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scene_flow3d import rigid_flow, residual_flow, smooth_flow  # noqa: E402


def rotation_matrix(axis, deg):
    """軸まわり deg 度の回転行列(ロドリゲスの公式)。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def rotation_error_deg(R_est, R_gt):
    """2 つの回転行列の間の測地距離(度)。相対回転の回転角 = 誤差。"""
    R_est = np.asarray(R_est)
    cos = (np.trace(R_est.T @ R_gt) - 1) / 2
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def box_lattice():
    """非対称な直方体格子の点群(格子間隔 1.0)。

    x:0..9, y:0..5, z:0..3 の整数格子 = 10x6x4 = 240 点。3 辺の長さが違う
    (9x5x3)ので回転が一意に決まる(立方体だと回転対称で姿勢が定まらない)。
    格子間隔 1.0 を 1 ボクセルの物理単位として並進誤差を測る。
    """
    xs, ys, zs = np.arange(10.0), np.arange(6.0), np.arange(4.0)
    gx, gy, gz = np.meshgrid(xs, ys, zs, indexing="ij")
    return np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)


def main():
    # --- 1) 合成データ: frame0 を既知の剛体運動で動かして frame1 を作る ---
    voxel = 1.0                                        # 格子間隔 = 1 ボクセル
    frame0 = box_lattice()                             # 時刻 0 の物体点群 (240, 3)
    # 運動は格子間隔より小さく設計(最近傍対応が正しく張れる前提を満たすため)。
    R_gt = rotation_matrix([0.2, 1.0, 0.3], 2.0)       # 真の回転 = 2 度
    t_gt = np.array([0.20, -0.15, 0.10])               # 真の並進(すべて < 1 voxel)
    frame1 = frame0 @ R_gt.T + t_gt                    # 時刻 1 の物体点群 = R*p + t

    # 各点の真の変位フィールド(GT シーンフロー)と、その大きさ = null の EPE。
    gt_flow = frame1 - frame0                          # (240, 3) 真変位
    null_epe = float(np.mean(np.linalg.norm(gt_flow, axis=1)))  # ゼロフロー時の EPE

    # --- 2) op を鎖でつなぐ: rigid_flow -> residual_flow -> smooth_flow ---
    rigid = rigid_flow(frame0, frame1)                 # {"R","t","rmse"} を復元
    R_est, t_est, rmse = rigid["R"], rigid["t"], rigid["rmse"]

    # 復元した剛体を差し引いた残差。真に剛体なら ~0 に潰れる。
    resid = residual_flow(frame0, frame1, R_est, t_est)  # (240, 3)
    resid_mag = float(np.mean(np.linalg.norm(resid, axis=1)))

    # 最近傍フローを近傍平均で正則化した密な変位フィールド。
    dense = smooth_flow(frame0, frame1, k=7, n_iter=5)   # (240, 3)
    smooth_epe = float(np.mean(np.linalg.norm(dense - gt_flow, axis=1)))

    # --- 3) 真値チェック(GT / beat-the-null) ---
    rerr = rotation_error_deg(R_est, R_gt)
    terr = float(np.linalg.norm(t_est - t_gt))
    trans_mag = float(np.linalg.norm(t_gt))            # null(無運動)の並進誤差

    print(f"点数                       : {frame0.shape[0]}  (格子間隔 = {voxel:.1f} voxel)")
    print(f"真の運動                   : 回転 2.00 度, 並進 |t|={trans_mag:.3f} voxel")
    print(f"rigid_flow 回転誤差 (度)   : {rerr:.4f}   (null=無運動なら 2.000 度)")
    print(f"rigid_flow 並進誤差 (voxel): {terr:.5f}   (null=無運動なら {trans_mag:.3f})")
    print(f"rigid_flow 整合 rmse       : {rmse:.5f}")
    print(f"residual 平均大きさ (voxel): {resid_mag:.5f}   (剛体なら ~0)")
    print(f"smooth_flow EPE (voxel)    : {smooth_epe:.5f}")
    print(f"null(ゼロフロー) EPE       : {null_epe:.5f}   (= 変位の大きさそのもの)")

    # rigid_flow: 回転 < 1 度、並進 < 1 voxel。かつ null(無運動)を明確に下回る。
    assert rerr < 1.0, f"回転誤差が大きすぎる: {rerr:.4f} 度"
    assert terr < 1.0 * voxel, f"並進誤差が大きすぎる: {terr:.5f} voxel"
    assert rerr < 0.1 * 2.0, f"回転が null(2 度)を明確に下回らない: {rerr:.4f}"
    assert terr < 0.1 * trans_mag, f"並進が null({trans_mag:.3f})を明確に下回らない: {terr:.5f}"

    # residual: 剛体部は ~0。null(=変位の大きさ)を桁で下回る。
    assert resid_mag < 0.05 * null_epe, \
        f"残差が剛体で潰れていない: {resid_mag:.5f} vs null {null_epe:.5f}"

    # smooth_flow: EPE が許容内、かつ beat-the-null(ゼロフローの半分未満)。
    assert smooth_epe < 0.5 * null_epe, \
        f"smooth_flow が null を下回らない: EPE {smooth_epe:.5f} vs null {null_epe:.5f}"
    assert smooth_epe < 0.1 * voxel, f"smooth_flow EPE が許容超過: {smooth_epe:.5f} voxel"

    print(
        f"PASS: rigid_flow 回転誤差 {rerr:.3f} 度 (<1)・並進誤差 {terr:.4f} voxel (<1), "
        f"residual {resid_mag:.4f}~0, smooth_flow EPE {smooth_epe:.4f} < null {null_epe:.4f} "
        f"(beat-the-null)"
    )


if __name__ == "__main__":
    main()
