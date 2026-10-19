# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""anomaly_patch — patch-feature anomaly detection from good samples only (classical features, no learned network).

The family of methods that dominates visual-inspection research learns what *good* looks like
from a handful of good images and scores every patch of a test image by how far its feature is
from the good ones. The usual features come from a pretrained deep network; here they are
**classical, interpretable and deterministic**: multi-resolution gradient (structure-tensor)
channels, Gabor energies, rotation-invariant uniform local binary patterns, local spectral
bands and colour. Two scorers are built on them and share one yard-stick (``anomeval``):

  * :func:`patchdist_fit` / :func:`patchdist_score` — **a normal distribution per position**
    (a multivariate Gaussian of the patch feature at every grid cell; Mahalanobis distance).
    The covariance is estimated from n good images, so for n <= D (D = feature dimension) it is
    singular: the shrinkage toward ``tr(S)/D * I`` is therefore *declared* (``shrinkage="auto"``
    is the Ledoit–Wolf analytic intensity, a number in [0, 1] fixes it) and reported in the
    model; ``shrinkage="none"`` is only accepted when the covariance is full rank and is
    otherwise refused with a ``ValueError``.
  * :func:`patchbank_fit` / :func:`patchbank_score` — **a memory bank of good patch features**
    and the distance to the k nearest ones (exact, brute force). The bank is thinned by greedy
    k-centre covering (``coreset``), the covering radius is reported, and ``position_weight``
    appends the grid position to the feature so that a patch is compared with good patches from
    *where it should be*.

The feature stage is a separate op, :func:`patch_features`, so the features can be inspected and
reused. Everything is deterministic: random choices (the covering start, the random
projection, the random subset of dimensions) take an explicit ``seed``.

Assumptions (stated): good samples share a distribution per position (the Gaussian scorer) or
are covered by a modest number of patch prototypes (the bank). A stack that mixes defective
images into the good set weakens both; the bank is the more tolerant one, the Gaussian the more
data-efficient one.

References (published literature only): T. Defard et al., ICPR Workshops 2020 (a Gaussian per
position, Mahalanobis); K. Roth et al., CVPR 2022 (a memory bank of patch features and a
greedy coreset); O. Sener, S. Savarese, ICLR 2018 (k-centre greedy); O. Ledoit, M. Wolf,
J. Multivar. Anal. 88:365, 2004 (the analytic shrinkage intensity); T. Ojala et al., IEEE TPAMI
24:971, 2002 (rotation-invariant uniform local binary patterns); J. G. Daugman, JOSA A 2:1160,
1985 (Gabor).
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["patch_features", "patchdist_fit", "patchdist_score", "patchbank_fit",
           "patchbank_score", "FEATURE_GROUPS"]

#: feature groups: mean intensity / structure tensor / Gabor energy / rotation-invariant uniform LBP
#: histogram / local spectral bands of the patch / colour opponents (needs an (H, W, 3) image).
FEATURE_GROUPS = ("intensity", "gradient", "gabor", "lbp", "fourier", "color")

_MAX_VALUES = 1 << 27                  # memory guard for one call
_MAX_FEATURES = 1 << 26                # stored model feature values
_EPS = 1e-12
_LBP_BINS = 10
_FOURIER_BANDS = 3


# ----------------------------------------------------------------------------- validation
def _int(v, name, op, lo, hi):
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    if isinstance(v, (float, np.floating)) and math.isfinite(float(v)) and float(v) == int(v):
        v = int(v)
    if not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    v = int(v)
    if not lo <= v <= hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, v))
    return v


def _num(v, name, op, lo, hi, lo_open=False):
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v)) from None
    if isinstance(v, (bool, np.bool_)) or not math.isfinite(f) or f > hi or f < lo or (lo_open and f == lo):
        raise ValueError("%s: %s must be in %s%g, %g], got %r" % (op, name, "(" if lo_open else "[", lo, hi, v))
    return f


