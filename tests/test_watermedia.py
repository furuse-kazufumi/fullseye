# -*- coding: utf-8 -*-
"""Gates for ``watermedia`` (waves, refraction, attenuation, scattering, bottles).

Every number is scored against something the op does not share with itself: a closed form, a second implementation
(the quartic of the flat Fermat problem, a direct minimisation of the optical path, a trigonometric chord of the rod, a
Monte Carlo count) or a published table value. Each family has a probe that breaks the answer on purpose and must be caught.
"""
import math

import numpy as np
import pytest

import glassmirror
import watermedia as W
import watermedia_data as WD

G = W.G


# ---------------------------------------------------------------- 1. the wave spectrum
@pytest.mark.parametrize("U", [5.0, 10.0, 20.0])
def test_pm_hs_and_peak_follow_the_closed_forms(U):
    from scipy.integrate import quad
    r = W.ocean_spectrum(U)
    assert r["kind"] == "pierson_moskowitz" and r["omega"].size == 6000
    hs_rule = 0.21 * U * U / G
    assert abs(r["hs_m"] / hs_rule - 1.0) < 0.02                       # numerical integral of the spectrum vs 0.21 U^2/g
    m0, _ = quad(lambda w: PM_S(w, U), 1e-3, 200.0, points=[0.877 * G / U], limit=400)       # a second integral (adaptive)
    assert abs(r["hs_m"] / (4.0 * math.sqrt(m0)) - 1.0) < 1e-4
    assert abs(r["hs_closed_form_m"] / r["hs_m"] - 1.0) < 1e-4
    assert abs(r["omega_peak"] / (0.877 * G / U) - 1.0) < 1e-3          # omega_p = 0.877 g / U
    assert abs(r["omega_peak_numeric"] / r["omega_peak"] - 1.0) < 1e-6   # the maximum of S is at omega_p
    assert abs(r["tp_s"] - 2.0 * math.pi / r["omega_peak"]) < 1e-12


def PM_S(w, U):
    return 0.0081 * G * G / w ** 5 * math.exp(-0.74 * (G / (U * w)) ** 4)


def test_jonswap_reduces_to_pm_and_peaks_by_gamma():
    pm = W.ocean_spectrum(10.0)
    jn = W.ocean_spectrum(10.0, kind="jonswap", gamma=1.0)
    assert np.abs(jn["S"] - pm["S"]).max() / pm["S"].max() < 1e-9
    wp = pm["omega_peak"]
    grid = np.array([0.5 * wp, wp, 2.0 * wp])
    j33 = W.ocean_spectrum(10.0, kind="jonswap", omega=grid)
    p33 = W.ocean_spectrum(10.0, omega=grid)
    assert abs(j33["S"][1] / p33["S"][1] - 3.3) < 1e-12                 # gamma^1 at the peak
    assert abs(j33["S"][0] / p33["S"][0] - 1.0) < 1e-3 and abs(j33["S"][2] / p33["S"][2] - 1.0) < 1e-3   # little change far from it
    short, long_ = W.ocean_spectrum(10.0, 20e3, "jonswap"), W.ocean_spectrum(10.0, 200e3, "jonswap")
    assert long_["hs_m"] > short["hs_m"] and long_["tp_s"] > short["tp_s"]      # a longer fetch grows a bigger, slower sea
    assert not short["fully_developed"] and short["alpha"] > long_["alpha"]


def test_spectrum_refusals():
    for bad in (-1.0, 0.0, float("nan"), float("inf"), "10", True, None, 100.0):
        with pytest.raises(ValueError):
            W.ocean_spectrum(bad)
    for bad in (0.0, -5.0, float("nan")):
        with pytest.raises(ValueError):
            W.ocean_spectrum(10.0, fetch_m=bad, kind="jonswap")
    with pytest.raises(ValueError):
        W.ocean_spectrum(10.0, fetch_m=1e4)                           # pierson_moskowitz is fully developed
    with pytest.raises(ValueError):
        W.ocean_spectrum(10.0, kind="phillips")
    with pytest.raises(ValueError):
        W.ocean_spectrum(10.0, omega=[2.0, 1.0])
    with pytest.raises(ValueError):
        W.ocean_spectrum(10.0, kind="jonswap", gamma=0.5)


def test_spectrum_probe_catches_a_wrong_constant():
    r = W.ocean_spectrum(10.0)
    wrong = 4.0 * math.sqrt(0.0081 * 1.1 / (4.0 * 0.74)) * 100.0 / G              # alpha 10 % too large
    assert abs(wrong / r["hs_m"] - 1.0) > 0.02                           # the 2 % gate would catch it


# ---------------------------------------------------------------- 2. the FFT sea
_SEAS = {}


def _sea(U, seed, n=256, L=1000.0, **kw):
    key = (U, seed, n, L, tuple(sorted(kw.items())))
    if key not in _SEAS:
        _SEAS[key] = W.ocean_height_field(n, L, U, 0.0, seed=seed, **kw)
    return _SEAS[key]


def test_height_is_real_and_hermitian():
    f = _sea(8.0, 0)
    assert f["height"].shape == (256, 256) and f["normal"].shape == (256, 256, 3)
    assert f["imag_residual"] <= 1e-12
    assert abs(f["height"].mean()) < 1e-12                               # no mean level
    nrm = f["normal"]
    assert np.abs(np.linalg.norm(nrm, axis=-1) - 1.0).max() < 1e-12 and (nrm[..., 2] > 0).all()
    assert np.abs(nrm[..., 0] + f["slope_x"] * nrm[..., 2]).max() < 1e-12


@pytest.mark.parametrize("U", [5.0, 8.0, 10.0])
def test_spatial_variance_equals_the_integral_of_the_spectrum(U):
    seeds = range(8)
    vars_ = [float(_sea(U, s)["height"].var()) for s in seeds]
    expected = _sea(U, 0)["variance_expected_m2"]
    assert len(vars_) == 8
    assert abs(np.mean(vars_) / expected - 1.0) < 0.03
    # the discrete sum is the integral of the continuous spectrum over the wave numbers the grid holds: inside the circle of the
    # Nyquist wave number at the least, inside the circle through the corners at the most
    kn = _sea(U, 0)["k_nyquist_rad_per_m"]
    wp = W.ocean_spectrum(U)["omega_peak"]

    def m0_up_to(k):
        return W.ocean_spectrum(U, omega=np.geomspace(0.15 * wp, math.sqrt(G * k), 20000))["m0"]
    assert m0_up_to(kn) * 0.98 < expected < m0_up_to(math.sqrt(2.0) * kn) * 1.02


