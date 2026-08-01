"""imgevolve — SCALABLE typed image-op registry.

The whole point (toward a HALCON-scale operator catalog): operators live in one
REGISTRY with metadata; adding an operator makes the evolutionary search AND the
codegen pick it up automatically — no driver changes. Each op is a pure
image->image map on float64 in [0,1] (edge/deriv ops are normalised to [0,1] so
pipelines compose). Op families mirror HALCON's: smoothing, rank, morphology,
edges, gray/point, threshold, frequency, texture.

Genome = [0,1]^GENOME_LEN: N_SLOTS stages x (op-select t, param a, param b). Decode
is deterministic (r2 bit-identical discipline). runtime dict RT[name] is the shared
Python backend that both apply_genome() and codegen'd modules call — so a generated
pipeline is verified against the IR by re-baking the same params (see difftest.py).

stdlib + numpy + scipy.ndimage only. C support is a growing subset (see .c_stmt).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy import ndimage


def _k(a: float) -> int:
    return (3, 5, 7, 9)[min(3, int(a * 4))]


def _norm(x: np.ndarray) -> np.ndarray:
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


# --- operator implementations (image, a, b) -> image ------------------------- #
def _identity(img, a, b): return img
def _gaussian(img, a, b): return ndimage.gaussian_filter(img, sigma=0.3 + 2.7 * a)
def _mean_box(img, a, b): return ndimage.uniform_filter(img, size=_k(a))
def _median(img, a, b): return ndimage.median_filter(img, size=_k(a))
def _min_filter(img, a, b): return ndimage.minimum_filter(img, size=_k(a))
def _max_filter(img, a, b): return ndimage.maximum_filter(img, size=_k(a))
def _percentile(img, a, b): return ndimage.percentile_filter(img, percentile=int(5 + 90 * b), size=_k(a))
def _erode(img, a, b): return ndimage.grey_erosion(img, size=_k(a))
def _dilate(img, a, b): return ndimage.grey_dilation(img, size=_k(a))
def _open(img, a, b): return ndimage.grey_opening(img, size=_k(a))
def _close(img, a, b): return ndimage.grey_closing(img, size=_k(a))
def _tophat(img, a, b): return _norm(ndimage.white_tophat(img, size=_k(a)))
def _bothat(img, a, b): return _norm(ndimage.black_tophat(img, size=_k(a)))
def _morph_grad(img, a, b): return _norm(ndimage.morphological_gradient(img, size=_k(a)))
def _sobel_mag(img, a, b): return _norm(np.hypot(ndimage.sobel(img, 1), ndimage.sobel(img, 0)))
def _laplace(img, a, b): return _norm(np.abs(ndimage.laplace(img)))
def _prewitt_mag(img, a, b): return _norm(np.hypot(ndimage.prewitt(img, 1), ndimage.prewitt(img, 0)))


def _roberts_mag(img, a, b):
    gx = img - np.roll(np.roll(img, -1, 0), -1, 1)
    gy = np.roll(img, -1, 1) - np.roll(img, -1, 0)
    return _norm(np.hypot(gx, gy))


def _dog(img, a, b):
    s1, s2 = 0.5 + 2.0 * a, 1.0 + 4.0 * b
    return _norm(np.abs(ndimage.gaussian_filter(img, s1) - ndimage.gaussian_filter(img, s2)))


def _gamma(img, a, b): return np.clip(img, 0, 1) ** (0.5 + 1.5 * a)
def _invert(img, a, b): return 1.0 - np.clip(img, 0, 1)
def _scale_clip(img, a, b): return np.clip((0.5 + 1.5 * a) * img + (b - 0.5), 0, 1)


def _equalize(img, a, b):
    x = np.clip(img, 0, 1)
    hist, edges = np.histogram(x, 256, (0, 1))
    cdf = np.cumsum(hist).astype(np.float64)
    cdf = cdf / cdf[-1] if cdf[-1] > 0 else cdf
    return np.interp(x.ravel(), (edges[:-1] + edges[1:]) / 2, cdf).reshape(x.shape)


def _sigmoid(img, a, b):
    gain, center = 4.0 + 12.0 * a, 0.2 + 0.6 * b
    return 1.0 / (1.0 + np.exp(-gain * (np.clip(img, 0, 1) - center)))


def _bilateral(img, a, b):
    ss, sr, r = 1.0 + 3.0 * a, 0.05 + 0.4 * b, 2
    out = np.zeros_like(img, np.float64); wsum = np.zeros_like(img, np.float64)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            sh = np.roll(np.roll(img, dy, 0), dx, 1)
            w = np.exp(-(dx * dx + dy * dy) / (2 * ss * ss)) * np.exp(-((sh - img) ** 2) / (2 * sr * sr))
            out += w * sh; wsum += w
    return out / np.maximum(wsum, 1e-8)


def _threshold(img, a, b): return (img > a).astype(np.float64)


def _otsu(img, a, b):
    x = np.clip(img, 0, 1); hist, edges = np.histogram(x, 256, (0, 1))
    p = hist.astype(np.float64) / max(1, hist.sum()); omega = np.cumsum(p)
    mids = (edges[:-1] + edges[1:]) / 2; mu = np.cumsum(p * mids); mu_t = mu[-1]
    den = omega * (1 - omega); sb = np.where(den > 1e-12, (mu_t * omega - mu) ** 2 / np.maximum(den, 1e-12), 0.0)
    return (x > mids[int(np.argmax(sb))]).astype(np.float64)


def _dyn_threshold(img, a, b):
    local = ndimage.uniform_filter(img, size=_k(a))
    return (img > local + (b - 0.5) * 0.4).astype(np.float64)


def _std_filter(img, a, b):
    k = _k(a); m = ndimage.uniform_filter(img, k); m2 = ndimage.uniform_filter(img * img, k)
    return _norm(np.sqrt(np.maximum(m2 - m * m, 0.0)))


def _fft_mask(img, cutoff, high):
    H, W = img.shape
    fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None, :]
    rad = np.sqrt(fy * fy + fx * fx)
    mask = (rad > cutoff) if high else (rad <= cutoff)
    out = np.real(np.fft.ifft2(np.fft.fft2(img) * mask))
    return out


def _lowpass(img, a, b): return np.clip(_fft_mask(img, 0.05 + 0.4 * a, False), 0, 1)
def _highpass(img, a, b): return _norm(_fft_mask(img, 0.02 + 0.3 * a, True))
def _unsharp(img, a, b): return img + (1.5 * a) * (img - ndimage.gaussian_filter(img, 0.5 + 1.5 * b))


@dataclass
class Op:
    name: str
    category: str
    halcon: str                       # nearest HALCON operator analog
    fn: Callable
    c_stmt: Optional[Callable[[float, float], str]] = None  # emit a C statement, or None


# C statement emitters for ops already in imgops.c (the growing C subset).
def _c(name):
    return {
        "gaussian": lambda a, b: f"gaussian(buf, w, h, {0.3 + 2.7 * a:.6f}f);",
        "mean_box": lambda a, b: f"box(buf, w, h, {_k(a)});",
        "gamma": lambda a, b: f"gamma_op(buf, w, h, {0.5 + 1.5 * a:.6f}f);",
        "invert": lambda a, b: "invert(buf, w, h);",
        "scale_clip": lambda a, b: f"scale_clip(buf, w, h, {0.5 + 1.5 * a:.6f}f, {b - 0.5:.6f}f);",
        "threshold": lambda a, b: f"threshold(buf, w, h, {a:.6f}f);",
        "unsharp": lambda a, b: f"sharpen(buf, w, h, {1.5 * a:.6f}f, {0.5 + 1.5 * b:.6f}f);",
        "sobel_mag": lambda a, b: "sobel_mag(buf, w, h);",
    }.get(name)


_DEFS = [
    ("identity", "misc", "copy_image", _identity),
    ("gaussian", "smoothing", "gauss_filter", _gaussian),
    ("mean_box", "smoothing", "mean_image", _mean_box),
    ("median", "rank", "median_image", _median),
    ("min_filter", "rank", "gray_erosion_rect", _min_filter),
    ("max_filter", "rank", "gray_dilation_rect", _max_filter),
    ("percentile", "rank", "rank_image", _percentile),
    ("bilateral", "smoothing", "bilateral_filter", _bilateral),
    ("erode", "morphology", "gray_erosion", _erode),
    ("dilate", "morphology", "gray_dilation", _dilate),
    ("morph_open", "morphology", "gray_opening", _open),
    ("morph_close", "morphology", "gray_closing", _close),
    ("tophat", "morphology", "gray_tophat", _tophat),
    ("bothat", "morphology", "gray_bothat", _bothat),
    ("morph_grad", "morphology", "gray_range_rect", _morph_grad),
    ("sobel_mag", "edges", "sobel_amp", _sobel_mag),
    ("laplace", "edges", "laplace", _laplace),
    ("prewitt_mag", "edges", "prewitt", _prewitt_mag),
    ("roberts_mag", "edges", "roberts", _roberts_mag),
    ("dog", "edges", "diff_of_gauss", _dog),
    ("gamma", "gray", "pow_image", _gamma),
    ("invert", "gray", "invert_image", _invert),
    ("scale_clip", "gray", "scale_image", _scale_clip),
    ("equalize", "gray", "equ_histo_image", _equalize),
    ("sigmoid", "gray", "scale_image_max", _sigmoid),
    ("threshold", "segmentation", "threshold", _threshold),
    ("otsu", "segmentation", "binary_threshold", _otsu),
    ("dyn_threshold", "segmentation", "dyn_threshold", _dyn_threshold),
    ("lowpass", "frequency", "lowpass", _lowpass),
    ("highpass", "frequency", "highpass", _highpass),
    ("std_filter", "texture", "deviation_image", _std_filter),
    ("unsharp", "smoothing", "emphasize", _unsharp),
]

REGISTRY: list[Op] = [Op(n, c, h, f, _c(n)) for (n, c, h, f) in _DEFS]
RT: dict[str, Callable] = {op.name: op.fn for op in REGISTRY}
OPS = tuple((op.name, op.fn) for op in REGISTRY)  # back-compat
N_OPS = len(REGISTRY)
N_SLOTS = 5
GENOME_LEN = N_SLOTS * 3


def categories() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for op in REGISTRY:
        out.setdefault(op.category, []).append(op.name)
    return out


@dataclass
class Stage:
    op: str
    a: float
    b: float


def decode(genome) -> list[Stage]:
    g = np.clip(np.asarray(genome, np.float64), 0.0, 1.0)
    out = []
    for i in range(N_SLOTS):
        t, a, b = g[3 * i], g[3 * i + 1], g[3 * i + 2]
        out.append(Stage(REGISTRY[min(N_OPS - 1, int(t * N_OPS))].name, float(a), float(b)))
    return out


def apply_genome(genome, img) -> np.ndarray:
    out = img.astype(np.float64)
    for st in decode(genome):
        out = np.clip(RT[st.op](out, st.a, st.b), 0.0, 1.0)
    return out


def pipeline_str(genome) -> str:
    parts = [f"{s.op}(a={s.a:.2f},b={s.b:.2f})" for s in decode(genome) if s.op != "identity"]
    return " -> ".join(parts) if parts else "identity"


def psnr(a, b) -> float:
    mse = float(np.mean((np.asarray(a, np.float64) - np.asarray(b, np.float64)) ** 2))
    return 99.0 if mse <= 1e-12 else float(10.0 * np.log10(1.0 / mse))
