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
CONTOUR, MATCH = "contour", "match"   # XLD subpixel contours / template-match result
VOLUME = "volume"                     # 3D voxel array (CT/MRI/depth stacks)
COLOR = "color"                       # multichannel H x W x 3 (RGB); reached via cfa_to_rgb

# Matching context: the locate problem sets a reference template here before scoring
# (matching needs a model + a search image; the pipeline threads the image, the model
# comes from context). Honest coupling — documented, single-threaded.
_MATCH_CTX: dict = {"template": None}


def set_match_template(t) -> None:
    _MATCH_CTX["template"] = None if t is None else np.asarray(t, np.float64)


def _k(a: float) -> int:
    return (3, 5, 7, 9)[min(3, int(a * 4))]


def _it(a: float) -> int:
    return 1 + int(a * 3)  # morphology iterations 1..4


def _norm(x):
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


def _shift_edge(x, dy, dx):
    """Shift like ``np.roll`` but REPLICATE the border instead of wrapping around.

    ``np.roll`` is circular, so a neighbourhood built from it makes the first
    column/row see the LAST column/row of the image. Every local neighbourhood
    here must stay inside the image, so out-of-image taps are clamped to the
    nearest in-image pixel (``mode="edge"``). Interior values are bit-identical
    to ``np.roll``; only the border ring changes.
    """
    x = np.asarray(x, np.float64)
    H, W = x.shape[0], x.shape[1]
    py0, py1, px0, px1 = max(dy, 0), max(-dy, 0), max(dx, 0), max(-dx, 0)
    p = np.pad(x, ((py0, py1), (px0, px1)), mode="edge")
    return p[py1:py1 + H, px1:px1 + W]


def _signed01(x):
    """Map a signed response to [0,1] with the zero-crossing at 0.5 (preserves the
    negative half that a plain _norm→[-1,1] would lose to the pipeline's clip)."""
    x = np.asarray(x, np.float64)
    m = float(np.max(np.abs(x))) if x.size else 0.0
    return np.clip(x / (2 * m) + 0.5, 0, 1) if m > 1e-8 else np.full_like(x, 0.5)


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
    return _norm(np.hypot(v - _shift_edge(v, -1, -1), _shift_edge(v, 0, -1) - _shift_edge(v, -1, 0)))


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
            sh = _shift_edge(v, dy, dx)   # edge-clamped: never wraps to the opposite border
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
def _highpass(v, a, b): return _signed01(_fft_mask(v, 0.02 + 0.3 * a, True))
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
def _reg_close(v, a, b): return ndimage.binary_closing(_bin(v), iterations=_it(a), border_value=1).astype(np.float64)
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


# --- more image -> image ----------------------------------------------------- #
def _grad_dir(v, a, b):
    return (np.arctan2(ndimage.sobel(v, 0), ndimage.sobel(v, 1)) + np.pi) / (2 * np.pi)


def _log(v, a, b):
    return _norm(np.abs(ndimage.gaussian_laplace(v, sigma=0.5 + 2.5 * a)))


# --- more image -> region ---------------------------------------------------- #
def _canny(v, a, b):
    g = ndimage.gaussian_filter(v, 0.5 + 1.5 * a)
    m = _norm(np.hypot(ndimage.sobel(g, 1), ndimage.sobel(g, 0)))
    return (m > (0.1 + 0.5 * b)).astype(np.float64)


def _local_max(v, a, b):
    return ((v >= ndimage.maximum_filter(v, size=_k(a))) & (v > (0.3 + 0.4 * b))).astype(np.float64)


# --- more region ops --------------------------------------------------------- #
def _dist_transform(v, a, b):
    return _norm(ndimage.distance_transform_edt(_bin(v)))


def _region_boundary(v, a, b):
    return (_bin(v).astype(np.float64) - ndimage.binary_erosion(_bin(v)).astype(np.float64)).clip(0, 1)


