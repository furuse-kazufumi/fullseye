# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 動いた物体の 3-D シーンフローを剛体運動 + 密フィールドに分解 (scene_flow3d).

現実の問題(平たく言うと): デプスカメラや LiDAR が「同じ物体の 2 時刻の点群」を撮った。
物体はフレーム間で少し動いた(回って・ずれた)し、センサには測定ノイズが乗る。知りたいのは:
  (1) 物体は全体としてどう動いたか(1 個の剛体運動 R, t)。
  (2) 各点は 3-D 空間でどこへ動いたか(密な変位フィールド = シーンフロー)。
  (3) 剛体運動で説明しきれない「変形」は残っているか(残差)。

手法(3 つの op を鎖でつなぐ):
  frame0 の点群を **既知の剛体変換 (R_gt, t_gt)** で動かし、**seed 固定の測定ノイズ**を
  載せて frame1 を作る(GT を握りつつ、生の観測はノイズで濁す)。
    -> rigid_flow  : frame0 -> frame1 の単一剛体運動 (R, t) を ICP 風に復元(ノイズ平均化)。
    -> residual_flow: 復元した (R, t) を差し引いた残差フロー。剛体成分を除くと残るのは
                      測定ノイズの床(厳密 0 ではない)。
    -> smooth_flow : 最近傍フローを近傍平均で正則化した密な変位フィールド。生の最近傍
                      フローに乗ったノイズを均し、真の運動に近づける(= 平滑化の本来の仕事)。

なぜノイズを入れるか(honest / 退化回避): ノイズが無いと frame1 は frame0 の厳密な剛体像に
なり、生の最近傍フローがそのまま真値と一致して EPE=0 になる。すると rigid_flow は自明に厳密、
residual は自明に 0、smooth_flow の平滑化は「均す対象(ノイズ)」が無いので価値を発揮できず、
むしろ僅かに悪化する。ノイズを注入して初めて rmse>0・残差>0 の非自明な問題になり、
smooth_flow の denoising が本当に効いているかを検証できる。

真値チェック(GT / beat-the-null):
  * 回転誤差 = 復元 R と真の R の測地角。目標 < 1 度、かつ null(無運動=2 度)を桁で下回る。
  * 並進誤差 = 復元 t と真の t の差(ボクセル=格子間隔 1.0 単位)。目標 < 1 voxel、かつ null を下回る。
  * residual は剛体を除くと測定ノイズの床まで潰れ、null(変位の大きさ)を明確に下回る。
  * smooth_flow の EPE(真の運動に対する平均端点誤差)が、
    (a) null(ゼロフロー)を下回り(beat-the-null)、かつ
    (b) 平滑化前の生の最近傍フローより **有意に低い**(平滑化が価値を足していることの検証。
        生フローを返すだけの no-op ではこの assert を通せない)。

