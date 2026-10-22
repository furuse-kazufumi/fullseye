# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Gates for lockin: per-pixel quadrature demodulation of an image sequence (2026-10-19).

External truths, none of them computed by the op under test:
  * the closed-form complex response of a sinusoid (Dirichlet kernel written out by hand) for any detuning;
  * the Rice-phase / Gaussian closed form for the noise of the amplitude and phase, scored by a Monte-Carlo with
    fixed seeds and a stated tolerance;
  * analytic surface normals of a quadratic bowl (central differences are exact on a quadratic) for the ring;
  * a brute-force per-pixel sum over the ring sources (a second implementation of the shading);
  * an explicit Crank-Nicolson finite-volume solution of the 1-D heat equation (a second implementation of the
    thermal wave) for the closed form coth(sigma L) / sigma.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import lockin as LK
import opsoptics

N = 64
FPS = 64.0


def _sine(amp, phase, dc, periods=4, n=N):
    k = np.arange(n)[:, None, None]
    return dc + amp * np.cos(2.0 * np.pi * periods * k / n + phase)


def _dirichlet(delta_bins, n):
    """(1/n) sum_k exp(j 2 pi delta k / n), written as the closed geometric sum."""
    d = np.asarray(delta_bins, np.float64)
    out = np.ones(d.shape, np.complex128)
    nz = np.abs(d) > 1e-12
    x = np.pi * d[nz] / n
    out[nz] = np.exp(1j * x * (n - 1)) * np.sin(x * n) / (n * np.sin(x))
    return out


# --------------------------------------------------------------------------- #
# 0. the ledger entry                                                           #
# --------------------------------------------------------------------------- #
def test_ledger_registers_nine_lockin_ops():
    names = opsoptics.list_ops("lockin")
    assert len(names) == 9
    assert sorted(names) == sorted(LK.__all__)
    for n in names:
        assert opsoptics.OPSOPTICS[n]["module"] == "lockin"
        assert callable(opsoptics.OPSOPTICS[n]["func"])


# --------------------------------------------------------------------------- #
# 1. closed form for a sinusoid                                                 #
# --------------------------------------------------------------------------- #
def test_sinusoid_amplitude_phase_dc_are_exact():
    rng = np.random.default_rng(101)
    amp = 0.1 + 4.0 * rng.random((6, 7))
    ph = 6.0 * rng.random((6, 7)) - 3.0
    dc = 5.0 * rng.random((6, 7)) - 2.0
    k = np.arange(N)[:, None, None]
    vid = dc + amp * np.cos(2.0 * np.pi * 4 * k / N + ph)
    r = LK.lockin_demodulate(vid, 4.0 * FPS / N, FPS)
    assert r["amplitude"].shape == (6, 7)
    assert np.max(np.abs(r["amplitude"] - amp)) < 1e-12
    assert np.max(np.abs(np.angle(np.exp(1j * (r["phase"] - ph))))) < 1e-12
    assert np.max(np.abs(r["dc"] - dc)) < 1e-12
    assert np.max(np.abs(r["in_phase"] - amp * np.cos(ph))) < 1e-12
    assert np.max(np.abs(r["quadrature"] - amp * np.sin(ph))) < 1e-12
    assert r["periods"] == pytest.approx(4.0, abs=1e-12)
    assert r["leak_image"] < 1e-15 and r["leak_dc"] < 1e-15
    assert np.array_equal(LK.lockin_amplitude(vid, 4.0 * FPS / N, FPS), r["amplitude"])
    assert np.array_equal(LK.lockin_phase(vid, 4.0 * FPS / N, FPS), r["phase"])


def test_other_frequencies_and_a_steady_background_are_rejected_exactly():
    vid = _sine(1.0, 0.3, 7.0) + _sine(3.0, 1.0, 0.0, periods=9) + _sine(2.0, -1.0, 0.0, periods=1)
    r = LK.lockin_demodulate(vid, 4.0 * FPS / N, FPS)
    assert abs(r["amplitude"][0, 0] - 1.0) < 1e-12 and abs(r["dc"][0, 0] - 7.0) < 1e-12


