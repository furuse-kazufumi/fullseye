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
    if isinstance(final, np.ndarray) and final.ndim in (2, 3):
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
    in_sort: str = "image"  # pipeline start sort (image | volume | ...)

    def score(self, genome, data) -> float:
        inp, items = data["input"], data["items"]
        return float(np.mean([self.score_value(ops.run_genome(genome, inp[i], self.in_sort), items[i])
                              for i in range(len(inp))]))

    def score_stages(self, stages, data) -> float:
        inp, items = data["input"], data["items"]
        return float(np.mean([self.score_value(ops.run_stages(stages, inp[i]), items[i]) for i in range(len(inp))]))

    @classmethod
    def from_pairs(cls, inputs, targets, name="pairs", metric=None, unit=None,
                   in_sort="image", hand_stages=None) -> "Problem":
        """Build a Problem from explicit ``(input, target)`` arrays.

        This is the real-data counterpart to the synthetic ``_synth`` generator:
        drop in captured frames (``inputs``) and their desired outputs (``targets``)
        and evolution optimizes against them exactly like a built-in PROBLEM. Purely
        additive — it does not touch ``PROBLEMS`` or ``_synth``.

        Parameters
        ----------
        inputs, targets : array-likes of equal length; ``inputs[i]`` pairs with
            ``targets[i]``. Targets may be images (H x W) or scalars (counts).
        metric : ``(final_value, target) -> float`` (higher better). Defaults to
            PSNR when the target is a 2-D image, else ``1/(1+|count_err|)``.
        unit : label for reporting (defaults to a metric-appropriate string).
        in_sort : pipeline start sort (``"image"`` | ``"volume"`` | ...).
        hand_stages : optional ``() -> list`` baseline; defaults to trivial (identity).

        ``make(n, size, seed)`` returns a deterministic ``n``-item subset via a
        seed-dependent rotation over the pool, so evolve.run's train (seed) and
        holdout (seed+10000) splits draw different orderings. For a genuinely
        disjoint holdout, provide enough distinct pairs (an honest caveat: a tiny
        pool cannot yield a clean holdout).
        """
        inp = np.asarray(inputs, np.float64)
        tgt = np.asarray(targets)
        if inp.shape[0] == 0 or tgt.shape[0] == 0:
            raise ValueError("from_pairs needs at least one (input, target) pair")
        if inp.shape[0] != tgt.shape[0]:
            raise ValueError(f"inputs ({inp.shape[0]}) and targets ({tgt.shape[0]}) "
                             "must have equal length")

        def _default_metric(final, target):
            if np.ndim(target) == 2:                      # image / region target
                return ops.psnr(_as_image(final, np.shape(target)), target)
            return 1.0 / (1.0 + abs(_as_count(final) - float(np.asarray(target).ravel()[0])))

        m = metric or _default_metric
        if unit is None:
            unit = "dB PSNR" if tgt.ndim == 3 else "score"

        def _make(n, size, seed, _inp=inp, _tgt=tgt):
            pool = _inp.shape[0]
            n = int(n)
            # ★A deterministic global shuffle (fixed base, so train/holdout/locked
            # index the SAME permutation) split into three DISJOINT bands keyed by
            # the seed's role (evolve.run draws train=seed, holdout=seed+10000,
            # locked=seed+20000, so seed//10000 mod 3 picks the band).  The old
            # `off = seed % pool` collapsed all three windows to the SAME frames
            # whenever pool divided 10000 — a silent train↔holdout↔locked leak that
            # made a train-overfit champion look like it "beat hand on a pure
            # holdout".  A pure 3-way split needs pool >= 3n; a smaller pool cannot
            # yield a clean holdout, so we refuse rather than leak silently.
            third = pool // 3
            perm = np.random.default_rng(0xC0FFEE).permutation(pool)
            band = (int(seed) // 10000) % 3          # 0=train,1=holdout,2=locked
            if third >= n:
                idx = perm[band * third:band * third + n]      # fully disjoint splits
            else:
                # pool too small for a pure 3-way split — a tiny pool cannot yield an
                # untouched holdout.  Best effort: give each split a DISTINCT band
                # offset so holdout/locked are no longer IDENTICAL to train (the old
                # `off = seed % pool` collapsed all three to the same frames whenever
                # pool divided 10000).  Overlap is now partial and disclosed, not a
                # silent total leak.  A pure holdout needs pool >= 3*n.
                import warnings
                warnings.warn(
                    f"from_pairs pool={pool} < 3*n={3 * n}: train/holdout/locked "
                    f"cannot be fully disjoint; splits overlap partially (holdout is "
                    f"not pure). Supply >= {3 * n} frames for a clean split.",
                    stacklevel=2)
                start = (band * max(1, third)) % pool
                idx = perm[[(start + i) % pool for i in range(n)]]
            return {"input": _inp[idx], "items": _tgt[idx]}

        return cls(name=name, unit=unit, make=_make, score_value=m,
                   hand_stages=(hand_stages or (lambda: [])), in_sort=in_sort)


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


# --- locate_rot (shape-based, rotation invariant) ---------------------------- #
def _template_L(size=11):
    t = np.zeros((size, size), np.float64); t[2:size - 2, 2:4] = 1.0; t[size - 4:size - 2, 2:size - 2] = 1.0
    return t


def _make_locate_rot(n, size, seed):
    rng = np.random.default_rng(seed + 8)
    T = _template_L(11); ops.set_match_template(T); rr = T.shape[0] // 2
    imgs, locs = [], []
    for _ in range(n):
        base = _synth(rng, size) * 0.4
        tr = ndimage.rotate(T, rng.uniform(0, 360), reshape=False)
        r = int(rng.integers(rr + 1, size - rr - 1)); c = int(rng.integers(rr + 1, size - rr - 1))
        base[r - rr:r + rr + 1, c - rr:c + rr + 1] = np.maximum(base[r - rr:r + rr + 1, c - rr:c + rr + 1], tr)
        imgs.append(np.clip(base + rng.normal(0, 0.1, base.shape), 0, 1)); locs.append([float(r), float(c)])
    return {"input": np.stack(imgs), "items": np.array(locs)}


# --- classify (round vs elongated; OCR/decision basis) ----------------------- #
def _make_classify(n, size, seed):
    rng = np.random.default_rng(seed + 6); imgs, labels = [], []
    for _ in range(n):
        img = np.full((size, size), 0.15, np.float64)
        cx, cy = rng.integers(size // 3, 2 * size // 3, 2)
        if rng.random() < 0.5:  # circle
            r = int(rng.integers(size // 6, size // 4)); yy, xx = np.mgrid[0:size, 0:size]
            img[(xx - cx) ** 2 + (yy - cy) ** 2 <= r * r] = 0.9; lab = 1.0
        else:                    # elongated rectangle
            h = int(rng.integers(size // 6, size // 4)); w = max(2, h // 4)
            if rng.random() < 0.5:
                w, h = h, w
            img[max(0, cy - h // 2):cy + h // 2, max(0, cx - w // 2):cx + w // 2] = 0.9; lab = 0.0
        imgs.append(np.clip(img + rng.normal(0, 0.08, img.shape), 0, 1)); labels.append(lab)
    return {"input": np.stack(imgs), "items": np.array(labels)}


def _score_classify(final, gt):
    if _is_img(final):
        circ = 0.5
    elif isinstance(final, dict):
        return 0.0
    else:
        try:
            circ = float(np.asarray(final, np.float64).ravel()[0])
        except Exception:
            return 0.0
    return 1.0 if (1.0 if circ > 0.8 else 0.0) == gt else 0.0


# --- barcode-lite (count vertical bars) -------------------------------------- #
def _make_barcode(n, size, seed):
    rng = np.random.default_rng(seed + 7); imgs, counts = [], []
    for _ in range(n):
        img = np.full((size, size), 0.85, np.float64)
        nb = int(rng.integers(2, 8))
        xs = sorted(rng.choice(range(4, size - 4, 3), size=nb, replace=False))
        for x in xs:
            img[:, x:x + int(rng.integers(1, 3))] = 0.1
        imgs.append(np.clip(img + rng.normal(0, 0.05, img.shape), 0, 1)); counts.append(float(nb))
    return {"input": np.stack(imgs), "items": np.array(counts)}


# --- 3D volumes (CT/MRI-like voxel blobs) ------------------------------------ #
def _vol_stack(n, size, seed):
    rng = np.random.default_rng(seed)
    vols = []
    for _ in range(n):
        vol = np.zeros((size, size, size), np.float64)
        zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
        for _ in range(rng.integers(2, 5)):
            cz, cy, cx = rng.integers(0, size, 3); r = rng.integers(size // 8, size // 4)
            vol[(xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2 <= r * r] = rng.uniform(0.5, 1.0)
        vols.append(vol)
    return np.stack(vols)


def _make_vol_denoise(n, size, seed, noise=0.15):
    clean = _vol_stack(n, 24, seed)
    noisy = np.clip(clean + np.random.default_rng(seed + 1).normal(0, noise, clean.shape), 0, 1)
    return {"input": noisy, "items": clean}


def _make_vol_count(n, size, seed, noise=0.1):
    clean = _vol_stack(n, 24, seed)
    inp = np.clip(clean + np.random.default_rng(seed + 2).normal(0, noise, clean.shape), 0, 1)
    counts = np.array([float(ndimage.label(c > 0.5)[1]) for c in clean])
    return {"input": inp, "items": counts}


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
    "locate_rot": Problem("locate_rot", "1/(1+px)", _make_locate_rot, _score_locate,
                          lambda: [ops.stage("gaussian", 0.2, 0.0), ops.stage("shape_locate", 0.0, 0.0)]),
    "classify": Problem("classify", "accuracy", _make_classify, _score_classify,
                        lambda: [ops.stage("gaussian", 0.2, 0.0), ops.stage("otsu", 0.0, 0.0),
                                 ops.stage("select_largest", 0.0, 0.0), ops.stage("classify_shape", 0.0, 0.0)]),
    "barcode": Problem("barcode", "1/(1+err)", _make_barcode,
                       lambda f, gt: 1.0 / (1.0 + abs(_as_count(f) - gt)),
                       lambda: [ops.stage("decode_barcode", 0.5, 0.0)]),
    "vol_denoise": Problem("vol_denoise", "dB PSNR", _make_vol_denoise,
                           lambda f, tgt: ops.psnr(np.clip(f, 0, 1), tgt)
                           if isinstance(f, np.ndarray) and f.ndim == 3 else 0.0,
                           lambda: [ops.stage("vol_gaussian", 0.26, 0.0)], in_sort="volume"),
    "vol_count": Problem("vol_count", "1/(1+err)", _make_vol_count,
                         lambda f, gt: 1.0 / (1.0 + abs(_as_count(f) - gt)),
                         lambda: [ops.stage("vol_gaussian", 0.3, 0.0), ops.stage("vol_threshold", 0.4, 0.0),
                                  ops.stage("vol_count", 0.0, 0.0)], in_sort="volume"),
}


def trivial_stages() -> list:
    return []
