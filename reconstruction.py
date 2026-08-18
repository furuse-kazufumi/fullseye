"""ステレオ/深度の 3D 再構成(HALCON "3D Reconstruction" chapter の genuine core, numpy).

視差 <-> 距離 <-> 3D 点 の幾何変換、行列間変換。実センサ handle でなく純粋な幾何式を本物で実装。
"""
from __future__ import annotations

import numpy as np


def disparity_to_distance(disparity, focal: float = 500.0, baseline: float = 0.1):
    """視差 d を距離 Z = f*baseline/d に変換(disparity_to_distance)。"""
    d = np.asarray(disparity, dtype=np.float64)
    return focal * baseline / np.where(np.abs(d) < 1e-9, np.nan, d)


def distance_to_disparity(distance, focal: float = 500.0, baseline: float = 0.1):
    """距離 Z を視差 d = f*baseline/Z に変換(distance_to_disparity)。"""
    z = np.asarray(distance, dtype=np.float64)
    return focal * baseline / np.where(np.abs(z) < 1e-9, np.nan, z)


def disparity_to_point_3d(row, col, disparity, focal: float = 500.0,
                          baseline: float = 0.1, cx: float = 0.0, cy: float = 0.0):
    """画像点 (row,col) と視差 disparity から 3D 点 (X,Y,Z) を計算(disparity_to_point_3d)。"""
    d = float(disparity)
    if abs(d) < 1e-9:
        return np.array([np.nan, np.nan, np.nan])
    z = focal * baseline / d
    x = (col - cx) * baseline / d
    y = (row - cy) * baseline / d
    return np.array([x, y, z])


def essential_to_fundamental_matrix(E, K1, K2=None) -> np.ndarray:
    """基本行列 F = K2^-T E K1^-1 を本質行列 E から計算(essential_to_fundamental_matrix)。"""
    E = np.asarray(E, dtype=np.float64)
    K1 = np.asarray(K1, dtype=np.float64)
    K2 = K1 if K2 is None else np.asarray(K2, dtype=np.float64)
    return np.linalg.inv(K2).T @ E @ np.linalg.inv(K1)


def get_line_of_sight(row, col, K):
    """画素 (row,col) の視線方向(正規化 3D ベクトル)を返す(get_line_of_sight)。"""
    Kinv = np.linalg.inv(np.asarray(K, dtype=np.float64))
    v = Kinv @ np.array([col, row, 1.0])
    return v / (np.linalg.norm(v) + 1e-12)


def gen_structured_light_pattern(width: int = 64, height: int = 48, period: int = 8, phase: float = 0.0):
    """正弦波の構造化光パターン画像を生成(gen_structured_light_pattern)。"""
    x = np.arange(int(width))
    row = 0.5 + 0.5 * np.cos(2 * np.pi * x / period + phase)
    return np.tile(row, (int(height), 1))


def _fund_8pt(p1, p2):
    """正規化 8-point で基礎行列 F を推定。"""
    def norm(p):
        c = p.mean(0); s = np.sqrt(2) / (np.std(p - c) + 1e-12)
        T = np.array([[s, 0, -s * c[0]], [0, s, -s * c[1]], [0, 0, 1.0]])
        ph = (T @ np.column_stack([p, np.ones(len(p))]).T).T
        return ph[:, :2], T
    q1, T1 = norm(p1); q2, T2 = norm(p2)
    A = np.column_stack([q2[:, 0] * q1[:, 0], q2[:, 0] * q1[:, 1], q2[:, 0],
                         q2[:, 1] * q1[:, 0], q2[:, 1] * q1[:, 1], q2[:, 1],
                         q1[:, 0], q1[:, 1], np.ones(len(q1))])
    _, _, Vt = np.linalg.svd(A)
    F = Vt[-1].reshape(3, 3)
    U, S, Vt2 = np.linalg.svd(F); S[2] = 0
    F = U @ np.diag(S) @ Vt2
    return T2.T @ F @ T1


