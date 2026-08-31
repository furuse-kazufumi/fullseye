# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""optics — closed-form ground truth, sign conventions, and the fail-closed contract.

Every operator in :mod:`optics` is a *calculation with a known answer*, so this
suite is built around exact identities rather than golden files: the thin-lens
reciprocal, ``det(ABCD) = 1`` in a single medium, the first Airy zero at
``1.2197*lambda*N``, the diffraction MTF's textbook 0.391 at half cutoff, a
Gaussian PSF's ``exp(-2*pi^2*sigma^2*f^2)``, Malus's law, and — the check that
actually catches sign slips — the Jones and Mueller families agreeing on the
same Stokes vector for every element kind.

Scale invariance is tested in two independent ways wherever the physics has a
scale (two f-numbers, two wavelengths, two pixel pitches, two grid sizes), so a
unit mix-up cannot hide behind a single lucky constant.

The classes at the end pin the bugs the 2026-09-01 adversarial pass found, each
with the minimal reproduction that exposed it.
"""
import os
import sys
import warnings

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import optics as O  # noqa: E402
import opsoptics  # noqa: E402


# --------------------------------------------------------------------------- #
# geometric: thin lens                                                         #
# --------------------------------------------------------------------------- #
def test_thin_lens_reproduces_the_gaussian_conjugate_equation():
    r = O.thin_lens(50.0, 200.0)
    assert r["image_mm"] == pytest.approx(200.0 / 3.0, rel=1e-12)
    assert r["magnification"] == pytest.approx(-1.0 / 3.0, rel=1e-12)
    assert r["working_distance_mm"] == pytest.approx(200.0 + 200.0 / 3.0, rel=1e-12)


@pytest.mark.parametrize("f", [10.0, 50.0, 135.0])
@pytest.mark.parametrize("ratio", [1.5, 2.0, 3.0, 10.0, 100.0])
def test_thin_lens_satisfies_1_over_f_at_every_scale(f, ratio):
    """1/f = 1/s_o + 1/s_i to machine precision, for two decades of focal length."""
    s_o = f * ratio
    r = O.thin_lens(f, s_o)
    assert 1.0 / f - 1.0 / s_o - 1.0 / r["image_mm"] == pytest.approx(0.0, abs=1e-12)


def test_thin_lens_1to1_conjugate_is_at_2f():
    r = O.thin_lens(50.0, 100.0)
    assert r["image_mm"] == pytest.approx(100.0, rel=1e-12)
    assert r["magnification"] == pytest.approx(-1.0, rel=1e-12)


def test_thin_lens_sign_convention_virtual_images():
    """Negative image distance = virtual image; positive magnification = upright."""
    diverging = O.thin_lens(-50.0, 200.0)          # a negative lens: always virtual
    assert diverging["image_mm"] == pytest.approx(-40.0, rel=1e-12)
    assert diverging["magnification"] > 0          # upright
    magnifier = O.thin_lens(50.0, 25.0)            # object inside the focal length
    assert magnifier["image_mm"] == pytest.approx(-50.0, rel=1e-12)
    assert magnifier["magnification"] == pytest.approx(2.0, rel=1e-12)


def test_thin_lens_refuses_the_degenerate_cases():
    with pytest.raises(ValueError, match="focal_mm must not be 0"):
        O.thin_lens(0.0, 200.0)
    with pytest.raises(ValueError, match="images at infinity"):
        O.thin_lens(50.0, 50.0)                    # object at the front focus
    with pytest.raises(ValueError, match="object_mm must be > 0"):
        O.thin_lens(50.0, 0.0)
    with pytest.raises(ValueError, match="must be finite"):
        O.thin_lens(50.0, float("nan"))


# --------------------------------------------------------------------------- #
# geometric: ABCD ray transfer                                                 #
# --------------------------------------------------------------------------- #
def test_abcd_free_space_is_the_textbook_matrix():
    m = O.abcd_matrix([("free", 100.0)])
    assert np.allclose(m, [[1.0, 100.0], [0.0, 1.0]], atol=0)


@pytest.mark.parametrize("system", [
    [("free", 100.0)],
    [("lens", 50.0), ("free", 50.0)],
    [("free", 25.0), ("lens", -75.0), ("free", 10.0), ("mirror", 200.0)],
    [("interface", 1.0, 1.5), ("free", 10.0), ("interface", 1.5, 1.0)],
])
def test_abcd_determinant_is_one_in_a_single_medium(system):
    """det(M) = n_in/n_out, so it is exactly 1 whenever the system starts and
    ends in the same medium — the cheapest self-check an ABCD matrix has."""
    m = O.abcd_matrix(system)
    assert float(np.linalg.det(m)) == pytest.approx(1.0, abs=1e-12)


def test_abcd_determinant_reports_the_index_ratio_across_an_interface():
    for n2 in (1.33, 1.5, 2.4):
        m = O.abcd_matrix([("interface", 1.0, n2)])
        assert float(np.linalg.det(m)) == pytest.approx(1.0 / n2, rel=1e-12)
        m2 = O.abcd_matrix([("curved", 1.0, n2, 50.0)])
        assert float(np.linalg.det(m2)) == pytest.approx(1.0 / n2, rel=1e-12)


@pytest.mark.parametrize("f1,f2,d", [(100.0, 200.0, 50.0), (-80.0, 40.0, 12.5)])
def test_abcd_two_lenses_compose_to_the_classical_combined_power(f1, f2, d):
    m = O.abcd_matrix([("lens", f1), ("free", d), ("lens", f2)])
    assert -float(m[1, 0]) == pytest.approx(
        1.0 / f1 + 1.0 / f2 - d / (f1 * f2), rel=1e-12)


def test_abcd_lens_between_two_focal_lengths_is_the_fourier_geometry():
    f = 50.0
    m = O.abcd_matrix([("free", f), ("lens", f), ("free", f)])
    assert np.allclose(m, [[0.0, f], [-1.0 / f, 0.0]], atol=1e-12)


def test_abcd_element_order_is_the_order_light_meets_them():
    """A lens then 100 mm of glass-free space is not the same as the reverse."""
    a = O.abcd_matrix([("lens", 50.0), ("free", 100.0)])
    b = O.abcd_matrix([("free", 100.0), ("lens", 50.0)])
    assert not np.allclose(a, b)
    assert np.allclose(a, np.array([[1.0, 100.0], [0.0, 1.0]])
                       @ np.array([[1.0, 0.0], [-1.0 / 50.0, 1.0]]))


def test_abcd_refuses_malformed_systems():
    with pytest.raises(ValueError, match="system is empty"):
        O.abcd_matrix([])
    with pytest.raises(ValueError, match="unknown kind"):
        O.abcd_matrix([("prism", 1.0)])
    with pytest.raises(ValueError, match="takes 1 parameter"):
        O.abcd_matrix([("free", 1.0, 2.0)])
    with pytest.raises(ValueError, match="must be >= 0"):
        O.abcd_matrix([("free", -1.0)])
    with pytest.raises(ValueError, match="must not be 0"):
        O.abcd_matrix([("lens", 0.0)])
    with pytest.raises(ValueError, match="must be > 0"):
        O.abcd_matrix([("interface", 1.0, 0.0)])
    with pytest.raises(ValueError, match="exceeds the 1024 cap"):
        O.abcd_matrix([("free", 1.0)] * 5000)
    with pytest.raises(ValueError, match="must be a sequence"):
        O.abcd_matrix("free")


def test_abcd_trace_free_space_and_lens_behave_as_rays_do():
    free = O.abcd_matrix([("free", 100.0)])
    r = O.abcd_trace(free, height_mm=1.0, angle_mrad=10.0)
    assert r["height_mm"] == pytest.approx(1.0 + 100.0 * 0.010, rel=1e-12)
    assert r["angle_mrad"] == pytest.approx(10.0, rel=1e-12)
    assert r["determinant"] == pytest.approx(1.0, abs=1e-12)
    lens = O.abcd_matrix([("lens", 50.0)])
    r2 = O.abcd_trace(lens, height_mm=2.0, angle_mrad=0.0)
    assert r2["height_mm"] == pytest.approx(2.0, rel=1e-12)
    # a ray parallel to the axis is bent by -y/f, so it crosses at exactly f
    assert r2["angle_mrad"] * 1e-3 == pytest.approx(-2.0 / 50.0, rel=1e-12)


def test_abcd_trace_flags_a_conjugate_plane():
    imaging = O.abcd_matrix([("free", 100.0), ("lens", 50.0), ("free", 100.0)])
    assert O.abcd_trace(imaging)["imaging"] is True
    assert O.abcd_trace(imaging, 1.0, 0.0)["height_mm"] == pytest.approx(-1.0, rel=1e-12)
    assert O.abcd_trace(O.abcd_matrix([("free", 10.0)]))["imaging"] is False


def test_abcd_trace_refuses_non_2x2_and_singular_matrices():
    with pytest.raises(ValueError, match=r"must be \(2, 2\)"):
        O.abcd_trace(np.eye(3))
    with pytest.raises(ValueError, match="singular"):
        O.abcd_trace(np.zeros((2, 2)))


# --------------------------------------------------------------------------- #
# geometric: depth of field, relative illumination                             #
# --------------------------------------------------------------------------- #
def test_depth_of_field_hyperfocal_matches_the_closed_form():
    r = O.depth_of_field(50.0, 8.0, 2000.0, 0.03)
    h = 50.0 ** 2 / (8.0 * 0.03) + 50.0
    assert r["hyperfocal_mm"] == pytest.approx(h, rel=1e-12)
    assert r["near_mm"] < 2000.0 < r["far_mm"]
    assert r["depth_mm"] == pytest.approx(r["far_mm"] - r["near_mm"], rel=1e-12)


@pytest.mark.parametrize("f,n,c", [(50.0, 8.0, 0.03), (12.0, 2.8, 0.005)])
def test_depth_of_field_near_limit_at_the_hyperfocal_is_exactly_half(f, n, c):
    """Focus at H and everything from H/2 to infinity is acceptably sharp."""
    h = f * f / (n * c) + f
    r = O.depth_of_field(f, n, h, c)
    assert r["near_mm"] == pytest.approx(h / 2.0, rel=1e-12)
    assert r["far_is_infinite"] is True
    assert np.isinf(r["far_mm"]) and np.isinf(r["depth_mm"])   # documented contract


def test_depth_of_field_halving_the_circle_of_confusion_doubles_the_hyperfocal():
    a = O.depth_of_field(50.0, 8.0, 2000.0, 0.03)
    b = O.depth_of_field(50.0, 8.0, 2000.0, 0.015)
    assert (b["hyperfocal_mm"] - 50.0) == pytest.approx(
        2.0 * (a["hyperfocal_mm"] - 50.0), rel=1e-12)
    assert b["depth_mm"] < a["depth_mm"]


def test_depth_of_field_refuses_impossible_geometry():
    with pytest.raises(ValueError, match="must be greater than focal_mm"):
        O.depth_of_field(50.0, 8.0, 50.0, 0.03)
    with pytest.raises(ValueError, match="f_number must be > 0"):
        O.depth_of_field(50.0, 0.0, 2000.0, 0.03)


def test_relative_illumination_is_the_cosine_fourth_law():
    curve = O.relative_illumination(60.0, 7, 4.0)
    assert curve.shape == (7, 2)
    assert curve[0, 0] == 0.0 and curve[0, 1] == pytest.approx(1.0, abs=0)
    assert curve[-1, 0] == pytest.approx(60.0)
    assert curve[-1, 1] == pytest.approx(1.0 / 16.0, rel=1e-12)   # cos^4(60) = 1/16
    at45 = O.relative_illumination(45.0, 2, 4.0)
    assert at45[-1, 1] == pytest.approx(0.25, rel=1e-12)          # cos^4(45) = 1/4
    assert np.all(np.diff(curve[:, 1]) < 0)                       # monotone


def test_relative_illumination_exponent_selects_the_falloff_law():
    cos3 = O.relative_illumination(60.0, 2, 3.0)[-1, 1]
    assert cos3 == pytest.approx(0.125, rel=1e-12)                # cos^3(60) = 1/8
    assert O.relative_illumination(60.0, 2, 0.0)[-1, 1] == pytest.approx(1.0)


def test_relative_illumination_refuses_the_degenerate_field():
    with pytest.raises(ValueError, match=r"must be in \(0, 90\)"):
        O.relative_illumination(90.0)
    with pytest.raises(ValueError, match=r"must be in \[2, 4096\]"):
        O.relative_illumination(20.0, 10 ** 9)
    with pytest.raises(ValueError, match="exponent must be >= 0"):
        O.relative_illumination(20.0, 8, -1.0)


# --------------------------------------------------------------------------- #
# wave: Airy, angular spectrum, Fraunhofer, Gaussian beam                      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("lam,fn", [(0.55, 5.6), (1.064, 2.8), (0.4, 11.0)])
def test_airy_first_dark_ring_is_at_1p2197_lambda_f(lam, fn):
    """The first zero of J1 at 3.8317 puts the ring at 1.2197*lambda*N — checked
    at three wavelength/aperture combinations so no single constant can hide a
    unit error."""
    expect = 1.2197 * lam * fn
    pitch = expect / 40.0                       # ~40 samples to the first ring
    img = O.airy_pattern(401, lam, fn, pitch)
    row = img[200, 200:]
    mins = [i for i in range(1, 120) if row[i] < row[i - 1] and row[i] < row[i + 1]]
    assert mins, "no dark ring found"
    assert mins[0] * pitch == pytest.approx(expect, rel=0.02)


def test_airy_peak_is_analytically_one_and_the_pattern_is_symmetric():
    img = O.airy_pattern(65, 0.55, 5.6, 0.05)
    assert img[32, 32] == 1.0                   # the v -> 0 limit, not 0/0
    assert np.isfinite(img).all()
    assert np.abs(img - img[::-1, :]).max() < 1e-15
    assert np.abs(img - img[:, ::-1]).max() < 1e-15
    assert img.max() == 1.0


def test_airy_refuses_oversized_grids_and_bad_units():
    with pytest.raises(ValueError, match=r"must be in \[2, 4096\]"):
        O.airy_pattern(10 ** 9)
    with pytest.raises(ValueError, match="wavelength_um must be > 0"):
        O.airy_pattern(16, 0.0)
    with pytest.raises(ValueError, match="pixel_pitch_um must be > 0"):
        O.airy_pattern(16, 0.55, 5.6, -1.0)


def _band_limited_field(n=64, seed=0):
    """A smooth complex field with no evanescent content at pitch=1um/550nm."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] / n
    amp = np.exp(-((y - 0.5) ** 2 + (x - 0.5) ** 2) / 0.05)
    return amp * np.exp(2j * np.pi * (0.1 * x + 0.07 * y)) + 0.01 * rng.random((n, n))