def _spec(patch, stride, scales, groups, n_orient, op):
    patch = _int(patch, "patch", op, 2, 64)
    stride = _int(stride, "stride", op, 1, patch)
    if isinstance(scales, (int, float, np.integer, np.floating)):
        scales = (scales,)
    sc = tuple(_num(s, "scales", op, 0.5, 16.0) for s in scales)
    if len(sc) == 0 or len(set(sc)) != len(sc):
        raise ValueError("%s: scales must be a non-empty list of distinct sigmas (px), got %r" % (op, scales))
    if isinstance(groups, str):
        groups = (groups,)
    gr = tuple(groups)
    bad = [g for g in gr if g not in FEATURE_GROUPS]
    if len(gr) == 0 or bad or len(set(gr)) != len(gr):
        raise ValueError("%s: groups must be a non-empty subset of %s, got %r" % (op, FEATURE_GROUPS, groups))
    return {"patch": patch, "stride": stride, "scales": sc, "groups": gr,
            "n_orient": _int(n_orient, "n_orient", op, 1, 16)}


def _images(x, name, op, min_n=1):
    """(n, H, W) gray or (n, H, W, 3) colour, finite float64."""
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            raise ValueError("%s: %s is empty (0 images)" % (op, name))
        arrs = [np.asarray(a, dtype=np.float64) for a in x]
        if len({a.shape for a in arrs}) != 1:
            raise ValueError("%s: images in %s differ in shape: %s" % (op, name, sorted({a.shape for a in arrs})))
        a = np.stack(arrs, axis=0)
    else:
        a = np.asarray(x, dtype=np.float64)
    if a.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if a.ndim == 2:
        a = a[None]
    if a.ndim not in (3, 4) or (a.ndim == 4 and a.shape[-1] != 3):
        raise ValueError("%s: %s must be (n, H, W) or (n, H, W, 3), got shape %s" % (op, name, a.shape))
    if a.size > _MAX_VALUES:
        raise ValueError("%s: %s has %d values (> %d); downsample first" % (op, name, a.size, _MAX_VALUES))
    if a.shape[0] < min_n:
        raise ValueError("%s: %s needs at least %d images, got %d" % (op, name, min_n, a.shape[0]))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s contains non-finite values" % (op, name))
    return a


def _one(x, name, op):
    a = np.asarray(x, dtype=np.float64)
    if a.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if a.ndim == 2 or (a.ndim == 3 and a.shape[-1] == 3):
        if not np.isfinite(a).all():
            raise ValueError("%s: %s contains non-finite values" % (op, name))
        return a
    raise ValueError("%s: %s must be a 2-D image or (H, W, 3), got shape %s" % (op, name, a.shape))


# ----------------------------------------------------------------------------- pixel channels
def _gray(img):
    return img if img.ndim == 2 else img @ np.array([0.299, 0.587, 0.114])


def _gabor_kernel(scale, theta):
    """Zero-mean complex Gabor: wavelength 4*scale px, envelope sigma 0.56*wavelength."""
    lam = 4.0 * scale
    se = 0.56 * lam
    half = int(math.ceil(3.0 * se))
    yy, xx = np.mgrid[-half:half + 1, -half:half + 1].astype(np.float64)
    env = np.exp(-(xx * xx + yy * yy) / (2.0 * se * se))
    u = xx * math.cos(theta) + yy * math.sin(theta)
    g = env * np.exp(2j * math.pi * u / lam)
    g -= env * (g.sum() / env.sum())
    return g, half


def _gabor_energy(gray, scale, k, n_orient):
    from scipy.signal import fftconvolve        # noqa: PLC0415
    g, half = _gabor_kernel(scale, math.pi * k / n_orient)
    lim = min(gray.shape) - 1
    if half > lim:                              # kernel larger than the image: crop its support
        c = half
        g = g[c - lim:c + lim + 1, c - lim:c + lim + 1]
        half = lim
    pad = np.pad(gray, half, mode="reflect")
    return np.abs(fftconvolve(pad, g, mode="valid"))


def _lbp_riu2(sm, r):
    """Rotation-invariant uniform LBP code (0..9) with 8 compass neighbours at integer radius r."""
    h, w = sm.shape
    r = min(max(1, int(r)), min(h, w) - 1)
    pad = np.pad(sm, r, mode="reflect")
    bits = []
    for a in range(8):
        dy = int(round(-r * math.sin(2.0 * math.pi * a / 8.0)))
        dx = int(round(r * math.cos(2.0 * math.pi * a / 8.0)))
        bits.append(pad[r + dy:r + dy + h, r + dx:r + dx + w] >= sm)
    b = np.stack(bits).astype(np.int8)
    trans = sum((b[a] != b[(a + 1) % 8]).astype(np.int8) for a in range(8))
    return np.where(trans <= 2, b.sum(axis=0), 9)