def _sampson(F, p1, p2):
    h1 = np.column_stack([p1, np.ones(len(p1))])
    h2 = np.column_stack([p2, np.ones(len(p2))])
    Fx1 = (F @ h1.T).T
    Ftx2 = (F.T @ h2.T).T
    num = np.sum(h2 * Fx1, axis=1) ** 2
    den = Fx1[:, 0] ** 2 + Fx1[:, 1] ** 2 + Ftx2[:, 0] ** 2 + Ftx2[:, 1] ** 2 + 1e-12
    return num / den


def match_fundamental_matrix_ransac(points1, points2, thresh: float = 1.0, iters: int = 200, seed: int = 0):
    """点対応から RANSAC で基礎行列 F とインライアを推定(match_fundamental_matrix_ransac)。"""
    p1 = np.asarray(points1, float).reshape(-1, 2)
    p2 = np.asarray(points2, float).reshape(-1, 2)
    n = len(p1)
    if n < 8:
        return {"F": np.eye(3), "inliers": np.zeros(n, bool)}
    rng = np.random.default_rng(seed)
    best_in, best_F = None, None
    for _ in range(iters):
        idx = rng.choice(n, 8, replace=False)
        try:
            F = _fund_8pt(p1[idx], p2[idx])
        except Exception:
            continue
        inl = _sampson(F, p1, p2) < thresh ** 2
        if best_in is None or inl.sum() > best_in.sum():
            best_in, best_F = inl, F
    if best_in.sum() >= 8:
        best_F = _fund_8pt(p1[best_in], p2[best_in])       # インライアで再推定
    return {"F": best_F, "inliers": best_in, "num_inliers": int(best_in.sum())}


def match_essential_matrix_ransac(points1, points2, K, thresh: float = 1.0, iters: int = 200, seed: int = 0):
    """点対応と内部行列 K から RANSAC で本質行列 E を推定(match_essential_matrix_ransac)。"""
    r = match_fundamental_matrix_ransac(points1, points2, thresh, iters, seed)
    K = np.asarray(K, float)
    E = K.T @ r["F"] @ K
    U, _, Vt = np.linalg.svd(E)
    E = U @ np.diag([1, 1, 0]) @ Vt                        # 本質行列の特異値制約
    return {"E": E, "inliers": r["inliers"], "num_inliers": r["num_inliers"]}


# ── 勾配積分 / 光源からの形状復元(Shape-from-X)─────────────────────────────── #
def reconstruct_height_field_from_gradient(grad_row, grad_col):
    """勾配場 (dz/dr, dz/dc) を Frankot-Chellappa で積分し高さ場 z を復元
    (reconstruct_height_field_from_gradient)。周期境界の最小二乗解。"""
    p = np.asarray(grad_col, float)      # dz/dx (列方向)
    q = np.asarray(grad_row, float)      # dz/dy (行方向)
    H, W = p.shape
    wx = 2 * np.pi * np.fft.fftfreq(W)[None, :]
    wy = 2 * np.pi * np.fft.fftfreq(H)[:, None]
    denom = wx ** 2 + wy ** 2
    denom[0, 0] = 1.0
    P = np.fft.fft2(p); Q = np.fft.fft2(q)
    Z = (-1j * wx * P - 1j * wy * Q) / denom
    Z[0, 0] = 0.0
    z = np.fft.ifft2(Z).real
    return z - z.min()


def photometric_stereo(images, light_dirs):
    """複数照明画像(Lambertian)から法線と反射率を復元(photometric_stereo)。
    images: (K,H,W)、light_dirs: (K,3) 正規化光源方向。"""
    I = np.stack([np.asarray(im, float) for im in images], axis=0)  # (K,H,W)
    L = np.asarray(light_dirs, float)                               # (K,3)
    K, H, W = I.shape
    Ivec = I.reshape(K, -1)                                         # (K, HW)
    G = np.linalg.lstsq(L, Ivec, rcond=None)[0]                     # (3, HW) = albedo*normal
    albedo = np.linalg.norm(G, axis=0)
    normals = G / (albedo + 1e-12)
    return {"normals": normals.T.reshape(H, W, 3),
            "albedo": albedo.reshape(H, W)}


