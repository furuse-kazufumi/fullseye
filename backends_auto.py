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

from backend_safe import signed01
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


def _shift_edge(x, dy, dx):
    """Shift like ``np.roll`` but REPLICATE the border instead of wrapping around
    (``np.roll`` is circular, so the last row/col would leak into the first)."""
    x = np.asarray(x, np.float64)
    H, W = x.shape[0], x.shape[1]
    py0, py1, px0, px1 = max(dy, 0), max(-dy, 0), max(dx, 0), max(-dx, 0)
    p = np.pad(x, ((py0, py1), (px0, px1)), mode="edge")
    return p[py1:py1 + H, px1:px1 + W]


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
            return signed01(np.tan((x - 0.5) * (np.pi * 0.9)))
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
            return signed01(ndimage.gaussian_laplace(x, 0.5 + 2.5 * a))
        if kind == "dog":
            return _norm(np.abs(ndimage.gaussian_filter(x, 0.5 + 2 * a)
                                - ndimage.gaussian_filter(x, 1 + 4 * b)))
        if kind == "mean_curvature":
            y = x.copy()
            for _ in range(1 + int(a * 6)):
                y = ndimage.gaussian_filter(y, 0.6)
            return y
        if kind == "motion":                         # directional (linear) motion blur
            ang, L = np.pi * a, 5 + int(b * 10)
            ker = np.zeros((L, L))
            c = (L - 1) / 2
            for t in np.linspace(-c, c, L * 2):
                yy, xx = int(round(c + t * np.sin(ang))), int(round(c + t * np.cos(ang)))
                if 0 <= yy < L and 0 <= xx < L:
                    ker[yy, xx] = 1.0
            ker = ker / ker.sum() if ker.sum() > 0 else ker
            return ndimage.convolve(x, ker, mode="reflect")
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
            return _norm(np.hypot(x - _shift_edge(x, -1, -1),
                                  _shift_edge(x, 0, -1) - _shift_edge(x, -1, 0)))
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
            # _FREI[0] is the horizontal-edge kernel (row/y gradient), _FREI[1] the
            # vertical-edge kernel (col/x gradient); arctan2(gy, gx) matches the
            # sobel_dir / prewitt_dir convention.
            return (np.arctan2(ndimage.convolve(x, _FREI[0]),
                               ndimage.convolve(x, _FREI[1])) + np.pi) / (2 * np.pi)
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


