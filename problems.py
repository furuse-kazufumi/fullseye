"""imgevolve — problem definitions (multi-sort aware).

Four shared-DSL problems; the last exercises the full HALCON-shaped chain
image -> region -> feature:

  denoise  : recover clean from noise            (image target) -> PSNR
  edge     : detect edges vs gradient GT         (region target) -> F1
  binarize : segment foreground (clean>0.5)      (region target) -> IoU
  count    : count foreground blobs              (feature target) -> 1/(1+|err|)

A pipeline's final value may be an image/region (2-D) or a feature (scalar); each
problem coerces it to what its metric needs, so evolution is rewarded for landing
in the right sort.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy import ndimage

import ops


def _synth(rng, size):
    img = np.full((size, size), rng.uniform(0.1, 0.4), np.float64)
    for _ in range(rng.integers(3, 7)):
        v = rng.uniform(0.0, 1.0)
        x0, y0 = rng.integers(0, size, 2)
        w, h = rng.integers(size // 6, size // 2, 2)
        img[y0:y0 + h, x0:x0 + w] = v
    yy, xx = np.mgrid[0:size, 0:size]
    for _ in range(rng.integers(1, 3)):
        cx, cy = rng.integers(0, size, 2)
        r = rng.integers(size // 8, size // 4)
        img[(xx - cx) ** 2 + (yy - cy) ** 2 <= r * r] = rng.uniform(0.0, 1.0)
    return np.clip(img, 0.0, 1.0)


def _clean_stack(n, size, seed):
    rng = np.random.default_rng(seed)
    return np.stack([_synth(rng, size) for _ in range(n)]).astype(np.float64)


def _is_img(v):
    return isinstance(v, np.ndarray) and v.ndim == 2


def _as_image(final, shape):
    if _is_img(final):
        return np.clip(final, 0, 1)
    if isinstance(final, (int, float)) or (isinstance(final, np.ndarray) and final.ndim == 0):
        return np.full(shape, float(np.clip(final, 0, 1)), np.float64)
    return np.zeros(shape, np.float64)  # contour dict / match array -> penalise for image tasks


def _as_binary(final, shape):
    return (_as_image(final, shape) > 0.5).astype(np.float64)


def _as_count(final):
    if _is_img(final):
        return float(ndimage.label(final > 0.5)[1])
    if isinstance(final, dict) and "cs" in final:      # contour -> number of contours
        return float(len(final["cs"]))
    try:
        return float(np.asarray(final).ravel()[0])
    except Exception:
        return 0.0


def _f1(pred, gt):
    tp = float(np.sum(pred * gt)); fp = float(np.sum(pred * (1 - gt))); fn = float(np.sum((1 - pred) * gt))
    return tp / (tp + 0.5 * (fp + fn)) if (tp + fp + fn) > 0 else 1.0


def _iou(pred, gt):
    inter = float(np.sum(pred * gt)); union = float(np.sum(np.clip(pred + gt, 0, 1)))
    return inter / union if union > 0 else 1.0


@dataclass
class Problem:
    name: str
    unit: str
    make: Callable[[int, int, int], dict]
    score_value: Callable  # (final_value, item) -> float (higher better)
    hand_stages: Callable[[], list]

    def score(self, genome, data) -> float:
        inp, items = data["input"], data["items"]
        return float(np.mean([self.score_value(ops.run_genome(genome, inp[i]), items[i]) for i in range(len(inp))]))

    def score_stages(self, stages, data) -> float:
        inp, items = data["input"], data["items"]
        return float(np.mean([self.score_value(ops.run_stages(stages, inp[i]), items[i]) for i in range(len(inp))]))


# --- denoise ----------------------------------------------------------------- #
def _make_denoise(n, size, seed, noise=0.2):
    clean = _clean_stack(n, size, seed)
    noisy = np.clip(clean + np.random.default_rng(seed + 1).normal(0, noise, clean.shape), 0, 1)
    return {"input": noisy, "items": clean}


# --- edge -------------------------------------------------------------------- #
def _make_edge(n, size, seed, noise=0.05):
    clean = _clean_stack(n, size, seed)
    inp = np.clip(clean + np.random.default_rng(seed + 2).normal(0, noise, clean.shape), 0, 1)
    gt = np.stack([(np.hypot(ndimage.sobel(c, 1), ndimage.sobel(c, 0)) > 0.5).astype(np.float64) for c in clean])
    return {"input": inp, "items": gt}


# --- binarize ---------------------------------------------------------------- #
def _make_binarize(n, size, seed, noise=0.15):
    clean = _clean_stack(n, size, seed)
    inp = np.clip(clean + np.random.default_rng(seed + 3).normal(0, noise, clean.shape), 0, 1)
    return {"input": inp, "items": (clean > 0.5).astype(np.float64)}


# --- count ------------------------------------------------------------------- #
def _make_count(n, size, seed, noise=0.12):
    clean = _clean_stack(n, size, seed)
    inp = np.clip(clean + np.random.default_rng(seed + 4).normal(0, noise, clean.shape), 0, 1)
    counts = np.array([float(ndimage.label(c > 0.5)[1]) for c in clean])
    return {"input": inp, "items": counts}


# --- locate (template matching) ---------------------------------------------- #
def _template(size=11):
    yy, xx = np.mgrid[0:size, 0:size]; c = size // 2
    return ((xx - c) ** 2 + (yy - c) ** 2 <= (size // 2 - 1) ** 2).astype(np.float64)


def _make_locate(n, size, seed):
    rng = np.random.default_rng(seed + 5)
    T = _template(11); ops.set_match_template(T); rr = T.shape[0] // 2
    imgs, locs = [], []
    for _ in range(n):
        base = _synth(rng, size) * 0.4
        r = int(rng.integers(rr + 1, size - rr - 1)); c = int(rng.integers(rr + 1, size - rr - 1))
        base[r - rr:r + rr + 1, c - rr:c + rr + 1] = np.maximum(base[r - rr:r + rr + 1, c - rr:c + rr + 1], T)
        imgs.append(np.clip(base + rng.normal(0, 0.1, base.shape), 0, 1)); locs.append([float(r), float(c)])
    return {"input": np.stack(imgs), "items": np.array(locs)}


def _score_locate(final, gt):
    if isinstance(final, np.ndarray) and final.ndim == 1 and final.size >= 3:
        return 1.0 / (1.0 + float(np.hypot(final[1] - gt[0], final[2] - gt[1])))
    return 0.0


PROBLEMS: dict[str, Problem] = {
    "denoise": Problem("denoise", "dB PSNR", _make_denoise,
                       lambda f, tgt: ops.psnr(_as_image(f, tgt.shape), tgt),
                       lambda: [ops.stage("gaussian", (1.0 - 0.3) / 2.7, 0.0)]),
    "edge": Problem("edge", "F1", _make_edge,
                    lambda f, gt: _f1(_as_binary(f, gt.shape), gt),
                    lambda: [ops.stage("sobel_mag", 0.0, 0.0), ops.stage("threshold", 0.2, 0.0)]),
    "binarize": Problem("binarize", "IoU", _make_binarize,
                        lambda f, gt: _iou(_as_binary(f, gt.shape), gt),
                        lambda: [ops.stage("gaussian", 0.3, 0.0), ops.stage("otsu", 0.0, 0.0)]),
    "count": Problem("count", "1/(1+err)", _make_count,
                     lambda f, gtc: 1.0 / (1.0 + abs(_as_count(f) - gtc)),
                     lambda: [ops.stage("gaussian", 0.3, 0.0), ops.stage("otsu", 0.0, 0.0),
                              ops.stage("remove_small", 0.2, 0.0), ops.stage("blob_count", 0.0, 0.0)]),
    "locate": Problem("locate", "1/(1+px)", _make_locate, _score_locate,
                      lambda: [ops.stage("gaussian", 0.2, 0.0), ops.stage("ncc_locate", 0.0, 0.0)]),
}


def trivial_stages() -> list:
    return []
