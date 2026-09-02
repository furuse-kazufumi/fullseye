# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""volrestore regressions: the module's own forward model must feed back in.

An FFT convolution of a non-negative volume leaves -1e-16 where the exact value
is 0. Until 2026-09-03 ``vol_richardson_lucy`` rejected that observation as
"negative data", so blur -> deconvolve round-trips needed a manual clip.
"""
import numpy as np
import pytest
from scipy.signal import fftconvolve

import volrestore


def _dusty_observation():
    psf = volrestore.vol_gaussian_psf((1.0, 2.0, 0.5))
    v = np.zeros((9, 17, 11))
    v[4, 8, 5] = 100.0
    blur = fftconvolve(v, psf, mode="same")
    return blur, psf


def test_richardson_lucy_tolerates_fft_rounding_dust():
    blur, psf = _dusty_observation()
    if blur.min() >= 0.0:                                     # keep the test honest
        pytest.skip("this scipy build produced no rounding dust")
    assert blur.min() > -1e-12                                # dust, not data
    est = volrestore.vol_richardson_lucy(blur, psf, iterations=5)
    assert est.shape == blur.shape and np.isfinite(est).all()
    assert est.min() >= 0.0
    assert np.unravel_index(est.argmax(), est.shape) == (4, 8, 5)


def test_richardson_lucy_still_rejects_genuinely_negative_data():
    blur, psf = _dusty_observation()
    with pytest.raises(ValueError, match="negative"):
        volrestore.vol_richardson_lucy(blur - 1e-3, psf, iterations=2)
    # the tolerance is relative to the data scale: -1e-3 on a max-100 volume is
    # 1e-5 relative, far above NEGATIVE_DUST_TOL
    assert 1e-3 / blur.max() > volrestore.NEGATIVE_DUST_TOL


def test_negative_dust_tolerance_is_tiny_and_exported():
    assert 0.0 < volrestore.NEGATIVE_DUST_TOL <= 1e-6
