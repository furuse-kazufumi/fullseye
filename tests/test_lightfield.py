# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lightfield — closed-form ground truth, sign conventions, and the fail-closed contract.

A light field is the rare case where the "truth" is genuinely available: a
fronto-parallel layer at slope ``s`` puts a scene point at
``x = x_c + s*(u - u_c)`` in every view, exactly, so the refocus sharpness peak,
the EPI line lag, the disparity between extreme views and the metric depth all
have analytic answers. This suite is built on those rather than golden files:

  * the raw <-> light-field re-sort is **bit-identical** both ways;
  * refocusing a single-layer field at its own integer slope with ``edge="wrap"``
    returns the source texture (measured 5.6e-16), and the sharpness peak of a
    slope sweep lands on the true slope and **not** on its negative — the check
    that catches a flipped shift sign;
  * the EPI row lag between the extreme angular rows is exactly ``s*(U-1)`` px;
  * ``Z = focal_px * baseline / |s|`` holds to machine precision;
  * a median synthetic aperture recovers a hidden background **exactly** when
    fewer than half the views are blocked — a property of the median, not a
    tuned threshold;
  * ``lf_plenoptic_design``'s refocusing gain equals the angular resolution,
    the textbook plenoptic result, computed by composing ``optics``.

Scale invariance is tested with two angular grids, two texture scales, two
interpolation orders and two edge modes wherever the physics has a scale, so a
convention slip cannot hide behind one lucky constant.