# ---- image -> image : corner strength (Harris/Foerstner/Shi-Tomasi) --------- #
def _sh_corner(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        s = 0.5 + 2.0 * a
        if kind == "harris" and _HAS_SK:
            return signed01(skfeat.corner_harris(x, sigma=s))
        if kind == "harris_binomial":                # Harris on a binomially pre-smoothed image
            xb = ndimage.gaussian_filter(x, 0.5 + 1.5 * b)
            if _HAS_SK:
                return signed01(skfeat.corner_harris(xb, sigma=s))
            gx, gy = ndimage.sobel(xb, 1), ndimage.sobel(xb, 0)
            axx = ndimage.gaussian_filter(gx * gx, s)
            ayy = ndimage.gaussian_filter(gy * gy, s)
            axy = ndimage.gaussian_filter(gx * gy, s)
            return _norm(axx * ayy - axy * axy - 0.04 * (axx + ayy) ** 2)
        if kind == "foerstner" and _HAS_SK:
            w, q = skfeat.corner_foerstner(x, sigma=s)
            return _norm(np.nan_to_num(w) * np.nan_to_num(q))
        if kind == "shi_tomasi" and _HAS_SK:
            return _norm(skfeat.corner_shi_tomasi(x, sigma=s))
        raise ValueError(kind)
    return fn


# ---- image -> image : Hough accumulator (line / circle) --------------------- #
def _sh_hough(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        edges = _norm(np.hypot(ndimage.sobel(x, 1), ndimage.sobel(x, 0))) > (0.2 + 0.4 * a)
        if kind == "line" and _HAS_SK:
            h, _, _ = sktrans.hough_line(edges)
            acc = _norm(h.astype(np.float64))
            return cv2.resize(acc, (x.shape[1], x.shape[0])).astype(np.float64) if _HAS_CV \
                else np.resize(acc, x.shape)
        if kind == "circle" and _HAS_SK:
            radii = np.arange(4, 20, 3)
            return _norm(sktrans.hough_circle(edges, radii).max(0))    # (R,H,W) -> (H,W)
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
        if kind == "ifft":                           # inverse Fourier transform (fft_image_inv)
            return _norm(np.real(np.fft.ifft2(x)))
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
            g = g - g.mean()   # DC-free (zero-mean) kernel: a Gabor is band-pass, not a brightness detector
            return _norm(np.abs(ndimage.convolve(x, g, mode="reflect")))
        if kind == "lbp" and _HAS_SK:
            return _norm(skfeat.local_binary_pattern(x, 8, _rad(a)))
        if kind == "coherence" and _HAS_SK:
            return signed01(np.nan_to_num(skfeat.shape_index(x, sigma=0.5 + 2 * a)))
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
            # Zero-init the destination: cv2.warpPolar never writes pixels whose
            # source maps outside the image, so a fresh buffer would leak stale
            # memory (nondeterministic + out of range). Pre-zeroing makes the
            # unmapped pixels a deterministic 0.
            dst = np.zeros((h, w), np.float32)
            cv2.warpPolar(x.astype(np.float32), (w, h), (w / 2, h / 2),
                          min(h, w) / 2, cv2.WARP_POLAR_LINEAR, dst)
            return np.clip(dst.astype(np.float64), 0, 1)
        if kind == "polar_inv" and _HAS_CV:          # inverse polar->Cartesian (polar_trans_image_inv)
            h, w = x.shape
            # Cartesian corners fall outside the polar disc and are never written;
            # zero-init for determinism (see the forward branch above).
            dst = np.zeros((h, w), np.float32)
            cv2.warpPolar(x.astype(np.float32), (w, h), (w / 2, h / 2), min(h, w) / 2,
                          cv2.WARP_POLAR_LINEAR + cv2.WARP_INVERSE_MAP, dst)
            return np.clip(dst.astype(np.float64), 0, 1)
        if kind == "projective" and _HAS_CV:         # perspective warp (projective_trans_image)
            h, w = x.shape
            d = 0.06 + 0.12 * a
            src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
            dst = np.float32([[w * d * b, h * d], [w * (1 - d * b), 0], [w, h], [0, h * (1 - d)]])
            M = cv2.getPerspectiveTransform(src, dst)
            out = cv2.warpPerspective(x.astype(np.float32), M, (w, h), borderMode=cv2.BORDER_REFLECT)
            return np.clip(out.astype(np.float64), 0, 1)
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
        if method == "dual":                         # signed threshold: |x-0.5| > t (dual_threshold)
            return (np.abs(x - 0.5) > (0.1 + 0.35 * a)).astype(np.float64)
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
        if kind == "mser" and _HAS_CV:               # maximally stable extremal regions (segment_image_mser)
            mser = cv2.MSER_create(delta=int(3 + 8 * a))
            regs, _ = mser.detectRegions(_u8(x))
            out = np.zeros_like(x, np.float64)
            for pts in regs:
                out[pts[:, 1], pts[:, 0]] = 1.0
            return skseg.find_boundaries(out > 0.5).astype(np.float64) if _HAS_SK else out
        if kind == "zero_crossing":                  # Laplacian sign-changes (zero_crossing)
            lap = ndimage.gaussian_laplace(x, 0.5 + 2.0 * a)
            s = np.sign(lap)
            zc = np.zeros_like(x, bool)
            zc[:-1, :] |= np.abs(np.diff(s, axis=0)) > 0
            zc[:, :-1] |= np.abs(np.diff(s, axis=1)) > 0
            return zc.astype(np.float64)
        if kind == "local_min":                      # regional minima (local_min)
            return ((x <= ndimage.minimum_filter(x, _k(a))) & (x < (0.7 - 0.4 * b))).astype(np.float64)
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
        if kind == "pruning":                        # remove skeleton spurs (pruning)
            sk = skmorph.skeletonize(m) if _HAS_SK else m
            for _ in range(1 + int(a * 4)):
                nb = ndimage.convolve(sk.astype(int), np.ones((3, 3)), mode="constant") - sk.astype(int)
                sk = sk & ~(sk & (nb <= 1))
            return sk.astype(np.float64)
        if kind == "closest_point_transform":        # distance to the nearest region point (EDT of complement)
            return _norm(ndimage.distance_transform_edt(~m))
        if kind == "junctions_skeleton":             # skeleton branch points (>=3 neighbours)
            sk = skmorph.skeletonize(m) if _HAS_SK else m
            nb = ndimage.convolve(sk.astype(int), np.ones((3, 3)), mode="constant") - sk.astype(int)
            return (sk & (nb >= 3)).astype(np.float64)
        raise ValueError(kind)
    return fn


# ---- region -> feature : shape measurements -------------------------------- #
def _sh_region_feat(p):
    metric = p["metric"]
    # 2026-08-30 (KNOWN_ISSUES #1): the "count" metric now labels with
    # 8-connectivity by default — HALCON parity (`connection` / `count_obj`
    # default to 8-connectivity, and `segment_objects` here already did). The
    # old scipy default (4-connectivity) split diagonally-touching blobs and
    # over-counted (cell counting: 342 vs 327 on real data). The legacy
    # behaviour stays reachable via params {"connectivity": 4}.
    connectivity = int(p.get("connectivity", 8))

    def fn(v, a, b):
        m = _bin(v)
        if metric == "count":
            st = ndimage.generate_binary_structure(2, 2 if connectivity == 8 else 1)
            return np.float64(ndimage.label(m, structure=st)[1])
        big, lab, n = _largest_label(m)
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
        if metric == "thickness":                    # 2x max inscribed distance (get_region_thickness)
            return np.float64(min(1.0, 2 * float(ndimage.distance_transform_edt(m).max()) / max(m.shape)))
        if metric == "perimeter":
            return np.float64(min(1.0, per / (2.0 * (m.shape[0] + m.shape[1]))))
        if metric == "area_holes":
            return np.float64((pr.area_filled - pr.area) / max(pr.area_filled, 1))
        if metric == "aspect":
            minr, minc, maxr, maxc = pr.bbox
            return np.float64(min(1.0, (maxr - minr) / max(maxc - minc, 1)))
        if metric.startswith(("moment", "hu")):
            nu = skmeasure.moments_normalized(skmeasure.moments_central(big.astype(float)))
            hu = skmeasure.moments_hu(nu)
            table = {
                "moment2": abs(nu[2, 0] + nu[0, 2]),
                "moment3": abs(nu[3, 0] + nu[0, 3]),
                "moment_central": abs(nu[2, 0] + nu[1, 1] + nu[0, 2]),
                "hu1": abs(hu[0]), "hu2": abs(hu[1]), "hu3": abs(hu[2]), "hu4": abs(hu[3]),
            }
            if metric in table:
                return np.float64(min(1.0, float(table[metric])))
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
        if metric == "noise_est":                    # robust noise sigma (estimate_noise): MAD of Laplacian
            lap = ndimage.laplace(x)
            return np.float64(min(1.0, 1.4826 * np.median(np.abs(lap - np.median(lap))) * 3))
        raise ValueError(metric)
    return fn


# ---- image -> contour (XLD) and contour ops -------------------------------- #
# Clockwise ring of 8-neighbour offsets: N, NE, E, SE, S, SW, W, NW.
_RING8 = ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))
_RING8_IDX = {d: i for i, d in enumerate(_RING8)}


