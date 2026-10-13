# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""flyvision, 2026-10-13 — a periodic surface seen by a periodic eye (the zebra question).

Six operators, each scored against a closed form rather than a golden file:

  * :func:`fly_view_plane_texture` — the analytic acceptance integral: a sinusoid's
    amplitude at the central ommatidium is ``c mu exp(-pi^2 drho^2 (D/P)^2 / 4 ln2)``
    and its angular frequency at azimuth theta is ``D/(P cos^2 theta)``;
  * :func:`sampling_alias_distance` — ``P cos^2 theta / (sqrt 3 dphi)``: 2.105 m /
    0.526 m for a 7 cm period on a 1.1-degree eye, 0.500 / 0.125 m on a 4.63-degree
    eye, and the acceptance's MTF at Nyquist 0.375 / 0.024;
  * :func:`fly_expansion_readout` — the exact plane flow returns tau, the
    aperture-projected flow returns 2 tau;
  * :func:`traj_tau_dot` — tau-dot is -1 at constant speed and -0.5 under the
    constant deceleration that stops at the target (Lee 1976);
  * :func:`fly_vogel_lattice` — same count, mean nearest-neighbour angle == dphi,
    Delaunay mean degree ~ 6, no hexagonal neighbourhood (refused where one is needed);
  * :func:`lattice_moire_peak` — a sinusoid just below Nyquist is one sharp peak on
    the hexagon and a much flatter one on the Vogel eye.
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

NEW_OPS = ("fly_view_plane_texture", "sampling_alias_distance", "fly_expansion_readout",
           "traj_tau_dot", "fly_vogel_lattice", "lattice_moire_peak")


def _centre(lat):
    uv = np.asarray(lat["uv"])
    return int(np.where((uv[:, 0] == 0) & (uv[:, 1] == 0))[0][0])


def _mtf(drho_deg, f_cyc_per_rad):
    d = np.deg2rad(drho_deg)
    return np.exp(-np.pi ** 2 * d * d * f_cyc_per_rad ** 2 / (4.0 * np.log(2.0)))


