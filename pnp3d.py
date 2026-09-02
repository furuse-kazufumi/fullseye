# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pnp3d — Perspective-n-Point: 3D-2D 対応からカメラ姿勢を復元(射影の逆問題)。

match3d.project_points が順方向(3D → 2D)なら、pnp3d はその逆(既知の 3D 点とその 2D 投影 +
内部行列 K から回転 R・並進 t を復元)。Physical AI の物体姿勢推定・hand-eye・AR の核。

手順(:func:`pnp_pose` / :func:`dlt_pose`):
  1. **正規化** — 画素は ``K⁻¹`` で正規化画像座標(光線)へ、3D 点は重心を原点・平均距離を
     ``√3`` へ(Hartley 正規化)。素の画素座標・世界座標で DLT を組むと係数行列の条件数が
     焦点距離や世界原点からの距離に比例して悪化する(2026-09-02 実測: 世界原点を
     (100,200,0) ずらすだけでカメラ中心誤差 0.02 → 2.1、再投影 4.5 → 106 px)。
  2. **初期姿勢** — 非共平面なら DLT(``x ≅ P X`` を SVD で解き ``M=K⁻¹P`` を正規直交化)、
     共平面/準共平面(:func:`coplanarity_ratio` < :data:`_COPLANAR_TOL`)なら平面→画像の
     ホモグラフィを分解する平面 PnP(H&Z §8.1.1)。準共平面でも DLT は組めるので両方を
     試し、精密化後の再投影 RMS が小さい方を採る。
  3. **精密化** — 再投影誤差の Levenberg-Marquardt(解析ヤコビアン)。DLT は代数誤差の
     最小化で、ノイズ下では幾何誤差最小の解から系統的にずれる(0.5 px ノイズで回転誤差
     0.35° → 精密化後 0.06°、camera.solve_pnp と同等)。

外れ値には pnp_ransac。GT 検証 = 既知姿勢で投影 → 復元 → pose_error ~0・再投影 ~0。