def test_detuned_signal_matches_the_hand_written_dirichlet_kernel():
    """x = A cos(2 pi (f + d) t + phi): z = A e^{j phi} D(d) + A e^{-j phi} conj(D(2 f + d)), D = Dirichlet kernel."""
    rng = np.random.default_rng(7)
    f_bins = 8
    n = 128
    worst = 0.0
    cases = 0
    for d in (0.0, 0.1, 0.25, 0.5, 0.9, 1.0, 1.5, 2.5, -0.4, -1.2):
        for _ in range(3):
            a, phi = 0.5 + rng.random(), 6.0 * rng.random() - 3.0
            k = np.arange(n)
            x = a * np.cos(2.0 * np.pi * (f_bins + d) * k / n + phi)
            r = LK.lockin_demodulate(np.tile(x[:, None, None], (1, 4, 4)), f_bins * FPS / n, FPS)
            z = r["in_phase"][0, 0] + 1j * r["quadrature"][0, 0]
            want = a * np.exp(1j * phi) * _dirichlet(d, n) + a * np.exp(-1j * phi) * np.conj(_dirichlet(2 * f_bins + d, n))
            worst = max(worst, abs(z - want))
            cases += 1
    assert cases == 30
    assert worst < 1e-12


def test_reference_detuning_rolls_off_as_sinc():
    """The gain at a frequency offset of Delta f over a window T is |sinc(Delta f T)|: 0.5 at 0.6033, zero at 1."""
    n = 1024
    periods = 64
    k = np.arange(n)
    gains = {}
    for dt_ in (0.2, 0.6033, 1.0, 1.5, 2.0):
        x = np.cos(2.0 * np.pi * (periods + dt_) * k / n)                  # offset of dt_ bins = Delta f T
        r = LK.lockin_demodulate(np.tile(x[:, None, None], (1, 4, 4)), periods * FPS / n, FPS)
        gains[dt_] = r["amplitude"][0, 0]
    sinc = lambda v: abs(math.sin(math.pi * v) / (math.pi * v))             # noqa: E731
    assert len(gains) == 5
    for dt_, g in gains.items():
        assert abs(g - sinc(dt_)) < 4e-3, (dt_, g, sinc(dt_))      # the rest is the conjugate image, about 1 / (4 pi 64)
    assert abs(gains[0.6033] - 0.5) < 5e-3
    assert gains[1.0] < 3e-3 and gains[2.0] < 3e-3
    assert gains[0.2] > gains[0.6033] > gains[1.5] > gains[1.0]


# --------------------------------------------------------------------------- #
# 2. the window is declared or the op refuses                                   #
# --------------------------------------------------------------------------- #
def test_fractional_period_count_is_refused_for_rect_and_declared_for_hann():
    vid = _sine(2.5, 0.7, 1.5)[:60]                                          # 3.75 periods
    with pytest.raises(ValueError, match="3.75"):
        LK.lockin_demodulate(vid, 4.0 * FPS / N, FPS)
    with pytest.raises(ValueError, match="hann"):
        LK.lockin_amplitude(vid, 4.0 * FPS / N, FPS)
    r = LK.lockin_demodulate(vid, 4.0 * FPS / N, FPS, "hann")
    err = abs(r["amplitude"][0, 0] - 2.5)
    bound = 2.5 * r["leak_image"] + 2.0 * 1.5 * r["leak_dc"] + 1e-15
    assert r["window"] == "hann" and abs(r["periods"] - 3.75) < 1e-12
    assert 1e-4 < err <= bound < 0.05          # the error is real, it is within what the table declares, and it is small


def test_hann_costs_the_stated_noise_and_rect_has_none_of_that_leakage():
    r = LK.lockin_demodulate(_sine(1.0, 0.2, 0.0), 4.0 * FPS / N, FPS, "hann")
    assert r["leak_image"] < 1e-15 and r["leak_dc"] < 1e-15
    assert abs(r["amplitude"][0, 0] - 1.0) < 1e-12
    a = LK.lockin_noise_floor(N, 1.0, 1.0, "rect")["component_std"]
    b = LK.lockin_noise_floor(N, 1.0, 1.0, "hann")["component_std"]
    assert a == pytest.approx(math.sqrt(2.0 / N), rel=1e-12) and b == pytest.approx(math.sqrt(3.0 / N), rel=1e-12)


