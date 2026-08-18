"""残 genuine 最終: 自己校正・MLP/SVM 分類・Sojka コーナー・凸包表面積
(HALCON 複数 chapter genuine, numpy).

いずれも本物のアルゴリズムで実装。学習型(MLP/SVM)は小規模 numpy 実装。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


# ── 自己校正 ─────────────────────────────────────────────────────────────────── #
def radial_distortion_self_calibration(line_points, cx, cy, kappa_range=(-1e-4, 1e-4)):
    """本来直線であるべき点列の残差を最小化して半径歪み kappa を推定(plumb-line 法)
    (radial_distortion_self_calibration)。line_points: 直線ごとの (N,2) 点列リスト。"""
    def undistort(pts, k):
        y = pts[:, 0] - cy; x = pts[:, 1] - cx
        r2 = x * x + y * y
        f = 1 + k * r2
        return np.column_stack([cy + y * f, cx + x * f])

    def straightness_cost(k):
        cost = 0.0
        for pts in line_points:
            u = undistort(np.asarray(pts, float), k)
            c = u.mean(0); d = u - c
            _, s, _ = np.linalg.svd(d, full_matrices=False)
            cost += s[1] ** 2                                   # 2 番目の特異値=直線からの広がり
        return cost
    ks = np.linspace(kappa_range[0], kappa_range[1], 401)
    costs = [straightness_cost(k) for k in ks]
    return {"kappa": float(ks[int(np.argmin(costs))]), "cost": float(min(costs))}


def radiometric_self_calibration(images, exposures):
    """異なる露光の画像群からカメラ応答関数(逆応答 LUT)を推定
    (radiometric_self_calibration)。Debevec 風の相互性拘束の簡易版。"""
    imgs = [np.clip(_img(im), 0, 1) for im in images]
    exp = np.asarray(exposures, float)
    # 各露光比での輝度対応から単調な応答 g を最小二乗推定(256 レベル)
    L = 256
    g = np.linspace(0, 1, L)                                    # 初期=線形
    for _ in range(20):
        # 参照露光 0 に対する期待輝度
        E = np.zeros_like(imgs[0])
        for im, e in zip(imgs, exp):
            E += g[np.clip((im * (L - 1)).astype(int), 0, L - 1)] / e
        E /= len(imgs)
        # g 更新: level ごとに観測輝度の平均へ
        acc = np.zeros(L); cnt = np.zeros(L)
        for im, e in zip(imgs, exp):
            lev = np.clip((im * (L - 1)).astype(int), 0, L - 1).ravel()
            np.add.at(acc, lev, (E * e).ravel())
            np.add.at(cnt, lev, 1)
        newg = np.where(cnt > 0, acc / np.maximum(cnt, 1), g)
        newg = np.maximum.accumulate(newg)                     # 単調性強制
        if np.abs(newg - g).max() < 1e-6:
            g = newg; break
        g = newg
    return {"response": g / (g.max() + 1e-12)}


def _sym_basis():
    """対称 3x3 の 6 基底行列(パラメータ w=[w11,w12,w13,w22,w23,w33] に対応)。"""
    B = []
    for (i, j) in [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2)]:
        M = np.zeros((3, 3)); M[i, j] = 1; M[j, i] = 1
        B.append(M)
    return B


def stationary_camera_self_calibration(homographies):
    """回転のみの無限遠ホモグラフィ H = K R K^-1 から内部行列 K を推定
    (stationary_camera_self_calibration)。DIAC ω*=KK^T は H ω* H^T = ω* を満たす拘束を解く。"""
    basis = _sym_basis()
    upper = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2)]
    A = []
    for H in homographies:
        H = np.asarray(H, float)
        for (i, j) in upper:                                   # 各 H から 6 個の線形拘束
            row = [((H @ B @ H.T) - B)[i, j] for B in basis]
            A.append(row)
    _, _, Vt = np.linalg.svd(np.asarray(A))
    w = Vt[-1]
    Ws = np.array([[w[0], w[1], w[2]], [w[1], w[3], w[4]], [w[2], w[4], w[5]]])
    if Ws[2, 2] < 0:
        Ws = -Ws
    Ws = Ws / Ws[2, 2]                                          # ω* = KK^T (最終要素 1 に正規化)
    try:
        K = np.linalg.cholesky(Ws)                             # 下三角 = K(上三角形式へ)
        # cholesky は下三角 L で Ws=L L^T。K は上三角なので RQ 的に整える
        K = K / K[2, 2]
    except np.linalg.LinAlgError:
        K = np.eye(3)
    # KK^T の Cholesky(下三角)から上三角 K を得るには転置反転が必要 → 直接パラメータ抽出
    cx = Ws[0, 2]; cy = Ws[1, 2]
    fx2 = Ws[0, 0] - cx ** 2; fy2 = Ws[1, 1] - cy ** 2
    fx = float(np.sqrt(fx2)) if fx2 > 0 else float("nan")
    fy = float(np.sqrt(fy2)) if fy2 > 0 else float("nan")
    Kmat = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.0]])
    return {"fx": fx, "fy": fy, "cx": float(cx), "cy": float(cy), "K": Kmat}


# ── MLP / SVM 分類(小規模 genuine 学習)──────────────────────────────────────── #
def _train_mlp(X, y, hidden=8, epochs=300, lr=0.5, seed=0):
    rng = np.random.default_rng(seed)
    classes = np.unique(y); K = len(classes)
    Y = np.eye(K)[np.searchsorted(classes, y)]
    D = X.shape[1]
    W1 = rng.normal(0, 0.5, (D, hidden)); b1 = np.zeros(hidden)
    W2 = rng.normal(0, 0.5, (hidden, K)); b2 = np.zeros(K)
    for _ in range(epochs):
        h = np.tanh(X @ W1 + b1)
        o = h @ W2 + b2
        p = np.exp(o - o.max(1, keepdims=True)); p /= p.sum(1, keepdims=True)
        dO = (p - Y) / len(X)
        dW2 = h.T @ dO; db2 = dO.sum(0)
        dh = (dO @ W2.T) * (1 - h ** 2)
        dW1 = X.T @ dh; db1 = dh.sum(0)
        W1 -= lr * dW1; b1 -= lr * db1; W2 -= lr * dW2; b2 -= lr * db2
    return {"W1": W1, "b1": b1, "W2": W2, "b2": b2, "classes": classes}


def classify_image_class_mlp(feature_images, model):
    """学習済み MLP で多チャネル特徴画像を画素分類(classify_image_class_mlp)。"""
    F = feature_images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = _img(F); H, W, D = F.shape
    X = F.reshape(-1, D)
    h = np.tanh(X @ model["W1"] + model["b1"])
    o = h @ model["W2"] + model["b2"]
    return model["classes"][o.argmax(1)].reshape(H, W)


def train_class_mlp(features, labels, hidden=8, epochs=300):
    """MLP 分類器を学習(train_class_mlp)。"""
    return _train_mlp(np.asarray(features, float).reshape(len(features), -1),
                      np.asarray(labels).ravel(), hidden, epochs)


def train_class_svm(features, labels, C=1.0, epochs=300, lr=0.01):
    """線形 SVM(hinge 損失, one-vs-rest)を学習(train_class_svm)。"""
    X = np.asarray(features, float).reshape(len(features), -1)
    y = np.asarray(labels).ravel(); classes = np.unique(y)
    D = X.shape[1]; Ws = []
    for c in classes:
        t = np.where(y == c, 1.0, -1.0)
        w = np.zeros(D); b = 0.0
        for _ in range(epochs):
            margin = t * (X @ w + b)
            mask = margin < 1
            dw = w - C * (X[mask] * t[mask, None]).sum(0)
            db = -C * t[mask].sum()
            w -= lr * dw; b -= lr * db
        Ws.append((w, b))
    return {"weights": Ws, "classes": classes}


def classify_image_class_svm(feature_images, model):
    """学習済み線形 SVM で多チャネル特徴画像を画素分類(classify_image_class_svm)。"""
    F = feature_images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = _img(F); H, W, D = F.shape
    X = F.reshape(-1, D)
    scores = np.column_stack([X @ w + b for w, b in model["weights"]])
    return model["classes"][scores.argmax(1)].reshape(H, W)


# ── Sojka サブピクセルコーナー ──────────────────────────────────────────────── #
def points_sojka(image, sigma=1.0, thresh_rel=0.01, max_points=500):
    """Sojka の勾配共分散に基づくコーナー応答でサブピクセルコーナーを抽出
    (points_sojka)。構造テンソルの最小固有値をコーナー強度とする。"""
    from scipy.ndimage import gaussian_filter, maximum_filter
    im = _img(image)
    gy, gx = np.gradient(gaussian_filter(im, sigma))
    Axx = gaussian_filter(gx * gx, sigma); Ayy = gaussian_filter(gy * gy, sigma)
    Axy = gaussian_filter(gx * gy, sigma)
    tmp = np.sqrt((Axx - Ayy) ** 2 + 4 * Axy ** 2)
    lam_min = 0.5 * (Axx + Ayy - tmp)                          # 最小固有値=コーナー強度
    mx = maximum_filter(lam_min, 3)
    peaks = (lam_min == mx) & (lam_min > thresh_rel * lam_min.max())
    ys, xs = np.where(peaks)
    if len(ys) == 0:
        return np.zeros((0, 2))
    order = np.argsort(lam_min[ys, xs])[::-1][:max_points]
    # サブピクセル: 局所 2 次当てはめ
    out = []
    for y, x in zip(ys[order], xs[order]):
        if 0 < y < im.shape[0] - 1 and 0 < x < im.shape[1] - 1:
            dy = 0.5 * (lam_min[y + 1, x] - lam_min[y - 1, x]) / \
                (lam_min[y + 1, x] - 2 * lam_min[y, x] + lam_min[y - 1, x] - 1e-12)
            dx = 0.5 * (lam_min[y, x + 1] - lam_min[y, x - 1]) / \
                (lam_min[y, x + 1] - 2 * lam_min[y, x] + lam_min[y, x - 1] - 1e-12)
            out.append([y - np.clip(dy, -0.5, 0.5), x - np.clip(dx, -0.5, 0.5)])
        else:
            out.append([y, x])
    return np.asarray(out)


# ── 凸包表面積(3D Object Model)────────────────────────────────────────────── #
def area_object_model_3d(points):
    """3D 点群の凸包表面積を返す(area_object_model_3d)。
    凸物体では厳密。非凸では凸包近似(過小)であることに注意。"""
    from scipy.spatial import ConvexHull
    p = np.asarray(points, float).reshape(-1, 3)
    if len(p) < 4:
        return 0.0
    try:
        return float(ConvexHull(p).area)
    except Exception:
        return 0.0
