"""pose_graph — 姿勢グラフ最適化(SLAM back-end: 相対姿勢制約 + ループ閉じ → 大域姿勢)。

bundle3d が「カメラ姿勢 + 3D 点」を再投影で最適化するのに対し、pose_graph は **3D 点を持たず
相対姿勢制約(オドメトリ + ループ閉じ)だけ**から大域姿勢を最適化する = SLAM の back-end。
各ノード姿勢を回転ベクトル rvec(3) + 並進 t(3) の 6 パラメータで表し、各エッジの相対姿勢誤差
(measured⁻¹ ∘ predicted)を tangent 空間(rvec + t)で残差にして Levenberg-Marquardt で最小化。
gauge は先頭ノードを固定して除く。ループ閉じ制約が累積ドリフトを一括補正する。

規約: 姿勢 T_i は world←body_i(p_world = R_i p_i + t_i)。相対 T_ij = T_i⁻¹ ∘ T_j(= i←j)。
GT 検証 = ループ状の合成姿勢 + オドメトリ/ループ閉じ制約 → ドリフト初期から真姿勢へ回復(残差~0)。

用途: LiDAR/visual SLAM の姿勢グラフ、マルチセンサ較正、軌跡最適化(Physical AI の空間認識 back-end)。
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def rvec_to_R(rvec):
    """回転ベクトル(3,) → 回転行列(3,3)。"""
    return Rotation.from_rotvec(np.asarray(rvec, float)).as_matrix()


def R_to_rvec(R):
    """回転行列(3,3) → 回転ベクトル(3,)。"""
    return Rotation.from_matrix(np.asarray(R, float)).as_rotvec()


def _invert(R, t):
    """姿勢 (R,t) の逆。→ (R.T, -R.T t)。"""
    Rt = R.T
    return Rt, -Rt @ t


def _compose(Ra, ta, Rb, tb):
    """姿勢合成 (Ra,ta) ∘ (Rb,tb)。→ (Ra Rb, Ra tb + ta)。"""
    return Ra @ Rb, Ra @ tb + ta


def relative_pose(pose_i, pose_j):
    """T_i⁻¹ ∘ T_j = i←j の相対姿勢。pose_* = [rvec|t] (6,)。→ (rvec_ij (3,), t_ij (3,))。"""
    Ri, ti = rvec_to_R(pose_i[:3]), np.asarray(pose_i[3:], float)
    Rj, tj = rvec_to_R(pose_j[:3]), np.asarray(pose_j[3:], float)
    Rii, tii = _invert(Ri, ti)
    Rij, tij = _compose(Rii, tii, Rj, tj)
    return R_to_rvec(Rij), tij


def _edge_residual(pose_i, pose_j, rvec_meas, t_meas, w_rot, w_trans):
    """1 エッジの残差(6,): measured⁻¹ ∘ predicted を tangent(rvec+t)で。"""
    Ri, ti = rvec_to_R(pose_i[:3]), np.asarray(pose_i[3:], float)
    Rj, tj = rvec_to_R(pose_j[:3]), np.asarray(pose_j[3:], float)
    Rii, tii = _invert(Ri, ti)
    Rij, tij = _compose(Rii, tii, Rj, tj)             # predicted i←j
    Rm, tm = rvec_to_R(rvec_meas), np.asarray(t_meas, float)
    Rmi, tmi = _invert(Rm, tm)
    Rerr, terr = _compose(Rmi, tmi, Rij, tij)         # measured⁻¹ ∘ predicted
    return np.concatenate([R_to_rvec(Rerr) * np.sqrt(w_rot), terr * np.sqrt(w_trans)])


def pose_graph_residuals(poses, edges):
    """全エッジの残差を連結(6*E,)。poses (N,6)=[rvec|t]、edges=[(i,j,rvec_meas,t_meas,[w_rot,w_trans]),...]。"""
    poses = np.asarray(poses, float).reshape(-1, 6)
    res = []
    for e in edges:
        i, j, rvec_meas, t_meas = e[0], e[1], e[2], e[3]
        w_rot = e[4] if len(e) > 4 else 1.0
        w_trans = e[5] if len(e) > 5 else 1.0
        res.append(_edge_residual(poses[i], poses[j], rvec_meas, t_meas, w_rot, w_trans))
    return np.concatenate(res) if res else np.zeros(0)


def mean_edge_error(poses, edges):
    """エッジ残差の RMS(姿勢グラフの整合度)。→ scalar。"""
    r = pose_graph_residuals(poses, edges)
    return float(np.sqrt(np.mean(r ** 2))) if len(r) else 0.0


def optimize_pose_graph(poses_init, edges, fix_first=True, max_iter=200):
    """相対姿勢制約 + ループ閉じから大域姿勢を最適化。→ dict{poses, rmse, cost}。

    poses_init (N,6)=[rvec|t] の初期推定(ドリフトあり)、edges の相対姿勢制約を満たすよう最適化。
    fix_first=True で先頭ノードを固定し gauge を除く。
    """
    poses_init = np.asarray(poses_init, float).reshape(-1, 6)
    n = len(poses_init)
    if n < 2:
        raise ValueError("姿勢グラフは 2 ノード以上必要")
    if len(edges) == 0:
        raise ValueError("エッジ(相対姿勢制約)が空")
    for e in edges:                                  # fail-closed: エッジ index を検証(負の silent wrap/範囲外を拒否)
        ei, ej = int(e[0]), int(e[1])
        if not (0 <= ei < n and 0 <= ej < n):
            raise ValueError(f"エッジのノード index が範囲外 [0,{n}): ({e[0]},{e[1]})")
    pose0 = poses_init[0].copy()

    def unpack(p):
        if fix_first:
            return np.vstack([pose0[None, :], p.reshape(n - 1, 6)])
        return p.reshape(n, 6)

    def fun(p):
        return pose_graph_residuals(unpack(p), edges)

    p0 = poses_init[1:].ravel() if fix_first else poses_init.ravel()
    sol = least_squares(fun, p0, method="lm", max_nfev=max_iter * max(len(p0), 1))
    poses = unpack(sol.x)
    return {"poses": poses, "rmse": mean_edge_error(poses, edges), "cost": float(sol.cost)}