def _moore_boundaries(mask):
    """Outer boundary of every 8-connected component, in **trace order**.

    Moore-neighbour tracing with Jacob's stopping criterion (pure numpy/scipy —
    the no-skimage fallback for `gen_contour_region_xld`). Each returned array is
    (N, 2) float64 (row, col) pixel coordinates walking the component's outer
    boundary; the loop is closed (last point == first point) so downstream
    arc-length consumers (elliptic Fourier, perimeter) see a closed curve.
    Adjacent points are 8-neighbours, so consecutive distances are <= sqrt(2).
    """
    H, W = mask.shape
    lab, n = ndimage.label(mask, structure=np.ones((3, 3), bool))
    out = []
    for i in range(1, n + 1):
        comp = lab == i
        ys, xs = np.nonzero(comp)
        sy, sx = int(ys[0]), int(xs[0])         # raster-first pixel: W neighbour is bg
        pts = [(sy, sx)]
        # backtrack direction: from the current pixel toward the last background
        # pixel examined (start: the West neighbour, guaranteed background).
        back = 6
        cy, cx, cb = sy, sx, back
        seen_at_start = {back}                  # Jacob's criterion, state-based
        limit = 4 * int(comp.sum()) + 8         # hard cap: boundary <= 4*area
        for _ in range(limit):
            step = None
            for k in range(1, 9):               # clockwise sweep after the backtrack
                j = (cb + k) % 8
                ny, nx = cy + _RING8[j][0], cx + _RING8[j][1]
                if 0 <= ny < H and 0 <= nx < W and comp[ny, nx]:
                    step = (j, ny, nx)
                    break
            if step is None:
                break                            # isolated single pixel
            j, ny, nx = step
            # new backtrack = the (background) neighbour examined just before the
            # hit, re-expressed as a direction from the NEW pixel. Adjacent ring
            # cells are 8-neighbours of each other, so the delta is a ring index.
            py, px = cy + _RING8[(j - 1) % 8][0], cx + _RING8[(j - 1) % 8][1]
            nb = _RING8_IDX[(py - ny, px - nx)]
            cy, cx, cb = ny, nx, nb
            if (cy, cx) == (sy, sx):
                if cb in seen_at_start:
                    break                        # Jacob: start re-entered same way
                seen_at_start.add(cb)
            pts.append((cy, cx))
        pts.append((sy, sx))                     # close the loop
        out.append(np.asarray(pts, np.float64))
    return out