# --------------------------------------------------------------------------- #
# 1. the analytic surface                                                      #
# --------------------------------------------------------------------------- #
class TestViewPlaneTexture:
    def test_sine_amplitude_at_the_centre_is_the_acceptance_mtf(self):
        lat = fv.fly_hex_lattice(radius=6, dphi_deg=1.1)
        c = _centre(lat)
        for D, P, drho in ((1.0, 0.07, 1.0), (0.4, 0.07, 8.23), (2.0, 0.05, 1.5)):
            v0 = fv.fly_view_plane_texture(lat, D, P, "sine", drho_deg=drho,
                                           contrast=0.8, mean=0.5)[c] - 0.5
            v90 = fv.fly_view_plane_texture(lat, D, P, "sine", drho_deg=drho,
                                            contrast=0.8, mean=0.5, phase_deg=90.0)[c] - 0.5
            amp = float(np.hypot(v0, v90))
            assert abs(amp - 0.4 * _mtf(drho, D / P)) < 1e-9

    def test_off_axis_frequency_carries_the_cos_squared(self):
        """At azimuth theta on the equator the angular frequency is D/(P cos^2 theta)."""
        lat = fv.fly_hex_lattice(radius=8, dphi_deg=1.1)
        uv = np.asarray(lat["uv"])
        row = np.where(uv[:, 0] == 0)[0]                      # the equator
        th = np.asarray(lat["az_rad"])[row]
        D, P, drho = 1.0, 0.07, 1.0
        v0 = fv.fly_view_plane_texture(lat, D, P, "sine", drho_deg=drho, contrast=0.8)[row] - 0.5
        v90 = fv.fly_view_plane_texture(lat, D, P, "sine", drho_deg=drho, contrast=0.8,
                                        phase_deg=90.0)[row] - 0.5
        amp = np.hypot(v0, v90)
        pred = 0.4 * _mtf(drho, D / (P * np.cos(th) ** 2))
        assert np.abs(amp - pred).max() < 1e-9

    def test_the_closed_form_agrees_with_the_alias_distance_op(self):
        """The MTF at the Nyquist distance of sampling_alias_distance is its mtf_at_nyquist."""
        lat = fv.fly_hex_lattice(radius=4, dphi_deg=1.1)
        c = _centre(lat)
        r = fv.sampling_alias_distance(0.07, 1.1, acceptance_deg=1.0)
        D = r["distance_m"]
        v0 = fv.fly_view_plane_texture(lat, D, 0.07, "sine", drho_deg=1.0)[c] - 0.5
        v90 = fv.fly_view_plane_texture(lat, D, 0.07, "sine", drho_deg=1.0, phase_deg=90.0)[c] - 0.5
        assert abs(np.hypot(v0, v90) / 0.5 - r["mtf_at_nyquist"]) < 1e-9

    def test_stripes_and_checker_are_bounded_and_grey_is_flat(self):
        lat = fv.fly_hex_lattice(radius=6, dphi_deg=1.1)
        for pat in ("vertical", "horizontal", "checker", "pink"):
            s = fv.fly_view_plane_texture(lat, 0.6, 0.07, pat, drho_deg=1.0, contrast=0.9, mean=0.5)
            assert s.shape == (lat["dirs"].shape[0],)
            assert np.isfinite(s).all() and s.min() >= 0.0 and s.max() <= 0.5 * 1.9 + 1e-9
            assert s.std() > 0.05, pat
        g = fv.fly_view_plane_texture(lat, 0.6, 0.07, "grey", drho_deg=1.0)
        assert np.allclose(g, 0.5)

    def test_a_square_wave_far_below_nyquist_keeps_its_fourier_amplitude(self):
        """Near the centre, with a coarse stripe, the fundamental's amplitude is 4/pi * MTF."""
        lat = fv.fly_hex_lattice(radius=3, dphi_deg=0.5)
        c = _centre(lat)
        D, P = 0.5, 0.2                                        # 23-degree angular period
        vals = np.array([fv.fly_view_plane_texture(lat, D, P, "vertical", drho_deg=1.0,
                                                   phase_deg=ph)[c] - 0.5
                         for ph in np.linspace(0.0, 360.0, 64, endpoint=False)])
        spec = np.fft.rfft(vals) / vals.size
        fund = 2.0 * abs(spec[1])
        assert abs(fund - 0.5 * 4.0 / np.pi * _mtf(1.0, D / P)) < 1e-3

    def test_a_vogel_eye_is_accepted(self):
        v = fv.fly_vogel_lattice(radius=4, dphi_deg=1.1)
        s = fv.fly_view_plane_texture(v, 0.8, 0.07, "vertical", drho_deg=1.0)
        assert s.shape == (v["dirs"].shape[0],) and s.std() > 0.05

    def test_refusals(self):
        lat = fv.fly_hex_lattice(radius=3)
        with pytest.raises(ValueError):
            fv.fly_view_plane_texture({}, 1.0, 0.07)
        with pytest.raises(ValueError):
            fv.fly_view_plane_texture(lat, 0.0, 0.07)
        with pytest.raises(ValueError):
            fv.fly_view_plane_texture(lat, 1.0, 0.07, "zebra")
        with pytest.raises(ValueError):
            fv.fly_view_plane_texture(lat, 1.0, 0.07, contrast=1.5)
        with pytest.raises(ValueError):
            fv.fly_view_plane_texture(lat, 1.0, 0.07, lateral_m=(1.0,))
        with pytest.raises(ValueError):
            fv.fly_view_plane_texture(lat, 1.0, 0.07, mean=0.0)


