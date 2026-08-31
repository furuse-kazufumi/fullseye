# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""GT tests for 3-D frequency filtering (volfreq) and RL deconvolution (volrestore)."""
import numpy as np
import pytest

import volfreq
import volrestore


# --------------------------------------------------------------------------- #
# volfreq                                                                      #
# --------------------------------------------------------------------------- #
def _two_scale_volume(n=32):
    """A slow single-period sine along z (f=1/32 c/vox — genuinely periodic,
    unlike a ramp, whose wrap-around jump leaks energy into all frequencies:
    the documented periodicity limitation) + a fine checkerboard (Nyquist)."""
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    slow = np.sin(2 * np.pi * z / n)
    fine = 0.25 * ((-1.0) ** (z + y + x))
    return slow, fine, slow + fine


def test_lowpass_keeps_slow_and_kills_fine():
    slow, fine, v = _two_scale_volume()
    lp = volfreq.vol_fft_lowpass(v, cutoff=0.1)
    # the checkerboard (|f| ~ 0.87 cycles/voxel diag) is crushed, the slow
    # sine (0.031 c/vox, transfer exp(-0.031^2/(2*0.1^2)) = 0.95) survives
    assert np.abs(lp - 0.95 * slow).max() < 0.02
    assert np.abs(lp - v).max() > 0.2                # it genuinely removed something


def test_highpass_is_exact_complement():
    _, _, v = _two_scale_volume()
    lp = volfreq.vol_fft_lowpass(v, cutoff=0.07)
    hp = volfreq.vol_fft_highpass(v, cutoff=0.07)
    assert np.allclose(lp + hp, v, atol=1e-10)       # documented identity
    assert abs(float(hp.mean())) < 1e-10             # DC removed


def test_lowpass_preserves_dc_exactly():
    const = np.full((8, 8, 8), 0.37)
    lp = volfreq.vol_fft_lowpass(const, cutoff=0.05)
    assert np.allclose(lp, 0.37, atol=1e-12)


def test_bandpass_selects_middle_scale():
    n = 48
    z = np.mgrid[0:n, 0:n, 0:n][0].astype(np.float64)
    lowf = np.sin(2 * np.pi * z * (1.0 / 48.0))       # f = 0.021 c/vox
    midf = np.sin(2 * np.pi * z * (6.0 / 48.0))       # f = 0.125
    highf = np.sin(2 * np.pi * z * (20.0 / 48.0))     # f = 0.417
    v = lowf + midf + highf
    bp = volfreq.vol_fft_bandpass(v, low=0.06, high=0.25)
    # the mid tone survives with the largest share of its original energy
    def share(comp):
        return float(np.vdot(bp, comp).real / np.vdot(comp, comp).real)
    assert share(midf) > 0.5
    assert share(lowf) < 0.35 and share(highf) < 0.35
    assert share(midf) > 2.0 * max(share(lowf), share(highf))


def test_spacing_makes_cutoff_physical():
    """The same physical structure must respond the same under anisotropic
    spacing when the cutoff is physical (cycles/mm)."""
    n = 32
    z = np.mgrid[0:n, 0:n, 0:n][0].astype(np.float64)
    # a 8-voxel period along z; with sz=2.0 mm that's a 16 mm period = 1/16 c/mm
    v = np.sin(2 * np.pi * z / 8.0)
    keep = volfreq.vol_fft_lowpass(v, cutoff=0.5, spacing=(2.0, 1.0, 1.0))
    kill = volfreq.vol_fft_lowpass(v, cutoff=0.01, spacing=(2.0, 1.0, 1.0))
    assert float(np.abs(keep).max()) > 0.8            # far below 0.5 c/mm: kept
    assert float(np.abs(kill).max()) < 0.05           # far above 0.01 c/mm: gone