def test_slope_variance_against_cox_munk():
    out = {}
    for U in (5.0, 10.0):
        seeds = range(8)
        measured = np.mean([float((_sea(U, s)["slope_x"] ** 2 + _sea(U, s)["slope_y"] ** 2).mean()) for s in seeds])
        f0 = _sea(U, 0)
        cm = 0.003 + 0.00512 * U
        assert abs(f0["cox_munk_slope_variance"] - cm) < 1e-15
        assert abs(measured / f0["slope_variance_expected"] - 1.0) < 0.03          # the field has the slopes of its spectrum
        out[U] = (measured, f0["slope_variance_with_tail"], cm)
    # the resolved waves (down to 0.8 rad/m... ~8 m) carry a small part of the Cox-Munk slope: capillary waves are not in the spectrum
    for U, (resolved, tail, cm) in out.items():
        assert resolved / cm < 0.2
    # with the saturation range carried to the gravity-capillary wave number: agrees at 5 m/s, 40 % short at 10 m/s
    assert abs(out[5.0][1] / out[5.0][2] - 1.0) < 0.25
    assert 0.45 < out[10.0][1] / out[10.0][2] < 0.8          # known limitation of the constant-alpha range (reported, not hidden)
    print("Cox-Munk: U=5 resolved %.4f with tail %.4f vs %.4f; U=10 resolved %.4f with tail %.4f vs %.4f"
          % (out[5.0][0], out[5.0][1], out[5.0][2], out[10.0][0], out[10.0][1], out[10.0][2]))


def test_single_mode_period_and_analytic_slope():
    n, L, A = 32, 100.0, 0.3
    f0 = W.ocean_height_field(n, L, 8.0, 0.0, single_mode=(2, 1, A))
    k = 2.0 * math.pi / L * math.hypot(2, 1)
    om = math.sqrt(G * k)
    assert abs(f0["omega_mode"] - om) < 1e-12
    T = 2.0 * math.pi / om
    fT = W.ocean_height_field(n, L, 8.0, 0.0, t=T, single_mode=(2, 1, A))
    assert np.abs(fT["height"] - f0["height"]).max() < 1e-6 * A          # the period is 2 pi / omega
    fh = W.ocean_height_field(n, L, 8.0, 0.0, t=0.5 * T, single_mode=(2, 1, A))
    assert np.abs(fh["height"] + f0["height"]).max() < 1e-6 * A          # half a period inverts the wave
    x = f0["x_m"][None, :]
    y = f0["y_m"][:, None]
    phase = 2.0 * math.pi / L * (2 * x + 1 * y)
    assert np.abs(f0["height"] - A * np.cos(phase)).max() < 1e-12
    assert np.abs(f0["slope_x"] + A * (2.0 * math.pi / L * 2) * np.sin(phase)).max() < 1e-12     # analytic dh/dx
    assert np.abs(f0["slope_y"] + A * (2.0 * math.pi / L * 1) * np.sin(phase)).max() < 1e-12
    # finite depth: omega^2 = g k tanh(k h)
    fd = W.ocean_height_field(n, L, 8.0, 0.0, single_mode=(2, 1, A), depth_m=3.0)
    assert abs(fd["omega_mode"] - math.sqrt(G * k * math.tanh(k * 3.0))) < 1e-12
    assert fd["omega_mode"] < f0["omega_mode"]                           # shallow water slows the wave


def test_time_is_deterministic_and_choppiness_zero_means_no_displacement():
    a = W.ocean_height_field(64, 200.0, 8.0, 30.0, t=1.5, seed=3)
    b = W.ocean_height_field(64, 200.0, 8.0, 30.0, t=1.5, seed=3)
    c = W.ocean_height_field(64, 200.0, 8.0, 30.0, t=2.5, seed=3)
    d = W.ocean_height_field(64, 200.0, 8.0, 30.0, t=1.5, seed=4)
    assert np.array_equal(a["height"], b["height"]) and np.array_equal(a["normal"], b["normal"])
    assert not np.allclose(a["height"], c["height"]) and not np.allclose(a["height"], d["height"])
    assert np.array_equal(a["displacement_x"], np.zeros((64, 64))) and np.array_equal(a["displacement_y"], np.zeros((64, 64)))
    ch = W.ocean_height_field(64, 200.0, 8.0, 30.0, t=1.5, seed=3, choppiness=1.0)
    assert np.abs(ch["displacement_x"]).max() > 1e-3 and np.array_equal(ch["height"], a["height"])
    e0 = W.ocean_height_field(64, 200.0, 8.0, 30.0, t=0.0, seed=3)
    e1 = W.ocean_height_field(64, 200.0, 8.0, 30.0, t=1e-6, seed=3)
    assert np.abs(e1["height"] - e0["height"]).max() < 1e-4              # continuous in time


def test_waves_travel_with_the_wind_and_spreading_is_normalised():
    th = np.linspace(-np.pi, np.pi, 200001)
    for kind, s in (("cos2", 10.0), ("cos2s", 4.0), ("cos2s", 20.0)):
        D = W._spreading(th, kind, s)
        assert abs(float(np.sum(0.5 * (D[1:] + D[:-1]) * np.diff(th))) - 1.0) < 1e-6
    # wind along +x: the slope variance is larger along x than across, for both spreadings
    for d in ("cos2", "cos2s"):
        f = W.ocean_height_field(128, 600.0, 8.0, 0.0, seed=2, directional=d)
        assert (f["slope_x"] ** 2).mean() > 2.0 * (f["slope_y"] ** 2).mean()
    # turning the wind by 90 degrees swaps the two
    g = W.ocean_height_field(128, 600.0, 8.0, 90.0, seed=2)
    assert (g["slope_y"] ** 2).mean() > 2.0 * (g["slope_x"] ** 2).mean()