def _pixel_channels(img, spec):
    from scipy import ndimage as ndi            # noqa: PLC0415
    gray = _gray(img)
    chans, names = [], []
    for s in spec["scales"]:
        tag = "s%g" % s
        if "intensity" in spec["groups"]:
            chans.append(ndi.gaussian_filter(gray, s, mode="reflect"))
            names.append("mean_" + tag)
        if "gradient" in spec["groups"]:
            gx = ndi.gaussian_filter(gray, s, order=(0, 1), mode="reflect")
            gy = ndi.gaussian_filter(gray, s, order=(1, 0), mode="reflect")
            mag = np.hypot(gx, gy)
            den = mag + _EPS
            chans += [mag, (gx * gx - gy * gy) / den, 2.0 * gx * gy / den]
            names += ["grad_mag_" + tag, "grad_c2_" + tag, "grad_s2_" + tag]
        if "gabor" in spec["groups"]:
            for k in range(spec["n_orient"]):
                chans.append(_gabor_energy(gray, s, k, spec["n_orient"]))
                names.append("gabor%d_%s" % (k, tag))
        if "lbp" in spec["groups"]:
            code = _lbp_riu2(ndi.gaussian_filter(gray, 0.5 * s, mode="reflect") if s > 1.0 else gray,
                             int(round(s)))
            for c in range(_LBP_BINS):
                chans.append((code == c).astype(np.float64))
                names.append("lbp%d_%s" % (c, tag))
        if "color" in spec["groups"]:
            if img.ndim != 3:
                raise ValueError("patch_features: group 'color' needs an (H, W, 3) image")
            sm = np.stack([ndi.gaussian_filter(img[..., c], s, mode="reflect") for c in range(3)], axis=-1)
            chans += [sm[..., 0] - sm[..., 1], 0.5 * (sm[..., 0] + sm[..., 1]) - sm[..., 2]]
            names += ["opp_rg_" + tag, "opp_yb_" + tag]
    return chans, names


def _pool(chans, patch, stride):
    """Box mean of every channel over patch x patch windows at the given stride -> (gh, gw, K)."""
    c = np.stack(chans, axis=-1)
    h, w, _ = c.shape
    gh = (h - patch) // stride + 1
    gw = (w - patch) // stride + 1
    ii = np.zeros((h + 1, w + 1, c.shape[-1]))
    ii[1:, 1:] = c.cumsum(axis=0).cumsum(axis=1)
    r0 = np.arange(gh) * stride
    c0 = np.arange(gw) * stride
    a = ii[r0[:, None] + patch, c0[None, :] + patch]
    b = ii[r0[:, None], c0[None, :] + patch]
    d = ii[r0[:, None] + patch, c0[None, :]]
    e = ii[r0[:, None], c0[None, :]]
    return (a - b - d + e) / float(patch * patch)


def _fourier_bands(gray, patch, stride):
    from numpy.lib.stride_tricks import sliding_window_view      # noqa: PLC0415
    win = sliding_window_view(gray, (patch, patch))[::stride, ::stride]
    gh, gw = win.shape[:2]
    han = np.outer(np.hanning(patch + 2)[1:-1], np.hanning(patch + 2)[1:-1])
    power = np.abs(np.fft.fft2(win * han, axes=(-2, -1))) ** 2
    rad = np.hypot(np.fft.fftfreq(patch)[:, None], np.fft.fftfreq(patch)[None, :])
    edges = np.linspace(0.0, 0.75, _FOURIER_BANDS + 1)          # corner frequency of a patch is 0.707
    tot = power[..., rad > 0].sum(axis=-1) + _EPS
    out = np.empty((gh, gw, _FOURIER_BANDS))
    for b in range(_FOURIER_BANDS):
        m = (rad > edges[b]) & (rad <= edges[b + 1])
        out[..., b] = np.log10(power[..., m].sum(axis=-1) / tot + 1e-6)
    return out


