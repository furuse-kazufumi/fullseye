"""オプティカルフロー/ベクトル場/帯域フィルタ(HALCON "Filters" chapter genuine, numpy).

密なオプティカルフロー(Horn-Schunck)・異方性拡散インペイント・周波数帯域マスク・
ベクトル場の微分と画像のワープ。歩行 Physical AI の視覚オドメトリ/地形知覚を支える。
image = 2D float64。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


def _hs_iterate(im1, im2, u, v, alpha, iterations):
    """1 スケールの Horn-Schunck 反復(u,v は初期流れ、warp 済み残差に対して更新)。"""
    from scipy.ndimage import convolve, map_coordinates
    rr, cc = np.mgrid[0:im1.shape[0], 0:im1.shape[1]].astype(float)
    warped = map_coordinates(im2, [rr + v, cc + u], order=1, mode="reflect")
    Ix = np.gradient(im1, axis=1); Iy = np.gradient(im1, axis=0)
    It = warped - im1
    du = np.zeros_like(im1); dv = np.zeros_like(im1)
    kernel = np.array([[1 / 12, 1 / 6, 1 / 12], [1 / 6, 0, 1 / 6], [1 / 12, 1 / 6, 1 / 12]])
    for _ in range(int(iterations)):
        ubar = convolve(du, kernel, mode="nearest")
        vbar = convolve(dv, kernel, mode="nearest")
        deriv = (Ix * ubar + Iy * vbar + It) / (alpha ** 2 + Ix ** 2 + Iy ** 2)
        du = ubar - Ix * deriv
        dv = vbar - Iy * deriv
    return u + du, v + dv


def optical_flow_mg(image1, image2, alpha=1.0, iterations=100, levels=4):
    """マルチグリッド(粗密ピラミッド + warping)Horn-Schunck 密オプティカルフロー
    を推定(optical_flow_mg)。大変位も復元。返り値 vfield {row, col}。"""
    from scipy.ndimage import zoom
    im1 = _img(image1); im2 = _img(image2)
    pyr1 = [im1]; pyr2 = [im2]
    for _ in range(int(levels) - 1):
        if min(pyr1[-1].shape) < 8:
            break
        pyr1.append(zoom(pyr1[-1], 0.5, order=1))
        pyr2.append(zoom(pyr2[-1], 0.5, order=1))
    u = np.zeros_like(pyr1[-1]); v = np.zeros_like(pyr1[-1])
    for lvl in range(len(pyr1) - 1, -1, -1):
        a, b = pyr1[lvl], pyr2[lvl]
        if u.shape != a.shape:
            sr = a.shape[0] / u.shape[0]; sc = a.shape[1] / u.shape[1]
            u = zoom(u, (sr, sc), order=1) * sc      # 流れは座標スケールに比例
            v = zoom(v, (sr, sc), order=1) * sr
        u, v = _hs_iterate(a, b, u, v, alpha, iterations)
    return {"row": v, "col": u}


def unwarp_image_vector_field(image, vfield_row, vfield_col):
    """ベクトル場に沿って画像をワープ(逆マッピング)(unwarp_image_vector_field)。"""
    from scipy.ndimage import map_coordinates
    im = _img(image)
    rr, cc = np.mgrid[0:im.shape[0], 0:im.shape[1]].astype(float)
    return map_coordinates(im, [rr + _img(vfield_row), cc + _img(vfield_col)], order=1, mode="reflect")


def derivate_vector_field(vfield_row, vfield_col, feature="divergence"):
    """ベクトル場の発散/回転/ヤコビアンを計算(derivate_vector_field)。"""
    vr = _img(vfield_row); vc = _img(vfield_col)
    dvr_dr = np.gradient(vr, axis=0); dvr_dc = np.gradient(vr, axis=1)
    dvc_dr = np.gradient(vc, axis=0); dvc_dc = np.gradient(vc, axis=1)
    if feature == "divergence":
        return dvc_dc + dvr_dr
    if feature == "curl":
        return dvc_dr - dvr_dc
    return {"div": dvc_dc + dvr_dr, "curl": dvc_dr - dvr_dc}


def gen_gauss_bandpass(shape, sigma_low, sigma_high):
    """周波数領域のガウス帯域通過マスクを生成(gen_gauss_bandpass)。"""
    H, W = shape
    fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None, :]
    r = np.sqrt(fx ** 2 + fy ** 2)
    lo = np.exp(-(r ** 2) / (2 * sigma_high ** 2))     # 高周波遮断
    hi = np.exp(-(r ** 2) / (2 * sigma_low ** 2))      # 低周波遮断
    return lo - hi


def gen_sin_bandpass(shape, freq_low, freq_high):
    """正弦窓の周波数帯域通過マスク(gen_sin_bandpass)。"""
    H, W = shape
    fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None, :]
    r = np.sqrt(fx ** 2 + fy ** 2)
    band = (r >= freq_low) & (r <= freq_high)
    out = np.zeros((H, W))
    span = max(freq_high - freq_low, 1e-6)
    out[band] = np.sin(np.pi * (r[band] - freq_low) / span)
    return out


def gen_std_bandpass(shape, freq_low, freq_high, order=2):
    """Butterworth 型の帯域通過マスク(gen_std_bandpass)。"""
    H, W = shape
    fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None, :]
    r = np.sqrt(fx ** 2 + fy ** 2) + 1e-12
    center = (freq_low + freq_high) / 2
    width = max(freq_high - freq_low, 1e-6)
    return 1.0 / (1.0 + ((r ** 2 - center ** 2) / (r * width)) ** (2 * order))


def apply_bandpass(image, mask):
    """周波数マスクを画像に適用(FFT 領域フィルタ)(apply_bandpass)。"""
    im = _img(image)
    F = np.fft.fft2(im)
    return np.fft.ifft2(F * np.asarray(mask)).real


def convol_channels(image, filter_mask):
    """多チャネル画像を各チャネル畳み込み(convol_channels)。image=(H,W,C) or 2D。"""
    from scipy.ndimage import convolve
    im = _img(image); k = _img(filter_mask)
    if im.ndim == 2:
        return convolve(im, k, mode="reflect")
    return np.stack([convolve(im[..., c], k, mode="reflect") for c in range(im.shape[-1])], axis=-1)


def inpainting_aniso(image, region, iterations=200, kappa=0.1, gamma=0.2):
    """異方性拡散(Perona-Malik)で欠損領域を修復(inpainting_aniso)。
    region=True の画素を周囲からエッジ保存拡散で埋める。"""
    im = _img(image).copy(); m = np.asarray(region, bool)
    for _ in range(int(iterations)):
        dn = np.roll(im, -1, 0) - im; ds = np.roll(im, 1, 0) - im
        de = np.roll(im, -1, 1) - im; dw = np.roll(im, 1, 1) - im
        cn = np.exp(-(dn / kappa) ** 2); cs = np.exp(-(ds / kappa) ** 2)
        ce = np.exp(-(de / kappa) ** 2); cw = np.exp(-(dw / kappa) ** 2)
        upd = gamma * (cn * dn + cs * ds + ce * de + cw * dw)
        im = np.where(m, im + upd, im)
    return im


def inpainting_ct(image, region, iterations=300):
    """コヒーレンス輸送に近い等方拡散インペイント(inpainting_ct)。
    穴を Laplace 拡散で埋める(境界条件保持)。"""
    im = _img(image).copy(); m = np.asarray(region, bool)
    for _ in range(int(iterations)):
        avg = 0.25 * (np.roll(im, 1, 0) + np.roll(im, -1, 0)
                      + np.roll(im, 1, 1) + np.roll(im, -1, 1))
        im = np.where(m, avg, im)
    return im