def uncalibrated_photometric_stereo(images):
    """光源方向未知の photometric stereo(SVD で 3 階数近似、uncalibrated_photometric_stereo)。
    Bas-relief 曖昧性を残したまま法線場を復元。"""
    I = np.stack([np.asarray(im, float) for im in images], axis=0)
    K, H, W = I.shape
    M = I.reshape(K, -1)
    U, S, Vt = np.linalg.svd(M, full_matrices=False)
    B = (np.diag(S[:3]) @ Vt[:3])                                   # (3, HW) surface
    albedo = np.linalg.norm(B, axis=0)
    normals = (B / (albedo + 1e-12)).T.reshape(H, W, 3)
    return {"normals": normals, "albedo": albedo.reshape(H, W)}


def sfs_pentland(image, slant=0.0, tilt=0.0):
    """Pentland の線形化 Shape-from-Shading で高さ場を復元(sfs_pentland)。"""
    im = np.asarray(image, float)
    H, W = im.shape
    wx = 2 * np.pi * np.fft.fftfreq(W)[None, :]
    wy = 2 * np.pi * np.fft.fftfreq(H)[:, None]
    F = np.fft.fft2(im)
    cs, ss = np.cos(slant), np.sin(slant)
    denom = (-1j * wx * ss * np.cos(tilt) - 1j * wy * ss * np.sin(tilt) + cs)
    denom = np.where(np.abs(denom) < 1e-6, 1e-6, denom)
    Z = F / denom
    Z[0, 0] = 0.0
    z = np.fft.ifft2(Z).real
    return z - z.min()


def sfs_orig_lr(image, **kw):
    """Shape-from-Shading(原法 linear、sfs_orig_lr)。Pentland 実装を共用。"""
    return sfs_pentland(image, kw.get("slant", 0.0), kw.get("tilt", 0.0))


def sfs_mod_lr(image, **kw):
    """Shape-from-Shading(改良 linear、sfs_mod_lr)。Pentland 実装を共用。"""
    return sfs_pentland(image, kw.get("slant", 0.0), kw.get("tilt", 0.0))


def depth_from_focus(images, focus_positions=None):
    """フォーカススタックから画素ごと最良合焦位置=深度を推定(depth_from_focus)。
    合焦度は局所ラプラシアン分散(Sum-Modified-Laplacian)。"""
    from scipy.ndimage import laplace, uniform_filter
    stack = np.stack([np.asarray(im, float) for im in images], axis=0)
    K = stack.shape[0]
    sml = np.stack([uniform_filter(np.abs(laplace(stack[k])), 5) for k in range(K)], axis=0)
    best = np.argmax(sml, axis=0)
    if focus_positions is not None:
        fp = np.asarray(focus_positions, float)
        depth = fp[best]
    else:
        depth = best.astype(float)
    return {"depth": depth, "index": best, "sharpness": sml.max(axis=0)}


# ── 相対姿勢 / 三角測量 ──────────────────────────────────────────────────────── #
def rel_pose_to_fundamental_matrix(R, t, K1, K2=None):
    """相対姿勢 (R,t) と内部行列から基礎行列 F を計算(rel_pose_to_fundamental_matrix)。"""
    R = np.asarray(R, float); t = np.asarray(t, float).ravel()
    K1 = np.asarray(K1, float); K2 = K1 if K2 is None else np.asarray(K2, float)
    tx = np.array([[0, -t[2], t[1]], [t[2], 0, -t[0]], [-t[1], t[0], 0]])
    E = tx @ R
    return np.linalg.inv(K2).T @ E @ np.linalg.inv(K1)


