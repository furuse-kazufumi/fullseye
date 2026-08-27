# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Generalized-ICP(plane-to-plane 共分散重み ICP)による剛体位置合わせ。

point-to-point ICP(``match3d.icp_point2point_3d``, Kabsch/SVD)は各対応を等方な
点距離で扱い、point-to-plane ICP(``match3d.icp_point2plane``)は *target 側* の
接平面へ点を落とす(残差を法線方向へ射影 = rank-1 重み ``n nᵀ``)。Generalized-ICP
(Segal, Haehnel, Thrun, RSS 2009)はこれを一般化し、**source と target の両方**に
局所共分散を割り当て、残差 ``d = R·s + t - q`` をマハラノビス重み
``W = (C_target + R·C_source·Rᵀ)⁻¹`` で測る。

「plane-to-plane」共分散は各点の局所共分散を固有分解し、固有値を
``(ε, 1, 1)`` に置換して作る(表面法線方向=最小固有値方向のみ ε の小分散、
接平面内の 2 方向は分散 1)。これにより点は「接平面に沿ってはどこにでも
居てよいが、法線方向にはよく決まっている」という面的モデルになり、
平面的/ノイズを含む点群で point-to-point より頑健・高精度に収束する
(法線推定への鋭敏さも point-to-plane より緩和される)。

本モジュールの固有価値(重複回避):
- ``match3d`` の ICP 2 種とは重み行列が別物(等方距離 / rank-1 法線射影 に対し、
  こちらは source・target 双方の **full 3×3 共分散** の合成マハラノビス重み)。
- ``pointcloud.estimate_normals``(PCA 法線)や ``ransac_fit``(プリミティブ適合)
  とは目的が異なり、こちらは 2 雲間の剛体変換 (R,t) を推定する登録手法。

線形化 Gauss-Newton(小角近似 ``R ≈ I + [ω]×``)で各反復の増分を解く。ICP は
ローカル最適化なので **近い初期化を前提**(粗マッチや妥当な ``init`` を与える)。