# --------------------------------------------------------------------------- #
# 3. noise: amplitude and phase from the SNR                                     #
# --------------------------------------------------------------------------- #
def _mc_phase_std(amp, sigma, window, seed, n=N, shape=(200, 200)):
    rng = np.random.default_rng(seed)
    vid = _sine(amp, 0.4, 0.0, n=n) + rng.normal(0.0, sigma, (n,) + shape)
    r = LK.lockin_demodulate(vid, 4.0 * FPS / n, FPS, window)
    err = np.angle(np.exp(1j * (r["phase"] - 0.4)))
    return float(np.std(err)), float(np.std(r["amplitude"])), float(np.mean(r["in_phase"]) - amp * math.cos(0.4))


def test_phase_variance_under_noise_matches_the_rice_closed_form():
    cases = [(8.0, 1), (4.0, 2), (1.0, 3), (0.3, 4), (0.1, 5)]     # amplitude, seed (noise sigma 1, N = 64): SNR 45 ... 0.57
    assert len(cases) == 5
    for amp, seed in cases:
        mc, _, _ = _mc_phase_std(amp, 1.0, "rect", seed)
        cf = LK.lockin_noise_floor(N, 1.0, amp)
        assert abs(mc / cf["phase_std_exact"] - 1.0) < 0.03, (amp, mc, cf["phase_std_exact"])
    # the small-noise value is the exact one at high SNR and is wrong at low SNR (the exact form is needed)
    hi = LK.lockin_noise_floor(N, 1.0, 8.0)
    lo = LK.lockin_noise_floor(N, 1.0, 0.2)                    # SNR 1.1
    assert abs(hi["phase_std_small_noise"] / hi["phase_std_exact"] - 1.0) < 0.01
    assert abs(lo["phase_std_small_noise"] / lo["phase_std_exact"] - 1.0) > 0.1
    # and the limit with no signal: pi / sqrt(3)
    nosig = LK.lockin_noise_floor(N, 1.0, 1e-6)
    assert abs(nosig["phase_std_exact"] - math.pi / math.sqrt(3.0)) < 2e-3


def test_amplitude_noise_and_the_hann_window_match_the_closed_form():
    _, a_std, bias = _mc_phase_std(8.0, 1.0, "rect", 11)
    cf = LK.lockin_noise_floor(N, 1.0, 8.0)
    assert abs(a_std / cf["amplitude_std"] - 1.0) < 0.03
    assert abs(bias) < 4.0 * cf["component_std"] / math.sqrt(200 * 200)         # the estimate is unbiased
    mc_h, a_h, _ = _mc_phase_std(8.0, 1.0, "hann", 12)
    ch = LK.lockin_noise_floor(N, 1.0, 8.0, "hann")
    assert abs(mc_h / ch["phase_std_exact"] - 1.0) < 0.03 and abs(a_h / ch["amplitude_std"] - 1.0) < 0.03


def test_noise_floor_refusals():
    for bad in ((2, 1.0, 1.0), (64, -1.0, 1.0), (64, 1.0, 0.0), (64, float("nan"), 1.0), (64.5, 1.0, 1.0)):
        with pytest.raises(ValueError):
            LK.lockin_noise_floor(*bad)
    with pytest.raises(ValueError, match="window"):
        LK.lockin_noise_floor(64, 1.0, 1.0, "boxcar")


# --------------------------------------------------------------------------- #
# 4. multipole ring illumination -> normals                                      #
# --------------------------------------------------------------------------- #
def _bowl(n=48):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    x, y = xx - n / 2, yy - n / 2
    a, b, c, d, e = 0.012, 0.008, 0.004, 0.05, -0.03                 # h = a x^2 + b y^2 + c x y + d x + e y
    h = a * x * x + b * y * y + c * x * y + d * x + e * y
    return h, 2 * a * x + c * y + d, 2 * b * y + c * x + e          # analytic h_x, h_y


def _angle_deg(gx, gy, tx, ty):
    n1 = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    n2 = np.stack([-tx, -ty, np.ones_like(tx)], -1)
    # atan2(|n1 x n2|, n1 . n2): acos((n1 . n2)) has a sqrt(eps) floor near 0 (about 1e-6 degrees)
    return np.degrees(np.arctan2(np.linalg.norm(np.cross(n1, n2), axis=-1), np.sum(n1 * n2, -1)))