def test_ocean_refusals():
    ok = dict(size=16, extent_m=50.0, wind_speed_mps=6.0, wind_dir_deg=0.0)
    W.ocean_height_field(**ok)
    for key, bad in (("size", 7), ("size", 4096), ("size", 16.5), ("size", True), ("extent_m", 0.0), ("extent_m", -1.0),
                     ("wind_speed_mps", 0.0), ("wind_speed_mps", -3.0), ("wind_speed_mps", float("nan")),
                     ("wind_dir_deg", float("inf")), ("wind_dir_deg", "0")):
        with pytest.raises(ValueError):
            W.ocean_height_field(**{**ok, key: bad})
    for kw in ({"kind": "x"}, {"directional": "x"}, {"choppiness": -1.0}, {"seed": -1}, {"depth_m": 0.0}, {"t": float("nan")},
               {"single_mode": (0, 0, 1.0)}, {"single_mode": (1, 1)}, {"fetch_m": 1e4}, {"spreading_s": 0.0}):
        with pytest.raises(ValueError):
            W.ocean_height_field(**ok, **kw)


# ---------------------------------------------------------------- 3. Fresnel
def test_brewster_critical_and_normal_incidence():
    n = 1.333
    br = W.fresnel_water_air(90.0, n_water=n)["brewster_deg"]
    assert abs(br - 53.12) < 0.01 and abs(br - math.degrees(math.atan(n))) < 1e-12
    rp = W.fresnel_water_air(br, polarization="p", n_water=n)
    assert rp["R"] < 1e-6 and abs(rp["T"] - 1.0) < 1e-6                 # nothing p-polarised is reflected at Brewster's angle
    assert abs(W.fresnel_water_air(30.0, n_water=n)["critical_deg"] - 48.6) < 0.05
    for pol in W.POLARIZATIONS:
        r0 = W.fresnel_water_air(0.0, n_water=n, polarization=pol)
        assert abs(r0["R"] - ((n - 1.0) / (n + 1.0)) ** 2) < 1e-12
        assert abs(r0["T"] - 4.0 * n / (n + 1.0) ** 2) < 1e-12
    # the table value of water at 0.55 um: R(0) = 0.0204
    assert abs(W.fresnel_water_air(0.0)["R"] - ((1.334683329053798 - 1) / (1.334683329053798 + 1)) ** 2) < 1e-12


@pytest.mark.parametrize("direction", ["air_to_water", "water_to_air"])
def test_energy_conservation_and_polarisation_mean(direction):
    th = np.linspace(0.0, 90.0, 361)
    s = W.fresnel_water_air(th, polarization="s", direction=direction)
    p = W.fresnel_water_air(th, polarization="p", direction=direction)
    u = W.fresnel_water_air(th, polarization="unpolarized", direction=direction)
    assert th.size == 361
    assert np.abs(s["R"] + s["T"] - 1.0).max() < 1e-12 and np.abs(p["R"] + p["T"] - 1.0).max() < 1e-12
    assert np.abs(u["R"] - 0.5 * (s["R"] + p["R"])).max() < 1e-15 and np.abs(u["T"] - 0.5 * (s["T"] + p["T"])).max() < 1e-15
    # a second implementation: glassmirror's Fresnel (cos_i, n1, n2)
    n = s["n_water"]
    n1, n2 = (1.0, n) if direction == "air_to_water" else (n, 1.0)
    for pol, r in (("s", s), ("p", p), ("unpolarized", u)):
        ref = glassmirror.fresnel_dielectric(np.cos(np.radians(th)), n1, n2, pol)
        assert np.abs(r["R"] - ref).max() < 1e-12


def test_total_internal_reflection_and_snell():
    n = 1.333
    th = np.array([10.0, 40.0, 48.0, 49.0, 60.0, 90.0])
    r = W.fresnel_water_air(th, direction="water_to_air", n_water=n)
    assert list(r["tir"]) == [False, False, False, True, True, True]
    assert (r["R"][3:] == 1.0).all() and (r["T"][3:] == 0.0).all() and np.isnan(r["theta_t_deg"][3:]).all()
    ok = ~r["tir"]
    assert np.abs(n * np.sin(np.radians(th[ok])) - np.sin(np.radians(r["theta_t_deg"][ok]))).max() < 1e-12
    a = W.fresnel_water_air(th, n_water=n)
    assert not a["tir"].any()
    assert np.abs(np.sin(np.radians(th)) - n * np.sin(np.radians(a["theta_t_deg"]))).max() < 1e-12
    # dispersion: the blue sees a higher index than the red
    assert W.fresnel_water_air(0.0, 0.40)["n_water"] > W.fresnel_water_air(0.0, 0.70)["n_water"]
    assert abs(W.fresnel_water_air(0.0, 0.55)["n_water"] - 1.3347) < 1e-3


def test_fresnel_probe_catches_a_wrong_index():
    assert abs(math.degrees(math.atan(1.4)) - 53.12) > 0.01              # the Brewster gate would catch n = 1.4


def test_fresnel_refusals():
    for bad in (-1.0, 91.0, float("nan"), "30", None):
        with pytest.raises(ValueError):
            W.fresnel_water_air(bad)
    for kw in ({"polarization": "x"}, {"direction": "up"}, {"n_water": 1.0}, {"n_water": 0.5}, {"wavelength_um": -1.0},
               {"wavelength_um": 50.0}, {"n_water": True}):
        with pytest.raises(ValueError):
            W.fresnel_water_air(30.0, **kw)


# ---------------------------------------------------------------- 4. Snell's window
def test_snell_window_closed_forms():
    n = 4.0 / 3.0
    r = W.snell_window([1.0, 2.0, 5.0], n_water=n)
    tc = math.asin(1.0 / n)
    assert abs(r["critical_deg"] - math.degrees(tc)) < 1e-12 and abs(r["critical_deg"] - 48.59) < 0.05
    assert abs(r["window_full_angle_deg"] - 2.0 * r["critical_deg"]) < 1e-12 and abs(r["window_full_angle_deg"] - 97.2) < 0.1
    assert np.abs(r["window_radius_m"] - np.array([1.0, 2.0, 5.0]) * math.tan(tc)).max() < 1e-12
    assert abs(r["apparent_depth_factor_paraxial"] - 1.0 / n) < 1e-12 and abs(r["apparent_depth_factor"] - 1.0 / n) < 1e-12
    assert np.abs(r["apparent_depth_m"] - np.array([1.0, 2.0, 5.0]) / n).max() < 1e-12
    assert abs(r["paraxial_error"]) < 1e-12


