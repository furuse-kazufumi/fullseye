"""Ground-truth regression guard for the ``frei_dir`` edge-direction convention.

Bug (audit finding #47): ``_sh_edge`` built ``frei_dir`` as
``arctan2(conv(_FREI[1]), conv(_FREI[0]))`` -- i.e. ``arctan2(gx, gy)`` -- while its
siblings ``sobel_dir``/``prewitt_dir`` use ``arctan2(gy, gx)``.  ``_FREI[0]`` is the
horizontal-edge kernel (row/y derivative) and ``_FREI[1]`` the vertical-edge kernel
(col/x derivative), so the reported angle was mirrored about the 45 deg line: a pure
column ramp (gradient pointing +x, 0 deg) came out as 90 deg.

The ground truth here is analytic rather than a golden value: for the plane
``f(x, y) = cos(t) * x + sin(t) * y`` the gradient direction is exactly ``t``, and the
house encoding for a ``*_dir`` op is ``(angle + pi) / (2 * pi)`` so that ``t = 0`` maps
to 0.5 and ``t = +90 deg`` maps to 0.75.  ``sobel_dir``/``prewitt_dir`` are parametrized
alongside ``frei_dir`` so the anchor itself stays honest -- they pass both before and
after the fix.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops

DIR_OPS = ["sobel_dir", "prewitt_dir", "frei_dir"]
# planar-ramp gradient directions in degrees (kept away from the +-180 wrap seam)
ANGLES = [0.0, 30.0, 45.0, 90.0, 135.0, -60.0, -120.0]


def _plane(theta_deg: float, n: int = 48) -> np.ndarray:
    """Plane whose gradient points at ``theta_deg`` (x = cols, y = rows)."""
    t = np.radians(theta_deg)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    return np.cos(t) * xx + np.sin(t) * yy


def _expected(theta_deg: float) -> float:
    """House encoding of a gradient direction: (angle + pi) / (2 pi)."""
    return (np.radians(theta_deg) + np.pi) / (2.0 * np.pi)


def _circ(a, b):
    """Circular distance on the unit circle, expressed in turns, in [0, 0.5]."""
    d = np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64))
    return np.minimum(d, 1.0 - d)


def _core(a: np.ndarray) -> np.ndarray:
    """Interior pixels only -- the boundary mode is not part of the contract."""
    return a[3:-3, 3:-3]


@pytest.mark.parametrize("name", DIR_OPS)
@pytest.mark.parametrize("theta", ANGLES)
def test_dir_ops_report_the_true_gradient_direction(name, theta):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered")
    out = np.asarray(fn(_plane(theta), 0.5, 0.5), np.float64)
    got = _core(out)
    assert np.all(np.isfinite(got)), f"{name} produced non-finite values"
    assert got.min() >= -1e-9 and got.max() <= 1 + 1e-9, (
        f"{name} escaped [0,1]: min={got.min()} max={got.max()}")
    err = _circ(got, _expected(theta))
    assert err.max() < 1e-6, (
        f"{name} direction wrong on a {theta:g} deg planar ramp: "
        f"got {got.mean():.4f} (={got.mean() * 360 - 180:.1f} deg), "
        f"expected {_expected(theta):.4f} (={theta:.1f} deg)")


@pytest.mark.parametrize("theta", ANGLES)
def test_frei_dir_agrees_with_sobel_and_prewitt_dir(theta):
    for name in DIR_OPS:
        if ops.RT.get(name) is None:
            pytest.skip(f"{name} not registered")
    img = _plane(theta)
    ref = _core(np.asarray(ops.RT["sobel_dir"](img, 0.5, 0.5), np.float64))
    for name in ("prewitt_dir", "frei_dir"):
        got = _core(np.asarray(ops.RT[name](img, 0.5, 0.5), np.float64))
        assert _circ(got, ref).max() < 1e-6, (
            f"{name} disagrees with sobel_dir on a {theta:g} deg ramp: "
            f"{got.mean():.4f} vs {ref.mean():.4f}")


def test_frei_dir_axis_convention_matches_siblings():
    """Column ramp -> 0 deg (0.5); row ramp -> +90 deg (0.75), same as the siblings."""
    fn = ops.RT.get("frei_dir")
    if fn is None:
        pytest.skip("frei_dir not registered")
    n = 32
    col = np.tile(np.linspace(0.0, 1.0, n), (n, 1))   # gradient along +x
    row = col.T                                        # gradient along +y
    assert _circ(np.asarray(fn(col, 0.5, 0.5))[n // 2, n // 2], 0.50).max() < 1e-6
    assert _circ(np.asarray(fn(row, 0.5, 0.5))[n // 2, n // 2], 0.75).max() < 1e-6