def test_ring_normals_recover_known_normals_independently_of_albedo():
    h, gx, gy = _bowl()
    inner = (slice(1, -1), slice(1, -1))                           # np.gradient is exact on a quadratic in the interior
    tilt = np.degrees(np.arctan(np.hypot(gx, gy)))[inner]
    assert tilt.max() > 25.0 and tilt.max() < 60.0
    rng = np.random.default_rng(3)
    errs = []
    for zen, alb in ((20.0, None), (20.0, 0.1 + 0.9 * rng.random(h.shape)), (30.0, 0.05 + rng.random(h.shape))):
        vid = LK.lockin_ring_synthesize(h, zen, 8, 1, 16, 3, albedo=alb)
        d = LK.lockin_demodulate(vid, 1.0, 16.0)
        nrm = LK.lockin_ring_normals(d, zen)
        assert nrm["valid"][inner].all()
        e = _angle_deg(nrm["height_gradient_x"], nrm["height_gradient_y"], gx, gy)[inner]
        errs.append(float(e.max()))
        assert np.max(np.abs(np.linalg.norm(nrm["normal"], axis=-1)[inner] - 1.0)) < 1e-12
    assert len(errs) == 3
    assert max(errs) < 1e-9, errs                                  # degrees


def test_ring_physics_matches_a_brute_force_sum_over_the_sources():
    h, _, _ = _bowl(16)
    s, z, fpp = 5, math.radians(25.0), 8
    vid = LK.lockin_ring_synthesize(h, 25.0, s, 1, fpp, 2, albedo=np.full(h.shape, 0.5))
    gy, gx = np.gradient(h)
    worst = 0.0
    for (i, j) in ((3, 4), (8, 8), (12, 5), (7, 13)):
        n = np.array([-gx[i, j], -gy[i, j], 1.0])
        n /= np.linalg.norm(n)
        for k in range(2 * fpp):
            v = 0.0
            for q in range(s):
                th = 2.0 * math.pi * q / s
                l = np.array([math.sin(z) * math.cos(th), math.sin(z) * math.sin(th), math.cos(z)])
                v += 0.5 * max(0.0, float(n @ l)) * (1.0 + math.cos(2.0 * math.pi * k / fpp - th)) / s
            worst = max(worst, abs(v - vid[k, i, j]))
    assert worst < 1e-14


def test_multipole_orders_other_than_one_carry_no_relief_signal_for_a_lambertian_surface():
    h, _, _ = _bowl()
    inner = (slice(1, -1), slice(1, -1))
    d1 = LK.lockin_demodulate(LK.lockin_ring_synthesize(h, 20.0, 8, 1, 16, 2), 1.0, 16.0)
    d2 = LK.lockin_demodulate(LK.lockin_ring_synthesize(h, 20.0, 8, 2, 16, 2), 1.0, 16.0)
    d0 = LK.lockin_demodulate(LK.lockin_ring_synthesize(h, 20.0, 8, 0, 16, 2), 1.0, 16.0)
    assert d1["amplitude"][inner].min() >= 0.0 and d1["amplitude"][inner].max() > 0.02
    assert np.max(d2["amplitude"][inner]) < 1e-14                  # quadrupole: nothing for a Lambertian relief
    assert np.max(np.abs(d0["amplitude"][inner] - d0["dc"][inner])) < 1e-14   # monopole: amplitude = DC (no direction)