依存: numpy + scipy(cKDTree)のみ。cv2/skimage 不使用。
参考(公開): Segal, Haehnel & Thrun, "Generalized-ICP", RSS 2009。
"""
from __future__ import annotations

import numpy as np

__all__ = ["estimate_covariances", "gicp"]


# ═══════════════════════════════════════════════════════════════════════════
# 内部ヘルパ(numpy, device 非依存)
# ═══════════════════════════════════════════════════════════════════════════
def _skew_batch(v: np.ndarray) -> np.ndarray:
    """点集合 (N,3) → 歪対称行列 [v]× の束 (N,3,3)。cross(v,x) = [v]×·x。"""
    v = np.asarray(v, np.float64)
    N = v.shape[0]
    K = np.zeros((N, 3, 3), np.float64)
    K[:, 0, 1] = -v[:, 2]; K[:, 0, 2] = v[:, 1]
    K[:, 1, 0] = v[:, 2];  K[:, 1, 2] = -v[:, 0]
    K[:, 2, 0] = -v[:, 1]; K[:, 2, 1] = v[:, 0]
    return K


def _rodrigues(omega: np.ndarray) -> np.ndarray:
    """回転ベクトル ω → 回転行列 R = expm([ω]×)  (Rodrigues, 3×3)。"""
    omega = np.asarray(omega, np.float64).reshape(3)
    theta = float(np.linalg.norm(omega))
    eye = np.eye(3, dtype=np.float64)
    if theta < 1e-12:
        return eye
    k = omega / theta
    K = np.array([[0.0, -k[2], k[1]],
                  [k[2], 0.0, -k[0]],
                  [-k[1], k[0], 0.0]], np.float64)
    return eye + np.sin(theta) * K + (1.0 - np.cos(theta)) * (K @ K)


# ═══════════════════════════════════════════════════════════════════════════
# plane-to-plane 共分散
# ═══════════════════════════════════════════════════════════════════════════
def estimate_covariances(points, k: int = 20, epsilon: float = 1e-3) -> np.ndarray:
    """各点の局所共分散を固有値 (ε,1,1) に置換した plane-to-plane 共分散 (N,3,3)。

    k 近傍(自身を含む)の標本共分散を固有分解し、固有値を **接平面内は 1・
    表面法線方向(最小固有値方向)は ε** に置き換えて再構成する。共分散の
    大きさは近傍の広がりに依らず一定(ε,1,1)で、スケール不変な「面的な
    確からしさ」モデルになる(GICP の中核)。

    引数:
        points (N,3): 点群。
        k: 近傍数(自身を含む)。共分散推定は k≥4 程度が安定。
        epsilon: 法線方向に割り当てる小分散(0<ε<1)。小さいほど接平面へ
                 強く拘束する。スケール不変(次元なし比)。

    返り値:
        (N,3,3) 対称正定値共分散の束。各共分散の固有値は {ε,1,1}、ε に
        対応する固有ベクトルが局所表面法線方向。

    例外:
        ValueError: points が (N,3) でない / N<3(法線が定まらず縮退)/
                    epsilon が (0,1) 外(fail-closed)。
    """
    from scipy.spatial import cKDTree

    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points は (N,3) でなければならない")
    N = P.shape[0]
    if N < 3:
        raise ValueError("共分散推定には少なくとも 3 点が必要(N<3 は縮退)")
    if not (0.0 < float(epsilon) < 1.0):
        raise ValueError("epsilon は (0,1) の範囲でなければならない")

    kk = int(min(max(4, k), N))
    _, idx = cKDTree(P).query(P, k=kk)
    if kk == 1:                                    # 退避(実際上 kk>=4)
        idx = idx.reshape(N, 1)
    nb = P[idx]                                     # (N,k,3)
    mu = nb.mean(axis=1, keepdims=True)             # (N,1,3)
    dev = nb - mu                                    # (N,k,3)
    C = np.einsum("nki,nkj->nij", dev, dev) / kk    # (N,3,3) 標本共分散

    # 固有分解(対称 → eigh, 固有値昇順)。V[:,0]=最小固有値=法線方向。
    w, V = np.linalg.eigh(C)                         # w:(N,3) 昇順, V:(N,3,3)
    L = np.zeros((N, 3, 3), np.float64)
    L[:, 0, 0] = float(epsilon)                     # 最小固有値方向(法線)← ε
    L[:, 1, 1] = 1.0                                # 接平面方向 ← 1
    L[:, 2, 2] = 1.0
    # Cov = V L Vᵀ
    cov = np.einsum("nij,njk,nlk->nil", V, L, V)    # (N,3,3)
    # 数値対称化
    cov = 0.5 * (cov + np.transpose(cov, (0, 2, 1)))
    return cov


# ═══════════════════════════════════════════════════════════════════════════
# Generalized-ICP
# ═══════════════════════════════════════════════════════════════════════════
def gicp(source, target, max_iter: int = 30, k: int = 20, epsilon: float = 1e-3,
         tol: float = 1e-8, init=None) -> dict:
    """Generalized-ICP(共分散重みマハラノビス ICP)で剛体変換 (R,t) を推定する。

    各反復で source→target の最近傍対応を張り、残差 ``d_i = R·s_i + t - q_i`` を
    重み ``W_i = (C_target[q_i] + R·C_source[s_i]·Rᵀ)⁻¹`` で測るマハラノビス
    コスト ``Σ d_iᵀ W_i d_i`` を、小角線形化 ``R ← (I+[ω]×)R`` の Gauss-Newton で
    最小化する。各対応のヤコビアン ``J_i = [-[R·s_i+t]× | I]``(3×6)から
    正規方程式 ``(Σ J_iᵀ W_i J_i) x = -(Σ J_iᵀ W_i d_i)``(6×6)を解いて増分
    ``x=[ω|τ]`` を得、Rodrigues で回転に戻して累積する。

    共分散は plane-to-plane(``estimate_covariances``)。point-to-plane が target の
    法線方向へ残差を射影する(rank-1)のに対し、GICP は source・target 双方の
    full 3×3 共分散を合成した重みを使うため、平面的・ノイズを含む点群で頑健。

    ICP はローカル最適化なので **近い初期化を前提**(粗マッチや ``init`` を渡す)。

    引数:
        source (N,3): 動かす側の点群。
        target (M,3): 参照側(固定)の点群。
        max_iter: 最大反復数。
        k: 共分散推定の近傍数。
        epsilon: plane-to-plane の法線方向小分散(0<ε<1)。
        tol: 収束閾値。増分並進 ‖τ‖ が ``tol×(target のRMS半径)`` 未満かつ
             増分回転 ‖ω‖(rad)が ``tol`` 未満で打ち切り(スケール相対)。
        init: (R0(3,3), t0(3,)) の初期姿勢タプル、または None(単位)。

    返り値:
        dict:
          "R" (3,3) ndarray  — target ≈ R·source + t を満たす回転。
          "t" (3,) ndarray   — 並進。
          "rmse" float       — 最終対応上のユークリッド RMSE(採用点)。
          "iterations" int   — 実反復数。

    例外:
        ValueError: 入力形状不正 / 点数不足 / 数値発散(非有限)= fail-closed。
    """
    from scipy.spatial import cKDTree

    S = np.asarray(source, np.float64)
    Q = np.asarray(target, np.float64)
    if S.ndim != 2 or S.shape[1] != 3:
        raise ValueError("source は (N,3) でなければならない")
    if Q.ndim != 2 or Q.shape[1] != 3:
        raise ValueError("target は (M,3) でなければならない")
    if S.shape[0] < 3 or Q.shape[0] < 3:
        raise ValueError("source/target とも 3 点以上が必要(縮退)")

    # 初期姿勢
    if init is None:
        R = np.eye(3, dtype=np.float64)
        t = np.zeros(3, dtype=np.float64)
    else:
        R = np.asarray(init[0], np.float64).reshape(3, 3).copy()
        t = np.asarray(init[1], np.float64).reshape(3).copy()

    # スケール相対な収束判定のための特徴長(target の RMS 半径)
    q_center = Q.mean(axis=0)
    scale = float(np.sqrt(np.mean(np.sum((Q - q_center) ** 2, axis=1))))
    scale = max(scale, 1e-12)

    # 共分散は各フレームで一度だけ推定(source は source 系、target は target 系)
    cov_s = estimate_covariances(S, k=k, epsilon=epsilon)   # (N,3,3)
    cov_t = estimate_covariances(Q, k=k, epsilon=epsilon)   # (M,3,3)
    tree = cKDTree(Q)

    n_iter = 0
    rmse = float("inf")
    for it in range(int(max_iter)):
        n_iter = it + 1
        p = S @ R.T + t                                     # 変換後 source (N,3)
        _, idx = tree.query(p, k=1)                         # 最近傍対応
        d = p - Q[idx]                                       # 残差 (N,3)

        # 重み W_i = (C_t[q] + R C_s Rᵀ)⁻¹
        RCsRT = np.einsum("ab,nbc,dc->nad", R, cov_s, R)    # (N,3,3)
        Mcov = cov_t[idx] + RCsRT                            # (N,3,3) 対称正定値
        W = np.linalg.inv(Mcov)                             # (N,3,3)
        W = 0.5 * (W + np.transpose(W, (0, 2, 1)))          # 数値対称化

        # ヤコビアン J_i = [-[p_i]× | I]  (N,3,6)
        J = np.zeros((p.shape[0], 3, 6), np.float64)
        J[:, :, 0:3] = -_skew_batch(p)
        J[:, 0, 3] = 1.0; J[:, 1, 4] = 1.0; J[:, 2, 5] = 1.0

        Jt = np.transpose(J, (0, 2, 1))                     # (N,6,3)
        JtW = np.einsum("nij,njk->nik", Jt, W)              # (N,6,3)
        H = np.einsum("nik,nkl->nil", JtW, J).sum(axis=0)   # (6,6)
        g = -np.einsum("nik,nk->ni", JtW, d).sum(axis=0)    # (6,)

        # スケール相対な微小正則化(縮退=平面などで H が特異になっても解ける)。
        # 未拘束 DOF(平面内の滑り/法線回り回転)には ~0 の更新を返し発散を防ぐ。
        # Marquardt 対角スケーリング: 減衰を各パラメータの H 対角に比例させる。単一スカラ×I だと
        # 回転ブロック(∝座標スケール²)と並進ブロック(∝スケール⁰)の単位差で、スケールが 1 から大きく
        # 離れると小さい方が過減衰され剛体復元が静かに失敗する(極端スケール bug)。対角比例なら各方向が
        # 自分の単位で減衰=スケール不変。null 方向(縮退)は最大対角の相対 floor で最小限だけ正則化。
        dH = np.diag(H).copy()
        floor = 1e-12 * (float(dH.max()) + 1e-30)
        Hr = H + 1e-9 * np.diag(np.maximum(dH, floor))
        try:
            x = np.linalg.solve(Hr, g)
        except np.linalg.LinAlgError:
            x, *_ = np.linalg.lstsq(Hr, g, rcond=None)
        if not np.all(np.isfinite(x)):
            raise ValueError("GICP 数値発散(非有限な更新)= fail-closed")

        omega = x[0:3]
        tau = x[3:6]
        R_inc = _rodrigues(omega)
        R = R_inc @ R
        t = R_inc @ t + tau

        # 収束判定(スケール相対): 並進はスケールで正規化、回転は rad で絶対。
        if float(np.linalg.norm(tau)) < tol * scale and float(np.linalg.norm(omega)) < tol:
            break

    # 最終 RMSE(採用対応上のユークリッド距離)
    p = S @ R.T + t
    _, idx = tree.query(p, k=1)
    d = p - Q[idx]
    rmse = float(np.sqrt(np.mean(np.sum(d ** 2, axis=1))))
    if not (np.all(np.isfinite(R)) and np.all(np.isfinite(t)) and np.isfinite(rmse)):
        raise ValueError("GICP 数値発散(非有限な結果)= fail-closed")

    return {"R": R, "t": t, "rmse": rmse, "iterations": n_iter}
