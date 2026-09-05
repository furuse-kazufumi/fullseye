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

from backend_safe import gradient_normals, signed01, subpixel_refine_edges
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
            # gain > 1 は log 変換の出力を 1 より上へ押し上げる(実測 max=1.1380,
            # a=0.5)。`image` は [0,1] 契約なので op の出口で clip する
            # (`ops._apply` は段間で同じ clip を掛けているので **パイプライン結果は
            # ビット不変**、直接 `fullseye.apply` した時だけ白飛びが消える)。
            return np.clip(skexp.adjust_log(x, gain=0.5 + 1.5 * a), 0, 1) if _HAS_SK \
                else _norm(np.log1p(x))
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
    """FFT-domain image ops.

    ★正規化の規約(2026-09-02 修正): **符号つきの応答は `signed01`、非負の応答は
    `_norm`**。`highpass` / `bandpass` / `ifft` は零平均の *符号つき* 応答
    (帯域を落とせば必ず負の半分が出る)なのに `_norm` を通していたため、
    `image` を名乗りながら値域 [-1,1] の配列を返していた。実測(camera.png,
    a=0.2,b=0.5): `highpass_image` min=-0.6067 / 負 50.2%、`bandpass_image`
    min=-0.8812 / 負 49.8%、`fft_image_inv` 負 49.4%。`image` として保存・表示
    すると **画素の約半分が無言で真っ黒に潰れる**(`ops._apply` の段間 clip でも
    同じことが起きる)。core の兄弟 `ops._highpass` は最初から `_signed01` を
    通しており、**兄弟の間で規約が割れていた**のが本体。

    非負の応答(`fft_power` = log1p|F|、`fft_power_real` = |Re F|、`lowpass` =
    低域だけを残した実信号)は従来どおり。`fft_phase` は角度を [0,1] へ写す
    自前の規約で、これも符号問題は無い。
    """
    kind = p["kind"]

    def fn(v, a, b):
        x = np.asarray(v, np.float64)
        F = np.fft.fftshift(np.fft.fft2(x))
        if kind == "fft_power":
            return _norm(np.log1p(np.abs(F)))        # |.| >= 0 -> _norm で [0,1]
        if kind == "fft_power_real":
            return _norm(np.abs(np.real(F)))         # |.| >= 0 -> _norm で [0,1]
        if kind == "fft_phase":
            return (np.angle(F) + np.pi) / (2 * np.pi)
        if kind == "ifft":                           # inverse Fourier transform (fft_image_inv)
            return signed01(np.real(np.fft.ifft2(x)))   # 符号つき -> 0 が 0.5
        H, W = x.shape
        rad = np.sqrt(np.fft.fftfreq(H)[:, None] ** 2 + np.fft.fftfreq(W)[None, :] ** 2)
        if kind == "lowpass":
            return np.clip(np.real(np.fft.ifft2(np.fft.fft2(x) * (rad <= (0.05 + 0.4 * a)))), 0, 1)
        if kind == "highpass":
            return signed01(np.real(np.fft.ifft2(       # 符号つき -> 0 が 0.5
                np.fft.fft2(x) * (rad > (0.02 + 0.3 * a)))))
        if kind == "bandpass":
            lo, hi = 0.02 + 0.15 * a, 0.2 + 0.3 * b
            return signed01(np.real(np.fft.ifft2(       # 符号つき -> 0 が 0.5
                np.fft.fft2(x) * ((rad > lo) & (rad < hi)))))
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
            # 向きの規約: a=0 (θ=0) が **縦縞**、a=0.5 (θ=90°) が横縞に応答する。
            # 正規化はカーネル L1(画像に依らない固定スケール)—— core の
            # `ops._gabor` と同じ。`_norm` (画像ごとの最大値で割る) は向きによる
            # 応答の大小を潰してしまう(実測 54.9 倍 -> 1.35 倍)。
            theta, freq = np.pi * a, 0.1 + 0.3 * b
            yy, xx = np.mgrid[-7:8, -7:8]
            xr = xx * np.cos(theta) + yy * np.sin(theta)
            g = np.exp(-(xx * xx + yy * yy) / 8.0) * np.cos(2 * np.pi * freq * xr)
            g = g - g.mean()   # DC-free (zero-mean) kernel: a Gabor is band-pass, not a brightness detector
            l1 = float(np.abs(g).sum())
            resp = np.abs(ndimage.convolve(x, g, mode="reflect"))
            return np.clip(resp / l1, 0, 1) if l1 > 1e-12 else np.zeros_like(resp)
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
            # ★キャンバスを変えない(reshape=False)+ 枠外は鏡映(mode="reflect")。
            #   角度は -45°..+45°(a=0.5 で 0°)。四隅には元画像が **折り返して**
            #   写り込むので、帳票の傾き補正 (deskew) のように「枠外は背景色で
            #   埋めたい」用途にはそのままでは向かない(既知の設計判断であって
            #   バグではない — 詳細と使い分けは `ops._rotate_img` の docstring)。
            return np.clip(ndimage.rotate(x, -45 + 90 * a, reshape=False, mode="reflect"), 0, 1)
        if kind == "zoom":                            # 等方ズーム(zoom_region など)
            s = 0.7 + 0.6 * a
            off = (x.shape[0] * (1 - 1 / s) / 2, x.shape[1] * (1 - 1 / s) / 2)
            return np.clip(ndimage.affine_transform(x, np.diag([1 / s, 1 / s]),
                                                    offset=off, mode="reflect"), 0, 1)
        if kind == "zoom_factor":                     # HALCON zoom_image_factor
            # ScaleHeight = a, ScaleWidth = b の **2 つの倍率**(HALCON と同じ)。
            # キャンバスは保つ(内容だけを中心基準で拡大縮小)。
            sr, sc = 0.7 + 0.6 * a, 0.7 + 0.6 * b
            off = (x.shape[0] * (1 - 1 / sr) / 2, x.shape[1] * (1 - 1 / sc) / 2)
            return np.clip(ndimage.affine_transform(x, np.diag([1 / sr, 1 / sc]),
                                                    offset=off, mode="reflect"), 0, 1)
        if kind == "zoom_size":                       # HALCON zoom_image_size
            # **目標サイズ**指定: 入力画像 *全体* を (Ht, Wt) = (H(0.5+a), W(0.5+b))
            # 画素ちょうどへリサンプルする。決まるのは倍率ではなく **サイズ**で、
            # 縦横が独立なので zoom_image_factor(倍率 2 つ・中心固定)とは別物。
            #
            # ★ただし戻り値の shape は **入力と同じキャンバス**に保つ。この registry の
            #   image は「段間で無条件に繋がる」契約で、shape を変えると評価器が
            #   目標画像と突き合わせられずに落ちる(実測: 目標サイズ版が (70,50) を
            #   返した瞬間 `test_evolve_is_reproducible_given_seed` が
            #   "operands could not be broadcast together with shapes (70,50) (64,64)"
            #   で失敗した)。そこで Ht x Wt にリサンプルした像をキャンバス左上に置き、
            #   余白は 0、はみ出す分は切る —— 「画像が今 Ht x Wt 画素である」ことは
            #   そのまま見える。
            H, W = x.shape[:2]
            ht = max(1, int(round(H * (0.5 + a))))
            wt = max(1, int(round(W * (0.5 + b))))
            small = ndimage.affine_transform(x, np.diag([H / ht, W / wt]),
                                             output_shape=(ht, wt), order=1, mode="reflect")
            out = np.zeros((H, W), np.float64)
            hh, ww = min(H, ht), min(W, wt)
            out[:hh, :ww] = small[:hh, :ww]
            return np.clip(out, 0, 1)
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
            #
            # **Use the return value, not the buffer we passed in.** cv2 is free to
            # allocate its own output and hand it back; the `dst` argument is a hint,
            # not a promise. Measured on cv2 5.0.0 (2026-09-02): the forward call
            # happens to return the same object (`ret is dst` -> True) but the
            # inverse one does NOT (`False`, 3139 non-zero pixels in the returned
            # array against 0 in `dst`). Reading `dst` therefore produced an
            # all-black image for every input — see the inverse branch below.
            dst = np.zeros((h, w), np.float32)
            out = cv2.warpPolar(x.astype(np.float32), (w, h), (w / 2, h / 2),
                                min(h, w) / 2, cv2.WARP_POLAR_LINEAR, dst)
            return np.clip(np.asarray(out, np.float64), 0, 1)
        if kind == "polar_inv" and _HAS_CV:          # inverse polar->Cartesian (polar_trans_image_inv)
            h, w = x.shape
            # Cartesian corners fall outside the polar disc and are never written;
            # zero-init for determinism (see the forward branch above).
            #
            # 2026-09-02: this branch read `dst` instead of the return value and so
            # returned **an all-zero image for every input** — measured 360/360
            # calls with zero non-zero pixels, across 4 sizes x 3 contents x 15 knob
            # settings. It went unnoticed because the existing guards
            # (`tests/test_known_bugs.py`) check determinism and the [0,1] range,
            # and an all-black image passes both.
            radius = min(h, w) / 2
            dst = np.zeros((h, w), np.float32)
            out = np.asarray(
                cv2.warpPolar(x.astype(np.float32), (w, h), (w / 2, h / 2), radius,
                              cv2.WARP_POLAR_LINEAR + cv2.WARP_INVERSE_MAP, dst),
                np.float64)
            # cv2 が**書かなかった画素は未初期化のまま**返ってくる(戻り値は自前で
            # 確保した新しいバッファで、渡した dst は使われない)。そこを読むと
            # 実行ごとに値が変わる ―― これが Bug A の本体で、これまでは「dst を
            # 読んで全ゼロ」だったせいで決定的に見えていただけだった。
            #
            # 書かれる範囲は中心からの半径 R の円盤だが、境界の双線形補間の
            # ぶんだけ実際はわずかに内側で終わる。実測 2026-09-02(8 プロセス x
            # 4 サイズ 32/48/64/96): 非決定的な画素が円盤内へ食い込む深さは
            # **最大 0.911 画素**、それより内側は一度も変動しなかった。
            # 1 画素の余裕を取って外側を 0 で塗る(0 は「写像の外」を表す既定値で、
            # 元の実装が意図していたもの)。
            yy, xx = np.mgrid[0:h, 0:w]
            rr = np.hypot(xx + 0.5 - w / 2, yy + 0.5 - h / 2)
            out = np.where(rr <= radius - 1.0, out, 0.0)
            return np.clip(out, 0, 1)
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
        if metric == "area_center":
            # HALCON area_center = (Area, Row, Column)。1 スカラでは表せないので
            # match sort の 1-D ベクトルで 3 つとも返す(`ops._ncc_locate` と同形)。
            # 3 成分とも **解像度に依らない** よう [0,1] 正規化する:
            #   [0] 面積 / 画像画素数、[1] 重心行 / (H-1)、[2] 重心列 / (W-1)。
            # 領域が空のときは (0, 0.5, 0.5) = 面積ゼロ・中心は画像中心(fail-soft)。
            H, W = m.shape[:2]
            area = float(m.sum())
            if area <= 0:
                return np.array([0.0, 0.5, 0.5])
            ys, xs = np.nonzero(m)
            return np.array([area / float(m.size),
                             float(ys.mean()) / max(H - 1, 1),
                             float(xs.mean()) / max(W - 1, 1)])
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


#: ``ndimage.laplace`` の 5 点カーネル [[0,1,0],[1,-4,1],[0,1,0]] のノイズ利得。
#: 独立同分布ノイズ σ を通すと分散は (-4)^2 + 4*1^2 = 20 倍になるので、応答の
#: 標準偏差は sqrt(20)*σ。実測(平坦画像 + ガウス雑音 512x512、σ=0.01..0.30):
#: 1.4826*MAD(lap)/σ = 4.4501 .. 4.4816 で sqrt(20)=4.4721 と 0.5% 以内で一致。
_LAPLACE_NOISE_GAIN = float(np.sqrt(20.0))


def _noise_sigma(x):
    """Robust estimate of the additive-noise **standard deviation σ**, in gray levels.

    返すのは「[0,1] 階調でのノイズ σ」そのもの(単位つきの量)。ラプラシアン応答の
    MAD を正規分布換算(×1.4826)し、カーネルのノイズ利得 sqrt(20) で割る。MAD なので
    エッジや構造の外れ値には鈍い。

    ★2026-09-02 の修正。旧実装は ``min(1.0, 1.4826*MAD*3)`` で、

      * σ の単位ですらなかった(σ=0.02 の画像に 0.3523 を返していた)
      * σ≈0.08 以上で **1.0 に張り付いて単調でなくなっていた**。実測
        (camera.png + ``add_noise_white(0.5, b)``、σ = 0.02+0.2b を 11 点):
        [0.3523, 0.6063, 0.8492, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        —— **11 点中 8 点が厳密に 1.0**。ノイズが 3 倍違っても同じ値を返す
        「推定量」を、飽和したという印もなしに返していた。

    現在の値域: 入力は [0,1] に clip されるので σ が 1.0 に達することは実際上ない
    (一様分布でも σ=0.289)。したがって上限 1.0 の clip は **到達しない安全弁**で
    あって動作域ではない。飽和が起きるのは σ>=1 の異常入力だけ。
    """
    lap = ndimage.laplace(x)
    mad = float(np.median(np.abs(lap - np.median(lap))))
    return np.float64(min(1.0, 1.4826 * mad / _LAPLACE_NOISE_GAIN))


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
        if metric == "noise_est":
            return _noise_sigma(x)
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
            # ★2026-09-02: 返していたのは `np.where` の **整数画素座標** そのもので、
            #   `sub_pix` を名乗りながらサブピクセル精度が無かった。放物線当てはめ
            #   による法線方向の精密化を追加(core `ops._edges_sub_pix` と同じ
            #   共有ヘルパ。同名 op はレジストリで後勝ちなので、実際に走るのは
            #   こちら —— core だけ直しても効かない)。
            #   実測(真の位置が列 20.37 の合成ステップエッジ、a=0.2): 旧実装の
            #   返す列は {20.0, 21.0} で平均絶対誤差 0.500 px、精密化後は
            #   {20.324, 20.370} で 0.0228 px(約 22 倍改善)。
            #   点の個数・連結成分の分け方は不変(座標が 1 px 未満動くだけ)。
            x = np.asarray(v, np.float64)
            g, ny, nx = gradient_normals(x)
            m = _norm(g)
            lab, n = ndimage.label(m > (0.15 + 0.5 * a), structure=np.ones((3, 3)))
            cs = []
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                if len(ys) >= 3:
                    pts = np.stack([ys, xs], 1).astype(np.float64)
                    cs.append(subpixel_refine_edges(pts, m, ny, nx))
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
MAT = "match"       # 1-D vector result (score/座標を運ぶ。ops._ncc_locate と同じ形)

