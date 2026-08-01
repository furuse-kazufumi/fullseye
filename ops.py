"""imgevolve — typed image-op DSL, genome apply, PSNR/metrics helpers.

The genome the search optimises is a fixed-length float vector in [0,1]^GENOME_LEN:
N_SLOTS pipeline stages, each decoded to (op, a, b). Decoding is deterministic, so
the same genome always yields the same pipeline (r2 bit-identical discipline). Every
op is a pure image->image map — that is what makes the pipeline verifiable and, in
S2, emittable to Python/C (see codegen.py).

Enriched op set (S4/A): smoothing (gaussian/median/uniform/bilateral), tone (gamma/
sharpen), edges (sobel_mag), and segmentation (threshold/otsu/morph). Different
problems (denoise/edge/binarize) reward different ops — the DSL is shared.

stdlib + numpy + scipy.ndimage only.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage


def _identity(img, a, b):
    return img


def _gaussian(img, a, b):
    return ndimage.gaussian_filter(img, sigma=0.3 + 2.7 * a)  # sigma in [0.3,3]


def _median(img, a, b):
    return ndimage.median_filter(img, size=(3, 5, 7)[min(2, int(a * 3))])


def _uniform(img, a, b):
    return ndimage.uniform_filter(img, size=3 + 2 * int(a * 3))  # {3,5,7}


def _gamma(img, a, b):
    return np.clip(img, 0.0, 1.0) ** (0.5 + 1.5 * a)  # [0.5,2]


def _sharpen(img, a, b):
    blur = ndimage.gaussian_filter(img, sigma=0.5 + 1.5 * b)
    return img + (1.5 * a) * (img - blur)  # unsharp mask


def _bilateral(img, a, b):
    """Edge-preserving smoothing (small-window, wrap-padded approximation)."""
    ss = 1.0 + 3.0 * a          # spatial sigma
    sr = 0.05 + 0.4 * b         # range sigma
    r = 2
    out = np.zeros_like(img, np.float64)
    wsum = np.zeros_like(img, np.float64)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            sh = np.roll(np.roll(img, dy, 0), dx, 1)
            w = np.exp(-(dx * dx + dy * dy) / (2 * ss * ss)) * np.exp(-((sh - img) ** 2) / (2 * sr * sr))
            out += w * sh
            wsum += w
    return out / np.maximum(wsum, 1e-8)


def _sobel_mag(img, a, b):
    gx = ndimage.sobel(img, axis=1)
    gy = ndimage.sobel(img, axis=0)
    m = np.hypot(gx, gy)
    mx = float(m.max())
    return m / mx if mx > 1e-8 else m


def _threshold(img, a, b):
    return (img > a).astype(np.float64)  # a is the level


def _otsu(img, a, b):
    x = np.clip(img, 0.0, 1.0)
    hist, edges = np.histogram(x, bins=256, range=(0.0, 1.0))
    p = hist.astype(np.float64) / max(1, hist.sum())
    omega = np.cumsum(p)
    mids = (edges[:-1] + edges[1:]) / 2
    mu = np.cumsum(p * mids)
    mu_t = mu[-1]
    denom = omega * (1 - omega)
    sigma_b = np.where(denom > 1e-12, (mu_t * omega - mu) ** 2 / np.maximum(denom, 1e-12), 0.0)
    t = mids[int(np.argmax(sigma_b))]
    return (x > t).astype(np.float64)


def _morph_open(img, a, b):
    k = 3 + 2 * int(a * 3)  # {3,5,7}
    return ndimage.grey_opening(img, size=k)


def _morph_close(img, a, b):
    k = 3 + 2 * int(a * 3)
    return ndimage.grey_closing(img, size=k)


OPS: tuple = (
    ("identity", _identity),
    ("gaussian", _gaussian),
    ("median", _median),
    ("uniform", _uniform),
    ("gamma", _gamma),
    ("sharpen", _sharpen),
    ("bilateral", _bilateral),
    ("sobel_mag", _sobel_mag),
    ("threshold", _threshold),
    ("otsu", _otsu),
    ("morph_open", _morph_open),
    ("morph_close", _morph_close),
)
N_OPS = len(OPS)
N_SLOTS = 5
GENOME_LEN = N_SLOTS * 3
_FNS = {name: fn for name, fn in OPS}


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
        out.append(Stage(OPS[min(N_OPS - 1, int(t * N_OPS))][0], float(a), float(b)))
    return out


def apply_genome(genome, img) -> np.ndarray:
    out = img.astype(np.float64)
    for st in decode(genome):
        out = _FNS[st.op](out, st.a, st.b)
    return np.clip(out, 0.0, 1.0)


def pipeline_str(genome) -> str:
    parts = [f"{s.op}(a={s.a:.2f},b={s.b:.2f})" for s in decode(genome) if s.op != "identity"]
    return " -> ".join(parts) if parts else "identity"


def psnr(a, b) -> float:
    mse = float(np.mean((np.asarray(a, np.float64) - np.asarray(b, np.float64)) ** 2))
    return 99.0 if mse <= 1e-12 else float(10.0 * np.log10(1.0 / mse))
