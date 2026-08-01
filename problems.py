"""imgevolve — problem definitions (the tasks the AI designs algorithms for).

Three shared-DSL problems, each = deterministic dataset + ground truth + a
higher-is-better score. The evolution/baseline/report drivers are problem-agnostic;
they just call PROBLEMS[name].score(genome, data).

  denoise  : recover clean from Gaussian-noised image     -> PSNR (dB)
  edge     : detect edges vs a gradient ground-truth       -> F1
  binarize : segment foreground (clean>0.5) from noisy      -> IoU

Ground truth is derived from the synthetic generator (we make the images, so GT is
known exactly). stdlib + numpy + scipy only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy import ndimage

import ops


def build_genome(stages: list[tuple[str, float, float]]) -> np.ndarray:
    """Construct a [0,1]^GENOME_LEN genome that decodes to the given (op,a,b) list."""
    names = [n for n, _ in ops.OPS]
    g = np.zeros(ops.GENOME_LEN)
    for i, (op, a, b) in enumerate(stages[: ops.N_SLOTS]):
        idx = names.index(op)
        g[3 * i] = (idx + 0.5) / ops.N_OPS
        g[3 * i + 1] = a
        g[3 * i + 2] = b
    return g


def _synth(rng: np.random.Generator, size: int) -> np.ndarray:
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


def _f1(pred_bin, gt_bin) -> float:
    tp = float(np.sum(pred_bin * gt_bin))
    fp = float(np.sum(pred_bin * (1 - gt_bin)))
    fn = float(np.sum((1 - pred_bin) * gt_bin))
    return tp / (tp + 0.5 * (fp + fn)) if (tp + fp + fn) > 0 else 1.0


def _iou(pred_bin, gt_bin) -> float:
    inter = float(np.sum(pred_bin * gt_bin))
    union = float(np.sum(np.clip(pred_bin + gt_bin, 0, 1)))
    return inter / union if union > 0 else 1.0


@dataclass
class Problem:
    name: str
    unit: str
    make: Callable[[int, int, int], dict]
    score: Callable[[np.ndarray, dict], float]
    hand: Callable[[], np.ndarray]


# --- denoise ----------------------------------------------------------------- #
def _make_denoise(n, size, seed, noise=0.2):
    clean = _clean_stack(n, size, seed)
    rng = np.random.default_rng(seed + 1)
    noisy = np.clip(clean + rng.normal(0, noise, clean.shape), 0.0, 1.0)
    return {"input": noisy, "target": clean}


def _score_denoise(genome, data):
    inp, tgt = data["input"], data["target"]
    return float(np.mean([ops.psnr(ops.apply_genome(genome, inp[i]), tgt[i]) for i in range(len(inp))]))


# --- edge -------------------------------------------------------------------- #
def _make_edge(n, size, seed, noise=0.05):
    clean = _clean_stack(n, size, seed)
    rng = np.random.default_rng(seed + 2)
    inp = np.clip(clean + rng.normal(0, noise, clean.shape), 0.0, 1.0)
    gt = np.stack([(np.hypot(ndimage.sobel(c, 1), ndimage.sobel(c, 0)) > 0.5).astype(np.float64) for c in clean])
    return {"input": inp, "gt": gt}


def _score_edge(genome, data):
    inp, gt = data["input"], data["gt"]
    return float(np.mean([_f1((ops.apply_genome(genome, inp[i]) > 0.5).astype(np.float64), gt[i])
                          for i in range(len(inp))]))


# --- binarize ---------------------------------------------------------------- #
def _make_binarize(n, size, seed, noise=0.15):
    clean = _clean_stack(n, size, seed)
    rng = np.random.default_rng(seed + 3)
    inp = np.clip(clean + rng.normal(0, noise, clean.shape), 0.0, 1.0)
    gt = (clean > 0.5).astype(np.float64)
    return {"input": inp, "gt": gt}


def _score_binarize(genome, data):
    inp, gt = data["input"], data["gt"]
    return float(np.mean([_iou((ops.apply_genome(genome, inp[i]) > 0.5).astype(np.float64), gt[i])
                          for i in range(len(inp))]))


PROBLEMS: dict[str, Problem] = {
    "denoise": Problem("denoise", "dB PSNR", _make_denoise, _score_denoise,
                       lambda: build_genome([("gaussian", (1.0 - 0.3) / 2.7, 0.0)])),
    "edge": Problem("edge", "F1", _make_edge, _score_edge,
                    lambda: build_genome([("sobel_mag", 0.0, 0.0), ("threshold", 0.2, 0.0)])),
    "binarize": Problem("binarize", "IoU", _make_binarize, _score_binarize,
                        lambda: build_genome([("gaussian", 0.3, 0.0), ("otsu", 0.0, 0.0)])),
}


def trivial_genome() -> np.ndarray:
    """Do-nothing pipeline (all identity)."""
    return np.zeros(ops.GENOME_LEN)