def test_volfreq_fail_closed():
    v = np.zeros((4, 4, 4))
    with pytest.raises(ValueError, match="cutoff"):
        volfreq.vol_fft_lowpass(v, cutoff=0.0)
    with pytest.raises(ValueError, match="low < high"):
        volfreq.vol_fft_bandpass(v, low=0.3, high=0.1)
    with pytest.raises(ValueError, match="3-D"):
        volfreq.vol_fft_lowpass(np.zeros((4, 4)), cutoff=0.1)
    bad = v.copy(); bad[0, 0, 0] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        volfreq.vol_fft_highpass(bad, cutoff=0.1)
    with pytest.raises(ValueError, match="spacing"):
        volfreq.vol_fft_lowpass(v, cutoff=0.1, spacing=(1.0, 0.0, 1.0))


# --------------------------------------------------------------------------- #
# volrestore                                                                   #
# --------------------------------------------------------------------------- #
def _blurred_spheres(n=40, sigma=2.0, seed=5):
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    truth = (((z - 14) ** 2 + (y - 14) ** 2 + (x - 14) ** 2) <= 36).astype(np.float64)
    truth += (((z - 27) ** 2 + (y - 27) ** 2 + (x - 27) ** 2) <= 16).astype(np.float64)
    psf = volrestore.vol_gaussian_psf(sigma)
    from scipy.signal import fftconvolve
    blurred = fftconvolve(truth, psf, mode="same")
    blurred = np.clip(blurred, 0.0, None)
    return truth, psf, blurred


def test_gaussian_psf_is_normalised_and_centred():
    k = volrestore.vol_gaussian_psf((1.0, 2.0, 3.0))
    assert k.sum() == pytest.approx(1.0)
    assert k.shape == (9, 17, 25)                     # 2*ceil(4*s)+1 per axis
    assert np.unravel_index(k.argmax(), k.shape) == (4, 8, 12)
    with pytest.raises(ValueError, match="sigma"):
        volrestore.vol_gaussian_psf(-1.0)


def test_richardson_lucy_improves_gradually_and_is_forward_consistent():
    """The docstring claims, pinned to measurements: RMSE falls to 0.81x at 10
    iterations / 0.68x at 50 (gradual — hard edges dominate the residual), and
    re-blurring the estimate reproduces the observation (the quantity RL
    actually optimises)."""
    from scipy.signal import fftconvolve
    truth, psf, blurred = _blurred_spheres()
    rmse_blur = float(np.sqrt(np.mean((blurred - truth) ** 2)))
    est10 = volrestore.vol_richardson_lucy(blurred, psf, iterations=10)
    est50 = volrestore.vol_richardson_lucy(blurred, psf, iterations=50)
    r10 = float(np.sqrt(np.mean((est10 - truth) ** 2))) / rmse_blur
    r50 = float(np.sqrt(np.mean((est50 - truth) ** 2))) / rmse_blur
    assert r10 < 0.85, r10                             # measured 0.809
    assert r50 < r10 and r50 < 0.72, (r50, r10)        # measured 0.679
    # forward consistency: K * est ~= observation, far tighter than K * truth is
    reblur = fftconvolve(est50, psf, mode="same")
    assert float(np.sqrt(np.mean((reblur - blurred) ** 2))) < 0.02 * rmse_blur
    assert est10.min() >= 0.0                          # non-negativity preserved
    # intensity is approximately conserved (the RL update preserves flux)
    assert float(est10.sum()) == pytest.approx(float(blurred.sum()), rel=0.02)


def test_richardson_lucy_fail_closed():
    truth, psf, blurred = _blurred_spheres(n=20, sigma=1.0)
    with pytest.raises(ValueError, match="negative"):
        volrestore.vol_richardson_lucy(blurred - 1.0, psf)
    with pytest.raises(ValueError, match="iterations"):
        volrestore.vol_richardson_lucy(blurred, psf, iterations=0)
    with pytest.raises(ValueError, match="psf"):
        volrestore.vol_richardson_lucy(blurred, -psf)
    with pytest.raises(ValueError, match="psf"):
        volrestore.vol_richardson_lucy(blurred, np.zeros((3, 3)))
    big_psf = volrestore.vol_gaussian_psf(10.0)        # 81^3 kernel > 20^3 volume
    with pytest.raises(ValueError, match="exceeds"):
        volrestore.vol_richardson_lucy(blurred, big_psf)
