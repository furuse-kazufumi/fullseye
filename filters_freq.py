"""周波数領域/畳み込み/復元フィルタ(HALCON "Filters" chapter の genuine 実装, numpy).

FFT 畳み込み・相関・位相相関・Wiener 復元・調和補間・PSF 生成・Gabor エネルギー。
image = 2D float64。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


def convol_fft(image, filter_mask):
    """FFT による線形畳み込み(convol_fft/convol_image)。"""
    from scipy.signal import fftconvolve
    return fftconvolve(_img(image), _img(filter_mask), mode="same")


def convol_image(image, filter_mask):
    """空間畳み込み(convol_image)。"""
    from scipy.ndimage import convolve
    return convolve(_img(image), _img(filter_mask), mode="reflect")


def correlation_fft(image1, image2):
    """FFT による相互相関(correlation_fft)。"""
    a = _img(image1); b = _img(image2)
    F = np.fft.rfft2(a); G = np.fft.rfft2(b, s=a.shape)
    return np.fft.irfft2(F * np.conj(G), s=a.shape)


def phase_correlation_fft(image1, image2):
    """位相相関で並進 (drow, dcol) を推定(phase_correlation_fft)。"""
    a = _img(image1); b = _img(image2)
    F = np.fft.fft2(a); G = np.fft.fft2(b)
    R = F * np.conj(G)
    R /= np.abs(R) + 1e-12
    corr = np.fft.ifft2(R).real
    pk = np.unravel_index(np.argmax(corr), corr.shape)
    dr = pk[0] - (a.shape[0] if pk[0] > a.shape[0] // 2 else 0)
    dc = pk[1] - (a.shape[1] if pk[1] > a.shape[1] // 2 else 0)
    return {"row_shift": float(dr), "col_shift": float(dc),
            "peak": float(corr[pk]), "correlation": corr}


def gen_gauss_filter(sigma=1.0, size=None):
    """正規化 2D ガウスフィルタマスク(gen_gauss_filter)。"""
    s = float(sigma)
    n = int(size) if size else int(2 * np.ceil(3 * s) + 1)
    ax = np.arange(n) - (n - 1) / 2
    g = np.exp(-(ax[:, None] ** 2 + ax[None, :] ** 2) / (2 * s * s))
    return g / g.sum()


def gen_mean_filter(size=3):
    """平均(box)フィルタマスク(gen_mean_filter)。"""
    n = int(size)
    return np.ones((n, n)) / (n * n)


def gen_filter_mask(coeffs):
    """任意係数のフィルタマスクを生成(gen_filter_mask)。"""
    return _img(coeffs)


def gen_psf_motion(length=9, angle=0.0):
    """直線ブラー(モーション)PSF(gen_psf_motion)。"""
    L = int(length)
    psf = np.zeros((L, L))
    a = np.deg2rad(angle)
    c = (L - 1) / 2
    for t in np.linspace(-c, c, L * 4):
        r = int(round(c - t * np.sin(a))); col = int(round(c + t * np.cos(a)))
        if 0 <= r < L and 0 <= col < L:
            psf[r, col] = 1.0
    s = psf.sum()
    return psf / s if s > 0 else psf


def gen_psf_defocus(radius=3):
    """円形ボケ(デフォーカス)PSF(gen_psf_defocus)。"""
    r = int(radius); n = 2 * r + 1
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    psf = (xx * xx + yy * yy <= r * r).astype(float)
    return psf / psf.sum()


def gen_savitzky_golay_filter(size=5, order=2, deriv=0):
    """Savitzky-Golay 平滑/微分 1D フィルタ係数(gen_savitzky_golay_filter)。"""
    from scipy.signal import savgol_coeffs
    return savgol_coeffs(int(size), int(order), deriv=int(deriv))


def wiener_filter(image, psf, noise=0.01):
    """Wiener デコンボリューション(wiener_filter)。"""
    im = _img(image); h = _img(psf)
    H = np.fft.fft2(h, s=im.shape)
    Hn = H * np.exp(-2j * np.pi * (
        np.outer(np.fft.fftfreq(im.shape[0]), np.ones(im.shape[1])) * ((h.shape[0] - 1) / 2)
        + np.outer(np.ones(im.shape[0]), np.fft.fftfreq(im.shape[1])) * ((h.shape[1] - 1) / 2)))
    G = np.fft.fft2(im)
    W = np.conj(Hn) / (np.abs(Hn) ** 2 + float(noise))
    return np.fft.ifft2(G * W).real


def harmonic_interpolation(image, region):
    """穴(region=True)を Laplace 方程式(調和関数)で埋める(harmonic_interpolation)。"""
    im = _img(image).copy(); m = np.asarray(region, bool)
    for _ in range(500):
        avg = 0.25 * (np.roll(im, 1, 0) + np.roll(im, -1, 0)
                      + np.roll(im, 1, 1) + np.roll(im, -1, 1))
        new = np.where(m, avg, im)
        if np.abs(new - im)[m].max() < 1e-6:
            im = new; break
        im = new
    return im


def map_image(image, lut_map):
    """LUT (map) を画素に適用(map_image)。map は長さ N の 1D 配列。"""
    im = _img(image); lut = _img(lut_map); N = len(lut)
    idx = np.clip((im * (N - 1)).round().astype(int), 0, N - 1)
    return lut[idx]


def vector_field_length(vfield_row, vfield_col):
    """ベクトル場の各点の大きさ(vector_field_length)。"""
    return np.hypot(_img(vfield_row), _img(vfield_col))


def energy_gabor(image_real, image_imag):
    """Gabor 実/虚応答からエネルギー(振幅二乗)(energy_gabor)。"""
    return _img(image_real) ** 2 + _img(image_imag) ** 2