def _convex_fill(v, a, b):
    return ndimage.binary_closing(_bin(v), iterations=_it(a) + 2, border_value=1).astype(np.float64)


# --- image -> contour (XLD) -------------------------------------------------- #
def _edges_sub_pix(v, a, b):
    m = _norm(np.hypot(ndimage.sobel(v, 1), ndimage.sobel(v, 0)))
    lab, n = ndimage.label(m > (0.15 + 0.5 * a), structure=np.ones((3, 3)))
    cs = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) >= 3:
            cs.append(np.stack([ys, xs], 1).astype(np.float64))
    return {"shape": v.shape, "cs": cs}


# --- contour -> contour ------------------------------------------------------ #
def _select_contours(cv, a, b):
    thr = 3 + int(a * 40)
    return {"shape": cv["shape"], "cs": [c for c in cv["cs"] if len(c) >= thr]}


def _smooth_contours(cv, a, b):
    w = 1 + int(a * 3); out = []
    for c in cv["cs"]:
        if len(c) > 2 * w + 1:
            k = np.ones(2 * w + 1) / (2 * w + 1)
            out.append(np.stack([np.convolve(c[:, 0], k, "same"), np.convolve(c[:, 1], k, "same")], 1))
        else:
            out.append(c)
    return {"shape": cv["shape"], "cs": out}


def _fit_line_contours(cv, a, b):
    out = []
    for c in cv["cs"]:
        if len(c) >= 2:
            mean = c.mean(0); _, _, vt = np.linalg.svd(c - mean); d = vt[0]
            t = (c - mean) @ d
            out.append(mean + np.outer(np.linspace(t.min(), t.max(), max(2, len(c))), d))
        else:
            out.append(c)
    return {"shape": cv["shape"], "cs": out}


# --- contour -> region ------------------------------------------------------- #
def _contours_to_region(cv, a, b):
    H, W = cv["shape"]; mask = np.zeros((H, W), np.float64)
    for c in cv["cs"]:
        idx = np.clip(np.round(c).astype(int), [0, 0], [H - 1, W - 1])
        mask[idx[:, 0], idx[:, 1]] = 1.0
    return ndimage.binary_dilation(mask > 0.5, iterations=1 + int(a * 2)).astype(np.float64)


# --- contour -> feature ------------------------------------------------------ #
def _count_contours(cv, a, b):
    return np.float64(len(cv["cs"]))


def _total_length(cv, a, b):
    tot = 0.0
    for c in cv["cs"]:
        if len(c) >= 2:
            tot += float(np.sum(np.hypot(np.diff(c[:, 0]), np.diff(c[:, 1]))))
    return np.float64(tot)