def _features_of(img, spec):
    """(gh, gw, D) patch features and the channel names, for one image."""
    h, w = img.shape[:2]
    if min(h, w) < spec["patch"]:
        raise ValueError("patch_features: the image %s is smaller than patch=%d" % ((h, w), spec["patch"]))
    chans, names = _pixel_channels(img, spec)
    parts = []
    if chans:
        parts.append(_pool(chans, spec["patch"], spec["stride"]))
    if "fourier" in spec["groups"]:
        parts.append(_fourier_bands(_gray(img), spec["patch"], spec["stride"]))
        names = names + ["fourier_b%d" % b for b in range(_FOURIER_BANDS)]
    return (parts[0] if len(parts) == 1 else np.concatenate(parts, axis=-1)), names


def _stack_features(stack, spec):
    f0, names = _features_of(stack[0], spec)
    out = np.empty((stack.shape[0],) + f0.shape)
    out[0] = f0
    for i in range(1, stack.shape[0]):
        out[i] = _features_of(stack[i], spec)[0]
    return out, names


def patch_features(image, patch=8, stride=4, scales=(1.0, 2.0, 4.0), groups=("gradient", "gabor", "lbp"),
                   n_orient=4):
    """Classical patch features on a grid: one D-vector per patch (``table``).

    ``image`` is (H, W) or (H, W, 3). Pixel channels are computed at every Gaussian scale in
    ``scales`` (sigma, px) and averaged over ``patch`` x ``patch`` windows every ``stride`` px:
    ``intensity`` (smoothed mean), ``gradient`` (Gaussian-derivative magnitude and the
    doubled-angle components |g|cos2t, |g|sin2t: the structure tensor), ``gabor`` (zero-mean
    Gabor energy, wavelength 4 sigma, ``n_orient`` orientations), ``lbp`` (histogram of the 10
    rotation-invariant uniform local binary patterns, radius = round(sigma)), ``color``
    (red-green and yellow-blue opponents, needs a colour image). ``fourier`` is computed on the
    raw patches, not per scale: the log share of a Hann-windowed patch's spectrum in three
    radial bands. Returns ``features`` (gh, gw, D), ``names`` (D), ``grid`` (gh, gw), ``dim``
    and the parameters.

    Raises ``ValueError`` on an empty / non-finite / wrongly shaped image, an image smaller
    than ``patch``, unknown groups, or ``color`` on a gray image.
    """
    op = "patch_features"
    img = _one(image, "image", op)
    spec = _spec(patch, stride, scales, groups, n_orient, op)
    f, names = _features_of(img, spec)
    return {"features": f, "names": names, "grid": f.shape[:2], "dim": f.shape[-1],
            "patch": spec["patch"], "stride": spec["stride"], "scales": spec["scales"],
            "groups": spec["groups"], "n_orient": spec["n_orient"]}


# ----------------------------------------------------------------------------- shrinkage
def _lw_intensity(xc, s_mle):
    """Ledoit–Wolf (2004) analytic intensity for one position. xc: (n, D) centred, s_mle = xc'xc/n."""
    n, d = xc.shape
    m = np.trace(s_mle) / d
    d2 = float(((s_mle - m * np.eye(d)) ** 2).sum()) / d
    if d2 <= 0.0:
        return 1.0
    b2 = (float((np.sum(xc * xc, axis=1) ** 2).sum()) - n * float((s_mle ** 2).sum())) / (n * n * d)
    return float(min(max(b2, 0.0) / d2, 1.0))


def _shrinkage_spec(shrinkage, op):
    if isinstance(shrinkage, str):
        if shrinkage not in ("auto", "none"):
            raise ValueError("%s: shrinkage must be 'auto', 'none' or a number in [0, 1], got %r" % (op, shrinkage))
        return shrinkage
    f = _num(shrinkage, "shrinkage", op, 0.0, 1.0)
    return "none" if f == 0.0 else f                                 # 0 means no shrinkage: the full-rank rule applies