# --------------------------------------------------------------------------- #
# 2. the alias distance                                                        #
# --------------------------------------------------------------------------- #
class TestAliasDistance:
    def test_the_report_numbers(self):
        r = fv.sampling_alias_distance(0.07, 1.1, acceptance_deg=1.0)
        assert abs(r["distance_m"] - 2.105) < 2e-3
        assert abs(r["mtf_at_nyquist"] - 0.375) < 1e-3
        assert abs(fv.sampling_alias_distance(0.07, 1.1, view_angle_deg=60.0)["distance_m"]
                   - 0.526) < 1e-3
        r = fv.sampling_alias_distance(0.07, 4.63, acceptance_deg=8.23)
        assert abs(r["distance_m"] - 0.500) < 1e-3
        assert abs(r["mtf_at_nyquist"] - 0.024) < 1e-3
        assert abs(fv.sampling_alias_distance(0.07, 4.63, view_angle_deg=60.0)["distance_m"]
                   - 0.125) < 1e-3

    def test_square_lattice_and_across_obliquity(self):
        h = fv.sampling_alias_distance(0.07, 1.1)["distance_m"]
        s = fv.sampling_alias_distance(0.07, 1.1, lattice="square")["distance_m"]
        assert abs(s / h - np.sqrt(3.0) / 2.0) < 1e-12
        along = fv.sampling_alias_distance(0.07, 1.1, view_angle_deg=60.0)["distance_m"]
        across = fv.sampling_alias_distance(0.07, 1.1, view_angle_deg=60.0,
                                            obliquity="across")["distance_m"]
        assert abs(across / along - 2.0) < 1e-12
        assert fv.sampling_alias_distance(0.07, 1.1)["mtf_at_nyquist"] == 1.0

    def test_refusals(self):
        for bad in (dict(period_m=0.0, pitch_deg=1.0), dict(period_m=0.07, pitch_deg=-1.0),
                    dict(period_m=0.07, pitch_deg=1.0, view_angle_deg=90.0),
                    dict(period_m=0.07, pitch_deg=1.0, lattice="triangle"),
                    dict(period_m=0.07, pitch_deg=1.0, acceptance_deg=-1.0),
                    dict(period_m=[], pitch_deg=1.0)):
            with pytest.raises(ValueError):
                fv.sampling_alias_distance(**bad)


# --------------------------------------------------------------------------- #
# 3. the expansion readout and the aperture effect's 2 tau                     #
# --------------------------------------------------------------------------- #
def _plane_flow(lat, tau):
    """Exact flow of a fronto-parallel plane approach: sin cos / tau, outward."""
    dirs = lat["dirs"]
    a = dirs[_centre(lat)]
    el = np.asarray(lat["el_rad"])
    az = np.asarray(lat["az_rad"])
    e_az = np.stack([-np.sin(az), np.cos(az), np.zeros_like(az)], axis=-1)
    e_el = np.stack([-np.sin(el) * np.cos(az), -np.sin(el) * np.sin(az), np.cos(el)], axis=-1)
    cosang = np.clip(dirs @ a, -1.0, 1.0)
    th = np.arccos(cosang)
    r = -(a[None, :] - cosang[:, None] * dirs)
    rn = np.linalg.norm(r, axis=1)
    r[rn > 1e-12] /= rn[rn > 1e-12, None]
    radial = np.stack([(r * e_az).sum(1), (r * e_el).sum(1)], axis=1)
    return (np.sin(th) * np.cos(th) / tau)[:, None] * radial


