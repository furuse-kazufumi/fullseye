"""特徴空間分類・領域成長・マーカー watershed(HALCON "Segmentation" chapter genuine, numpy).

グレー/多次元特徴空間での画素分類、gray 類似度での領域拡張、マーカー制御 watershed。
学習型(GMM/MLP/SVM)は別ドメインのため対象外。image = 2D float64、region = bool 2D。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


def check_difference(image, ref_image, tol=0.1):
    """基準画像との差が tol を超える画素を領域として返す(check_difference)。"""
    return np.abs(_img(image) - _img(ref_image)) > float(tol)


def class_2dim_sup(image1, image2, ref_region):
    """2 チャネル特徴空間で ref_region の分布に入る画素を分類(教師つき)(class_2dim_sup)。"""
    a = _img(image1); b = _img(image2); m = np.asarray(ref_region, bool)
    fa = a[m]; fb = b[m]
    lo_a, hi_a = fa.min(), fa.max(); lo_b, hi_b = fb.min(), fb.max()
    return (a >= lo_a) & (a <= hi_a) & (b >= lo_b) & (b <= hi_b)


def learn_ndim_norm(features_fg, features_bg=None):
    """特徴ベクトル群から正規分布クラス(平均・共分散)を学習(learn_ndim_norm)。"""
    X = np.asarray(features_fg, float).reshape(len(features_fg), -1)
    mu = X.mean(0); cov = np.cov(X.T) + 1e-6 * np.eye(X.shape[1])
    model = {"mean": mu, "cov": cov, "inv": np.linalg.inv(cov)}
    if features_bg is not None:
        Xb = np.asarray(features_bg, float).reshape(len(features_bg), -1)
        model["bg_mean"] = Xb.mean(0)
    return model


def class_ndim_norm(feature_images, model, thresh=3.0):
    """ND 特徴画像を学習済み正規分布クラスで分類(Mahalanobis 距離 < thresh)(class_ndim_norm)。
    feature_images: (H,W,D) or D 枚の 2D。"""
    F = feature_images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = np.asarray(F, float)
    H, W, D = F.shape
    diff = F.reshape(-1, D) - model["mean"]
    md = np.einsum("ij,jk,ik->i", diff, model["inv"], diff)
    return (np.sqrt(md) < thresh).reshape(H, W)


def class_2dim_unsup(image1, image2, n_clusters=3, iters=20):
    """2 チャネル特徴空間を k-means で教師なし分類(class_2dim_unsup)。ラベル画像を返す。"""
    a = _img(image1); b = _img(image2)
    X = np.column_stack([a.ravel(), b.ravel()])
    rng = np.random.default_rng(0)
    C = X[rng.choice(len(X), int(n_clusters), replace=False)]
    for _ in range(int(iters)):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(2)
        lab = d.argmin(1)
        newC = np.array([X[lab == k].mean(0) if (lab == k).any() else C[k]
                         for k in range(int(n_clusters))])
        if np.allclose(newC, C):
            break
        C = newC
    return lab.reshape(a.shape)


def classify_image_class_lut(image, lut):
    """グレー LUT による画素分類(閾値/ラベル LUT)(classify_image_class_lut)。"""
    im = _img(image); L = len(lut)
    idx = np.clip((im * (L - 1)).round().astype(int), 0, L - 1)
    return np.asarray(lut)[idx]


def expand_gray(image, seed_region, tol=0.05):
    """seed から gray 類似(|Δ|<tol)で領域を膨張(expand_gray)。"""
    from scipy.ndimage import binary_dilation
    im = _img(image); reg = np.asarray(seed_region, bool).copy()
    ref = im[reg].mean() if reg.any() else 0.0
    for _ in range(1000):
        cand = binary_dilation(reg) & ~reg & (np.abs(im - ref) < tol)
        if not cand.any():
            break
        reg |= cand
    return reg


def regiongrowing_n(feature_images, tol=0.05, min_size=1):
    """多チャネル特徴の類似性で画像全体を領域分割(regiongrowing_n)。ラベル画像を返す。"""
    F = feature_images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = np.asarray(F, float)
    if F.ndim == 2:
        F = F[..., None]
    H, W, D = F.shape
    labels = np.zeros((H, W), int); cur = 0
    from collections import deque
    for r0 in range(H):
        for c0 in range(W):
            if labels[r0, c0]:
                continue
            cur += 1; ref = F[r0, c0]
            q = deque([(r0, c0)]); labels[r0, c0] = cur; size = 0
            while q:
                r, c = q.popleft(); size += 1
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and not labels[rr, cc]:
                        if np.abs(F[rr, cc] - ref).max() < tol:
                            labels[rr, cc] = cur; q.append((rr, cc))
    return labels


def watersheds_marker(image, markers):
    """マーカー制御 watershed 分割(watersheds_marker)。markers: int ラベル画像(0=未割当)。"""
    from scipy import ndimage
    try:
        from skimage.segmentation import watershed
        return watershed(_img(image), markers=np.asarray(markers, int))
    except Exception:
        # skimage 不在時の代替: マーカーからの測地的最近傍(距離変換ベース)
        mk = np.asarray(markers, int)
        idx = ndimage.distance_transform_edt(mk == 0, return_distances=False,
                                             return_indices=True)
        return mk[tuple(idx)]
