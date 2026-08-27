"""事例: 平面ばかりの部屋コーナーを撮った2枚のスキャンを位置合わせ (registration).

掃除ロボや3Dスキャナが部屋の隅(床 + 直交する2枚の壁 = コーナー)を、少しだけ
視点を変えて2回撮る場面を考える。2枚を1つに貼り合わせる(=自己位置を求める)には、
「1枚目から2枚目へどれだけ回転・並進したか」を正確に当てる必要がある。

この場面が難しいのは、写っているのがほぼ平らな面だけだからだ。平らな面どうしは
面に沿って「すべって」しまう — 少し横にずらしても点と点はまた近くで合ってしまうので、
点の距離だけを最小化する素朴な point-to-point ICP は、面に沿った偽の解に引き込まれて
ずれる。GICP(Generalized-ICP, plane-to-plane)は各点に「面に沿う向きはゆるく・
面を貫く向きはきつい」共分散(estimate_covariances)を割り当て、面に垂直な隙間だけを
詰めて面内のすべりは無視する。これで平面主体の場面でも頑健・高精度に姿勢を復元する。

method:
  1) estimate_covariances でソース点群の plane-to-plane 共分散を作る
     (固有値は {ε,1,1} = 法線方向だけ小分散。gicp が内部で使う重みの正体)。
  2) gicp(source, target) でマハラノビス重み ICP を回し、剛体変換 (R,t) を推定。
  3) 素の点対点 ICP (match3d.icp_point2point_3d) と「何もしない(恒等変換)」を
     ベースライン(null)として並べ、GICP がそれらを明確に上回ることを確認。

GT(ground truth): 2枚目は、1枚目のコーナーとは *独立にサンプルし直した* 点群を、
既知の小さな回転 R_gt(6度)・並進 t_gt で動かし、微小なセンサノイズを足して作る。
独立サンプルなので点どうしの真の対応は存在せず(=面上のどこか)、これが素朴 ICP を
すべらせる原因そのもの。真値 (R_gt, t_gt) が分かっているので回転誤差(度)・並進誤差
(点間隔 voxel 単位)を厳密に測れる。target: 回転 < 1度、並進 < 1 voxel。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from gicp import estimate_covariances, gicp
import match3d


def rotation_matrix(axis, deg):
    """軸まわり deg 度の回転行列 (ロドリゲスの公式)。"""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def rotation_error_deg(R_est, R_gt):
    """2つの回転行列の間の測地距離(度)。相対回転の回転角 = 誤差。"""
    R_est = np.asarray(R_est)
    cos = (np.trace(R_est.T @ R_gt) - 1) / 2
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def corner_scan(n_per_plane, extent, seed):
    """部屋コーナー(床 z=0 + 壁 x=0 + 壁 y=0)の表面から点を一様サンプル。

    3枚の直交平面は姿勢を一意に拘束する(球のような対称縮退はない)。seed を
    変えると *独立に* サンプルし直すので、2枚のスキャン間に点どうしの真の対応は
    生まれない(実センサで2回撮ると別々の点が当たるのと同じ)。この独立性が、
    素の点対点 ICP を面に沿ってすべらせる「平面すべり」の原因になる。
    """
    rng = np.random.default_rng(seed)
    a = rng.random((n_per_plane, 2)) * extent
    floor = np.c_[a[:, 0], a[:, 1], np.zeros(n_per_plane)]          # 床 z=0
    b = rng.random((n_per_plane, 2)) * extent
    wall_x = np.c_[np.zeros(n_per_plane), b[:, 0], b[:, 1]]         # 壁 x=0
    c = rng.random((n_per_plane, 2)) * extent
    wall_y = np.c_[c[:, 0], np.zeros(n_per_plane), c[:, 1]]         # 壁 y=0
    return np.vstack([floor, wall_x, wall_y])


def main():
    # --- 1) 合成データ: 平面主体のコーナーを2回スキャン(既知の姿勢差 + ノイズ) ---
    extent = 1.0
    n_per_plane = 300                       # 3面 × 300 = 900 点
    voxel = extent / np.sqrt(n_per_plane)   # 点間隔(平均最近傍距離)~ センサ分解能

    src = corner_scan(n_per_plane, extent, seed=0)   # 1枚目のスキャン(基準)

    applied_deg = 6.0                                 # 既知の小さな回転(真値)
    R_gt = rotation_matrix([0.2, 1.0, 0.3], applied_deg)
    t_gt = np.array([0.6, -0.4, 0.3]) * voxel         # 既知の小さな並進(真値)

    noise = 0.25 * voxel                              # 微小センサノイズ(点間隔の1/4)
    rng = np.random.default_rng(7)
    # 2枚目 = 独立サンプルのコーナーを真の姿勢で動かし、ノイズを重畳
    tgt = corner_scan(n_per_plane, extent, seed=1) @ R_gt.T + t_gt
    tgt = tgt + rng.normal(0.0, noise, tgt.shape)

    # --- 2) chain: まず plane-to-plane 共分散を作る(gicp が内部で使う重みの正体)---
    cov = estimate_covariances(src, k=20, epsilon=1e-3)
    eig = np.linalg.eigvalsh(cov)                      # (N,3) 昇順固有値
    # 設計上、各共分散の固有値は {ε,1,1}(法線方向だけ ε の小分散)。これを確認して
    # 「面に沿う向きはゆるく・貫く向きはきつい」重みになっていることを裏取りする。
    normal_var_err = float(np.abs(eig[:, 0] - 1e-3).max())
    plane_var_err = float(np.abs(eig[:, 1:] - 1.0).max())

    # --- 3) 登録: GICP(共分散重み)で恒等姿勢から (R,t) を推定 ---
    result = gicp(src, tgt, max_iter=60, k=20, epsilon=1e-3)
    R_gicp, t_gicp = result["R"], result["t"]
    gicp_rot = rotation_error_deg(R_gicp, R_gt)
    gicp_trans = float(np.linalg.norm(t_gicp - t_gt) / voxel)

    # --- 4) beat-the-null: (a)素の点対点ICP (b)何もしない(恒等) を並べる ---
    R_p2p, t_p2p, _ = match3d.icp_point2point_3d(src, tgt, iters=60)
    R_p2p = np.asarray(R_p2p.cpu().numpy() if hasattr(R_p2p, "cpu") else R_p2p)
    t_p2p = np.asarray(t_p2p.cpu().numpy() if hasattr(t_p2p, "cpu") else t_p2p)
    p2p_rot = rotation_error_deg(R_p2p, R_gt)
    p2p_trans = float(np.linalg.norm(t_p2p - t_gt) / voxel)

    identity_rot = rotation_error_deg(np.eye(3), R_gt)          # null: 何もしない誤差
    identity_trans = float(np.linalg.norm(t_gt) / voxel)

    # --- 5) GT検証と表示 ---
    print(f"点間隔 voxel(平均最近傍)   : {voxel:.4f}")
    print(f"注入した姿勢差 (真値)        : 回転 {applied_deg:.1f}度, 並進 {identity_trans:.3f} voxel")
    print(f"注入ノイズ (標準偏差)        : {noise:.4f}  (voxel の 1/4)")
    print(f"共分散の固有値ずれ           : 法線方向 {normal_var_err:.2e}, 接平面方向 {plane_var_err:.2e}  (~0 なら plane-to-plane 成立)")
    print(f"GICP 反復数                  : {result['iterations']}")
    print("--- 姿勢復元の誤差(小さいほど良い)---")
    print(f"GICP                         : 回転 {gicp_rot:.4f}度,  並進 {gicp_trans:.4f} voxel")
    print(f"素の点対点ICP (null)         : 回転 {p2p_rot:.4f}度,  並進 {p2p_trans:.4f} voxel")
    print(f"恒等変換=何もしない (null)   : 回転 {identity_rot:.4f}度,  並進 {identity_trans:.4f} voxel")

    # 共分散が設計どおり {ε,1,1} であること(chain の裏取り)
    assert normal_var_err < 1e-9 and plane_var_err < 1e-9, \
        f"plane-to-plane 共分散が {{ε,1,1}} になっていない: 法線 {normal_var_err:.2e}, 接平面 {plane_var_err:.2e}"

    # target: 回転 < 1度、並進 < 1 voxel を GICP が満たす
    assert gicp_rot < 1.0, f"GICP 回転誤差が大きすぎる: {gicp_rot:.4f} 度"
    assert gicp_trans < 1.0, f"GICP 並進誤差が大きすぎる: {gicp_trans:.4f} voxel"

    # beat-the-null (1): 何もしない(恒等)を明確に上回る
    assert gicp_rot < identity_rot, \
        f"GICP が恒等変換を上回れていない: {gicp_rot:.4f} vs {identity_rot:.4f} 度"

    # beat-the-null (2): 平面すべりに弱い素の点対点ICP を明確に(2倍以上の精度で)上回る
    assert gicp_rot < 0.5 * p2p_rot, \
        f"GICP が点対点ICP を回転で明確に上回れていない: {gicp_rot:.4f} vs {p2p_rot:.4f} 度"
    assert gicp_trans < 0.5 * p2p_trans, \
        f"GICP が点対点ICP を並進で明確に上回れていない: {gicp_trans:.4f} vs {p2p_trans:.4f} voxel"

    print(
        f"PASS: GICP 回転 {gicp_rot:.3f}度 < 1度・並進 {gicp_trans:.3f} voxel < 1、"
        f"平面すべりに弱い点対点ICP(回転 {p2p_rot:.3f}度)を約 {p2p_rot / gicp_rot:.1f}倍の精度で上回った"
    )


if __name__ == "__main__":
    main()
