"""Regression guard: the Gabor kernel must be DC-free (zero-mean).

Ground truth (Daugman 1985 / the standard 2D Gabor definition, already cited for
this op in ``references.py``): a Gabor filter is a BAND-PASS texture/orientation
filter.  Its kernel integrates to zero, so

  * convolving a CONSTANT image yields exactly 0 (no DC leakage),
  * the response is invariant to adding a constant offset to the input, and
  * a grating at the filter's tuned frequency out-responds a flat bright patch.

The pre-fix kernel was ``exp(-r**2/8) * cos(2*pi*f*xr)`` with no DC correction.
At the low end of the frequency sweep (b=0 -> f=0.1) the Gaussian envelope does
not complete a cycle inside the 15x15 support, so the coefficients summed to
~11.4 and the "texture" op was really a brightness (low-pass) detector: a flat
1.0 block beat a tuned grating by ~1.9x, and a constant image saturated to 1.0
after ``_norm``.

Both copies of the kernel are covered: ``gabor`` (ops.py::_gabor) and
``gen_gabor`` (backends_auto.py::_sh_texture, kind=="gabor").
"""
from __future__ import annotations

import numpy as np
import pytest

import ops

GABOR_OPS = ["gabor", "gen_gabor"]

# theta = pi*a  -> a=0 gives theta=0 (kernel oscillates along x);
# freq = 0.1 + 0.3*b -> b=0 gives the 0.1 cycles/px the test grating carries.
# The op is therefore TUNED to the grating below: it has every advantage.
TUNED_A, TUNED_B = 0.0, 0.0


def _fn(name):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered")
    return fn


def _scene(n=64):
    """rows 8..24: flat bright block (1.0).  rows 40..56: freq-0.1 grating."""
    img = np.zeros((n, n), np.float64)
    img[8:24, :] = 1.0
    x = np.arange(n)
    img[40:56, :] = (0.5 + 0.5 * np.cos(2 * np.pi * 0.1 * x))[None, :]
    return img


@pytest.mark.parametrize("name", GABOR_OPS)
@pytest.mark.parametrize("level", [0.25, 0.7, 1.0])
def test_gabor_kernel_is_zero_mean_constant_image_gives_zero(name, level):
    """Zero-mean kernel <=> a constant image convolves to 0 everywhere."""
    fn = _fn(name)
    out = np.asarray(fn(np.full((64, 64), level), TUNED_A, TUNED_B), np.float64)
    assert float(np.max(np.abs(out))) < 1e-6, (
        f"{name}: constant image gave a response "
        f"(max={float(np.max(np.abs(out))):.4f}); the kernel carries DC gain")


@pytest.mark.parametrize("name", GABOR_OPS)
def test_gabor_prefers_tuned_grating_over_flat_bright_block(name):
    """A texture filter must respond to structure, not to brightness."""
    fn = _fn(name)
    out = np.asarray(fn(_scene(), TUNED_A, TUNED_B), np.float64)
    block = float(out[10:22, 8:56].mean())    # flat 1.0 patch, interior only
    grating = float(out[42:54, 8:56].mean())  # tuned grating, interior only
    assert grating > 1.5 * block, (
        f"{name}: flat bright block ({block:.4f}) rivals the tuned grating "
        f"({grating:.4f}) - the filter is measuring brightness, not texture")


@pytest.mark.parametrize("name", GABOR_OPS)
def test_gabor_is_invariant_to_a_dc_offset(name):
    """A DC-free linear filter is unchanged by adding a constant to the input."""
    fn = _fn(name)
    rng = np.random.default_rng(20260813)
    base = rng.random((64, 64)) * 0.6
    lo = np.asarray(fn(base, TUNED_A, TUNED_B), np.float64)
    hi = np.asarray(fn(base + 0.3, TUNED_A, TUNED_B), np.float64)
    assert np.allclose(lo, hi, atol=1e-8), (
        f"{name}: response changed under a pure DC offset "
        f"(max delta={float(np.max(np.abs(lo - hi))):.4f})")


@pytest.mark.parametrize("name", GABOR_OPS)
def test_gabor_still_returns_a_unit_range_image(name):
    """Contract guard: out_sort=image must stay in [0,1] after the DC fix."""
    fn = _fn(name)
    out = np.asarray(fn(_scene(), 0.3, 0.4), np.float64)
    assert out.shape == (64, 64)
    assert np.isfinite(out).all()
    assert out.min() >= -1e-12 and out.max() <= 1.0 + 1e-12