def _gauss_fit(feats, shrinkage, ridge, op):
    """Per-position mean, precision matrix of the shrunk covariance and the shrinkage used. feats (n, gh, gw, D)."""
    n, gh, gw, d = feats.shape
    mean = feats.mean(axis=0)
    xc = feats - mean
    s = np.einsum("nijd,nije->ijde", xc, xc) / n                    # maximum-likelihood covariance per position
    m = np.trace(s, axis1=2, axis2=3) / d
    if not float(np.median(m)) > 1e-18 * max(float(np.mean(feats ** 2)), _EPS):
        raise ValueError("%s: the good images show no variation in the features (the median variance is zero relative to the feature scale); "
                         "an identical stack gives no model of what varies" % op)
    ident = np.eye(d)
    if shrinkage == "auto":
        lam = np.empty((gh, gw))
        for i in range(gh):
            for j in range(gw):
                lam[i, j] = _lw_intensity(xc[:, i, j, :], s[i, j])
    elif shrinkage == "none":
        lam = np.zeros((gh, gw))
    else:
        lam = np.full((gh, gw), float(shrinkage))
    sig = (1.0 - lam)[..., None, None] * s + (lam * m)[..., None, None] * ident
    if shrinkage == "none":
        if n - 1 < d:
            raise ValueError("%s: shrinkage='none' needs a full-rank covariance, but n=%d good images "
                             "give rank <= %d for D=%d features; declare a shrinkage (shrinkage='auto' or a "
                             "number in (0, 1]) or use more good images / fewer features" % (op, n, n - 1, d))
    else:
        sig = sig + ridge * max(float(np.median(m)), _EPS) * ident
    try:
        chol = np.linalg.cholesky(sig)
    except np.linalg.LinAlgError:
        raise ValueError("%s: the covariance is singular at some position with shrinkage=%r (a feature "
                         "is constant over the good images there); drop that feature group or raise "
                         "the shrinkage" % (op, shrinkage)) from None
    cinv = np.linalg.solve(chol, np.broadcast_to(ident, chol.shape))
    prec = np.einsum("ijkd,ijke->ijde", cinv, cinv)                  # (L L')^-1 = L'^-1 L^-1
    return mean, prec, lam


def _upsample_smooth(grid_map, shape, spec, smooth):
    from scipy import ndimage as ndi            # noqa: PLC0415
    gh, gw = grid_map.shape
    p, st = spec["patch"], spec["stride"]
    rr = np.clip((np.arange(shape[0]) - (p - 1) / 2.0) / st, 0, gh - 1)
    cc = np.clip((np.arange(shape[1]) - (p - 1) / 2.0) / st, 0, gw - 1)
    full = ndi.map_coordinates(grid_map, np.meshgrid(rr, cc, indexing="ij"), order=1, mode="nearest")
    return ndi.gaussian_filter(full, smooth, mode="nearest") if smooth > 0 else full


def _spec_of(model, op, kind):
    if not isinstance(model, dict) or model.get("kind") != kind:
        raise ValueError("%s: model must be the dict returned by %s" % (
            op, "patchdist_fit" if kind == "patchdist" else "patchbank_fit"))
    return {"patch": model["patch"], "stride": model["stride"], "scales": tuple(model["scales"]),
            "groups": tuple(model["groups"]), "n_orient": model["n_orient"]}


def _check_shape(img, model, op):
    if tuple(img.shape[:2]) != tuple(model["image_shape"]) or (img.ndim == 3) != bool(model["colour"]):
        raise ValueError("%s: the test image %s does not match the model's training images %s%s"
                         % (op, img.shape, tuple(model["image_shape"]), " (colour)" if model["colour"] else ""))


def _select_dims(d, n_dims, seed, op):
    if n_dims is None:
        return np.arange(d)
    nd = _int(n_dims, "n_dims", op, 1, d)
    return np.sort(np.random.default_rng(_int(seed, "seed", op, 0, 2 ** 31 - 1)).permutation(d)[:nd])


