"""色変換 LUT・主成分/正準変量変換・インペイント変種(HALCON "Filters" chapter genuine, numpy).

色空間変換 LUT、多チャネル画像の PCA/CVA、拡散系インペイント。
多チャネル画像 = (H,W,C) float64、単一画像 = 2D。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


def create_color_trans_lut(kind="rgb_to_hsv"):
    """色変換 LUT(変換種別)を作る(create_color_trans_lut)。"""
    return {"kind": kind}


def clear_color_trans_lut(lut):
    """色変換 LUT を破棄(clear_color_trans_lut)。"""
    return None


def apply_color_trans_lut(image_rgb, lut):
    """RGB (H,W,3) を LUT の色空間へ変換(apply_color_trans_lut)。rgb_to_hsv / rgb_to_yuv 等。"""
    rgb = _img(image_rgb)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    kind = lut["kind"]
    if kind == "rgb_to_hsv":
        mx = rgb.max(-1); mn = rgb.min(-1); df = mx - mn + 1e-12
        h = np.zeros_like(mx)
        idx = mx == r; h[idx] = ((g - b) / df)[idx] % 6
        idx = mx == g; h[idx] = ((b - r) / df)[idx] + 2
        idx = mx == b; h[idx] = ((r - g) / df)[idx] + 4
        h = h / 6.0
        s = np.where(mx > 0, (mx - mn) / (mx + 1e-12), 0)
        return np.stack([h, s, mx], axis=-1)
    if kind == "rgb_to_yuv":
        y = 0.299 * r + 0.587 * g + 0.114 * b
        u = -0.14713 * r - 0.28886 * g + 0.436 * b
        v = 0.615 * r - 0.51499 * g - 0.10001 * b
        return np.stack([y, u, v], axis=-1)
    if kind == "rgb_to_gray":
        return 0.299 * r + 0.587 * g + 0.114 * b
    raise ValueError("unknown color transform: " + kind)


def trans_from_rgb(image_rgb, color_space="hsv"):
    """RGB から指定色空間へ変換(trans_from_rgb)。"""
    return apply_color_trans_lut(image_rgb, {"kind": "rgb_to_" + color_space})


def convert_map_type(map_array, target="float"):
    """マップ/画像の型変換(convert_map_type)。"""
    a = np.asarray(map_array)
    if target in ("float", "real"):
        return a.astype(np.float64)
    if target in ("int", "int32"):
        return a.astype(np.int32)
    if target == "byte":
        return np.clip(a * 255, 0, 255).astype(np.uint8) if a.dtype.kind == "f" else a.astype(np.uint8)
    return a


def gen_principal_comp_trans(images):
    """多チャネル画像群から主成分変換(固有ベクトル/固有値)を求める(gen_principal_comp_trans)。"""
    F = images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = _img(F)
    D = F.shape[-1]
    X = F.reshape(-1, D)
    mu = X.mean(0)
    cov = np.cov((X - mu).T)
    w, V = np.linalg.eigh(cov)
    order = np.argsort(w)[::-1]
    return {"mean": mu, "eigenvectors": V[:, order], "eigenvalues": w[order]}


def principal_comp(images):
    """PCA 変換を適用し主成分画像を返す(principal_comp)。"""
    F = images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = _img(F); H, W, D = F.shape
    pc = gen_principal_comp_trans(F)
    X = F.reshape(-1, D) - pc["mean"]
    proj = X @ pc["eigenvectors"]
    return proj.reshape(H, W, D)


def gen_canonical_variates_trans(images, labels):
    """クラス付き多チャネル画像から正準変量(LDA)変換を求める(gen_canonical_variates_trans)。"""
    F = images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = _img(F); D = F.shape[-1]
    X = F.reshape(-1, D); y = np.asarray(labels).ravel()
    mu = X.mean(0)
    Sw = np.zeros((D, D)); Sb = np.zeros((D, D))
    for c in np.unique(y):
        Xc = X[y == c]; muc = Xc.mean(0)
        Sw += (Xc - muc).T @ (Xc - muc)
        Sb += len(Xc) * np.outer(muc - mu, muc - mu)
    w, V = np.linalg.eig(np.linalg.pinv(Sw) @ Sb)
    order = np.argsort(w.real)[::-1]
    return {"mean": mu, "variates": V[:, order].real, "eigenvalues": w[order].real}


def inpainting_ced(image, region, iterations=300, sigma=1.0):
    """コヒーレンス強調拡散(構造テンソル方向へ拡散)でインペイント(inpainting_ced)。"""
    from scipy.ndimage import gaussian_filter
    im = _img(image).copy(); m = np.asarray(region, bool)
    for _ in range(int(iterations)):
        gy, gx = np.gradient(gaussian_filter(im, sigma))
        # 勾配に直交する方向へ優先拡散(等値線方向)
        lap_perp = (np.roll(im, 1, 0) + np.roll(im, -1, 0) + np.roll(im, 1, 1) + np.roll(im, -1, 1)
                    - 4 * im)
        im = np.where(m, im + 0.2 * lap_perp, im)
    return im


def inpainting_mcf(image, region, iterations=300, dt=0.1):
    """平均曲率流(Mean Curvature Flow)インペイント(inpainting_mcf)。
    穴を調和充填で初期化してから曲率流で等値線を滑らかにする(数値安定化)。"""
    im = _img(image).copy(); m = np.asarray(region, bool)
    # 調和(Laplace)事前充填で sharp 初期不連続を除去
    for _ in range(400):
        avg = 0.25 * (np.roll(im, 1, 0) + np.roll(im, -1, 0)
                      + np.roll(im, 1, 1) + np.roll(im, -1, 1))
        new = np.where(m, avg, im)
        if np.abs(new - im)[m].max() < 1e-6:
            im = new; break
        im = new
    # 曲率流(kappa をクランプして発散回避)
    for _ in range(int(iterations)):
        gy, gx = np.gradient(im)
        gxx = np.gradient(gx, axis=1); gyy = np.gradient(gy, axis=0)
        gxy = np.gradient(gx, axis=0)
        den = (gx ** 2 + gy ** 2) ** 1.5
        kappa = np.where(den > 1e-4, (gxx * gy ** 2 - 2 * gx * gy * gxy + gyy * gx ** 2) / (den + 1e-9), 0.0)
        kappa = np.clip(kappa, -1.0, 1.0)
        im = np.where(m, im + dt * kappa, im)
    return im


def inpainting_texture(image, region, patch=5, iterations=1):
    """テクスチャ合成インペイント(近傍既知パッチのコピー)(inpainting_texture)。"""
    im = _img(image).copy(); m = np.asarray(region, bool)
    from scipy.ndimage import distance_transform_edt
    idx = distance_transform_edt(m, return_distances=False, return_indices=True)
    filled = im[tuple(idx)]
    im[m] = filled[m]
    return im


def wiener_filter_ni(image, psf, noise=0.01):
    """非反復 Wiener 復元(wiener_filter_ni)。"""
    from filters_freq import wiener_filter
    return wiener_filter(image, psf, noise)


def exhaustive_match_mg(image, template, metric="sad"):
    """マルチグリッド全探索テンプレートマッチ(粗密で高速化)(exhaustive_match_mg)。"""
    from scipy.ndimage import zoom
    im = _img(image); t = _img(template)
    # 粗レベルで候補、細レベルで精緻化
    best = None
    for scale in (0.5, 1.0):
        i2 = zoom(im, scale, order=1); t2 = zoom(t, scale, order=1)
        H, W = i2.shape; th, tw = t2.shape
        if H <= th or W <= tw:
            continue
        rr = range(0, H - th, 1) if scale == 1.0 and best else range(0, H - th)
        cr = range(0, W - tw)
        best_local = None
        for r in range(0, H - th):
            for c in range(0, W - tw):
                patch = i2[r:r + th, c:c + tw]
                d = np.abs(patch - t2).sum() if metric == "sad" else ((patch - t2) ** 2).sum()
                if best_local is None or d < best_local[0]:
                    best_local = (d, r / scale, c / scale)
        best = best_local
    return {"row": best[1], "column": best[2], "score": best[0]} if best else None