# --- image -> match (template matching) -------------------------------------- #
def _ncc_map(v, T):
    """Normalized cross-correlation of template `T` over image `v` (Lewis 1995).

    Value at (y,x) is Pearson's correlation between `T` and the T-sized window
    centred there::

        sum_w (I_w - mean_w)(T - mean_T) / (||I_w - mean_w|| * ||T - mean_T||)

    so it is bounded to [-1,1], invariant to the window's brightness/contrast,
    and 1.0 exactly for a match up to a positive affine map. Raw correlation
    (no local normalization) instead peaks on whatever is brightest/largest.
    Positions where the template does not fully overlap the image, flat windows
    and a zero-energy template all score 0 (no match).
    """
    v = np.asarray(v, np.float64)
    T = np.asarray(T, np.float64)
    if T.ndim != v.ndim:
        return np.zeros_like(v)
    Tz = T - float(T.mean())
    tnorm = float(np.sqrt(np.sum(Tz * Tz)))
    if tnorm < 1e-12:
        return np.zeros_like(v)
    num = ndimage.correlate(v, Tz, mode="constant")          # sum(Tz) == 0 -> mean-free
    m1 = ndimage.uniform_filter(v, size=T.shape, mode="constant")
    m2 = ndimage.uniform_filter(v * v, size=T.shape, mode="constant")
    den = np.sqrt(np.maximum(m2 - m1 * m1, 0.0) * float(T.size)) * tnorm
    ok = np.zeros(v.shape, bool)                             # full-overlap positions only
    lo = tuple(s // 2 for s in T.shape)
    hi = tuple(n - (s - 1 - s // 2) for n, s in zip(v.shape, T.shape))
    if all(h > l for l, h in zip(lo, hi)):
        ok[tuple(slice(l, h) for l, h in zip(lo, hi))] = True
    out = np.zeros_like(v)
    np.divide(num, den, out=out, where=ok & (den > 1e-12))
    return np.clip(out, -1.0, 1.0)


def _ncc_locate(v, a, b):
    T = _MATCH_CTX.get("template")
    if T is None or not (isinstance(v, np.ndarray) and v.ndim == 2):
        return np.array([0.0, 0.0, 0.0])
    corr = _ncc_map(v, T)
    idx = np.unravel_index(int(np.argmax(corr)), corr.shape)
    return np.array([float(corr[idx]), float(idx[0]), float(idx[1])])


# --- geometry (image -> image; calibration/rectification building blocks) ----- #
def _rotate_img(v, a, b):
    return np.clip(ndimage.rotate(v, angle=-45 + 90 * a, reshape=False, mode="reflect"), 0, 1)


def _rescale_img(v, a, b):
    s = 0.7 + 0.6 * a
    off = (v.shape[0] * (1 - 1 / s) / 2, v.shape[1] * (1 - 1 / s) / 2)
    return np.clip(ndimage.affine_transform(v, np.array([1 / s, 1 / s]), offset=off, mode="reflect"), 0, 1)


def _affine_warp(v, a, b):
    ang = np.deg2rad(-20 + 40 * a); sh = (b - 0.5) * 0.4
    M = np.array([[np.cos(ang), -np.sin(ang) + sh], [np.sin(ang), np.cos(ang)]])
    c = np.array(v.shape) / 2
    return np.clip(ndimage.affine_transform(v, M, offset=c - M @ c, mode="reflect"), 0, 1)


# --- more filters (OpenCV/skimage families) ---------------------------------- #
def _gabor(v, a, b):
    theta = np.pi * a; freq = 0.1 + 0.3 * b; k = 7
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    xr = xx * np.cos(theta) + yy * np.sin(theta)
    g = np.exp(-(xx * xx + yy * yy) / 8.0) * np.cos(2 * np.pi * freq * xr)
    g = g - g.mean()   # DC-free (zero-mean) kernel: a Gabor is band-pass, not a brightness detector
    return _norm(np.abs(ndimage.convolve(v, g, mode="reflect")))


def _clahe(v, a, b):
    nb = 2 + int(a * 3); H, W = v.shape; out = v.copy()
    # Boundaries from linspace so the tiles PARTITION the image: the last tile
    # absorbs the H % nb / W % nb remainder instead of leaving it unequalised.
    ys = np.linspace(0, H, nb + 1).astype(int); xs = np.linspace(0, W, nb + 1).astype(int)
    for i in range(nb):
        for j in range(nb):
            blk = v[ys[i]:ys[i + 1], xs[j]:xs[j + 1]]
            if blk.size:
                out[ys[i]:ys[i + 1], xs[j]:xs[j + 1]] = _equalize(blk, 0, 0)
    return out


def _corner_response(v, a, b):
    gx = ndimage.sobel(v, 1); gy = ndimage.sobel(v, 0); s = 0.5 + 2.0 * a
    axx = ndimage.gaussian_filter(gx * gx, s); ayy = ndimage.gaussian_filter(gy * gy, s)
    axy = ndimage.gaussian_filter(gx * gy, s)
    return _signed01(axx * ayy - axy * axy - 0.04 * (axx + ayy) ** 2)


def _adaptive_gauss_thresh(v, a, b):
    return (v > ndimage.gaussian_filter(v, 1.0 + 3.0 * a) + (b - 0.5) * 0.3).astype(np.float64)


# --- shape-based matching (rotation invariant; image -> match) --------------- #
def _shape_locate(v, a, b):
    T = _MATCH_CTX.get("template")
    if T is None or not (isinstance(v, np.ndarray) and v.ndim == 2):
        return np.array([0.0, 0.0, 0.0, 0.0])
    best = [-1e18, 0.0, 0.0, 0.0]
    for ang in range(0, 360, 30):
        corr = _ncc_map(v, ndimage.rotate(T, ang, reshape=False))   # NCC per rotation
        idx = np.unravel_index(int(np.argmax(corr)), corr.shape)
        m = float(corr[idx])
        if m > best[0]:
            best = [m, float(idx[0]), float(idx[1]), float(ang)]
    return np.array(best)


# --- classification (region -> feature; OCR/decision basis) ------------------ #
def _classify_shape(v, a, b):
    lab, n = ndimage.label(_bin(v))
    if n == 0:
        return np.float64(0.0)
    sizes = ndimage.sum(np.ones_like(lab), lab, index=range(1, n + 1))
    mask = lab == (int(np.argmax(sizes)) + 1)
    area = float(mask.sum())
    per = float((mask.astype(np.float64) - ndimage.binary_erosion(mask).astype(np.float64)).sum())
    return np.float64(min(1.0, 4 * np.pi * area / (per * per)) if per > 0 else 0.0)  # ~1 circle


# --- barcode-lite (image -> feature; count dark bars on the mid scanline) ---- #
def _decode_barcode(v, a, b):
    row = (v[v.shape[0] // 2] < (0.3 + 0.4 * a)).astype(int)
    return np.float64(int((np.diff(np.concatenate([[0], row, [0]])) == 1).sum()))


# --- 3D volume ops (scipy.ndimage is N-D; CT/MRI/depth stacks) --------------- #
def _vol_gaussian(v, a, b):
    return ndimage.gaussian_filter(v, sigma=0.3 + 2.7 * a)


def _vol_median(v, a, b):
    return ndimage.median_filter(v, size=3)


def _vol_erode(v, a, b):
    return ndimage.grey_erosion(v, size=1 + 2 * (1 + int(a)))


def _vol_dilate(v, a, b):
    return ndimage.grey_dilation(v, size=1 + 2 * (1 + int(a)))


def _vol_threshold(v, a, b):
    return (v > a).astype(np.float64)                    # volume -> binary volume


def _vol_mip(v, a, b):
    return _norm(np.max(v, axis=0))                      # volume -> image (max-intensity projection)


def _vol_slice(v, a, b):
    return np.clip(v[min(v.shape[0] - 1, int(a * v.shape[0]))], 0, 1)  # volume -> image


def _vol_count(v, a, b):
    return np.float64(ndimage.label(np.asarray(v) > 0.5)[1])          # volume -> feature (3D blobs)


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
    ("prewitt_mag", "edges", "prewitt_amp", IMAGE, IMAGE, _prewitt_mag),
    ("roberts_mag", "edges", "roberts", IMAGE, IMAGE, _roberts_mag),
    ("dog", "edges", "diff_of_gauss", IMAGE, IMAGE, _dog),
    ("gamma", "gray", "pow_image", IMAGE, IMAGE, _gamma),
    ("invert", "gray", "invert_image", IMAGE, IMAGE, _invert),
    ("scale_clip", "gray", "scale_image", IMAGE, IMAGE, _scale_clip),
    ("equalize", "gray", "equ_histo_image", IMAGE, IMAGE, _equalize),
    ("sigmoid", "gray", "scale_image_max", IMAGE, IMAGE, _sigmoid),
    ("lowpass", "frequency", "", IMAGE, IMAGE, _lowpass),
    ("highpass", "frequency", "highpass_image", IMAGE, IMAGE, _highpass),
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
    ("select_largest", "region", "select_shape_std", REGION, REGION, _select_largest),
    ("remove_small", "region", "select_shape", REGION, REGION, _remove_small),
    ("invert_region", "region", "complement", REGION, REGION, _invert_region),
    # region -> feature (measurement)
    ("blob_count", "features", "count_obj", REGION, FEATURE, _blob_count),
    ("area_frac", "features", "area_center", REGION, FEATURE, _area_frac),
    # extra image ops
    ("grad_dir", "edges", "", IMAGE, IMAGE, _grad_dir),
    ("log", "edges", "laplace_of_gauss", IMAGE, IMAGE, _log),
    # extra segmentation (image -> region)
    ("canny", "segmentation", "edges_image", IMAGE, REGION, _canny),
    ("local_max", "segmentation", "local_max_sub_pix", IMAGE, REGION, _local_max),
    # extra region ops
    ("dist_transform", "region", "distance_transform", REGION, IMAGE, _dist_transform),
    ("region_boundary", "region", "boundary", REGION, REGION, _region_boundary),
    ("convex_fill", "region", "shape_trans", REGION, REGION, _convex_fill),
    # image -> contour (XLD)
    ("edges_sub_pix", "contour", "edges_sub_pix", IMAGE, CONTOUR, _edges_sub_pix),
    # contour -> contour
    ("select_contours", "contour", "select_contours_xld", CONTOUR, CONTOUR, _select_contours),
    ("smooth_contours", "contour", "smooth_contours_xld", CONTOUR, CONTOUR, _smooth_contours),
    ("fit_line_contours", "contour", "fit_line_contour_xld", CONTOUR, CONTOUR, _fit_line_contours),
    # contour -> region / feature
    ("contours_to_region", "contour", "gen_region_contour_xld", CONTOUR, REGION, _contours_to_region),
    ("count_contours", "features", "count_obj", CONTOUR, FEATURE, _count_contours),
    ("total_length", "features", "length_xld", CONTOUR, FEATURE, _total_length),
    # image -> match (template matching)
    ("ncc_locate", "matching", "find_ncc_model", IMAGE, MATCH, _ncc_locate),
    # geometry (calibration/rectification basis)
    ("rotate_img", "geometry", "rotate_image", IMAGE, IMAGE, _rotate_img),
    ("rescale_img", "geometry", "zoom_image_size", IMAGE, IMAGE, _rescale_img),
    ("affine_warp", "geometry", "affine_trans_image", IMAGE, IMAGE, _affine_warp),
    # extra filters
    ("gabor", "texture", "gen_gabor", IMAGE, IMAGE, _gabor),
    ("clahe", "gray", "", IMAGE, IMAGE, _clahe),
    ("corner_response", "edges", "points_harris", IMAGE, IMAGE, _corner_response),
    ("adaptive_gauss_thresh", "segmentation", "local_threshold", IMAGE, REGION, _adaptive_gauss_thresh),
    # shape-based matching (rotation invariant)
    ("shape_locate", "matching", "find_shape_model", IMAGE, MATCH, _shape_locate),
    # classification (OCR/decision basis)
    ("classify_shape", "classification", "", REGION, FEATURE, _classify_shape),
    # barcode
    ("decode_barcode", "barcode", "find_bar_code", IMAGE, FEATURE, _decode_barcode),
    # 3D volume (CT/MRI/depth stacks)
    ("vol_gaussian", "3d", "", VOLUME, VOLUME, _vol_gaussian),
    ("vol_median", "3d", "", VOLUME, VOLUME, _vol_median),
    ("vol_erode", "3d", "", VOLUME, VOLUME, _vol_erode),
    ("vol_dilate", "3d", "", VOLUME, VOLUME, _vol_dilate),
    ("vol_threshold", "3d", "", VOLUME, VOLUME, _vol_threshold),
    ("vol_mip", "3d", "", VOLUME, IMAGE, _vol_mip),
    ("vol_slice", "3d", "", VOLUME, IMAGE, _vol_slice),
    ("vol_count", "features", "", VOLUME, FEATURE, _vol_count),
]

REGISTRY: list[Op] = [Op(n, c, h, i, o, f, _c(n)) for (n, c, h, i, o, f) in _DEFS]
RT: dict[str, Callable] = {op.name: op.fn for op in REGISTRY}
_BY_NAME: dict[str, Op] = {op.name: op for op in REGISTRY}
OPS = tuple((op.name, op.fn) for op in REGISTRY)  # back-compat
N_OPS = len(REGISTRY)
N_SLOTS = 6
GENOME_LEN = N_SLOTS * 3

# Optional library backends (scikit-image / OpenCV): wrap the ecosystem so op count
# scales without reimplementing. Disable with IMGEVOLVE_NO_BACKENDS=1 for the pure,
# always-deterministic numpy/scipy core. Adding backends only widens per-sort
# candidate sets — GENOME_LEN is unchanged.
import os as _os  # noqa: E402

if _os.environ.get("IMGEVOLVE_NO_BACKENDS", "") != "1":
    _extra = []
    for _mod in ("backends", "backends_dl", "backends_auto", "backends_color",
                 "backends_extra", "backends_pil", "backends_scipy",
                 "backends_ski2", "backends_cv2b", "backends_r3", "backends_kornia",
                 "backends_filters2", "backends_regions2", "backends_subpix", "backends_xldgeom",
                 "backends_regions3", "backends_imgtools", "backends_measure1d",
                 "backends_physics", "backends_decomp",
                 "backends_inverse", "backends_transform2", "backends_segment2", "backends_tomo",
                 # self-expanding registry: macro ("DNA") ops condensed from evolved
                 # champions (backends_macro.py). LAST, so it can reference any backend
                 # op and minimally perturbs existing registration indices.
                 "backends_macro"):
        try:
            _b = __import__(_mod)
            _extra += _b.build(Op, IMAGE, REGION, FEATURE, CONTOUR, _norm, _bin)
        except Exception:
            pass
    if _extra:
        REGISTRY = REGISTRY + _extra
        RT = {op.name: op.fn for op in REGISTRY}
        _BY_NAME = {op.name: op for op in REGISTRY}
        OPS = tuple((op.name, op.fn) for op in REGISTRY)
        N_OPS = len(REGISTRY)


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


def decode(genome, start: str = IMAGE) -> list[Stage]:
    """Type-aware decode: each slot picks a sort-compatible op; sort threads through."""
    g = np.clip(np.asarray(genome, np.float64), 0.0, 1.0)
    sort = start
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
    v = np.asarray(img, np.float64)
    for st in stages:
        v = RT[st.op](v, st.a, st.b)
        if isinstance(v, np.ndarray) and v.ndim in (2, 3):
            v = np.clip(v, 0.0, 1.0)
    return v


def run_genome(genome, img, start: str = IMAGE):
    """Run the decoded pipeline; returns an image/region (2-D), volume (3-D), or feature."""
    return _apply(decode(genome, start), img)


def run_stages(stages: list, img):
    return _apply(stages, img)


def apply_genome(genome, img):
    """Back-compat: coerce the final value to a 2-D array (feature -> constant image)."""
    v = run_genome(genome, img)
    if isinstance(v, np.ndarray) and v.ndim == 2:
        return v
    if isinstance(v, dict):                       # contour -> use the contour count
        v = float(len(v.get("cs", [])))
    try:
        m = float(np.clip(np.mean(np.asarray(v, np.float64)), 0, 1))
    except Exception:
        m = 0.0
    return np.full(img.shape, m, np.float64)


def stage(op: str, a: float, b: float) -> Stage:
    """Build one typed stage (for hand-written baseline pipelines)."""
    return Stage(op, a, b, _BY_NAME[op].in_sort)


def pipeline_str(genome, start: str = IMAGE) -> str:
    parts = [f"{s.op}(a={s.a:.2f},b={s.b:.2f})" for s in decode(genome, start) if s.op != "identity"]
    return " -> ".join(parts) if parts else "identity"


# --------------------------------------------------------------------------- #
# Wave-0: stable op slots + name-pinned (cross-install) champion records.       #
# --------------------------------------------------------------------------- #
# SLOTS freezes each op's registration-order index the moment REGISTRY is fully
# built (core _DEFS first, then any optional backends in import order). decode()
# indexes _candidates(sort) in exactly this order, so within a given install the
# genome->op mapping is deterministic and documented by SLOTS.
#
# CROSS-INSTALL CAVEAT (honest): the index a genome resolves to depends on how
# many candidates a sort has, which grows with the optional backends present in
# THIS install. Re-sorting _candidates to a globally stable order WOULD change
# that mapping and therefore change every existing champion — so decode() is
# deliberately left byte-identical (proven in tests/test_wave0.py). Reproducing a
# champion across installs is done by op NAME instead of index: pipeline_stages()
# records the champion as (name, a, b) and decode_by_names() rebuilds the exact
# pipeline from those names, independent of the index layout. See docs/WAVE0_STABLE_SLOTS.md.
#
# A few names occur twice (a backend overrides a core op, e.g. "laplace"). Like RT
# and _BY_NAME, SLOTS resolves a name to its LAST (canonical) occurrence — the op
# that actually executes (decode() stores a name; _apply runs RT[name]). Name-pinned
# reload is therefore consistent with execution on both sides.
SLOTS: dict[str, int] = {op.name: i for i, op in enumerate(REGISTRY)}


def op_slot(name: str) -> int:
    """Stable registration-order slot of an op (frozen when REGISTRY was built)."""
    return SLOTS[name]


def stages_str(stages) -> str:
    """Render a decoded pipeline (list[Stage]) to the same string form as
    pipeline_str, but from stages rather than a genome (drops identity)."""
    parts = [f"{s.op}(a={s.a:.2f},b={s.b:.2f})" for s in stages if s.op != "identity"]
    return " -> ".join(parts) if parts else "identity"


def pipeline_stages(genome, start: str = IMAGE) -> list[dict]:
    """Name-pinned champion record: the decoded pipeline as a list of
    ``{"op", "a", "b", "sort"}`` dicts (identity dropped). Index-independent, so
    it reloads to the SAME pipeline on any install that has the named ops, via
    :func:`decode_by_names`. This is the cross-install-reproducible counterpart
    to the index-based :func:`decode`."""
    return [{"op": s.op, "a": float(s.a), "b": float(s.b), "sort": s.sort}
            for s in decode(genome, start) if s.op != "identity"]


def decode_by_names(stage_specs) -> list[Stage]:
    """Reconstruct a pipeline from op NAMES (independent of registry index order).

    ``stage_specs`` is an iterable of either ``(name, a, b)`` tuples or dicts with
    keys ``op``/``a``/``b``. Each op's ``in_sort`` is resolved from ``_BY_NAME``,
    so a champion saved by name (see :func:`pipeline_stages`) rebuilds to the same
    pipeline regardless of which optional backends shifted the index layout. Raises
    ``KeyError`` (fail-closed) if a named op is absent in this install."""
    out: list[Stage] = []
    for spec in stage_specs:
        if isinstance(spec, dict):
            name = spec["op"]
            a = float(spec.get("a", 0.0))
            b = float(spec.get("b", 0.0))
        else:
            name, a, b = spec[0], float(spec[1]), float(spec[2])
        out.append(Stage(name, a, b, _BY_NAME[name].in_sort))
    return out


def psnr(a, b) -> float:
    mse = float(np.mean((np.asarray(a, np.float64) - np.asarray(b, np.float64)) ** 2))
    return 99.0 if mse <= 1e-12 else float(10.0 * np.log10(1.0 / mse))
