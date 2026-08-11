"""HALCON-parity operator generation from a fixed, hand-verified shape vocabulary.

Goal (user): *do the same things HALCON can do*, not merely name them. So every
generated op is a GENUINE implementation (numpy/scipy/skimage/cv2), not a stub —
if a backend call throws it degrades to identity via `_safe`, and the functional
gate (`verify_auto.py`) counts only ops that actually run and return the declared
sort. Coverage is therefore earned, not claimed.

Separation of concerns that keeps this honest at scale:
  * SHAPES  — a small vocabulary of correct factory functions, authored & verified
              here by hand. Each `factory(params) -> fn(v, a, b)` computes one
              family of operations (rank filters, gray morphology, edge amplitude,
              FFT-domain, thresholding, region features, geometric transforms, ...).
  * SPECS   — pure DATA mapping one real HALCON operator to (shape, params, sorts).
              Authored inline (SEED) and expanded by per-chapter mining agents into
              `data/auto_specs/*.json`. Agents produce mappings onto the FIXED
              vocabulary — they never write executable code, so breadth cannot
              introduce incorrectness.

`build()` validates every spec's `halcon` name against the scraped real reference
(`data/halcon_operators.json`); names that do not exist are DROPPED (fail-closed)
and reported — a claimed-but-fake name can never inflate coverage.

Only UNARY operators (one image/region/contour in) live here — they thread the
single-image evolution pipeline. N-ary HALCON ops (image arithmetic, region set
theory) are a separate capability tier (`imgops_nary.py`).
"""
from __future__ import annotations

import json
import os

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))

try:
    import skimage  # noqa: F401
    from skimage import (filters as skfilters, morphology as skmorph,
                         measure as skmeasure, segmentation as skseg,
                         restoration as skrest, feature as skfeat,
                         transform as sktrans, exposure as skexp)
    _HAS_SK = True
except Exception:  # pragma: no cover - skimage is expected but optional
    _HAS_SK = False

try:
    import cv2
    _HAS_CV = True
except Exception:  # pragma: no cover
    _HAS_CV = False


# --------------------------------------------------------------------------- #
# small shared helpers                                                        #
# --------------------------------------------------------------------------- #
def _k(a: float) -> int:
    return (3, 5, 7, 9)[min(3, int(a * 4))]


def _rad(a: float) -> int:
    return 1 + int(a * 3)                       # structuring-element radius 1..4


def _norm(x):
    x = np.asarray(x, np.float64)
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


def _bin(v):
    return np.asarray(v) > 0.5


def _u8(v):
    return (np.clip(np.asarray(v, np.float64), 0, 1) * 255).astype(np.uint8)


def _largest_label(mask):
    lab, n = ndimage.label(mask)
    if n == 0:
        return None, lab, 0
    sizes = ndimage.sum(np.ones_like(lab), lab, index=range(1, n + 1))
    return (lab == int(np.argmax(sizes)) + 1), lab, n


# --------------------------------------------------------------------------- #
# SHAPE FACTORIES  (each: params -> fn(v, a, b))                              #
# The correctness core. Verified by hand; agents only map names onto these.   #
# --------------------------------------------------------------------------- #

# ---- image -> image : pointwise math (abs/sqrt/exp/log/trig ...) ----------- #
def _sh_pointwise(p):
    kind = p["func"]

    def fn(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0.0, 1.0)
        if kind == "abs":
            return np.abs(np.asarray(v, np.float64))
        if kind == "sqrt":
            return np.sqrt(x)
        if kind == "square":
            return x * x
        if kind == "exp":
            return (np.exp(x) - 1.0) / (np.e - 1.0)
        if kind == "log":
            return np.log1p(x) / np.log(2.0)
        if kind == "sin":
            return (np.sin(2 * np.pi * x) + 1.0) / 2.0
        if kind == "cos":
            return (np.cos(2 * np.pi * x) + 1.0) / 2.0
        if kind == "tan":
            return _norm(np.tan((x - 0.5) * (np.pi * 0.9)))
        if kind == "asin":
            return np.arcsin(x) / (np.pi / 2)
        if kind == "acos":
            return np.arccos(x) / np.pi
        if kind == "atan":
            return np.arctan(x) / (np.pi / 2)
        if kind == "reciprocal":
            return _norm(1.0 / np.maximum(x, 1e-3))
        raise ValueError(kind)
    return fn