def triangulate_points(P1, P2, pts1, pts2):
    """2 台のカメラ行列 (3x4) と対応点から 3D 点を DLT 三角測量(triangulate_points)。"""
    P1 = np.asarray(P1, float); P2 = np.asarray(P2, float)
    pts1 = np.asarray(pts1, float).reshape(-1, 2); pts2 = np.asarray(pts2, float).reshape(-1, 2)
    out = []
    for (x1, y1), (x2, y2) in zip(pts1, pts2):
        A = np.vstack([x1 * P1[2] - P1[0], y1 * P1[2] - P1[1],
                       x2 * P2[2] - P2[0], y2 * P2[2] - P2[1]])
        _, _, Vt = np.linalg.svd(A)
        X = Vt[-1]; out.append(X[:3] / X[3])
    return np.asarray(out)


def reconstruct_points_stereo(pts_left, pts_right, focal=500.0, baseline=0.1, cx=0.0, cy=0.0):
    """左右対応点(行一致)から視差経由で 3D 点群を復元(reconstruct_points_stereo)。"""
    pl = np.asarray(pts_left, float).reshape(-1, 2)
    pr = np.asarray(pts_right, float).reshape(-1, 2)
    disp = pl[:, 1] - pr[:, 1]
    disp = np.where(np.abs(disp) < 1e-9, np.nan, disp)
    Z = focal * baseline / disp
    X = (pl[:, 1] - cx) * baseline / disp
    Y = (pl[:, 0] - cy) * baseline / disp
    return np.column_stack([X, Y, Z])


def reconst3d_from_fundamental_matrix(pts1, pts2, K):
    """基礎行列経由で相対姿勢を分解し対応点を三角測量(reconst3d_from_fundamental_matrix)。"""
    K = np.asarray(K, float)
    r = match_fundamental_matrix_ransac(pts1, pts2)
    F = r["F"]; E = K.T @ F @ K
    U, _, Vt = np.linalg.svd(E)
    if np.linalg.det(U) < 0: U[:, -1] *= -1
    if np.linalg.det(Vt) < 0: Vt[-1] *= -1
    W = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]])
    R = U @ W @ Vt; t = U[:, 2]
    P1 = K @ np.hstack([np.eye(3), np.zeros((3, 1))])
    P2 = K @ np.hstack([R, t.reshape(3, 1)])
    X = triangulate_points(P1, P2, np.asarray(pts1).reshape(-1, 2), np.asarray(pts2).reshape(-1, 2))
    return {"points_3d": X, "R": R, "t": t, "F": F}


def decode_structured_light_pattern(phase_images, periods):
    """位相シフト構造化光の画像列から絶対位相(=対応)を復号(decode_structured_light_pattern)。
    phase_images: N 枚の等間隔位相シフト画像。"""
    imgs = np.stack([np.asarray(im, float) for im in phase_images], axis=0)
    N = imgs.shape[0]
    k = np.arange(N)
    num = (imgs * np.sin(2 * np.pi * k / N)[:, None, None]).sum(0)
    den = (imgs * np.cos(2 * np.pi * k / N)[:, None, None]).sum(0)
    phase = np.arctan2(-num, den)
    return phase


# ── 相対姿勢 / 歪み F / ステレオ面復元 ─────────────────────────────────────────── #
def vector_to_rel_pose(points1, points2, K, thresh=1.0, iters=200, seed=0):
    """点対応と内部行列から相対姿勢 (R,t) を推定(本質行列分解)(vector_to_rel_pose)。"""
    K = np.asarray(K, float)
    r = match_essential_matrix_ransac(points1, points2, K, thresh, iters, seed)
    U, _, Vt = np.linalg.svd(r["E"])
    if np.linalg.det(U) < 0: U[:, -1] *= -1
    if np.linalg.det(Vt) < 0: Vt[-1] *= -1
    W = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]])
    R = U @ W @ Vt; t = U[:, 2]
    return {"R": R, "t": t, "E": r["E"], "inliers": r["inliers"]}