限界(honest): 最近傍対応は変位が局所点間隔より十分小さい前提で正しい。本例は運動を格子間隔より
小さく、ノイズも格子間隔の数 % に設計してあるので対応は正しく張れる。大変位・大ノイズでは前提が
崩れ、smooth_flow の EPE は悪化しうる(scene_flow3d のモジュール docstring 参照)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# examples_3d/ の 1 つ上(リポジトリ直下)に本体モジュールがある。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scene_flow3d import (  # noqa: E402
    nearest_neighbor_flow,
    residual_flow,
    rigid_flow,
    smooth_flow,
)


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
    # --- 1) 合成データ: frame0 を既知の剛体運動で動かし、測定ノイズを載せて frame1 を作る ---
    voxel = 1.0                                        # 格子間隔 = 1 ボクセル
    frame0 = box_lattice()                             # 時刻 0 の物体点群 (240, 3)
    # 運動は格子間隔より小さく設計(最近傍対応が正しく張れる前提を満たすため)。
    R_gt = rotation_matrix([0.2, 1.0, 0.3], 2.0)       # 真の回転 = 2 度
    t_gt = np.array([0.20, -0.15, 0.10])               # 真の並進(すべて < 1 voxel)
    frame1_clean = frame0 @ R_gt.T + t_gt              # ノイズなしの真の剛体像 = R*p + t

    # 測定ノイズ(センサの揺らぎ)を注入。seed 固定で再現可能。これが無いと生の最近傍
    # フローが厳密に真値と一致(EPE=0)し、rigid/residual/smooth のどれも試されない
    # (退化した簡単すぎる例)。詳細はモジュール docstring「なぜノイズを入れるか」を参照。
    noise_std = 0.03                                   # ~0.03 voxel(格子間隔の 3%)
    rng = np.random.default_rng(0)
    noise = rng.normal(0.0, noise_std, size=frame1_clean.shape)
    frame1 = frame1_clean + noise                      # 観測される(ノイズ込み)時刻 1 点群
    noise_floor = float(np.mean(np.linalg.norm(noise, axis=1)))  # 実測ノイズ平均大きさ

    # GT = 「真の運動」= ノイズなしの変位。EPE はこの真値に対して測る
    # (smooth_flow の仕事は観測ノイズを均して真の運動へ近づけること)。
    gt_flow = frame1_clean - frame0                    # (240, 3) 真変位(ノイズなし)
    null_epe = float(np.mean(np.linalg.norm(gt_flow, axis=1)))  # ゼロフロー時の EPE

    # --- 2) op を鎖でつなぐ: rigid_flow -> residual_flow -> (raw) -> smooth_flow ---
    rigid = rigid_flow(frame0, frame1)                 # {"R","t","rmse"} を復元
    R_est, t_est, rmse = rigid["R"], rigid["t"], rigid["rmse"]

    # 復元した剛体を差し引いた残差。剛体成分を除くと測定ノイズの床まで潰れる。
    resid = residual_flow(frame0, frame1, R_est, t_est)  # (240, 3)
    resid_mag = float(np.mean(np.linalg.norm(resid, axis=1)))

    # 生の最近傍フロー(平滑化なし)= smooth_flow が改善すべきベースライン。
    raw = nearest_neighbor_flow(frame0, frame1)          # (240, 3)
    raw_epe = float(np.mean(np.linalg.norm(raw - gt_flow, axis=1)))

    # 最近傍フローを近傍平均で正則化した密な変位フィールド(ノイズを均す)。
    dense = smooth_flow(frame0, frame1, k=7, n_iter=5)   # (240, 3)
    smooth_epe = float(np.mean(np.linalg.norm(dense - gt_flow, axis=1)))

    # --- 3) 真値チェック(GT / beat-the-null) ---
    rerr = rotation_error_deg(R_est, R_gt)
    terr = float(np.linalg.norm(t_est - t_gt))
    trans_mag = float(np.linalg.norm(t_gt))            # null(無運動)の並進誤差

    print(f"点数                       : {frame0.shape[0]}  (格子間隔 = {voxel:.1f} voxel)")
    print(f"真の運動                   : 回転 2.00 度, 並進 |t|={trans_mag:.3f} voxel")
    print(f"測定ノイズ std             : {noise_std:.3f} voxel  (ノイズ床 EPE={noise_floor:.5f})")
    print(f"rigid_flow 回転誤差 (度)   : {rerr:.4f}   (null=無運動なら 2.000 度)")
    print(f"rigid_flow 並進誤差 (voxel): {terr:.5f}   (null=無運動なら {trans_mag:.3f})")
    print(f"rigid_flow 整合 rmse       : {rmse:.5f}   (ノイズ由来で > 0)")
    print(f"residual 平均大きさ (voxel): {resid_mag:.5f}   (ノイズ床 {noise_floor:.5f} まで潰れる)")
    print(f"raw NN フロー EPE (voxel)  : {raw_epe:.5f}   (平滑化なしのベースライン)")
    print(f"smooth_flow EPE (voxel)    : {smooth_epe:.5f}   (raw 比 {100 * (1 - smooth_epe / raw_epe):.0f}% 改善)")
    print(f"null(ゼロフロー) EPE       : {null_epe:.5f}   (= 変位の大きさそのもの)")

    # rigid_flow: 回転 < 1 度、並進 < 1 voxel。かつ null(無運動)を桁で下回る。
    assert rerr < 1.0, f"回転誤差が大きすぎる: {rerr:.4f} 度"
    assert terr < 1.0 * voxel, f"並進誤差が大きすぎる: {terr:.5f} voxel"
    assert rerr < 0.1 * 2.0, f"回転が null(2 度)を明確に下回らない: {rerr:.4f}"
    assert terr < 0.1 * trans_mag, f"並進が null({trans_mag:.3f})を明確に下回らない: {terr:.5f}"

    # residual: 剛体を差し引くと残差は測定ノイズの床まで潰れる(厳密 0 ではない)。
    # ノイズ床の近傍にあり、かつ null(=変位の大きさ)を明確に下回ることを確認。
    assert resid_mag < 1.5 * noise_floor, \
        f"残差がノイズ床まで潰れていない: {resid_mag:.5f} vs floor {noise_floor:.5f}"
    assert resid_mag < 0.3 * null_epe, \
        f"残差が null を明確に下回らない: {resid_mag:.5f} vs null {null_epe:.5f}"

    # smooth_flow: (a) beat-the-null、(b) 生フローより有意に低い = 平滑化が価値を足す。
    # (b) が肝: 生フローをそのまま返す no-op なら smooth_epe == raw_epe で必ず落ちる。
    assert smooth_epe < 0.5 * null_epe, \
        f"smooth_flow が null を下回らない: EPE {smooth_epe:.5f} vs null {null_epe:.5f}"
    assert smooth_epe < 0.8 * raw_epe, \
        f"smooth_flow が生フローを有意に下回らない(平滑化が無価値): " \
        f"EPE {smooth_epe:.5f} vs raw {raw_epe:.5f}"

    print(
        f"PASS: rigid_flow 回転誤差 {rerr:.3f} 度 (<1)・並進誤差 {terr:.4f} voxel (<1), "
        f"residual {resid_mag:.4f} (ノイズ床 {noise_floor:.4f}) << null {null_epe:.4f}, "
        f"smooth_flow EPE {smooth_epe:.4f} < raw {raw_epe:.4f} < null {null_epe:.4f} "
        f"(denoise adds value, beat-the-null)"
    )


if __name__ == "__main__":
    main()