def test_normals_refuse_the_shadowed_pixels_instead_of_inventing_a_normal():
    yy, xx = np.mgrid[0:40, 0:40].astype(np.float64)
    h = 0.9 * xx                                                  # a 42-degree ramp
    d = LK.lockin_demodulate(LK.lockin_ring_synthesize(h, 60.0, 8, 1, 16, 2), 1.0, 16.0)
    nrm = LK.lockin_ring_normals(d, 60.0)                         # shadow limit: tilt < 30 degrees; this ramp is 42 degrees
    assert not nrm["valid"][5:-5, 5:-5].any()
    assert np.isnan(nrm["normal"][5:-5, 5:-5]).all() and np.isnan(nrm["tilt_deg"][5:-5, 5:-5]).all()
    flat = LK.lockin_demodulate(LK.lockin_ring_synthesize(0.0 * h, 60.0, 8, 1, 16, 2), 1.0, 16.0)
    ok = LK.lockin_ring_normals(flat, 60.0)
    assert ok["valid"].all() and np.max(np.abs(ok["tilt_deg"])) < 1e-9
    with pytest.raises(ValueError, match="demod"):
        LK.lockin_ring_normals({"amplitude": d["amplitude"]}, 60.0)
    with pytest.raises(ValueError, match="zenith"):
        LK.lockin_ring_normals(d, 90.0)


def test_ring_noise_needs_an_explicit_seed_and_is_reproducible():
    h, _, _ = _bowl(16)
    with pytest.raises(ValueError, match="seed"):
        LK.lockin_ring_synthesize(h, 20.0, 8, 1, 16, 2, noise_sigma=0.01)
    a = LK.lockin_ring_synthesize(h, 20.0, 8, 1, 16, 2, noise_sigma=0.01, seed=1)
    b = LK.lockin_ring_synthesize(h, 20.0, 8, 1, 16, 2, noise_sigma=0.01, seed=1)
    c = LK.lockin_ring_synthesize(h, 20.0, 8, 1, 16, 2, noise_sigma=0.01, seed=2)
    assert np.array_equal(a, b) and not np.array_equal(a, c)
    for bad in ({"n_sources": 2}, {"multipole": 8}, {"zenith_deg": 90.0}, {"frames_per_period": 2}):
        kw = dict(height=h, zenith_deg=20.0, n_sources=8, multipole=1, frames_per_period=16, n_periods=2)
        kw.update(bad)
        with pytest.raises(ValueError):
            LK.lockin_ring_synthesize(**kw)


# --------------------------------------------------------------------------- #
# 5. coded intermittent illumination -> separation                              #
# --------------------------------------------------------------------------- #
def _coded_scene(n=32, codes=None, ambient=None):
    rng = np.random.default_rng(21)
    lights = [rng.random((10, 12)) for _ in range(3)]
    amb = 5.0 * rng.random((10, 12)) if ambient is None else ambient
    c = LK.lockin_walsh_codes(n, 3) if codes is None else codes
    vid = amb[None] + sum(lt[None] * ((1.0 + c[i])[:, None, None] / 2.0) for i, lt in enumerate(lights))
    return vid, lights, amb, c


def test_walsh_codes_are_orthogonal_zero_mean_and_plus_minus_one():
    c = LK.lockin_walsh_codes(32, 5)
    assert c.shape == (5, 32)
    assert set(np.unique(c)) == {-1.0, 1.0}
    g = c @ c.T
    assert np.array_equal(g, 32.0 * np.eye(5)) and np.all(c.sum(axis=1) == 0.0)
    for bad in ((12, 3), (1, 1), (8, 8), (8, 0)):
        with pytest.raises(ValueError):
            LK.lockin_walsh_codes(*bad)


def test_three_coded_lights_and_the_ambient_are_separated_exactly():
    vid, lights, amb, c = _coded_scene()
    r = LK.lockin_separate(vid, c)
    assert r["coefficients"].shape == (3, 10, 12) and r["n_codes"] == 3
    for i in range(3):
        assert np.max(np.abs(r["on_image"][i] - lights[i])) < 1e-12
    assert np.max(np.abs(r["dc"] - (amb + sum(lights) / 2.0))) < 1e-12
    assert r["residual_rms"].max() < 1e-12 and abs(r["condition"] - 1.0) < 1e-12
    # a non-orthogonal pair of codes is still separated by the least-squares fit
    c2 = np.stack([c[0], 0.5 * c[0] + 0.5 * c[1]])
    v2 = amb[None] + lights[0][None] * ((1 + c2[0])[:, None, None] / 2) + lights[1][None] * ((1 + c2[1])[:, None, None] / 2)
    r2 = LK.lockin_separate(v2, c2)
    assert np.max(np.abs(r2["on_image"][0] - lights[0])) < 1e-10 and np.max(np.abs(r2["on_image"][1] - lights[1])) < 1e-10
    assert r2["condition"] > 1.5