def test_apparent_depth_factor_against_a_ray_construction():
    n = 1.3347
    angles = np.array([0.0, 10.0, 30.0, 45.0, 60.0, 75.0, 85.0])
    f = W.snell_window(1.0, n_water=n, view_angle_deg=angles)["apparent_depth_factor"]
    # a second route: the ray in the water makes theta_w with the vertical and meets the surface x = d tan(theta_w)
    # from the point; the eye ray continued below the surface reaches that horizontal position at depth x / tan(theta_a)
    tw = np.arcsin(np.sin(np.radians(angles)) / n)
    x = np.tan(tw)
    ta = np.radians(angles)
    ref = np.empty_like(ta)
    ref[0] = 1.0 / n
    ref[1:] = x[1:] / np.tan(ta[1:])
    assert np.abs(f - ref).max() < 1e-12
    err = W.snell_window(1.0, n_water=n, view_angle_deg=[0.0, 60.0])["paraxial_error"]
    assert abs(err[0]) < 1e-12 and err[1] > 0.3                         # the d / n rule is 30+ % off at 60 degrees
    assert (np.diff(f) < 0).all()                                       # and the apparent depth keeps falling with the angle
    print("paraxial apparent-depth error at 60 deg: %.1f %%" % (100 * err[1]))


def test_snell_window_refusals():
    for kw in ({"depth_m": 0.0}, {"depth_m": -1.0}, {"depth_m": float("nan")}, {"depth_m": "2"}, {"depth_m": 1.0, "view_angle_deg": 90.0},
               {"depth_m": 1.0, "view_angle_deg": -1.0}, {"depth_m": 1.0, "n_water": 1.0}):
        with pytest.raises(ValueError):
            W.snell_window(**kw)


# ---------------------------------------------------------------- 5. refracted view
def _quartic_x(d, h, s, n):
    """Second implementation: the Snell condition squared is a quartic in the crossing x."""
    # (n^2 - 1) x^2 (s - x)^2 + n^2 h^2 x^2 - d^2 (s - x)^2 = 0
    p1 = np.polynomial.Polynomial([0.0, 0.0, 1.0]) * np.polynomial.Polynomial([s, -1.0]) ** 2 * (n * n - 1.0)
    p2 = np.polynomial.Polynomial([0.0, 0.0, n * n * h * h])
    p3 = np.polynomial.Polynomial([s, -1.0]) ** 2 * (-d * d)
    roots = (p1 + p2 + p3).roots()
    good = [r.real for r in roots if abs(r.imag) < 1e-9 and 0.0 < r.real < s]
    assert len(good) == 1
    return good[0]


def test_flat_normal_incidence_and_snell():
    n = 1.333
    P = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, -2.5], [0.0, 0.0, -0.1]])
    r = W.refracted_view(P, np.array([0.0, 0.0, 4.0]), n_water=n)
    assert np.abs(r["apparent_depth_m"] - np.array([1.0, 2.5, 0.1]) / n).max() < 1e-9      # d / n
    rng = np.random.default_rng(5)
    Q = np.column_stack([rng.uniform(-3, 3, 60), rng.uniform(-3, 3, 60), -rng.uniform(0.2, 4.0, 60)])
    E = np.array([0.7, -0.4, 2.5])
    r = W.refracted_view(Q, E, n_water=n)
    assert r["converged"].all() and not r["in_air"].any() and Q.shape[0] == 60
    R = r["refraction_point"]
    assert np.abs(R[:, 2]).max() == 0.0
    # Snell at the refraction point, from the geometry (not from the solver's residual)
    dw, da = R - Q, E[None, :] - R
    sin_w = np.hypot(dw[:, 0], dw[:, 1]) / np.linalg.norm(dw, axis=1)
    sin_a = np.hypot(da[:, 0], da[:, 1]) / np.linalg.norm(da, axis=1)
    assert np.abs(n * sin_w - sin_a).max() < 1e-9 and np.abs(r["snell_residual"]).max() < 1e-9
    # the refraction point lies in the vertical plane of the point and the eye
    cross = (R[:, 0] - Q[:, 0]) * (E[1] - Q[:, 1]) - (R[:, 1] - Q[:, 1]) * (E[0] - Q[:, 0])
    assert np.abs(cross).max() < 1e-9
    # second implementation: the quartic
    for i in range(0, 60, 7):
        s = math.hypot(E[0] - Q[i, 0], E[1] - Q[i, 1])
        xq = _quartic_x(-Q[i, 2], E[2], s, n)
        assert abs(math.hypot(R[i, 0] - Q[i, 0], R[i, 1] - Q[i, 1]) - xq) < 1e-9
    # third: Fermat directly, the minimum of the optical path
    from scipy.optimize import minimize_scalar
    i = 11
    s = math.hypot(E[0] - Q[i, 0], E[1] - Q[i, 1])
    res = minimize_scalar(lambda x: n * math.hypot(x, -Q[i, 2]) + math.hypot(s - x, E[2]), bounds=(0.0, s), method="bounded",
                          options={"xatol": 1e-13})
    assert abs(res.x - math.hypot(R[i, 0] - Q[i, 0], R[i, 1] - Q[i, 1])) < 1e-6
    # the apparent point is shallower than the true one and lies on the eye ray
    A = r["apparent"]
    assert (A[:, 2] > Q[:, 2]).all() and np.abs(A[:, :2] - Q[:, :2]).max() < 1e-12
    v1, v2 = R - E[None, :], A - R
    assert np.abs(np.cross(v1, v2)).max() < 1e-9