SEED: list[tuple] = [
    # ---- Filters: pointwise math -----------------------------------------
    ("abs_image", "arithmetic", IMG, IMG, "pointwise", {"func": "abs"},
     '画素値の絶対値を取る(``np.abs``)。fullseye の ``image`` は既に [0,1] 契約\n(非負)なので、通常の画像に対しては何も変えない**恒等写像**として働く。差分\n画像など符号つきの中間結果を直接渡したときだけ意味を持つ。HALCON の\n``abs_image``（Calculate the absolute value (modulus) of an image.）の代役。\n\n``a``, ``b`` は未使用。clip 前の生値 ``v`` にそのまま ``abs`` を掛けている点に\n注意(他の pointwise 分岐は ``x = clip(v,0,1)`` を使うが、この分岐だけ ``v``\nを直接見る)。'),
    ("sqrt_image", "arithmetic", IMG, IMG, "pointwise", {"func": "sqrt"},
     '[0,1] に clip した画素値の平方根を取る。暗部を持ち上げるガンマ的な階調\n圧縮になる(√x は x=0.25 を 0.5 へ、x=0.04 を 0.2 へ押し上げる)。HALCON の\n``sqrt_image``（Calculate the square root of an image.）に相当。\n\n``a``, ``b`` は未使用 —— 固定の平方根写像で調整点はない。強さを変えたいなら\n``gamma_image``(exponent が ``a`` で振れる)を使う。'),
    ("exp_image", "arithmetic", IMG, IMG, "pointwise", {"func": "exp"},
     '``(exp(x) - 1) / (e - 1)`` という指数写像で [0,1] を [0,1] に写す(x=1 で\nちょうど 1 になるよう正規化してある)。低い階調を圧縮し明部を強調する\nコントラスト強調で、``log_image`` とは逆向きのカーブ。HALCON の\n``exp_image``（Calculate the exponentiation of an image.）の代役。\n\n``a``, ``b`` は未使用。底(``e``)や倍率を変える調整点は無い —— 曲率を変えたい\n場合は ``gamma_image``(``a`` でべき指数を振れる)を使う。'),
    ("log_image", "arithmetic", IMG, IMG, "pointwise", {"func": "log"},
     '``log1p(x) / log(2)`` で [0,1] を [0,1] に写す対数圧縮(x=1 で 1 になる\n正規化つき)。明部を圧縮し暗部のディテールを持ち上げる、``exp_image`` と逆の\nトーンカーブ。HALCON の ``log_image``（Calculate the logarithm of an image.）\nの代役。\n\n``a``, ``b`` は未使用。ゲイン付き対数変換が欲しい場合は\n``lut`` の ``log_gain`` 分岐(``a`` でゲインを振れる、ただし SEED には未登録)\nに近い実装が別途ある。'),
    ("sin_image", "arithmetic", IMG, IMG, "pointwise", {"func": "sin"},
     '``(sin(2πx) + 1) / 2`` で階調を正弦波状に折り返す周期 LUT。x=0 と x=1 で\n0.5 に戻り、x=0.25/0.75 付近で 0/1 に達する ―― 単調増加ではなく**同じ出力を\n複数の入力階調が共有する**非可逆変換になる。HALCON の ``sin_image``\n（Calculate the sine of an image.）の代役。\n\n``a``, ``b`` は未使用。周期や位相を変える調整点は無い。等高線状の疑似カラー\n効果や階調の折返しを作る用途向けで、通常のコントラスト調整には向かない。'),
    ("cos_image", "arithmetic", IMG, IMG, "pointwise", {"func": "cos"},
     '``(cos(2πx) + 1) / 2`` による周期 LUT。``sin_image`` と位相が π/2 ずれた\n版で、x=0 で最大(1)、x=0.5 で最小(0)に達してから再び上がる。HALCON の\n``cos_image``（Calculate the cosine of an image.）の代役。\n\n``a``, ``b`` は未使用。``sin_image`` と同じく非単調・非可逆な周期写像なので、\n一般のコントラスト補正ではなく擬似的な等高線表現などに使う。'),
    ("asin_image", "arithmetic", IMG, IMG, "pointwise", {"func": "asin"},
     '``arcsin(x) / (π/2)`` で [0,1] を [0,1] に写す逆正弦 LUT。x=0 近傍と x=1\n近傍で傾きが急峻になり(定義域端で導関数が発散する)、中間階調を圧縮して\n両端のコントラストを強調する効果を持つ。HALCON の ``asin_image``\n（Calculate the arcsine of an image.）の代役。\n\n``a``, ``b`` は未使用。端点付近で数値的に敏感になる点に注意(x が 1 にごく\n近いとわずかな量子化誤差でも出力が大きく動く)。'),
    ("acos_image", "arithmetic", IMG, IMG, "pointwise", {"func": "acos"},
     '``arccos(x) / π`` で [0,1] を [0,1] に写す逆余弦 LUT。``asin_image`` を\n反転させた形(単調減少)で、x=0 で最大(1)、x=1 で最小(0)になる。HALCON の\n``acos_image``（Calculate the arccosine of an image.）の代役。\n\n``a``, ``b`` は未使用。``asin_image`` と同様に端点近傍で傾きが急峻になる\n(数値的に敏感)。単純な階調反転がしたいだけなら ``invert_image`` の方が\n挙動が読みやすい。'),
    ("atan_image", "arithmetic", IMG, IMG, "pointwise", {"func": "atan"},
     '``arctan(x) / (π/2)`` で [0,1] を [0,1] に写す逆正接 LUT。中心付近\n(x≈0.5)で傾きが最大、両端に近づくほど傾きが緩やかになる ―― ``asin_image``\nとは逆に**両端でなく中間のコントラストを強調する**S字カーブ。HALCON の\n``atan_image``（Calculate the arctangent of an image.）の代役。\n\n``a``, ``b`` は未使用。傾きの急峻さを変える調整点は無い固定カーブ。'),
    # ---- Filters/Image: gray LUT -----------------------------------------
    ("gamma_image", "gray", IMG, IMG, "lut", {"kind": "gamma"},
     'ガンマ補正 ``x ** (0.3 + 2.5*a)``。``a`` が 0 に近いほど指数は 0.3 に\n近づき暗部を持ち上げ、``a`` が 1 に近いほど指数は 2.8 に近づき暗部を潰して\nコントラストを強める。HALCON の ``gamma_image``（Perform a gamma encoding or\ndecoding of an image.）の代役。\n\n``a`` はガンマ指数を 0.3〜2.8 の範囲で振る。``b`` は未使用。HALCON の実装は\nEncode/Decode の切替や AmpFactor など複数パラメータを持つが、ここでは\n単純なべき乗写像 1 本に単純化している(近似)。'),
    ("pow_image", "gray", IMG, IMG, "lut", {"kind": "gamma"},
     '実装は ``gamma_image`` と**まったく同じ関数**(``_sh_lut`` の ``kind:\n"gamma"`` 分岐)を指す。つまり ``pow_image`` と ``gamma_image`` は\nこのバックエンド上では計算結果が一致する ―― HALCON では別の演算子(指数を\n明示的に指定する ``pow_image`` と符号化/復号を意図した ``gamma_image``)\nだが、ここでは代役の実体が重複している(近似の限界として明記)。\n\n``a`` がべき指数を 0.3〜2.8 の範囲で振る。``b`` は未使用。HALCON の\n``pow_image``（Raise an image to a power.）の代役。'),
    ("invert_image", "gray", IMG, IMG, "lut", {"kind": "invert"},
     '階調を反転する ``1.0 - x``(ネガポジ反転)。HALCON の ``invert_image``\n（Invert an image.）にそのまま対応する、近似ではなく厳密に等価な演算。\n\n``a``, ``b`` は未使用 ―― 調整点のない固定変換。'),
    ("scale_image", "gray", IMG, IMG, "lut", {"kind": "scale"},
     '線形の階調スケーリング ``clip((0.5 + 1.5*a) * x + (b - 0.5), 0, 1)``。\n傾き(コントラスト)とオフセット(明るさ)を同時に動かすリニア LUT で、\nはみ出した値は [0,1] にクリップされる。HALCON の ``scale_image``（Scale the\ngray values of an image.）に相当。\n\n``a`` は傾き(Mult 相当)を 0.5〜2.0 の範囲で、``b`` はオフセット(Add 相当)を\n-0.5〜+0.5 の範囲で振る。両方が使われる。'),
    ("equ_histo_image", "gray", IMG, IMG, "lut", {"kind": "equalize"},
     '画像全体のヒストグラム平坦化(累積分布関数によるトーンカーブ生成、256\nビン)。暗部・明部に偏った階調分布を均して見かけのコントラストを上げる古典的\nな手法。HALCON の ``equ_histo_image``（Histogram linearization of images）\nに相当。\n\n``a``, ``b`` は未使用。局所版(ブロックごとに平坦化)が欲しい場合は\n``equ_histo_image_rect`` を使う。'),
    ("illuminate", "gray", IMG, IMG, "lut", {"kind": "illuminate"},
     'アンシャープマスク型の局所コントラスト強調。``sm`` = ガウシアンぼかし\n(半径 ``3+12*a``)を引いた差分 ``x - sm`` を元画像に足し戻すことで、\n低周波の照明ムラを残しつつ局所的なエッジ・テクスチャを持ち上げる。HALCON の\n``illuminate``（Illuminate image.）の代役。\n\n``a`` はぼかしの強さ(構造とみなすスケール、シグマ 3〜15)を、``b`` は強調の\n強さ(0.3〜1.0)を振る。両方が使われる。強すぎるとハローアーティファクトが\n出る。'),
    ("scale_image_max", "gray", IMG, IMG, "lut", {"kind": "rescale"},
     '画像の最小値〜最大値を [0,1] いっぱいに引き伸ばす min-max 正規化\n(``(x - min) / (max - min)``、定数画像なら無変更)。HALCON の\n``scale_image_max``（Maximum gray value spreading in the value range 0 to\n255.）に相当(値域は 0〜255 ではなく [0,1] 契約)。\n\n``a``, ``b`` は未使用。画像全体の統計から自動的に決まるため調整の余地が\nない。'),
    # ---- Filters: linear / smoothing -------------------------------------
    ("gauss_filter", "smoothing", IMG, IMG, "linfilter", {"kind": "gauss"},
     'ガウシアンぼかし(``scipy.ndimage.gaussian_filter``、シグマ ``0.3+2.7*a``)\nによる平滑化。HALCON の ``gauss_filter``（Smooth using discrete Gauss\nfunctions.）の代役 ―― HALCON は離散ガウス核(整数演算)、こちらは連続ガウス核\nの scipy 実装で、近似ではあるが結果は非常に近い。\n\n``a`` がシグマを 0.3〜3.0 の範囲で振る。``b`` は未使用。実装は\n``gauss_image`` と同一。'),
    ("gauss_image", "smoothing", IMG, IMG, "linfilter", {"kind": "gauss"},
     '実装は ``gauss_filter`` と同一(同じ ``kind: "gauss"`` 分岐、シグマ\n``0.3+2.7*a`` のガウシアンぼかし)。HALCON では ``gauss_filter``(離散近似)\nと ``gauss_image``(周波数領域/連続ガウス)は別演算子だが、この代役では\n区別せず同じ関数を指す。HALCON の ``gauss_image``（Smooth an image using\ndiscrete Gaussian functions.）の代役。\n\n``a`` がシグマを 0.3〜3.0 の範囲で振る。``b`` は未使用。'),
    ("mean_image", "smoothing", IMG, IMG, "linfilter", {"kind": "mean"},
     '矩形平均フィルタ(box filter)。HALCON の ``mean_image``（Smooth by\naveraging.）に相当する近似で、注目画素を一辺 k の窓の平均で置き換える。\n\n``a`` が窓の一辺 k を ``{3,5,7,9}`` の 4 段階(``_k(a)``)で振る。``b`` は\n未使用。ガウシアンより速いが、エッジがぼやけずに角ばったブロック状の\nアーティファクトを残しやすい。'),
    ("binomial_filter", "smoothing", IMG, IMG, "linfilter", {"kind": "binomial"},
     '二項係数(パスカルの三角形)を重みとする分離型平滑化フィルタ。\n``ndimage.correlate1d`` を縦・横に順に掛けることでガウシアンを離散二項核で\n近似する ―― HALCON の ``binomial_filter``（Smooth an image using the\nbinomial filter.）が使う核と同じ発想の実装。\n\n``a`` が核サイズを ``{3,5,7,9}`` の 4 段階(``_k(a)``)で振る。``b`` は\n未使用。ガウシアンぼかしより計算が軽く、リンギングも出にくい。'),
    ("smooth_image", "smoothing", IMG, IMG, "linfilter", {"kind": "smooth"},
     'ガウシアンぼかし(シグマ ``0.5+2.0*a``)一本で近似した汎用スムージング。\nHALCON の ``smooth_image``（Smooth an image using various filters.）は\nDeriche/Gauss/Mean など複数のフィルタ種別を選べる万能演算子だが、ここでは\nガウシアン 1 種類に単純化している(近似の限界)。\n\n``a`` がシグマを 0.5〜2.5 の範囲で振る。``b`` は未使用。'),
    ("derivate_gauss", "edges", IMG, IMG, "linfilter", {"kind": "derivate_gauss"},
     'ガウス微分(``order=(1,0)`` と ``(0,1)``)の勾配強度 ``hypot`` を [0,1]\nに正規化したもの。ガウシアンで平滑化してから微分するので、ノイズに強い\nエッジ検出器として働く。HALCON の ``derivate_gauss``（Convolve an image\nwith derivatives of the Gaussian.）に相当。\n\n``a`` がガウス核のシグマを 0.5〜3.0 の範囲で振る(平滑化の強さとエッジの\n太さがトレードオフ)。``b`` は未使用。方向別成分(dx, dy)ではなく振幅のみを\n返す点に注意。'),
    ("laplace_of_gauss", "edges", IMG, IMG, "linfilter", {"kind": "laplace_gauss"},
     'LoG(Laplacian of Gaussian、ガウス平滑化後にラプラシアンを掛けた\n二階微分エッジ検出)。``signed01`` により符号つき応答を [0,1] へ写像し\n(0.5 がゼロ交差に相当)、ゼロ交差検出やブロブ検出の下地に使える。HALCON の\n``laplace_of_gauss``（LoG-Operator (Laplace of Gaussian).）に相当。\n\n``a`` がガウス核のシグマを 0.5〜3.0 の範囲で振る。``b`` は未使用。値が 0.5\nから離れるほど強いエッジ/ブロブ応答であることを示す。'),
    ("diff_of_gauss", "edges", IMG, IMG, "linfilter", {"kind": "dog"},
     'DoG(Difference of Gaussians、2 段階の異なるシグマでぼかした画像の差)\nによるバンドパスエッジ/ブロブ検出。LoG の高速近似として知られる古典的手法。\nHALCON の ``diff_of_gauss``（Approximate the LoG operator (Laplace of\nGaussian).）に相当。\n\n``a`` が狭い側のシグマ(0.5〜2.5)、``b`` が広い側のシグマ(1〜5)を振る ―― 両方\nが使われ、``b`` の方を大きくとることで帯域幅が決まる。応答は絶対値を取って\nから正規化しているため符号情報は失われる。'),
    ("mean_curvature_flow", "smoothing", IMG, IMG, "linfilter", {"kind": "mean_curvature"},
     '小さなシグマ(0.6)のガウシアンぼかしを繰り返し適用することで平均曲率流を\n**近似**したスムージング。真の平均曲率 PDE(``ops`` 側の別実装が本来やる\n拡散方程式)ではなく、反復ぼかしという計算コストの軽い代用になっている点が\nこのバックエンド固有の近似の限界。HALCON の ``mean_curvature_flow``\n（Apply the mean curvature flow to an image.）の代役。\n\n``a`` が反復回数を 1〜7 回の範囲で振る(回数が多いほど強く滑らかになる)。\n``b`` は未使用。'),
    # ---- Filters: rank ----------------------------------------------------
    ("median_image", "rank", IMG, IMG, "rank", {"kind": "median"},
     'メディアンフィルタ(``ndimage.median_filter``、正方窓)。窓内の中央値で\n置き換えるノイズ除去で、平均フィルタと違いエッジを保ったまま塩胡椒ノイズを\n除去できる。HALCON の ``median_image``（Compute a median filter with\nvarious masks.）に相当(HALCON は円形・八角形等の任意マスクを選べるが、\nここでは正方形マスクに固定)。\n\n``a`` が窓の一辺を ``{3,5,7,9}``(``_k(a)``)で振る。``b`` は未使用。'),
    ("median_rect", "rank", IMG, IMG, "rank", {"kind": "median_rect"},
     '矩形メディアンフィルタ。``median_image`` と同じ ``scipy`` 実装だが、\n高さと幅を独立に指定できる(``size=(k_a, k_b)``)。HALCON の ``median_rect``\n（Compute a median filter with rectangular masks.）に相当。\n\n``a`` が窓の高さ、``b`` が窓の幅を、それぞれ ``{3,5,7,9}``(``_k``)の 4 段階\nで振る。両方が使われる。'),
    ("median_separate", "rank", IMG, IMG, "rank", {"kind": "median"},
     '実装は ``median_image`` と同じ(``kind: "median"``、正方窓の 2 次元\nメディアン)。HALCON の ``median_separate``（Separated median filtering with\nrectangle masks.）は行方向・列方向に分離した 1 次元メディアンを 2 パス\n掛ける高速近似演算子だが、この代役では区別せず通常の 2 次元メディアンを\n返す(結果は近い場合が多いが厳密には別アルゴリズム ―― 近似の限界)。\n\n``a`` が窓の一辺を ``{3,5,7,9}`` で振る。``b`` は未使用。'),
    ("gray_erosion_rect", "rank", IMG, IMG, "rank", {"kind": "min"},
     '矩形窓内の最小値を返すグレースケール収縮(``ndimage.minimum_filter``)。\n明るい細線・小突起を暗部側から侵食して消す。HALCON の\n``gray_erosion_rect``（Determine the minimum gray value within a\nrectangle.）に相当。\n\n``a`` が窓の一辺を ``{3,5,7,9}``(``_k(a)``)で振る。``b`` は未使用。'),
    ("gray_dilation_rect", "rank", IMG, IMG, "rank", {"kind": "max"},
     '矩形窓内の最大値を返すグレースケール膨張(``ndimage.maximum_filter``)。\n暗い細線・小穴を明部側から埋めて消す、``gray_erosion_rect`` と対の演算。\nHALCON の ``gray_dilation_rect``（Determine the maximum gray value within a\nrectangle.）に相当。\n\n``a`` が窓の一辺を ``{3,5,7,9}`` で振る。``b`` は未使用。'),
    ("gray_range_rect", "rank", IMG, IMG, "rank", {"kind": "range"},
     '矩形窓内の最大値と最小値の差(局所レンジ)を正規化して返す。テクスチャの\n局所的な起伏の激しさ(コントラスト量)を可視化する。HALCON の\n``gray_range_rect``（Determine the gray value range within a rectangle.）\nに相当。\n\n``a`` が窓の一辺を ``{3,5,7,9}`` で振る。``b`` は未使用。平坦な領域では\nほぼ 0、エッジやテクスチャの多い領域で値が大きくなる。'),
    ("rank_image", "rank", IMG, IMG, "rank", {"kind": "rank"},
     '窓内の画素値を昇順に並べて指定パーセンタイル位置の値を返す汎用ランク\nフィルタ(``ndimage.percentile_filter``)。パーセンタイル 0 で収縮相当、\n100 で膨張相当、50 でメディアン相当になる連続的な一般化。HALCON の\n``rank_image``（Compute a rank filter with arbitrary masks.）に相当\n(HALCON は任意形状マスクを取れるが、ここでは正方形マスクに固定)。\n\n``a`` が窓の一辺を ``{3,5,7,9}`` で、``b`` がパーセンタイルを 5〜95% の\n範囲で振る。両方が使われる。'),
    ("rank_rect", "rank", IMG, IMG, "rank", {"kind": "rank"},
     '実装は ``rank_image`` と同一(``kind: "rank"``、正方窓のパーセンタイル\nフィルタ)。HALCON では ``rank_image``(任意マスク)と ``rank_rect``(矩形\nマスク限定)は別演算子だが、この代役ではどちらも同じ正方窓実装を指す。\nHALCON の ``rank_rect``（Compute a rank filter with rectangular masks.）\nの代役。\n\n``a`` が窓の一辺、``b`` がパーセンタイル(5〜95%)を振る。両方が使われる。'),
    ("sigma_image", "smoothing", IMG, IMG, "rank", {"kind": "sigma"},
     'シグマフィルタによる非線形平滑化。中心画素値に近い(``|x-mean|<σ``)\n近傍画素だけを平均する ―― エッジ付近では反対側の階調が平均に混ざらないため、\n平均フィルタよりエッジを保ちやすいノイズ除去になる。HALCON の\n``sigma_image``（Non-linear smoothing with the sigma filter.）に相当。\n\n``a`` が窓の一辺を ``{3,5,7,9}`` で振る(内部の平均計算にも使う)。``b`` が\n許容帯域(シグマ、0.05〜0.4)を振る。両方が使われる。近傍がすべて帯域外の\n画素は元の値のまま残る。'),
    ("trimmed_mean", "rank", IMG, IMG, "rank", {"kind": "trimmed_mean"},
     '20 パーセンタイルと 80 パーセンタイルのフィルタ結果の平均を返すことで\nトリム平均を近似する。外れ値(最小・最大側)の影響を除いた平均に近い値になる\nが、真の「中央 60% を平均する」トリム平均とは計算方法が異なる近似である点に\n注意。HALCON の ``trimmed_mean``（Smooth an image with an arbitrary rank\nmask.）の代役。\n\n``a`` が窓の一辺を ``{3,5,7,9}`` で振る。``b`` は未使用(トリム比率は 20/80\nに固定)。'),
    # ---- Morphology: gray -------------------------------------------------
    ("gray_erosion", "morphology", IMG, IMG, "graymorph", {"op": "erosion"},
     'グレースケール収縮(``ndimage.grey_erosion``)。矩形構造要素(既定\nshape="rect")内の最小値で画素を置き換え、明るい細部を侵食する。HALCON の\n``gray_erosion``（Perform a gray value erosion on an image.）に相当。\n\n``a`` が構造要素のサイズを ``{3,5,7,9}``(``_k(a)``、矩形)で振る。``b`` は\nこのバックエンドの全グレーモルフォロジー op に共通して**未使用**。円形\n構造要素が欲しい場合は ``gray_erosion`` ではなく形状指定つきの派生\n(``*_shape``)を使う。'),
    ("gray_dilation", "morphology", IMG, IMG, "graymorph", {"op": "dilation"},
     'グレースケール膨張(``ndimage.grey_dilation``)。矩形構造要素内の最大値\nで画素を置き換え、暗い細部を埋める、``gray_erosion`` と対の演算。HALCON の\n``gray_dilation``（Perform a gray value dilation on an image.）に相当。\n\n``a`` が構造要素サイズを ``{3,5,7,9}`` で振る。``b`` は未使用。'),
    ("gray_opening", "morphology", IMG, IMG, "graymorph", {"op": "opening"},
     'グレースケールオープニング(収縮の後に同じ構造要素で膨張)。明るい\n小突起・細線を除去しつつ、全体の明るさの分布は概ね保つ。HALCON の\n``gray_opening``（Perform a gray value opening on an image.）に相当。\n\n``a`` が矩形構造要素のサイズを ``{3,5,7,9}`` で振る。``b`` は未使用。'),
    ("gray_closing", "morphology", IMG, IMG, "graymorph", {"op": "closing"},
     'グレースケールクロージング(膨張の後に同じ構造要素で収縮)。暗い小さな\n穴・くぼみを埋める、``gray_opening`` と対の演算。HALCON の\n``gray_closing``（Perform a gray value closing on an image.）に相当。\n\n``a`` が矩形構造要素のサイズを ``{3,5,7,9}`` で振る。``b`` は未使用。'),
    ("gray_opening_shape", "morphology", IMG, IMG, "graymorph", {"op": "opening", "shape": "disk"},
     '円盤形(disk)構造要素を使うグレースケールオープニング。``gray_opening``\nとの違いは構造要素の形だけで、演算そのもの(収縮→膨張)は同じ。HALCON の\n``gray_opening_shape``（Perform a gray value opening with a selected\nmask.）に相当(HALCON は矩形/円/八角形などから選べるが、ここでは円形に\n固定)。\n\n``a`` が構造要素の半径を 1〜4 の範囲(``_rad(a)``)で振る。``b`` は未使用。'),
    ("gray_closing_shape", "morphology", IMG, IMG, "graymorph", {"op": "closing", "shape": "disk"},
     '円盤形構造要素を使うグレースケールクロージング。``gray_closing`` との\n違いは構造要素の形のみ。HALCON の ``gray_closing_shape``（Perform a gray\nvalue closing with a selected mask.）に相当(円形固定の近似)。\n\n``a`` が構造要素の半径を 1〜4 の範囲(``_rad(a)``)で振る。``b`` は未使用。'),
    ("gray_tophat", "morphology", IMG, IMG, "graymorph", {"op": "tophat"},
     'ホワイトトップハット(元画像 − オープニング)。周囲より明るい小さな\n構造(スポット・細線)だけを抽出する。``_norm`` で正規化して返すため、\n絶対的な明るさではなく相対的な突出度になる。HALCON の ``gray_tophat``\n（Perform a gray value top hat transformation on an image.）に相当。\n\n``a`` が矩形構造要素のサイズを ``{3,5,7,9}`` で振る。``b`` は未使用。'),
    ("gray_bothat", "morphology", IMG, IMG, "graymorph", {"op": "bothat"},
     'ブラックトップハット(クロージング − 元画像)。周囲より暗い小さな構造\n(穴・くぼみ)だけを抽出する、``gray_tophat`` と明暗が逆の演算。HALCON の\n``gray_bothat``（Perform a gray value bottom hat transformation on an\nimage.）に相当。\n\n``a`` が矩形構造要素のサイズを ``{3,5,7,9}`` で振る。``b`` は未使用。'),
    # ---- Filters: edges (named kernels) ----------------------------------
    ("sobel_amp", "edges", IMG, IMG, "edge", {"kind": "sobel"},
     'Sobel 勾配の振幅(``hypot(sobel_x, sobel_y)`` を正規化)。縦横それぞれの\n1 次微分カーネルから勾配ベクトルの大きさを求める最も基本的なエッジ検出。\nHALCON の ``sobel_amp``（Detect edges (amplitude) using the Sobel\noperator.）に相当。\n\n``a``, ``b`` は未使用 ―― 固定カーネル 1 種類のみで、シグマや閾値のような\n調整点は無い(ぼかしてから使いたい場合は前段に ``gauss_filter`` 等を挟む)。'),
    ("sobel_dir", "edges", IMG, IMG, "edge", {"kind": "sobel_dir"},
     'Sobel 勾配の向き(``arctan2(dy, dx)`` を [0,1] に写像。0=−π, 1=+π)。\n振幅を返す ``sobel_amp`` と対になる、エッジの走る方向を求める演算。HALCON の\n``sobel_dir``（Detect edges (amplitude and direction) using the Sobel\noperator.）に相当(HALCON は振幅と方向を同時に返すが、ここでは方向のみの\n別 op として分離)。\n\n``a``, ``b`` は未使用。平坦な領域では勾配がほぼゼロベクトルになり、方向は\nノイズに支配される点に注意。'),
    ("prewitt_amp", "edges", IMG, IMG, "edge", {"kind": "prewitt"},
     'Prewitt 勾配の振幅。Sobel と同じ 1 次微分だが重み付けが均一\n(``[1,1,1]``)なカーネルを使う ―― Sobel よりノイズにやや弱いが計算は単純。\nHALCON の ``prewitt_amp``（Detect edges (amplitude) using the Prewitt\noperator.）に相当。\n\n``a``, ``b`` は未使用。固定カーネル 1 種類。'),
    ("prewitt_dir", "edges", IMG, IMG, "edge", {"kind": "prewitt_dir"},
     'Prewitt 勾配の向き。``prewitt_amp`` と対になる方向成分\n(``arctan2`` を [0,1] に写像)。HALCON の ``prewitt_dir``（Detect edges\n(amplitude and direction) using the Prewitt operator.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("roberts", "edges", IMG, IMG, "edge", {"kind": "roberts"},
     'Roberts クロス演算子。2x2 の対角差分(左上−右下、右上−左下)から\n``hypot`` で振幅を求める、最小サイズのエッジ検出カーネル。斜め方向の\nエッジに敏感だがノイズにも敏感。HALCON の ``roberts``（Detect edges using\nthe Roberts filter.）に相当。\n\n``a``, ``b`` は未使用。境界は ``_shift_edge`` でエッジ複製(reflect 相当)\nして扱うため、画像端でも折り返しノイズは出ない。'),
    ("kirsch_amp", "edges", IMG, IMG, "edge", {"kind": "kirsch"},
     'Kirsch コンパスフィルタの振幅。8 方向に回転させたカーネル群それぞれで\n畳み込み、絶対値の最大値を取ることで方向に依らない強いエッジ応答を得る。\nHALCON の ``kirsch_amp``（Detect edges (amplitude) using the Kirsch\noperator.）に相当。\n\n``a``, ``b`` は未使用。8 方向を総当たりするため Sobel/Prewitt より計算量は\n多いが、斜め方向のエッジも同等の感度で拾える。'),
    ("kirsch_dir", "edges", IMG, IMG, "edge", {"kind": "kirsch_dir"},
     'Kirsch コンパスフィルタで最も強く応答した方向のインデックス(8 方向中の\n``argmax``)を [0,1] に正規化して返す。``kirsch_amp`` と対になる方向成分。\nHALCON の ``kirsch_dir``（Detect edges (amplitude and direction) using the\nKirsch operator.）に相当。\n\n``a``, ``b`` は未使用。方向は 8 段階の離散値しか取れない(Sobel/Prewitt の\n連続角度とは分解能が異なる)。'),
    ("frei_amp", "edges", IMG, IMG, "edge", {"kind": "frei"},
     'Frei-Chen 等方性エッジ検出。重み ``√2`` を持つ 2 本のカーネル対から\n``hypot`` で振幅を求める ―― Sobel より各方向への感度差が小さい(等方的)\nとされる古典的カーネル。HALCON の ``frei_amp``（Detect edges (amplitude)\nusing the Frei-Chen operator.）に相当。\n\n``a``, ``b`` は未使用。固定カーネル 2 本のみ(Frei-Chen 本来の全 9 基底の\n一部だけを使った近似)。'),
    ("robinson_amp", "edges", IMG, IMG, "edge", {"kind": "robinson"},
     'Robinson コンパスフィルタの振幅。基本カーネル 2 本をそれぞれ 4 回転\nさせた計 8 本で畳み込み、絶対値の最大を取る(Kirsch と同じ発想の\nコンパス法)。HALCON の ``robinson_amp``（Detect edges (amplitude) using the\nRobinson operator.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("laplace", "edges", IMG, IMG, "edge", {"kind": "laplace"},
     'ラプラシアン(``ndimage.laplace``、有限差分による 2 階微分)の絶対値を\n正規化したもの。方向性を持たない二階微分エッジ検出で、Sobel 系より高周波\nノイズに敏感。HALCON の ``laplace``（Calculate the Laplace operator by using\nfinite differences.）に相当。\n\n``a``, ``b`` は未使用。ノイズを抑えたい場合は事前にぼかすか\n``laplace_of_gauss``(ガウス平滑化込み)を使う。'),
    # ---- Filters: frequency ----------------------------------------------
    ("fft_image", "frequency", IMG, IMG, "freq", {"kind": "fft_power"},
     '2 次元 FFT のパワースペクトルを ``log1p(|F|)`` で圧縮し正規化した画像。\n低周波(直流)成分が中心にくるよう ``fftshift`` 済み。周期的なノイズや\nテクスチャの空間周波数を可視化するのに使う。HALCON の ``fft_image``\n（Compute the fast Fourier transform of an image.）に相当。\n\n``a``, ``b`` は未使用 ―― 画像全体に対するグローバルな FFT で、窓関数や\n帯域選択のような調整点は無い。'),
    ("power_real", "frequency", IMG, IMG, "freq", {"kind": "fft_power_real"},
     'FFT の実部の絶対値 ``|Re(F)|`` を正規化した画像(``fft_image`` の対数\nパワースペクトルとは異なり、対数を取らず実部だけを見る)。HALCON の\n``power_real``（Return the power spectrum of a complex image.）に相当する\n近似(HALCON の本来の定義は |F|² のパワーだが、ここでは実部絶対値で代用)。\n\n``a``, ``b`` は未使用。'),
    ("power_byte", "frequency", IMG, IMG, "freq", {"kind": "fft_power"},
     '実装は ``fft_image`` と同じ(``kind: "fft_power"``、log1p パワース\nペクトル)。HALCON では ``power_byte`` は 8bit 出力用のバイト量子化された\nパワースペクトルを指すが、この代役では ``power_real``/``fft_image`` と\n区別せず同じ処理を返す(近似の限界)。HALCON の ``power_byte``（Return the\npower spectrum of a complex image.）の代役。\n\n``a``, ``b`` は未使用。'),
    ("phase_rad", "frequency", IMG, IMG, "freq", {"kind": "fft_phase"},
     'FFT の位相 ``angle(F)`` をラジアンから [0,1] に線形写像したもの(0=−π,\n1=+π)。パワースペクトルが失う位相情報(構造の空間的な位置情報の大半を\n担う)を可視化する。HALCON の ``phase_rad``（Return the phase of a complex\nimage in radians.）に相当。\n\n``a``, ``b`` は未使用。位相はノイズにきわめて敏感で、平坦な領域ではほぼ\n無意味な値になる点に注意。'),
    ("highpass_image", "frequency", IMG, IMG, "freq", {"kind": "highpass"},
     '周波数領域で低域(半径 ``<= 0.02+0.3*a``)を遮断し、残りを逆 FFT で\n実空間に戻したハイパスフィルタ。零平均の**符号つき**応答になるため\n``signed01`` で [0,1] に写像している(0.5 がゼロ、つまり画素の約半分が\n0.5 未満になるのが正常)。HALCON の ``highpass_image``（Extract high\nfrequency components from an image.）に相当。\n\n``a`` が遮断半径(カットオフ周波数)を振る。``b`` は未使用。単純に\n``> 0.5`` で二値化するとほぼ半分の画素が黒に潰れるので注意(詳細は\n``_sh_freq`` の docstring)。'),
    ("bandpass_image", "frequency", IMG, IMG, "freq", {"kind": "bandpass"},
     '周波数領域で指定した帯域だけを通すバンドパスフィルタ(低域と高域を\n遮断)、逆 FFT で実空間に戻す。``highpass_image`` と同様に零平均の符号つき\n応答なので ``signed01`` で [0,1] に写像する。HALCON の ``bandpass_image``\n（Edge extraction using bandpass filters.）に相当。\n\n``a`` が下限カットオフ、``b`` が上限カットオフを振る。両方が使われる。\n帯域(``b`` 側の上限)を下限より下に設定すると通過域が空になり出力はほぼ\n0.5(ゼロ)一色になる。'),
    # ---- Filters: diffusion / texture ------------------------------------
    ("anisotropic_diffusion", "smoothing", IMG, IMG, "diffusion", {"kind": "anisotropic"},
     'Perona-Malik 型の異方性拡散。上下左右 4 方向の画素差にガウス型の\n伝導度関数 ``exp(-(Δ/K)^2)`` を掛けて反復的に加算する ―― 差が閾値 K より\n大きい(=エッジ)方向には拡散させず、小さい(=平坦)方向だけ滑らかにする\nエッジ保存平滑化。HALCON の ``anisotropic_diffusion``（Perform an\nanisotropic diffusion of an image.）に相当。\n\n``a`` が反復回数を 2〜10 回の範囲で、``b`` が伝導度の閾値 K を 0.05〜0.3\nの範囲で振る。両方が使われる。K が小さいほどエッジを厳しく保護する。'),
    ("isotropic_diffusion", "smoothing", IMG, IMG, "diffusion", {"kind": "isotropic"},
     '実装は単純なガウシアンぼかし(``gaussian_filter``、シグマ\n``0.5+2.5*a``)。等方拡散方程式の解はガウシアン核による畳み込みと数学的に\n等価なので、この近似は理論的にも妥当(異方性拡散のようなエッジ保存効果は\n無く、方向を問わず一様に滑らかになる)。HALCON の ``isotropic_diffusion``\n（Perform an isotropic diffusion of an image.）に相当。\n\n``a`` がシグマ(拡散時間に相当)を 0.5〜3.0 の範囲で振る。``b`` は未使用。'),
    ("coherence_enhancing_diff", "smoothing", IMG, IMG, "diffusion", {"kind": "anisotropic"},
     '実装は ``anisotropic_diffusion`` と同一(``kind: "anisotropic"``)。\n本来の coherence-enhancing diffusion は構造テンソルの固有ベクトルに沿って\n拡散方向を制御する(線状構造をつなげる)手法だが、この代役ではその構造\nテンソル計算を行わず、単純な Perona-Malik 異方性拡散で代用している\n(近似の限界 ―― 線状構造の連結効果は再現されない)。HALCON の\n``coherence_enhancing_diff``（Perform a coherence enhancing diffusion of\nan image.）の代役。\n\n``a`` が反復回数、``b`` が伝導度閾値 K を振る。両方が使われる。'),
    ("bilateral_filter", "smoothing", IMG, IMG, "diffusion", {"kind": "bilateral"},
     'OpenCV のバイラテラルフィルタ(``cv2.bilateralFilter``)。近傍画素を\n空間距離と輝度差の両方で重み付けして平均する、エッジを保ったまま平滑化する\n定番手法。HALCON の ``bilateral_filter``（bilateral filtering of an\nimage.）に相当。\n\n``a`` が空間方向のシグマ(1〜4)を、``b`` が輝度(色)方向のシグマ(0.05〜0.45)\nを振る。両方が使われる。``cv2`` が無い環境ではこの分岐は呼べない。'),
    ("guided_filter", "smoothing", IMG, IMG, "diffusion", {"kind": "bilateral"},
     '実装は ``bilateral_filter`` と同一(``kind: "bilateral"``)。本来の\nガイド付きフィルタ(guided filter、局所線形モデルに基づくエッジ保存平滑化)\nとは数学的に別のアルゴリズムだが、この代役ではバイラテラルフィルタで\n代用している(似た用途=エッジ保存平滑化を満たすための近似、結果の数値は\n一致しない)。HALCON の ``guided_filter``（Guided filtering of an image.）\nの代役。\n\n``a`` が空間シグマ、``b`` が輝度シグマを振る。両方が使われる。'),
    ("deviation_image", "texture", IMG, IMG, "texture", {"kind": "deviation"},
     '矩形窓内の画素値の標準偏差(局所標準偏差、``E[x^2]-E[x]^2`` の平方根)\nを正規化した画像。テクスチャの局所的なばらつき(粗さ)を可視化する。HALCON\nの ``deviation_image``（Calculate the standard deviation of gray values\nwithin rectangular windows.）に相当。\n\n``a`` が窓の一辺を ``{3,5,7,9}`` で振る。``b`` は未使用。平坦な領域では\n0 に近く、テクスチャの激しい領域で値が大きくなる。'),
    ("texture_laws", "texture", IMG, IMG, "texture", {"kind": "variance"},
     "実装は局所分散(``deviation_image`` の分散版、窓内の\n``E[x^2]-E[x]^2``)。本来の Laws' テクスチャフィルタは L5/E5/S5/W5/R5 などの\n1 次元カーネル対から作る 25 種類の畳み込みバンク(エネルギー/エッジ/波状/\n斑点/波紋を捉える)だが、この代役ではその全カーネルバンクではなく単一の\n局所分散で代用している(近似の限界 ―― 方向別・周波数別の情報は失われる)。\nHALCON の ``texture_laws``（Filter an image using a Laws texture filter.）\nの代役。\n\n``a`` が窓の一辺を ``{3,5,7,9}`` で振る。``b`` は未使用。"),
    ("entropy_image", "texture", IMG, IMG, "texture", {"kind": "entropy"},
     '円形窓内のグレースケール Shannon エントロピー(``skimage.filters.rank.\nentropy``、8bit 量子化)を正規化した画像。窓内の階調の「散らばり具合」を\n測るテクスチャ指標で、一様な領域では低く、雑多な階調が混在する領域では\n高くなる。HALCON の ``entropy_image``（Calculate the entropy of gray values\nwithin a rectangular window.）に相当(HALCON は矩形窓、ここでは円形窓を\n使う近似)。\n\n``a`` が窓の半径を 1〜4 の範囲(``_rad(a)``)で振る。``b`` は未使用。skimage\nが無い環境ではこの分岐は呼べない。'),
    ("gen_gabor", "texture", IMG, IMG, "texture", {"kind": "gabor"},
     '単一の Gabor カーネル(向き ``θ=π*a``、周波数 ``0.1+0.3*b``)による\n畳み込み応答の絶対値を、カーネルの L1 ノルムで正規化して返す。DC 成分を\n除いた(平均を引いた)実部のみのカーネルで、指定方向・周波数の縞模様に\n選択的に反応するバンドパステクスチャフィルタ。HALCON の ``gen_gabor``\n（Generate a Gabor filter.）に相当(虚部/位相は持たない実カーネルのみの\n簡易版)。\n\n``a`` が向き θ(0〜180°)を、``b`` が空間周波数(0.1〜0.4)を振る。両方が\n使われる。``a=0`` が縦縞、``a=0.5``(90°)が横縞に応答する規約。'),
    # ---- Transformations: geometric --------------------------------------
    ("mirror_image", "geometry", IMG, IMG, "geom", {"kind": "mirror"},
     '``a`` の値で 3 通りの鏡映を切り替える(``a<0.34``: 上下反転、\n``a<0.67``: 左右反転、それ以外: 転置)。連続的な鏡映変換ではなく離散的な\nモード選択である点に注意。HALCON の ``mirror_image``（Mirror an image.）に\n相当(HALCON は上下/左右/対角を明示的なモード引数で選ぶが、ここでは ``a``\nの値域で疑似的に選ぶ近似)。\n\n``a`` が鏡映モードを 3 段階で選ぶ。``b`` は未使用。'),
    ("transpose_region", "geometry", REG, REG, "geom", {"kind": "transpose"},
     '領域(2 値マスク)を転置する(``x.T``、対角線に関する鏡映=行と列の\n入れ替え)。カテゴリは geometry だが in/out は ``region``。幾何変換の一種\nとして ``_sh_geom`` で実装されているが、転置は補間を伴わないため\n``build()`` の ``_rebinarise`` を通しても値は変化しない(すでに {0,1} の\nまま)。HALCON の ``transpose_region``（Reflect a region about a point.）に\n相当(HALCON の「点に関する反転」とは厳密には別の変換で、行列の転置=\n対角線に関する反転という近似)。\n\n``a``, ``b`` は未使用。'),
    ("rotate_image", "geometry", IMG, IMG, "geom", {"kind": "rotate"},
     '画像を中心を軸に ``-45°〜+45°``(``a`` で決まる)回転する\n(``scipy.ndimage.rotate``、``reshape=False`` でキャンバスサイズを維持)。\n枠外にはみ出す部分は反射(``mode="reflect"``)で埋めるため、四隅には元画像が\n折り返して写り込む(帳票の傾き補正のように「枠外を背景色で埋めたい」用途\nにはそのままでは向かない、既知の設計上の制約)。HALCON の\n``rotate_image``（Rotate an image about its center.）に相当。\n\n``a`` が回転角を -45°〜+45° の範囲で振る。``b`` は未使用。'),
    # ★2026-09-02: この 2 つは `{"kind": "zoom"}` を共有していたため **完全に同一
    #   の実装**で、しかも 2 つとも b を使っていなかった(実測: 同一入力に対する
    #   最大差 0.0、b=0 と b=1 の差 0.0)。HALCON では factor 版が 2 つの倍率、
    #   size 版が目標サイズを取る **別物** なので、kind を分けて実態を名前に合わせた。
    ("zoom_image_factor", "geometry", IMG, IMG, "geom", {"kind": "zoom_factor"},
     '高さ方向・幅方向で独立な倍率(``0.7+0.6*a``, ``0.7+0.6*b``)を持つ等方\nでないズーム。中心を基準にアフィン変換で拡大縮小し、キャンバスサイズは\n変えない(はみ出す/余る部分は反射で埋める)。HALCON の\n``zoom_image_factor``（Zoom an image by a given factor.）に相当し、\nHALCON と同じく **2 つの倍率**(ScaleHeight/ScaleWidth)を取る。\n\n``a`` が縦方向の倍率、``b`` が横方向の倍率を振る。両方が使われる\n(2026-09-02 以前は ``zoom_image_size`` と実装が重複していたが、現在は\n別の ``kind`` に分離済み)。'),
    ("zoom_image_size", "geometry", IMG, IMG, "geom", {"kind": "zoom_size"},
     '目標サイズ(高さ ``H*(0.5+a)``、幅 ``W*(0.5+b)``)へリサンプルする\nズーム。``zoom_image_factor`` が倍率を 2 つ取るのに対し、こちらは**サイズ**\nそのものを縦横独立に指定する ―― HALCON の意味論としては別物。ただし\nこのパイプラインの ``image`` は「入力と同じキャンバスサイズで返る」契約\nなので、リサンプル結果は元の解像度のキャンバス左上に置き、余白は 0、\nはみ出す分は切り捨てる(実際に画像が縮小/拡大されたことは見た目で分かる\nが、配列の shape 自体は変わらない)。HALCON の ``zoom_image_size``\n（Zoom an image to a given size.）に相当。\n\n``a`` が目標高さの比率、``b`` が目標幅の比率を振る。両方が使われる。'),
    ("affine_trans_image", "geometry", IMG, IMG, "geom", {"kind": "affine"},
     '回転(``-20°〜+20°``、``a`` で決まる)とせん断(``b`` で決まる)を組み\n合わせた一般的なアフィン変換。中心を基準に ``ndimage.affine_transform`` を\n適用し、枠外は反射で埋める。HALCON の ``affine_trans_image``（Apply an\narbitrary affine 2D transformation to images.）に相当(HALCON は任意の\n2x3/3x3 変換行列を直接渡せるが、ここでは回転+せん断の 2 パラメータ化に\n限定した近似)。\n\n``a`` が回転角、``b`` がせん断量を振る。両方が使われる。平行移動・独立な\n拡大縮小はこの op では表現できない。'),
    ("polar_trans_image", "geometry", IMG, IMG, "geom", {"kind": "polar"},
     '直交座標→極座標変換(``cv2.warpPolar``)。画像中心を極の中心、\n``min(H,W)/2`` を最大半径として、円環状の内容を横長の展開図に変換する。\n未マッピングの画素は 0 埋め(``dst`` を事前ゼロクリアしてから、cv2 が返す\n戻り値を読む ―― ``dst`` バッファ自体を読むと空になることがある実装上の\n注意点がコードコメントに詳しい)。HALCON の ``polar_trans_image``\n（Transform an image to polar coordinates）に相当。\n\n``a``, ``b`` は未使用 ―― 中心と半径は画像サイズから自動的に決まり、\n調整点は無い。'),
    # ---- Segmentation: thresholding --------------------------------------
    ("threshold", "segmentation", IMG, REG, "threshold", {"method": "fixed"},
     '帯域しきい値処理(``a < x < a+0.5+0.5*b`` を満たす画素を前景とする)。\nHALCON の ``threshold``(Segment an image using global threshold.)は\nMin/Max の 2 値を直接指定する演算子だが、この代役では下限を ``a`` から、\n帯域幅を ``b`` から導出する 1 パラメータ相当の簡略化になっている。登録名は\n``threshold`` が Python 側で予約語的に扱われるため ``h_threshold`` になる\n(spec の ``halcon`` フィールドは ``threshold`` のまま)。\n\n``a`` が下限しきい値(0〜1)を、``b`` が帯域幅(0〜0.5 の追加分)を振る。\n両方が使われる。'),
    ("binary_threshold", "segmentation", IMG, REG, "threshold", {"method": "otsu"},
     "大津の判別分析法(Otsu's method)による自動しきい値二値化\n(``skimage.filters.threshold_otsu``、無ければ平均値で代用)。クラス間分散\nを最大化するしきい値を画像のヒストグラムから自動決定する。HALCON の\n``binary_threshold``（Segment an image using binary thresholding.）に\n相当(HALCON は Otsu 以外の複数アルゴリズムを選べるが、ここでは Otsu 固定)。\n\n``a``, ``b`` は未使用 ―― ヒストグラムから自動決定されるため調整点は無い。"),
    ("auto_threshold", "segmentation", IMG, REG, "threshold", {"method": "otsu"},
     '実装は ``binary_threshold`` と同一(Otsu の判別分析法による自動\nしきい値化)。HALCON の ``auto_threshold``（Segment an image using\nthresholds determined from its histogram.）は本来ヒストグラムの複数の谷\nから**複数のしきい値**(多クラス分割)を決める演算子だが、この代役では\n単一の Otsu しきい値による二値化に単純化している(近似の限界)。\n\n``a``, ``b`` は未使用。'),
    ("dyn_threshold", "segmentation", IMG, REG, "threshold", {"method": "dyn"},
     '局所しきい値処理。局所平均(窓一辺 ``_k(a)`` の ``uniform_filter``)に\nオフセット ``(b-0.5)*0.4`` を加えたものをしきい値として使う ―― 照明ムラの\nある画像でも局所的なコントラストで前景を抽出できる。HALCON の\n``dyn_threshold``（Segment an image using a local threshold.）に相当。\n\n``a`` が局所平均の窓サイズを、``b`` がオフセット(しきい値を上下に振る量)\nを振る。両方が使われる。'),
    ("var_threshold", "segmentation", IMG, REG, "threshold", {"method": "sauvola"},
     'Sauvola の局所適応的二値化(``skimage.filters.threshold_sauvola``、\n窓サイズ ``2*int(a*6)+3``)。局所平均と局所標準偏差の両方を使ってしきい値\nを決めるため、``dyn_threshold`` より照明ムラや低コントラスト文書に強い。\nHALCON の ``var_threshold``（Threshold an image by local mean and standard\ndeviation analysis.）に相当する近似(定式化は似た発想だが Sauvola の式と\nHALCON の式は係数が異なる ―― 同一の数値結果にはならない)。\n\n``a`` が局所窓のサイズを振る。``b`` は未使用(Sauvola の k, r は skimage の\n既定値に固定)。'),
    ("local_threshold", "segmentation", IMG, REG, "threshold", {"method": "local_gauss"},
     '局所ガウス平滑化+オフセットによるしきい値処理(``gaussian_filter(x,\n1+3*a)`` にオフセット ``(b-0.5)*0.3`` を加えたものがしきい値)。\n``dyn_threshold`` と似た発想だが、局所平均を矩形窓でなくガウシアンで\n求める点が異なる。HALCON の ``local_threshold``（Segment an image using\nlocal thresholding.）に相当。\n\n``a`` が平滑化のシグマを、``b`` がオフセットを振る。両方が使われる。'),
    ("hysteresis_threshold", "segmentation", IMG, REG, "threshold", {"method": "hysteresis"},
     'ヒステリシスしきい値処理(``skimage.filters.apply_hysteresis_\nthreshold``)。低いしきい値(``0.2+0.3*a``)を超えた画素のうち、高い\nしきい値(``0.5+0.3*b``)を超えた画素につながっているものだけを前景として\n残す ―― Canny エッジ検出の後処理としても使われる、途切れにくいエッジ\n抽出手法。HALCON の ``hysteresis_threshold``（Perform a hysteresis\nthreshold operation on an image.）に相当。\n\n``a`` が低いしきい値を、``b`` が高いしきい値を振る。両方が使われる。'),
    # ---- Segmentation: edges / regions -----------------------------------
    ("edges_image", "segmentation", IMG, REG, "segment", {"kind": "sk_canny"},
     'Canny エッジ検出(``skimage.feature.canny``、シグマ ``0.5+2*a``)による\n領域抽出。ガウス平滑化→勾配→非極大抑制→ヒステリシスしきい値という多段の\n処理をまとめて行う、広く使われるエッジ検出法。HALCON の ``edges_image``\n（Detect edges using Deriche, Lanser, Shen, or Canny filters.）に相当\n(HALCON は Deriche/Lanser/Shen/Canny を選べるが、ここでは Canny 固定)。\n\n``a`` がガウス平滑化のシグマを振る。``b`` は未使用(内部のヒステリシス\nしきい値は skimage の既定値)。skimage が無い環境ではこの分岐は呼べない。'),
    ("watersheds", "segmentation", IMG, REG, "segment", {"kind": "watershed"},
     '分水嶺(watershed)セグメンテーション。勾配画像を地形とみなし、\n暗い領域(``x < 0.2+0.3*a``)をマーカーとして分水嶺線を求め、その境界線を\n返す。HALCON の ``watersheds``（Extract watersheds and basins from an\nimage.）に相当。\n\n``a`` がマーカーを決める暗さのしきい値を振る。``b`` は未使用。'),
    ("watersheds_threshold", "segmentation", IMG, REG, "segment", {"kind": "watershed"},
     '実装は ``watersheds`` と同一(``kind: "watershed"``)。HALCON の\n``watersheds_threshold``（Extract watershed basins from an image using a\nthreshold.）は本来、隣接する集水域を統合する深さのしきい値を持つ演算子\nだが、この代役では統合しきい値を実装せず ``watersheds`` と同じ結果を返す\n(近似の限界)。\n\n``a`` がマーカーのしきい値を振る。``b`` は未使用。'),
    ("regiongrowing", "segmentation", IMG, REG, "segment", {"kind": "regiongrow"},
     '領域成長の簡易近似。まず高いしきい値(``x > 0.5+0.3*a``)でシード\n(種)領域を作り、それを ``1+4*b`` 回だけ二値膨張して広げる ―― 真の領域成長\n(隣接画素との類似度を逐次判定しながら広げる)ではなく、しきい値+膨張という\n軽量な代用になっている(近似の限界)。HALCON の ``regiongrowing``\n（Segment an image using region growing.）の代役。\n\n``a`` がシードのしきい値を、``b`` が膨張の反復回数を振る。両方が使われる。'),
    ("local_max", "segmentation", IMG, REG, "segment", {"kind": "local_max"},
     '局所極大点検出。``x`` が窓内の最大値(``_k(a)``)に一致し、かつ\n``x > 0.3+0.4*b`` を満たす画素だけを前景とする ―― 平坦な高原状の領域では\n複数の隣接画素が同時に「極大」として残る点に注意(真の孤立点ピークだけを\n残す保証はない)。HALCON の ``local_max``（Detect all local maxima in an\nimage.）に相当。\n\n``a`` が窓サイズを、``b`` が輝度の下限しきい値を振る。両方が使われる。'),
    # ---- Regions: binary morphology --------------------------------------
    ("erosion_circle", "region", REG, REG, "binmorph", {"op": "erosion", "shape": "disk"},
     '円盤形構造要素による二値収縮(``ndimage.binary_erosion``)。前景領域を\n外周から侵食して縮める、最も基本的な二値モルフォロジー演算。HALCON の\n``erosion_circle``（Erode a region with a circular structuring element.）\nに相当。\n\n``a`` が構造要素の半径を 1〜4 の範囲(``_rad(a)``)で振る。``b`` はこの\nバックエンドの二値モルフォロジー op(erosion/dilation/opening/closing の\n円形・矩形いずれも)に共通して**未使用**。'),
    ("dilation_circle", "region", REG, REG, "binmorph", {"op": "dilation", "shape": "disk"},
     '円盤形構造要素による二値膨張(``ndimage.binary_dilation``)。前景領域を\n外側へ広げる、``erosion_circle`` と対の演算。HALCON の\n``dilation_circle``（Dilate a region with a circular structuring\nelement.）に相当。\n\n``a`` が構造要素の半径を 1〜4 の範囲で振る。``b`` は未使用。'),
    ("opening_circle", "region", REG, REG, "binmorph", {"op": "opening", "shape": "disk"},
     '円盤形構造要素による二値オープニング(収縮の後に膨張)。小さな突起や\n細い連結部を除去しつつ、大まかな形状は保つ。HALCON の\n``opening_circle``（Open a region with a circular structuring element.）\nに相当。\n\n``a`` が構造要素の半径を 1〜4 の範囲で振る。``b`` は未使用。'),
    ("closing_circle", "region", REG, REG, "binmorph", {"op": "closing", "shape": "disk"},
     '円盤形構造要素による二値クロージング(膨張の後に収縮)。小さな穴や\nくびれを埋める、``opening_circle`` と対の演算。HALCON の\n``closing_circle``（Close a region with a circular structuring\nelement.）に相当。\n\n``a`` が構造要素の半径を 1〜4 の範囲で振る。``b`` は未使用。'),
    ("erosion_rectangle1", "region", REG, REG, "binmorph", {"op": "erosion", "shape": "rect"},
     '正方形構造要素による二値収縮。``erosion_circle`` との違いは構造要素の\n形のみ(円ではなく正方形)。HALCON の ``erosion_rectangle1``（Erode a\nregion with a rectangular structuring element.）に相当。\n\n``a`` が正方形の一辺を ``{3,5,7,9}``(``_k(a)``)で振る。``b`` は未使用。'),
    ("dilation_rectangle1", "region", REG, REG, "binmorph", {"op": "dilation", "shape": "rect"},
     '正方形構造要素による二値膨張。``dilation_circle`` の矩形版。HALCON の\n``dilation_rectangle1``（Dilate a region with a rectangular structuring\nelement.）に相当。\n\n``a`` が正方形の一辺を ``{3,5,7,9}`` で振る。``b`` は未使用。'),
    ("opening_rectangle1", "region", REG, REG, "binmorph", {"op": "opening", "shape": "rect"},
     '正方形構造要素による二値オープニング。``opening_circle`` の矩形版。\nHALCON の ``opening_rectangle1``（Open a region with a rectangular\nstructuring element.）に相当。\n\n``a`` が正方形の一辺を ``{3,5,7,9}`` で振る。``b`` は未使用。'),
    ("closing_rectangle1", "region", REG, REG, "binmorph", {"op": "closing", "shape": "rect"},
     '正方形構造要素による二値クロージング。``closing_circle`` の矩形版。\nHALCON の ``closing_rectangle1``（Close a region with a rectangular\nstructuring element.）に相当。\n\n``a`` が正方形の一辺を ``{3,5,7,9}`` で振る。``b`` は未使用。'),
    # ---- Regions: transforms ---------------------------------------------
    ("fill_up", "region", REG, REG, "region_trans", {"kind": "fill_up"},
     '領域内部の穴(背景に完全に囲まれた領域)を埋める\n(``ndimage.binary_fill_holes``)。外周とつながっていない背景の孔だけが\n埋まり、外周とつながった凹みは埋まらない。HALCON の ``fill_up``（Fill up\nholes in regions.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("boundary", "region", REG, REG, "region_trans", {"kind": "boundary"},
     '領域からその 1 画素収縮版を引くことで外周境界線(輪郭の内側 1 画素の\nリング)を取り出す。塗りつぶされた領域を輪郭線に変換する。HALCON の\n``boundary``（Reduce a region to its boundary.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("skeleton", "region", REG, REG, "region_trans", {"kind": "skeleton"},
     '位相を保ったまま領域を 1 画素幅の骨格線に細める\n(``skimage.morphology.skeletonize``)。分岐や端点の位置は保存されるため、\n枝分かれした形状の解析(指の本数を数える等)によく使われる。HALCON の\n``skeleton``（Compute the skeleton of a region.）に相当。\n\n``a``, ``b`` は未使用。skimage が無い環境ではこの分岐は呼べない。'),
    ("thinning", "region", REG, REG, "region_trans", {"kind": "thin"},
     '``skimage.morphology.thin``(Zhang-Suen 系の細線化アルゴリズム)による\n1 画素幅化。``skeleton`` と目的は似ているが内部アルゴリズムが異なるため、\n分岐点周辺などで結果がわずかに違うことがある。HALCON の ``thinning``\n（Remove the result of a hit-or-miss operation from a region.）の代役。\n\n``a``, ``b`` は未使用。skimage が無い環境ではこの分岐は呼べない。'),
    ("shape_trans", "region", REG, REG, "region_trans", {"kind": "convex"},
     '領域の凸包(``skimage.morphology.convex_hull_image``)を返す。HALCON の\n``shape_trans``（Transform the shape of a region.）は本来 convex/\nrectangle1/ellipse など複数の変形モードを ``Type`` 引数で選べる演算子\nだが、この代役では凸包 1 種類に固定している(近似の限界)。\n\n``a``, ``b`` は未使用。skimage が無い環境ではこの分岐は呼べない。'),
    ("select_shape_std", "region", REG, REG, "region_trans", {"kind": "select_largest"},
     '連結成分のうち最大の面積を持つものだけを残す(``_largest_label`` で\n選択)。HALCON の ``select_shape_std``（Select regions of a given shape.）\nは ``max_area`` を含む複数の標準基準を選べる演算子だが、ここでは\n「面積最大」1 種類に固定している(近似)。\n\n``a``, ``b`` は未使用。複数領域が同面積の場合は ``argmax`` の実装依存で\nどれか 1 つが選ばれる。'),
    ("select_shape", "region", REG, REG, "region_trans", {"kind": "remove_small"},
     '面積が閾値(``16+a*200`` 画素)未満の連結成分を除去する(小さなノイズ状\n領域の除去)。HALCON の ``select_shape``（Choose regions with the aid of\nshape features.）は面積・円形度・凸性など任意の形状特徴で選別できる\n汎用演算子だが、ここでは面積による足切り 1 種類に固定している(近似)。\n\n``a`` が面積の下限しきい値を振る。``b`` は未使用。'),
    ("distance_transform", "region", REG, IMG, "region_trans", {"kind": "dist_transform"},
     'ユークリッド距離変換(``ndimage.distance_transform_edt``)を最大値で\n正規化した画像。各前景画素について最も近い背景画素までの距離を表す ――\n値が大きいほど領域の「奥」にある画素。出力は ``region`` ではなく\n``image`` 型になる点に注意。HALCON の ``distance_transform``（Compute the\ndistance transformation of a region.）に相当。\n\n``a``, ``b`` は未使用。'),
    # ---- Regions: features -----------------------------------------------
    # ★2026-09-02: 旧仕様は out_sort=feature / metric="area" で、実体は
    #   `np.mean(mask)` = **画像に占める面積比**。HALCON の `area_center` は
    #   (Area, Row, Column) を返す op なので、(1) 中心を返さない (2) 面積が画素数
    #   ではなく比率(= 解像度依存)という二重の食い違いがあった。1 スカラでは
    #   名前を満たせないため、`ncc_locate` と同じ **match sort の 1-D ベクトル**
    #   にして (面積比, 行, 列) を返す。match / feature はどちらも終端 sort
    #   (候補は identity のみ)なので、ゲノム→op の写像は動かない。
    ("area_center", "features", REG, MAT, "region_feat", {"metric": "area_center"},
     '領域の面積と重心を、解像度に依らない正規化済みの 3 成分ベクトル\n(面積比 = 面積/画像画素数、正規化重心行、正規化重心列)として返す。1\nスカラーでは (Area, Row, Column) を表せないため、``match`` ソート(1 次元\nベクトル、``ncc_locate`` と同じ形)で返す点が他の region 特徴 op と異なる。\n領域が空のときは (0, 0.5, 0.5)(面積ゼロ・中心=画像中心)を返す fail-soft\n仕様。HALCON の ``area_center``（Area and center of regions.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("count_obj", "features", REG, FEA, "region_feat", {"metric": "count"},
     '連結成分の個数を数える(``ndimage.label``、既定 8 連結)。HALCON の\n``count_obj``/``connection`` の既定と同じ 8 連結を採用しており、斜めに\n接する 2 つの塊は 1 個として数える(4 連結にすると過剰カウントになる例\n=セルカウントで実測 342 個 vs 327 個、コード内コメント参照)。HALCON の\n``count_obj``（Number of objects in a tuple.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("circularity", "features", REG, FEA, "region_feat", {"metric": "circularity"},
     '円形度 ``4π・面積 / 周囲長²``(1 に近いほど真円に近い)。連結成分が\n複数ある場合は最大面積のものだけを評価する。HALCON の ``circularity``\n（Shape factor for the circularity (similarity to a circle) of a\nregion.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("compactness", "features", REG, FEA, "region_feat", {"metric": "compactness"},
     'コンパクトさ ``周囲長² / (4π・面積) / 10``(円形度の逆数に近い量を\n10 で正規化しただけの実装 ―― この ``/10`` は HALCON の定義に基づく係数\nではなく、値を [0,1] に収めるための便宜的なスケーリングである点に注意)。\nHALCON の ``compactness``（Shape factor for the compactness of a region.）\nに相当する近似。\n\n``a``, ``b`` は未使用。'),
    ("convexity", "features", REG, FEA, "region_feat", {"metric": "convexity"},
     '凸性 ``面積 / 凸包面積``(1 に近いほど凸形状に近い)。``skimage.\nmeasure.regionprops`` の ``area`` と ``area_convex`` の比。HALCON の\n``convexity``（Shape factor for the convexity of a region.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("rectangularity", "features", REG, FEA, "region_feat", {"metric": "rectangularity"},
     '矩形度(``skimage`` の ``extent`` = 面積 / 外接矩形の面積)。値が 1 に\n近いほど、領域が自身の外接矩形を隙間なく埋めていることを示す。HALCON の\n``rectangularity``（Shape factor for the rectangularity of a region.）に\n相当。\n\n``a``, ``b`` は未使用。'),
    ("eccentricity", "features", REG, FEA, "region_feat", {"metric": "eccentricity"},
     '楕円近似による離心率(``skimage.measure.regionprops`` の\n``eccentricity``、0=真円、1に近いほど細長い線分状)。領域を等価な楕円に\nフィットしたときの形状指標。HALCON の ``eccentricity``（Shape features\nderived from the ellipse parameters.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("orientation_region", "features", REG, FEA, "region_feat", {"metric": "orientation"},
     '領域の主軸の向き(``regionprops`` の ``orientation``、[-π/2,π/2] を\n[0,1] へ線形写像)。楕円フィットした際の長軸の傾きを表す。HALCON の\n``orientation_region``（Orientation of a region.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("roundness", "features", REG, FEA, "region_feat", {"metric": "roundness"},
     '真円度 ``4・面積 / (π・長軸長²)``(1 に近いほど真円に近い、\n``circularity`` とは分母に周囲長でなく長軸長を使う点が異なる別の指標)。\nHALCON の ``roundness``（Shape factors from contour.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("diameter_region", "features", REG, FEA, "region_feat", {"metric": "diameter"},
     '等価直径(面積が等しい円の直径)を領域の最大辺長で正規化した値\n(``regionprops`` の ``equivalent_diameter_area``)。HALCON の\n``diameter_region``（Maximal distance between two boundary points of a\nregion.）が定義する「境界上の 2 点間の最大距離」とは厳密には異なる指標\n(等価円直径による近似)。\n\n``a``, ``b`` は未使用。'),
    ("euler_number", "features", REG, FEA, "region_feat", {"metric": "euler"},
     'オイラー数(``skimage.measure.euler_number``、連結成分数から穴の数を\n引いた位相不変量)。値が小さい(負に近い)ほど穴が多いことを示す。HALCON の\n``euler_number``（Calculate the Euler number.）に相当。\n\n``a``, ``b`` は未使用。'),
    # ---- Image: gray-value statistics ------------------------------------
    ("min_max_gray", "features", IMG, FEA, "img_feat", {"metric": "max"},
     '画像の最大階調値のみを返す(``x.max()``)。HALCON の ``min_max_gray``\n（Determine the minimum and maximum gray values within regions.）は本来\n最小値と最大値の**両方**を返す演算子だが、この代役では最大値のみを実装\nしており最小値の情報は失われる(データが欠落した近似 ―― 名前が示す\n「min_max」の半分しか計算していない点は正直に明記しておく)。\n\n``a``, ``b`` は未使用。'),
    ("intensity", "features", IMG, FEA, "img_feat", {"metric": "mean"},
     '画像の平均輝度(``x.mean()``)を返す。HALCON の ``intensity``\n（Calculate the mean and deviation of gray values.）は平均と標準偏差の\n組を返す演算子だが、この代役では平均のみを返す(標準偏差が欲しい場合は\n``gray_histo_abs``(標準偏差 std を返す)を併用する)。\n\n``a``, ``b`` は未使用。'),
    ("gray_histo_abs", "features", IMG, FEA, "img_feat", {"metric": "std"},
     '画像の階調の標準偏差(``x.std()``)を返す。HALCON の ``gray_histo_abs``\n（Calculate the gray value distribution.）は本来ヒストグラム全体\n(各階調のビン度数)を返す演算子だが、この代役ではヒストグラムそのものでは\nなく分布の広がりを表す標準偏差 1 個のスカラーに要約している(近似 ―― この\nパイプラインの ``feature`` ソートが 1 スカラーである契約上の制約)。\n\n``a``, ``b`` は未使用。'),
    ("entropy_gray", "features", IMG, FEA, "img_feat", {"metric": "entropy"},
     'グレースケール階調の Shannon エントロピー(64 ビンヒストグラムから計算\nし、最大値 ``log2(64)=6`` bit で正規化)。階調分布の「ばらつき/情報量」を\n表し、一様な画像ほど値は大きく、単一階調に偏るほど 0 に近づく。HALCON の\n``entropy_gray``（Determine the entropy and anisotropy of images.）は\nエントロピーと異方性の組を返すが、この代役ではエントロピーのみを実装\nしている。\n\n``a``, ``b`` は未使用。'),
    # ---- XLD contours -----------------------------------------------------
    ("edges_sub_pix", "contour", IMG, CON, "xld", {"kind": "edges_sub_pix"},
     'サブピクセル精度のエッジ点抽出。勾配とその法線方向(``gradient_\nnormals``)を求め、しきい値(``0.15+0.5*a``)を超える画素を連結成分化した\n後、放物線当てはめで各点をサブピクセル位置へ精密化する(``subpixel_\nrefine_edges``、``ops`` 側の同名 op と共有する実装 ―― 2026-09-02 修正で\n真の意味でサブピクセルになった。旧実装は整数画素座標をそのまま返して\nいた)。HALCON の ``edges_sub_pix``（Extract sub-pixel precise edges using\nDeriche, Lanser, Shen, or Canny filters.）に相当。\n\n``a`` がエッジ強度のしきい値を振る。``b`` は未使用。'),
    ("lines_gauss", "contour", IMG, CON, "xld", {"kind": "lines_gauss"},
     '線状構造(リッジ)検出。``skimage.filters.frangi``(血管様のリッジ強調\nフィルタ)の応答をしきい値(``0.1+0.4*a``)で二値化し、連結成分を輪郭点群\nとして返す。HALCON の ``lines_gauss``（Detect lines and their width.）が\n本来行う「線の中心線+幅の推定」ではなく、リッジ強調画像のしきい値化に\n単純化している(線幅の情報は返らない近似)。\n\n``a`` がリッジ検出のしきい値を振る。``b`` は未使用。skimage が無い環境\nではこの分岐は呼べない。'),
    ("select_contours_xld", "contour", CON, CON, "xld", {"kind": "select_contours"},
     '既存の輪郭(XLD contour)集合から、点数が閾値(``3+40*a``)以上のものだけ\nを残すフィルタ。HALCON の ``select_contours_xld``（Select XLD contours\naccording to several features.）は面積・円形度など任意の特徴で選別できる\n汎用演算子だが、この代役では点数(長さの代理指標)による足切り 1 種類に\n固定している(近似)。\n\n``a`` が点数のしきい値を振る。``b`` は未使用。'),
    ("smooth_contours_xld", "contour", CON, CON, "xld", {"kind": "smooth_contours"},
     '輪郭の座標列を移動平均(窓幅 ``2*(1+3*a)+1``)で平滑化する。輪郭の\nギザギザ(画素境界由来のジグザグ)を滑らかにする。HALCON の\n``smooth_contours_xld``（Smooth an XLD contour.）に相当。\n\n``a`` が平滑化窓の幅を振る。``b`` は未使用。点数が窓幅以下の短い輪郭は\n平滑化されずそのまま返る。'),
    ("gen_region_contour_xld", "contour", CON, REG, "xld", {"kind": "to_region"},
     '輪郭(点列)を画素グリッドにラスタライズしてから、``1+2*a`` 回だけ\n二値膨張して太らせ、連結した領域マスクを作る(細い線のままだと ``region``\nの {0,1} 契約上「線が繋がって見えない」ことがあるための補強)。HALCON の\n``gen_region_contour_xld``（Create a region from an XLD contour.）に相当。\n\n``a`` が膨張の反復回数(=線の太さ)を振る。``b`` は未使用。'),
    ("length_xld", "features", CON, FEA, "xld", {"kind": "length"},
     'すべての輪郭の線分長(隣接点間のユークリッド距離)を合計した総延長。\n複数の輪郭がある場合はまとめて加算する。HALCON の ``length_xld``（Length\nof contours or polygons.）に相当。\n\n``a``, ``b`` は未使用。'),
    # ---- v11b increment: newly-enabled genuine families ------------------
    # region measurements
    ("contlength", "features", REG, FEA, "region_feat", {"metric": "perimeter"},
     '領域の周囲長(``regionprops`` の ``perimeter``)を画像の外周長\n``2*(H+W)`` で正規化した値。HALCON の ``contlength``（Contour length of a\nregion.）に相当。\n\n``a``, ``b`` は未使用。1.0 でクリップされるため、外周長より極端に長い\n複雑な境界(フラクタル的な形状など)では情報が飽和する。'),
    ("area_holes", "features", REG, FEA, "region_feat", {"metric": "area_holes"},
     '領域内の穴が占める面積比 ``(穴埋め後面積 - 元面積) / 穴埋め後面積``。\n0 に近いほど穴が無く、1 に近いほど大半が穴という極端な形状を示す。HALCON\nの ``area_holes``（Compute the area of holes of regions.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("height_width_ratio", "features", REG, FEA, "region_feat", {"metric": "aspect"},
     '外接矩形の縦横比 ``min(1, 高さ/幅)``。高さが幅以下のときだけ正しい\n比率を返し、高さが幅を超える(縦長の)領域では 1.0 に飽和してしまう\n(実装の非対称性 ―― 真のアスペクト比ではなく「横長方向の扁平さ」しか\n表現できない近似)。HALCON の ``height_width_ratio``（Compute the width,\nheight, and aspect ratio of the surrounding rectangle parallel to the\ncoordinate axes.）の代役。\n\n``a``, ``b`` は未使用。'),
    ("moments_region_2nd", "features", REG, FEA, "region_feat", {"metric": "moment2"},
     '正規化中心 2 次モーメントの和の絶対値 ``|μ20 + μ02|``(``skimage.\nmeasure.moments_normalized`` 由来)。HALCON の ``moments_region_2nd``\n（Calculate the geometric moments of regions.）は本来 M20/M02/M11 を\nそれぞれ返すが、この代役では 1 スカラーに単純化するため 2 成分を単純\n加算した合成値で近似している(個々の方向成分は失われる)。\n\n``a``, ``b`` は未使用。'),
    ("moments_region_2nd_invar", "features", REG, FEA, "region_feat", {"metric": "hu1"},
     'Hu の第 1 不変モーメント(``skimage.measure.moments_hu`` の\n``hu[0]``)の絶対値。回転・スケール・平行移動に対して不変な形状記述子。\nHALCON の ``moments_region_2nd_invar``（Geometric moments of regions.）\nに相当する近似(HALCON 独自の相対不変モーメント定義とは厳密には異なり、\n古典的な Hu モーメントで代用している)。\n\n``a``, ``b`` は未使用。'),
    # Haralick texture (image -> feature)
    ("cooc_feature_matrix", "texture", IMG, FEA, "cooc", {"prop": "energy"},
     'グレーレベル共起行列(GLCM、``skimage.feature.graycomatrix``、16 階調\nに量子化、距離 ``1+3*a``、角度 0°)から Haralick テクスチャ特徴量\n``energy``(角二次モーメント、行列の値の集中度=テクスチャの均一性)を計算\nする。HALCON の ``cooc_feature_matrix``（Calculate gray value features\nfrom a co-occurrence matrix.）に相当(HALCON は複数の特徴量・複数角度を\n同時に返せるが、ここでは energy・角度 0° 固定に単純化)。\n\n``a`` が共起を取る画素間距離を 1〜4 の範囲で振る。``b`` は未使用。'),
    # windowed histogram equalisation
    ("equ_histo_image_rect", "gray", IMG, IMG, "lut", {"kind": "equalize_local"},
     'ブロック単位のヒストグラム平坦化。画像を ``nb x nb``(``nb=2+4*a``)\n個のブロックに分割し、各ブロックごとに独立して(64 ビンの)ヒストグラム\n平坦化を行う ―― 局所的な照明ムラに対して ``equ_histo_image``(画像全体を\n一括処理)より頑健だが、ブロック境界に段差(ブロックアーティファクト)が\n出ることがある。HALCON の ``equ_histo_image_rect``（Histogram\nlinearization within a rectangluar mask.）に相当。\n\n``a`` がブロック分割数を 2〜6 の範囲で振る。``b`` は未使用。'),
    # motion blur
    ("simulate_motion", "smoothing", IMG, IMG, "linfilter", {"kind": "motion"},
     '線形の動きぼけ(モーションブラー)をシミュレートする。角度\n``π*a``(0〜180°)方向に長さ ``5+10*b`` 画素の線分カーネルを作り畳み込む。\nHALCON の ``simulate_motion``（Simulation of (linearly) motion blur.）に\n相当。\n\n``a`` がぶれの方向角を、``b`` がぶれの長さを振る。両方が使われる。'),
    # projective / inverse transforms
    ("projective_trans_image", "geometry", IMG, IMG, "geom", {"kind": "projective"},
     '透視(射影)変換(``cv2.warpPerspective``)。4 隅のうち上 2 隅を\n``d=0.06+0.12*a`` の比率で内側に寄せることで台形(パースがかかった)歪みを\n作る。枠外は反射で埋める。HALCON の ``projective_trans_image``（Apply a\nprojective transformation to an image.）に相当(HALCON は任意のホモグラフィ\n行列を渡せるが、ここでは台形歪み 1 パターンに限定した近似)。\n\n``a`` が歪みの強さを、``b`` が左右の非対称さ(どちら側をより歪ませるか)を\n振る。両方が使われる。'),
    ("projective_trans_image_size", "geometry", IMG, IMG, "geom", {"kind": "projective"},
     '実装は ``projective_trans_image`` と同一(``kind: "projective"``)。\n名前は出力サイズを指定できることを示唆するが、このバックエンドでは\n出力キャンバスサイズは変更されず、``projective_trans_image`` と全く同じ\n台形歪みを返す(近似の限界、サイズ変更機能は再現されていない)。HALCON の\n``projective_trans_image_size``（Apply a projective transformation to an\nimage and specify the output image size.）の代役。\n\n``a`` が歪みの強さ、``b`` が非対称さを振る。両方が使われる。'),
    ("projective_trans_region", "geometry", REG, REG, "geom", {"kind": "projective"},
     '``projective_trans_image`` と同じ台形歪みを領域(2 値マスク)に適用する。\n``out_sort`` が ``region`` のため ``build()`` が ``_rebinarise`` で包み、\n補間で生じた小数値を ``>0.5`` で二値に戻してから返す(領域の {0,1} 契約を\n壊さないための後処理)。HALCON の ``projective_trans_region``（Apply a\nprojective transformation to a region.）に相当。\n\n``a`` が歪みの強さ、``b`` が非対称さを振る。両方が使われる。'),
    ("polar_trans_image_inv", "geometry", IMG, IMG, "geom", {"kind": "polar_inv"},
     '極座標→直交座標への逆変換(``cv2.warpPolar`` + ``WARP_INVERSE_MAP``)。\n``polar_trans_image`` の逆写像で、半径 ``min(H,W)/2`` の円盤の外側は 0 で\n埋める。2026-09-02 に「cv2 が書かなかった画素が未初期化のまま返る」バグを\n修正済み(戻り値でなく渡した ``dst`` を読んでいたため実行毎に値が変わって\nいた ―― 詳細はコード内コメント)。HALCON の\n``polar_trans_image_inv``（Transform an image in polar coordinates back\nto Cartesian coordinates）に相当。\n\n``a``, ``b`` は未使用 ―― 中心・半径は画像サイズから自動的に決まる。'),
    ("fft_image_inv", "frequency", IMG, IMG, "freq", {"kind": "ifft"},
     '入力画像をそのまま周波数領域の配列とみなして逆 FFT を掛け、実部を\n``signed01`` で [0,1] に写す(0.5 がゼロ)。本来 HALCON の\n``fft_image_inv``（Compute the inverse fast Fourier transform of an\nimage.）は ``fft_image`` が作った複素スペクトル(実部・虚部の組)を戻す\n演算だが、この代役はグレー画像 1 枚しか扱えないパイプライン契約のため、\n画素値をそのまま(虚部 0 の)複素配列として逆変換する近似になっている\n(``fft_image`` の出力をそのまま渡しても意味的な往復にはならない点に注意)。\n\n``a``, ``b`` は未使用。'),
    # deterministic noise
    ("add_noise_white", "noise", IMG, IMG, "noise", {"kind": "gaussian"},
     'ガウス性ホワイトノイズを加える(``np.random.default_rng`` で生成、\n標準偏差 ``0.02+0.2*b``)。乱数シードは ``int(a*997)+7`` で ``a`` から\n決定的に導出されるため、**同じ ``a`` なら常に同じノイズパターンが再現\nされる**(真にランダムではなく、``a`` を「ノイズの見え方の型」を選ぶ\n擬似的なノブとして使っている点に注意)。HALCON の ``add_noise_white``\n（Add noise to an image.）に相当。\n\n``a`` は乱数シード(=ノイズパターン)を、``b`` はノイズの強さ(標準偏差)\nを振る。両方が使われるが、``a`` の意味は「強さ」ではなく「パターン」で\nある点が他の op と異なる。'),
    # ---- v11d increment: XLD contour ops + region moments + misc ----------
    # XLD contour -> feature
    ("area_center_xld", "features", CON, FEA, "xld", {"kind": "area"},
     '最大の点数を持つ輪郭 1 本について、シューレース公式(靴紐公式)で\n多角形面積を求め、画像の全画素数で正規化して返す。HALCON の\n``area_center_xld``（Area and center of gravity (centroid) of contours and\npolygons.）は面積に加えて重心も返す演算子だが、この代役では面積のみを\n返す(重心情報は失われる近似 ―― ``feature`` ソートが 1 スカラーである\n契約上の制約)。\n\n``a``, ``b`` は未使用。輪郭が無ければ 0 を返す。'),
    ("circularity_xld", "features", CON, FEA, "xld", {"kind": "circularity"},
     '最大の輪郭についてシューレース公式で面積、線分長の和で周囲長を求め、\n円形度 ``4π・面積/周囲長²`` を計算する(領域版の ``circularity`` の輪郭\n版)。HALCON の ``circularity_xld``（Shape factor for the circularity\n(similarity to a circle) of contours or polygons.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("compactness_xld", "features", CON, FEA, "xld", {"kind": "compactness"},
     '最大の輪郭についてコンパクトさ ``周囲長²/(4π・面積)/10`` を計算する\n(``compactness`` の輪郭版で、``/10`` は値を [0,1] に収めるための便宜的な\nスケーリング、HALCON の定義そのものではない)。HALCON の\n``compactness_xld``（Shape factor for the compactness of contours or\npolygons.）に相当する近似。\n\n``a``, ``b`` は未使用。'),
    ("convexity_xld", "features", CON, FEA, "xld", {"kind": "convexity"},
     '最大の輪郭について凸性 ``輪郭の面積 / 凸包の面積`` を計算する\n(``cv2.convexHull`` + ``cv2.contourArea``)。cv2 が無い環境では常に 1.0\n(完全凸)を返すフォールバックになる点に注意。HALCON の ``convexity_xld``\n（Shape factor for the convexity of contours or polygons.）に相当。\n\n``a``, ``b`` は未使用。'),
    # XLD contour -> contour (transforms / closing)
    ("close_contours_xld", "contour", CON, CON, "xld", {"kind": "close"},
     '各輪郭の始点を末尾に複製して追加し、開いた折れ線を閉じたループにする\n(点数 2 以上の輪郭のみ)。HALCON の ``close_contours_xld``（Close an XLD\ncontour.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("affine_trans_contour_xld", "contour", CON, CON, "xld", {"kind": "affine"},
     '輪郭の各点を画像中心を軸に回転(``-20°〜+20°``、``a`` で決まる)する。\nHALCON の ``affine_trans_contour_xld``（Apply an arbitrary affine 2D\ntransformation to XLD contours.）は任意のアフィン行列(平行移動・拡大縮小・\nせん断を含む)を取れるが、この代役では純粋な回転のみに単純化している\n(近似)。\n\n``a`` が回転角を振る。``b`` は未使用。'),
    ("projective_trans_contour_xld", "contour", CON, CON, "xld", {"kind": "projective"},
     '輪郭の各点に、列位置に応じた疑似的な遠近収縮(``d = 1 + 0.3*a*(col -\n中心)/幅``で各点の座標を割る)を適用する。真の 3x3 ホモグラフィ行列による\n射影変換ではなく、片方向だけの簡易な縮尺変化で近似している点に注意。\nHALCON の ``projective_trans_contour_xld``（Apply a projective\ntransformation to an XLD contour.）の代役。\n\n``a`` が収縮の強さを振る。``b`` は未使用(画像版の\n``projective_trans_image`` とは異なり、この輪郭版は ``b`` を使わない)。'),
    ("polar_trans_contour_xld", "contour", CON, CON, "xld", {"kind": "polar"},
     '輪郭の各点を画像中心からの極座標(半径・角度)に変換し、疑似的な画素\n座標(半径を ``H`` or ``W`` の大きい方でスケール、角度を [0,1] に写像)へ\n詰め直す。HALCON の ``polar_trans_contour_xld``（Transform a contour in an\nannular arc to polar coordinates.）に相当する簡易な座標変換。\n\n``a``, ``b`` は未使用 ―― 中心・スケールは画像サイズから自動的に決まる。'),
    # region moments
    ("moments_region_3rd", "features", REG, FEA, "region_feat", {"metric": "moment3"},
     '正規化中心 3 次モーメントの和の絶対値 ``|μ30 + μ03|``。\n``moments_region_2nd`` の 3 次版で、こちらも複数成分を単純加算した合成値\nによる近似(個々の方向成分は失われる)。HALCON の\n``moments_region_3rd``（Geometric moments of regions.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("moments_region_central", "features", REG, FEA, "region_feat", {"metric": "moment_central"},
     '正規化中心モーメント(2 次まで)の和の絶対値 ``|μ20+μ11+μ02|``。\nHALCON の ``moments_region_central``（Geometric moments of regions.）に\n相当する、複数成分を 1 スカラーへ合成した近似。\n\n``a``, ``b`` は未使用。'),
    ("moments_region_central_invar", "features", REG, FEA, "region_feat", {"metric": "hu2"},
     'Hu の第 2 不変モーメント(``hu[1]``)の絶対値。HALCON の\n``moments_region_central_invar``（Geometric moments of regions.）に相当\nする近似(``moments_region_2nd_invar`` が Hu[0] を使うのに対し、こちらは\nHu[1] を使う ―― どちらも HALCON 独自の相対不変モーメントの厳密な代用では\nない)。\n\n``a``, ``b`` は未使用。'),
    ("moments_region_2nd_rel_invar", "features", REG, FEA, "region_feat", {"metric": "hu3"},
     'Hu の第 3 不変モーメント(``hu[2]``)の絶対値。名前(2nd_rel_invar)と\n実装(Hu の 3 番目の不変量)が厳密には対応していない点に注意 ―― HALCON\n独自の「2 次相対不変モーメント」ではなく、汎用の Hu 不変モーメント系列\nから割り当てただけの近似。HALCON の ``moments_region_2nd_rel_invar``\n（Geometric moments of regions.）の代役。\n\n``a``, ``b`` は未使用。'),
    ("moments_region_3rd_invar", "features", REG, FEA, "region_feat", {"metric": "hu4"},
     'Hu の第 4 不変モーメント(``hu[3]``)の絶対値。``moments_region_*_invar``\n系列の一つとして Hu モーメント配列から順番に割り当てている(HALCON 独自の\n定義との厳密な対応はない近似)。HALCON の ``moments_region_3rd_invar``\n（Geometric moments of regions.）の代役。\n\n``a``, ``b`` は未使用。'),
    # segmentation / threshold / stats
    ("dual_threshold", "segmentation", IMG, REG, "threshold", {"method": "dual"},
     '符号つき画像向けのしきい値処理。中央値 0.5 を「ゼロ」とみなし、\n``|x - 0.5| > 0.1+0.35*a`` を満たす画素(0.5 から十分離れた画素)を前景と\nする ―― 正負どちらの側にも対称に反応する。HALCON の ``dual_threshold``\n（Threshold operator for signed images.）に相当(HALCON は正負で別々の\nしきい値を持てるが、ここでは 0.5 を中心とした対称な帯域に単純化)。\n\n``a`` が除外帯域の半幅を振る。``b`` は未使用。``highpass_image`` や\n``bandpass_image`` のような符号つき応答(0.5=ゼロ)の後段でよく使う。'),
    ("segment_image_mser", "segmentation", IMG, REG, "segment", {"kind": "mser"},
     'MSER(Maximally Stable Extremal Regions、最大安定極値領域)検出\n(``cv2.MSER_create``)。しきい値を連続的に変化させても形が安定して残る\n領域を検出し、その境界線を返す(文字・ロゴなど照明変化に頑健な領域検出に\n使われる)。HALCON の ``segment_image_mser``（Segment image using Maximally\nStable Extremal Regions (MSER).）に相当。\n\n``a`` が MSER の安定性パラメータ(delta、3〜11)を振る。``b`` は未使用。\n``cv2`` が無い環境ではこの分岐は呼べない。'),
    ("regiongrowing_mean", "segmentation", IMG, REG, "segment", {"kind": "regiongrow"},
     '実装は ``regiongrowing`` と同一(しきい値によるシード生成+膨張)。\nHALCON の ``regiongrowing_mean``（Perform a region growing using mean gray\nvalues.）は本来、各領域の平均輝度との近さを基準に成長させる演算子だが、\nこの代役では平均輝度による判定を行わず ``regiongrowing`` と同じ処理を\n返す(近似の限界)。\n\n``a`` がシードのしきい値、``b`` が膨張の反復回数を振る。両方が使われる。'),
    ("estimate_noise", "features", IMG, FEA, "img_feat", {"metric": "noise_est"},
     '加法性ノイズの標準偏差 σ をロバスト推定する(``_noise_sigma``:\nラプラシアン応答の MAD を正規分布換算し、5 点ラプラシアン核のノイズ利得\n``sqrt(20)`` で割る)。エッジ由来の外れ値には鈍く、平坦部のノイズだけを\n拾う設計(2026-09-02 に旧実装の「σ が単位を持たず σ≈0.08 以上で 1.0 に\n張り付く」不具合を修正済み、詳細は ``_noise_sigma`` の docstring)。HALCON\nの ``estimate_noise``（Estimate the image noise from a single image.）に\n相当。\n\n``a``, ``b`` は未使用。'),
    # corner strength maps (points_harris already covered by core corner_response)
    ("points_foerstner", "edges", IMG, IMG, "corner", {"kind": "foerstner"},
     'Förstner 演算子によるコーナー強度マップ(``skimage.feature.\ncorner_foerstner`` の重み ``w`` とロバスト形状指標 ``q`` の積、NaN は 0 に\n置換)。誤差楕円の大きさ(w)と円形度(q)を組み合わせて点特徴らしさを評価する。\nHALCON の ``points_foerstner``（Detect points of interest using the\nFörstner operator.）に相当。\n\n``a`` が勾配計算のガウス窓シグマを 0.5〜2.5 の範囲で振る。``b`` は未使用。\nskimage が無い環境ではこの分岐自体が呼べない(``_HAS_SK`` ガード)。'),
    ("points_harris_binomial", "edges", IMG, IMG, "corner", {"kind": "harris_binomial"},
     '二項(ガウス)平滑化を前段に挟んだ Harris コーナー応答。まず ``b`` で\n決まるシグマで画像を平滑化し、その上で Harris 応答(skimage があれば\n``corner_harris``、無ければ構造テンソルを手計算、k=0.04)を求める。HALCON\nの ``points_harris_binomial``（Detect points of interest using the\nbinomial approximation of the Harris operator.）に相当。\n\n``a`` が Harris 応答自体のシグマ(0.5〜2.5)を、``b`` が前段の平滑化シグマ\n(0.5〜2.0)を振る。両方が使われる。'),
    # ---- v11e increment: XLD ellipse/moment features + crossings + pruning ----
    ("eccentricity_xld", "features", CON, FEA, "xld", {"kind": "eccentricity"},
     '最大の輪郭(5 点以上)に ``cv2.fitEllipse`` で楕円をフィットし、その\n離心率 ``sqrt(1-(短軸/長軸)^2)`` を返す(0=真円、1に近いほど細長い)。\nHALCON の ``eccentricity_xld``（Shape features derived from the ellipse\nparameters of contours or polygons.）に相当。cv2 が無い、または点数不足\nの場合は 0 を返す。\n\n``a``, ``b`` は未使用。'),
    ("orientation_xld", "features", CON, FEA, "xld", {"kind": "orientation"},
     '楕円フィットした輪郭の傾き角(``cv2.fitEllipse`` の角度を 180° で\n折り返して [0,1] に正規化)。HALCON の ``orientation_xld``（Calculate the\norientation of contours or polygons.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("elliptic_axis_xld", "features", CON, FEA, "xld", {"kind": "elliptic_axis"},
     '楕円フィットした輪郭の短軸/長軸の比。値が 1 に近いほど真円に近く、\n0 に近いほど細長い。HALCON の ``elliptic_axis_xld``（Parameters of the\nequivalent ellipse of contours or polygons.）が返す(長軸, 短軸, 角度)の\n組のうち、比 1 個のスカラーだけを返す近似。\n\n``a``, ``b`` は未使用。'),
    ("diameter_xld", "features", CON, FEA, "xld", {"kind": "diameter"},
     '輪郭を包含する最小外接円(``cv2.minEnclosingCircle``)の直径を画像の\n最大辺長で正規化した値。HALCON の ``diameter_xld``（Maximum distance\nbetween two contour or polygon points.）が定義する「輪郭上の 2 点間の\n最大距離」とは厳密には異なる指標(外接円の直径による近似、最小外接円は\n必ずしも最遠 2 点を結ぶ直径と一致しない)。\n\n``a``, ``b`` は未使用。'),
    ("rectangularity_xld", "features", CON, FEA, "xld", {"kind": "rectangularity"},
     '輪郭面積を最小外接回転矩形(``cv2.minAreaRect``)の面積で割った充填率。\n値が 1 に近いほど輪郭が自身の外接矩形を隙間なく埋めていることを示す。\nHALCON の ``rectangularity_xld``（Shape factor for the rectangularity of\ncontours or polygons.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("moments_xld", "features", CON, FEA, "xld", {"kind": "moment_xld"},
     '輪郭の生モーメント(``cv2.moments``)から ``(mu20+mu02)/面積²`` という\n単一スカラーを計算する ―― HALCON の ``moments_xld``（Geometric moments\nM20, M02, and M11 of contours or polygons.）が返す M20/M02/M11 の 3 成分を\n1 つに合成した近似(個々の方向成分・M11 は失われる)。\n\n``a``, ``b`` は未使用。'),
    ("shape_trans_xld", "contour", CON, CON, "xld", {"kind": "convex"},
     '輪郭の凸包(``cv2.convexHull``)を計算し、輪郭形式のまま返す\n(``shape_trans`` の輪郭版)。HALCON の ``shape_trans_xld``（Transform the\nshape of contours or polygons.）が持つ複数の変形モードのうち、凸包 1 種類\nのみを実装している(近似)。\n\n``a``, ``b`` は未使用。cv2 が無い環境ではこの分岐は呼べない。'),
    ("zero_crossing", "segmentation", IMG, REG, "segment", {"kind": "zero_crossing"},
     'ラプラシアン(ガウス平滑化込み、シグマ ``0.5+2*a``)の符号が反転する\n画素(ゼロ交差)を検出する。LoG のゼロ交差はエッジの位置を高精度に示す\nことで知られる古典的な検出法。HALCON の ``zero_crossing``（Extract zero\ncrossings from an image.）に相当。\n\n``a`` がガウス平滑化のシグマを振る。``b`` は未使用。上下・左右いずれかの\n方向で符号が変わればゼロ交差とみなす(斜め方向は直接見ていない)。'),
    ("local_min", "segmentation", IMG, REG, "segment", {"kind": "local_min"},
     '局所極小点(領域極小)検出。``x`` が窓内の最小値(``_k(a)``)に一致し、\nかつ ``x < 0.7-0.4*b`` を満たす画素を前景とする、``local_max`` の暗部版。\nHALCON の ``local_min``（Detect all local minima in an image.）に相当。\n\n``a`` が窓サイズを、``b`` が輝度の上限しきい値を振る。両方が使われる。'),
    ("pruning", "region", REG, REG, "region_trans", {"kind": "pruning"},
     '骨格化(``skeletonize``、無ければ入力をそのまま使用)の後、近傍数が\n1 以下の端点画素(スパー=枝毛)を繰り返し ``1+4*a`` 回削り取ることで、\n骨格から短い枝を除去する。HALCON の ``pruning``（Prune the branches of a\nregion.）に相当(HALCON は枝の長さを指定できるが、ここでは反復回数による\n近似)。\n\n``a`` が削り取る反復回数を 1〜5 回の範囲で振る。``b`` は未使用。回数が\n多いほど主要な骨格まで削れてしまうことがある。'),
    # ---- v11f increment: Hough, subpixel crossings, skeleton/EDT region ops ----
    ("hough_line_trans", "features", IMG, IMG, "hough", {"kind": "line"},
     '直線検出のための Hough 変換アキュムレータ。まず Sobel 勾配からエッジ\nマスクを作り、``skimage.transform.hough_line`` でアキュムレータ空間\n(角度×距離)を計算、正規化してから入力と同じ画素形状にリサイズして返す\n(アキュムレータそのものの座標系ではなく画像として可視化する形)。HALCON の\n``hough_line_trans``（Produce the Hough transform for lines within\nregions.）に相当。\n\n``a`` がエッジ抽出の閾値(0.2〜0.6)を振る。``b`` は未使用。半径・角度分解能\nは skimage の既定値に固定されている。'),
    ("hough_circle_trans", "features", IMG, IMG, "hough", {"kind": "circle"},
     '円検出のための Hough 変換。エッジマスクに対して半径 4〜19(3 刻み)の\n円テンプレート群で ``skimage.transform.hough_circle`` を計算し、全半径での\n最大応答を [0,1] に正規化して返す。HALCON の ``hough_circle_trans``\n（Return the Hough-Transform for circles with a given radius.）に相当\n(HALCON は半径を明示指定するが、ここでは固定レンジを総当たりする近似)。\n\n``a`` がエッジ抽出の閾値を振る。``b`` は未使用 ―― 探索する半径レンジは\nコード側に固定されており、``b`` で半径を選ぶことはできない。'),
    ("threshold_sub_pix", "contour", IMG, CON, "xld", {"kind": "threshold_sub_pix"},
     'マーチングスクエア法(``skimage.measure.find_contours``)によるレベル\nクロッシング(等高線)抽出。指定した階調レベル(``0.2+0.5*a``)を横切る位置を\nサブピクセル精度で輪郭として返す。HALCON の ``threshold_sub_pix``\n（Extract level crossings from an image with subpixel accuracy.）に相当。\n\n``a`` がクロッシングを取るレベルを振る。``b`` は未使用。skimage が無い\n環境ではこの分岐は呼べない。'),
    ("zero_crossing_sub_pix", "contour", IMG, CON, "xld", {"kind": "zero_crossing_sub_pix"},
     'LoG(ガウス平滑化込みラプラシアン、シグマ ``0.5+2*a``)のゼロ交差を\n``find_contours`` でサブピクセル精度の輪郭として抽出する。領域版の\n``zero_crossing``(画素解像度)に対するサブピクセル精度版。HALCON の\n``zero_crossing_sub_pix``（Extract zero crossings from an image with\nsubpixel accuracy.）に相当。\n\n``a`` がガウス平滑化のシグマを振る。``b`` は未使用。skimage が無い環境\nではこの分岐は呼べない。'),
    ("closest_point_transform", "region", REG, IMG, "region_trans", {"kind": "closest_point_transform"},
     '領域の**補集合**に対するユークリッド距離変換を正規化して返す ―― 各\n画素から最も近い領域(前景)画素までの距離を表す、``distance_transform``\nとは前景/背景が逆の距離場。出力は ``image`` 型。HALCON の\n``closest_point_transform``（Compute the closest-point transformation of\na region.）に相当。\n\n``a``, ``b`` は未使用。'),
    ("junctions_skeleton", "region", REG, REG, "region_trans", {"kind": "junctions_skeleton"},
     '骨格化した領域のうち、3x3 近傍に 3 つ以上の骨格画素を持つ画素(分岐点・\n交差点)だけを残す。骨格の端点(``pruning`` が削る対象)ではなく、枝分かれ\nする結節点を検出する。HALCON の ``junctions_skeleton``（Find junctions and\nend points in a skeleton.）に相当(HALCON は端点も同時に返すが、ここでは\n分岐点のみを検出する近似)。\n\n``a``, ``b`` は未使用。'),
    ("get_region_thickness", "features", REG, FEA, "region_feat", {"metric": "thickness"},
     '領域の太さの近似値 ``2 × 最大内接円半径 / 最大辺長``\n(``distance_transform_edt`` の最大値の 2 倍を画像サイズで正規化)。HALCON\nの ``get_region_thickness``（Access the thickness of a region along the\nmain axis.）が定義する「主軸に沿った太さのプロファイル」とは異なり、\n方向を問わないグローバルな最大内接半径だけを見る単純化(主軸方向の情報は\n失われる)。\n\n``a``, ``b`` は未使用。'),
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
    # SEED の行は 7 要素 (…, params, doc)。6 要素のままの行は「説明がまだ無い」
    # として通す —— zip が短い方で止まるので doc が落ちるだけ。数えるのは
    # tests/test_op_descriptions.py の役目で、ここで填め物を作らない。
    _cols = ("halcon", "category", "in_sort", "out_sort", "shape", "params", "doc")
    specs = [dict(zip(_cols, s)) for s in SEED]
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
    """Fail-soft wrapper -> the shared, RECORDING guard (backend_safe.guard).

    A failure degrades to a sort-valid fallback exactly as before, but the event
    is now written to the fallback ledger and strict mode re-raises, so a
    permanently broken op can no longer masquerade as a working identity.
    """
    from backend_safe import guard
    return guard(fn, out_sort)


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
        _op = Op(opname, s.get("category", "misc"), name,
                 s.get("in_sort", "image"), out_sort,
                 _safe(fn, out_sort))
        # spec が説明の置き場 —— この backend の op は generic な shape から
        # 組み立てられるので、実装のそばに書ける docstring が存在しない。
        # 空のまま登録すると「説明なし」の op になる(tests が数えている)。
        _op.doc = (s.get("doc") or "").strip()
        ops_out.append(_op)
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