def test_a_flicker_the_codes_do_not_carry_shows_in_the_residual_and_the_error_is_bounded():
    n = 32
    vid, lights, amb, c = _coded_scene(n)
    k = np.arange(n)[:, None, None]
    flick = vid + 0.8 * np.cos(2.0 * np.pi * 5 * k / n)                     # a mains-like flicker, 5 cycles in the window
    r = LK.lockin_separate(flick, c)
    want = 0.8 * np.cos(2.0 * np.pi * 5 * np.arange(n) / n)
    leak = [abs(float(c[i] @ want)) / n * 2.0 for i in range(3)]               # the flicker's projection on each code
    for i in range(3):
        err = np.max(np.abs(r["on_image"][i] - lights[i]))
        assert abs(err - leak[i]) < 1e-12
    assert r["residual_rms"].min() > 0.1                                       # the flicker is visible as residual
    assert LK.lockin_separate(vid, c)["residual_rms"].max() < 1e-12


def test_dependent_constant_or_misfit_codes_are_refused():
    vid, _, _, c = _coded_scene()
    with pytest.raises(ValueError, match="dependent"):
        LK.lockin_separate(vid, np.stack([c[0], c[0]]))
    with pytest.raises(ValueError, match="dependent"):
        LK.lockin_separate(vid, np.stack([c[0], c[1], c[0] + c[1]]))
    with pytest.raises(ValueError, match="constant"):
        LK.lockin_separate(vid, np.ones((1, 32)))
    with pytest.raises(ValueError, match="codes must be"):
        LK.lockin_separate(vid, c[:, :16])
    with pytest.raises(ValueError, match="non-finite"):
        LK.lockin_separate(vid, np.where(c > 0, np.nan, c))


# --------------------------------------------------------------------------- #
# 6. lock-in thermography                                                         #
# --------------------------------------------------------------------------- #
def _fv_surface_response(ratio, n=300, steps_per_period=400, periods=10):
    """Second implementation: Crank-Nicolson finite volume for T_t = T_xx (alpha = k = 1), flux cos(w t) in at x = 0,
    insulated at x = L = ratio * mu with mu = sqrt(2 / w). Returns the complex surface amplitude of the last period."""
    w = 2.0 * math.pi
    mu = math.sqrt(2.0 / w)
    big_l = ratio * mu
    dx = big_l / n
    lap = np.zeros((n, n))
    for i in range(n):
        lap[i, i] = -2.0
        if i > 0:
            lap[i, i - 1] = 1.0
        if i < n - 1:
            lap[i, i + 1] = 1.0
    lap[0, 0] = -1.0
    lap[-1, -1] = -1.0                                                          # insulated back face
    lap /= dx * dx
    dt = 1.0 / steps_per_period
    eye = np.eye(n)
    a_inv = np.linalg.inv(eye - 0.5 * dt * lap)
    b = eye + 0.5 * dt * lap
    src = np.zeros(n)
    src[0] = 1.0 / dx                                                           # flux density 1 into cell 0
    t = np.zeros(n)
    ts = []
    for step in range(steps_per_period * periods):
        tm = step * dt
        f = 0.5 * (math.cos(w * tm) + math.cos(w * (tm + dt))) * src
        t = a_inv @ (b @ t + dt * f)
        ts.append(t[0] + 0.5 * dx * math.cos(w * (tm + dt)))                    # extrapolate cell centre -> surface (k = 1)
    last = np.asarray(ts[-steps_per_period:])
    tt = (np.arange(steps_per_period) + 1) / steps_per_period
    z = 2.0 * np.mean(last * np.exp(-1j * w * tt))
    return z


def test_thermal_wave_closed_form_agrees_with_an_explicit_finite_volume_solution():
    worst_ph, worst_amp, cases = 0.0, 0.0, 0
    for ratio in (0.25, 0.7, 1.5):
        z_fv = _fv_surface_response(ratio)
        sig_l = (1.0 + 1.0j) * ratio                                           # sigma L with L = ratio * mu
        mu = math.sqrt(2.0 / (2.0 * math.pi))
        z_cf = (1.0 / np.tanh(sig_l)) / ((1.0 + 1.0j) / mu)                  # q coth(sigma L) / (k sigma), k = q = 1
        worst_ph = max(worst_ph, abs(math.degrees(np.angle(z_fv / z_cf))))
        worst_amp = max(worst_amp, abs(abs(z_fv) / abs(z_cf) - 1.0))
        cases += 1
    assert cases == 3
    assert worst_ph < 0.1 and worst_amp < 5e-3, (worst_ph, worst_amp)