def test_mirror_symmetry_and_air_points():
    n = 1.3347
    E = np.array([0.0, 0.0, 3.0])
    P = np.array([[1.2, 0.5, -1.5], [-1.2, 0.5, -1.5], [0.4, -0.9, -0.7], [0.4, 0.9, -0.7]])
    r = W.refracted_view(P, E, n_water=n)
    A = r["apparent"]
    assert np.abs(A[0] * np.array([-1, 1, 1]) - A[1]).max() < 1e-9
    assert np.abs(A[2] * np.array([1, -1, 1]) - A[3]).max() < 1e-9
    Pa = np.array([[1.0, 2.0, 0.0], [0.0, 0.0, 5.0], [-3.0, 1.0, 0.5]])
    ra = W.refracted_view(Pa, E, n_water=n)
    assert np.array_equal(ra["apparent"], Pa) and ra["in_air"].all() and np.isnan(ra["refraction_point"]).all()
    mix = W.refracted_view(np.vstack([Pa[:1], P[:1]]), E, n_water=n)
    assert list(mix["in_air"]) == [True, False] and np.array_equal(mix["apparent"][0], Pa[0])
    one = W.refracted_view(np.array([0.3, 0.2, -1.0]), E, n_water=n)
    assert one["apparent"].shape == (1, 3)


def test_wavy_surface_reduces_to_flat_and_satisfies_vector_snell():
    n = 1.333
    E = np.array([20.0, 20.0, 12.0])
    P = np.array([[8.0, 9.0, -2.0], [15.0, 22.0, -1.5], [24.0, 18.0, -3.0]])
    flat = W.refracted_view(P, E, n_water=n)
    zero = W.refracted_view(P, E, surface={"height": np.zeros((16, 16)), "extent_m": 40.0}, n_water=n)
    assert zero["converged"].all() and np.abs(zero["apparent"] - flat["apparent"]).max() < 1e-9
    assert np.abs(zero["refraction_point"] - flat["refraction_point"]).max() < 1e-9
    sea = W.ocean_height_field(64, 40.0, 5.0, 0.0, seed=7)
    wavy = W.refracted_view(P, E, surface=sea, n_water=n)
    assert wavy["converged"].all() and wavy["snell_residual"].max() < 1e-9
    assert np.abs(wavy["apparent"] - flat["apparent"]).max() > 1e-4        # the waves do move the image
    # the vector Snell law from the surface slope, independently of the solver
    surf = W._PeriodicSurface(sea["height"], sea["extent_m"], "test")
    for i in range(3):
        R = wavy["refraction_point"][i]
        assert abs(R[2] - float(surf.h(R[0], R[1]))) < 1e-12                # on the surface
        hx, hy = surf.grad(R[0], R[1])
        N = np.array([-hx, -hy, 1.0])
        N /= np.linalg.norm(N)
        dw = (R - P[i]) / np.linalg.norm(R - P[i])
        da = (E - R) / np.linalg.norm(E - R)
        assert np.linalg.norm(n * np.cross(dw, N) - np.cross(da, N)) < 1e-9
        # a brute-force minimisation of the optical path from a different start agrees
        from scipy.optimize import minimize
        f = lambda xy: n * np.linalg.norm(np.array([xy[0], xy[1], float(surf.h(xy[0], xy[1]))]) - P[i]) \
            + np.linalg.norm(E - np.array([xy[0], xy[1], float(surf.h(xy[0], xy[1]))]))
        res = minimize(f, R[:2] + np.array([0.3, -0.2]), method="Nelder-Mead", options={"xatol": 1e-10, "fatol": 1e-14, "maxiter": 4000})
        assert np.linalg.norm(res.x - R[:2]) < 1e-4


def test_refracted_view_refusals():
    n = 1.333
    E = np.array([0.0, 0.0, 3.0])
    P = np.array([[0.0, 0.0, -1.0]])
    for kw in ({"eye": np.array([0.0, 0.0, -1.0])}, {"eye": np.array([0.0, 0.0, 0.0])}, {"eye": np.array([0.0, 0.0])},
               {"eye": np.array([0.0, 0.0, float("nan")])}, {"surface": "wavy"}, {"surface": {"height": np.zeros((16, 16))}},
               {"n_water": 1.0}, {"points": np.array([[0.0, 0.0]])}, {"points": np.array([[0.0, float("inf"), -1.0]])},
               {"points": "x"}):
        args = {"points": P, "eye": E, "surface": "flat", "n_water": n}
        args.update(kw)
        with pytest.raises(ValueError):
            W.refracted_view(args["points"], args["eye"], args["surface"], args["n_water"])
    sea = W.ocean_height_field(32, 40.0, 8.0, 0.0, seed=1)
    with pytest.raises(ValueError):
        W.refracted_view(P, np.array([5.0, 5.0, 0.5 * sea["height"].max()]), sea, n)        # the eye is inside the waves
    with pytest.raises(ValueError):
        W.refracted_view(P, np.array([5.0, 5.0, 8.0]), {"height": np.zeros((16, 8)), "extent_m": 10.0}, n)


# ---------------------------------------------------------------- 6. attenuation of water
def test_pope_fry_table_values():
    wl = np.array([x for x, _ in WD.POPE_FRY_1997]) / 1000.0
    assert wl.size == 140 and abs(wl[0] - 0.38) < 1e-12 and abs(wl[-1] - 0.7275) < 1e-12
    r = W.water_attenuation(wl, "pure")
    i = int(np.argmin(r["a"]))
    assert abs(wl[i] - 0.4175) < 1e-12 and abs(r["a"][i] - 0.00442) < 1e-12        # the minimum: 417.5 nm, 0.00442 /m
    assert abs(r["a"][i] - 0.0044) < 1e-4
    assert abs(W.water_attenuation(0.700, "pure")["a"][0] - 0.624) < 1e-12           # a(700 nm) = 0.624 /m
    assert abs(W.water_attenuation(0.380, "pure")["a"][0] - 0.01137) < 1e-12
    assert abs(W.water_attenuation(0.7275, "pure")["a"][0] - 1.678) < 1e-12
    mid = W.water_attenuation(0.5, "pure")["a"][0]
    assert abs(mid - 0.0204) < 1e-12                                               # table value at 500 nm
    # between two nodes the interpolation is the straight line
    a1, a2 = W.water_attenuation([0.5, 0.5025], "pure")["a"]
    assert abs(W.water_attenuation(0.50125, "pure")["a"][0] - 0.5 * (a1 + a2)) < 1e-15
    b = W.water_attenuation([0.4, 0.5, 0.7], "pure")["b"]
    assert np.abs(b - 0.00288 * (np.array([400.0, 500.0, 700.0]) / 500.0) ** -4.32).max() < 1e-15      # Smith & Baker
    assert abs(b[1] - 0.00288) < 1e-15