class TestExpansionReadout:
    def test_the_exact_plane_flow_returns_tau_from_both_readouts(self):
        lat = fv.fly_hex_lattice(radius=10, dphi_deg=2.0)
        f = _plane_flow(lat, 1.7)
        r = fv.fly_expansion_readout(f, lat)
        assert abs(r["tau_s"] - 1.7) < 1e-9
        assert abs(r["tau_div_s"] - 1.7) < 1e-9
        assert r["aperture_ratio"] > 0.999 and r["residual_rms"] < 1e-12

    def test_the_aperture_effect_doubles_tau(self):
        lat = fv.fly_hex_lattice(radius=10, dphi_deg=1.0)         # a 10-degree field
        f = _plane_flow(lat, 1.7)
        f[:, 1] = 0.0                                             # vertical stripes: no elevation flow
        r = fv.fly_expansion_readout(f, lat)
        assert abs(r["tau_s"] / 3.4 - 1.0) < 0.01
        assert abs(r["tau_div_s"] / 3.4 - 1.0) < 0.01
        assert r["aperture_ratio"] < 0.02

    def test_a_receding_surface_has_no_time_to_contact(self):
        lat = fv.fly_hex_lattice(radius=5, dphi_deg=2.0)
        r = fv.fly_expansion_readout(-_plane_flow(lat, 1.0), lat)
        assert np.isnan(r["tau_s"]) and np.isnan(r["tau_div_s"]) and r["rate_1_s"] < 0.0

    def test_weights_can_drop_the_rim(self):
        lat = fv.fly_hex_lattice(radius=8, dphi_deg=2.0)
        f = _plane_flow(lat, 2.0)
        rim = np.abs(np.asarray(lat["uv"])).max(axis=1) == 8
        f[rim] = 0.0                                              # what fly_flow_from_directions reports there
        wrong = fv.fly_expansion_readout(f, lat)["tau_s"]
        right = fv.fly_expansion_readout(f, lat, weights=(~rim).astype(float))["tau_s"]
        assert abs(right - 2.0) < 1e-9 and abs(wrong - 2.0) > 0.05

    def test_a_vogel_eye_is_accepted(self):
        v = fv.fly_vogel_lattice(radius=8, dphi_deg=2.0)
        r = fv.fly_expansion_readout(_plane_flow(v, 1.3), v)
        assert abs(r["tau_s"] - 1.3) < 1e-9

    def test_refusals(self):
        lat = fv.fly_hex_lattice(radius=3)
        n = lat["dirs"].shape[0]
        with pytest.raises(ValueError):
            fv.fly_expansion_readout(np.zeros((0, 2)), lat)
        with pytest.raises(ValueError):
            fv.fly_expansion_readout(np.zeros((n, 3)), lat)
        with pytest.raises(ValueError):
            fv.fly_expansion_readout(np.zeros((n, 2)), lat, weights=np.zeros(n))
        with pytest.raises(ValueError):
            fv.fly_expansion_readout(np.zeros((n, 2)), lat, axis=(0.0, 0.0, 0.0))


# --------------------------------------------------------------------------- #
# 4. tau-dot along a measured trajectory                                       #
# --------------------------------------------------------------------------- #
class TestTrajTauDot:
    def test_constant_speed_has_tau_dot_minus_one(self):
        t = np.linspace(0.0, 1.5, 151)
        pts = np.stack([2.0 - 0.5 * t, np.zeros_like(t), np.zeros_like(t)], axis=1)
        r = fv.traj_tau_dot(pts, t)
        assert np.abs(r["tau_dot"] + 1.0).max() < 1e-9
        assert np.abs(r["tau_s"] - (2.0 - 0.5 * t) / 0.5).max() < 1e-9
        assert abs(r["speed_m_s"].mean() - 0.5) < 1e-12 and r["mode"] == "point"

    def test_stopping_deceleration_has_tau_dot_minus_half(self):
        a, d0 = 1.0, 2.0
        v0 = np.sqrt(2.0 * a * d0)
        t = np.linspace(0.0, 0.9 * v0 / a, 200)
        d = d0 - v0 * t + 0.5 * a * t * t
        pts = np.stack([d, 0.3 + 0.0 * t, 0.0 * t], axis=1)
        r = fv.traj_tau_dot(pts, t, normal=(1.0, 0.0, 0.0))
        assert np.abs(r["tau_dot"] + 0.5).max() < 1e-9
        assert r["mode"] == "plane" and abs(r["closest_m"] - d[-1]) < 1e-12

    def test_receding_samples_are_nan(self):
        t = np.linspace(0.0, 1.0, 21)
        pts = np.stack([1.0 + t, 0.0 * t, 0.0 * t], axis=1)
        r = fv.traj_tau_dot(pts, t)
        assert np.isnan(r["tau_s"]).all()

    def test_refusals(self):
        t = np.linspace(0.0, 1.0, 5)
        pts = np.zeros((5, 3))
        with pytest.raises(ValueError):
            fv.traj_tau_dot(np.zeros((0, 3)), t[:0])
        with pytest.raises(ValueError):
            fv.traj_tau_dot(pts, t[::-1])
        with pytest.raises(ValueError):
            fv.traj_tau_dot(pts[:, :2], t)
        with pytest.raises(ValueError):
            fv.traj_tau_dot(pts, t, normal=(0.0, 0.0, 0.0))


