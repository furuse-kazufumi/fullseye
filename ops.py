"""imgevolve — typed image-op DSL, genome apply, dataset, PSNR.

The genome the evolutionary search optimises is a fixed-length float vector in
[0,1]^(N_SLOTS*3): N_SLOTS pipeline stages, each decoded to (op, p1, p2). Decoding
is deterministic, so the same genome always yields the same pipeline (mirrors the
r2 "bit-identical determinism" discipline). Every op is a pure image->image map,
which is what makes the pipeline verifiable and (later, S2) emittable to C/etc.

Images are float32 in [0,1], single channel. stdlib + numpy + scipy.ndimage only.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

# --- op-DSL ------------------------------------------------------------------ #
# Each op is (name, apply(img, a, b)->img). a,b are decoded params in [0,1].
# identity lets the search use an effectively shorter pipeline.


def _identity(img: np.ndarray, a: float, b: float) -> np.ndarray:
    return img


def _gaussian(img: np.ndarray, a: float, b: float) -> np.ndarray:
    sigma = 0.3 + 2.7 * a  # [0.3, 3.0]
    return ndimage.gaussian_filter(img, sigma=sigma)


def _median(img: np.ndarray, a: float, b: float) -> np.ndarray:
    k = (3, 5, 7)[min(2, int(a * 3))]  # {3,5,7}
    return ndimage.median_filter(img, size=k)


def _uniform(img: np.ndarray, a: float, b: float) -> np.ndarray:
    k = 3 + 2 * int(a * 3)  # {3,5,7}
    return ndimage.uniform_filter(img, size=k)


def _gamma(img: np.ndarray, a: float, b: float) -> np.ndarray:
    g = 0.5 + 1.5 * a  # [0.5, 2.0]
    return np.clip(img, 0.0, 1.0) ** g


def _sharpen(img: np.ndarray, a: float, b: float) -> np.ndarray:
    amount = 1.5 * a  # [0, 1.5]
    sigma = 0.5 + 1.5 * b  # [0.5, 2.0]
    blur = ndimage.gaussian_filter(img, sigma=sigma)
    return img + amount * (img - blur)


OPS: tuple = (
    ("identity", _identity),
    ("gaussian", _gaussian),
    ("median", _median),
    ("uniform", _uniform),
    ("gamma", _gamma),
    ("sharpen", _sharpen),
)
N_OPS = len(OPS)
N_SLOTS = 4
GENOME_LEN = N_SLOTS * 3


@dataclass
class Stage:
    op: str
    a: float
    b: float


def decode(genome: np.ndarray) -> list[Stage]:
    """Decode a [0,1]^GENOME_LEN vector into a list of typed stages."""
    g = np.clip(np.asarray(genome, np.float64), 0.0, 1.0)
    stages: list[Stage] = []
    for i in range(N_SLOTS):
        t, a, b = g[3 * i], g[3 * i + 1], g[3 * i + 2]
        op_idx = min(N_OPS - 1, int(t * N_OPS))
        stages.append(Stage(OPS[op_idx][0], float(a), float(b)))
    return stages


def apply_genome(genome: np.ndarray, img: np.ndarray) -> np.ndarray:
    """Run the decoded pipeline on one image; result clipped to [0,1]."""
    out = img.astype(np.float64)
    fns = {name: fn for name, fn in OPS}
    for st in decode(genome):
        out = fns[st.op](out, st.a, st.b)
    return np.clip(out, 0.0, 1.0)


def pipeline_str(genome: np.ndarray) -> str:
    """Human-readable pipeline (skips identity) — the 'algorithm' the AI designed."""
    parts = [f"{s.op}(a={s.a:.2f},b={s.b:.2f})" for s in decode(genome) if s.op != "identity"]
    return " -> ".join(parts) if parts else "identity"


# --- dataset (synthetic, deterministic) -------------------------------------- #


def _one_image(rng: np.random.Generator, size: int) -> np.ndarray:
    """Piecewise-constant canvas with rectangles + circles (edges matter for denoise)."""
    img = np.full((size, size), rng.uniform(0.1, 0.4), np.float64)
    for _ in range(rng.integers(3, 7)):
        val = rng.uniform(0.0, 1.0)
        x0, y0 = rng.integers(0, size, 2)
        w, h = rng.integers(size // 6, size // 2, 2)
        img[y0:y0 + h, x0:x0 + w] = val
    # a couple of circles
    yy, xx = np.mgrid[0:size, 0:size]
    for _ in range(rng.integers(1, 3)):
        cx, cy = rng.integers(0, size, 2)
        r = rng.integers(size // 8, size // 4)
        img[(xx - cx) ** 2 + (yy - cy) ** 2 <= r * r] = rng.uniform(0.0, 1.0)
    return np.clip(img, 0.0, 1.0)


def make_dataset(n: int, size: int = 64, noise_sigma: float = 0.12, seed: int = 0):
    """Return (clean, noisy) float32 arrays of shape (n, size, size), deterministic."""
    rng = np.random.default_rng(seed)
    clean = np.stack([_one_image(rng, size) for _ in range(n)])
    noisy = np.clip(clean + rng.normal(0.0, noise_sigma, clean.shape), 0.0, 1.0)
    return clean.astype(np.float32), noisy.astype(np.float32)


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    """PSNR in dB for images in [0,1]. Higher is better."""
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    if mse <= 1e-12:
        return 99.0
    return float(10.0 * np.log10(1.0 / mse))


def mean_psnr_over(genome: np.ndarray, clean: np.ndarray, noisy: np.ndarray) -> float:
    """Mean PSNR after applying the pipeline to each noisy image vs its clean GT."""
    return float(np.mean([psnr(apply_genome(genome, noisy[i]), clean[i]) for i in range(len(clean))]))