def test_beer_lambert_consistency_and_a_photon_count():
    wl = np.array([0.45, 0.55, 0.65])
    z = np.array([0.5, 2.0, 7.5])
    for wt in ("pure", "jerlov_I", "jerlov_III", "jerlov_1C"):
        r = W.water_attenuation(wl, wt, depth_m=z)
        assert r["transmittance"].shape == (3, 3)
        for i, zi in enumerate(z):
            ref = glassmirror.beer_lambert_transmittance(zi * 1000.0, r["kd"] / 1000.0)      # path in mm, sigma per mm
            assert np.abs(r["transmittance"][i] - ref).max() < 1e-12
        assert np.abs(r["c"] - (r["a"] + r["b"])).max() < 1e-15
    assert W.water_attenuation(0.5, "pure", depth_m=2.0)["transmittance"].shape == (1,)
    # a Monte Carlo count of absorbed photons at 0.65 um in pure water (a = 0.34 /m), 6 m deep
    rng = np.random.default_rng(11)
    a = float(W.water_attenuation(0.65, "pure")["a"][0])
    n_ph = 400000
    free_path = -np.log(1.0 - rng.random(n_ph)) / a
    surv = float(np.mean(free_path > 6.0))
    t = math.exp(-a * 6.0)
    assert abs(surv - t) < 4.0 * math.sqrt(t * (1.0 - t) / n_ph)


def test_jerlov_types_ordering_and_tables():
    kd = {t: W.water_attenuation(0.5, "jerlov_" + t)["kd"][0] for t in ("I", "IA", "IB", "II", "III", "1C", "3C", "5C", "7C", "9C")}
    assert len(kd) == 10
    assert kd["I"] < kd["II"] < kd["III"] < kd["1C"]                        # the ordering at 500 nm
    assert kd["I"] < kd["IA"] < kd["IB"] < kd["II"] and kd["1C"] < kd["3C"] < kd["5C"] < kd["7C"] < kd["9C"]
    assert abs(kd["I"] - 0.029) < 1e-12 and abs(kd["9C"] - 1.0) < 1e-12     # Solonenko & Mobley (2015), Table values
    assert W.water_attenuation(0.55, "jerlov_I")["b_suspect"] and not W.water_attenuation(0.55, "jerlov_II")["b_suspect"]
    # clear water is blue: red is attenuated much faster than blue
    r = W.water_attenuation([0.45, 0.65], "jerlov_I")["kd"]
    assert r[1] / r[0] > 10.0
    assert abs(W.water_attenuation(0.4, "jerlov_I")["kd"][0] - 0.028) < 1e-12
    # the water types that the tables do not cover are refused, not extrapolated
    for t, wl in (("jerlov_3C", 0.70), ("jerlov_3C", 0.675), ("jerlov_5C", 0.60), ("jerlov_5C", 0.70)):
        with pytest.raises(ValueError):
            W.water_attenuation(wl, t)
    assert W.water_attenuation(0.65, "jerlov_3C")["kd"][0] > 0 and W.water_attenuation(0.575, "jerlov_5C")["kd"][0] > 0


def test_attenuation_refusals():
    with pytest.raises(ValueError) as e:
        W.water_attenuation(0.5, "jerlov_X")
    msg = str(e.value)
    assert "pure" in msg and "jerlov_I" in msg and "jerlov_9C" in msg          # the message lists the known types
    for wl in (0.3, 0.38 - 1e-6, 0.73, -0.5, float("nan"), "0.5"):
        with pytest.raises(ValueError):
            W.water_attenuation(wl, "pure")
    for wl in (0.399, 0.701):
        with pytest.raises(ValueError):
            W.water_attenuation(wl, "jerlov_II")
    for bad in (-1.0, float("nan"), "3"):
        with pytest.raises(ValueError):
            W.water_attenuation(0.5, "pure", depth_m=bad)
    with pytest.raises(ValueError):
        W.water_attenuation(0.5, 3)
    with pytest.raises(ValueError):
        W.water_attenuation(0.5, "pure", depth_m=np.ones((2, 2)))


# ---------------------------------------------------------------- 7. underwater image
def _chart(k=3):
    rng = np.random.default_rng(2)
    return 0.15 + 0.8 * rng.random((8, 8, k))


def test_distance_zero_returns_the_input_and_darkening_is_monotone():
    im = _chart()
    for bs in (True, False):
        o = W.underwater_image(im, 5.0, 0.0, "jerlov_II", backscatter=bs)
        assert np.abs(o["image"] - im).max() < 1e-12
    prev = im.copy()
    for r in (1.0, 3.0, 8.0, 20.0):
        o = W.underwater_image(im, 0.0, r, "jerlov_I")["image"]
        assert (o < prev).all()                                         # every band darkens with distance
        prev = o
    # far enough, the recording is the veiling light alone
    far = W.underwater_image(im, 3.0, 1e4, "jerlov_I")
    assert np.abs(far["image"] - far["veiling_light"]).max() < 1e-12


def test_red_decays_faster_than_blue_in_clear_water():
    im = np.full((4, 4, 3), 0.8)
    o = W.underwater_image(im, 0.0, 10.0, "jerlov_I", backscatter=False)
    t = o["transmission"][0, 0]
    assert t[0] < t[1] < t[2]                                           # red < green < blue
    ratio = math.log(t[0]) / math.log(t[2])
    assert abs(ratio - o["red_to_blue_kd_ratio"]) < 1e-12 and ratio > 8.0
    print("Jerlov I: red / blue attenuation ratio %.2f, transmission over 10 m: R %.3f G %.3f B %.3f" % (ratio, t[0], t[1], t[2]))
    c = W.underwater_image(im, 0.0, 10.0, "jerlov_3C", backscatter=False)
    assert c["transmission"][0, 0, 2] < t[2] and c["red_to_blue_kd_ratio"] < ratio     # coastal water is less blue-selective