def patchdist_fit(stack, patch=8, stride=4, scales=(1.0, 2.0, 4.0), groups=("gradient", "gabor", "lbp"),
                  n_orient=4, shrinkage="auto", n_dims=None, seed=0, ridge=1e-6, pool="position"):
    """Learn a normal distribution of the patch feature at every grid position from good images (``table``).

    ``stack`` is (n, H, W) or (n, H, W, 3) of good images, n >= 2, registered well enough that a
    grid cell sees the same content. The feature is ``patch_features`` (same parameters). At
    every cell the mean and the covariance (maximum likelihood, divided by n) of the D-dimensional
    feature are estimated; n <= D makes the covariance singular, so the **shrinkage toward
    tr(S)/D * I is declared**: ``"auto"`` is the Ledoit–Wolf analytic intensity per position,
    a number in (0, 1] fixes it, ``"none"`` (or 0) is accepted only when n - 1 >= D and the
    covariance is positive definite and otherwise refused. ``n_dims`` keeps a seeded random subset of the
    D dimensions (the memory trick of the original method), ``ridge`` (relative to the median
    variance, applied unless ``shrinkage="none"``) is a numerical floor against exactly constant
    channels. ``pool="position"`` (default) estimates one distribution per grid cell, right when
    the content is registered; ``pool="global"`` estimates ONE distribution from the patches of
    all cells and images (n * gh * gw samples, overlapping patches are not independent), right
    for a stationary texture whose content at a cell differs from image to image and which has
    far more samples than dimensions.

    Returns the model: per-position ``mean`` and ``precision`` (inverse of the shrunk
    covariance), ``shrinkage_map`` and its mean ``shrinkage_mean``, ``n_train``, ``dim``,
    ``dims`` (kept channels), the feature parameters and ``image_shape``. Pass it to
    ``patchdist_score``.

    Raises ``ValueError`` for fewer than two images, a singular covariance with
    ``shrinkage="none"``, a constant feature that stays singular, or invalid parameters.
    """
    op = "patchdist_fit"
    st = _images(stack, "stack", op, min_n=2)
    spec = _spec(patch, stride, scales, groups, n_orient, op)
    sh = _shrinkage_spec(shrinkage, op)
    rg = _num(ridge, "ridge", op, 0.0, 1.0)
    if "color" in spec["groups"] and st.ndim != 4:
        raise ValueError("%s: group 'color' needs colour images (n, H, W, 3)" % op)
    feats, names = _stack_features(st, spec)
    dims = _select_dims(feats.shape[-1], n_dims, seed, op)
    feats = feats[..., dims]
    if feats.size > _MAX_FEATURES:
        raise ValueError("%s: %d feature values (> %d); use fewer images, n_dims or a larger stride"
                         % (op, feats.size, _MAX_FEATURES))
    if pool not in ("position", "global"):
        raise ValueError("%s: pool must be 'position' or 'global', got %r" % (op, pool))
    if pool == "global":
        gh, gw = feats.shape[1:3]
        mean, prec, lam = _gauss_fit(feats.reshape(-1, 1, 1, feats.shape[-1]), sh, rg, op)
        mean = np.broadcast_to(mean, (gh, gw, mean.shape[-1]))
        prec = np.broadcast_to(prec, (gh, gw) + prec.shape[2:])
        lam = np.broadcast_to(lam, (gh, gw))
    else:
        mean, prec, lam = _gauss_fit(feats, sh, rg, op)
    return {"kind": "patchdist", "mean": mean, "precision": prec, "shrinkage_map": lam, "pool": pool,
            "shrinkage_mean": float(lam.mean()), "shrinkage": sh, "n_train": int(st.shape[0]),
            "dim": int(feats.shape[-1]), "dims": dims, "names": [names[i] for i in dims],
            "grid": mean.shape[:2], "image_shape": tuple(st.shape[1:3]), "colour": st.ndim == 4,
            "patch": spec["patch"], "stride": spec["stride"], "scales": spec["scales"],
            "groups": spec["groups"], "n_orient": spec["n_orient"]}