def test_angular_spectrum_zero_distance_is_the_exact_identity():
    f = _band_limited_field()
    out = O.angular_spectrum_propagate(f, 0.55, 0.0, 1.0)
    assert np.array_equal(out, f.astype(np.complex128))


def test_angular_spectrum_round_trip_returns_the_field():
    f = _band_limited_field()
    a = O.angular_spectrum_propagate(f, 0.55, 250.0, 1.0)
    b = O.angular_spectrum_propagate(a, 0.55, -250.0, 1.0)
    assert np.linalg.norm(b - f) / np.linalg.norm(f) < 1e-12
    assert not np.allclose(a, f)                 # it really did propagate


@pytest.mark.parametrize("lam,pitch", [(0.55, 1.0), (1.064, 2.0)])
def test_angular_spectrum_conserves_power_and_composes(lam, pitch):
    f = _band_limited_field()
    p0 = float((np.abs(f) ** 2).sum())
    one = O.angular_spectrum_propagate(f, lam, 300.0, pitch)
    assert float((np.abs(one) ** 2).sum()) == pytest.approx(p0, rel=1e-10)
    # two 150 um hops == one 300 um hop (the transfer function is a group)
    half = O.angular_spectrum_propagate(f, lam, 150.0, pitch)
    twice = O.angular_spectrum_propagate(half, lam, 150.0, pitch)
    assert np.linalg.norm(twice - one) / np.linalg.norm(one) < 1e-12