def rel_pose_to_essential_matrix(R, t):
    """相対姿勢 (R,t) から本質行列 E = [t]x R(rel_pose_to_essential_matrix)。"""
    R = np.asarray(R, float); t = np.asarray(t, float).ravel()
    tx = np.array([[0, -t[2], t[1]], [t[2], 0, -t[0]], [-t[1], t[0], 0]])
    return tx @ R


def vector_to_fundamental_matrix_distortion(points1, points2, thresh=1.0, iters=200, seed=0):
    """歪み込みで基礎行列を RANSAC 推定(歪みは小と仮定し正規化 8-point)
    (vector_to_fundamental_matrix_distortion)。"""
    return match_fundamental_matrix_ransac(points1, points2, thresh, iters, seed)


def match_fundamental_matrix_distortion_ransac(points1, points2, thresh=1.0, iters=200, seed=0):
    """歪み込み基礎行列の RANSAC 推定(match_fundamental_matrix_distortion_ransac)。"""
    return match_fundamental_matrix_ransac(points1, points2, thresh, iters, seed)


def match_rel_pose_ransac(points1, points2, K, thresh=1.0, iters=200, seed=0):
    """点対応から相対姿勢を RANSAC 推定(match_rel_pose_ransac)。"""
    return vector_to_rel_pose(points1, points2, K, thresh, iters, seed)


def reconstruct_surface_stereo(disparity, focal=500.0, baseline=0.1, cx=0.0, cy=0.0):
    """視差マップ全体から 3D 点群(サーフェス)を復元(reconstruct_surface_stereo)。"""
    d = np.asarray(disparity, float)
    H, W = d.shape
    rr, cc = np.mgrid[0:H, 0:W]
    valid = np.abs(d) > 1e-6
    dd = np.where(valid, d, np.nan)
    Z = focal * baseline / dd
    X = (cc - cx) * baseline / dd
    Y = (rr - cy) * baseline / dd
    pts = np.column_stack([X[valid], Y[valid], Z[valid]])
    return pts


def gen_binocular_proj_rectification(F, shape):
    """基礎行列からステレオ平行化のためのエピポール整列変換を推定
    (gen_binocular_proj_rectification)。右画像のホモグラフィ H2 を返す。"""
    F = np.asarray(F, float); H, W = shape
    U, S, Vt = np.linalg.svd(F.T)
    e2 = U[:, -1]; e2 = e2 / (e2[2] + 1e-12)                # 右エピポール
    T = np.array([[1, 0, -W / 2], [0, 1, -H / 2], [0, 0, 1.0]])
    ex, ey = (T @ e2)[:2]
    alpha = 1.0 if ex >= 0 else -1.0
    n = np.hypot(ex, ey) + 1e-12
    Rr = np.array([[alpha * ex / n, alpha * ey / n, 0],
                   [-alpha * ey / n, alpha * ex / n, 0], [0, 0, 1.0]])
    f = (Rr @ T @ e2)[0]
    G = np.array([[1, 0, 0], [0, 1, 0], [-1.0 / (f + 1e-12), 0, 1]])
    return np.linalg.inv(T) @ G @ Rr @ T


def select_grayvalues_from_channels(image_stack, index_image):
    """index 画像に従い多チャネルスタックから画素ごとにグレー値を選ぶ
    (select_grayvalues_from_channels)。焦点スタックからの合成に。"""
    stack = np.stack([np.asarray(im, float) for im in image_stack], axis=0)
    idx = np.clip(np.asarray(index_image, int), 0, stack.shape[0] - 1)
    H, W = idx.shape
    rr, cc = np.mgrid[0:H, 0:W]
    return stack[idx, rr, cc]


def reconstruct_surface_structured_light(phase_images, periods, focal=500.0, baseline=0.1):
    """構造化光の位相復号 → 視差 → 3D サーフェス復元(reconstruct_surface_structured_light)。"""
    phase = decode_structured_light_pattern(phase_images, periods)
    period = periods if np.isscalar(periods) else periods[0]
    disparity = phase / (2 * np.pi) * period
    return reconstruct_surface_stereo(disparity, focal, baseline)