def test_thermal_wave_op_phase_is_the_closed_form_and_ignores_uneven_heating():
    alpha, f_heat = 4.2e-7, 0.2
    mu = math.sqrt(alpha / (math.pi * f_heat))
    depth = np.array([[0.1, 0.5, 1.0, 2.0], [3.0, 5.0, 20.0, 100.0]] * 2) * mu * 1e0
    vid = LK.lockin_thermal_wave(depth, alpha, f_heat, 16, 3)
    assert vid.shape == (48, 4, 4)
    d = LK.lockin_demodulate(vid, 1.0, 16.0)
    sig_l = (1.0 + 1.0j) * depth / mu                                     # mu = sqrt(2 alpha / w) = sqrt(alpha / (pi f))
    want = np.exp(-0.25j * math.pi) / np.tanh(sig_l)
    assert np.max(np.abs(np.angle(np.exp(1j * (d["phase"] - np.angle(want)))))) < 1e-12
    assert np.max(np.abs(d["amplitude"] / np.abs(want) - 1.0)) < 1e-12
    assert abs(math.degrees(d["phase"][3, 3]) + 45.0) < 1e-6               # a deep layer: -45 degrees
    assert math.degrees(d["phase"][0, 0]) < -85.0                           # a thin layer tends to -90
    nu = 0.3 + 1.4 * np.random.default_rng(5).random(depth.shape)
    d2 = LK.lockin_demodulate(LK.lockin_thermal_wave(depth, alpha, f_heat, 16, 3, nonuniformity=nu), 1.0, 16.0)
    assert np.max(np.abs(d2["phase"] - d["phase"])) < 1e-12                  # phase: untouched
    assert np.max(np.abs(d2["amplitude"] / d["amplitude"] - nu)) < 1e-12    # amplitude: carries the unevenness


def test_thermal_wave_refusals():
    ok = np.full((4, 4), 1e-3)
    for bad in (np.zeros((4, 4)), -ok, np.full((4, 4), np.nan), np.ones(4)):
        with pytest.raises(ValueError):
            LK.lockin_thermal_wave(bad, 4.2e-7, 0.1, 16, 2)
    with pytest.raises(ValueError):
        LK.lockin_thermal_wave(ok, 0.0, 0.1, 16, 2)
    with pytest.raises(ValueError, match="nonuniformity"):
        LK.lockin_thermal_wave(ok, 4.2e-7, 0.1, 16, 2, nonuniformity=np.zeros((4, 4)))


# --------------------------------------------------------------------------- #
# 7. refusals of the demodulator                                                  #
# --------------------------------------------------------------------------- #
def test_demodulate_refuses_what_would_be_silently_wrong():
    vid = _sine(1.0, 0.0, 0.0)
    f4 = 4.0 * FPS / N
    cases = [
        (vid, FPS / 2.0, FPS, "Nyquist"),                       # the Nyquist frequency itself
        (vid, 0.9 * FPS, FPS, "Nyquist"),
        (vid, 0.5 * FPS / N, FPS, "at least 1"),                # half a period
        (vid, 0.0, FPS, "f_ref"),
        (vid, float("nan"), FPS, "f_ref"),
        (vid, f4, 0.0, "fps"),
        (vid[:1], f4, FPS, "frames"),
        (vid[0], f4, FPS, "clip"),
        (np.where(vid > 0, np.nan, vid), f4, FPS, "non-finite"),
        (vid + 1j, f4, FPS, "complex"),
    ]
    assert len(cases) == 10
    for v, f, fps, msg in cases:
        with pytest.raises(ValueError, match=msg):
            LK.lockin_demodulate(v, f, fps)
    with pytest.raises(ValueError, match="window"):
        LK.lockin_demodulate(vid, f4, FPS, "triangle")