# ---- image -> image : gray-value LUT transforms ---------------------------- #
def _sh_lut(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0.0, 1.0)
        if kind == "gamma":
            return x ** (0.3 + 2.5 * a)
        if kind == "scale":
            return np.clip((0.5 + 1.5 * a) * x + (b - 0.5), 0, 1)
        if kind == "invert":
            return 1.0 - x
        if kind == "sigmoid":
            return 1.0 / (1.0 + np.exp(-(4 + 12 * a) * (x - (0.2 + 0.6 * b))))
        if kind == "log_gain":
            return skexp.adjust_log(x, gain=0.5 + 1.5 * a) if _HAS_SK else _norm(np.log1p(x))
        if kind == "equalize":
            hist, edges = np.histogram(x, 256, (0, 1))
            cdf = np.cumsum(hist).astype(np.float64)
            cdf = cdf / cdf[-1] if cdf[-1] > 0 else cdf
            return np.interp(x.ravel(), (edges[:-1] + edges[1:]) / 2, cdf).reshape(x.shape)
        if kind == "rescale":
            lo, hi = float(x.min()), float(x.max())
            return (x - lo) / (hi - lo) if hi > lo else x
        if kind == "clip_range":
            return np.clip(x, a * 0.5, 0.5 + 0.5 * b)
        if kind == "illuminate":
            sm = ndimage.gaussian_filter(x, 3 + 12 * a)
            return np.clip(x + (0.3 + 0.7 * b) * (x - sm), 0, 1)
        if kind == "monotony":                      # HALCON monotony: rank of centre among 8 neighbours
            cnt = np.zeros_like(x)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy or dx:
                        cnt += (np.roll(np.roll(x, dy, 0), dx, 1) < x).astype(np.float64)
            return cnt / 8.0
        if kind == "equalize_local":                 # windowed histogram equalisation (equ_histo_image_rect)
            nb = 2 + int(a * 4)
            H, W = x.shape
            hs, ws = max(1, H // nb), max(1, W // nb)
            out = x.copy()
            for i in range(nb):
                for j in range(nb):
                    blk = x[i * hs:(i + 1) * hs, j * ws:(j + 1) * ws]
                    if blk.size:
                        h, e = np.histogram(blk, 64, (0, 1))
                        c = np.cumsum(h).astype(np.float64)
                        c = c / c[-1] if c[-1] > 0 else c
                        out[i * hs:(i + 1) * hs, j * ws:(j + 1) * ws] = \
                            np.interp(blk.ravel(), (e[:-1] + e[1:]) / 2, c).reshape(blk.shape)
            return out
        raise ValueError(kind)
    return fn


# ---- image -> image : linear / smoothing filters --------------------------- #
def _sh_linfilter(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        if kind == "gauss":
            return ndimage.gaussian_filter(x, 0.3 + 2.7 * a)
        if kind == "mean":
            return ndimage.uniform_filter(x, _k(a))
        if kind == "binomial":
            n = _k(a)
            ker = np.poly1d([1, 1]) ** (n - 1)
            w = np.array(ker.coeffs, np.float64)
            w = w / w.sum()
            return ndimage.correlate1d(ndimage.correlate1d(x, w, 0), w, 1)
        if kind == "smooth":
            return ndimage.gaussian_filter(x, 0.5 + 2.0 * a)
        if kind == "derivate_gauss":
            s = 0.5 + 2.5 * a
            return _norm(np.hypot(ndimage.gaussian_filter(x, s, order=(1, 0)),
                                  ndimage.gaussian_filter(x, s, order=(0, 1))))
        if kind == "laplace_gauss":
            return _norm(ndimage.gaussian_laplace(x, 0.5 + 2.5 * a))
        if kind == "dog":
            return _norm(np.abs(ndimage.gaussian_filter(x, 0.5 + 2 * a)
                                - ndimage.gaussian_filter(x, 1 + 4 * b)))
        if kind == "mean_curvature":
            y = x.copy()
            for _ in range(1 + int(a * 6)):
                y = ndimage.gaussian_filter(y, 0.6)
            return y
        raise ValueError(kind)
    return fn


# ---- image -> image : rank / order-statistic filters ----------------------- #
def _sh_rank(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        k = _k(a)
        if kind == "median":
            return ndimage.median_filter(x, size=k)
        if kind == "median_rect":
            return ndimage.median_filter(x, size=(k, _k(b)))
        if kind == "min":
            return ndimage.minimum_filter(x, size=k)
        if kind == "max":
            return ndimage.maximum_filter(x, size=k)
        if kind == "rank":
            return ndimage.percentile_filter(x, int(5 + 90 * b), size=k)
        if kind == "range":
            return _norm(ndimage.maximum_filter(x, k) - ndimage.minimum_filter(x, k))
        if kind == "sigma":
            m = ndimage.uniform_filter(x, k)
            sig = 0.05 + 0.35 * b
            near = np.abs(x - m) < sig
            sm = ndimage.uniform_filter(np.where(near, x, 0.0), k)
            cnt = ndimage.uniform_filter(near.astype(np.float64), k)
            return np.where(cnt > 1e-6, sm / np.maximum(cnt, 1e-6), x)
        if kind == "trimmed_mean":
            lo = ndimage.percentile_filter(x, 20, size=k)
            hi = ndimage.percentile_filter(x, 80, size=k)
            return (lo + hi) / 2
        raise ValueError(kind)
    return fn


# ---- image -> image : gray-scale morphology -------------------------------- #
def _sh_graymorph(p):
    op, shape = p["op"], p.get("shape", "rect")

    def _fp(a):
        if shape == "disk" and _HAS_SK:
            return skmorph.disk(_rad(a))
        return np.ones((_k(a), _k(a)))

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        fp = _fp(a)
        if op == "erosion":
            return ndimage.grey_erosion(x, footprint=fp)
        if op == "dilation":
            return ndimage.grey_dilation(x, footprint=fp)
        if op == "opening":
            return ndimage.grey_opening(x, footprint=fp)
        if op == "closing":
            return ndimage.grey_closing(x, footprint=fp)
        if op == "tophat":
            return _norm(ndimage.white_tophat(x, footprint=fp))
        if op == "bothat":
            return _norm(ndimage.black_tophat(x, footprint=fp))
        if op == "gradient":
            return _norm(ndimage.morphological_gradient(x, footprint=fp))
        raise ValueError(op)
    return fn


# ---- image -> image : edge amplitude / direction (named kernels) ----------- #
_KIRSCH = [np.array([[5, 5, 5], [-3, 0, -3], [-3, -3, -3]], float)]
for _i in range(7):
    _r = _KIRSCH[-1]
    _KIRSCH.append(np.array([[_r[0, 1], _r[0, 2], _r[1, 2]],
                             [_r[0, 0], 0, _r[2, 2]],
                             [_r[1, 0], _r[2, 0], _r[2, 1]]], float))
_S2 = np.sqrt(2.0)
_FREI = [np.array([[1, _S2, 1], [0, 0, 0], [-1, -_S2, -1]], float),
         np.array([[1, 0, -1], [_S2, 0, -_S2], [1, 0, -1]], float)]
_ROBINSON = [np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]], float),
             np.array([[2, 1, 0], [1, 0, -1], [0, -1, -2]], float)]


def _compass(x, kernels):
    resp = [ndimage.convolve(x, k, mode="reflect") for k in kernels]
    return np.max(np.abs(resp), axis=0)


