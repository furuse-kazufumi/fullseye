"""lf_epi_slope is unbiased over its stated range (fix 2026-11-03).

Root cause of the old bias: the angular central difference spans a
displacement of ``2 s`` px while the spatial one spans 2 px, so for a texture
component of angular frequency ``w`` the old estimator read
``sin(w s) / sin(w)`` instead of ``s`` — exact only at ``|s|`` in {0, 1}
(recipe finding: -1.388 for a true -1.5). The fix shears the light field by
an integer slope and measures only the residual (Wanner & Goldluecke 2012 /
2014 handle large disparities by shearing), with a matched discretisation.

Every truth here is closed form: lf_synthesize displaces each view by exactly
``s * (u - u_c)``, and a pure cosine has a known slope everywhere.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import lightfield as LF


def _single_layer(slope, angular=(5, 5), shape=(64, 64), sigma=2.0, seed=0):
    return LF.lf_synthesize((slope,), angular, shape, occlusion=False,
                            texture_sigma=sigma, edge="wrap", seed=seed)


def _median_interior(a, m=16):
    return float(np.median(a[m:-m, m:-m]))


#: Stated tolerance (px per view) over |s| <= 3 for 5x5 views; measured worst
#: 0.0054 px over sigma 1..5 and windows 5..15.
TOL = 0.01


@pytest.mark.parametrize("sigma", [1.0, 1.5, 2.0, 5.0])
@pytest.mark.parametrize("slope", [-3.0, -2.5, -2.0, -1.5, -1.0, -0.5, -0.25,
                                   0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0])
def test_slope_is_unbiased_over_plus_minus_three(slope, sigma):
    lf, _ = _single_layer(slope, sigma=sigma)
    got = _median_interior(LF.lf_epi_slope(lf)[0])
    assert got == pytest.approx(slope, abs=TOL)


def test_the_recipe_finding_minus_one_point_five_is_fixed():
    """The coverage recipe's exact input: default lf_synthesize at s = -1.5."""
    lf, gt = LF.lf_synthesize((-1.5,), (5, 5), (64, 64))
    got, energy = LF.lf_epi_slope(lf)
    assert _median_interior(got) == pytest.approx(-1.5, abs=TOL)   # old: -1.388
    assert (energy >= 0.0).all()
    depth = LF.lf_disparity_to_depth(np.median(got[16:-16, 16:-16]), 1000.0, 1.0)
    assert float(depth[0]) == pytest.approx(1000.0 / 1.5, rel=0.01)


@pytest.mark.parametrize("window", [5, 9, 15])
def test_no_window_size_reintroduces_the_bias(window):
    lf, _ = _single_layer(1.5, sigma=2.0)
    got = _median_interior(LF.lf_epi_slope(lf, window=window)[0])
    assert got == pytest.approx(1.5, abs=TOL)


@pytest.mark.parametrize("angular,tol", [((3, 3), 0.015), ((4, 4), 0.01),
                                         ((9, 9), 0.01), ((5, 1), 0.01),
                                         ((1, 6), 0.015)])
@pytest.mark.parametrize("slope", [-2.5, -1.5, 0.5, 2.0])
def test_every_view_count_including_even_and_one_direction(angular, tol, slope):
    lf, _ = _single_layer(slope, angular=angular, sigma=1.5)
    got = _median_interior(LF.lf_epi_slope(lf)[0])
    assert got == pytest.approx(slope, abs=tol)


@pytest.mark.parametrize("slope", [-1.5, 0.5, 1.5, 2.5])
def test_pure_cosine_meets_the_closed_form_bound(slope):
    """One frequency w = 0.6 rad/px: the residual |r| <= 1/2 is read as
    2 tan(w r / 2) / w, so |error| <= |2 tan(w/4)/w - 1/2| = 0.0038 px.
    The old estimator read sin(w s)/sin(w): 1.387 for s = 1.5."""
    w, U, W, H = 0.6, 7, 96, 8
    uc = (U - 1) / 2.0
    x = np.arange(W)
    lf = np.empty((1, U, H, W))
    for u in range(U):
        lf[0, u] = 0.5 + 0.4 * np.cos(w * (x - slope * (u - uc)))[None, :]
    got = float(np.median(LF.lf_epi_slope(lf)[0][:, 24:-24]))
    # every slope here is a half-integer, so |r| = 1/2 exactly and the error
    # is the closed form itself (to the 1e-4 of a sampled Gaussian derivative)
    predicted = abs(2.0 * math.tan(w * 0.25) / w - 0.5)
    assert abs(got - slope) == pytest.approx(predicted, abs=1e-4)
    assert abs(got - slope) < 0.004


def test_occluding_front_layer_reads_its_true_slope():
    lf, gt = LF.lf_synthesize((0.5, -1.5), (5, 5), (96, 96), occlusion=True,
                              texture_sigma=2.0, edge="wrap", seed=0)
    from scipy import ndimage as ndi
    got = LF.lf_epi_slope(lf)[0]
    front = ndi.binary_erosion(gt == -1.5, iterations=6)
    assert float(np.median(got[front])) == pytest.approx(-1.5, abs=TOL)   # old: -1.234


def test_valid_range_limit_is_the_documented_one():
    """Honest disclosure pinned: the shear ladder starts at k = 0, so an
    aliased texture (sigma 1 px) is followed to |s| = 5 and lost at 6, while a
    sigma 2 texture is followed to 8."""
    def read(s, sigma):
        lf, _ = _single_layer(s, shape=(96, 96), sigma=sigma, seed=1)
        return _median_interior(LF.lf_epi_slope(lf)[0], 24)
    assert read(5.0, 1.0) == pytest.approx(5.0, abs=TOL)
    assert abs(read(6.0, 1.0) - 6.0) > 1.0                 # documented failure
    assert read(8.0, 2.0) == pytest.approx(8.0, abs=TOL)


def test_textureless_field_still_reports_zero_slope_and_zero_energy():
    got, energy = LF.lf_epi_slope(np.full((5, 5, 24, 24), 0.3))
    assert np.array_equal(got, np.zeros((24, 24)))
    assert float(energy.max()) < 1e-20
