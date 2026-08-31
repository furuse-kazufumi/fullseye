# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""3-D restoration: Richardson–Lucy deconvolution for volumes.

The 2-D side has a 12-op ``restoration`` family; the voxel world had none —
yet deconvolution is *the* daily restoration task on volumes: a confocal /
widefield microscope stack is the true structure convolved with the
instrument's 3-D point-spread function (PSF), and Richardson–Lucy is the
standard iterative deblur under Poisson noise.

Provenance: W. H. Richardson, "Bayesian-Based Iterative Method of Image
Restoration", JOSA 62(1):55-59, 1972; L. B. Lucy, "An iterative technique for
the rectification of observed distributions", Astronomical Journal
79(6):745-754, 1974. The multiplicative update implemented here is the
classical ``x <- x * (K^T (y / (K x)))`` with FFT convolutions.

Honest limitations:

  * RL amplifies noise as iterations grow — the estimate first improves, then
    degrades ("semi-convergence"). There is no universal stopping rule; the
    test pins improvement at moderate iteration counts, not monotonicity.
  * The PSF is assumed known and shift-invariant. A wrong PSF gives a
    confidently wrong result — this cannot be detected here.
  * FFT convolution treats borders periodically-ish (``fftconvolve`` +
    ``mode='same'``); structure hard against the border deblurs less cleanly.

Fail-closed: 3-D only, float64, NaN/Inf rejected, non-negative input required
(RL is a Poisson model — negative intensities are meaningless and would break
the multiplicative update), voxel cap before FFT allocations.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import fftconvolve

__all__ = ["vol_richardson_lucy", "vol_gaussian_psf", "VOLRESTORE_OPS",
           "MAX_VOXELS"]

#: Public operators (facade wiring).
VOLRESTORE_OPS = ["vol_richardson_lucy", "vol_gaussian_psf"]

#: FFT convolutions allocate several complex temporaries; cap accordingly
#: (~16.7 M voxels, the volops Hessian budget).
MAX_VOXELS = 1 << 24


def _require_volume(vol, name: str = "vol") -> np.ndarray:
    v = np.ascontiguousarray(vol, dtype=np.float64)
    if v.ndim != 3:
        raise ValueError("%s must be a 3-D (D, H, W) volume, got a %d-D array"
                         % (name, v.ndim))
    if not np.isfinite(v).all():
        raise ValueError("%s has non-finite voxel(s) (NaN/Inf) — refusing"
                         % (name,))
    if v.size > MAX_VOXELS:
        raise ValueError("%s: %d voxels exceeds the %d cap "
                         "(volrestore.MAX_VOXELS) — crop or downsample first"
                         % (name, v.size, MAX_VOXELS))
    return v


def vol_gaussian_psf(sigma, truncate=4.0):
    """A normalised (sums to 1) 3-D Gaussian PSF kernel. *sigma* is a scalar or
    ``(sz, sy, sx)`` in voxels; the kernel spans ``+-truncate*sigma`` per axis
    (odd size, centre at the middle voxel). The convenient companion to
    :func:`vol_richardson_lucy` when the instrument PSF is well approximated
    as Gaussian."""
    s = np.atleast_1d(np.asarray(sigma, dtype=np.float64))
    if s.size == 1:
        s = np.repeat(s, 3)
    if s.size != 3 or not np.isfinite(s).all() or (s <= 0.0).any():
        raise ValueError("sigma must be a positive scalar or length-3 "
                         "(sz, sy, sx), got %r" % (sigma,))
    tr = float(truncate)
    if not np.isfinite(tr) or tr <= 0.0:
        raise ValueError("truncate must be positive and finite, got %r"
                         % (truncate,))
    if (s * s <= 0.0).any():
        raise ValueError("sigma %r is so small that sigma**2 underflows to 0 — "
                         "the Gaussian would be 0/0 = NaN; use a representable "
                         "sigma (> ~1.5e-154)" % (sigma,))
    axes = []
    for si in s:
        r = int(np.ceil(tr * si))
        x = np.arange(-r, r + 1, dtype=np.float64)
        axes.append(np.exp(-(x * x) / (2.0 * si * si)))
    k = axes[0][:, None, None] * axes[1][None, :, None] * axes[2][None, None, :]
    return k / k.sum()


def vol_richardson_lucy(vol, psf, iterations=10, clip_tiny=1e-12):
    """Richardson–Lucy deconvolution of a non-negative volume by a known PSF.

    *psf* is a 3-D non-negative kernel (any odd/even size smaller than the
    volume; it is normalised to sum 1 internally so overall intensity is
    preserved). *iterations* trades sharpness against noise amplification —
    5-30 is the practical range (see the module notes on semi-convergence).

    Returns the deblurred ``(D, H, W)`` float64 volume (non-negative).
    Measured on the test scene (binary sphere pair blurred by a sigma-2
    Gaussian): the RMSE to ground truth falls to 0.81x the blurred
    observation's at 10 iterations and 0.68x at 50 — genuine but *gradual*,
    because the residual is dominated by the spheres' hard edges, which RL
    recovers slowly. What converges fast is the *forward consistency*:
    re-blurring the estimate reproduces the observation almost exactly (that
    is the quantity the RL update actually optimises).
    """
    v = _require_volume(vol)
    if (v < 0.0).any():
        raise ValueError("vol has negative voxel(s) — Richardson-Lucy models "
                         "non-negative (Poisson) intensities")
    k = np.ascontiguousarray(psf, dtype=np.float64)
    if k.ndim != 3:
        raise ValueError("psf must be a 3-D kernel, got a %d-D array" % (k.ndim,))
    if not np.isfinite(k).all() or (k < 0.0).any() or k.sum() <= 0.0:
        raise ValueError("psf must be non-negative, finite and not all-zero")
    if any(ks > vs for ks, vs in zip(k.shape, v.shape)):
        raise ValueError("psf shape %r exceeds the volume shape %r"
                         % (k.shape, v.shape))
    n = int(iterations)
    if n != iterations or n < 1:
        raise ValueError("iterations must be a positive integer, got %r"
                         % (iterations,))
    k = k / k.sum()
    k_mirror = k[::-1, ::-1, ::-1]
    est = np.full(v.shape, max(float(v.mean()), clip_tiny))
    for _ in range(n):
        denom = fftconvolve(est, k, mode="same")
        ratio = v / np.maximum(denom, clip_tiny)
        est = est * fftconvolve(ratio, k_mirror, mode="same")
        np.maximum(est, 0.0, out=est)
    return np.ascontiguousarray(est, dtype=np.float64)