# --------------------------------------------------------------------------- #
# 5. the Fibonacci eye                                                         #
# --------------------------------------------------------------------------- #
class TestVogelLattice:
    def test_count_spacing_and_unit_vectors(self):
        for R, dphi in ((5, 4.63), (15, 1.1)):
            v = fv.fly_vogel_lattice(radius=R, dphi_deg=dphi)
            assert v["dirs"].shape[0] == 3 * R * (R + 1) + 1
            assert np.allclose(np.linalg.norm(v["dirs"], axis=1), 1.0, atol=1e-12)
            assert abs(float(v["nn_rad"].mean()) / np.deg2rad(dphi) - 1.0) < 1e-6
            assert v["geometry"] == "vogel" and v["uv"][0].tolist() == [0, 0]

    def test_nearest_neighbour_spread_and_the_fovea_knob(self):
        uni = fv.fly_vogel_lattice(radius=15, dphi_deg=1.1)
        cv = float(uni["nn_rad"].std() / uni["nn_rad"].mean())
        assert cv < 0.03
        fov = fv.fly_vogel_lattice(radius=15, dphi_deg=1.1, density_power=0.65)
        cv2 = float(fov["nn_rad"].std() / fov["nn_rad"].mean())
        assert cv2 > 0.1
        inner = fov["rho_rad"] < 0.3 * fov["rho_rad"].max()
        assert fov["nn_rad"][inner].mean() < 0.8 * fov["nn_rad"][~inner].mean()

    def test_delaunay_mean_degree_is_about_six(self):
        from scipy.spatial import Delaunay
        v = fv.fly_vogel_lattice(radius=15, dphi_deg=1.1)
        a = v["dirs"][0]
        az0, el0 = float(np.arctan2(a[1], a[0])), float(np.arcsin(a[2]))
        b_az = np.array([-np.sin(az0), np.cos(az0), 0.0])
        b_el = np.array([-np.sin(el0) * np.cos(az0), -np.sin(el0) * np.sin(az0), np.cos(el0)])
        den = v["dirs"] @ a
        g = np.stack([(v["dirs"] @ b_az) / den, (v["dirs"] @ b_el) / den], axis=1)
        tri = Delaunay(g)
        deg = np.zeros(g.shape[0])
        for s in tri.simplices:
            for i, j in ((s[0], s[1]), (s[1], s[2]), (s[2], s[0])):
                deg[i] += 1
                deg[j] += 1
        deg /= 2.0
        assert abs(deg.mean() - 6.0) < 0.5

    def test_hexagonal_neighbour_ops_refuse_it(self):
        v = fv.fly_vogel_lattice(radius=4, dphi_deg=4.63)
        n = v["dirs"].shape[0]
        movie = np.abs(np.random.default_rng(0).standard_normal((10, n)))
        with pytest.raises(ValueError):
            fv.fly_t4t5_field(movie, v, 0.01)
        with pytest.raises(ValueError):
            fv.fly_flow_from_directions(np.zeros((6, n)), v)
        # the ops that need only directions take it
        tmpl = fv.fly_matched_filter(v, axis=(0.0, 0.0, 1.0))
        assert fv.fly_egomotion_from_flow(tmpl * 0.7, v, axes=[[0.0, 0.0, 1.0]])["yaw_rad_s"] == pytest.approx(0.7, abs=1e-9)

    def test_refusals(self):
        with pytest.raises(ValueError):
            fv.fly_vogel_lattice(radius=1)
        with pytest.raises(ValueError):
            fv.fly_vogel_lattice(density_power=0.0)
        with pytest.raises(ValueError):
            fv.fly_vogel_lattice(density_power=1.5)
        with pytest.raises(ValueError):
            fv.fly_vogel_lattice(angle_deg=720.0)


