"""Named regression tests for defects found in the 2026-08-12 audit.

Each test reproduces one confirmed bug and fails on the pre-fix code (RED),
passing once the fix lands (GREEN). Keep them as pinpoint regression guards
even though the parametrized contracts in test_op_contracts.py also cover them.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops

RNG = np.random.default_rng(20260812)


def _img(n=48):
    return np.clip(RNG.random((n, n)), 0, 1)


def _region(n=48):
    return (RNG.random((n, n)) > 0.4).astype(np.float64)


# --- Bug A: cv2.warpPolar left the unmapped Cartesian corners uninitialised, --- #
#            making the whole polar family nondeterministic (and forward polar    #
#            unclamped, producing values far outside [0,1]).                      #
POLAR_OPS = ["polar_trans_image", "polar_trans_image_ext",
             "polar_trans_image_inv", "polar_trans_region_inv"]


@pytest.mark.parametrize("name", POLAR_OPS)
def test_polar_ops_are_deterministic(name):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered (cv2 backend absent)")
    src = _region() if "region" in name else _img()
    ref = np.asarray(fn(src.copy(), 0.5, 0.5), np.float64)
    for _ in range(8):
        again = np.asarray(fn(src.copy(), 0.5, 0.5), np.float64)
        assert np.array_equal(ref, again), f"{name} is nondeterministic (stale buffer)"


@pytest.mark.parametrize("name", POLAR_OPS)
def test_polar_ops_stay_in_unit_range(name):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered (cv2 backend absent)")
    src = _region() if "region" in name else _img()
    out = np.asarray(fn(src.copy(), 0.5, 0.5), np.float64)
    assert np.all(np.isfinite(out)), f"{name} produced non-finite values"
    assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, (
        f"{name} out of [0,1]: min={out.min()} max={out.max()}")


# --- Bug B: skimage.medial_axis breaks ties with an unseeded RNG. -------------- #
def test_sk_medial_is_deterministic():
    fn = ops.RT.get("sk_medial")
    if fn is None:
        pytest.skip("sk_medial not registered (skimage backend absent)")
    reg = _region()
    ref = np.asarray(fn(reg.copy(), 0.5, 0.5), np.float64)
    for _ in range(5):
        assert np.array_equal(ref, np.asarray(fn(reg.copy(), 0.5, 0.5), np.float64)), (
            "sk_medial is nondeterministic (medial_axis needs a fixed rng)")


# --- Bug C: restoration/denoise ops returned NaN on constant (zero-variance) --- #
#            input, which np.clip does not strip.                                 #
NAN_OPS = ["sk_wavelet", "xsp_wiener", "xsitk_laplacian_sharpen"]


@pytest.mark.parametrize("name", NAN_OPS)
@pytest.mark.parametrize("const", [0.0, 0.5, 1.0])
def test_denoise_ops_finite_on_constant_image(name, const):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered (backend absent)")
    v = np.full((32, 32), const, np.float64)
    out = np.asarray(fn(v, 0.5, 0.5), np.float64)
    assert np.all(np.isfinite(out)), (
        f"{name} produced NaN/Inf on a constant={const} image")
