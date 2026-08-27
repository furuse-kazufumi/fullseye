"""pnp3d — Perspective-n-Point: 3D-2D 対応からカメラ姿勢を復元(射影の逆問題)。

match3d.project_points が順方向(3D → 2D)なら、pnp3d はその逆(既知の 3D 点とその 2D 投影 +
内部行列 K から回転 R・並進 t を復元)。Physical AI の物体姿勢推定・hand-eye・AR の核。
DLT(Direct Linear Transform)で射影行列を解き、K 既知として [R|t] に分解・正規直交化。
外れ値には pnp_ransac。GT 検証 = 既知姿勢で投影 → 復元 → pose_error ~0・再投影 ~0。

規約: 同次投影 x ≅ K (R X + t)、u=x0/x2, v=x1/x2(match3d.project_points と一致)。
"""
import numpy as np


def _project(X, K, R, t):
    """3D 点 (n,3) → 2D (n,2)。x = K(RX+t)、透視除算。"""
    Xc = (R @ np.asarray(X, float).T).T + np.asarray(t, float)
    x = (np.asarray(K, float) @ Xc.T).T
    return x[:, :2] / x[:, 2:3]


def reprojection_error(points_3d, points_2d, K, R, t):
    """再投影誤差(RMS ピクセル)。姿勢の当てはまり評価。→ scalar。"""
    proj = _project(points_3d, K, R, t)
    d = np.linalg.norm(proj - np.asarray(points_2d, float), axis=1)
    return float(np.sqrt(np.mean(d ** 2)))


def _orthonormalize(M3):
    """3x3 行列を最近傍の回転行列へ(SVD、det=+1 を強制)。→ R。"""
    U, S, Vt = np.linalg.svd(M3)
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(U @ Vt))])
    return U @ D @ Vt, S


def coplanarity_ratio(points_3d):
    """3D 点集合の非平面度 = 共分散の最小/最大固有値比の平方根
    (= RMS 垂直偏差 / RMS 面内広がり、スケール不変)。

    0 に近いほど共平面(全点が 1 平面に載る)。DLT は非共平面点を要するため
    この比が小さい入力は縮退する。→ float(>= 0)。全点一致(退化)なら 0。
    """
    X = np.asarray(points_3d, float)
    Xc = X - X.mean(axis=0)
    cov = (Xc.T @ Xc) / len(Xc)          # 3x3 共分散(主軸方向の分散)
    w = np.clip(np.linalg.eigvalsh(cov), 0.0, None)   # 昇順・非負
    if w[-1] <= 0.0:
        return 0.0                        # 面内の広がりも 0 = 全点一致
    return float(np.sqrt(w[0] / w[-1]))


# DLT が縮退する共平面性の閾値。coplanar は理論上 0、非共平面の 6 点最小標本でも
# 実測 >= 0.07 なので、両者を安全に分離する。
_COPLANAR_TOL = 1e-6


def dlt_pose(points_3d, points_2d, K):
    """DLT で 3D-2D 対応からカメラ姿勢を復元(K 既知)。→ (R (3,3), t (3,))。6 点以上必要。

    x ≅ P X(P=K[R|t])を SVD で解き、M=K⁻¹P から R を正規直交化・scale と符号を depth 正で確定。
    """
    X = np.asarray(points_3d, float)
    x = np.asarray(points_2d, float)
    n = len(X)
    if n < 6:
        raise ValueError("DLT 姿勢推定は 6 点以上必要")
    if len(x) != n:
        raise ValueError("3D と 2D の点数が不一致")
    # 共平面性ガード(fail-closed): 共平面な 3D 点では DLT の係数行列が縮退し、
    # 例外も警告も無く巨大誤差の姿勢を返す。平面ターゲット(チェッカーボード等)は
    # DLT でなくホモグラフィ/IPPE を使うべきなので、ここで明示拒否する。
    if coplanarity_ratio(X) < _COPLANAR_TOL:
        raise ValueError(
            "DLT 姿勢推定には非共平面の 3D 点が必要(共平面入力は係数行列が縮退)。"
            "平面ターゲットにはホモグラフィ/IPPE を使うこと"
        )
    A = np.zeros((2 * n, 12))
    for i in range(n):
        Xi = np.append(X[i], 1.0)
        u, v = x[i]
        A[2 * i, 4:8] = -Xi
        A[2 * i, 8:12] = v * Xi
        A[2 * i + 1, 0:4] = Xi
        A[2 * i + 1, 8:12] = -u * Xi
    _, _, Vt = np.linalg.svd(A)
    P = Vt[-1].reshape(3, 4)
    M = np.linalg.inv(np.asarray(K, float)) @ P     # ≅ λ[R|t]
    # 符号: 点がカメラ前方(depth>0)になるよう M の符号を決める
    depth = M[2, :3] @ X.T + M[2, 3]
    if np.mean(depth) < 0:
        M = -M
    R, S = _orthonormalize(M[:, :3])
    scale = 1.0 / np.mean(S)                          # λ を除く
    t = M[:, 3] * scale
    return R, t


def pnp_ransac(points_3d, points_2d, K, thresh=2.0, iters=300, seed=0):
    """外れ値に頑健な PnP(RANSAC + 最終 DLT リフィット)。→ (R, t, inlier_mask, info)。

    6 点の最小サンプルで DLT → 再投影誤差 < thresh の inlier 最大化 → inlier 全体でリフィット。
    """
    X = np.asarray(points_3d, float)
    x = np.asarray(points_2d, float)
    n = len(X)
    if n < 6:
        raise ValueError("PnP は 6 点以上必要")
    rng = np.random.default_rng(seed)
    best_inliers = None
    best_count = -1
    for _ in range(iters):
        idx = rng.choice(n, 6, replace=False)
        try:
            R, t = dlt_pose(X[idx], x[idx], K)
        except (ValueError, np.linalg.LinAlgError):
            continue
        proj = _project(X, K, R, t)
        err = np.linalg.norm(proj - x, axis=1)
        inliers = err < thresh
        c = int(inliers.sum())
        if c > best_count:
            best_count = c
            best_inliers = inliers
    if best_inliers is None or best_count < 6:
        R, t = dlt_pose(X, x, K)
        mask = np.ones(n, bool)
        return R, t, mask, {"n_inliers": n, "inlier_ratio": 1.0, "iters": iters, "fallback": True}
    R, t = dlt_pose(X[best_inliers], x[best_inliers], K)
    info = {"n_inliers": best_count, "inlier_ratio": best_count / n, "iters": iters,
            "rms": reprojection_error(X[best_inliers], x[best_inliers], K, R, t)}
    return R, t, best_inliers, info