規約: 同次投影 x ≅ K (R X + t)、u=x0/x2, v=x1/x2(match3d.project_points と一致)。
"""
import numpy as np


def _as_image_points(points_2d, name="points_2d"):
    """画像平面の点列を (N,2) float へ。**fail-closed**: 画像や 3-D 点は明示拒否。

    ここが緩かったために「2-D 点列を要求する引数へ 32x32 の画像を渡す」使い方が
    生の ``IndexError`` になっていた(2026-09-01 実測)。何が悪いかを名指しする
    ``ValueError`` にすると、呼び手は入力を直せる — 素の IndexError では
    「この op の契約の穴」なのか「入力が悪い」のか区別できない。
    """
    x = np.asarray(points_2d, float)
    if x.ndim != 2 or x.shape[1] != 2:
        raise ValueError(
            f"{name} must be (N, 2) image-plane points, got shape {x.shape}"
            + (" — this looks like an image, not a point list;"
               " project 3-D points with match3d.project_points first"
               if x.ndim == 2 and x.shape[1] > 3 else "")
        )
    if not np.all(np.isfinite(x)):
        raise ValueError(f"{name} contains non-finite values (NaN/Inf)")
    return x


def _project(X, K, R, t):
    """3D 点 (n,3) → 2D (n,2)。x = K(RX+t)、透視除算。"""
    Xc = (R @ np.asarray(X, float).T).T + np.asarray(t, float)
    x = (np.asarray(K, float) @ Xc.T).T
    return x[:, :2] / x[:, 2:3]


def reprojection_error(points_3d, points_2d, K, R, t):
    """再投影誤差(RMS ピクセル)。姿勢の当てはまり評価。→ scalar。

    Raises ValueError: points_2d が (N,2) でない / 点数不一致 / 非有限。
    """
    x = _as_image_points(points_2d)
    proj = _project(points_3d, K, R, t)
    if len(proj) != len(x):
        raise ValueError(
            f"3D and 2D point counts do not match ({len(proj)} vs {len(x)})")
    d = np.linalg.norm(proj - x, axis=1)
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


# 一般 DLT だけでは信頼できない共平面性の閾値(RMS 厚み / RMS 面内広がり)。
# この比を下回る入力は平面 PnP(ホモグラフィ分解)も初期姿勢の候補に加える。
# 旧値 1e-6 は「厳密に平面」しか捕まえられず、厚み比 5e-2 でも 0.3 px ノイズで
# 素の DLT が 170° 級に破綻していた(2026-09-02 実測)。
_COPLANAR_TOL = 0.05

# 全点が一直線/一点(2 番目の広がりも 0)なら姿勢は定まらない → fail-closed。
_DEGENERATE_TOL = 1e-9


def _rodrigues(w):
    """回転ベクトル (3,) → 回転行列。"""
    w = np.asarray(w, float)
    th = float(np.linalg.norm(w))
    if th < 1e-12:
        return np.eye(3)
    k = w / th
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1.0 - np.cos(th)) * Kx @ Kx


def _normalized_rays(x, K):
    """画素 (N,2) → K⁻¹ 正規化画像座標 (N,2)。"""
    Kinv = np.linalg.inv(np.asarray(K, float))
    m = np.hstack([x, np.ones((len(x), 1))]) @ Kinv.T
    return m[:, :2] / m[:, 2:3]


def _hartley_3d(X):
    """3D Hartley 正規化: 重心→原点、平均距離→√3。→ (T (4x4), X_n)。"""
    c = X.mean(0)
    md = float(np.mean(np.linalg.norm(X - c, axis=1)))
    s = np.sqrt(3.0) / md if md > 1e-12 else 1.0
    T = np.eye(4)
    T[:3, :3] *= s
    T[:3, 3] = -s * c
    return T, (X - c) * s


def _hartley_2d(m):
    """2D Hartley 正規化: 重心→原点、平均距離→√2。→ (T (3x3), m_n)。"""
    c = m.mean(0)
    md = float(np.mean(np.linalg.norm(m - c, axis=1)))
    s = np.sqrt(2.0) / md if md > 1e-12 else 1.0
    T = np.array([[s, 0.0, -s * c[0]], [0.0, s, -s * c[1]], [0.0, 0.0, 1.0]])
    return T, (m - c) * s


def _pose_from_M(M, X):
    """M ≅ λ[R|t](正規化座標での射影)から (R, t) を符号・scale 込みで確定。"""
    depth = M[2, :3] @ X.T + M[2, 3]
    if np.mean(depth) < 0:                  # 点がカメラ前方(depth>0)になる符号
        M = -M
    R, S = _orthonormalize(M[:, :3])
    t = M[:, 3] / np.mean(S)                # λ を除く
    return R, t


def _dlt_init(X, m):
    """一般 DLT(正規化座標)。X (N,3) 世界点、m (N,2) 正規化画像座標。→ (R, t)。"""
    T3, Xn = _hartley_3d(X)
    T2, mn = _hartley_2d(m)
    n = len(Xn)
    A = np.zeros((2 * n, 12))
    for i in range(n):
        Xi = np.append(Xn[i], 1.0)
        u, v = mn[i]
        A[2 * i, 4:8] = -Xi
        A[2 * i, 8:12] = v * Xi
        A[2 * i + 1, 0:4] = Xi
        A[2 * i + 1, 8:12] = -u * Xi
    _, _, Vt = np.linalg.svd(A)
    Pn = Vt[-1].reshape(3, 4)
    M = np.linalg.inv(T2) @ Pn @ T3         # 正規化を戻す: m ≅ T2⁻¹ Pn T3 X
    return _pose_from_M(M, X)


def _planar_init(X, m):
    """平面 PnP: 最小二乗平面の面内座標→正規化画像のホモグラフィを分解(H&Z §8.1.1)。

    面内基底 B[:, :2] で ``X = c + B p``(p は (N,2) 面内座標)とし、``m ≅ H [p;1]`` を
    DLT で解いて ``H ≅ [r1 r2 t]`` から R・t を復元する。準共平面入力でも
    最良平面のホモグラフィが初期値として十分で、あとは精密化が面外成分を拾う。
    """
    c = X.mean(0)
    Xc = X - c
    _, _, Vt = np.linalg.svd(Xc)
    B = Vt.T                                # 列: 面内 2 軸 + 法線
    if np.linalg.det(B) < 0:
        B[:, 2] = -B[:, 2]
    p2 = Xc @ B[:, :2]
    Tp, pn = _hartley_2d(p2)
    Tm, mn = _hartley_2d(m)
    n = len(X)
    A = np.zeros((2 * n, 9))
    for i in range(n):
        x, y = pn[i]
        u, v = mn[i]
        A[2 * i] = [-x, -y, -1, 0, 0, 0, u * x, u * y, u]
        A[2 * i + 1] = [0, 0, 0, -x, -y, -1, v * x, v * y, v]
    _, _, Vt2 = np.linalg.svd(A)
    H = np.linalg.inv(Tm) @ Vt2[-1].reshape(3, 3) @ Tp
    best = None
    for s in (1.0, -1.0):
        lam = s / max(0.5 * (np.linalg.norm(H[:, 0]) + np.linalg.norm(H[:, 1])), 1e-12)
        r1, r2, t_h = lam * H[:, 0], lam * H[:, 1], lam * H[:, 2]
        Rh, _ = _orthonormalize(np.stack([r1, r2, np.cross(r1, r2)], 1))
        R = Rh @ B.T                        # 面内フレーム → 世界フレーム
        t = t_h - R @ c
        front = float((((X @ R.T) + t)[:, 2] > 0).mean())
        proj = (X @ R.T + t)
        proj = proj[:, :2] / np.where(np.abs(proj[:, 2:3]) > 1e-12, proj[:, 2:3], 1e-12)
        err = float(np.mean(np.linalg.norm(proj - m, axis=1)))
        score = (front, -err)
        if best is None or score > best[0]:
            best = (score, R, t)
    return best[1], best[2]


def _refine_lm(X, x, K, R, t, iters=30):
    """再投影誤差の Levenberg-Marquardt 精密化(解析ヤコビアン、左乗の微小回転)。→ (R, t)。"""
    K = np.asarray(K, float)
    N = len(X)
    # Parametrise the rotation about the point centroid, not the world origin:
    # X_c = R (X - c) + t'. With a far world origin (|X| ~ 1e2..1e3) a rotation
    # update about the origin moves the points by |X|·δω and t must undo it, an
    # ill-conditioned coupling on which LM stalled (offset (1000,0,0): 110 px rms
    # after 300 iterations, 2026-09-02). Centred, the two are nearly decoupled.
    c = X.mean(0)
    X = X - c
    t = t + R @ c

    def residual(R, t):
        return (_project(X, K, R, t) - x).ravel()

    r = residual(R, t)
    cost = float(r @ r)
    lam = 1e-3
    for _ in range(int(iters)):
        Xc = X @ R.T + t                                        # (N,3)
        # d Xc / d[δω, δt] = [ -[Xc]x | I ]  (R ← exp(δω) R)
        J3 = np.zeros((N, 3, 6))
        J3[:, 0, 1] = Xc[:, 2]; J3[:, 0, 2] = -Xc[:, 1]
        J3[:, 1, 0] = -Xc[:, 2]; J3[:, 1, 2] = Xc[:, 0]
        J3[:, 2, 0] = Xc[:, 1]; J3[:, 2, 1] = -Xc[:, 0]
        J3[:, 0, 3] = J3[:, 1, 4] = J3[:, 2, 5] = 1.0
        A = np.einsum("ij,njk->nik", K, J3)                     # d(K Xc)/dξ (N,3,6)
        p = Xc @ K.T                                            # (N,3)
        z = np.where(np.abs(p[:, 2]) > 1e-12, p[:, 2], 1e-12)
        Ju = (A[:, 0, :] * z[:, None] - p[:, 0:1] * A[:, 2, :]) / (z ** 2)[:, None]
        Jv = (A[:, 1, :] * z[:, None] - p[:, 1:2] * A[:, 2, :]) / (z ** 2)[:, None]
        J = np.empty((2 * N, 6))
        J[0::2] = Ju
        J[1::2] = Jv
        H = J.T @ J
        g = J.T @ r
        try:
            step = np.linalg.solve(H + lam * np.diag(np.diag(H) + 1e-12), -g)
        except np.linalg.LinAlgError:
            break
        R_new = _rodrigues(step[:3]) @ R
        t_new = t + step[3:]
        r_new = residual(R_new, t_new)
        cost_new = float(r_new @ r_new)
        if cost_new < cost:
            R, t, r, cost, lam = R_new, t_new, r_new, cost_new, max(lam * 0.5, 1e-9)
            if np.linalg.norm(step) < 1e-12:
                break
        else:
            lam = min(lam * 4.0, 1e6)
    return R, t - R @ c


def _check_inputs(points_3d, points_2d, name):
    X = np.asarray(points_3d, float)
    x = _as_image_points(points_2d)
    n = len(X)
    if X.ndim != 2 or X.shape[1] != 3:
        raise ValueError(f"points_3d must be (N, 3), got shape {X.shape}")
    if not np.all(np.isfinite(X)):
        raise ValueError("points_3d contains non-finite values (NaN/Inf)")
    if n < 6:
        raise ValueError(f"{name} requires at least 6 points")
    if len(x) != n:
        raise ValueError(
            f"3D and 2D point counts do not match ({n} vs {len(x)})")
    return X, x


def pnp_pose(points_3d, points_2d, K, refine=True, iters=30):
    """正規化 DLT / 平面 PnP 初期化 + LM 精密化で姿勢を復元。→ (R (3,3), t (3,), rms)。

    :func:`dlt_pose` の完全版(モジュール docstring の手順 1〜3)。``rms`` は返した姿勢の
    再投影 RMS 誤差 [px](小さいほど当てはまりが良い; 対応が正しく K が合っていれば
    画素ノイズ程度)。``refine=False`` で初期姿勢のみ(RANSAC の最小標本など速度優先時)。

    Raises ValueError: 形状不正 / 6 点未満 / 点数不一致 / 非有限 / 全点が一直線か
        一点(姿勢が定まらない)。
    """
    X, x = _check_inputs(points_3d, points_2d, "pnp_pose")
    K = np.asarray(K, float)
    sv = np.linalg.svd(X - X.mean(0), compute_uv=False)
    if sv[0] <= 0.0 or sv[1] <= _DEGENERATE_TOL * sv[0]:
        raise ValueError(
            "PnP requires 3D points spanning at least a plane "
            "(all points collinear/coincident: pose is not determined)")
    m = _normalized_rays(x, K)
    candidates = []
    planar = coplanarity_ratio(X) < _COPLANAR_TOL
    if not (planar and sv[2] <= _DEGENERATE_TOL * sv[0]):   # exactly planar: DLT is pure noise
        candidates.append(_dlt_init(X, m))
    if planar:
        candidates.append(_planar_init(X, m))
    best = None
    for R0, t0 in candidates:
        if refine:
            R0, t0 = _refine_lm(X, x, K, R0, t0, iters=iters)
        rms = reprojection_error(X, x, K, R0, t0)
        front = float(((X @ R0.T + t0)[:, 2] > 0).mean())
        score = (front, -rms)
        if best is None or score > best[0]:
            best = (score, R0, t0, rms)
    _, R, t, rms = best
    return R, t, float(rms)


def dlt_pose(points_3d, points_2d, K):
    """DLT で 3D-2D 対応からカメラ姿勢を復元(K 既知)。→ (R (3,3), t (3,))。6 点以上必要。

    :func:`pnp_pose` の (R, t) 部分(正規化 DLT + 平面 PnP 分岐 + LM 精密化)。再投影
    RMS も要るなら :func:`pnp_pose` を使う。共平面入力(チェッカーボード等)は平面 PnP へ
    自動で振り分ける(旧実装は fail-closed で拒否していたが、正しく解けるので解く)。
    """
    R, t, _ = pnp_pose(points_3d, points_2d, K, refine=True)
    return R, t


def pnp_ransac(points_3d, points_2d, K, thresh=2.0, iters=300, seed=0):
    """外れ値に頑健な PnP(RANSAC + 最終 DLT リフィット)。→ (R, t, inlier_mask, info)。

    6 点の最小サンプルで DLT(精密化なし)→ 再投影誤差 < thresh の inlier 最大化 →
    inlier 全体で :func:`pnp_pose`(精密化あり)リフィット。

    Raises ValueError: points_2d が (N,2) でない / points_3d が (N,3) でない /
        点数不一致 / 6 点未満 / 非有限。
    """
    X, x = _check_inputs(points_3d, points_2d, "PnP")
    n = len(X)
    rng = np.random.default_rng(seed)
    best_inliers = None
    best_count = -1
    for _ in range(iters):
        idx = rng.choice(n, 6, replace=False)
        try:
            R, t, _ = pnp_pose(X[idx], x[idx], K, refine=False)
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
        # RANSAC が最小合意(6 inlier)に届かず → 全点 PnP で fallback。
        # 旧実装は inlier_ratio=1.0・n_inliers=n を無条件で載せ「100% コンセンサス」を
        # 詐称していた。ここでは実測の再投影誤差で inlier を数え直し honest に報告する。
        try:
            R, t, rms = pnp_pose(X, x, K)
        except (ValueError, np.linalg.LinAlgError) as e:
            # 縮退など PnP 不能。姿勢を捏造せず fail-closed で失敗を明示する。
            raise ValueError(
                f"pnp_ransac: RANSAC consensus insufficient and full-point PnP fallback also failed: {e}"
            ) from e
        proj = _project(X, K, R, t)
        err = np.linalg.norm(proj - x, axis=1)
        mask = err < thresh
        info = {
            "n_inliers": int(mask.sum()),
            "inlier_ratio": float(mask.mean()),
            "iters": iters,
            "fallback": True,
            "rms": rms,
        }
        return R, t, mask, info
    R, t, rms = pnp_pose(X[best_inliers], x[best_inliers], K)
    info = {"n_inliers": best_count, "inlier_ratio": best_count / n, "iters": iters,
            "rms": rms}
    return R, t, best_inliers, info
