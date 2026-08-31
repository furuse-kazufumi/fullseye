# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Frequency-domain filtering for 3-D volumes (FFT low/high/band-pass).

The 2-D side has a 19-op ``frequency`` family (``complexops``); the voxel world
had none, yet frequency filtering is a staple on volumes too: detrending an
illumination/thickness drift (low-pass residual), suppressing periodic stripe
or ring artefacts, isolating a texture scale before measurement. This module
adds the three canonical filters with **Gaussian** transfer functions — smooth
in the frequency domain, hence no spatial ringing, which is the honest default
for measurement work (an ideal brick-wall filter rings; see limitations).

Cutoffs are given in **cycles per voxel** along each axis (Nyquist = 0.5). Pass
*spacing* ``(sz, sy, sx)`` in mm to interpret the cutoff in **cycles per mm**
instead — with anisotropic voxels the same physical structure has different
per-axis digital frequencies, and the spacing-aware path accounts for exactly
that.

Honest limitations:

  * The FFT treats the volume as periodic. A strong intensity mismatch between
    opposite faces leaks energy across the wrap; for measurement-grade work on
    non-periodic data, detrend (or pad) first. Nothing here windows the input
    silently — that would alter amplitudes without telling you.
  * A Gaussian transfer function has no sharp cutoff: ``cutoff`` is the
    frequency where attenuation reaches ``exp(-1/2) ~ 0.61``, not a brick
    wall. This is deliberate (no ringing), and documented rather than hidden.

Fail-closed: 3-D only, float64, NaN/Inf rejected, voxel cap before the FFT
allocation, positive finite cutoffs required.
"""
from __future__ import annotations

import numpy as np

__all__ = ["vol_fft_lowpass", "vol_fft_highpass", "vol_fft_bandpass",
           "VOLFREQ_OPS", "MAX_VOXELS"]

#: Public operators (facade wiring).
VOLFREQ_OPS = ["vol_fft_lowpass", "vol_fft_highpass", "vol_fft_bandpass"]

#: Same budget as volops' cheap ops (~134 M voxels); the FFT allocates a
#: complex128 copy (16 B/voxel), still bounded by this cap.
MAX_VOXELS = 1 << 27


def _require_volume(vol, name: str = "vol") -> np.ndarray:
    v = np.ascontiguousarray(vol, dtype=np.float64)
    if v.ndim != 3:
        raise ValueError("%s must be a 3-D (D, H, W) volume, got a %d-D array"
                         % (name, v.ndim))
    if not np.isfinite(v).all():
        raise ValueError("%s has non-finite voxel(s) (NaN/Inf) — refusing"
                         % (name,))
    if v.size > MAX_VOXELS:
        raise ValueError("%s: %d voxels exceeds the %d cap (volfreq.MAX_VOXELS)"
                         % (name, v.size, MAX_VOXELS))
    return v


def _freq_radius(shape, spacing):
    """Per-voxel frequency magnitude |f| — cycles/voxel, or cycles/mm when
    *spacing* is given (``d=spacing`` makes fftfreq return physical frequency)."""
    if spacing is None:
        sp = (1.0, 1.0, 1.0)
    else:
        if hasattr(spacing, "spacing_mm"):
            spacing = spacing.spacing_mm
        try:
            sp = tuple(float(s) for s in spacing)
        except (TypeError, ValueError):
            raise ValueError("spacing must be a length-3 (sz, sy, sx) sequence "
                             "or a VolumeMeta, got %r" % (spacing,)) from None
        if len(sp) != 3 or any(not np.isfinite(s) or s <= 0.0 for s in sp):
            raise ValueError("spacing must be 3 positive finite values, got %r"
                             % (spacing,))
    fz = np.fft.fftfreq(shape[0], d=sp[0])
    fy = np.fft.fftfreq(shape[1], d=sp[1])
    fx = np.fft.rfftfreq(shape[2], d=sp[2])
    return np.sqrt(fz[:, None, None] ** 2 + fy[None, :, None] ** 2
                   + fx[None, None, :] ** 2)


def _check_cutoff(c, name):
    c = float(c)
    if not np.isfinite(c) or c <= 0.0:
        raise ValueError("%s must be a positive finite frequency, got %r"
                         % (name, c))
    if c * c == 0.0:
        # the Gaussian transfer divides by 2*c**2 — a cutoff whose square
        # underflows to 0 would silently produce a NaN volume (0/0 at DC)
        raise ValueError("%s=%r is so small that its square underflows to 0 "
                         "(the transfer function would be 0/0 = NaN); use a "
                         "representable cutoff (> ~1.5e-154)" % (name, c))
    return c


def _apply_transfer(vol, spacing, transfer):
    v = _require_volume(vol)
    fr = _freq_radius(v.shape, spacing)
    spec = np.fft.rfftn(v)
    out = np.fft.irfftn(spec * transfer(fr), s=v.shape)
    return np.ascontiguousarray(out, dtype=np.float64)


def vol_fft_lowpass(vol, cutoff, spacing=None):
    """Gaussian low-pass: keeps structure coarser than ``1/cutoff`` (voxels, or
    mm with *spacing*), attenuates finer detail smoothly. Transfer
    ``exp(-f^2 / (2 cutoff^2))`` — the DC level (mean intensity) passes
    unchanged. Typical use: extract the illumination/thickness drift."""
    c = _check_cutoff(cutoff, "cutoff")
    return _apply_transfer(vol, spacing, lambda f: np.exp(-(f * f) / (2.0 * c * c)))


def vol_fft_highpass(vol, cutoff, spacing=None):
    """Gaussian high-pass — the exact complement ``1 - lowpass`` (the two sum
    to the input to float precision, proven in tests). Removes the DC level and
    slow drift, keeps edges/texture. Output is signed (mean ~ 0)."""
    c = _check_cutoff(cutoff, "cutoff")
    return _apply_transfer(vol, spacing,
                           lambda f: 1.0 - np.exp(-(f * f) / (2.0 * c * c)))


def vol_fft_bandpass(vol, low, high, spacing=None):
    """Gaussian band-pass ``lowpass(high) - lowpass(low)``: keeps structure
    between the two scales (``low < high`` required, both in cycles/voxel or
    cycles/mm with *spacing*). Typical use: isolate one texture scale, or a
    periodic artefact band before subtracting it."""
    lo = _check_cutoff(low, "low")
    hi = _check_cutoff(high, "high")
    if lo >= hi:
        raise ValueError("band-pass needs low < high, got low=%r high=%r"
                         % (low, high))
    return _apply_transfer(
        vol, spacing,
        lambda f: (np.exp(-(f * f) / (2.0 * hi * hi))
                   - np.exp(-(f * f) / (2.0 * lo * lo))))