def test_angular_spectrum_refuses_degenerate_fields():
    with pytest.raises(ValueError, match="at least 2x2"):
        O.angular_spectrum_propagate(np.ones((1, 5), dtype=complex))
    with pytest.raises(ValueError, match="non-finite"):
        O.angular_spectrum_propagate(np.full((4, 4), np.nan, dtype=complex))
    with pytest.raises(ValueError, match="wavelength_um must be > 0"):
        O.angular_spectrum_propagate(np.ones((4, 4), dtype=complex), 0.0)


@pytest.mark.parametrize("n,w", [(64, 4), (64, 8), (128, 16)])
def test_fraunhofer_slit_zeros_land_on_the_dft_bins(n, w):
    """A boxcar of width w in an n-point DFT vanishes exactly at bins k*n/w."""
    ap = np.zeros((n, n))
    ap[:, (n - w) // 2:(n + w) // 2] = 1.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        img = O.fraunhofer_pattern(ap, 0.55, 100.0, 10.0)
    centre = img[n // 2]
    assert centre[n // 2] == 1.0
    for k in (1, 2):
        if n // 2 + k * n // w < n:
            assert centre[n // 2 + k * n // w] == pytest.approx(0.0, abs=1e-24)
            assert centre[n // 2 - k * n // w] == pytest.approx(0.0, abs=1e-24)
    assert np.abs(img[:, 1:] - img[:, :0:-1]).max() < 1e-14      # symmetric


def test_fraunhofer_warns_when_the_far_field_condition_fails():
    ap = np.zeros((64, 64))
    ap[24:40, 24:40] = 1.0
    with pytest.warns(RuntimeWarning, match="Fresnel number"):
        O.fraunhofer_pattern(ap, 0.55, 0.01, 10.0)              # 10 um away
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        O.fraunhofer_pattern(ap, 0.55, 100000.0, 10.0)          # 100 m away: fine


def test_fraunhofer_refuses_an_opaque_or_negative_aperture():
    with pytest.raises(ValueError, match="entirely opaque"):
        O.fraunhofer_pattern(np.zeros((8, 8)))
    with pytest.raises(ValueError, match="negative value"):
        O.fraunhofer_pattern(-np.ones((8, 8)))


@pytest.mark.parametrize("w0,lam,n", [(100.0, 1.064, 1.0), (25.0, 0.633, 1.33)])
def test_gaussian_beam_rayleigh_range_identities(w0, lam, n):
    """At z = zR: spot sqrt(2)*w0, wavefront radius 2*zR, Gouy exactly 45 deg."""
    at0 = O.gaussian_beam(w0, lam, 0.0, n)
    zr = at0["rayleigh_mm"]
    assert zr == pytest.approx(np.pi * w0 * w0 * n / lam * 1e-3, rel=1e-12)
    assert at0["radius_um"] == pytest.approx(w0, rel=1e-12)
    assert np.isinf(at0["wavefront_radius_mm"])                  # documented
    assert at0["curvature_per_mm"] == 0.0
    assert at0["gouy_deg"] == pytest.approx(0.0, abs=1e-12)
    at = O.gaussian_beam(w0, lam, zr, n)
    assert at["radius_um"] == pytest.approx(np.sqrt(2.0) * w0, rel=1e-12)
    assert at["wavefront_radius_mm"] == pytest.approx(2.0 * zr, rel=1e-12)
    assert at["gouy_deg"] == pytest.approx(45.0, rel=1e-12)
    assert at["curvature_per_mm"] == pytest.approx(1.0 / (2.0 * zr), rel=1e-12)


def test_gaussian_beam_parameter_product_and_converging_side():
    for w0, lam, n in ((100.0, 1.064, 1.0), (25.0, 0.633, 1.33), (5.0, 0.4, 1.0)):
        g = O.gaussian_beam(w0, lam, 0.0, n)
        # w0 * theta = lambda / (pi * n), the diffraction-limited invariant
        assert w0 * g["divergence_mrad"] * 1e-3 == pytest.approx(
            lam / (np.pi * n), rel=1e-12)
    before = O.gaussian_beam(100.0, 1.064, -29.526246744264974, 1.0)
    assert before["wavefront_radius_mm"] < 0                     # converging
    assert before["gouy_deg"] < 0


def test_gaussian_beam_refuses_non_physical_parameters():
    with pytest.raises(ValueError, match="waist_um must be > 0"):
        O.gaussian_beam(0.0)
    with pytest.raises(ValueError, match="n_medium must be > 0"):
        O.gaussian_beam(100.0, 1.064, 0.0, 0.0)


# --------------------------------------------------------------------------- #
# imaging quality: MTF and wavefront                                           #
# --------------------------------------------------------------------------- #
def test_psf_to_mtf_of_a_delta_is_flat_at_one():
    psf = np.zeros((64, 64))
    psf[0, 0] = 1.0
    curve = O.psf_to_mtf(psf, 1.0)
    assert curve.shape[1] == 2
    assert np.abs(curve[:, 1] - 1.0).max() == 0.0


@pytest.mark.parametrize("n,sigma,tol", [(128, 2.0, 1e-3), (64, 1.5, 1e-3),
                                         (256, 3.0, 1e-3)])
def test_psf_to_mtf_of_a_gaussian_matches_the_closed_form(n, sigma, tol):
    """MTF of a Gaussian PSF is exp(-2*pi^2*sigma^2*f^2); checked at three
    (grid, sigma) scales so the radial averaging cannot pass by coincidence."""
    ax = np.fft.fftfreq(n) * n
    yy, xx = np.meshgrid(ax, ax, indexing="ij")
    psf = np.exp(-(yy ** 2 + xx ** 2) / (2.0 * sigma ** 2))
    psf /= psf.sum()
    curve = O.psf_to_mtf(psf, 1.0)
    f_per_px = curve[:, 0] / 1e3                # cycles/mm -> cycles/um == /px
    assert np.abs(curve[:, 1] - np.exp(-2.0 * np.pi ** 2 * sigma ** 2
                                       * f_per_px ** 2)).max() < tol


def test_psf_to_mtf_frequency_axis_scales_with_the_pixel_pitch():
    """Units regression: the frequency column is cycles/mm, so doubling the
    pitch (um) halves every frequency and leaves the MTF untouched."""
    ax = np.fft.fftfreq(128) * 128
    yy, xx = np.meshgrid(ax, ax, indexing="ij")
    psf = np.exp(-(yy ** 2 + xx ** 2) / 8.0)
    a = O.psf_to_mtf(psf, 1.0)
    b = O.psf_to_mtf(psf, 2.0)
    assert np.allclose(a[:, 0], 2.0 * b[:, 0], rtol=1e-12)
    assert np.array_equal(a[:, 1], b[:, 1])
    # Nyquist for a 1 um pitch is 500 cycles/mm
    assert a[:, 0].max() < 500.0 and a[:, 0].max() > 400.0


def test_psf_to_mtf_refuses_a_non_psf():
    with pytest.raises(ValueError, match="sums to 0"):
        O.psf_to_mtf(np.zeros((8, 8)))
    with pytest.raises(ValueError, match="sums to -64"):
        O.psf_to_mtf(-np.ones((8, 8)))
    with pytest.raises(ValueError, match="pixel_pitch_um must be > 0"):
        O.psf_to_mtf(np.ones((8, 8)), 0.0)


def test_mtf_diffraction_reproduces_the_textbook_curve():
    curve = O.mtf_diffraction(5.6, 0.55, 101)
    assert curve[0, 1] == pytest.approx(1.0, rel=1e-12)
    assert curve[-1, 1] == pytest.approx(0.0, abs=1e-12)
    # the classical value at half the cutoff
    exact = (2.0 / np.pi) * (np.arccos(0.5) - 0.5 * np.sqrt(0.75))
    assert curve[50, 1] == pytest.approx(exact, rel=1e-12)
    assert curve[50, 1] == pytest.approx(0.3910022, abs=1e-6)
    assert np.all(np.diff(curve[:, 1]) < 0)


@pytest.mark.parametrize("fn,lam", [(5.6, 0.55), (2.8, 0.55), (5.6, 1.064)])
def test_mtf_diffraction_cutoff_is_one_over_lambda_f_in_cycles_per_mm(fn, lam):
    """Units regression: nu_c = 1/(lambda*N) in cycles/um -> *1000 cycles/mm."""
    curve = O.mtf_diffraction(fn, lam, 32)
    assert curve[-1, 0] == pytest.approx(1e3 / (lam * fn), rel=1e-12)


def test_mtf_diffraction_refuses_bad_units():
    with pytest.raises(ValueError, match="f_number must be > 0"):
        O.mtf_diffraction(0.0)
    with pytest.raises(ValueError, match=r"must be in \[2, 4096\]"):
        O.mtf_diffraction(5.6, 0.55, 1)


def test_wavefront_stats_pure_defocus_matches_the_exact_pupil_rms():
    """Z(2,0) = 2*rho^2-1 has RMS 1/sqrt(3) and PV 2 over the unit pupil."""
    r = O.wavefront_stats({(2, 0): 0.1})
    assert r["rms_waves"] == pytest.approx(0.1 / np.sqrt(3.0), rel=2e-4)
    assert r["pv_waves"] == pytest.approx(0.2, rel=1e-12)
    assert r["strehl"] == pytest.approx(
        np.exp(-((2.0 * np.pi * 0.1 / np.sqrt(3.0)) ** 2)), rel=1e-4)
    assert r["marechal_valid"] is True
    assert r["terms"] == 1 and r["n_max"] == 2


@pytest.mark.parametrize("n", [2, 4, 6])
def test_wavefront_stats_rms_of_z_n_0_is_one_over_sqrt_n_plus_one(n):
    r = O.wavefront_stats({(n, 0): 0.1})
    assert r["rms_waves"] == pytest.approx(0.1 / np.sqrt(n + 1.0), rel=5e-3)


def test_wavefront_stats_quadrature_converges_as_the_grid_refines():
    exact = 0.1 / np.sqrt(3.0)
    errs = [abs(O.wavefront_stats({(2, 0): 0.1}, radial=nr)["rms_waves"] - exact)
            for nr in (64, 128, 256, 512)]
    assert errs == sorted(errs, reverse=True)
    assert errs[-1] / exact < 1e-5


def test_wavefront_stats_piston_is_not_an_aberration_and_rms_is_linear():
    assert O.wavefront_stats({(0, 0): 5.0})["rms_waves"] == pytest.approx(0.0, abs=1e-15)
    assert O.wavefront_stats({(0, 0): 5.0})["strehl"] == pytest.approx(1.0)
    one = O.wavefront_stats({(2, 0): 0.1})["rms_waves"]
    two = O.wavefront_stats({(2, 0): 0.2})["rms_waves"]
    assert two == pytest.approx(2.0 * one, rel=1e-12)


def test_wavefront_stats_consumes_fit_zernike_output():
    """The dict contract really is match3d.fit_zernike's — no adapter needed."""
    from match3d import fit_zernike
    yy, xx = np.mgrid[0:64, 0:64]
    rho2 = ((yy - 31.5) ** 2 + (xx - 31.5) ** 2) / 31.0 ** 2
    coeffs = fit_zernike(0.1 * (2.0 * rho2 - 1.0), n_max=4)
    r = O.wavefront_stats(coeffs)
    assert 0.0 < r["rms_waves"] < 0.2
    assert r["n_max"] == 4 and r["terms"] == len(coeffs)


def test_wavefront_stats_refuses_bad_expansions():
    with pytest.raises(ValueError, match="must be a dict"):
        O.wavefront_stats([1.0, 2.0])
    with pytest.raises(ValueError, match="is empty"):
        O.wavefront_stats({})
    with pytest.raises(ValueError, match="not a valid Zernike index"):
        O.wavefront_stats({(1, 0): 1.0})
    with pytest.raises(ValueError, match=r"not an \(n, m\) pair"):
        O.wavefront_stats({"defocus": 1.0})
    with pytest.raises(ValueError, match="exceeds the 512 cap"):
        O.wavefront_stats({(2 * i, 0): 0.0 for i in range(600)})


# --------------------------------------------------------------------------- #
# polarisation                                                                 #
# --------------------------------------------------------------------------- #
def test_jones_crossed_polarisers_block_the_light_exactly():
    p0 = O.jones_element("polarizer", 0.0)
    p90 = O.jones_element("polarizer", 90.0)
    assert np.abs(p90 @ p0).max() < 1e-15
    out = O.jones_apply(p90 @ p0, np.array([1.0 + 0j, 0.0 + 0j]))
    assert np.abs(out).max() < 1e-15


@pytest.mark.parametrize("theta", [0.0, 15.0, 30.0, 45.0, 60.0, 90.0, 137.0])
def test_jones_reproduces_malus_law(theta):
    v = O.jones_apply(O.jones_element("polarizer", theta),
                      np.array([1.0 + 0j, 0.0 + 0j]))
    intensity = float(np.abs(v[0]) ** 2 + np.abs(v[1]) ** 2)
    assert intensity == pytest.approx(np.cos(np.radians(theta)) ** 2, abs=1e-14)


def test_jones_polariser_is_idempotent_and_identity_passes_through():
    p = O.jones_element("polarizer", 33.0)
    assert np.abs(p @ p - p).max() < 1e-15
    v = np.array([0.6 + 0.2j, -0.3 + 0.7j])
    assert np.array_equal(O.jones_apply(np.eye(2, dtype=complex), v), v)


def test_jones_quarter_wave_at_45_makes_circular_light():
    q = O.jones_element("quarter_wave", 45.0)
    s = O.stokes_from_jones(O.jones_apply(q, np.array([1.0 + 0j, 0.0 + 0j])))
    assert abs(s[3]) == pytest.approx(s[0], rel=1e-14)          # fully circular
    assert abs(s[1]) < 1e-14 and abs(s[2]) < 1e-14
    h = O.jones_element("half_wave", 45.0)
    # a half-wave plate at 45 deg maps horizontal to vertical
    out = O.jones_apply(h, np.array([1.0 + 0j, 0.0 + 0j]))
    assert abs(out[0]) < 1e-15 and abs(abs(out[1]) - 1.0) < 1e-15


def test_stokes_from_jones_pins_the_handedness_convention():
    """[1, -i]/sqrt(2) is right circular and must give S3 = +1 here."""
    rc = np.array([1.0, -1.0j]) / np.sqrt(2.0)
    assert O.stokes_from_jones(rc) == pytest.approx([1.0, 0.0, 0.0, 1.0], abs=1e-15)
    lc = np.array([1.0, +1.0j]) / np.sqrt(2.0)
    assert O.stokes_from_jones(lc) == pytest.approx([1.0, 0.0, 0.0, -1.0], abs=1e-15)
    assert O.stokes_from_jones([1.0, 0.0]) == pytest.approx([1, 1, 0, 0], abs=1e-15)
    lin45 = np.array([1.0, 1.0]) / np.sqrt(2.0)
    assert O.stokes_from_jones(lin45) == pytest.approx([1, 0, 1, 0], abs=1e-15)


def test_stokes_from_jones_is_always_fully_polarised():
    rng = np.random.default_rng(3)
    for _ in range(20):
        v = rng.standard_normal(2) + 1j * rng.standard_normal(2)
        s = O.stokes_from_jones(v)
        assert np.hypot(np.hypot(s[1], s[2]), s[3]) == pytest.approx(s[0], rel=1e-13)


def test_mueller_polariser_halves_unpolarised_light_and_polarises_it():
    m = O.mueller_element("polarizer", 0.0)
    s = O.mueller_apply(m, [1.0, 0.0, 0.0, 0.0])
    assert s[0] == pytest.approx(0.5, rel=1e-15)
    assert O.stokes_analyze(s)["dop"] == pytest.approx(1.0, rel=1e-14)


@pytest.mark.parametrize("theta", [0.0, 22.5, 45.0, 60.0, 90.0])
def test_mueller_two_polarisers_reproduce_malus_for_unpolarised_input(theta):
    m = O.mueller_element("polarizer", theta) @ O.mueller_element("polarizer", 0.0)
    s = O.mueller_apply(m, [1.0, 0.0, 0.0, 0.0])
    assert s[0] == pytest.approx(0.5 * np.cos(np.radians(theta)) ** 2, abs=1e-15)


def test_mueller_rotator_and_depolariser_behave_as_named():
    rot = O.mueller_element("rotator", 45.0)
    s = O.mueller_apply(rot, [1.0, 1.0, 0.0, 0.0])
    assert s == pytest.approx([1.0, 0.0, 1.0, 0.0], abs=1e-15)
    assert O.stokes_analyze(s)["azimuth_deg"] == pytest.approx(45.0, abs=1e-12)
    dep = O.mueller_apply(O.mueller_element("depolarizer"), [1.0, 1.0, 0.0, 0.0])
    assert dep == pytest.approx([1.0, 0.0, 0.0, 0.0], abs=0)


@pytest.mark.parametrize("kind", ["polarizer", "retarder", "quarter_wave",
                                  "half_wave", "rotator"])
@pytest.mark.parametrize("angle", [0.0, 17.0, 45.0, 90.0, 123.0])
def test_jones_and_mueller_agree_on_every_element(kind, angle):
    """The cross-check that actually catches a sign slip: the same physical
    element, built independently in the two calculi, must transform the same
    input into the same Stokes vector."""
    state = np.array([0.8 + 0.1j, -0.3 + 0.5j])
    via_jones = O.stokes_from_jones(
        O.jones_apply(O.jones_element(kind, angle, 63.0), state))
    via_mueller = O.mueller_apply(O.mueller_element(kind, angle, 63.0),
                                  O.stokes_from_jones(state))
    assert via_jones == pytest.approx(via_mueller, abs=1e-14)


def test_stokes_analyze_canonical_states():
    assert O.stokes_analyze([1, 1, 0, 0])["azimuth_deg"] == pytest.approx(0.0)
    assert O.stokes_analyze([1, -1, 0, 0])["azimuth_deg"] == pytest.approx(90.0)
    assert O.stokes_analyze([1, 0, 1, 0])["azimuth_deg"] == pytest.approx(45.0)
    assert O.stokes_analyze([1, 0, -1, 0])["azimuth_deg"] == pytest.approx(135.0)
    rc = O.stokes_analyze([1, 0, 0, 1])
    assert rc["docp"] == pytest.approx(1.0) and rc["handedness"] == "right"
    assert rc["ellipticity_deg"] == pytest.approx(45.0)
    assert O.stokes_analyze([1, 0, 0, -1])["handedness"] == "left"
    partial = O.stokes_analyze([2, 1, 0, 0])
    assert partial["dop"] == pytest.approx(0.5) and partial["intensity"] == 2.0


def test_stokes_analyze_reports_undefined_angles_as_none():
    """Unpolarised light has no orientation — 0.0 would be a fabricated angle."""
    unpol = O.stokes_analyze([1, 0, 0, 0])
    assert unpol["dop"] == 0.0
    assert unpol["azimuth_deg"] is None and unpol["ellipticity_deg"] is None
    circ = O.stokes_analyze([1, 0, 0, 1])
    assert circ["azimuth_deg"] is None            # circular: no linear axis
    assert circ["ellipticity_deg"] == pytest.approx(45.0)


def test_polarisation_ops_refuse_unphysical_input():
    with pytest.raises(ValueError, match="not physically realisable"):
        O.mueller_apply(np.eye(4), [1.0, 1.0, 1.0, 1.0])
    with pytest.raises(ValueError, match="negative intensity"):
        O.stokes_analyze([-1.0, 0.0, 0.0, 0.0])
    with pytest.raises(ValueError, match="there is no light"):
        O.stokes_analyze([0.0, 0.0, 0.0, 0.0])
    with pytest.raises(ValueError, match="unknown kind"):
        O.jones_element("brewster")
    with pytest.raises(ValueError, match="unknown kind"):
        O.mueller_element("brewster")
    with pytest.raises(ValueError, match="exactly 2 component"):
        O.stokes_from_jones([1.0, 0.0, 0.0])
    with pytest.raises(ValueError, match=r"must be a \(4, 4\) matrix"):
        O.mueller_apply(np.eye(3), [1.0, 0.0, 0.0, 0.0])


# --------------------------------------------------------------------------- #
# ledger / facade wiring                                                       #
# --------------------------------------------------------------------------- #
def _ledger_args():
    """One valid call per registered op (also the fixture for the type check)."""
    field = _band_limited_field(16)
    ap = np.zeros((16, 16))
    ap[6:10, 6:10] = 1.0
    psf = np.zeros((16, 16))
    psf[8, 8] = 1.0
    return {
        "thin_lens": (), "abcd_matrix": ([("free", 100.0), ("lens", 50.0)],),
        "abcd_trace": (O.abcd_matrix([("free", 100.0)]),),
        "depth_of_field": (), "relative_illumination": (),
        "airy_pattern": (16,), "angular_spectrum_propagate": (field,),
        "fraunhofer_pattern": (ap,), "gaussian_beam": (),
        "psf_to_mtf": (psf,), "mtf_diffraction": (),
        "wavefront_stats": ({(2, 0): 0.05},),
        "jones_element": (), "jones_apply": (O.jones_element("polarizer", 30.0),
                                             np.array([1.0 + 0j, 0.0 + 0j])),
        "stokes_from_jones": (np.array([1.0 + 0j, 0.0 + 0j]),),
        "mueller_element": (),
        "mueller_apply": (O.mueller_element("polarizer"),
                          np.array([1.0, 0.0, 0.0, 0.0])),
        "stokes_analyze": (np.array([1.0, 1.0, 0.0, 0.0]),),
    }


def test_ledger_is_complete_and_every_op_has_an_implementation():
    assert opsoptics.missing() == []
    assert len(opsoptics.OPSOPTICS) == 18
    assert sorted(opsoptics.categories()) == ["geometric", "imaging",
                                              "polarization", "wave"]
    assert set(opsoptics.OPSOPTICS) == set(O.OPTICS) == set(O.__all__) & set(O.OPTICS)
    for name, meta in opsoptics.OPSOPTICS.items():
        assert meta["doc"], f"{name} has no docstring summary line"
        assert "Raises" in (meta["func"].__doc__ or ""), \
            f"{name} docstring has no Raises section"


def test_ledger_call_returns_the_declared_type():
    """The same machine check that caught mat_svd's declared-table/actual-tuple
    lie in the maths ledger. optics has no RESULT_ADAPTERS on purpose, so this
    verifies the *raw* returns against the declarations."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from chain_fuzz import TYPE_CHECKS
    args = _ledger_args()
    assert not [n for n in opsoptics.OPSOPTICS if n not in args], "args missing"
    for name, a in args.items():
        out_t = opsoptics.OPSOPTICS[name]["out"]
        check = TYPE_CHECKS.get(out_t)
        assert check is not None, f"{name}: type {out_t!r} unknown to the fuzzer"
        val = opsoptics.call(name, *a)
        assert check(val), (name, out_t, type(val).__name__)
        assert val is not None
        raw = opsoptics.get(name)(*a)
        assert type(raw) is type(val), f"{name}: adapter changed the type"


def test_optics_ops_are_registered_in_the_chain_fuzzer():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz
    names = {o[0] for o in chain_fuzz.catalog() if o[1] == "optics"}
    assert names == set(opsoptics.OPSOPTICS)


def test_facade_exports_every_optics_op():
    import api
    import fullseye
    for name in O.OPTICS:
        assert name in api.__all__, f"{name} missing from api.__all__"
        assert name in fullseye.__all__, f"{name} missing from fullseye.__all__"
        assert getattr(fullseye, name) is getattr(O, name)
    assert fullseye.optics is O


# --------------------------------------------------------------------------- #
# regressions from the 2026-09-01 adversarial pass                             #
# --------------------------------------------------------------------------- #
class TestAdversarialRegressions:
    """Each test is the minimal reproduction that exposed the bug."""

    def test_a_string_is_not_a_length(self):
        """``float("50")`` succeeds, so a string used to sail through as a
        millimetre value: thin_lens("50", "200") returned a plausible 66.667."""
        with pytest.raises(ValueError, match="is a string"):
            O.thin_lens("50", "200")
        with pytest.raises(ValueError, match="is a string"):
            O.abcd_matrix([("free", "100")])
        with pytest.raises(ValueError, match="is a string"):
            O.gaussian_beam("100")
        with pytest.raises(ValueError, match="is a bool"):
            O.thin_lens(True, 200.0)

    def test_an_overflowing_psf_no_longer_returns_a_column_of_nan(self):
        """A PSF of 1e308 overflows the FFT, so |OTF| and |OTF(0)| were both inf
        and the MTF came back NaN. The positive-sum guard does not catch it —
        the sum overflows to +inf, which is > 0."""
        with pytest.raises(ValueError, match="overflowed float64"):
            O.psf_to_mtf(np.full((8, 8), 1e308))

    def test_an_overflowing_determinant_is_not_reported_as_inf(self):
        """diag(1e200, 1e200) traces a finite ray while det overflows, so the
        returned dict carried a silent ``determinant: inf``."""
        with pytest.raises(ValueError, match="determinant overflowed"):
            O.abcd_trace(np.array([[1e200, 0.0], [0.0, 1e200]]))

    def test_high_zernike_orders_are_refused_not_silently_wrong(self):
        """The shared basis builder's factorial recurrence breaks its own
        |Z| <= 1 bound at n = 46 (measured 1.41; 71.5 at n = 50; 2.8e5 at 60),
        so a 60th-order 'wavefront' used to report an RMS of 3032 waves."""
        with pytest.raises(ValueError, match="exceeds the 40 cap"):
            O.wavefront_stats({(60, 0): 0.1})
        with pytest.warns(RuntimeWarning, match="under-sampled"):
            r = O.wavefront_stats({(40, 0): 0.1})
        assert r["rms_waves"] < 1.0             # bounded, not 3032 waves

    def test_a_small_call_cannot_ask_for_a_hundred_gigabytes(self):
        """wavefront_stats builds every (n, m) up to n_max on the whole polar
        grid: n_max=40 at 4096x4096 is 1.4e10 elements (108 GB) from a call
        whose arguments are one dict and two ints."""
        with pytest.raises(ValueError, match="over the .* cap"):
            O.wavefront_stats({(40, 0): 0.1}, radial=4096, angular=4096)

    def test_an_undersampled_quadrature_says_so(self):
        with pytest.warns(RuntimeWarning, match="under-sampled"):
            O.wavefront_stats({(20, 0): 0.1}, radial=128)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            O.wavefront_stats({(6, 0): 0.1}, radial=128)

    def test_documented_infinities_are_the_only_infinities(self):
        """Only depth_of_field's far limit and gaussian_beam's waist curvature
        may be non-finite, and both advertise it with a companion field."""
        documented = {"depth_of_field", "gaussian_beam"}
        for name, a in _ledger_args().items():
            if name in documented:
                continue                        # their infinities are the contract
            val = opsoptics.call(name, *a)
            if isinstance(val, np.ndarray):
                assert np.isfinite(val).all(), name
            elif isinstance(val, dict):
                for k, v in val.items():
                    if isinstance(v, float):
                        assert np.isfinite(v), f"{name}[{k}] = {v}"
        beyond = O.depth_of_field(50.0, 8.0, 20000.0, 0.03)
        assert np.isinf(beyond["far_mm"]) and beyond["far_is_infinite"] is True
        waist = O.gaussian_beam(100.0, 1.064, 0.0)
        assert np.isinf(waist["wavefront_radius_mm"])
        assert waist["curvature_per_mm"] == 0.0     # the finite companion