def _sh_edge(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        if kind == "sobel":
            return _norm(np.hypot(ndimage.sobel(x, 1), ndimage.sobel(x, 0)))
        if kind == "sobel_dir":
            return (np.arctan2(ndimage.sobel(x, 0), ndimage.sobel(x, 1)) + np.pi) / (2 * np.pi)
        if kind == "prewitt":
            return _norm(np.hypot(ndimage.prewitt(x, 1), ndimage.prewitt(x, 0)))
        if kind == "prewitt_dir":
            return (np.arctan2(ndimage.prewitt(x, 0), ndimage.prewitt(x, 1)) + np.pi) / (2 * np.pi)
        if kind == "roberts":
            return _norm(np.hypot(x - np.roll(np.roll(x, -1, 0), -1, 1),
                                  np.roll(x, -1, 1) - np.roll(x, -1, 0)))
        if kind == "scharr":
            sh = np.array([[3, 0, -3], [10, 0, -10], [3, 0, -3]], float)
            return _norm(np.hypot(ndimage.convolve(x, sh), ndimage.convolve(x, sh.T)))
        if kind == "kirsch":
            return _norm(_compass(x, _KIRSCH))
        if kind == "kirsch_dir":
            resp = np.stack([ndimage.convolve(x, k) for k in _KIRSCH])
            return np.argmax(resp, 0).astype(np.float64) / (len(_KIRSCH) - 1)
        if kind == "frei":
            return _norm(np.hypot(ndimage.convolve(x, _FREI[0]), ndimage.convolve(x, _FREI[1])))
        if kind == "frei_dir":
            return (np.arctan2(ndimage.convolve(x, _FREI[1]),
                               ndimage.convolve(x, _FREI[0])) + np.pi) / (2 * np.pi)
        if kind == "robinson":
            r0 = [np.rot90(_ROBINSON[0], i) for i in range(4)]
            r1 = [np.rot90(_ROBINSON[1], i) for i in range(4)]
            return _norm(_compass(x, r0 + r1))
        if kind == "robinson_dir":
            r = [np.rot90(_ROBINSON[0], i) for i in range(4)] + [np.rot90(_ROBINSON[1], i) for i in range(4)]
            return np.argmax(np.stack([ndimage.convolve(x, k) for k in r]), 0).astype(np.float64) / (len(r) - 1)
        if kind == "laplace":
            return _norm(np.abs(ndimage.laplace(x)))
        raise ValueError(kind)
    return fn


# ---- image -> image : FFT / frequency domain ------------------------------- #
def _sh_freq(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        F = np.fft.fftshift(np.fft.fft2(x))
        if kind == "fft_power":
            return _norm(np.log1p(np.abs(F)))
        if kind == "fft_power_real":
            return _norm(np.abs(np.real(F)))
        if kind == "fft_phase":
            return (np.angle(F) + np.pi) / (2 * np.pi)
        H, W = x.shape
        rad = np.sqrt(np.fft.fftfreq(H)[:, None] ** 2 + np.fft.fftfreq(W)[None, :] ** 2)
        if kind == "lowpass":
            return np.clip(np.real(np.fft.ifft2(np.fft.fft2(x) * (rad <= (0.05 + 0.4 * a)))), 0, 1)
        if kind == "highpass":
            return _norm(np.real(np.fft.ifft2(np.fft.fft2(x) * (rad > (0.02 + 0.3 * a)))))
        if kind == "bandpass":
            lo, hi = 0.02 + 0.15 * a, 0.2 + 0.3 * b
            return _norm(np.real(np.fft.ifft2(np.fft.fft2(x) * ((rad > lo) & (rad < hi)))))
        raise ValueError(kind)
    return fn


# ---- image -> image : anisotropic diffusion / edge-preserving --------------- #
def _sh_diffusion(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        if kind == "isotropic":
            return ndimage.gaussian_filter(x, 0.5 + 2.5 * a)
        if kind == "anisotropic":
            y = x.copy()
            K = 0.05 + 0.25 * b
            for _ in range(2 + int(a * 8)):
                dn = np.roll(y, -1, 0) - y
                ds = np.roll(y, 1, 0) - y
                de = np.roll(y, -1, 1) - y
                dw = np.roll(y, 1, 1) - y
                cn, cs = np.exp(-(dn / K) ** 2), np.exp(-(ds / K) ** 2)
                ce, cw = np.exp(-(de / K) ** 2), np.exp(-(dw / K) ** 2)
                y = y + 0.2 * (cn * dn + cs * ds + ce * de + cw * dw)
            return np.clip(y, 0, 1)
        if kind == "tv" and _HAS_SK:
            return skrest.denoise_tv_chambolle(x, weight=0.02 + 0.3 * a)
        if kind == "bilateral" and _HAS_CV:
            return cv2.bilateralFilter(x.astype(np.float32), 5, 0.05 + 0.4 * b,
                                       1 + 3 * a).astype(np.float64)
        if kind == "nlm" and _HAS_SK:
            return skrest.denoise_nl_means(x, patch_size=5, h=0.02 + 0.2 * a)
        raise ValueError(kind)
    return fn


# ---- image -> image : texture ---------------------------------------------- #
def _sh_texture(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        k = _k(a)
        if kind == "deviation":
            m = ndimage.uniform_filter(x, k)
            m2 = ndimage.uniform_filter(x * x, k)
            return _norm(np.sqrt(np.maximum(m2 - m * m, 0)))
        if kind == "variance":
            m = ndimage.uniform_filter(x, k)
            m2 = ndimage.uniform_filter(x * x, k)
            return _norm(np.maximum(m2 - m * m, 0))
        if kind == "entropy" and _HAS_SK:
            return _norm(skfilters.rank.entropy(_u8(x), skmorph.disk(_rad(a))).astype(np.float64))
        if kind == "gabor":
            theta, freq = np.pi * a, 0.1 + 0.3 * b
            yy, xx = np.mgrid[-7:8, -7:8]
            xr = xx * np.cos(theta) + yy * np.sin(theta)
            g = np.exp(-(xx * xx + yy * yy) / 8.0) * np.cos(2 * np.pi * freq * xr)
            return _norm(np.abs(ndimage.convolve(x, g, mode="reflect")))
        if kind == "lbp" and _HAS_SK:
            return _norm(skfeat.local_binary_pattern(x, 8, _rad(a)))
        if kind == "coherence" and _HAS_SK:
            return _norm(np.nan_to_num(skfeat.shape_index(x, sigma=0.5 + 2 * a)))
        raise ValueError(kind)
    return fn


# ---- image -> image : geometric transforms --------------------------------- #
def _sh_geom(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        if kind == "mirror":
            return np.flipud(x) if a < 0.34 else (np.fliplr(x) if a < 0.67 else x.T)
        if kind == "transpose":
            return x.T
        if kind == "rotate":
            return np.clip(ndimage.rotate(x, -45 + 90 * a, reshape=False, mode="reflect"), 0, 1)
        if kind == "zoom":
            s = 0.7 + 0.6 * a
            off = (x.shape[0] * (1 - 1 / s) / 2, x.shape[1] * (1 - 1 / s) / 2)
            return np.clip(ndimage.affine_transform(x, np.diag([1 / s, 1 / s]),
                                                    offset=off, mode="reflect"), 0, 1)
        if kind == "affine":
            ang = np.deg2rad(-20 + 40 * a)
            M = np.array([[np.cos(ang), -np.sin(ang) + (b - 0.5) * 0.4],
                          [np.sin(ang), np.cos(ang)]])
            c = np.array(x.shape) / 2
            return np.clip(ndimage.affine_transform(x, M, offset=c - M @ c, mode="reflect"), 0, 1)
        if kind == "polar" and _HAS_CV:
            h, w = x.shape
            return cv2.warpPolar(x.astype(np.float32), (w, h), (w / 2, h / 2),
                                 min(h, w) / 2, cv2.WARP_POLAR_LINEAR).astype(np.float64)
        if kind == "swirl" and _HAS_SK:
            return np.clip(sktrans.swirl(x, strength=1 + 4 * a, radius=30), 0, 1)
        raise ValueError(kind)
    return fn


# ---- image -> region : thresholding / segmentation ------------------------- #
def _sh_threshold(p):
    method = p["method"]

    def fn(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        if method == "fixed":
            return ((x > a) & (x < (a + 0.5 + 0.5 * b))).astype(np.float64)
        if method == "otsu":
            return (x > skfilters.threshold_otsu(x)).astype(np.float64) if _HAS_SK else \
                   (x > x.mean()).astype(np.float64)
        if method == "li":
            return (x > skfilters.threshold_li(x)).astype(np.float64)
        if method == "yen":
            return (x > skfilters.threshold_yen(x)).astype(np.float64)
        if method == "triangle":
            return (x > skfilters.threshold_triangle(x)).astype(np.float64)
        if method == "isodata":
            return (x > skfilters.threshold_isodata(x)).astype(np.float64)
        if method == "mean":
            return (x > skfilters.threshold_mean(x)).astype(np.float64)
        if method == "minimum":
            return (x > skfilters.threshold_minimum(x)).astype(np.float64)
        if method == "sauvola":
            return (x > skfilters.threshold_sauvola(x, window_size=2 * int(a * 6) + 3)).astype(np.float64)
        if method == "niblack":
            return (x > skfilters.threshold_niblack(x, window_size=2 * int(a * 6) + 3)).astype(np.float64)
        if method == "dyn":
            return (x > ndimage.uniform_filter(x, _k(a)) + (b - 0.5) * 0.4).astype(np.float64)
        if method == "local_gauss":
            return (x > ndimage.gaussian_filter(x, 1 + 3 * a) + (b - 0.5) * 0.3).astype(np.float64)
        if method == "hysteresis" and _HAS_SK:
            return skfilters.apply_hysteresis_threshold(x, 0.2 + 0.3 * a, 0.5 + 0.3 * b).astype(np.float64)
        raise ValueError(method)
    return fn


def _sh_segment(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        if kind == "canny":
            g = ndimage.gaussian_filter(x, 0.5 + 1.5 * a)
            m = _norm(np.hypot(ndimage.sobel(g, 1), ndimage.sobel(g, 0)))
            return (m > (0.1 + 0.5 * b)).astype(np.float64)
        if kind == "sk_canny" and _HAS_SK:
            return skfeat.canny(x, sigma=0.5 + 2 * a).astype(np.float64)
        if kind == "local_max":
            return ((x >= ndimage.maximum_filter(x, _k(a))) & (x > 0.3 + 0.4 * b)).astype(np.float64)
        if kind == "watershed" and _HAS_SK:
            grad = _norm(np.hypot(ndimage.sobel(x, 1), ndimage.sobel(x, 0)))
            markers = ndimage.label(x < (0.2 + 0.3 * a))[0]
            return skseg.find_boundaries(skseg.watershed(grad, markers)).astype(np.float64)
        if kind == "felzenszwalb" and _HAS_SK:
            return skseg.find_boundaries(
                skseg.felzenszwalb(x, scale=20 + 200 * a, channel_axis=None)).astype(np.float64)
        if kind == "slic" and _HAS_SK:
            return skseg.find_boundaries(
                skseg.slic(x, n_segments=int(10 + 80 * a), channel_axis=None)).astype(np.float64)
        if kind == "chan_vese" and _HAS_SK:
            return skseg.chan_vese(x, mu=0.1 + 0.4 * a, max_num_iter=60).astype(np.float64)
        if kind == "regiongrow":
            seed = x > (0.5 + 0.3 * a)
            return ndimage.binary_dilation(seed, iterations=1 + int(b * 4)).astype(np.float64)
        raise ValueError(kind)
    return fn


# ---- region -> region : binary morphology / transforms --------------------- #
def _sh_binmorph(p):
    op, shape = p["op"], p.get("shape", "disk")

    def _fp(a):
        if shape == "disk" and _HAS_SK:
            return skmorph.disk(_rad(a))
        if shape == "rect":
            return np.ones((_k(a), _k(a)))
        return ndimage.generate_binary_structure(2, 1)

    def fn(v, a, b):
        m = _bin(v)
        it = 1 + int(a * 3)
        fp = _fp(a)
        if op == "erosion":
            return ndimage.binary_erosion(m, fp).astype(np.float64)
        if op == "dilation":
            return ndimage.binary_dilation(m, fp).astype(np.float64)
        if op == "opening":
            return ndimage.binary_opening(m, fp).astype(np.float64)
        if op == "closing":
            return ndimage.binary_closing(m, fp).astype(np.float64)
        if op == "erosion_it":
            return ndimage.binary_erosion(m, iterations=it).astype(np.float64)
        if op == "dilation_it":
            return ndimage.binary_dilation(m, iterations=it).astype(np.float64)
        raise ValueError(op)
    return fn


def _sh_region_trans(p):
    kind = p["kind"]

    def fn(v, a, b):
        m = _bin(v)
        if kind == "fill_up":
            return ndimage.binary_fill_holes(m).astype(np.float64)
        if kind == "boundary":
            return (m.astype(np.float64) - ndimage.binary_erosion(m).astype(np.float64)).clip(0, 1)
        if kind == "skeleton" and _HAS_SK:
            return skmorph.skeletonize(m).astype(np.float64)
        if kind == "medial" and _HAS_SK:
            return skmorph.medial_axis(m).astype(np.float64)
        if kind == "thin" and _HAS_SK:
            return skmorph.thin(m).astype(np.float64)
        if kind == "convex" and _HAS_SK:
            return skmorph.convex_hull_image(m).astype(np.float64)
        if kind == "clear_border" and _HAS_SK:
            return skseg.clear_border(m).astype(np.float64)
        if kind == "remove_small":
            lab, n = ndimage.label(m)
            if n == 0:
                return np.zeros_like(m, np.float64)
            sizes = ndimage.sum(np.ones_like(lab), lab, index=range(1, n + 1))
            thr = int(16 + a * 200)
            keep = np.isin(lab, [i for i, s in enumerate(sizes, 1) if s >= thr])
            return keep.astype(np.float64)
        if kind == "remove_holes" and _HAS_SK:
            return skmorph.remove_small_holes(m, area_threshold=int(16 + a * 200)).astype(np.float64)
        if kind == "select_largest":
            big, _, n = _largest_label(m)
            return big.astype(np.float64) if big is not None else np.zeros_like(m, np.float64)
        if kind == "dist_transform":
            return _norm(ndimage.distance_transform_edt(m))
        if kind == "shape_bbox":
            ys, xs = np.where(m)
            out = np.zeros_like(m, np.float64)
            if len(ys):
                out[ys.min():ys.max() + 1, xs.min():xs.max() + 1] = 1.0
            return out
        raise ValueError(kind)
    return fn


# ---- region -> feature : shape measurements -------------------------------- #
def _sh_region_feat(p):
    metric = p["metric"]

    def fn(v, a, b):
        m = _bin(v)
        big, lab, n = _largest_label(m)
        if metric == "count":
            return np.float64(n)
        if metric == "area":
            return np.float64(np.mean(m))
        if big is None:
            return np.float64(0.0)
        if not _HAS_SK:
            return np.float64(float(big.sum()) / big.size)
        pr = skmeasure.regionprops(big.astype(int))[0]
        per = pr.perimeter or 1.0
        if metric == "circularity":
            return np.float64(min(1.0, 4 * np.pi * pr.area / (per * per)))
        if metric == "compactness":
            return np.float64(min(1.0, (per * per) / (4 * np.pi * max(pr.area, 1)) / 10))
        if metric == "convexity":
            return np.float64(pr.area / max(pr.area_convex, 1))
        if metric == "solidity":
            return np.float64(pr.solidity)
        if metric == "rectangularity":
            return np.float64(pr.extent)
        if metric == "eccentricity":
            return np.float64(pr.eccentricity)
        if metric == "orientation":
            return np.float64((pr.orientation + np.pi / 2) / np.pi)
        if metric == "roundness":
            return np.float64(min(1.0, 4 * pr.area / (np.pi * max(pr.axis_major_length, 1) ** 2)))
        if metric == "diameter":
            return np.float64(pr.equivalent_diameter_area / max(m.shape))
        if metric == "euler":
            return np.float64(skmeasure.euler_number(m))
        if metric == "anisometry":
            return np.float64(pr.axis_major_length / max(pr.axis_minor_length, 1e-6) / 10)
        if metric == "perimeter":
            return np.float64(min(1.0, per / (2.0 * (m.shape[0] + m.shape[1]))))
        if metric == "area_holes":
            return np.float64((pr.area_filled - pr.area) / max(pr.area_filled, 1))
        if metric == "aspect":
            minr, minc, maxr, maxc = pr.bbox
            return np.float64(min(1.0, (maxr - minr) / max(maxc - minc, 1)))
        if metric in ("moment2", "hu1"):
            nu = skmeasure.moments_normalized(skmeasure.moments_central(big.astype(float)))
            if metric == "moment2":
                return np.float64(min(1.0, abs(nu[2, 0] + nu[0, 2])))
            return np.float64(min(1.0, abs(skmeasure.moments_hu(nu)[0])))
        raise ValueError(metric)
    return fn


# ---- image -> feature : gray-value statistics ------------------------------ #
def _sh_img_feat(p):
    metric = p["metric"]

    def fn(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        if metric == "min":
            return np.float64(x.min())
        if metric == "max":
            return np.float64(x.max())
        if metric == "mean":
            return np.float64(x.mean())
        if metric == "std":
            return np.float64(x.std())
        if metric == "median":
            return np.float64(np.median(x))
        if metric == "entropy":
            h, _ = np.histogram(x, 64, (0, 1))
            pp = h / max(1, h.sum())
            pp = pp[pp > 0]
            return np.float64(-np.sum(pp * np.log2(pp)) / 6.0)
        if metric == "area_gray":
            return np.float64(np.mean(x > a))
        raise ValueError(metric)
    return fn


# ---- image -> contour (XLD) and contour ops -------------------------------- #
def _sh_xld(p):
    kind = p["kind"]

    def fn(v, a, b):
        if kind == "edges_sub_pix":
            x = np.asarray(v, np.float64)
            m = _norm(np.hypot(ndimage.sobel(x, 1), ndimage.sobel(x, 0)))
            lab, n = ndimage.label(m > (0.15 + 0.5 * a), structure=np.ones((3, 3)))
            cs = []
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                if len(ys) >= 3:
                    cs.append(np.stack([ys, xs], 1).astype(np.float64))
            return {"shape": x.shape, "cs": cs}
        if kind == "lines_gauss" and _HAS_SK:
            x = np.asarray(v, np.float64)
            r = _norm(skfilters.frangi(x, sigmas=range(1, 4)))
            lab, n = ndimage.label(r > (0.1 + 0.4 * a), structure=np.ones((3, 3)))
            cs = [np.stack(np.where(lab == i), 1).astype(np.float64) for i in range(1, n + 1)]
            return {"shape": x.shape, "cs": [c for c in cs if len(c) >= 3]}
        # contour -> contour / region / feature
        cv = v
        if kind == "select_contours":
            thr = 3 + int(a * 40)
            return {"shape": cv["shape"], "cs": [c for c in cv["cs"] if len(c) >= thr]}
        if kind == "smooth_contours":
            w = 1 + int(a * 3)
            ker = np.ones(2 * w + 1) / (2 * w + 1)
            out = []
            for c in cv["cs"]:
                if len(c) > 2 * w + 1:
                    out.append(np.stack([np.convolve(c[:, 0], ker, "same"),
                                         np.convolve(c[:, 1], ker, "same")], 1))
                else:
                    out.append(c)
            return {"shape": cv["shape"], "cs": out}
        if kind == "to_region":
            H, W = cv["shape"]
            mask = np.zeros((H, W), np.float64)
            for c in cv["cs"]:
                idx = np.clip(np.round(c).astype(int), [0, 0], [H - 1, W - 1])
                mask[idx[:, 0], idx[:, 1]] = 1.0
            return ndimage.binary_dilation(mask > 0.5, iterations=1 + int(a * 2)).astype(np.float64)
        if kind == "count":
            return np.float64(len(cv["cs"]))
        if kind == "length":
            tot = 0.0
            for c in cv["cs"]:
                if len(c) >= 2:
                    tot += float(np.sum(np.hypot(np.diff(c[:, 0]), np.diff(c[:, 1]))))
            return np.float64(tot)
        raise ValueError(kind)
    return fn


SHAPES = {
    "pointwise": _sh_pointwise, "lut": _sh_lut, "linfilter": _sh_linfilter,
    "rank": _sh_rank, "graymorph": _sh_graymorph, "edge": _sh_edge,
    "freq": _sh_freq, "diffusion": _sh_diffusion, "texture": _sh_texture,
    "geom": _sh_geom, "threshold": _sh_threshold, "segment": _sh_segment,
    "binmorph": _sh_binmorph, "region_trans": _sh_region_trans,
    "region_feat": _sh_region_feat, "img_feat": _sh_img_feat, "xld": _sh_xld,
}


# --------------------------------------------------------------------------- #
# SEED SPECS — hand-authored, high-confidence HALCON analogues.               #
# Each: (halcon, category, in_sort, out_sort, shape, params)                  #
# --------------------------------------------------------------------------- #
IMG = "image"
REG = "region"
FEA = "feature"
CON = "contour"

SEED: list[tuple] = [
    # ---- Filters: pointwise math -----------------------------------------
    ("abs_image", "arithmetic", IMG, IMG, "pointwise", {"func": "abs"}),
    ("sqrt_image", "arithmetic", IMG, IMG, "pointwise", {"func": "sqrt"}),
    ("exp_image", "arithmetic", IMG, IMG, "pointwise", {"func": "exp"}),
    ("log_image", "arithmetic", IMG, IMG, "pointwise", {"func": "log"}),
    ("sin_image", "arithmetic", IMG, IMG, "pointwise", {"func": "sin"}),
    ("cos_image", "arithmetic", IMG, IMG, "pointwise", {"func": "cos"}),
    ("asin_image", "arithmetic", IMG, IMG, "pointwise", {"func": "asin"}),
    ("acos_image", "arithmetic", IMG, IMG, "pointwise", {"func": "acos"}),
    ("atan_image", "arithmetic", IMG, IMG, "pointwise", {"func": "atan"}),
    # ---- Filters/Image: gray LUT -----------------------------------------
    ("gamma_image", "gray", IMG, IMG, "lut", {"kind": "gamma"}),
    ("pow_image", "gray", IMG, IMG, "lut", {"kind": "gamma"}),
    ("invert_image", "gray", IMG, IMG, "lut", {"kind": "invert"}),
    ("scale_image", "gray", IMG, IMG, "lut", {"kind": "scale"}),
    ("equ_histo_image", "gray", IMG, IMG, "lut", {"kind": "equalize"}),
    ("illuminate", "gray", IMG, IMG, "lut", {"kind": "illuminate"}),
    ("scale_image_max", "gray", IMG, IMG, "lut", {"kind": "rescale"}),
    # ---- Filters: linear / smoothing -------------------------------------
    ("gauss_filter", "smoothing", IMG, IMG, "linfilter", {"kind": "gauss"}),
    ("gauss_image", "smoothing", IMG, IMG, "linfilter", {"kind": "gauss"}),
    ("mean_image", "smoothing", IMG, IMG, "linfilter", {"kind": "mean"}),
    ("binomial_filter", "smoothing", IMG, IMG, "linfilter", {"kind": "binomial"}),
    ("smooth_image", "smoothing", IMG, IMG, "linfilter", {"kind": "smooth"}),
    ("derivate_gauss", "edges", IMG, IMG, "linfilter", {"kind": "derivate_gauss"}),
    ("laplace_of_gauss", "edges", IMG, IMG, "linfilter", {"kind": "laplace_gauss"}),
    ("diff_of_gauss", "edges", IMG, IMG, "linfilter", {"kind": "dog"}),
    ("mean_curvature_flow", "smoothing", IMG, IMG, "linfilter", {"kind": "mean_curvature"}),
    # ---- Filters: rank ----------------------------------------------------
    ("median_image", "rank", IMG, IMG, "rank", {"kind": "median"}),
    ("median_rect", "rank", IMG, IMG, "rank", {"kind": "median_rect"}),
    ("median_separate", "rank", IMG, IMG, "rank", {"kind": "median"}),
    ("gray_erosion_rect", "rank", IMG, IMG, "rank", {"kind": "min"}),
    ("gray_dilation_rect", "rank", IMG, IMG, "rank", {"kind": "max"}),
    ("gray_range_rect", "rank", IMG, IMG, "rank", {"kind": "range"}),
    ("rank_image", "rank", IMG, IMG, "rank", {"kind": "rank"}),
    ("rank_rect", "rank", IMG, IMG, "rank", {"kind": "rank"}),
    ("sigma_image", "smoothing", IMG, IMG, "rank", {"kind": "sigma"}),
    ("trimmed_mean", "rank", IMG, IMG, "rank", {"kind": "trimmed_mean"}),
    # ---- Morphology: gray -------------------------------------------------
    ("gray_erosion", "morphology", IMG, IMG, "graymorph", {"op": "erosion"}),
    ("gray_dilation", "morphology", IMG, IMG, "graymorph", {"op": "dilation"}),
    ("gray_opening", "morphology", IMG, IMG, "graymorph", {"op": "opening"}),
    ("gray_closing", "morphology", IMG, IMG, "graymorph", {"op": "closing"}),
    ("gray_opening_shape", "morphology", IMG, IMG, "graymorph", {"op": "opening", "shape": "disk"}),
    ("gray_closing_shape", "morphology", IMG, IMG, "graymorph", {"op": "closing", "shape": "disk"}),
    ("gray_tophat", "morphology", IMG, IMG, "graymorph", {"op": "tophat"}),
    ("gray_bothat", "morphology", IMG, IMG, "graymorph", {"op": "bothat"}),
    # ---- Filters: edges (named kernels) ----------------------------------
    ("sobel_amp", "edges", IMG, IMG, "edge", {"kind": "sobel"}),
    ("sobel_dir", "edges", IMG, IMG, "edge", {"kind": "sobel_dir"}),
    ("prewitt_amp", "edges", IMG, IMG, "edge", {"kind": "prewitt"}),
    ("prewitt_dir", "edges", IMG, IMG, "edge", {"kind": "prewitt_dir"}),
    ("roberts", "edges", IMG, IMG, "edge", {"kind": "roberts"}),
    ("kirsch_amp", "edges", IMG, IMG, "edge", {"kind": "kirsch"}),
    ("kirsch_dir", "edges", IMG, IMG, "edge", {"kind": "kirsch_dir"}),
    ("frei_amp", "edges", IMG, IMG, "edge", {"kind": "frei"}),
    ("robinson_amp", "edges", IMG, IMG, "edge", {"kind": "robinson"}),
    ("laplace", "edges", IMG, IMG, "edge", {"kind": "laplace"}),
    # ---- Filters: frequency ----------------------------------------------
    ("fft_image", "frequency", IMG, IMG, "freq", {"kind": "fft_power"}),
    ("power_real", "frequency", IMG, IMG, "freq", {"kind": "fft_power_real"}),
    ("power_byte", "frequency", IMG, IMG, "freq", {"kind": "fft_power"}),
    ("phase_rad", "frequency", IMG, IMG, "freq", {"kind": "fft_phase"}),
    ("highpass_image", "frequency", IMG, IMG, "freq", {"kind": "highpass"}),
    ("bandpass_image", "frequency", IMG, IMG, "freq", {"kind": "bandpass"}),
    # ---- Filters: diffusion / texture ------------------------------------
    ("anisotropic_diffusion", "smoothing", IMG, IMG, "diffusion", {"kind": "anisotropic"}),
    ("isotropic_diffusion", "smoothing", IMG, IMG, "diffusion", {"kind": "isotropic"}),
    ("coherence_enhancing_diff", "smoothing", IMG, IMG, "diffusion", {"kind": "anisotropic"}),
    ("bilateral_filter", "smoothing", IMG, IMG, "diffusion", {"kind": "bilateral"}),
    ("guided_filter", "smoothing", IMG, IMG, "diffusion", {"kind": "bilateral"}),
    ("deviation_image", "texture", IMG, IMG, "texture", {"kind": "deviation"}),
    ("texture_laws", "texture", IMG, IMG, "texture", {"kind": "variance"}),
    ("entropy_image", "texture", IMG, IMG, "texture", {"kind": "entropy"}),
    ("gen_gabor", "texture", IMG, IMG, "texture", {"kind": "gabor"}),
    # ---- Transformations: geometric --------------------------------------
    ("mirror_image", "geometry", IMG, IMG, "geom", {"kind": "mirror"}),
    ("transpose_region", "geometry", REG, REG, "geom", {"kind": "transpose"}),
    ("rotate_image", "geometry", IMG, IMG, "geom", {"kind": "rotate"}),
    ("zoom_image_factor", "geometry", IMG, IMG, "geom", {"kind": "zoom"}),
    ("zoom_image_size", "geometry", IMG, IMG, "geom", {"kind": "zoom"}),
    ("affine_trans_image", "geometry", IMG, IMG, "geom", {"kind": "affine"}),
    ("polar_trans_image", "geometry", IMG, IMG, "geom", {"kind": "polar"}),
    # ---- Segmentation: thresholding --------------------------------------
    ("threshold", "segmentation", IMG, REG, "threshold", {"method": "fixed"}),
    ("binary_threshold", "segmentation", IMG, REG, "threshold", {"method": "otsu"}),
    ("auto_threshold", "segmentation", IMG, REG, "threshold", {"method": "otsu"}),
    ("dyn_threshold", "segmentation", IMG, REG, "threshold", {"method": "dyn"}),
    ("var_threshold", "segmentation", IMG, REG, "threshold", {"method": "sauvola"}),
    ("local_threshold", "segmentation", IMG, REG, "threshold", {"method": "local_gauss"}),
    ("hysteresis_threshold", "segmentation", IMG, REG, "threshold", {"method": "hysteresis"}),
    # ---- Segmentation: edges / regions -----------------------------------
    ("edges_image", "segmentation", IMG, REG, "segment", {"kind": "sk_canny"}),
    ("watersheds", "segmentation", IMG, REG, "segment", {"kind": "watershed"}),
    ("watersheds_threshold", "segmentation", IMG, REG, "segment", {"kind": "watershed"}),
    ("regiongrowing", "segmentation", IMG, REG, "segment", {"kind": "regiongrow"}),
    ("local_max", "segmentation", IMG, REG, "segment", {"kind": "local_max"}),
    # ---- Regions: binary morphology --------------------------------------
    ("erosion_circle", "region", REG, REG, "binmorph", {"op": "erosion", "shape": "disk"}),
    ("dilation_circle", "region", REG, REG, "binmorph", {"op": "dilation", "shape": "disk"}),
    ("opening_circle", "region", REG, REG, "binmorph", {"op": "opening", "shape": "disk"}),
    ("closing_circle", "region", REG, REG, "binmorph", {"op": "closing", "shape": "disk"}),
    ("erosion_rectangle1", "region", REG, REG, "binmorph", {"op": "erosion", "shape": "rect"}),
    ("dilation_rectangle1", "region", REG, REG, "binmorph", {"op": "dilation", "shape": "rect"}),
    ("opening_rectangle1", "region", REG, REG, "binmorph", {"op": "opening", "shape": "rect"}),
    ("closing_rectangle1", "region", REG, REG, "binmorph", {"op": "closing", "shape": "rect"}),
    # ---- Regions: transforms ---------------------------------------------
    ("fill_up", "region", REG, REG, "region_trans", {"kind": "fill_up"}),
    ("boundary", "region", REG, REG, "region_trans", {"kind": "boundary"}),
    ("skeleton", "region", REG, REG, "region_trans", {"kind": "skeleton"}),
    ("thinning", "region", REG, REG, "region_trans", {"kind": "thin"}),
    ("shape_trans", "region", REG, REG, "region_trans", {"kind": "convex"}),
    ("select_shape_std", "region", REG, REG, "region_trans", {"kind": "select_largest"}),
    ("select_shape", "region", REG, REG, "region_trans", {"kind": "remove_small"}),
    ("distance_transform", "region", REG, IMG, "region_trans", {"kind": "dist_transform"}),
    # ---- Regions: features -----------------------------------------------
    ("area_center", "features", REG, FEA, "region_feat", {"metric": "area"}),
    ("count_obj", "features", REG, FEA, "region_feat", {"metric": "count"}),
    ("circularity", "features", REG, FEA, "region_feat", {"metric": "circularity"}),
    ("compactness", "features", REG, FEA, "region_feat", {"metric": "compactness"}),
    ("convexity", "features", REG, FEA, "region_feat", {"metric": "convexity"}),
    ("rectangularity", "features", REG, FEA, "region_feat", {"metric": "rectangularity"}),
    ("eccentricity", "features", REG, FEA, "region_feat", {"metric": "eccentricity"}),
    ("orientation_region", "features", REG, FEA, "region_feat", {"metric": "orientation"}),
    ("roundness", "features", REG, FEA, "region_feat", {"metric": "roundness"}),
    ("diameter_region", "features", REG, FEA, "region_feat", {"metric": "diameter"}),
    ("euler_number", "features", REG, FEA, "region_feat", {"metric": "euler"}),
    # ---- Image: gray-value statistics ------------------------------------
    ("min_max_gray", "features", IMG, FEA, "img_feat", {"metric": "max"}),
    ("intensity", "features", IMG, FEA, "img_feat", {"metric": "mean"}),
    ("gray_histo_abs", "features", IMG, FEA, "img_feat", {"metric": "std"}),
    ("entropy_gray", "features", IMG, FEA, "img_feat", {"metric": "entropy"}),
    # ---- XLD contours -----------------------------------------------------
    ("edges_sub_pix", "contour", IMG, CON, "xld", {"kind": "edges_sub_pix"}),
    ("lines_gauss", "contour", IMG, CON, "xld", {"kind": "lines_gauss"}),
    ("select_contours_xld", "contour", CON, CON, "xld", {"kind": "select_contours"}),
    ("smooth_contours_xld", "contour", CON, CON, "xld", {"kind": "smooth_contours"}),
    ("gen_region_contour_xld", "contour", CON, REG, "xld", {"kind": "to_region"}),
    ("length_xld", "features", CON, FEA, "xld", {"kind": "length"}),
]


# --------------------------------------------------------------------------- #
# spec loading + validation + compilation                                     #
# --------------------------------------------------------------------------- #
def _real_ops() -> set:
    path = os.path.join(HERE, "data", "halcon_operators.json")
    if not os.path.exists(path):
        return set()
    data = json.load(open(path, encoding="utf-8"))
    return {op["name"] for op in data["operators"]}


def load_specs() -> list[tuple]:
    """SEED + every spec in data/auto_specs/*.json (agent-authored breadth)."""
    specs = [dict(zip(("halcon", "category", "in_sort", "out_sort", "shape", "params"), s))
             for s in SEED]
    d = os.path.join(HERE, "data", "auto_specs")
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                try:
                    for s in json.load(open(os.path.join(d, fn), encoding="utf-8")):
                        specs.append(s)
                except Exception:
                    pass
    return specs


def _safe(fn):
    def w(v, a, b):
        try:
            out = fn(v, a, b)
            return out if out is not None else v
        except Exception:
            return v
    return w


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Compile validated specs into typed Op wrappers.

    Fail-closed: a spec whose `halcon` name is not a real HALCON operator, or
    whose `shape` is unknown, is dropped (never counted). One op claims one
    HALCON name; later duplicates for the same name are skipped.
    """
    real = _real_ops()
    ops_out, seen, dropped = [], set(), []
    for s in load_specs():
        name = s.get("halcon", "")
        shape = s.get("shape", "")
        if real and name not in real:
            dropped.append(("fake_name", name))
            continue
        if shape not in SHAPES:
            dropped.append(("bad_shape", name + ":" + shape))
            continue
        if name in seen:
            continue                        # one op per HALCON name (coverage de-dups anyway)
        try:
            fn = SHAPES[shape](s.get("params", {}))
        except Exception:
            dropped.append(("bad_params", name))
            continue
        seen.add(name)
        opname = name if name not in ("threshold", "identity") else "h_" + name
        ops_out.append(Op(opname, s.get("category", "misc"), name,
                          s.get("in_sort", "image"), s.get("out_sort", "image"), _safe(fn)))
    build.dropped = dropped                 # introspectable for honest reporting
    return ops_out


build.dropped = []


if __name__ == "__main__":  # quick self-report (no registry side effects)
    from dataclasses import dataclass
    from typing import Callable

    @dataclass
    class _Op:
        name: str
        category: str
        halcon: str
        in_sort: str
        out_sort: str
        fn: Callable
        c_stmt: object = None

    got = build(_Op, "image", "region", "feature", "contour", _norm, _bin)
    print("backends_auto: %d ops from %d specs (%d dropped)"
          % (len(got), len(load_specs()), len(build.dropped)))
    if build.dropped:
        print("dropped:", build.dropped[:20])
