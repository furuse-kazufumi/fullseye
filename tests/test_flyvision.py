# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""flyvision — closed-form ground truth for the fly optic-lobe vision pathway.

Every operator here has an analytic identity, so this suite scores against exact
formulae rather than golden files:

  * the hexagonal lattice has ``n = 3*radius*(radius+1)+1`` ommatidia and, for the
    boxeye geometry, a diagonal-to-axial spacing ratio of 1.118;
  * a Gaussian-acceptance resample transfers an azimuthal grating by exactly
    ``exp(-pi^2 drho^2 nu^2 / (4 ln2))``, measured at four wavelengths;
  * the Hassenstein-Reichardt mean response is
    ``dI^2 sin(psi) omega tau/(1+(omega tau)^2)``, zero at ``lambda = 2 dphi`` and
    peaked at ``f = 1/(2 pi tau)``;
  * the LGMD/eta response peaks ``alpha*l/|v|`` before collision at an angle of
    exactly ``2 atan(1/alpha)`` = 24.0 degrees;
  * the two time-to-contact object models both recover ``d/|v|`` and differ by
    33% at a 60-degree subtense;
  * the direction-selectivity index is 1 for a single direction and 0 for an
    isotropic response.

Every randomised check fixes the seed and states its sample size.
"""
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import flyvision as fv                                       # noqa: E402
import opsflyvision                                          # noqa: E402


# --------------------------------------------------------------------------- #
# 1. lattice                                                                   #
# --------------------------------------------------------------------------- #
class TestLattice:
    def test_ommatidia_count_is_the_closed_form(self):
        for r in (1, 3, 8, 15, 30):
            lat = fv.fly_hex_lattice(radius=r)
            assert lat["dirs"].shape[0] == 3 * r * (r + 1) + 1

    def test_directions_are_unit_vectors(self):
        lat = fv.fly_hex_lattice(radius=10, az0_deg=12.0, el0_deg=-7.0)
        assert np.allclose(np.linalg.norm(lat["dirs"], axis=1), 1.0, atol=1e-12)

    def test_azimuth_is_left_positive_elevation_is_up(self):
        lat = fv.fly_hex_lattice(radius=1)
        c = np.where((lat["uv"][:, 0] == 0) & (lat["uv"][:, 1] == 0))[0][0]
        assert np.allclose(lat["dirs"][c], [1.0, 0.0, 0.0])   # centre = forward

    def test_boxeye_diagonal_is_1_118_times_the_axial_spacing(self):
        box = fv.fly_hex_lattice(radius=5, geometry="boxeye")
        dirs, uv = box["dirs"], box["uv"]
        c = np.where((uv[:, 0] == 0) & (uv[:, 1] == 0))[0][0]
        d = np.degrees(np.arccos(np.clip(dirs @ dirs[c], -1.0, 1.0)))
        d[c] = np.inf
        near = np.sort(d)[:6]
        assert abs(near.max() / near.min() - 1.118) < 0.005

    def test_regular_geometry_is_isotropic(self):
        reg = fv.fly_hex_lattice(radius=5, geometry="regular")
        dirs, uv = reg["dirs"], reg["uv"]
        c = np.where((uv[:, 0] == 0) & (uv[:, 1] == 0))[0][0]
        d = np.degrees(np.arccos(np.clip(dirs @ dirs[c], -1.0, 1.0)))
        d[c] = np.inf
        near = np.sort(d)[:6]
        assert near.max() / near.min() < 1.001


# --------------------------------------------------------------------------- #
# 2. resample — the modulation transfer identity                              #
# --------------------------------------------------------------------------- #
DRHO = 8.23


def _mtf(lmbda):
    return np.exp(-np.pi ** 2 * DRHO ** 2 * (1.0 / lmbda) ** 2 / (4.0 * np.log(2.0)))


def _resample_grating(lmbda, radius=10, dphi=4.0, npix=201, fov=110.0):
    """Resample a pinhole azimuthal sinusoid of wavelength *lmbda* deg and return
    the measured MTF from equatorial ommatidia."""
    lat = fv.fly_hex_lattice(radius=radius, dphi_deg=dphi)
    az, el = lat["az_rad"], lat["el_rad"]
    h = w = npix
    f = (h / 2.0) / np.tan(np.deg2rad(fov) / 2.0)
    _yy, xx = np.mgrid[0:h, 0:w].astype(float)
    xc = (xx + 0.5 - w / 2.0) / f
    azpix = np.degrees(np.arctan2(xc, 1.0))
    img = 0.5 + 0.5 * np.cos(2.0 * np.pi * azpix / lmbda)
    sig = fv.fly_hex_resample(img, lat, drho_deg=DRHO, fov_deg=fov)
    phi = 2.0 * np.pi * np.degrees(az) / lmbda
    good = (np.abs(np.degrees(el)) < 3.0) & (np.abs(np.cos(phi)) > 0.5)
    return float(np.median((sig[good] - 0.5) / (0.5 * np.cos(phi[good]))))


class TestResampleMTF:
    @pytest.mark.parametrize("lmbda", [15.0, 25.0, 40.0, 80.0])
    def test_grating_amplitude_follows_the_analytic_mtf(self, lmbda):
        meas = _resample_grating(lmbda)
        assert abs(meas - _mtf(lmbda)) < 0.05

    def test_resample_refuses_a_lattice_that_reaches_outside_the_image(self):
        # a wide lattice with a narrow field of view leaves ommatidia uncovered
        lat = fv.fly_hex_lattice(radius=10, dphi_deg=6.0)
        with pytest.raises(ValueError, match="outside the image"):
            fv.fly_hex_resample(np.random.default_rng(0).random((32, 32)), lat,
                                fov_deg=20.0)

    def test_resample_returns_one_value_per_ommatidium(self):
        lat = fv.fly_hex_lattice(radius=4)
        sig = fv.fly_hex_resample(np.random.default_rng(1).random((64, 64)), lat,
                                  fov_deg=120.0)
        assert sig.shape == (lat["dirs"].shape[0],)


# --------------------------------------------------------------------------- #
# 3. motion — Hassenstein-Reichardt                                            #
# --------------------------------------------------------------------------- #
class TestEMD:
    def _mean(self, f, tau=0.05, dphi=4.0, lam=16.0, dt=0.0005, T=20000):
        t = np.arange(T) * dt
        psi = 2.0 * np.pi * dphi / lam
        om = 2.0 * np.pi * f
        a = np.cos(om * t)
        b = np.cos(om * t - psi)
        r = fv.fly_emd_response(a, b, tau_s=tau, dt_s=dt)
        pred = np.sin(psi) * om * tau / (1.0 + (om * tau) ** 2)
        return float(r[T // 2:].mean()), pred

    def test_mean_response_matches_the_correlator_identity(self):
        for f in (2.0, 1.0 / (2 * np.pi * 0.05), 8.0):
            meas, pred = self._mean(f)
            assert abs(meas - pred) < 0.05 * abs(pred)

    def test_response_is_zero_when_wavelength_is_twice_the_spacing(self):
        # lambda = 2*dphi -> psi = pi -> sin(psi) = 0
        dt, tau, dphi = 0.0005, 0.05, 4.0
        t = np.arange(20000) * dt
        psi = 2.0 * np.pi * dphi / (2.0 * dphi)
        a = np.cos(2 * np.pi * 2.0 * t)
        b = np.cos(2 * np.pi * 2.0 * t - psi)
        r = fv.fly_emd_response(a, b, tau_s=tau, dt_s=dt)
        assert abs(r[10000:].mean()) < 1e-3

    def test_optimum_frequency_is_independent_of_wavelength(self):
        # f_opt = 1/(2 pi tau); the response peaks there for any lambda
        tau = 0.05
        fopt = 1.0 / (2 * np.pi * tau)
        best = {}
        for lam in (12.0, 24.0):
            vals = {f: self._mean(f, tau=tau, lam=lam)[0] for f in
                    (0.5, 1.5, fopt, 6.0, 12.0)}
            best[lam] = max(vals, key=vals.get)
        assert best[12.0] == fopt and best[24.0] == fopt


# --------------------------------------------------------------------------- #
# 4. looming                                                                   #
# --------------------------------------------------------------------------- #
class TestLGMD:
    def test_peak_time_and_angle_match_gabbiani(self):
        dt, alpha, ratio = 0.001, 4.7, 0.05      # ratio = l/|v|, seconds
        t = np.arange(0.0, 2.0 - dt, dt)
        ttc = 2.0 - t
        theta = 2.0 * np.arctan(ratio / ttc)
        eta = fv.fly_lgmd_eta(theta, dt, alpha=alpha)
        k = int(np.argmax(eta))
        assert abs(ttc[k] - alpha * ratio) < 2e-3               # Eq. 5
        assert abs(np.degrees(theta[k]) - np.degrees(2 * np.arctan(1 / alpha))) < 0.1


class TestTau:
    def test_both_models_recover_distance_over_speed(self):
        dt, l, v = 0.001, 0.05, 1.0
        t = np.arange(0.0, 0.9, dt)
        d = 1.0 - v * t
        th_s = 2.0 * np.arcsin(np.clip(l / d, 0.0, 0.9999))
        th_d = 2.0 * np.arctan(l / d)
        k = len(t) // 2
        tau_s = fv.fly_tau_from_expansion(th_s, dt, shape="sphere")
        tau_d = fv.fly_tau_from_expansion(th_d, dt, shape="disk")
        assert abs(tau_s[k] - d[k] / v) < 1e-3
        assert abs(tau_d[k] - d[k] / v) < 1e-3

    def test_disk_and_sphere_differ_by_33_percent_at_60_degrees(self):
        disk = np.sin(np.radians(60.0))
        sphere = 2.0 * np.tan(np.radians(30.0))
        assert abs(sphere / disk - 4.0 / 3.0) < 1e-9

    def test_non_expanding_angle_returns_nan_not_a_number(self):
        # a static angle has no time-to-contact: NaN is the documented return
        tau = fv.fly_tau_from_expansion(np.full(9, 0.5), 0.001)
        assert np.all(np.isnan(tau))


# --------------------------------------------------------------------------- #
# 5. integrate — horizontal-system readout                                    #
# --------------------------------------------------------------------------- #
class TestHSReadout:
    def test_preferred_only_upper_field_reads_plus_one(self):
        lat = fv.fly_hex_lattice(radius=4)
        n = lat["dirs"].shape[0]
        upper = np.degrees(lat["el_rad"]) > 0.0
        resp = np.zeros((4, n))
        resp[0, upper] = 1.0
        resp[1, upper] = 1.0             # both preferred rows active, anti silent
        out = fv.fly_hs_readout(resp, lat, n_pref=2, el_min_deg=0.0)
        assert abs(out - 1.0) < 1e-4

    def test_anti_preferred_only_reads_minus_one(self):
        lat = fv.fly_hex_lattice(radius=4)
        n = lat["dirs"].shape[0]
        upper = np.degrees(lat["el_rad"]) > 0.0
        resp = np.zeros((4, n))
        resp[2, upper] = 1.0
        resp[3, upper] = 1.0
        out = fv.fly_hs_readout(resp, lat, n_pref=2, el_min_deg=0.0)
        assert abs(out + 1.0) < 1e-4

    def test_no_upper_field_raises(self):
        lat = fv.fly_hex_lattice(radius=4)
        n = lat["dirs"].shape[0]
        top = float(np.degrees(lat["el_rad"].max()))
        with pytest.raises(ValueError, match="upper visual field"):
            fv.fly_hs_readout(np.ones((4, n)), lat, n_pref=2,
                              el_min_deg=top + 10.0)


# --------------------------------------------------------------------------- #
# 6. stimulus — the 1/f sky                                                    #
# --------------------------------------------------------------------------- #
class TestSky:
    def test_texture_is_confined_to_the_band(self):
        sky = fv.fly_sky_1f(width=1024, height=256, seed=3)
        h = sky.shape[0]
        el = 90.0 - 180.0 * (np.arange(h) + 0.5) / h
        inb = sky[np.argmin(np.abs(el - 40.0))].std()
        outb = sky[np.argmin(np.abs(el + 30.0))].std()
        assert inb > 5.0 * outb

    def test_azimuth_spectrum_is_one_over_f(self):
        sky = fv.fly_sky_1f(width=2048, height=256, seed=3)
        h = sky.shape[0]
        el = 90.0 - 180.0 * (np.arange(h) + 0.5) / h
        row = sky[np.argmin(np.abs(el - 50.0))]
        r = row - row.mean()
        power = np.abs(np.fft.rfft(r)) ** 2
        k = np.arange(power.size)
        sel = (k >= 2) & (k <= power.size // 8)
        slope = np.polyfit(np.log(k[sel]), np.log(power[sel]), 1)[0]
        assert abs(slope + 2.0) < 0.4


# --------------------------------------------------------------------------- #
# 7. tuning                                                                    #
# --------------------------------------------------------------------------- #
class TestDSI:
    def test_single_direction_is_fully_selective(self):
        ang = np.linspace(0.0, 360.0, 8, endpoint=False)
        r = np.zeros(8)
        r[2] = 1.0
        out = fv.fly_dsi(r, ang)
        assert abs(out["dsi"] - 1.0) < 1e-6      # the 1e-9 denominator eps floors it
        assert abs(out["pref_deg"] - ang[2]) < 1e-6

    def test_isotropic_response_is_not_selective(self):
        ang = np.linspace(0.0, 360.0, 8, endpoint=False)
        out = fv.fly_dsi(np.ones(8), ang)
        assert out["dsi"] < 1e-9


# --------------------------------------------------------------------------- #
# 8. fail-closed                                                               #
# --------------------------------------------------------------------------- #
class TestFailClosed:
    def test_string_and_complex_scalars_are_refused(self):
        with pytest.raises(ValueError):
            fv.fly_hex_lattice(dphi_deg="4.63")
        with pytest.raises(ValueError):
            fv.fly_hex_lattice(az0_deg=1 + 2j)

    def test_unknown_geometry_and_mode_are_refused(self):
        with pytest.raises(ValueError, match="geometry"):
            fv.fly_hex_lattice(geometry="square")
        lat = fv.fly_hex_lattice(radius=3)
        with pytest.raises(ValueError, match="mode"):
            fv.fly_hex_resample(np.zeros((16, 16)), lat, mode="omni")

    def test_a_non_lattice_table_is_not_mistaken_for_an_eye(self):
        # a csi_design-style dict has different keys; it must not be read as a lattice
        with pytest.raises(ValueError, match="missing key"):
            fv.fly_hex_resample(np.zeros((16, 16)), {"foo": 1, "bar": 2})

    def test_nan_input_is_refused(self):
        x = np.linspace(0.0, 1.0, 32)
        x[5] = np.nan
        with pytest.raises(ValueError, match="non-finite"):
            fv.fly_emd_response(x, x)

    def test_mismatched_lengths_are_refused(self):
        with pytest.raises(ValueError, match="same length"):
            fv.fly_emd_response(np.zeros(16), np.zeros(20))
        with pytest.raises(ValueError, match="correspond"):
            fv.fly_dsi(np.ones(8), np.linspace(0, 360, 6, endpoint=False))

    def test_all_zero_responses_refuse_a_fabricated_dsi(self):
        with pytest.raises(ValueError, match="did not respond"):
            fv.fly_dsi(np.zeros(8), np.linspace(0, 360, 8, endpoint=False))

    def test_n_pref_out_of_range_is_refused(self):
        lat = fv.fly_hex_lattice(radius=3)
        n = lat["dirs"].shape[0]
        with pytest.raises(ValueError, match="n_pref"):
            fv.fly_hs_readout(np.ones((4, n)), lat, n_pref=4)   # == k, not < k


# --------------------------------------------------------------------------- #
# 9. honest disclosure — the holes that exist now                             #
# --------------------------------------------------------------------------- #
class TestKnownLimits:
    def test_resample_mtf_degrades_off_axis(self):
        # ★ The MTF identity is a small-footprint approximation and is NOT claimed
        # ★ far from the optical axis: at ~35 deg elevation the measured transfer
        # ★ already departs from exp(-...) by more than the on-axis tolerance. This
        # ★ assert pins that hole so a future "curvature-corrected" resample has a
        # ★ failing test to turn green rather than a silent regression to argue about.
        lmbda = 25.0
        lat = fv.fly_hex_lattice(radius=12, dphi_deg=4.0)
        az, el = lat["az_rad"], lat["el_rad"]
        h = w = 181
        fov = 130.0
        f = (h / 2.0) / np.tan(np.deg2rad(fov) / 2.0)
        _yy, xx = np.mgrid[0:h, 0:w].astype(float)
        xc = (xx + 0.5 - w / 2.0) / f
        img = 0.5 + 0.5 * np.cos(2.0 * np.pi * np.degrees(np.arctan2(xc, 1.0)) / lmbda)
        sig = fv.fly_hex_resample(img, lat, drho_deg=DRHO, fov_deg=fov)
        phi = 2.0 * np.pi * np.degrees(az) / lmbda
        offax = (np.abs(np.degrees(el)) > 33.0) & (np.abs(np.cos(phi)) > 0.5)
        meas = np.median((sig[offax] - 0.5) / (0.5 * np.cos(phi[offax])))
        assert abs(meas - _mtf(lmbda)) > 0.02      # the hole: off-axis it is worse


# --------------------------------------------------------------------------- #
# 10. ledger consistency                                                       #
# --------------------------------------------------------------------------- #
class TestLedger:
    def test_every_op_has_an_implementation(self):
        assert opsflyvision.missing() == []
        assert len(opsflyvision.OPSFLYVISION) == len(fv.FLYVISION) == 16

    def test_declared_out_types_are_what_the_ops_return(self):
        lat = fv.fly_hex_lattice(radius=3)
        assert isinstance(opsflyvision.get("fly_hex_lattice")(radius=3), dict)
        assert isinstance(opsflyvision.get("fly_dsi")(
            np.ones(6), np.linspace(0, 360, 6, endpoint=False)), dict)
        assert isinstance(opsflyvision.get("fly_hs_readout")(
            np.ones((4, lat["dirs"].shape[0])), lat, 2, el_min_deg=0.0), float)
        sig = opsflyvision.get("fly_hex_resample")(
            np.random.default_rng(0).random((64, 64)),
            fv.fly_hex_lattice(radius=4), fov_deg=120.0)
        assert isinstance(sig, np.ndarray) and sig.ndim == 1

    def test_no_op_name_collides_with_a_two_d_registry_op(self):
        import ops
        reg = {o.name for o in ops.REGISTRY}
        assert not (set(fv.FLYVISION) & reg)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])


# --------------------------------------------------------------------------- #
# fly_hex_quantize —— 複眼は量子化器(2026-09-20)                                 #
# --------------------------------------------------------------------------- #
def test_hex_quantize_levels_modes_and_refusals():
    import flyvision as fv

    x = np.array([0.0, 0.1, 0.5, 1.0, 2.0, 4.0])
    for bits in (1, 3, 8):
        q = fv.fly_hex_quantize(x, bits=bits, mode="log")
        levels = 2 ** bits - 1
        assert q.shape == x.shape and q.min() >= 0.0 and q.max() <= 1.0
        assert np.allclose(q * levels, np.round(q * levels))               # 格子に乗っている
        assert np.all(np.diff(q) >= 0)                                      # 単調
    lin = fv.fly_hex_quantize(x, bits=2, mode="linear")
    assert lin[-1] == 1.0 and lin[0] == 0.0 and len(np.unique(lin)) <= 4
    oo = fv.fly_hex_quantize(x, mode="onoff", contrast=0.5)
    n = len(x)
    assert oo.shape == (2 * n,) and oo.min() >= 0.0 and oo.max() <= 1.0
    assert (oo[:n] * oo[n:] == 0).all()                                     # ON と OFF は排他
    assert oo[n + 0] > 0 and oo[n - 1] > 0                                  # 暗い個眼は OFF、明るい個眼は ON
    assert np.all(fv.fly_hex_quantize(np.full(5, 0.7), mode="log") == 0.0)   # 定数 = コントラスト無し
    assert np.all(fv.fly_hex_quantize(np.full(5, 0.7), mode="onoff") == 0.0)
    for bad in (dict(bits=0), dict(bits=9), dict(mode="pcm"), dict(contrast=0.0)):
        with pytest.raises(ValueError, match="fly_hex_quantize"):
            fv.fly_hex_quantize(x, **bad)
    with pytest.raises(ValueError, match="fly_hex_quantize"):
        fv.fly_hex_quantize(np.array([1.0, -0.1]))
    with pytest.raises(ValueError, match="fly_hex_quantize"):
        fv.fly_hex_quantize(np.ones((3, 3)))


def test_hex_quantize_is_registered_and_runs_through_op_run():
    import fullseye as fs
    import opsflyvision

    assert "fly_hex_quantize" in opsflyvision.OPSFLYVISION
    out, _ = fs.op_run("fly_hex_quantize", np.linspace(0.0, 1.0, 16), bits=2)
    assert np.asarray(out).shape == (16,)


# --------------------------------------------------------------------------- #
# 8. lamina — adaptation and the band-pass (2026-09-22)                         #
# --------------------------------------------------------------------------- #
def _flicker(n_t=400, n=7, dt=0.005, f=2.0, mean=1.0, contrast=0.2):
    t = np.arange(n_t) * dt
    return mean * (1.0 + contrast * np.sin(2.0 * np.pi * f * t))[:, None] * np.ones((1, n))


def _discrete_lp_gain(tau, dt, f):
    """The exact steady-state gain of the exponential smoother at frequency f."""
    a = 1.0 - np.exp(-dt / tau)
    z = np.exp(-1j * 2.0 * np.pi * f * dt)
    return a / (1.0 - (1.0 - a) * z)


class TestLamina:
    def test_weber_invariance_is_exact(self):
        """Scaling the light by any factor returns the same contrast — that is the stage."""
        x = _flicker()
        y = fv.fly_lamina_filter(x, 0.005)
        for k in (0.1, 10.0, 1e4):
            assert np.abs(fv.fly_lamina_filter(k * x, 0.005) - y).max() < 1e-12

    def test_the_band_pass_matches_the_product_of_the_two_filters(self):
        dt, ta, tl = 0.005, 0.2, 0.02
        for f in (0.2, 1.0, 3.0, 8.0):
            x = _flicker(n_t=4000, n=1, dt=dt, f=f, contrast=0.1)
            y = fv.fly_lamina_filter(x, dt, tau_adapt_s=ta, tau_lp_s=tl, mode="subtractive")
            want = abs(1.0 - _discrete_lp_gain(ta, dt, f)) * abs(_discrete_lp_gain(tl, dt, f))
            got = float(np.abs(np.fft.rfft(y[2000:, 0] * np.hanning(2000))).max()
                        / np.abs(np.fft.rfft((x[2000:, 0] - x[2000:, 0].mean()) * np.hanning(2000))).max())
            assert got == pytest.approx(want, rel=0.02), (f, got, want)

    def test_a_step_returns_to_zero_with_the_adaptation_time_constant(self):
        dt, ta = 0.001, 0.05
        x = np.ones((600, 1))
        x[:100] = 0.5
        y = fv.fly_lamina_filter(x, dt, tau_adapt_s=ta, tau_lp_s=1e-6, mode="subtractive")
        peak = int(np.argmax(y[:, 0]))
        after = y[peak + int(ta / dt), 0]
        assert after == pytest.approx(y[peak, 0] * np.exp(-1.0), rel=0.05)
        # DC は落ちる。残りは厳密に 0.5·exp(−t/τ)(ステップから 499 ms)
        assert y[-1, 0] == pytest.approx(0.5 * np.exp(-0.499 / ta), rel=0.02)
        assert abs(y[-1, 0]) < 1e-4

    def test_refusals(self):
        x = _flicker(n_t=10, n=3)
        with pytest.raises(ValueError, match="fly_lamina_filter.*negative"):
            fv.fly_lamina_filter(-x, 0.005)
        with pytest.raises(ValueError, match="fly_lamina_filter.*all zero"):
            fv.fly_lamina_filter(np.zeros((10, 3)), 0.005)
        with pytest.raises(ValueError, match="fly_lamina_filter.*at least 2"):
            fv.fly_lamina_filter(np.ones((1, 3)), 0.005)
        with pytest.raises(ValueError, match="fly_lamina_filter.*movie"):
            fv.fly_lamina_filter(np.ones(10), 0.005)
        with pytest.raises(ValueError, match="fly_lamina_filter.*mode"):
            fv.fly_lamina_filter(x, 0.005, mode="log")
        with pytest.raises(ValueError, match="floor must be"):
            fv.fly_lamina_filter(x, 0.005, floor=0.0)      # 0 は暗い個眼で 0/0 = NaN
        with pytest.raises(ValueError, match="dt_s must be"):
            fv.fly_lamina_filter(x, 0.0)
        # 符号つきの入力は subtractive なら通る(対比はすでに引かれている)
        assert fv.fly_lamina_filter(x - 1.0, 0.005, mode="subtractive").shape == x.shape


class TestOnOff:
    def test_the_two_channels_add_and_subtract_to_the_filtered_input(self):
        c = _flicker(n_t=300, n=5, contrast=0.4) - 1.0
        oo = fv.fly_onoff_split(c, 0.005, tau_on_s=0.03, tau_off_s=0.03)
        n = c.shape[1]
        assert oo.shape == (c.shape[0], 2 * n)
        on, off = oo[:, :n], oo[:, n:]
        lp = fv.fly_lamina_filter                       # 同じ 1 次低域を通した基準を作る
        del lp
        want_diff = fv._lowpass_columns(c, 0.03, 0.005)
        want_sum = fv._lowpass_columns(np.abs(c), 0.03, 0.005)
        assert np.abs((on - off) - want_diff).max() < 1e-12
        assert np.abs((on + off) - want_sum).max() < 1e-12
        assert on.min() >= 0.0 and off.min() >= 0.0

    def test_a_brightening_only_movie_leaves_the_off_channel_empty(self):
        c = np.abs(_flicker(n_t=200, n=4) - 1.0)
        n = c.shape[1]
        oo = fv.fly_onoff_split(c, 0.005)
        assert np.all(oo[:, n:] == 0.0)
        assert oo[:, :n].max() > 0.0
        oo2 = fv.fly_onoff_split(-c, 0.005)
        assert np.all(oo2[:, :n] == 0.0)

    def test_the_linear_mode_does_not_rectify(self):
        c = _flicker(n_t=200, n=2) - 1.0
        n = c.shape[1]
        oo = fv.fly_onoff_split(c, 0.005, rectify=False)
        assert oo[:, n:].min() < 0.0                    # OFF は素の反転(整流していない)
        assert np.abs(oo[:, :n] + oo[:, n:]).max() < 1e-12

    def test_refusals(self):
        with pytest.raises(ValueError, match="fly_onoff_split.*movie"):
            fv.fly_onoff_split(np.ones(8), 0.005)
        with pytest.raises(ValueError, match="tau_on_s must be"):
            fv.fly_onoff_split(np.ones((8, 2)), 0.005, tau_on_s=0.0)


# --------------------------------------------------------------------------- #
# 9. direction — T4/T5 over the lattice                                         #
# --------------------------------------------------------------------------- #
def _two_column_pulse(lat, k, order, dt=0.001, tau=0.25):
    """Haag らの見かけ運動: 1 本目を tau 秒、2 本目(中央)を最終サンプルだけ。"""
    uv = np.asarray(lat["uv"])
    lut = {(int(u), int(v)): i for i, (u, v) in enumerate(uv)}
    step = fv.HEX_STEPS[k]
    first = lut[(-step[0], -step[1])] if order == "pd" else lut[step]
    x = np.zeros((int(round(tau / dt)) + 1, len(uv)))
    x[1:, first] = 1.0
    x[-1, lut[(0, 0)]] = 1.0
    return x, lut[(0, 0)]


def _drift(lat, k, dt=0.01, n_t=400, speed=1.0, lam_col=4.0, contrast=0.5):
    """六角の k 方向へ流れる正弦(位相は接平面での k 方向の座標)。"""
    step = fv.HEX_STEPS[k]
    daz = step[1] + 0.5 * step[0]
    dele = (np.sqrt(3.0) / 2.0) * step[0]
    nrm = np.hypot(daz, dele)
    coord = (np.asarray(lat["az_rad"]) * daz + np.asarray(lat["el_rad"]) * dele) / (nrm * lat["dphi_rad"])
    t = np.arange(n_t) * dt
    return 1.0 + contrast * np.sin(2.0 * np.pi * (coord[None, :] - speed * t[:, None]) / lam_col)


class TestT4T5:
    def test_the_paper_numbers_come_out_of_the_two_column_stimulus(self):
        """Haag ら 2016 の逐語の定数(τ=250 ms, k=5/5/10, DC=1)での見かけ運動。"""
        lat = fv.fly_hex_lattice(radius=4)
        lp = 1.0 - np.exp(-1.0)
        want = {"pd": (1 + 5 * lp) * 6.0, "nd": 6.0 / (1 + 10 * lp)}
        for order in ("pd", "nd"):
            x, c = _two_column_pulse(lat, 0, order)
            R = fv.fly_t4t5_field(x, lat, 0.001, reduce="last")
            assert R[0, c] + 1.0 == pytest.approx(want[order], rel=1e-9)
        assert want["pd"] == pytest.approx(24.9636, abs=1e-3)
        assert want["nd"] == pytest.approx(0.8195, abs=1e-3)

    def test_the_whole_model_is_the_product_of_its_two_halves(self):
        """論文の主張「2 つの仕組みは相補的」= 比の積の恒等式。任意の刺激で成り立つ。"""
        lat = fv.fly_hex_lattice(radius=3)
        rng = np.random.default_rng(0)
        for seed in range(4):
            x = rng.random((150, lat["dirs"].shape[0]))
            r = {m: fv.fly_t4t5_field(x, lat, 0.005, model=m, reduce="last") + 1.0
                 for m in ("three_arm", "enhance", "suppress")}
            c = int(np.where((np.asarray(lat["uv"])[:, 0] == 0)
                             & (np.asarray(lat["uv"])[:, 1] == 0))[0][0])
            lhs = r["three_arm"][0, c] / r["three_arm"][3, c]
            rhs = ((r["enhance"][0, c] / r["enhance"][3, c])
                   * (r["suppress"][0, c] / r["suppress"][3, c]))
            assert lhs == pytest.approx(rhs, rel=1e-9), seed
        # 論文の 2 柱刺激では 4.16 x 7.32 = 30.46
        lp = 1.0 - np.exp(-1.0)
        assert ((1 + 5 * lp) * 6.0 / 6.0) * (6.0 / (6.0 / (1 + 10 * lp))) == pytest.approx(
            (1 + 5 * lp) * 6.0 / (6.0 / (1 + 10 * lp)), rel=1e-12)

    def test_each_detector_prefers_its_own_direction(self):
        lat = fv.fly_hex_lattice(radius=4)
        c = int(np.where((np.asarray(lat["uv"])[:, 0] == 0)
                         & (np.asarray(lat["uv"])[:, 1] == 0))[0][0])
        M = np.array([fv.fly_t4t5_field(_drift(lat, k), lat, 0.01)[:, c] for k in range(6)])
        assert M.argmax(axis=1).tolist() == list(range(6))
        for k in range(6):
            assert M[k, k] > M[k, (k + 3) % 6]           # 反対方向より必ず大きい

    def test_the_rim_reads_exactly_zero(self):
        """腕の片方が無い個眼は 0。作ると眼のまわりに偽の流れの輪ができる。"""
        lat = fv.fly_hex_lattice(radius=2)
        uv = np.asarray(lat["uv"])
        R = fv.fly_t4t5_field(_drift(lat, 0, n_t=100), lat, 0.01)
        lut = {(int(u), int(v)) for u, v in uv}
        for k, step in enumerate(fv.HEX_STEPS):
            for i, (u, v) in enumerate(uv):
                has = ((int(u) - step[0], int(v) - step[1]) in lut
                       and (int(u) + step[0], int(v) + step[1]) in lut)
                if not has:
                    assert R[k, i] == 0.0

    def test_all_four_models_and_the_reductions_run(self):
        lat = fv.fly_hex_lattice(radius=2)
        x = _drift(lat, 1, n_t=80)
        for m in fv.T4_MODELS:
            for red in fv.T4_REDUCTIONS:
                out = fv.fly_t4t5_field(x, lat, 0.01, model=m, reduce=red)
                assert out.shape == (6, lat["dirs"].shape[0]) and np.isfinite(out).all()

    def test_a_signed_movie_is_refused_by_the_divisive_models(self):
        """割り算を持つ腕に符号つきの対比を渡すと分母が 0 を跨ぐ —— 入口で断る。"""
        lat = fv.fly_hex_lattice(radius=2)
        n = lat["dirs"].shape[0]
        x = np.random.default_rng(0).random((20, n)) - 0.5
        for m in ("three_arm", "enhance", "suppress"):
            with pytest.raises(ValueError, match="fly_t4t5_field.*one polarity"):
                fv.fly_t4t5_field(x, lat, 0.01, model=m)
        assert fv.fly_t4t5_field(x, lat, 0.01, model="hr").shape == (6, n)

    def test_refusals(self):
        lat = fv.fly_hex_lattice(radius=2)
        n = lat["dirs"].shape[0]
        with pytest.raises(ValueError, match="fly_t4t5_field.*column"):
            fv.fly_t4t5_field(np.ones((10, 2 * n)), lat, 0.01)
        with pytest.raises(ValueError, match="fly_t4t5_field.*model"):
            fv.fly_t4t5_field(np.ones((10, n)), lat, 0.01, model="energy")
        with pytest.raises(ValueError, match="fly_t4t5_field.*reduce"):
            fv.fly_t4t5_field(np.ones((10, n)), lat, 0.01, reduce="median")
        with pytest.raises(ValueError, match="fly_t4t5_field.*lattice"):
            fv.fly_t4t5_field(np.ones((10, n)), {"dsi": 1.0, "pref_deg": 0.0}, 0.01)


class TestFlowFromDirections:
    def test_a_cosine_tuned_field_returns_its_own_amplitude_and_angle(self):
        lat = fv.fly_hex_lattice(radius=4)
        n = lat["dirs"].shape[0]
        th = np.arange(6) * np.pi / 3.0
        for amp, ang in ((2.5, 0.7), (0.3, -2.0), (1.0, 0.0)):
            R = (amp * np.cos(th - ang))[:, None] * np.ones((1, n))
            f = fv.fly_flow_from_directions(R, lat)
            i = int(np.where((np.asarray(lat["uv"])[:, 0] == 0)
                             & (np.asarray(lat["uv"])[:, 1] == 0))[0][0])
            assert np.hypot(*f[i]) == pytest.approx(amp, rel=1e-9)
            assert np.arctan2(f[i, 1], f[i, 0]) == pytest.approx(ang, abs=1e-9)

    def test_opposite_directions_cancel_exactly(self):
        lat = fv.fly_hex_lattice(radius=3)
        n = lat["dirs"].shape[0]
        R = np.full((6, n), 3.7)                      # どの方向にも同じ = 動きではなく明滅
        assert np.abs(fv.fly_flow_from_directions(R, lat)).max() < 1e-12
        # 縁(6 方向が揃わない個眼)は 0 —— 部分和は打ち消さず、偽の流れの輪になる
        uv = np.asarray(lat["uv"])
        lut = {(int(u), int(v)) for u, v in uv}
        rim = [i for i, (u, v) in enumerate(uv)
               if not all((int(u) + s0, int(v) + s1) in lut for s0, s1 in fv.HEX_STEPS)]
        assert rim and np.all(fv.fly_flow_from_directions(np.ones((6, n)), lat)[rim] == 0.0)

    def test_refusals(self):
        lat = fv.fly_hex_lattice(radius=2)
        n = lat["dirs"].shape[0]
        with pytest.raises(ValueError, match="fly_flow_from_directions.*6, n"):
            fv.fly_flow_from_directions(np.ones((5, n)), lat)
        with pytest.raises(ValueError, match="fly_flow_from_directions.*column"):
            fv.fly_flow_from_directions(np.ones((6, n + 1)), lat)


# --------------------------------------------------------------------------- #
# 10. selfmotion — matched filters, the linear fit, and wide eyes                #
# --------------------------------------------------------------------------- #
class TestMatchedFilter:
    def test_rotation_template_is_the_sine_of_the_angle_to_the_axis(self):
        lat = fv.fly_hex_lattice(radius=6, az0_deg=30.0, el0_deg=15.0)
        d = lat["dirs"]
        for ax in ((0, 0, 1), (0, 1, 0), (1, 0, 0), (0.3, -0.5, 0.8)):
            a = np.asarray(ax, float)
            a = a / np.linalg.norm(a)
            f = fv.fly_matched_filter(lat, axis=ax)
            want = np.linalg.norm(np.cross(np.broadcast_to(a, d.shape), d), axis=1)
            assert np.abs(np.hypot(f[:, 0], f[:, 1]) - want).max() < 1e-12

    def test_the_template_vanishes_where_you_look_along_the_axis(self):
        lat = fv.fly_hex_lattice(radius=3)
        axis = lat["dirs"][int(np.where((np.asarray(lat["uv"])[:, 0] == 0)
                                        & (np.asarray(lat["uv"])[:, 1] == 0))[0][0])]
        f = fv.fly_matched_filter(lat, axis=axis)
        i = int(np.argmin(np.linalg.norm(lat["dirs"] - axis, axis=1)))
        assert np.hypot(*f[i]) < 1e-12

    def test_translation_scales_with_one_over_depth(self):
        lat = fv.fly_hex_lattice(radius=3, az0_deg=60.0)
        a = fv.fly_matched_filter(lat, axis=(1, 0, 0), motion="translation", depth_m=1.0)
        b = fv.fly_matched_filter(lat, axis=(1, 0, 0), motion="translation", depth_m=4.0)
        assert np.abs(a - 4.0 * b).max() < 1e-12

    def test_refusals(self):
        lat = fv.fly_hex_lattice(radius=2)
        with pytest.raises(ValueError, match="fly_matched_filter.*zero vector"):
            fv.fly_matched_filter(lat, axis=(0, 0, 0))
        with pytest.raises(ValueError, match="fly_matched_filter.*motion"):
            fv.fly_matched_filter(lat, motion="spin")
        with pytest.raises(ValueError, match="fly_matched_filter.*3 numbers"):
            fv.fly_matched_filter(lat, axis=(1, 0))


class TestEgomotion:
    def test_a_scaled_template_comes_back_exactly(self):
        lat = fv.fly_hex_lattice(radius=5, az0_deg=45.0, el0_deg=10.0)
        for ax, rate in (((0, 0, 1), 3.0), ((0, 1, 0), -1.25), ((1, 0, 0), 0.4)):
            e = fv.fly_egomotion_from_flow(fv.fly_matched_filter(lat, axis=ax) * rate, lat)
            assert np.allclose(e["omega_rad_s"], np.asarray(ax, float) * rate, atol=1e-9)
            assert e["explained"] == pytest.approx(1.0, abs=1e-9)
        assert e["n_ommatidia"] == lat["dirs"].shape[0]

    def test_asking_only_for_yaw_is_the_well_conditioned_question(self):
        lat = fv.fly_hex_lattice(radius=5)
        full = fv.fly_egomotion_from_flow(fv.fly_matched_filter(lat, axis=(0, 0, 1)) * 2.0, lat)
        yaw = fv.fly_egomotion_from_flow(fv.fly_matched_filter(lat, axis=(0, 0, 1)) * 2.0,
                                         lat, axes=[[0, 0, 1]])
        assert yaw["yaw_rad_s"] == pytest.approx(2.0, rel=1e-9)
        assert yaw["condition"] == pytest.approx(1.0, abs=1e-9)
        assert full["condition"] > yaw["condition"]

    def test_a_translation_field_is_not_explained_as_a_rotation(self):
        lat = fv.fly_hex_lattice(radius=6, dphi_deg=8.0)
        t = fv.fly_matched_filter(lat, axis=(1, 0, 0), motion="translation", depth_m=1.0)
        e = fv.fly_egomotion_from_flow(t, lat)
        assert e["explained"] < 0.9                      # 回転では説明しきれない
        assert e["flow_rms"] > 0.0

    def test_weights_can_silence_part_of_the_eye(self):
        lat = fv.fly_hex_lattice(radius=4)
        f = fv.fly_matched_filter(lat, axis=(0, 0, 1)) * 1.5
        bad = f.copy()
        w = np.ones(f.shape[0])
        bad[:10] = 99.0
        w[:10] = 0.0
        e = fv.fly_egomotion_from_flow(bad, lat, weights=w)
        assert e["yaw_rad_s"] == pytest.approx(1.5, rel=1e-9)

    def test_refusals(self):
        lat = fv.fly_hex_lattice(radius=2)
        n = lat["dirs"].shape[0]
        with pytest.raises(ValueError, match="fly_egomotion_from_flow.*n, 2"):
            fv.fly_egomotion_from_flow(np.ones((n, 3)), lat)
        with pytest.raises(ValueError, match="fly_egomotion_from_flow.*weights"):
            fv.fly_egomotion_from_flow(np.ones((n, 2)), lat, weights=np.ones(n + 1))
        with pytest.raises(ValueError, match="fly_egomotion_from_flow.*negative"):
            fv.fly_egomotion_from_flow(np.ones((n, 2)), lat, weights=-np.ones(n))
        with pytest.raises(ValueError, match="fly_egomotion_from_flow.*zero"):
            fv.fly_egomotion_from_flow(np.ones((n, 2)), lat, weights=np.zeros(n))
        with pytest.raises(ValueError, match="fly_egomotion_from_flow.*axes"):
            fv.fly_egomotion_from_flow(np.ones((n, 2)), lat, axes=np.ones((2, 2)))


class TestEyeMerge:
    def test_merging_keeps_every_ommatidium_and_marks_which_eye(self):
        eyes = [fv.fly_hex_lattice(radius=3, az0_deg=a) for a in (-60.0, 0.0, 60.0)]
        m = fv.fly_eye_merge(*eyes)
        n = eyes[0]["dirs"].shape[0]
        assert m["dirs"].shape == (3 * n, 3)
        assert np.bincount(m["eye"]).tolist() == [n, n, n]
        assert np.allclose(m["dirs"][:n], eyes[0]["dirs"])
        # 束ねた眼はそのまま整合フィルタと当てはめに渡せる
        e = fv.fly_egomotion_from_flow(fv.fly_matched_filter(m, axis=(0, 0, 1)) * 0.75, m)
        assert e["yaw_rad_s"] == pytest.approx(0.75, rel=1e-9)

    def test_a_wider_eye_is_better_conditioned_than_one_patch(self):
        one = fv.fly_hex_lattice(radius=4, dphi_deg=5.0)
        wide = fv.fly_eye_merge(fv.fly_hex_lattice(radius=4, dphi_deg=5.0, az0_deg=-70.0),
                                one,
                                fv.fly_hex_lattice(radius=4, dphi_deg=5.0, az0_deg=70.0))
        c1 = fv.fly_egomotion_from_flow(fv.fly_matched_filter(one, axis=(0, 0, 1)), one)["condition"]
        c3 = fv.fly_egomotion_from_flow(fv.fly_matched_filter(wide, axis=(0, 0, 1)), wide)["condition"]
        assert c3 < c1

    def test_a_merged_eye_is_refused_where_neighbours_are_needed(self):
        """束ねた眼の (u, v) は重複する —— 近傍を引くと**別の眼**の個眼が当たる。"""
        eyes = [fv.fly_hex_lattice(radius=3, az0_deg=a) for a in (0.0, 40.0)]
        m = fv.fly_eye_merge(*eyes)
        n = m["dirs"].shape[0]
        with pytest.raises(ValueError, match="fly_t4t5_field.*fly_eye_merge"):
            fv.fly_t4t5_field(np.ones((10, n)), m, 0.01)
        with pytest.raises(ValueError, match="fly_flow_from_directions.*fly_eye_merge"):
            fv.fly_flow_from_directions(np.ones((6, n)), m)
        # 束ねた眼を食ってよい 2 op はそのまま通る(視線方向しか要らない)
        assert fv.fly_matched_filter(m, axis=(0, 0, 1)).shape == (n, 2)
        assert fv.fly_egomotion_from_flow(
            fv.fly_matched_filter(m, axis=(0, 0, 1)) * 0.5, m,
            axes=[[0, 0, 1]])["yaw_rad_s"] == pytest.approx(0.5, rel=1e-9)

    def test_refusals(self):
        a = fv.fly_hex_lattice(radius=2)
        with pytest.raises(ValueError, match="fly_eye_merge.*same direction"):
            fv.fly_eye_merge(a, a)
        with pytest.raises(ValueError, match="fly_eye_merge.*sampling scales"):
            fv.fly_eye_merge(a, fv.fly_hex_lattice(radius=2, dphi_deg=9.0, az0_deg=40.0))
        with pytest.raises(ValueError, match="fly_eye_merge.*same eye"):
            fv.fly_eye_merge(a, fv.fly_hex_lattice(radius=2, az0_deg=40.0, geometry="boxeye"))
        with pytest.raises(ValueError, match="fly_eye_merge.*lattice"):
            fv.fly_eye_merge([a, a], a)


def test_the_pathway_runs_end_to_end_through_the_public_tier():
    """ラミナ → ON/OFF → T4/T5 → フロー → 回転 を facade から。向きが合うこと。"""
    import fullseye as fs

    L = fs.ledger
    lat = L.fly_hex_lattice(radius=5, dphi_deg=5.0)
    n = lat["dirs"].shape[0]
    dt = 0.01
    az = np.asarray(lat["az_rad"])
    t = np.arange(200) * dt
    got = []
    for speed in (-0.4, 0.4):
        movie = 1.0 + 0.3 * np.sin(2 * np.pi / np.deg2rad(30.0) * (az[None, :] - speed * t[:, None]))
        oo = L.fly_onoff_split(L.fly_lamina_filter(movie, dt, tau_adapt_s=0.1), dt)
        field = (L.fly_t4t5_field(oo[:, :n], lat, dt, tau_s=0.05)
                 + L.fly_t4t5_field(oo[:, n:], lat, dt, tau_s=0.05))
        est = L.fly_egomotion_from_flow(L.fly_flow_from_directions(field, lat), lat,
                                        axes=[[0.0, 0.0, 1.0]])
        got.append(est["yaw_rad_s"])
    # 模様が +方位へ動く = 眼が −方位へ回った、と読む。符号が分かれ、大きさは揃う
    assert got[0] > 0.0 > got[1]
    assert abs(got[0] + got[1]) < 0.2 * max(abs(got[0]), abs(got[1]))