def _sh_xld(p):
    kind = p["kind"]

    def fn(v, a, b):
        if kind == "region_boundary":
            # gen_contour_region_xld: region -> boundary contours in TRACE order.
            # 2026-08-30 (KNOWN_ISSUES #3): this op used the generic
            # "edges_sub_pix" path, whose points come from np.where (raster
            # order), silently breaking order-dependent consumers
            # (fourierdesc.elliptic_fourier collapsed to one axis). skimage
            # find_contours yields sub-pixel traced loops; the Moore tracer is
            # the numpy-only fallback (trace order, pixel resolution).
            m = _bin(v)
            if _HAS_SK:
                pm = np.pad(m.astype(np.float64), 1)     # close border-touching loops
                cs = [c - 1.0 for c in skmeasure.find_contours(pm, 0.5) if len(c) >= 3]
            else:
                cs = [c for c in _moore_boundaries(m) if len(c) >= 3]
            return {"shape": m.shape, "cs": cs}
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
        if kind == "threshold_sub_pix" and _HAS_SK:      # subpixel level crossings as contours
            x = np.asarray(v, np.float64)
            cs = [c for c in skmeasure.find_contours(x, 0.2 + 0.5 * a) if len(c) >= 3]
            return {"shape": x.shape, "cs": cs}
        if kind == "zero_crossing_sub_pix" and _HAS_SK:  # Laplacian zero crossings as contours
            x = np.asarray(v, np.float64)
            lap = ndimage.gaussian_laplace(x, 0.5 + 2.0 * a)
            cs = [c for c in skmeasure.find_contours(lap, 0.0) if len(c) >= 3]
            return {"shape": x.shape, "cs": cs}
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
        # ---- contour -> feature (XLD shape measures on the largest contour) ----
        if kind in ("area", "circularity", "compactness", "convexity", "num_points"):
            cs = [c for c in cv["cs"] if len(c) >= 3]
            if not cs:
                return np.float64(0.0)
            c = max(cs, key=len)
            y, x = c[:, 0], c[:, 1]
            area = 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
            per = float(np.sum(np.hypot(np.diff(y), np.diff(x)))) + 1e-8
            if kind == "num_points":
                return np.float64(min(1.0, len(c) / 500.0))
            if kind == "area":
                return np.float64(min(1.0, area / (cv["shape"][0] * cv["shape"][1])))
            if kind == "circularity":
                return np.float64(min(1.0, 4 * np.pi * area / (per * per)))
            if kind == "compactness":
                return np.float64(min(1.0, (per * per) / (4 * np.pi * max(area, 1)) / 10))
            if kind == "convexity":
                if _HAS_CV:
                    hull = cv2.convexHull(np.stack([x, y], 1).astype(np.float32))
                    ha = float(cv2.contourArea(hull))
                    return np.float64(min(1.0, area / max(ha, 1e-6)))
                return np.float64(1.0)
        # ---- contour -> feature (ellipse fit / diameter / moments; cv2) ----
        if kind in ("eccentricity", "orientation", "elliptic_axis", "diameter",
                    "rectangularity", "moment_xld") and _HAS_CV:
            cs = [c for c in cv["cs"] if len(c) >= 5]
            if not cs:
                return np.float64(0.0)
            c = max(cs, key=len)
            pts = np.stack([c[:, 1], c[:, 0]], 1).astype(np.float32)   # (x, y)
            if kind == "diameter":
                (_, _), r = cv2.minEnclosingCircle(pts)
                return np.float64(min(1.0, 2 * r / max(cv["shape"])))
            if kind == "rectangularity":
                ar = abs(float(cv2.contourArea(pts)))
                (_, (w, h), _) = cv2.minAreaRect(pts)
                return np.float64(min(1.0, ar / max(w * h, 1.0)))
            if kind == "moment_xld":
                mm = cv2.moments(pts)
                a2 = mm["m00"] or 1.0
                return np.float64(min(1.0, (mm["mu20"] + mm["mu02"]) / (a2 * a2 + 1e-6)))
            (_, _), (d1, d2), ang = cv2.fitEllipse(pts)
            major, minor = max(d1, d2), max(min(d1, d2), 1e-6)
            if kind == "eccentricity":
                return np.float64(np.sqrt(max(0.0, 1 - (minor / major) ** 2)))
            if kind == "orientation":
                return np.float64((ang % 180) / 180.0)
            return np.float64(minor / major)                          # elliptic_axis
        # ---- contour -> contour (transforms / closing) ----
        if kind == "convex" and _HAS_CV:
            out = []
            for c in cv["cs"]:
                if len(c) >= 3:
                    hull = cv2.convexHull(np.stack([c[:, 1], c[:, 0]], 1).astype(np.float32))
                    out.append(np.stack([hull[:, 0, 1], hull[:, 0, 0]], 1).astype(np.float64))
                else:
                    out.append(c)
            return {"shape": cv["shape"], "cs": out}
        if kind in ("close", "affine", "projective", "polar"):
            out = []
            H, W = cv["shape"]
            for c in cv["cs"]:
                if kind == "close" and len(c) >= 2:
                    out.append(np.vstack([c, c[:1]]))
                    continue
                pts = c.astype(np.float64)
                yc, xc = H / 2, W / 2
                if kind == "affine":
                    ang = np.deg2rad(-20 + 40 * a)
                    R = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
                    q = (pts - [yc, xc]) @ R.T + [yc, xc]
                elif kind == "projective":
                    q = pts.copy()
                    d = 1.0 + 0.3 * a * (pts[:, 1:2] - xc) / max(W, 1)
                    q = (pts - [yc, xc]) / d + [yc, xc]
                else:  # polar
                    rr = np.hypot(pts[:, 0] - yc, pts[:, 1] - xc)
                    th = np.arctan2(pts[:, 0] - yc, pts[:, 1] - xc)
                    q = np.stack([rr / max(H, W) * H, (th + np.pi) / (2 * np.pi) * W], 1)
                out.append(q)
            return {"shape": cv["shape"], "cs": out}
        raise ValueError(kind)
    return fn


