# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Encircled / ensquared energy, tangential-sagittal MTF and through-focus MTF -- external-truth gates.

Every reference is closed form or an independent quadrature, never the code under test:

* the Airy pattern: encircled energy ``1 - J0(v)^2 - J1(v)^2`` (83.8 % at the first dark ring, Born and
  Wolf) with ``v = pi r / (lambda N)`` from SciPy's Bessel functions, and the radii at 50 / 80 / 90 %
  from an independent root find;
* a square pupil: the separable ``sinc^2`` PSF, whose ensquared energy is ``S(a)^2`` with the sine
  integral;
* a Gaussian PSF: encircled energy ``1 - exp(-r^2 / 2 s^2)``, ensquared ``erf(w / s sqrt 2)^2``, and an
  MTF ``exp(-2 pi^2 s^2 nu^2)`` per axis (so an anisotropic Gaussian tells tangential from sagittal);
* the diffraction-limited circular pupil ``(2/pi)(arccos x - x sqrt(1 - x^2))``;
* defocus: Hopkins' overlap integral of two shifted pupils, by ``scipy.integrate.quad``.

The probes break the inputs on purpose (pitch doubled, axes swapped, the paraxial defocus without its
conjugate correction) and require the gate to go red.
"""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

scipy_special = pytest.importorskip("scipy.special")
from scipy.integrate import quad  # noqa: E402
from scipy.optimize import brentq  # noqa: E402

import lensimage as LI  # noqa: E402
import optics as O  # noqa: E402
import opsoptics  # noqa: E402
import raytrace as RT  # noqa: E402

LAM, N = 0.55, 5.6


def _airy_ee(r_um, lam=LAM, n=N):
    v = np.pi * np.asarray(r_um, float) / (lam * n)
    return 1.0 - scipy_special.j0(v) ** 2 - scipy_special.j1(v) ** 2


def _round_pupil_psf(n=64, oversample=16):
    yy, xx = np.mgrid[0:n, 0:n]
    c = (n - 1) / 2.0
    pup = (np.hypot(yy - c, xx - c) <= n / 2.0).astype(float)
    psf = O.pupil_psf(pup, 0.0, LAM, N, oversample=oversample)
    return psf, LAM * N * n / psf.shape[0]


def _gauss(sy, sx, size=129):
    yy, xx = np.mgrid[0:size, 0:size] - size // 2
    g = np.exp(-0.5 * (yy / sy) ** 2 - 0.5 * (xx / sx) ** 2)
    return g / g.sum()


# --------------------------------------------------------------------------- #
# encircled energy
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def airy():
    return _round_pupil_psf()


def test_airy_encircled_energy_is_83_8_percent_at_the_first_dark_ring(airy):
    psf, dx = airy
    r1 = 1.2197 * LAM * N
    ee = O.encircled_energy(psf, dx, samples=1601, max_radius_um=8 * LAM * N, centre="fft")
    got = float(np.interp(r1, ee[:, 0], ee[:, 1]))
    assert abs(got - 0.838) < 0.005, got                           # Born and Wolf: 83.8 %
    # and against the Bessel closed form at the first three dark rings and a few other radii
    errs = [abs(float(np.interp(k * LAM * N, ee[:, 0], ee[:, 1])) - float(_airy_ee(k * LAM * N)))
            for k in (1.2197, 2.2331, 3.2383, 1.0, 2.0, 4.0)]
    assert max(errs) < 2e-3, errs


def test_energy_curve_is_monotone_and_bounded(airy):
    psf, dx = airy
    for fn in (O.encircled_energy, O.ensquared_energy):
        c = fn(psf, dx, samples=200)
        assert c.shape == (200, 2) and c[0, 0] == 0.0 and c[0, 1] == pytest.approx(0.0, abs=1e-12)
        assert np.all(np.diff(c[:, 1]) >= -1e-12) and c[:, 1].max() <= 1.0
        assert np.all(np.diff(c[:, 0]) > 0)


def test_radii_at_50_80_90_percent_match_an_independent_root_find(airy):
    psf, dx = airy
    out = O.energy_radii(psf, dx, (0.5, 0.8, 0.9))
    ref = [brentq(lambda r, f=f: float(_airy_ee(r)) - f, 1e-3, 20 * LAM * N) for f in (0.5, 0.8, 0.9)]
    for got, want in zip(out["radius_um"], ref):
        assert abs(got - want) / want < 0.01, (got, want)
    assert out["diameter_um"] == pytest.approx([2 * v for v in out["radius_um"]])
    assert out["kind"] == "circle" and out["fractions"] == [0.5, 0.8, 0.9]


def test_ensquared_energy_of_a_square_pupil_matches_the_sine_integral():
    n = 64
    psf = O.pupil_psf(np.ones((n, n)), 0.0, LAM, N, oversample=16)
    dx = LAM * N * n / psf.shape[0]
    es = O.ensquared_energy(psf, dx, samples=1601, max_half_width_um=8 * LAM * N, centre="fft")
    scipy_sici = scipy_special.sici

    def closed(a):
        return ((2.0 / np.pi) * (scipy_sici(2 * np.pi * a)[0] - np.sin(np.pi * a) ** 2 / (np.pi * a))) ** 2

    errs = [abs(float(np.interp(a * LAM * N, es[:, 0], es[:, 1])) - float(closed(a))) for a in (0.5, 1.0, 2.0, 3.0)]
    assert max(errs) < 3e-3, errs           # the window wraps the sinc tails: array-normalised, so slightly high
    r = O.energy_radii(psf, dx, (0.5, 0.9), kind="square", centre="fft")
    for got, f in zip(r["radius_um"], (0.5, 0.9)):
        want = brentq(lambda a, f=f: float(closed(a)) - f, 1e-3, 20) * LAM * N
        assert abs(got - want) / want < 0.01


def test_gaussian_psf_has_the_closed_form_encircled_and_ensquared_energy():
    sig = 4.0
    g = _gauss(sig, sig)
    ee = O.encircled_energy(g, 1.0, samples=300, max_radius_um=40.0, centre="fft")
    want = 1.0 - np.exp(-0.5 * (ee[:, 0] / sig) ** 2)
    assert np.max(np.abs(ee[:, 1] - want)) < 2e-3
    es = O.ensquared_energy(g, 1.0, samples=300, max_half_width_um=40.0, centre="fft")
    want = np.vectorize(math.erf)(es[:, 0] / (sig * math.sqrt(2.0))) ** 2
    assert np.max(np.abs(es[:, 1] - want)) < 5e-3        # samples are point values held over a pixel: ~1/(24 s^2)


def test_centre_options_agree_on_a_symmetric_psf_and_an_offset_centre_is_honoured():
    g = _gauss(3.0, 3.0)
    a = O.energy_radii(g, 1.0, (0.8,), centre="centroid")["radius_um"][0]
    b = O.energy_radii(g, 1.0, (0.8,), centre="peak")["radius_um"][0]
    c = O.energy_radii(g, 1.0, (0.8,), centre=(64, 64))["radius_um"][0]
    assert a == pytest.approx(b, abs=1e-6) and a == pytest.approx(c, abs=1e-6)
    shifted = np.roll(g, (5, -7), axis=(0, 1))
    s1 = O.energy_radii(shifted, 1.0, (0.8,), centre="centroid")["radius_um"][0]
    assert s1 == pytest.approx(a, abs=2e-3)                          # the centroid follows the spot
    s2 = O.energy_radii(shifted, 1.0, (0.8,), centre="fft")["radius_um"][0]
    assert s2 > a + 1.0                                              # a wrong centre needs a bigger circle


def test_probe_a_doubled_pitch_doubles_the_radius_and_the_gate_notices(airy):
    psf, dx = airy
    good = O.energy_radii(psf, dx, (0.8,))["radius_um"][0]
    bad = O.energy_radii(psf, 2 * dx, (0.8,))["radius_um"][0]
    assert bad == pytest.approx(2 * good, rel=1e-9)
    want = brentq(lambda r: float(_airy_ee(r)) - 0.8, 1e-3, 20 * LAM * N)
    assert abs(good - want) / want < 0.01 and abs(bad - want) / want > 0.5


def test_energy_ops_refuse_bad_inputs():
    g = _gauss(3.0, 3.0, 65)
    with pytest.raises(ValueError, match="non-negative|negative"):
        O.encircled_energy(g - 0.5 * g.max())
    with pytest.raises(ValueError):
        O.encircled_energy(np.zeros((9, 9)))
    bad = g.copy(); bad[3, 3] = np.nan
    with pytest.raises(ValueError):
        O.ensquared_energy(bad)
    with pytest.raises(ValueError):
        O.encircled_energy(g, pixel_pitch_um=0.0)
    with pytest.raises(ValueError, match="leaves the array"):
        O.encircled_energy(g, 1.0, max_radius_um=1e3)
    with pytest.raises(ValueError, match="samples"):
        O.encircled_energy(g, samples=1)
    with pytest.raises(ValueError, match="centre"):
        O.encircled_energy(g, centre="middle")
    with pytest.raises(ValueError, match="centre"):
        O.encircled_energy(g, centre=(1000, 3))
    with pytest.raises(ValueError, match="fraction"):
        O.energy_radii(g, 1.0, (1.0,))
    with pytest.raises(ValueError, match="fraction"):
        O.energy_radii(g, 1.0, (float("nan"),))
    with pytest.raises(ValueError, match="kind"):
        O.energy_radii(g, 1.0, (0.5,), kind="disc")
    with pytest.raises(ValueError, match="not reached"):
        O.energy_radii(_gauss(30.0, 30.0, 65), 1.0, (0.9,))          # the window cuts the wings off
    with pytest.raises(ValueError):
        O.encircled_energy(np.ones((2, 2)))


# --------------------------------------------------------------------------- #
# tangential / sagittal MTF
# --------------------------------------------------------------------------- #
def test_diffraction_limited_mtf_matches_the_closed_form_on_both_meridians():
    psf, dx = _round_pupil_psf(n=256, oversample=2)
    out = O.mtf_tangential_sagittal(psf, dx)
    cut = 1e3 / (LAM * N)
    for key in ("tangential", "sagittal"):
        c = out[key]
        x = c[:, 0] / cut
        sel = (x > 0) & (x < 1)
        ref = (2 / np.pi) * (np.arccos(x[sel]) - x[sel] * np.sqrt(1 - x[sel] ** 2))
        assert np.max(np.abs(c[sel, 1] - ref)) < 1e-3, key
    assert np.max(np.abs(out["tangential"][:, 1] - out["sagittal"][:, 1])) < 1e-9   # symmetric PSF: the same curve
    assert out["nyquist_cpmm"] == pytest.approx(0.5e3 / dx)


def test_anisotropic_gaussian_separates_tangential_from_sagittal_by_its_axes():
    sy, sx = 2.0, 4.0                                                # narrower along y: wider MTF along y
    g = _gauss(sy, sx)
    out = O.mtf_tangential_sagittal(g, 1.0)
    for key, s in (("tangential", sy), ("sagittal", sx)):
        c = out[key]
        want = np.exp(-2.0 * math.pi ** 2 * s ** 2 * (c[:, 0] * 1e-3) ** 2)
        assert np.max(np.abs(c[:, 1] - want)) < 1e-3, key
    sw = O.mtf_tangential_sagittal(g, 1.0, tangential_axis="x")
    assert np.allclose(sw["tangential"], out["sagittal"]) and np.allclose(sw["sagittal"], out["tangential"])
    # probe: with the axes swapped the y-slice check must fail
    c = out["tangential"]
    wrong = np.exp(-2.0 * math.pi ** 2 * sx ** 2 * (c[:, 0] * 1e-3) ** 2)
    assert np.max(np.abs(c[:, 1] - wrong)) > 0.1


def test_mtf_slices_refuse_bad_inputs():
    with pytest.raises(ValueError, match="tangential_axis"):
        O.mtf_tangential_sagittal(_gauss(2, 2, 33), 1.0, tangential_axis="z")
    with pytest.raises(ValueError):
        O.mtf_tangential_sagittal(np.zeros((8, 8)), 1.0)
    with pytest.raises(ValueError):
        O.mtf_tangential_sagittal(_gauss(2, 2, 33), -1.0)


# --------------------------------------------------------------------------- #
# through-focus MTF (ideal lens: aberration-free, so the closed form applies)
# --------------------------------------------------------------------------- #
def _hopkins(nu_over_cutoff, w20_waves):
    """Defocused circular-pupil MTF: the overlap of two pupils shifted by s (radius units), with the phase."""
    s = 2.0 * nu_over_cutoff
    if s >= 2.0:
        return 0.0
    L = 1.0 - s / 2.0

    def f(x):
        return 2.0 * math.sqrt(max(1.0 - (abs(x) + s / 2.0) ** 2, 0.0)) * math.cos(4.0 * math.pi * w20_waves * s * x)
    return abs(quad(f, -L, L, limit=200)[0]) / math.pi


@pytest.fixture(scope="module")
def tf_ideal():
    sysm = RT.lens_system([{"f": 50.0, "t": None, "ap": 2.5}], stop=0)       # f/10, aberration free
    return sysm, LI.through_focus_mtf(sysm, size=192)


def test_through_focus_mtf_of_an_ideal_lens_follows_hopkins(tf_ideal):
    sysm, r = tf_ideal
    wl_mm = sysm["wavelength_um"] * 1e-3
    F = r["fno"]
    assert F == pytest.approx(10.0) and r["cutoff_cpmm"] == pytest.approx(1e3 / (sysm["wavelength_um"] * 10.0))
    worst = 0.0
    for i, d in enumerate(r["defocus_mm"]):
        # a wave focusing at the paraxial image, seen from a sphere re-centred on the shifted plane (radius R + d)
        w20 = d / (8 * F * F * wl_mm) * 50.0 / (50.0 + d)
        for j, f in enumerate(r["frequency_cpmm"]):
            ref = _hopkins(f / r["cutoff_cpmm"], w20)
            worst = max(worst, abs(r["tangential"][i, j] - ref), abs(r["sagittal"][i, j] - ref))
    assert worst < 5e-3, worst
    assert abs(r["best_focus_mm"]) < 0.01                                      # the paraxial focus
    k = int(np.argmin(np.abs(r["defocus_mm"])))
    assert r["tangential"][k, 0] == pytest.approx(
        (2 / np.pi) * (math.acos(0.1) - 0.1 * math.sqrt(0.99)), abs=2e-3)     # in focus: the diffraction limit


def test_probe_the_paraxial_defocus_without_its_conjugate_correction_fails_the_gate(tf_ideal):
    sysm, r = tf_ideal
    wl_mm = sysm["wavelength_um"] * 1e-3
    worst = 0.0
    for i, d in enumerate(r["defocus_mm"]):
        w20 = d / (8 * r["fno"] ** 2 * wl_mm)                                   # the naive paraxial W20
        for j, f in enumerate(r["frequency_cpmm"]):
            worst = max(worst, abs(r["tangential"][i, j] - _hopkins(f / r["cutoff_cpmm"], w20)))
    assert worst > 5e-3, worst


def test_through_focus_tangential_equals_sagittal_on_axis_and_separates_with_astigmatism():
    sym = RT.lens_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 2.0},
                          {"R": "inf", "t": None, "n": 1.0}], stop=0)
    r0 = LI.through_focus_mtf(sym, field=0.0, frequency_cpmm=[10.0, 30.0], defocus_mm=[-0.5, 0.0, 0.5])
    assert np.max(np.abs(r0["tangential"] - r0["sagittal"])) < 1e-6
    r1 = LI.through_focus_mtf(sym, field=8.0, frequency_cpmm=[10.0, 30.0], defocus_mm=[-0.5, 0.0, 0.5])
    assert np.max(np.abs(r1["tangential"] - r1["sagittal"])) > 0.05              # astigmatism splits the meridians
    # the field is along +y, so the y slice is the tangential one: swapping the axis swaps the curves
    r2 = LI.through_focus_mtf(sym, field=8.0, frequency_cpmm=[10.0, 30.0], defocus_mm=[-0.5, 0.0, 0.5],
                              tangential_axis="x")
    assert np.allclose(r2["tangential"], r1["sagittal"]) and np.allclose(r2["sagittal"], r1["tangential"])


def test_through_focus_refuses_bad_inputs():
    sysm = RT.lens_system([{"f": 50.0, "t": None, "ap": 2.5}], stop=0)
    with pytest.raises(ValueError, match="Nyquist"):
        LI.through_focus_mtf(sysm, frequency_cpmm=[1e6], defocus_mm=[0.0], size=32)
    with pytest.raises(ValueError, match="frequency_cpmm"):
        LI.through_focus_mtf(sysm, frequency_cpmm=[float("nan")])
    with pytest.raises(ValueError, match="defocus_mm"):
        LI.through_focus_mtf(sysm, defocus_mm=[])
    with pytest.raises(ValueError, match=">= 0"):
        LI.through_focus_mtf(sysm, frequency_cpmm=[-1.0], defocus_mm=[0.0])
    with pytest.raises(ValueError, match="tangential_axis"):
        LI.through_focus_mtf(sysm, tangential_axis="q")
    with pytest.raises(ValueError):
        LI.through_focus_mtf({"nope": 1})


def test_ops_are_registered_with_their_declared_sorts():
    want = {"encircled_energy": (["image2d"], "pairs"), "ensquared_energy": (["image2d"], "pairs"),
            "energy_radii": (["image2d"], "table"), "mtf_tangential_sagittal": (["image2d"], "table"),
            "through_focus_mtf": (["table"], "table")}
    for name, (ins, out) in want.items():
        info = opsoptics.info(name)
        assert info["in"] == ins and info["out"] == out, (name, info)
