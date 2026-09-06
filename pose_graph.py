# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
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
    """T_i⁻¹ ∘ T_j = i←j の相対姿勢。pose_* = [rvec|t] (6,)。→ (rvec_ij (3,), t_ij (3,))。

    姿勢の規約は world←body(``p_world = R p_body + t``)。``T_i⁻¹ = (R_iᵀ, -R_iᵀ t_i)`` と ``T_j`` を
    合成して ``R_ij = R_iᵀ R_j``、``t_ij = R_iᵀ (t_j - t_i)`` を求め、回転は回転ベクトル(軸 × 角
    [rad]、scipy の ``as_rotvec``)に戻して返す。これは「フレーム i から見たフレーム j の姿勢」で、
    ``optimize_pose_graph`` に渡すエッジ ``(i, j, rvec_ij, t_ij)`` の計測値をこの規約で作ればそのまま
    整合する(GT 姿勢からの合成エッジ生成にも使う)。

    - ``pose_i`` / ``pose_j``: 長さ 6 の ``[rvec(3) | t(3)]``。形状検証はしない(``pose[:3]`` /
      ``pose[3:]`` でスライスするだけ)。
    - 単位は並進が座標の単位、回転が rad。返る ``rvec_ij`` の角度は [0, π] に折り畳まれる。
    """
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
    """エッジ残差の RMS(姿勢グラフの整合度)。→ scalar。

    各エッジ ``(i, j, rvec_meas, t_meas[, w_rot, w_trans])`` について、予測相対姿勢 ``T_i⁻¹ ∘ T_j`` と
    計測 ``(rvec_meas, t_meas)`` の食い違い ``measured⁻¹ ∘ predicted`` を回転ベクトル 3 成分 + 並進
    3 成分の 6 次元残差にし(それぞれ ``sqrt(w_rot)``、``sqrt(w_trans)`` を掛ける。重み省略時は 1)、
    全エッジ・全成分をまとめた 2 乗平均平方根を返す。``optimize_pose_graph`` の返り値 ``rmse`` と
    同じ量で、最適化前後の比較に使う。

    - ``poses``: (N,6) にリシェイプできる ``[rvec | t]``(world←body)。
    - ``edges``: 上記タプルのリスト。空なら 0.0 を返す。

    注意: 回転成分(rad)と並進成分(座標の単位)を同じ配列で平均するため、値の次元は混在する。
    並進のスケールが大きいシーンでは並進項が支配的になるので、単位を揃えたいときは ``w_rot`` /
    ``w_trans`` で重み付けする。エッジ添字の範囲検証はこの関数では行わない(負の添字は numpy の
    折り返しで別ノードを黙って参照する。``optimize_pose_graph`` は検証する)。
    """
    r = pose_graph_residuals(poses, edges)
    return float(np.sqrt(np.mean(r ** 2))) if len(r) else 0.0


def optimize_pose_graph(poses_init, edges, fix_first=True, max_iter=200):
    """相対姿勢制約 + ループ閉じから大域姿勢を最適化。→ dict{poses, rmse, cost}。

    poses_init (N,6)=[rvec|t] の初期推定(ドリフトあり)、edges の相対姿勢制約を満たすよう最適化。
    fix_first=True で先頭ノードを固定し gauge を除く。

    - ``edges``: ``(i, j, rvec_ij, t_ij[, w_rot, w_trans])`` のリスト。``(rvec_ij, t_ij)`` は「i から
      見た j」= ``T_i⁻¹ ∘ T_j`` の計測値(``relative_pose`` と同じ規約)。オドメトリ (i, i+1) と
      ループ閉じ(離れた i, j)を同じ形で混ぜてよい。重みは残差に ``sqrt(w)`` を掛ける(省略時 1)。
    - 各エッジの残差は ``measured⁻¹ ∘ predicted`` を回転ベクトル + 並進の 6 次元にしたもので、
      ``scipy.optimize.least_squares(method="lm")`` で最小化する(``max_nfev = max_iter × パラメータ数``)。
    - 返り値: ``poses`` (N,6)(``fix_first`` なら先頭は初期値のまま)、``rmse`` =
      ``mean_edge_error(poses, edges)``、``cost`` = 最終コスト(残差 2 乗和の 1/2)。

    fail-closed: ノード数 < 2、エッジ 0 本、エッジの添字が ``[0, N)`` を外れる(負の添字の黙った
    折り返しも拒否)場合は ``ValueError``。``fix_first=False`` にすると gauge が残り解は一意でない
    (LM は初期値近くの 1 つを返す)。回転は rad、並進は座標の単位で、両者を同じ残差ベクトルに
    並べるため単位が大きく違うときは重みで揃える。3D 点も観測画素も使わない(それらを含めて
    最適化するのは ``bundle_adjust``)。
    """
    poses_init = np.asarray(poses_init, float).reshape(-1, 6)
    n = len(poses_init)
    if n < 2:
        raise ValueError("pose graph requires at least 2 nodes")
    if len(edges) == 0:
        raise ValueError("edges (relative pose constraints) are empty")
    for e in edges:                                  # fail-closed: エッジ index を検証(負の silent wrap/範囲外を拒否)
        ei, ej = int(e[0]), int(e[1])
        if not (0 <= ei < n and 0 <= ej < n):
            raise ValueError(f"edge node index out of range [0,{n}): ({e[0]},{e[1]})")
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