``TestAdversarial2026_09_01`` at the end pins the three bugs the adversarial
pass found, each with the minimal reproduction that exposed it.
"""
import os
import sys

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import lightfield as LF  # noqa: E402
import opslightfield  # noqa: E402
import optics as O  # noqa: E402

SWEEP = tuple(np.round(np.linspace(-3.0, 3.0, 121), 6))


def _single_layer(slope, angular=(5, 5), shape=(64, 64), sigma=2.0, seed=0):
    """A one-layer field: unambiguous ground truth everywhere."""
    lf, gt = LF.lf_synthesize((slope,), angular, shape, occlusion=False,
                              texture_sigma=sigma, edge="wrap", seed=seed)
    return lf, gt


def _interior(a, m=16):
    return a[m:-m, m:-m]


# --------------------------------------------------------------------------- #
# decode: the re-sort and its exact inverse                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("angular", [(1, 1), (2, 3), (5, 5), (3, 7)])
@pytest.mark.parametrize("spatial", [(8, 8), (7, 11)])
def test_mla_round_trip_is_bit_identical(angular, spatial):
    rng = np.random.default_rng(1)
    lf = rng.random(angular + spatial)
    raw = LF.lf_to_mla(lf)
    assert raw.shape == (spatial[0] * angular[0], spatial[1] * angular[1])
    assert np.array_equal(LF.lf_from_mla(raw, angular), lf)


def test_mla_index_arithmetic_is_the_documented_interleave():
    """raw[t*V + v, s*U + u] == L[v, u, t, s] — the one off-by-one that matters."""
    rng = np.random.default_rng(2)
    lf = rng.random((5, 4, 9, 6))
    raw = LF.lf_to_mla(lf)
    for (v, u, t, s) in [(0, 0, 0, 0), (1, 3, 2, 5), (4, 2, 8, 4), (2, 1, 5, 3)]:
        assert raw[t * 5 + v, s * 4 + u] == lf[v, u, t, s]


def test_mla_decode_refuses_a_non_multiple_size_unless_asked():
    """Silently dropping the partial block moves every microlens centre."""
    with pytest.raises(ValueError, match="not a whole multiple"):
        LF.lf_from_mla(np.zeros((33, 30)), (5, 5))
    cropped = LF.lf_from_mla(np.zeros((33, 30)), (5, 5), crop=True)
    assert cropped.shape == (5, 5, 6, 6)


def test_mla_decode_offset_matches_an_unshifted_decode():
    rng = np.random.default_rng(3)
    lf = rng.random((5, 5, 8, 8))
    raw = LF.lf_to_mla(lf)
    padded = np.zeros((raw.shape[0] + 3, raw.shape[1] + 2))
    padded[3:, 2:] = raw
    assert np.array_equal(LF.lf_from_mla(padded, (5, 5), offset=(3, 2)), lf)


def test_mla_decode_rejects_impossible_offsets():
    with pytest.raises(ValueError, match="outside the"):
        LF.lf_from_mla(np.zeros((10, 10)), (5, 5), offset=(10, 0))
    with pytest.raises(ValueError, match="less than one whole"):
        LF.lf_from_mla(np.zeros((10, 10)), (5, 5), offset=(7, 0))


# --------------------------------------------------------------------------- #
# refocus: the closed-form checks, including the sign                          #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("slope", [-2.0, -1.0, 0.0, 1.0, 2.0])
@pytest.mark.parametrize("angular", [(5, 5), (3, 7)])
def test_refocus_at_the_true_integer_slope_recovers_the_source_texture(slope, angular):
    """Wrapped + integer = a pure np.roll, so the alignment must be exact."""
    lf, _ = _single_layer(slope, angular=angular)
    centre = lf[(angular[0] - 1) // 2, (angular[1] - 1) // 2]
    got = LF.lf_refocus(lf, slope, edge="wrap")
    assert np.abs(got - centre).max() < 1e-14


@pytest.mark.parametrize("slope", [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0])
@pytest.mark.parametrize("sigma", [1.5, 3.0])
def test_refocus_sharpness_peaks_at_the_true_slope(slope, sigma):
    lf, _ = _single_layer(slope, sigma=sigma)
    stack = LF.lf_focal_stack(lf, SWEEP, edge="wrap")
    var = np.array([np.var(_interior(s)) for s in stack])
    assert SWEEP[int(var.argmax())] == pytest.approx(slope, abs=1e-9)


def test_refocus_at_the_negated_slope_is_not_sharp():
    """The check that catches a flipped shift sign — a mirrored refocus looks fine."""
    lf, _ = _single_layer(2.0)
    right = np.var(_interior(LF.lf_refocus(lf, 2.0, edge="wrap")))
    wrong = np.var(_interior(LF.lf_refocus(lf, -2.0, edge="wrap")))
    assert right > 4.0 * wrong


def test_refocus_at_zero_slope_is_exactly_the_mean_of_the_views():
    lf, _ = _single_layer(1.0)
    assert np.allclose(LF.lf_refocus(lf, 0.0), lf.mean(axis=(0, 1)), atol=1e-15)


def test_focal_stack_slices_equal_the_individual_refocus_calls():
    lf, _ = _single_layer(1.0)
    slopes = (-1.5, 0.0, 0.75)
    stack = LF.lf_focal_stack(lf, slopes, edge="wrap")
    assert len(stack) == 3
    for s, img in zip(slopes, stack):
        assert np.array_equal(img, LF.lf_refocus(lf, s, edge="wrap"))


@pytest.mark.parametrize("interp", ["nearest", "linear", "cubic"])
def test_every_interpolation_order_is_exact_on_an_integer_slope(interp):
    lf, _ = _single_layer(1.0)
    got = LF.lf_refocus(lf, 1.0, interp=interp, edge="wrap")
    assert np.abs(got - lf[2, 2]).max() < 1e-12


# --------------------------------------------------------------------------- #
# views and EPI                                                                #
# --------------------------------------------------------------------------- #
def test_subaperture_and_views_agree_with_direct_indexing():
    lf, _ = _single_layer(1.0)
    assert np.array_equal(LF.lf_subaperture(lf, 1, 3), lf[1, 3])
    views = LF.lf_views(lf)
    assert len(views) == 25
    for v in range(5):
        for u in range(5):
            assert np.array_equal(views[v * 5 + u], lf[v, u])
    views[0][0, 0] = 12345.0                       # copies, not views
    assert lf[0, 0, 0, 0] != 12345.0


def test_center_view_is_exact_for_odd_grids_and_states_itself_for_even_ones():
    odd, _ = _single_layer(1.0, angular=(5, 5))
    assert np.array_equal(LF.lf_center_view(odd), odd[2, 2])
    assert np.array_equal(LF.lf_center_view(odd, "nearest"), odd[2, 2])
    even, _ = _single_layer(0.5, angular=(4, 4), shape=(32, 32))
    assert np.allclose(LF.lf_center_view(even, "average"),
                       even[1:3, 1:3].mean(axis=(0, 1)))
    assert np.array_equal(LF.lf_center_view(even, "nearest"), even[1, 1])
    mixed, _ = _single_layer(0.5, angular=(5, 4), shape=(32, 32))
    assert np.allclose(LF.lf_center_view(mixed, "average"),
                       mixed[2, 1:3].mean(axis=0))


def test_epi_is_the_documented_slice():
    lf, _ = _single_layer(1.0, angular=(3, 7))
    h = LF.lf_epi(lf, "u", 10)
    assert h.shape == (7, 64)
    assert np.array_equal(h, lf[1, :, 10, :])
    v = LF.lf_epi(lf, "v", 20)
    assert v.shape == (3, 64)
    assert np.array_equal(v, lf[:, 3, :, 20])
    assert np.array_equal(LF.lf_epi(lf, "u", 10, view=0), lf[0, :, 10, :])


@pytest.mark.parametrize("slope", [1.0, 2.0, -1.0])
def test_epi_row_lag_between_extreme_views_is_slope_times_baseline(slope):
    """The defining property of an EPI: the line gradient *is* the disparity."""
    lf, _ = _single_layer(slope, angular=(5, 5))
    epi = LF.lf_epi(lf, "u", 20)
    a = epi[0] - epi[0].mean()
    b = epi[4] - epi[4].mean()
    corr = np.correlate(b, np.tile(a, 2), "valid")[:64]
    lag = int(corr.argmax())
    expect = int(round(slope * 4)) % 64
    assert lag == expect


# --------------------------------------------------------------------------- #
# aperture / synthetic aperture                                                #
# --------------------------------------------------------------------------- #
def test_aperture_mask_normalizes_and_selects_what_it_says():
    m = LF.lf_aperture_mask((5, 5), "circle", radius=1.0)
    assert m.sum() == pytest.approx(1.0, rel=1e-15)
    assert int((m > 0).sum()) == 5                      # the plus-shaped 4-neighbourhood
    m0 = LF.lf_aperture_mask((5, 5), "circle", radius=0.0)
    assert int((m0 > 0).sum()) == 1 and m0[2, 2] == pytest.approx(1.0)
    sq = LF.lf_aperture_mask((5, 5), "square", radius=1.0, normalize=False)
    assert int(sq.sum()) == 9
    ann = LF.lf_aperture_mask((5, 5), "annulus", radius=2.0, inner=2.0 - 1e-9,
                              normalize=False)
    assert int(ann.sum()) == 4                          # the four corners, r = 2*sqrt(2)...
    gau = LF.lf_aperture_mask((5, 5), "gaussian", radius=2.0, sigma=1.0)
    assert gau.sum() == pytest.approx(1.0, rel=1e-15)
    assert gau[2, 2] == gau.max()


def test_synthetic_aperture_with_a_uniform_mask_equals_plain_refocus():
    lf, _ = _single_layer(1.0)
    flat = LF.lf_aperture_mask((5, 5), "square", radius=10.0)
    got = LF.lf_synthetic_aperture(lf, 1.0, flat, edge="wrap")
    assert np.allclose(got, LF.lf_refocus(lf, 1.0, edge="wrap"), atol=1e-14)


def test_synthetic_aperture_radius_zero_is_the_single_centre_view():
    lf, _ = _single_layer(1.0)
    pin = LF.lf_aperture_mask((5, 5), "circle", radius=0.0)
    assert np.allclose(LF.lf_synthetic_aperture(lf, 0.0, pin), lf[2, 2],
                       atol=1e-15)


def _occluded_field(coverage=0.25, occ_slope=3.0, n=9, size=64, seed=7):
    """Background at slope 0 behind a blob occluder at *occ_slope*, built by hand.

    Everything is an integer roll, so the unoccluded views carry the background
    sample *exactly* and the median has an analytic answer.
    """
    rng = np.random.default_rng(seed)
    bg = gaussian_filter(rng.standard_normal((size, size)), 2.0, mode="wrap")
    bg = (bg - bg.min()) / (bg.max() - bg.min())
    blob = gaussian_filter(rng.standard_normal((size, size)), 2.0, mode="wrap")
    mask = blob >= np.quantile(blob, 1.0 - coverage)
    c = (n - 1) / 2.0
    lf = np.empty((n, n, size, size))
    blocked = np.zeros((size, size))
    for v in range(n):
        for u in range(n):
            a = np.roll(mask, (int(occ_slope * (v - c)), int(occ_slope * (u - c))),
                        axis=(0, 1))
            lf[v, u] = np.where(a, 0.95, bg)
            blocked += a
    return lf, bg, mask, blocked / (n * n)


def test_median_synthetic_aperture_recovers_a_hidden_background_exactly():
    """Fewer than half the views blocked => the median *is* the background sample."""
    lf, bg, mask, frac = _occluded_field()
    assert frac[mask].max() < 0.5              # the precondition, asserted not assumed
    med = LF.lf_synthetic_aperture(lf, 0.0, reduce="median", edge="wrap")
    mean = LF.lf_synthetic_aperture(lf, 0.0, reduce="mean", edge="wrap")
    assert np.abs(med[mask] - bg[mask]).max() < 1e-12         # exact, not "better"
    assert np.sqrt(((mean - bg)[mask] ** 2).mean()) > 0.1     # the mean is smeared
    centre = lf[4, 4]
    assert np.sqrt(((centre - bg)[mask] ** 2).mean()) > 0.1   # so is the raw view


def test_median_synthetic_aperture_loses_its_guarantee_past_half_coverage():
    """Honest: the see-through is a majority argument, and it can be outvoted."""
    lf, bg, mask, frac = _occluded_field(coverage=0.35)
    assert frac[mask].max() > 0.5
    med = LF.lf_synthetic_aperture(lf, 0.0, reduce="median", edge="wrap")
    assert np.abs(med[mask] - bg[mask]).max() > 0.1


@pytest.mark.parametrize("reduce", ["mean", "median", "max", "min"])
def test_every_reducer_returns_a_plain_finite_image(reduce):
    lf, _ = _single_layer(1.0)
    got = LF.lf_synthetic_aperture(lf, 0.5, reduce=reduce)
    assert got.shape == (64, 64) and np.isfinite(got).all()
    lo = LF.lf_synthetic_aperture(lf, 0.5, reduce="min")
    hi = LF.lf_synthetic_aperture(lf, 0.5, reduce="max")
    assert (lo <= got + 1e-12).all() and (got <= hi + 1e-12).all()


# --------------------------------------------------------------------------- #
# depth                                                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("slope", [0.0, 0.5, 1.0, 1.5, 2.0, -1.0])
@pytest.mark.parametrize("sigma", [1.5, 3.0, 5.0])
def test_depth_from_focus_argmax_lands_exactly_on_the_true_slope(slope, sigma):
    """18 combinations, and the sweep grid contains the answer in all of them."""
    lf, _ = _single_layer(slope, sigma=sigma)
    got, conf = LF.lf_depth_from_focus(lf, SWEEP, edge="wrap", subpixel=False)
    assert float(np.median(got)) == pytest.approx(slope, abs=1e-9)
    assert (conf >= 0.0).all()


@pytest.mark.parametrize("measure", ["laplacian", "variance", "gradient"])
def test_every_focus_measure_finds_the_same_plane(measure):
    lf, _ = _single_layer(1.0)
    got, _ = LF.lf_depth_from_focus(lf, SWEEP, measure=measure, edge="wrap",
                                    subpixel=False)
    assert float(np.median(got)) == pytest.approx(1.0, abs=1e-9)


def test_depth_from_focus_subpixel_reaches_between_the_sweep_samples():
    """A true slope halfway between two samples: the grid cannot express it."""
    lf, _ = _single_layer(0.75, sigma=3.0)
    coarse = (-1.0, -0.5, 0.0, 0.5, 1.0, 1.5)
    grid, _ = LF.lf_depth_from_focus(lf, coarse, edge="wrap", subpixel=False)
    fine, _ = LF.lf_depth_from_focus(lf, coarse, edge="wrap", subpixel=True)
    assert set(np.unique(grid)).issubset(set(coarse))         # on-grid only
    assert not set(np.unique(fine)).issubset(set(coarse))     # off-grid allowed
    assert abs(float(np.median(fine)) - 0.75) < abs(float(np.median(grid)) - 0.75)


def test_depth_from_focus_confidence_is_zero_on_a_textureless_field():
    flat = np.full((3, 3, 16, 16), 0.42)
    got, conf = LF.lf_depth_from_focus(flat, (-1.0, 0.0, 1.0))
    assert np.isfinite(got).all() and np.isfinite(conf).all()
    assert float(conf.max()) < 1e-12          # nothing to be confident about


@pytest.mark.parametrize("slope", [-1.0, 0.0, 1.0])
def test_epi_slope_recovers_an_integer_slope_and_its_sign(slope):
    lf, _ = _single_layer(slope, sigma=3.0)
    got, energy = LF.lf_epi_slope(lf)
    assert float(np.median(_interior(got))) == pytest.approx(slope, abs=2e-3)
    assert (energy >= 0.0).all()


def test_epi_slope_bias_at_large_slope_is_the_documented_one():
    """Pinning the honest disclosure: this estimator under-reads past |s| = 1."""
    rough, _ = _single_layer(2.0, sigma=1.5)
    smooth, _ = _single_layer(2.0, sigma=5.0)
    r = float(np.median(_interior(LF.lf_epi_slope(rough)[0])))
    s = float(np.median(_interior(LF.lf_epi_slope(smooth)[0])))
    assert r == pytest.approx(1.4614, abs=5e-3)      # 27% low, as documented
    assert s == pytest.approx(1.9482, abs=5e-3)
    assert r < s < 2.0                               # smoother texture, less bias


def test_epi_slope_is_zero_where_there_is_no_texture():
    flat = np.zeros((3, 3, 16, 16))
    got, energy = LF.lf_epi_slope(flat)
    assert np.array_equal(got, np.zeros((16, 16)))
    assert float(energy.max()) == 0.0


@pytest.mark.parametrize("f_px", [500.0, 1000.0])
@pytest.mark.parametrize("base", [0.5, 2.0])
def test_disparity_to_depth_is_the_closed_form_and_ignores_the_sign(f_px, base):
    s = np.array([[0.5, 1.0], [2.0, 4.0]])
    got = LF.lf_disparity_to_depth(s, f_px, base)
    assert np.allclose(got, f_px * base / s, rtol=1e-15)
    assert np.array_equal(got, LF.lf_disparity_to_depth(-s, f_px, base))


def test_disparity_to_depth_refuses_the_zero_parallax_pole_by_default():
    s = np.array([[1.0, 0.0], [2.0, 1e-9]])
    with pytest.raises(ValueError, match="below min_slope"):
        LF.lf_disparity_to_depth(s, 1000.0, 1.0)
    got = LF.lf_disparity_to_depth(s, 1000.0, 1.0, far_depth=1e6)
    assert got[0, 1] == 1e6 and got[1, 1] == 1e6
    assert got[0, 0] == pytest.approx(1000.0) and got[1, 0] == pytest.approx(500.0)


def test_depth_pipeline_end_to_end_hits_the_analytic_distance():
    """synthesize(known slope) -> depth_from_focus -> metric depth."""
    lf, _ = _single_layer(1.0, sigma=3.0)
    slope, _ = LF.lf_depth_from_focus(lf, SWEEP, edge="wrap", subpixel=False)
    depth = LF.lf_disparity_to_depth(slope, focal_px=800.0, baseline=1.5)
    assert float(np.median(depth)) == pytest.approx(800.0 * 1.5 / 1.0, rel=1e-9)


# --------------------------------------------------------------------------- #
# all-in-focus                                                                 #
# --------------------------------------------------------------------------- #
def test_all_in_focus_on_a_single_layer_is_that_layer_refocused():
    lf, gt = _single_layer(1.0)
    got = LF.lf_all_in_focus(lf, gt, edge="wrap")
    assert np.array_equal(got, LF.lf_refocus(lf, 1.0, edge="wrap"))


def test_all_in_focus_beats_every_single_refocus_slice():
    lf, _ = LF.lf_synthesize((2.0, 0.0), (7, 7), (64, 64), occlusion=True,
                             coverage=0.4, edge="wrap", seed=5)
    levels = tuple(np.round(np.linspace(-1.0, 3.0, 17), 6))
    slope, _ = LF.lf_depth_from_focus(lf, levels, edge="wrap", subpixel=False)
    fused = LF.lf_all_in_focus(lf, slope, levels=levels, edge="wrap")

    def sharp(x):
        gy, gx = np.gradient(x)
        return float((gy ** 2 + gx ** 2).mean())

    best = max(sharp(s) for s in LF.lf_focal_stack(lf, levels, edge="wrap"))
    assert sharp(fused) > best


def test_all_in_focus_quantises_a_continuous_map_to_n_levels():
    lf, _ = _single_layer(1.0)
    cont = np.random.default_rng(0).random((64, 64))     # 4096 distinct values
    got = LF.lf_all_in_focus(lf, cont, n_levels=8, edge="wrap")
    assert got.shape == (64, 64) and np.isfinite(got).all()
    with pytest.raises(ValueError, match="n_levels"):
        LF.lf_all_in_focus(lf, cont, n_levels=0)


# --------------------------------------------------------------------------- #
# stats and design (composition with optics)                                   #
# --------------------------------------------------------------------------- #
def test_stats_reports_the_geometry_it_promises():
    lf, _ = _single_layer(1.0, angular=(4, 5), shape=(32, 48))
    st = LF.lf_stats(lf)
    assert (st["angular_v"], st["angular_u"]) == (4, 5)
    assert (st["height"], st["width"]) == (32, 48)
    assert st["n_views"] == 20
    assert st["center_v"] == 1.5 and st["center_u"] == 2.0
    assert st["center_is_a_view"] is False
    assert st["baseline_views"] == (3, 4)
    assert st["max_slope_px"] == pytest.approx(32.0 / 4.0)
    assert st["min"] == pytest.approx(lf.min()) and st["max"] == pytest.approx(lf.max())
    single = LF.lf_stats(np.ones((1, 1, 8, 8)))
    assert single["center_is_a_view"] is True
    assert single["max_slope_px"] == 8.0


@pytest.mark.parametrize("pitch,expect", [(20.7, 6), (27.6, 8), (34.5, 10)])
def test_plenoptic_design_refocus_gain_equals_the_angular_resolution(pitch, expect):
    d = LF.lf_plenoptic_design(50.0, 8.0, 300.0, 3.45, pitch, (2048, 2448))
    assert d["angular_u"] == expect
    assert d["refocus_gain"] == pytest.approx(expect, rel=2e-3)
    assert d["n_views"] == expect * expect
    assert d["spatial_h"] == 2048 // expect and d["spatial_w"] == 2448 // expect


def test_plenoptic_design_composes_optics_rather_than_re_deriving_it():
    d = LF.lf_plenoptic_design(50.0, 8.0, 300.0, 3.45, 27.6, (2048, 2448))
    lens = O.thin_lens(50.0, 300.0)
    assert d["image_mm"] == pytest.approx(lens["image_mm"], rel=1e-15)
    assert d["magnification"] == pytest.approx(lens["magnification"], rel=1e-15)
    assert d["working_distance_mm"] == pytest.approx(lens["working_distance_mm"])
    assert d["dof_pixel_mm"] == pytest.approx(
        O.depth_of_field(50.0, 8.0, 300.0, 3.45e-3)["depth_mm"], rel=1e-15)
    assert d["dof_refocus_mm"] == pytest.approx(
        O.depth_of_field(50.0, 8.0, 300.0, 27.6e-3)["depth_mm"], rel=1e-15)
    assert d["aperture_mm"] == pytest.approx(50.0 / 8.0, rel=1e-15)
    assert d["baseline_mm"] == pytest.approx((50.0 / 8.0) / 7.0, rel=1e-15)
    assert d["pitch_is_integer"] is True
    # depth precision = Z^2 * dp / (f_px * b), the derivative of Z = f*b/d
    f_px = 50.0 / 27.6e-3
    assert d["depth_precision_mm"] == pytest.approx(
        300.0 ** 2 * 0.1 / (f_px * d["baseline_mm"]), rel=1e-12)


def test_plenoptic_design_reports_a_non_integer_microlens_pitch():
    d = LF.lf_plenoptic_design(50.0, 8.0, 300.0, 3.45, 25.0, (2048, 2448))
    assert d["pitch_is_integer"] is False
    assert d["angular_u"] == 7
    assert d["angular_exact"] == pytest.approx(25.0 / 3.45)


# --------------------------------------------------------------------------- #
# fail-closed contract                                                         #
# --------------------------------------------------------------------------- #
class TestFailClosed:
    def setup_method(self):
        self.lf, _ = _single_layer(1.0, angular=(3, 3), shape=(16, 16))

    @pytest.mark.parametrize("bad,msg", [
        ("1.0", "string"), (True, "bool"), (1 + 2j, "complex"),
        (np.nan, "finite"), (np.inf, "finite"), (1e9, "cap"),
    ])
    def test_slope_rejects_every_silent_coercion(self, bad, msg):
        with pytest.raises(ValueError, match=msg):
            LF.lf_refocus(self.lf, bad)

    def test_light_field_shape_and_dtype_are_exact(self):
        with pytest.raises(ValueError, match="4-D light field"):
            LF.lf_refocus(np.zeros((3, 16, 16)))
        with pytest.raises(ValueError, match="complex"):
            LF.lf_refocus(np.zeros((2, 2, 4, 4), dtype=complex))
        with pytest.raises(ValueError, match="non-finite"):
            LF.lf_refocus(np.full((2, 2, 4, 4), np.nan))
        with pytest.raises(ValueError, match="masked"):
            LF.lf_refocus(np.ma.masked_invalid(np.full((2, 2, 4, 4), np.nan)))
        with pytest.raises(ValueError, match="empty axis"):
            LF.lf_refocus(np.zeros((0, 2, 4, 4)))

    def test_allocation_caps_fail_closed(self):
        with pytest.raises(ValueError, match="MAX_LF_ELEMENTS"):
            LF.lf_synthesize((0.0,), (64, 64), (512, 512))
        with pytest.raises(ValueError, match="MAX_ANGULAR"):
            LF.lf_synthesize((0.0,), (128, 5))
        with pytest.raises(ValueError, match="MAX_STACK_SLICES"):
            LF.lf_focal_stack(self.lf, np.linspace(-1, 1, 5000))
        with pytest.raises(ValueError, match="MAX_STACK_ELEMENTS"):
            LF.lf_focal_stack(np.zeros((2, 2, 4096, 1024)), np.linspace(-1, 1, 200))
        with pytest.raises(ValueError, match="MAX_SPATIAL"):
            LF.lf_from_mla(np.zeros((10000, 12)), (2, 2))

    def test_opaque_aperture_is_refused_not_returned_as_zeros(self):
        with pytest.raises(ValueError, match="selects no view"):
            LF.lf_aperture_mask((4, 4), "circle", radius=0.0)
        with pytest.raises(ValueError, match="selects no view"):
            LF.lf_synthetic_aperture(self.lf, 0.0, np.zeros((3, 3)))
        with pytest.raises(ValueError, match="negative weight"):
            LF.lf_synthetic_aperture(self.lf, 0.0, -np.ones((3, 3)))
        with pytest.raises(ValueError, match="inner"):
            LF.lf_aperture_mask((5, 5), "annulus", radius=1.0, inner=1.0)
        with pytest.raises(ValueError, match="sigma"):
            LF.lf_aperture_mask((5, 5), "gaussian", sigma=0.0)

    def test_index_and_shape_mismatches_are_explicit(self):
        with pytest.raises(ValueError, match="v must be in"):
            LF.lf_subaperture(self.lf, -1, 0)
        with pytest.raises(ValueError, match="u must be in"):
            LF.lf_subaperture(self.lf, 0, 3)
        with pytest.raises(ValueError, match="index"):
            LF.lf_epi(self.lf, "u", 16)
        with pytest.raises(ValueError, match="view"):
            LF.lf_epi(self.lf, "u", 0, view=3)
        with pytest.raises(ValueError, match="does not match"):
            LF.lf_synthetic_aperture(self.lf, 0.0, np.ones((5, 5)))
        with pytest.raises(ValueError, match="does not match"):
            LF.lf_all_in_focus(self.lf, np.zeros((8, 8)), levels=(0.0,))

    def test_odd_window_is_required(self):
        with pytest.raises(ValueError, match="must be odd"):
            LF.lf_epi_slope(self.lf, window=8)
        with pytest.raises(ValueError, match="must be odd"):
            LF.lf_depth_from_focus(self.lf, (0.0,), window=4)

    @pytest.mark.parametrize("kw,val", [
        ("interp", "lanczos"), ("edge", "mirror"),
    ])
    def test_unknown_kernels_are_named(self, kw, val):
        with pytest.raises(ValueError, match="unknown"):
            LF.lf_refocus(self.lf, 0.0, **{kw: val})

    def test_unknown_enumerations_are_named(self):
        with pytest.raises(ValueError, match="unknown reduce"):
            LF.lf_synthetic_aperture(self.lf, 0.0, reduce="sum")
        with pytest.raises(ValueError, match="unknown shape"):
            LF.lf_aperture_mask((3, 3), "hexagon")
        with pytest.raises(ValueError, match="unknown measure"):
            LF.lf_depth_from_focus(self.lf, (0.0,), measure="tenengrad")
        with pytest.raises(ValueError, match="unknown axis"):
            LF.lf_epi(self.lf, "diagonal", 0)

    def test_slopes_must_be_a_non_empty_sequence(self):
        with pytest.raises(ValueError, match="must be a sequence"):
            LF.lf_focal_stack(self.lf, 1.0)
        with pytest.raises(ValueError, match="is empty"):
            LF.lf_focal_stack(self.lf, [])
        with pytest.raises(ValueError, match="sequence of layer slopes"):
            LF.lf_synthesize(1.0)
        with pytest.raises(ValueError, match="is empty"):
            LF.lf_synthesize([])

    def test_design_refuses_the_unphysical_configurations(self):
        with pytest.raises(ValueError, match="not a light field"):
            LF.lf_plenoptic_design(mla_pitch_um=5.0, pixel_um=3.45)
        with pytest.raises(ValueError, match="focal_mm must be > 0"):
            LF.lf_plenoptic_design(focal_mm=0.0)
        with pytest.raises(ValueError, match="images at infinity"):
            LF.lf_plenoptic_design(focal_mm=50.0, object_mm=50.0)
        with pytest.raises(ValueError, match="ratio of\n?\\s*infinities|unbounded"):
            LF.lf_plenoptic_design(object_mm=1e7)

    def test_synthesize_rejects_a_degenerate_scene(self):
        with pytest.raises(ValueError, match="coverage"):
            LF.lf_synthesize((0.0,), coverage=0.0)
        with pytest.raises(ValueError, match="texture_sigma"):
            LF.lf_synthesize((0.0,), texture_sigma=0.0)
        with pytest.raises(ValueError, match="constant"):
            LF.lf_synthesize((0.0,), shape=(8, 8), texture_sigma=400.0)


# --------------------------------------------------------------------------- #
# registry                                                                     #
# --------------------------------------------------------------------------- #
class TestRegistry:
    def test_every_catalogued_op_has_an_implementation(self):
        assert opslightfield.missing() == []
        assert len(opslightfield.OPSLIGHTFIELD) == 17
        assert set(opslightfield.list_ops()) == set(LF.LIGHTFIELD)
        assert set(LF.LIGHTFIELD) == set(LF.__all__) & set(LF.LIGHTFIELD)

    def test_categories_partition_the_catalogue(self):
        seen = []
        for c in opslightfield.categories():
            seen.extend(opslightfield.list_ops(c))
        assert sorted(seen) == sorted(opslightfield.list_ops())
        assert len(seen) == len(set(seen))

    def test_call_returns_the_declared_type_for_every_op(self):
        lf = opslightfield.call("lf_synthesize", (0.0, 1.0), (3, 3), (32, 32))
        rng = np.random.default_rng(0)
        img = rng.random((32, 32))
        args = {
            "lf_synthesize": ((0.0,), (3, 3), (32, 32)),
            "lf_from_mla": (opslightfield.call("lf_to_mla", lf), (3, 3)),
            "lf_to_mla": (lf,),
            "lf_stats": (lf,),
            "lf_subaperture": (lf,),
            "lf_center_view": (lf,),
            "lf_views": (lf,),
            "lf_epi": (lf,),
            "lf_refocus": (lf,),
            "lf_focal_stack": (lf,),
            "lf_aperture_mask": ((3, 3),),
            "lf_synthetic_aperture": (lf,),
            "lf_depth_from_focus": (lf,),
            "lf_epi_slope": (lf,),
            "lf_disparity_to_depth": (img + 0.5,),
            "lf_all_in_focus": (lf, img),
            "lf_plenoptic_design": (),
        }
        checks = {
            "lightfield": lambda v: isinstance(v, np.ndarray) and v.ndim == 4,
            "image2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
            "depth": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
            "images": lambda v: isinstance(v, (list, tuple)) and all(
                isinstance(x, np.ndarray) and x.ndim == 2 for x in v),
            "table": lambda v: isinstance(v, (list, dict)),
        }
        for name in opslightfield.list_ops():
            declared = opslightfield.info(name)["out"]
            got = opslightfield.call(name, *args[name])
            assert checks[declared](got), (name, declared, type(got))

    def test_result_adapters_cover_exactly_the_tuple_returning_ops(self):
        tuple_ops = set()
        for name in opslightfield.list_ops():
            fn = opslightfield.get(name)
            if name == "lf_synthesize":
                out = fn((0.0,), (3, 3), (16, 16))
            elif name in ("lf_depth_from_focus", "lf_epi_slope"):
                lf, _ = LF.lf_synthesize((0.0,), (3, 3), (16, 16))
                out = fn(lf) if name == "lf_epi_slope" else fn(lf, (0.0, 1.0))
            else:
                continue
            if isinstance(out, tuple):
                tuple_ops.add(name)
        assert tuple_ops == set(opslightfield.RESULT_ADAPTERS)

    def test_declared_input_types_use_the_existing_vocabulary_plus_lightfield(self):
        known = {"image2d", "images", "depth", "table", "lightfield"}
        for name in opslightfield.list_ops():
            m = opslightfield.info(name)
            assert set(m["in"]) <= known, (name, m["in"])
            assert m["out"] in known, (name, m["out"])


# --------------------------------------------------------------------------- #
# bugs the 2026-09-01 adversarial pass found (minimal reproductions)           #
# --------------------------------------------------------------------------- #
class TestAdversarial2026_09_01:
    def test_disparity_to_depth_no_longer_returns_a_silent_infinity(self):
        """focal_px*baseline/|s| overflowed float64 and handed back +inf, silently."""
        s = np.full((3, 3), 1e-300)
        with pytest.raises(ValueError, match="overflowed float64"):
            LF.lf_disparity_to_depth(s, 1e300, 1e300, min_slope=1e-300)

    def test_epi_slope_names_the_degenerate_shape_instead_of_leaking_numpy(self):
        """W == 1 left np.gradient to raise 'Shape of array too small'."""
        with pytest.raises(ValueError, match="no direction carries slope"):
            LF.lf_epi_slope(np.zeros((3, 1, 1, 8)))
        # W == 1 with a usable vertical direction still works (only the
        # horizontal term is dropped) — the fix is a per-direction gate, not a
        # blanket refusal.
        got, energy = LF.lf_epi_slope(np.zeros((3, 3, 8, 1)))
        assert got.shape == (8, 1) and np.isfinite(got).all()

    def test_from_mla_bounds_the_decoded_spatial_size(self):
        """_require_image has no element cap, so lf_from_mla had none either."""
        with pytest.raises(ValueError, match="MAX_SPATIAL"):
            LF.lf_from_mla(np.zeros((10000, 12)), (2, 2))
        ok = LF.lf_from_mla(np.zeros((4096, 8)), (2, 2))
        assert ok.shape == (2, 2, 2048, 4)