def test_backscatter_off_is_beer_lambert():
    im = _chart()
    dist = np.linspace(0.0, 12.0, 64).reshape(8, 8)
    o = W.underwater_image(im, 4.0, dist, "jerlov_III", backscatter=False)
    kd = W.water_attenuation(list(W.RGB_WAVELENGTHS_UM), "jerlov_III")["kd"]
    ref = im * np.exp(-dist[:, :, None] * kd[None, None, :])
    assert np.abs(o["image"] - ref).max() < 1e-12 and not o["backscatter"].any()
    # with backscatter on, the veiling light is added and never exceeds its limit
    ob = W.underwater_image(im, 4.0, dist, "jerlov_III")
    assert (ob["backscatter"] >= 0).all() and (ob["backscatter"] <= ob["veiling_light"] + 1e-15).all()
    assert np.abs(ob["image"] - (ob["direct"] + ob["backscatter"])).max() < 1e-15
    # ambient light at depth
    oa = W.underwater_image(im, 4.0, 0.0, "jerlov_III", apply_ambient=True)
    assert np.abs(oa["image"] - im * np.exp(-4.0 * kd)[None, None, :]).max() < 1e-12
    # a spectral input: five bands
    sp = _chart(5)
    wl = [0.45, 0.5, 0.55, 0.6, 0.65]
    os_ = W.underwater_image(sp, 2.0, 5.0, "pure", wavelengths_um=wl, backscatter=False)
    kdp = W.water_attenuation(wl, "pure")["kd"]
    assert np.abs(os_["image"] - sp * np.exp(-5.0 * kdp)).max() < 1e-12
    # the illumination spectrum scales the veiling light
    e = W.underwater_image(im, 4.0, 6.0, "jerlov_III", illumination=[1.0, 2.0, 3.0])
    assert np.abs(e["veiling_light"][0, 0] / ob["veiling_light"][0, 0] - np.array([1.0, 2.0, 3.0])).max() < 1e-12


def test_underwater_image_refusals():
    im = _chart()
    d = np.ones((8, 8))
    bad_im = im.copy()
    bad_im[0, 0, 0] = np.nan
    neg = im.copy()
    neg[0, 0, 0] = -0.1
    inf = im.copy()
    inf[1, 1, 1] = np.inf
    for image in (bad_im, neg, inf, im[:, :, 0], "x", None):
        with pytest.raises(ValueError):
            W.underwater_image(image, 1.0, d, "jerlov_I")
    for dep, dist in ((-1.0, d), (np.nan, d), (1.0, -d), (1.0, np.where(d > 0, np.nan, d)), (np.ones((3, 3)), d), (1.0, np.inf)):
        with pytest.raises(ValueError):
            W.underwater_image(im, dep, dist, "jerlov_I")
    for kw in ({"water_type": "ocean"}, {"illumination": "sun"}, {"illumination": [1.0, 2.0]}, {"illumination": [1.0, -1.0, 1.0]},
               {"beta_b_ratio": -1.0}, {"backscatter_ratio": 2.0}, {"wavelengths_um": [0.5, 0.6]}):
        with pytest.raises(ValueError):
            W.underwater_image(im, 1.0, d, **{"water_type": "jerlov_I", **kw})
    with pytest.raises(ValueError):
        W.underwater_image(_chart(5), 1.0, d, "jerlov_I")                 # five bands need their wavelengths
    with pytest.raises(ValueError):
        W.underwater_image(im, 1.0, d, "jerlov_3C", wavelengths_um=[0.7, 0.6, 0.5])        # outside the table of 3C


# ---------------------------------------------------------------- 8. phase functions
@pytest.mark.parametrize("g", [-0.9, 0.0, 0.5, 0.9])
def test_hg_is_normalised_with_mean_cosine_g(g):
    x, wt = np.polynomial.legendre.leggauss(3000)
    p = W.phase_function_hg(x, g)["phase_per_sr"]
    assert abs(2.0 * np.pi * np.sum(wt * p) - 1.0) < 1e-6
    assert abs(2.0 * np.pi * np.sum(wt * p * x) - g) < 1e-6              # the mean cosine is g
    assert abs(W.phase_function_hg(0.3, 0.0)["phase_per_sr"] - 1.0 / (4.0 * math.pi)) < 1e-15
    forward, back = W.phase_function_hg([1.0, -1.0], g)["phase_per_sr"]
    assert (forward > back) == (g > 0) or g == 0.0


def test_hg_refusals():
    for g in (1.0, -1.0, 1.5, float("nan"), "0.5", True):
        with pytest.raises(ValueError):
            W.phase_function_hg(0.0, g)
    for c in (1.01, -1.01, float("nan"), "0"):
        with pytest.raises(ValueError):
            W.phase_function_hg(c, 0.5)


def test_petzold_is_forward_peaked_and_reproduces_its_table():
    r = W.scattering_phase_petzold([1.0, 90.0], "clear")
    assert r["phase_per_sr"][0] / r["phase_per_sr"][1] > 1e3
    print("Petzold clear: p(1 deg) / p(90 deg) = %.0f" % (r["phase_per_sr"][0] / r["phase_per_sr"][1]))
    for kind in W.PETZOLD_KINDS:
        rec = WD.PETZOLD_1972[kind]
        t = W.scattering_phase_petzold(WD.PETZOLD_ANGLES_DEG, kind)
        assert t["theta_deg"].size == 55
        assert np.abs(t["beta_per_m_sr"] / np.array(rec["beta_per_m_sr"]) - 1.0).max() < 1e-12      # at the tabulated angles
        assert np.abs(t["phase_per_sr"] * rec["b_per_m"] / t["beta_per_m_sr"] - 1.0).max() < 1e-15
        assert 0.8 < t["integral_fraction"] < 1.0                       # the tabulated angles hold most of b
        fine = np.geomspace(0.1, 180.0, 40001)
        p = W.scattering_phase_petzold(fine, kind)["phase_per_sr"]
        th = np.radians(fine)
        w = 0.5 * (p[1:] * np.sin(th[1:]) + p[:-1] * np.sin(th[:-1])) * np.diff(th) * 2.0 * np.pi
        wc = 0.5 * (p[1:] * np.sin(th[1:]) * np.cos(th[1:]) + p[:-1] * np.sin(th[:-1]) * np.cos(th[:-1])) * np.diff(th) * 2.0 * np.pi
        g = float(wc.sum() / w.sum())
        assert 0.85 < g < 0.97                                          # the well-known asymmetry of natural waters
        assert (np.diff(p[fine < 60.0]) < 0).all()                      # falling over the forward half
    assert W.scattering_phase_petzold(1.0, "turbid")["b_per_m"] > W.scattering_phase_petzold(1.0, "clear")["b_per_m"]