# ---- image -> feature : Haralick / co-occurrence texture -------------------- #
def _sh_cooc(p):
    prop = p["prop"]

    def fn(v, a, b):
        lv = 16
        xq = (np.clip(np.asarray(v, np.float64), 0, 1) * (lv - 1)).astype(np.uint8)
        glcm = skfeat.graycomatrix(xq, distances=[1 + int(a * 3)], angles=[0.0],
                                   levels=lv, symmetric=True, normed=True)
        val = float(skfeat.graycoprops(glcm, prop)[0, 0])
        if prop in ("contrast", "dissimilarity"):
            val = val / (lv * lv)
        elif prop == "correlation":
            val = (val + 1) / 2
        return np.float64(min(1.0, max(0.0, val)))
    return fn


# ---- image -> image : deterministic noise (add_noise_*) --------------------- #
def _sh_noise(p):
    kind = p["kind"]

    def fn(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        rng = np.random.default_rng(int(a * 997) + 7)
        if kind == "gaussian":
            return np.clip(x + (0.02 + 0.2 * b) * rng.standard_normal(x.shape), 0, 1)
        if kind == "sp":
            m = rng.random(x.shape)
            p_ = 0.02 + 0.1 * b
            y = x.copy()
            y[m < p_] = 0.0
            y[m > 1 - p_] = 1.0
            return y
        raise ValueError(kind)
    return fn


SHAPES = {
    "pointwise": _sh_pointwise, "lut": _sh_lut, "linfilter": _sh_linfilter,
    "rank": _sh_rank, "graymorph": _sh_graymorph, "edge": _sh_edge,
    "freq": _sh_freq, "diffusion": _sh_diffusion, "texture": _sh_texture,
    "geom": _sh_geom, "threshold": _sh_threshold, "segment": _sh_segment,
    "binmorph": _sh_binmorph, "region_trans": _sh_region_trans,
    "region_feat": _sh_region_feat, "img_feat": _sh_img_feat, "xld": _sh_xld,
    "cooc": _sh_cooc, "noise": _sh_noise, "corner": _sh_corner, "hough": _sh_hough,
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
    # ---- v11b increment: newly-enabled genuine families ------------------
    # region measurements
    ("contlength", "features", REG, FEA, "region_feat", {"metric": "perimeter"}),
    ("area_holes", "features", REG, FEA, "region_feat", {"metric": "area_holes"}),
    ("height_width_ratio", "features", REG, FEA, "region_feat", {"metric": "aspect"}),
    ("moments_region_2nd", "features", REG, FEA, "region_feat", {"metric": "moment2"}),
    ("moments_region_2nd_invar", "features", REG, FEA, "region_feat", {"metric": "hu1"}),
    # Haralick texture (image -> feature)
    ("cooc_feature_matrix", "texture", IMG, FEA, "cooc", {"prop": "energy"}),
    # windowed histogram equalisation
    ("equ_histo_image_rect", "gray", IMG, IMG, "lut", {"kind": "equalize_local"}),
    # motion blur
    ("simulate_motion", "smoothing", IMG, IMG, "linfilter", {"kind": "motion"}),
    # projective / inverse transforms
    ("projective_trans_image", "geometry", IMG, IMG, "geom", {"kind": "projective"}),
    ("projective_trans_image_size", "geometry", IMG, IMG, "geom", {"kind": "projective"}),
    ("projective_trans_region", "geometry", REG, REG, "geom", {"kind": "projective"}),
    ("polar_trans_image_inv", "geometry", IMG, IMG, "geom", {"kind": "polar_inv"}),
    ("fft_image_inv", "frequency", IMG, IMG, "freq", {"kind": "ifft"}),
    # deterministic noise
    ("add_noise_white", "noise", IMG, IMG, "noise", {"kind": "gaussian"}),
    # ---- v11d increment: XLD contour ops + region moments + misc ----------
    # XLD contour -> feature
    ("area_center_xld", "features", CON, FEA, "xld", {"kind": "area"}),
    ("circularity_xld", "features", CON, FEA, "xld", {"kind": "circularity"}),
    ("compactness_xld", "features", CON, FEA, "xld", {"kind": "compactness"}),
    ("convexity_xld", "features", CON, FEA, "xld", {"kind": "convexity"}),
    # XLD contour -> contour (transforms / closing)
    ("close_contours_xld", "contour", CON, CON, "xld", {"kind": "close"}),
    ("affine_trans_contour_xld", "contour", CON, CON, "xld", {"kind": "affine"}),
    ("projective_trans_contour_xld", "contour", CON, CON, "xld", {"kind": "projective"}),
    ("polar_trans_contour_xld", "contour", CON, CON, "xld", {"kind": "polar"}),
    # region moments
    ("moments_region_3rd", "features", REG, FEA, "region_feat", {"metric": "moment3"}),
    ("moments_region_central", "features", REG, FEA, "region_feat", {"metric": "moment_central"}),
    ("moments_region_central_invar", "features", REG, FEA, "region_feat", {"metric": "hu2"}),
    ("moments_region_2nd_rel_invar", "features", REG, FEA, "region_feat", {"metric": "hu3"}),
    ("moments_region_3rd_invar", "features", REG, FEA, "region_feat", {"metric": "hu4"}),
    # segmentation / threshold / stats
    ("dual_threshold", "segmentation", IMG, REG, "threshold", {"method": "dual"}),
    ("segment_image_mser", "segmentation", IMG, REG, "segment", {"kind": "mser"}),
    ("regiongrowing_mean", "segmentation", IMG, REG, "segment", {"kind": "regiongrow"}),
    ("estimate_noise", "features", IMG, FEA, "img_feat", {"metric": "noise_est"}),
    # corner strength maps (points_harris already covered by core corner_response)
    ("points_foerstner", "edges", IMG, IMG, "corner", {"kind": "foerstner"}),
    ("points_harris_binomial", "edges", IMG, IMG, "corner", {"kind": "harris_binomial"}),
    # ---- v11e increment: XLD ellipse/moment features + crossings + pruning ----
    ("eccentricity_xld", "features", CON, FEA, "xld", {"kind": "eccentricity"}),
    ("orientation_xld", "features", CON, FEA, "xld", {"kind": "orientation"}),
    ("elliptic_axis_xld", "features", CON, FEA, "xld", {"kind": "elliptic_axis"}),
    ("diameter_xld", "features", CON, FEA, "xld", {"kind": "diameter"}),
    ("rectangularity_xld", "features", CON, FEA, "xld", {"kind": "rectangularity"}),
    ("moments_xld", "features", CON, FEA, "xld", {"kind": "moment_xld"}),
    ("shape_trans_xld", "contour", CON, CON, "xld", {"kind": "convex"}),
    ("zero_crossing", "segmentation", IMG, REG, "segment", {"kind": "zero_crossing"}),
    ("local_min", "segmentation", IMG, REG, "segment", {"kind": "local_min"}),
    ("pruning", "region", REG, REG, "region_trans", {"kind": "pruning"}),
    # ---- v11f increment: Hough, subpixel crossings, skeleton/EDT region ops ----
    ("hough_line_trans", "features", IMG, IMG, "hough", {"kind": "line"}),
    ("hough_circle_trans", "features", IMG, IMG, "hough", {"kind": "circle"}),
    ("threshold_sub_pix", "contour", IMG, CON, "xld", {"kind": "threshold_sub_pix"}),
    ("zero_crossing_sub_pix", "contour", IMG, CON, "xld", {"kind": "zero_crossing_sub_pix"}),
    ("closest_point_transform", "region", REG, IMG, "region_trans", {"kind": "closest_point_transform"}),
    ("junctions_skeleton", "region", REG, REG, "region_trans", {"kind": "junctions_skeleton"}),
    ("get_region_thickness", "features", REG, FEA, "region_feat", {"metric": "thickness"}),
]


# --------------------------------------------------------------------------- #
# spec loading + validation + compilation                                     #
# --------------------------------------------------------------------------- #
def _real_ops() -> set:
    """Real HALCON operator names — generated py-module first, flat data/ JSON second.

    `halcon_names_data` ALWAYS ships in the wheel; `data/halcon_operators.json` does
    NOT (same flat-layout gap the macro DNA store and auto_specs_data already dodge).
    Reading the JSON alone returned an EMPTY set on a pip-installed package, which
    turned the fail-closed name guard in `build` into a pass-everything no-op — see
    the guard there, which now drops rather than admits when this set is empty.
    """
    try:
        from halcon_names_data import HALCON_NAMES
        return set(HALCON_NAMES)
    except Exception:
        pass
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
    loaded = False
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                try:
                    for s in json.load(open(os.path.join(d, fn), encoding="utf-8")):
                        specs.append(s)
                    loaded = True
                except Exception:
                    pass
    if not loaded:
        # Wheel install: the flat-layout data/auto_specs/ dir is not shipped
        # (setuptools maps package-data to the fullseye package, not the root
        # data/ tree), so read the generated py-module mirror that DOES ship —
        # same data-as-code fix the macro DNA store uses. Keep in sync via
        # gen_auto_specs_data.py.
        try:
            from auto_specs_data import AUTO_SPECS
            specs.extend(AUTO_SPECS)
        except Exception:
            pass
    return specs


def _safe(fn, out_sort=None):
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:
            out = None
        return sanitize(out, v, out_sort)
    return w


def _rebinarise(fn):
    """Restore the {0,1} region contract after an INTERPOLATING geometry op.

    `_sh_geom` resamples with cubic-spline (`ndimage.affine_transform`), bilinear
    (`cv2.warpPolar`) or perspective (`cv2.warpPerspective`) interpolation and
    then only clips to [0,1].  Applied to a spec whose declared `out_sort` is
    "region" that produced FRACTIONAL membership -- transforming a 441 px binary
    disk gave `affine_trans_region` 2009 distinct values / 906 fractional pixels
    -- which both violates the sort contract and silently deletes small regions
    at the `> 0.5` cut every region consumer (`ops._bin`) applies (a 1-pixel
    region peaked at 0.4977 and vanished).  A geometric transform is a bijection
    of the plane, so the image of a SET is a SET: threshold here, at the op
    boundary, using the codebase's canonical region cut.

    Only region-typed geometry specs are wrapped (see `build`); the image-typed
    siblings compiled from the same `_sh_geom` (zoom_image_factor,
    affine_trans_image, rotate_image, projective_trans_image, ...) stay
    continuous.
    """
    def w(v, a, b):
        out = fn(v, a, b)
        if isinstance(out, np.ndarray) and out.dtype.kind in "fc":
            return (np.real(out) > 0.5).astype(np.float64)
        return out
    return w


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Compile validated specs into typed Op wrappers.

    Fail-closed: a spec whose `halcon` name is not a real HALCON operator, or
    whose `shape` is unknown, is dropped (never counted). One op claims one
    HALCON name; later duplicates for the same name are skipped.

    "Not a real operator" includes the case where the reference set itself is
    unavailable: an unverifiable name is dropped as `unverified_name`, never
    admitted. The previous `if real and ...` short-circuit meant an empty
    reference (a wheel install, before `_real_ops` gained its shipped mirror)
    silently compiled EVERY spec, fabricated names included.
    """
    real = _real_ops()
    ops_out, seen, dropped = [], set(), []
    for s in load_specs():
        name = s.get("halcon", "")
        shape = s.get("shape", "")
        if name not in real:
            dropped.append(("fake_name" if real else "unverified_name", name))
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
        out_sort = s.get("out_sort", "image")
        if shape == "geom" and out_sort == "region":
            fn = _rebinarise(fn)            # geometry interpolates; a region must stay {0,1}
        opname = name if name not in ("threshold", "identity") else "h_" + name
        ops_out.append(Op(opname, s.get("category", "misc"), name,
                          s.get("in_sort", "image"), out_sort,
                          _safe(fn, out_sort)))
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