def patchdist_score(image, model, smooth=4.0):
    """Score one image against a per-position normal distribution: the Mahalanobis distance per patch (``table``).

    ``model`` comes from ``patchdist_fit``; ``image`` must have the training images' shape. The
    grid of distances ``sqrt((x - mu)' P (x - mu))`` is interpolated (bilinear, between patch
    centres) to the image size and smoothed by a Gaussian of ``smooth`` px (0 = no smoothing).
    Returns ``map`` (H, W; higher = more anomalous), ``grid`` (the raw distances),
    ``image_score`` (the maximum of the smoothed map) and ``smooth``.

    Raises ``ValueError`` for a model that is not a ``patchdist_fit`` result, a different image
    shape, or a negative / non-finite ``smooth``.
    """
    op = "patchdist_score"
    spec = _spec_of(model, op, "patchdist")
    img = _one(image, "image", op)
    sm = _num(smooth, "smooth", op, 0.0, 64.0)
    _check_shape(img, model, op)
    f, _ = _features_of(img, spec)
    x = f[..., model["dims"]] - model["mean"]
    d2 = np.einsum("ijd,ijde,ije->ij", x, model["precision"], x)
    grid = np.sqrt(np.maximum(d2, 0.0))
    full = _upsample_smooth(grid, img.shape[:2], spec, sm)
    return {"map": full, "grid": grid, "image_score": float(full.max()), "smooth": sm}


# ----------------------------------------------------------------------------- memory bank
def _position_columns(gh, gw, weight, d):
    ii, jj = np.meshgrid(np.arange(gh) / max(gh - 1, 1), np.arange(gw) / max(gw - 1, 1), indexing="ij")
    return weight * math.sqrt(d) * np.stack([ii, jj], axis=-1)


def _greedy_kcenter(x, m, seed, proj_dim):
    """Greedy k-centre selection of m rows of x (Sener and Savarese 2018) with distances in a seeded random
    projection to proj_dim dimensions. Returns the indices and the covering radius after the selection."""
    n, d = x.shape
    rng = np.random.default_rng(seed)
    z = x if (proj_dim is None or proj_dim >= d) else x @ (rng.standard_normal((d, proj_dim)) / math.sqrt(proj_dim))
    first = int(rng.integers(0, n))
    sel = np.empty(m, dtype=np.int64)
    sel[0] = first
    mind = ((z - z[first]) ** 2).sum(axis=1)
    for t in range(1, m):
        nxt = int(np.argmax(np.round(mind, 10)))
        sel[t] = nxt
        mind = np.minimum(mind, ((z - z[nxt]) ** 2).sum(axis=1))
    return sel, float(math.sqrt(max(float(mind.max()), 0.0)))


def patchbank_fit(stack, patch=8, stride=4, scales=(1.0, 2.0, 4.0), groups=("gradient", "gabor", "lbp"),
                  n_orient=4, coreset=0.1, proj_dim=32, position_weight=0.0, seed=0):
    """Build a memory bank of good patch features, thinned by greedy k-centre covering (``table``).

    ``stack`` is (n, H, W) or (n, H, W, 3) of good images (n >= 1). Features are standardised
    with the mean and the standard deviation of each dimension over all good patches. With
    ``position_weight`` > 0 the grid position (0..1 in each direction) times ``position_weight *
    sqrt(D)`` is appended, so a patch is compared with good patches from nearby positions
    (0 = position-free). ``coreset`` in (0, 1] is the fraction of patches kept: the greedy
    k-centre cover picks, from a seeded start, always the patch farthest from the ones already
    kept, measuring distances in a seeded random projection to ``proj_dim`` dimensions (None =
    exact). The covering radius in that space after the selection is returned: the largest
    distance from any good patch to the bank. ``coreset=1`` keeps everything (radius 0, no
    selection, so ``seed`` and ``proj_dim`` have no effect).

    Returns the model: ``bank`` (m, D'), ``mean`` / ``std`` (D), ``n_total`` patches, ``n_memory``,
    ``fraction``, ``covering_radius``, the feature parameters and ``image_shape``.

    Raises ``ValueError`` for invalid parameters, a feature that is constant over all good patches,
    or a stack that would exceed the memory guard.
    """
    op = "patchbank_fit"
    st = _images(stack, "stack", op, min_n=1)
    spec = _spec(patch, stride, scales, groups, n_orient, op)
    frac = _num(coreset, "coreset", op, 0.0, 1.0, lo_open=True)
    pw = _num(position_weight, "position_weight", op, 0.0, 100.0)
    seed = _int(seed, "seed", op, 0, 2 ** 31 - 1)
    pd = None if proj_dim is None else _int(proj_dim, "proj_dim", op, 1, 4096)
    if "color" in spec["groups"] and st.ndim != 4:
        raise ValueError("%s: group 'color' needs colour images (n, H, W, 3)" % op)
    feats, names = _stack_features(st, spec)
    n, gh, gw, d = feats.shape
    if feats.size > _MAX_FEATURES:
        raise ValueError("%s: %d feature values (> %d); use fewer images or a larger stride"
                         % (op, feats.size, _MAX_FEATURES))
    flat = feats.reshape(-1, d)
    mean = flat.mean(axis=0)
    std = flat.std(axis=0)
    floor = 1e-9 * max(float(std.max()), _EPS)
    if (std <= floor).any():
        bad = [names[i] for i in np.nonzero(std <= floor)[0][:5]]
        raise ValueError("%s: feature(s) %s are constant over all good patches (cannot be standardised); "
                         "drop that group or use richer images" % (op, bad))
    z = (feats - mean) / std
    if pw > 0.0:
        z = np.concatenate([z, np.broadcast_to(_position_columns(gh, gw, pw, d), (n, gh, gw, 2))], axis=-1)
    z = z.reshape(-1, z.shape[-1])
    m = int(min(z.shape[0], max(1, math.ceil(frac * z.shape[0]))))
    if m == z.shape[0]:                                   # nothing to thin: every patch is kept, the cover is exact
        sel, radius = np.arange(m), 0.0
    else:
        sel, radius = _greedy_kcenter(z, m, seed, pd)
    return {"kind": "patchbank", "bank": z[sel], "mean": mean, "std": std, "n_total": int(z.shape[0]),
            "n_memory": int(m), "fraction": float(m) / z.shape[0], "covering_radius": radius,
            "position_weight": pw, "names": names, "grid": (gh, gw), "image_shape": tuple(st.shape[1:3]),
            "colour": st.ndim == 4, "patch": spec["patch"], "stride": spec["stride"],
            "scales": spec["scales"], "groups": spec["groups"], "n_orient": spec["n_orient"]}