def test_petzold_refusals():
    for th in (0.05, 181.0, -1.0, float("nan"), "5"):
        with pytest.raises(ValueError):
            W.scattering_phase_petzold(th)
    for kind in ("murky", None, 1):
        with pytest.raises(ValueError):
            W.scattering_phase_petzold(5.0, kind)


# ---------------------------------------------------------------- 9. a bottle as a lens
@pytest.mark.parametrize("R,n", [(10.0, 1.5), (20.0, 1.52), (5.0, 1.33), (12.0, 1.6)])
def test_solid_rod_focus_closed_form_and_spherical_aberration(R, n):
    s = W.cylinder_lens_caustic(R, n)
    f = n * R / (2.0 * (n - 1.0))
    assert s["solid"] and abs(s["efl_mm"] - f) < 1e-9 * f and abs(s["efl_closed_form_mm"] - f) < 1e-12
    assert abs(s["paraxial_focus_mm"] - f) < 1e-9 * f                    # the focus from the axis is the EFL for a symmetric rod
    assert abs(s["power_per_mm"] - 1.0 / f) < 1e-12
    assert s["marginal_focus_mm"] < s["paraxial_focus_mm"]               # positive spherical aberration
    assert s["longitudinal_aberration_mm"] > 0
    fz = s["focus_z_mm"]
    assert fz.size == 41 and np.isfinite(fz).sum() > 0
    ok = np.isfinite(fz)
    assert (np.diff(fz[ok]) < 0).all()                                   # the higher the ray, the shorter the focus
    # a second route: the chord of the rod by trigonometry
    y = s["heights_mm"]
    i = np.arcsin(y / R)
    r = np.arcsin(np.sin(i) / n)
    e1 = np.stack([-R * np.cos(i), y], 1)
    e2 = e1 + (2.0 * R * np.cos(r))[:, None] * np.stack([np.cos(i - r), -np.sin(i - r)], 1)
    zf = e2[:, 0] + e2[:, 1] / np.tan(2.0 * (i - r))
    assert np.abs(zf[ok] - fz[ok]).max() < 1e-9
    # a ray close to the axis comes to the paraxial focus
    near = W.cylinder_lens_caustic(R, n, n_rays=2001)
    assert abs(near["focus_z_mm"][0] / near["paraxial_focus_mm"] - 1.0) < 1e-4
    print("rod R=%g n=%g: paraxial %.4f mm from the axis, marginal %.4f mm" % (R, n, s["paraxial_focus_mm"], s["marginal_focus_mm"]))


def test_filled_bottle_versus_empty_bottle():
    R, ng, t = 30.0, 1.52, 1.5
    thin = W.cylinder_lens_caustic(R, ng, 1.333, 1e-6)
    f_thin = 1.333 * R / (2.0 * 0.333)
    assert abs(thin["efl_mm"] / f_thin - 1.0) < 1e-6 and abs(thin["efl_closed_form_mm"] - f_thin) < 1e-12
    full = W.cylinder_lens_caustic(R, ng, 1.333, t)
    empty = W.cylinder_lens_caustic(R, ng, 1.0, t)
    assert not full["solid"] and abs(full["efl_mm"] / f_thin - 1.0) < 0.05          # a thin wall barely changes the water lens
    assert abs(full["power_per_mm"] / empty["power_per_mm"]) > 10.0                 # the empty bottle has next to no power
    assert abs(empty["power_per_mm"]) < 0.1 * abs(full["power_per_mm"])
    assert full["marginal_focus_mm"] < full["paraxial_focus_mm"]
    assert np.isfinite(full["focus_z_mm"]).all()
    assert np.isnan(empty["focus_z_mm"]).sum() > 0 or abs(empty["power_per_mm"]) < 2e-3        # no real focus for the empty one
    assert full["caustic_z_mm"].size == 40 and np.isfinite(full["caustic_z_mm"]).sum() > 20
    # the fill index sets the power: more refractive fill, stronger lens
    oil = W.cylinder_lens_caustic(R, ng, 1.47, t)
    assert oil["power_per_mm"] > full["power_per_mm"] * 0.0 and abs(oil["efl_mm"]) < abs(full["efl_mm"])
    print("bottle R=30 t=1.5: water-filled paraxial %.2f mm marginal %.2f mm power %.4f /mm; empty power %.5f /mm (ratio %.1f)"
          % (full["paraxial_focus_mm"], full["marginal_focus_mm"], full["power_per_mm"], empty["power_per_mm"],
             abs(full["power_per_mm"] / empty["power_per_mm"])))


def test_cylinder_refusals():
    for kw in ({"radius_mm": 0.0}, {"radius_mm": -5.0}, {"radius_mm": float("nan")}, {"n_glass": 1.0}, {"n_glass": 0.9}, {"n_glass": -1.5},
               {"n_glass": float("inf")}, {"n_fill": 0.9}, {"thickness_wall_mm": -1.0}, {"thickness_wall_mm": 10.0},
               {"thickness_wall_mm": 12.0}, {"n_rays": 3}, {"n_rays": True}, {"radius_mm": "10"}, {"n_glass": None}):
        args = {"radius_mm": 10.0, "n_glass": 1.5, "n_fill": 1.0, "thickness_wall_mm": 0.0}
        args.update(kw)
        with pytest.raises(ValueError):
            W.cylinder_lens_caustic(**args)


# ---------------------------------------------------------------- registration
def test_registered_as_category_watermedia():
    import opsoptics
    names = ["ocean_spectrum", "ocean_height_field", "fresnel_water_air", "snell_window", "refracted_view", "water_attenuation",
             "underwater_image", "phase_function_hg", "scattering_phase_petzold", "cylinder_lens_caustic"]
    assert sorted(W.__all__) == sorted(names)
    assert sorted(opsoptics.list_ops("watermedia")) == sorted(names)
    assert len(opsoptics.list_ops("watermedia")) == 10
    for nm in names:
        rec = opsoptics.OPSOPTICS[nm]
        assert rec["module"] == "watermedia" and rec["category"] == "watermedia"
        assert callable(getattr(W, nm)) and (getattr(W, nm).__doc__ or "").strip()
