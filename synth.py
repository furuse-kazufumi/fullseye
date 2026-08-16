"""synth.py — learn an image's features and synthesise NEW, similar images.

A classical (numpy/scipy, **no learned model / no NN**) texture-synthesis facade:
extract a compact statistical *signature* of an exemplar and generate fresh images
that share it. Two complementary methods, both from public literature:

  method="spectral" (default) — Heeger & Bergen 1995 style, power-spectrum + marginal.
      Iterate: impose the exemplar's Fourier AMPLITUDE spectrum on random-phase noise
      (matches 2nd-order structure: roughness, directionality, spectral slope), then
      match the marginal intensity histogram. Randomised phase ⇒ a genuinely new
      image with the same 2nd-order + marginal statistics. Fast and fully
      reproducible. Best for stochastic textures (noise, grain, sand, cloud, fabric
      weave without rigid structure). Honest edge case: a DEGENERATE exemplar — a
      constant image, or a single pure frequency — has an amplitude spectrum with no
      broadband content, so random phase cannot add structure and the output can
      coincide with (a shift of) the source. That is correct, not a leak: there is
      essentially only one image with that spectrum and histogram. Check with
      :func:`patch_novelty` when it matters.

  method="patch" — Efros & Freeman 2001 image quilting (min-cut seams).
      Grow the output from overlapping exemplar blocks chosen to match already-placed
      neighbours, stitched along a minimum-error seam. Reproduces STRUCTURED textures
      (brick, tile, cellular) an amplitude spectrum cannot. Non-parametric: it copies
      and stitches real patches, so novelty is measured, not assumed.

**Honest scope.** This matches STATISTICS (marginal + 2nd-order spectrum, or local
patch statistics), not SEMANTICS. It makes "more of the same material/texture"; it
does NOT reproduce a scene, an object, or a labelled part. On a non-stationary image
(a face, a diagram) the spectral method returns same-spectrum noise, not the content.
Verify with :func:`feature_distance` (does it match the exemplar's stats?) and
:func:`patch_novelty` (is it actually new, not a copy?).

Widens applications: license-clean synthetic data / augmentation, procedural texture,
and generating the library's own sample images (dogfooding apply/pipeline/save).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = [
    "feature_distance",
    "learn_features",
    "match_histogram",
    "patch_novelty",
    "radial_power_spectrum",
    "synthesize_like",
]


def _gray01(img) -> np.ndarray:
    a = np.asarray(img, np.float64)
    if a.ndim == 3:
        a = a.mean(axis=2)                     # simple luma-free gray (RGB mean)
    if a.ndim != 2:
        raise ValueError(f"synth expects a 2-D (or H,W,3) image, got {a.ndim}D")
    return a


# --------------------------------------------------------------------------- #
# feature extraction ("learning" the signature)
# --------------------------------------------------------------------------- #
def radial_power_spectrum(img, nbins: int | None = None):
    """Rotationally-averaged power spectrum: (freqs[0..0.5], power) per radial bin.

    The DC term is removed (mean-subtracted) so the curve describes structure, not
    brightness. This is the isotropic 2nd-order signature — spectral slope encodes
    roughness; a peak encodes a dominant scale/period.
    """
    a = _gray01(img)
    a = a - a.mean()
    F = np.fft.fftshift(np.fft.fft2(a))
    P = (F.real ** 2 + F.imag ** 2)
    h, w = a.shape
    cy, cx = h // 2, w // 2
    y, x = np.ogrid[:h, :w]
    r = np.hypot(y - cy, x - cx)
    rmax = float(r.max()) if r.size else 0.0
    nb = nbins or (int(rmax) + 1)
    nb = max(2, nb)
    rb = np.zeros_like(r, dtype=np.int64) if rmax <= 0 else (r / rmax * (nb - 1)).astype(np.int64)
    power = np.bincount(rb.ravel(), P.ravel(), minlength=nb)[:nb]
    count = np.bincount(rb.ravel(), minlength=nb)[:nb]
    power = power / np.maximum(count, 1)
    # cycles/pixel: a radius of N/2 (Nyquist along the short axis) is 0.5; the
    # diagonal corner is ~0.707. (Earlier this wrongly pinned 0.5 to the diagonal,
    # compressing every reported frequency by ~1/sqrt(2).) Non-square is approximate.
    ref = float(max(1, min(h, w)))
    freqs = np.linspace(0.0, rmax, nb) / ref
    return freqs, power


def learn_features(img) -> dict:
    """A compact statistical signature of *img* (the "learned" features).

    ``histogram`` (256-bin marginal, normalised), ``radial_freqs``/``radial_power``
    (2nd-order spectrum), plus ``mean``/``std``/``shape``. Deterministic.
    """
    a = _gray01(img)
    hist, _ = np.histogram(a, bins=256, range=(0.0, 1.0))
    total = hist.sum()
    hist = hist.astype(np.float64) / (total if total else 1.0)
    freqs, power = radial_power_spectrum(a)
    return {"shape": a.shape, "mean": float(a.mean()), "std": float(a.std()),
            "histogram": hist, "radial_freqs": freqs, "radial_power": power}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def match_histogram(src, ref) -> np.ndarray:
    """Map *src* so its intensity distribution follows *ref*'s (rank-based).

    Each source pixel is sent, by its quantile, to an ACTUAL sorted reference value
    (nearest-rank) — never an interpolated in-between value. So the output only ever
    contains values that exist in ``ref`` (important for discrete/low-level
    exemplars). The match is EXACT when the two have the same number of pixels; for
    different sizes it is the closest rank (an exact multiset match is impossible
    when a value's count cannot be split).
    """
    s = np.asarray(src, np.float64)
    r = np.sort(_gray01(ref).ravel())
    if r.size == 0:
        return s
    flat = s.ravel()
    order = np.argsort(flat, kind="stable")
    ranks = np.empty(flat.size, np.float64)
    ranks[order] = np.arange(flat.size, dtype=np.float64)
    q = ranks / max(1, flat.size - 1)                       # each pixel's quantile in [0,1]
    idx = np.clip(np.rint(q * (r.size - 1)).astype(np.int64), 0, r.size - 1)
    matched = r[idx]                                        # always a real reference value
    return matched.reshape(s.shape)


def _resample_amplitude(amp: np.ndarray, shape) -> np.ndarray:
    """Resample an (unshifted) FFT amplitude spectrum to a new shape (approximate).

    Only used when the requested output size differs from the exemplar: the centred
    magnitude is zoomed to the target grid so the spectral SHAPE is preserved.
    """
    if amp.shape == tuple(shape):
        return amp
    centred = np.fft.fftshift(amp)
    zoom = (shape[0] / amp.shape[0], shape[1] / amp.shape[1])
    resized = ndimage.zoom(centred, zoom, order=1)
    # zoom can be off by a pixel; crop/pad to exact shape
    out = np.zeros(tuple(shape), np.float64)
    h = min(shape[0], resized.shape[0])
    w = min(shape[1], resized.shape[1])
    out[:h, :w] = resized[:h, :w]
    return np.fft.ifftshift(out)


# --------------------------------------------------------------------------- #
# synthesis
# --------------------------------------------------------------------------- #
def _synth_spectral(img: np.ndarray, shape, seed: int, iters: int) -> np.ndarray:
    amp = np.abs(np.fft.fft2(img))
    amp = _resample_amplitude(amp, shape)
    rng = np.random.default_rng(seed)
    out = rng.standard_normal(tuple(shape))
    for _ in range(max(1, iters)):
        F = np.fft.fft2(out)
        phase = np.angle(F)                                # keep the noise's phase (novelty)
        out = np.real(np.fft.ifft2(amp * np.exp(1j * phase)))   # impose exemplar amplitude
        out = match_histogram(out, img)                    # impose exemplar marginal
    return np.clip(out, 0.0, 1.0)


def _min_cut_mask(err: np.ndarray, axis: int) -> np.ndarray:
    """Boolean mask (True = take the NEW block) for a minimum-error seam through the
    overlap error surface ``err`` (Efros-Freeman). ``axis``: 0 = vertical seam in a
    left/right overlap, 1 = horizontal seam in a top/bottom overlap."""
    e = err if axis == 0 else err.T
    h, w = e.shape
    cost = e.copy()
    back = np.zeros((h, w), np.int64)
    for i in range(1, h):
        for j in range(w):
            lo, hi = max(0, j - 1), min(w, j + 2)
            k = lo + int(np.argmin(cost[i - 1, lo:hi]))
            back[i, j] = k
            cost[i, j] += cost[i - 1, k]
    seam = np.zeros(h, np.int64)
    seam[-1] = int(np.argmin(cost[-1]))
    for i in range(h - 2, -1, -1):
        seam[i] = back[i + 1, seam[i + 1]]
    mask = np.zeros((h, w), bool)               # True where we KEEP the new block
    for i in range(h):
        mask[i, seam[i]:] = True
    return mask if axis == 0 else mask.T


def _synth_patch(img: np.ndarray, shape, seed: int, block: int, overlap: int,
                 tol: float, max_candidates: int) -> np.ndarray:
    h, w = img.shape
    block = int(min(block, h, w))
    block = max(4, block)
    overlap = int(min(max(1, overlap), block - 1))
    rng = np.random.default_rng(seed)
    step = block - overlap
    H, W = shape
    out = np.zeros((H, W), np.float64)
    filled = np.zeros((H, W), bool)
    # candidate top-left corners in the exemplar. Full search is O(corners x
    # out-blocks) and hangs for large inputs, so cap to a random (seeded) subset —
    # the standard quilting speed-up (Efros-Freeman search a sampled pool).
    ys = list(range(h - block + 1)) or [0]
    xs = list(range(w - block + 1)) or [0]
    corners = [(yy, xx) for yy in ys for xx in xs]
    if max_candidates and len(corners) > max_candidates:
        sel = rng.choice(len(corners), size=max_candidates, replace=False)
        corners = [corners[int(i)] for i in sel]
    for oy in range(0, H, step):
        for ox in range(0, W, step):
            bh = min(block, H - oy)
            bw = min(block, W - ox)
            if bh <= 0 or bw <= 0:
                continue
            best = []
            for (cy, cx) in corners:
                patch = img[cy:cy + bh, cx:cx + bw]
                cost = 0.0
                if ox > 0:                       # left overlap
                    ov = min(overlap, bw)
                    a = out[oy:oy + bh, ox:ox + ov]
                    m = filled[oy:oy + bh, ox:ox + ov]
                    if m.any():
                        cost += float(np.sum((patch[:, :ov] - a)[m] ** 2))
                if oy > 0:                       # top overlap
                    ov = min(overlap, bh)
                    a = out[oy:oy + ov, ox:ox + bw]
                    m = filled[oy:oy + ov, ox:ox + bw]
                    if m.any():
                        cost += float(np.sum((patch[:ov, :] - a)[m] ** 2))
                best.append((cost, cy, cx))
            best.sort(key=lambda t: t[0])
            cutoff = best[0][0] * (1.0 + tol) + 1e-12
            pool = [b for b in best if b[0] <= cutoff] or best[:1]
            _, cy, cx = pool[int(rng.integers(len(pool)))]
            patch = img[cy:cy + bh, cx:cx + bw].copy()
            take = np.ones((bh, bw), bool)
            if ox > 0:
                ov = min(overlap, bw)
                m = filled[oy:oy + bh, ox:ox + ov]
                if m.any():
                    err = (patch[:, :ov] - out[oy:oy + bh, ox:ox + ov]) ** 2
                    keep = _min_cut_mask(err, axis=0)
                    take[:, :ov] = keep | (~m)
            if oy > 0:
                ov = min(overlap, bh)
                m = filled[oy:oy + ov, ox:ox + bw]
                if m.any():
                    err = (patch[:ov, :] - out[oy:oy + ov, ox:ox + bw]) ** 2
                    keep = _min_cut_mask(err, axis=1)
                    take[:ov, :] = take[:ov, :] & (keep | (~m))
            reg = out[oy:oy + bh, ox:ox + bw]
            reg[take] = patch[take]
            filled[oy:oy + bh, ox:ox + bw] = True
    return np.clip(out, 0.0, 1.0)


def synthesize_like(img, size=None, seed: int = 0, method: str = "spectral",
                    iters: int = 6, block: int = 32, overlap: int = 8, tol: float = 0.1,
                    max_candidates: int = 400, levels: int = 4) -> np.ndarray:
    """Generate a NEW image sharing *img*'s texture (gray, float64 in [0,1]).

    ``size`` = (H, W) output shape (default: the exemplar's). ``method`` = ``spectral``
    (single-band power-spectrum + histogram), ``pyramid`` (multi-scale Heeger-Bergen:
    per-scale band histograms), or ``patch`` (image quilting). ``seed`` makes it
    deterministic. ``levels`` sets the pyramid depth for ``pyramid``. ``max_candidates``
    caps the quilting search (bounds the cost to ~out_blocks x max_candidates; 0 =
    search every exemplar block, which can be very slow on large inputs). See the module
    docstring for the honest scope.
    """
    a = _gray01(img)
    if not np.isfinite(a).all():
        raise ValueError("synth input contains non-finite values (NaN/inf); "
                         "clean the image before synthesising (fail-closed)")
    a = np.clip(a, 0.0, 1.0)
    shape = tuple(size) if size is not None else a.shape
    if len(shape) != 2 or shape[0] < 2 or shape[1] < 2:
        raise ValueError("size must be a 2-tuple (H, W) >= (2, 2)")
    if method == "spectral":
        return _synth_spectral(a, shape, seed, iters)
    if method == "pyramid":
        return _synth_pyramid(a, shape, seed, iters, levels)
    if method == "patch":
        return _synth_patch(a, shape, seed, block, overlap, tol, max_candidates)
    raise ValueError(f"unknown method {method!r} (use 'spectral', 'pyramid' or 'patch')")


# --------------------------------------------------------------------------- #
# honest verification
# --------------------------------------------------------------------------- #
def _norm(v: np.ndarray) -> np.ndarray:
    v = v - v.mean()
    s = v.std()
    return v / s if s > 1e-9 else v


def feature_distance(a, b) -> dict:
    """How close two images' learned features are (0 = identical statistics).

    ``hist_chi2`` (marginal), ``spectrum_l2`` (normalised log radial power),
    ``mean_diff``/``std_diff``. Use it to show a synthesis matched the exemplar.
    """
    fa, fb = learn_features(a), learn_features(b)
    ha, hb = fa["histogram"], fb["histogram"]
    chi2 = 0.5 * float(np.sum((ha - hb) ** 2 / (ha + hb + 1e-12)))
    pa = np.log(fa["radial_power"] + 1e-12)
    pb = np.log(fb["radial_power"] + 1e-12)
    n = min(len(pa), len(pb))
    spec = float(np.sqrt(np.mean((_norm(pa[:n]) - _norm(pb[:n])) ** 2))) if n else float("inf")
    return {"hist_chi2": chi2, "spectrum_l2": spec,
            "mean_diff": abs(fa["mean"] - fb["mean"]), "std_diff": abs(fa["std"] - fb["std"])}


def patch_novelty(synth, source, block: int = 16, n: int = 48, seed: int = 0,
                  max_source_blocks: int = 20000) -> float:
    """Mean nearest-patch distance from *synth* back to *source* (higher = more novel).

    Samples ``n`` random blocks of *synth* and, for each, finds the smallest
    **mean-squared** distance to a block of *source*. ~0 means large verbatim
    copying; a clearly positive value means the output is genuinely new, not a crop.

    Honest limits: (1) it is a raw pixel MSE, **not intensity-normalised** — a copy
    that was globally brightened/inverted still reads as "novel" (for synthesis
    outputs, which share the exemplar's histogram, verbatim copying is the relevant
    mode and is detected). (2) The source blocks are sampled on a stride so the
    working set stays bounded (``max_source_blocks``); on a huge image the estimate
    uses a strided subset rather than every pixel offset (so it never allocates GBs).
    """
    s = _gray01(synth)
    src = _gray01(source)
    b = int(min(block, s.shape[0], s.shape[1], src.shape[0], src.shape[1]))
    b = max(2, b)
    rng = np.random.default_rng(seed)
    ny, nx = src.shape[0] - b + 1, src.shape[1] - b + 1
    # stride the source-block grid so at most ~max_source_blocks are materialised
    stride = 1
    if max_source_blocks and (max(1, ny) * max(1, nx)) > max_source_blocks:
        stride = max(1, int(np.ceil(np.sqrt(max(1, ny) * max(1, nx) / max_source_blocks))))
    sy = list(range(0, ny, stride)) or [0]
    sx = list(range(0, nx, stride)) or [0]
    src_blocks = np.stack([src[y:y + b, x:x + b] for y in sy for x in sx]).reshape(len(sy) * len(sx), -1)
    dists = []
    for _ in range(n):
        oy = int(rng.integers(0, max(1, s.shape[0] - b + 1)))
        ox = int(rng.integers(0, max(1, s.shape[1] - b + 1)))
        q = s[oy:oy + b, ox:ox + b].ravel()
        d = np.mean((src_blocks - q) ** 2, axis=1)
        dists.append(float(d.min()))
    return float(np.mean(dists)) if dists else 0.0