# --------------------------------------------------------------------------- #
# 6. the moire peak                                                            #
# --------------------------------------------------------------------------- #
class TestMoirePeak:
    def test_hexagon_peaks_and_the_vogel_eye_spreads(self):
        dphi, drho, P = 1.1, 1.0, 0.07
        floor = np.sqrt(3.0) * np.deg2rad(dphi)
        hexl = fv.fly_hex_lattice(radius=15, dphi_deg=dphi)
        vog = fv.fly_vogel_lattice(radius=15, dphi_deg=dphi)
        D = P / (1.1 * floor)                                     # just below Nyquist
        rh = fv.lattice_moire_peak(fv.fly_view_plane_texture(hexl, D, P, "sine", drho_deg=drho), hexl)
        rv = fv.lattice_moire_peak(fv.fly_view_plane_texture(vog, D, P, "sine", drho_deg=drho), vog)
        assert rh["peak_ratio"] > 100.0
        assert rv["peak_ratio"] < rh["peak_ratio"] / 10.0
        f_true = 1.0 / np.degrees(P / D)
        for r in (rh, rv):
            assert abs(abs(r["peak_cycles_per_deg"][0]) - f_true) < 2.0 * r["nyquist_cycles_per_deg"] / 47
            assert abs(r["peak_cycles_per_deg"][1]) < 2.0 * r["nyquist_cycles_per_deg"] / 47
        # above Nyquist the hexagon folds it to one sharp false stripe, the Vogel eye to a ring
        D2 = P / (0.8 * floor)
        rh2 = fv.lattice_moire_peak(fv.fly_view_plane_texture(hexl, D2, P, "sine", drho_deg=drho), hexl)
        rv2 = fv.lattice_moire_peak(fv.fly_view_plane_texture(vog, D2, P, "sine", drho_deg=drho), vog)
        assert rh2["peak_ratio"] > 100.0 and rv2["peak_ratio"] < 20.0

    def test_knobs_change_the_answer_and_a_flat_signal_is_refused(self):
        lat = fv.fly_hex_lattice(radius=6, dphi_deg=1.1)
        s = fv.fly_view_plane_texture(lat, 1.2, 0.07, "sine", drho_deg=1.0)
        a = fv.lattice_moire_peak(s, lat, n_freq=24)
        b = fv.lattice_moire_peak(s, lat, n_freq=24, window="none")
        c = fv.lattice_moire_peak(s, lat, n_freq=24, fmax_cycles_per_deg=0.2)
        assert a["peak_ratio"] != b["peak_ratio"] and a["n_freq"] == 24
        assert c["peak_ratio"] != a["peak_ratio"]
        with pytest.raises(ValueError):
            fv.lattice_moire_peak(np.full(lat["dirs"].shape[0], 0.5), lat)
        with pytest.raises(ValueError):
            fv.lattice_moire_peak(s[:0], lat)
        with pytest.raises(ValueError):
            fv.lattice_moire_peak(s, lat, n_freq=4)
        with pytest.raises(ValueError):
            fv.lattice_moire_peak(s, lat, window="hamming")


# --------------------------------------------------------------------------- #
# 7. ledger and public routes                                                  #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_the_six_ops_and_the_facade_reaches_them():
    import fullseye as fs

    assert opsflyvision.missing() == []
    for name in NEW_OPS:
        assert name in opsflyvision.OPSFLYVISION, name
        assert name in fv.__all__ and name in fv.FLYVISION, name
        assert hasattr(fs.ledger, name), name            # flyvision is reached through the ledger
    cats = {n: opsflyvision.info(n)["category"] for n in NEW_OPS}
    assert cats["sampling_alias_distance"] == cats["lattice_moire_peak"] == "alias"
    assert cats["traj_tau_dot"] == "trajectory"


def test_the_fuzzer_can_seed_every_op_that_has_required_arguments():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    rng = np.random.default_rng(0)
    for name in ("fly_view_plane_texture", "sampling_alias_distance", "fly_expansion_readout",
                 "traj_tau_dot", "lattice_moire_peak"):
        args, kwargs = cf.OP_ARG_BUILDERS[name]({}, rng)
        out = getattr(fv, name)(*args, **kwargs)
        assert out is not None
    assert isinstance(fv.fly_vogel_lattice(), dict)               # no required argument


def test_declared_out_types_are_what_the_ops_return():
    lat = fv.fly_hex_lattice(radius=3, dphi_deg=1.1)
    sig = opsflyvision.get("fly_view_plane_texture")(lat, 1.0, 0.07)
    assert isinstance(sig, np.ndarray) and sig.ndim == 1
    assert isinstance(opsflyvision.get("sampling_alias_distance")(0.07, 1.1), dict)
    assert isinstance(opsflyvision.get("fly_vogel_lattice")(radius=3), dict)
    assert isinstance(opsflyvision.get("lattice_moire_peak")(sig, lat, n_freq=8), dict)