def _knn_dist(q, bank, k, chunk=256):
    """Mean distance to the k nearest rows of bank for every row of q (exact, chunked)."""
    b2 = (bank ** 2).sum(axis=1)
    out = np.empty(q.shape[0])
    for a in range(0, q.shape[0], chunk):
        qq = q[a:a + chunk]
        d2 = np.maximum((qq ** 2).sum(axis=1)[:, None] + b2[None, :] - 2.0 * (qq @ bank.T), 0.0)
        if k == 1:
            out[a:a + chunk] = np.sqrt(d2.min(axis=1))
        else:
            out[a:a + chunk] = np.sqrt(np.partition(d2, k - 1, axis=1)[:, :k]).mean(axis=1)
    return out


def patchbank_score(image, model, k=1, smooth=4.0):
    """Score one image by the distance of each patch to its ``k`` nearest good patches in the bank (``table``).

    ``model`` comes from ``patchbank_fit``; ``image`` must have the training images' shape. The
    distance (Euclidean, in standardised feature space; the mean over the k nearest) is computed
    exactly by brute force, interpolated to the image size and smoothed by a Gaussian of
    ``smooth`` px. Returns ``map`` (H, W), ``grid`` (raw distances), ``image_score`` (maximum of
    the smoothed map), ``k`` and ``smooth``.

    Raises ``ValueError`` for a model that is not a ``patchbank_fit`` result, a different image
    shape, ``k`` larger than the bank, or a negative / non-finite ``smooth``.
    """
    op = "patchbank_score"
    spec = _spec_of(model, op, "patchbank")
    img = _one(image, "image", op)
    sm = _num(smooth, "smooth", op, 0.0, 64.0)
    bank = model["bank"]
    kk = _int(k, "k", op, 1, bank.shape[0])
    _check_shape(img, model, op)
    f, _ = _features_of(img, spec)
    gh, gw, d = f.shape
    z = (f - model["mean"]) / model["std"]
    if model["position_weight"] > 0.0:
        z = np.concatenate([z, _position_columns(gh, gw, model["position_weight"], d)], axis=-1)
    grid = _knn_dist(z.reshape(-1, z.shape[-1]), bank, kk).reshape(gh, gw)
    full = _upsample_smooth(grid, img.shape[:2], spec, sm)
    return {"map": full, "grid": grid, "image_score": float(full.max()), "k": kk, "smooth": sm}
