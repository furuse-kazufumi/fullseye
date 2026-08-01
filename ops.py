"""imgevolve — MULTI-SORT typed image-op registry (toward HALCON-scale).

The key upgrade for HALCON coverage: operators are typed by SORT, mirroring
HALCON's data model:

  image   : gray raster, float64 in [0,1]
  region  : a binary mask (float 0/1) — HALCON's Region
  feature : a scalar/tuple measurement (float) — HALCON's control tuple

Pipelines follow the canonical machine-vision shape
  image --(segment)--> region --(region morph / select)--> region --(measure)--> feature
and the type-aware decoder guarantees each stage is sort-compatible (an op only
runs on a value of its `in_sort`). Adding operators — in any sort — makes the
evolutionary search and codegen pick them up automatically.

Genome = [0,1]^GENOME_LEN: N_SLOTS stages x (op-select t, a, b). At each slot the
candidate set is the ops whose in_sort matches the running sort (+ the sort-neutral
identity), so t indexes into that filtered set. Deterministic decode.

stdlib + numpy + scipy.ndimage only. C support is a growing image-sort subset.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy import ndimage

IMAGE, REGION, FEATURE, ANY = "image", "region", "feature", "any"


def _k(a: float) -> int:
    return (3, 5, 7, 9)[min(3, int(a * 4))]


def _it(a: float) -> int:
    return 1 + int(a * 3)  # morphology iterations 1..4


def _norm(x):
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


def _bin(v):
    return (np.asarray(v) > 0.5)


# --- image -> image ---------------------------------------------------------- #
def _identity(v, a, b): return v
def _gaussian(v, a, b): return ndimage.gaussian_filter(v, sigma=0.3 + 2.7 * a)
def _mean_box(v, a, b): return ndimage.uniform_filter(v, size=_k(a))
def _median(v, a, b): return ndimage.median_filter(v, size=_k(a))
def _min_filter(v, a, b): return ndimage.minimum_filter(v, size=_k(a))
def _max_filter(v, a, b): return ndimage.maximum_filter(v, size=_k(a))
def _percentile(v, a, b): return ndimage.percentile_filter(v, percentile=int(5 + 90 * b), size=_k(a))
def _erode_g(v, a, b): return ndimage.grey_erosion(v, size=_k(a))
def _dilate_g(v, a, b): return ndimage.grey_dilation(v, size=_k(a))
def _open_g(v, a, b): return ndimage.grey_opening(v, size=_k(a))
def _close_g(v, a, b): return ndimage.grey_closing(v, size=_k(a))
def _tophat(v, a, b): return _norm(ndimage.white_tophat(v, size=_k(a)))
def _bothat(v, a, b): return _norm(ndimage.black_tophat(v, size=_k(a)))
def _morph_grad(v, a, b): return _norm(ndimage.morphological_gradient(v, size=_k(a)))
def _sobel_mag(v, a, b): return _norm(np.hypot(ndimage.sobel(v, 1), ndimage.sobel(v, 0)))
def _laplace(v, a, b): return _norm(np.abs(ndimage.laplace(v)))
def _prewitt_mag(v, a, b): return _norm(np.hypot(ndimage.prewitt(v, 1), ndimage.prewitt(v, 0)))


def _roberts_mag(v, a, b):
    return _norm(np.hypot(v - np.roll(np.roll(v, -1, 0), -1, 1), np.roll(v, -1, 1) - np.roll(v, -1, 0)))


def _dog(v, a, b):
    return _norm(np.abs(ndimage.gaussian_filter(v, 0.5 + 2.0 * a) - ndimage.gaussian_filter(v, 1.0 + 4.0 * b)))


def _gamma(v, a, b): return np.clip(v, 0, 1) ** (0.5 + 1.5 * a)
def _invert(v, a, b): return 1.0 - np.clip(v, 0, 1)
def _scale_clip(v, a, b): return np.clip((0.5 + 1.5 * a) * v + (b - 0.5), 0, 1)


def _equalize(v, a, b):
    x = np.clip(v, 0, 1); hist, edges = np.histogram(x, 256, (0, 1))
    cdf = np.cumsum(hist).astype(np.float64); cdf = cdf / cdf[-1] if cdf[-1] > 0 else cdf
    return np.interp(x.ravel(), (edges[:-1] + edges[1:]) / 2, cdf).reshape(x.shape)


def _sigmoid(v, a, b): return 1.0 / (1.0 + np.exp(-(4.0 + 12.0 * a) * (np.clip(v, 0, 1) - (0.2 + 0.6 * b))))


def _bilateral(v, a, b):
    ss, sr, r = 1.0 + 3.0 * a, 0.05 + 0.4 * b, 2
    out = np.zeros_like(v, np.float64); wsum = np.zeros_like(v, np.float64)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            sh = np.roll(np.roll(v, dy, 0), dx, 1)
            w = np.exp(-(dx * dx + dy * dy) / (2 * ss * ss)) * np.exp(-((sh - v) ** 2) / (2 * sr * sr))
            out += w * sh; wsum += w
    return out / np.maximum(wsum, 1e-8)


def _std_filter(v, a, b):
    k = _k(a); m = ndimage.uniform_filter(v, k); m2 = ndimage.uniform_filter(v * v, k)
    return _norm(np.sqrt(np.maximum(m2 - m * m, 0.0)))


def _fft_mask(v, cutoff, high):
    H, W = v.shape
    rad = np.sqrt(np.fft.fftfreq(H)[:, None] ** 2 + np.fft.fftfreq(W)[None, :] ** 2)
    mask = (rad > cutoff) if high else (rad <= cutoff)
    return np.real(np.fft.ifft2(np.fft.fft2(v) * mask))


def _lowpass(v, a, b): return np.clip(_fft_mask(v, 0.05 + 0.4 * a, False), 0, 1)
def _highpass(v, a, b): return _norm(_fft_mask(v, 0.02 + 0.3 * a, True))
def _unsharp(v, a, b): return v + (1.5 * a) * (v - ndimage.gaussian_filter(v, 0.5 + 1.5 * b))


# --- image -> region (segmentation) ------------------------------------------ #
def _threshold(v, a, b): return (v > a).astype(np.float64)


def _otsu(v, a, b):
    x = np.clip(v, 0, 1); hist, edges = np.histogram(x, 256, (0, 1))
    p = hist.astype(np.float64) / max(1, hist.sum()); omega = np.cumsum(p)
    mids = (edges[:-1] + edges[1:]) / 2; mu = np.cumsum(p * mids); mu_t = mu[-1]
    den = omega * (1 - omega); sb = np.where(den > 1e-12, (mu_t * omega - mu) ** 2 / np.maximum(den, 1e-12), 0.0)
    return (x > mids[int(np.argmax(sb))]).astype(np.float64)


def _dyn_threshold(v, a, b):
    return (v > ndimage.uniform_filter(v, size=_k(a)) + (b - 0.5) * 0.4).astype(np.float64)


# --- region -> region -------------------------------------------------------- #
def _reg_erode(v, a, b): return ndimage.binary_erosion(_bin(v), iterations=_it(a)).astype(np.float64)
def _reg_dilate(v, a, b): return ndimage.binary_dilation(_bin(v), iterations=_it(a)).astype(np.float64)
def _reg_open(v, a, b): return ndimage.binary_opening(_bin(v), iterations=_it(a)).astype(np.float64)
def _reg_close(v, a, b): return ndimage.binary_closing(_bin(v), iterations=_it(a)).astype(np.float64)
def _fill_holes(v, a, b): return ndimage.binary_fill_holes(_bin(v)).astype(np.float64)


def _select_largest(v, a, b):
    lab, n = ndimage.label(_bin(v))
    if n == 0:
        return np.zeros_like(v, np.float64)
    sizes = ndimage.sum(np.ones_like(lab), lab, index=range(1, n + 1))
    return (lab == (int(np.argmax(sizes)) + 1)).astype(np.float64)


def _remove_small(v, a, b):
    lab, n = ndimage.label(_bin(v))
    if n == 0:
        return np.zeros_like(v, np.float64)
    sizes = ndimage.sum(np.ones_like(lab), lab, index=range(1, n + 1))
    thr = (0.01 + 0.15 * a) * v.size
    keep = np.zeros_like(v, np.float64)
    for i, s in enumerate(sizes, 1):
        if s >= thr:
            keep[lab == i] = 1.0
    return keep


def _invert_region(v, a, b): return 1.0 - _bin(v).astype(np.float64)


# --- region -> feature (measurement) ----------------------------------------- #
def _blob_count(v, a, b):
    _, n = ndimage.label(_bin(v))
    return np.float64(n)


def _area_frac(v, a, b):
    return np.float64(np.mean(_bin(v)))


@dataclass
class Op:
    name: str
    category: str
    halcon: str
    in_sort: str
    out_sort: str
    fn: Callable
    c_stmt: Optional[Callable[[float, float], str]] = None


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
    ("identity", "misc", "copy_image", ANY, ANY, _identity),
    # image -> image
    ("gaussian", "smoothing", "gauss_filter", IMAGE, IMAGE, _gaussian),
    ("mean_box", "smoothing", "mean_image", IMAGE, IMAGE, _mean_box),
    ("bilateral", "smoothing", "bilateral_filter", IMAGE, IMAGE, _bilateral),
    ("unsharp", "smoothing", "emphasize", IMAGE, IMAGE, _unsharp),
    ("median", "rank", "median_image", IMAGE, IMAGE, _median),
    ("min_filter", "rank", "gray_erosion_rect", IMAGE, IMAGE, _min_filter),
    ("max_filter", "rank", "gray_dilation_rect", IMAGE, IMAGE, _max_filter),
    ("percentile", "rank", "rank_image", IMAGE, IMAGE, _percentile),
    ("gerode", "morphology", "gray_erosion", IMAGE, IMAGE, _erode_g),
    ("gdilate", "morphology", "gray_dilation", IMAGE, IMAGE, _dilate_g),
    ("gopen", "morphology", "gray_opening", IMAGE, IMAGE, _open_g),
    ("gclose", "morphology", "gray_closing", IMAGE, IMAGE, _close_g),
    ("tophat", "morphology", "gray_tophat", IMAGE, IMAGE, _tophat),
    ("bothat", "morphology", "gray_bothat", IMAGE, IMAGE, _bothat),
    ("morph_grad", "morphology", "gray_range_rect", IMAGE, IMAGE, _morph_grad),
    ("sobel_mag", "edges", "sobel_amp", IMAGE, IMAGE, _sobel_mag),
    ("laplace", "edges", "laplace", IMAGE, IMAGE, _laplace),
    ("prewitt_mag", "edges", "prewitt", IMAGE, IMAGE, _prewitt_mag),
    ("roberts_mag", "edges", "roberts", IMAGE, IMAGE, _roberts_mag),
    ("dog", "edges", "diff_of_gauss", IMAGE, IMAGE, _dog),
    ("gamma", "gray", "pow_image", IMAGE, IMAGE, _gamma),
    ("invert", "gray", "invert_image", IMAGE, IMAGE, _invert),
    ("scale_clip", "gray", "scale_image", IMAGE, IMAGE, _scale_clip),
    ("equalize", "gray", "equ_histo_image", IMAGE, IMAGE, _equalize),
    ("sigmoid", "gray", "scale_image_max", IMAGE, IMAGE, _sigmoid),
    ("lowpass", "frequency", "lowpass", IMAGE, IMAGE, _lowpass),
    ("highpass", "frequency", "highpass", IMAGE, IMAGE, _highpass),
    ("std_filter", "texture", "deviation_image", IMAGE, IMAGE, _std_filter),
    # image -> region (segmentation)
    ("threshold", "segmentation", "threshold", IMAGE, REGION, _threshold),
    ("otsu", "segmentation", "binary_threshold", IMAGE, REGION, _otsu),
    ("dyn_threshold", "segmentation", "dyn_threshold", IMAGE, REGION, _dyn_threshold),
    # region -> region
    ("reg_erode", "region", "erosion_circle", REGION, REGION, _reg_erode),
    ("reg_dilate", "region", "dilation_circle", REGION, REGION, _reg_dilate),
    ("reg_open", "region", "opening_circle", REGION, REGION, _reg_open),
    ("reg_close", "region", "closing_circle", REGION, REGION, _reg_close),
    ("fill_holes", "region", "fill_up", REGION, REGION, _fill_holes),
    ("select_largest", "region", "select_shape_largest", REGION, REGION, _select_largest),
    ("remove_small", "region", "select_shape_area", REGION, REGION, _remove_small),
    ("invert_region", "region", "complement", REGION, REGION, _invert_region),
    # region -> feature (measurement)
    ("blob_count", "features", "count_obj", REGION, FEATURE, _blob_count),
    ("area_frac", "features", "area_center", REGION, FEATURE, _area_frac),
]

REGISTRY: list[Op] = [Op(n, c, h, i, o, f, _c(n)) for (n, c, h, i, o, f) in _DEFS]
RT: dict[str, Callable] = {op.name: op.fn for op in REGISTRY}
_BY_NAME: dict[str, Op] = {op.name: op for op in REGISTRY}
OPS = tuple((op.name, op.fn) for op in REGISTRY)  # back-compat
N_OPS = len(REGISTRY)
N_SLOTS = 6
GENOME_LEN = N_SLOTS * 3


def categories() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for op in REGISTRY:
        out.setdefault(op.category, []).append(op.name)
    return out


def _candidates(sort: str) -> list[Op]:
    return [op for op in REGISTRY if op.in_sort == sort or op.in_sort == ANY]


@dataclass
class Stage:
    op: str
    a: float
    b: float
    sort: str  # the sort this stage operates on (for readability/codegen)


def decode(genome) -> list[Stage]:
    """Type-aware decode: each slot picks a sort-compatible op; sort threads through."""
    g = np.clip(np.asarray(genome, np.float64), 0.0, 1.0)
    sort = IMAGE
    out: list[Stage] = []
    for i in range(N_SLOTS):
        t, a, b = g[3 * i], g[3 * i + 1], g[3 * i + 2]
        cands = _candidates(sort)
        op = cands[min(len(cands) - 1, int(t * len(cands)))]
        out.append(Stage(op.name, float(a), float(b), sort))
        if op.name != "identity":
            sort = op.out_sort
    return out


def _apply(stages, img):
    v = img.astype(np.float64)
    for st in stages:
        v = RT[st.op](v, st.a, st.b)
        if isinstance(v, np.ndarray) and v.ndim == 2:
            v = np.clip(v, 0.0, 1.0)
    return v


def run_genome(genome, img):
    """Run the decoded pipeline; returns an image/region (2-D array) or a feature (scalar)."""
    return _apply(decode(genome), img)


def run_stages(stages: list, img):
    return _apply(stages, img)


def apply_genome(genome, img):
    """Back-compat: coerce the final value to a 2-D array (feature -> constant image)."""
    v = run_genome(genome, img)
    if not (isinstance(v, np.ndarray) and v.ndim == 2):
        return np.full(img.shape, float(np.clip(np.mean(v), 0, 1)), np.float64)
    return v


def stage(op: str, a: float, b: float) -> Stage:
    """Build one typed stage (for hand-written baseline pipelines)."""
    return Stage(op, a, b, _BY_NAME[op].in_sort)


def pipeline_str(genome) -> str:
    parts = [f"{s.op}(a={s.a:.2f},b={s.b:.2f})" for s in decode(genome) if s.op != "identity"]
    return " -> ".join(parts) if parts else "identity"


def psnr(a, b) -> float:
    mse = float(np.mean((np.asarray(a, np.float64) - np.asarray(b, np.float64)) ** 2))
    return 99.0 if mse <= 1e-12 else float(10.0 * np.log10(1.0 / mse))
