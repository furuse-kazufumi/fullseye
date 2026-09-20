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
        assert len(opsflyvision.OPSFLYVISION) == len(fv.FLYVISION) == 9

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
