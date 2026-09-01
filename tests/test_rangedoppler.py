# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""rangedoppler — closed-form ground truth, sign conventions, and fail-closed.

Coherent ranging is one of the corners of sensing where the answer is known
analytically, so this suite is built around exact identities rather than golden
files. Four physical facts generate almost every assertion:

  * a target at range ``R`` beats at ``f_b = 2*S*R/c``, so it lands in range bin
    ``f_b*N_s/f_s``;
  * a target closing or opening at ``v`` advances the carrier phase by
    ``4*pi*v*T_c/lambda`` per chirp, so it lands in velocity bin
    ``2*v*T_c*N_c/lambda``;
  * a plane wave from ``theta`` advances by ``2*pi*d*sin(theta)/lambda`` per
    array element, so a matched steering vector sums coherently to ``N_a``;
  * each of those is a Fourier pair, so each has an aliasing limit that is a
    number, not an opinion.

Because those are Fourier identities, a target placed on a bin centre is
recovered **bit-exactly** — the peak magnitude is exactly ``a*N_s*N_c`` — and
this file asserts equality, not tolerance, wherever that is true. Where it is
not (an off-bin target, a windowed transform, a noisy cube) the tolerance is
derived in a comment, because a tolerance without a derivation is a wish.

Every scale in the physics is checked at **two settings** (two waveform slopes,
two chirp periods, two wavelengths, two array sizes), so a unit mix-up cannot
hide behind one lucky constant.

The sign conventions get their own class. Both of them — receding-is-positive
and the array phase direction — are invisible in a picture: mirror either one
and the map looks exactly as plausible. They are the reason this module exists
rather than three lines of ``np.fft.fft2`` at a call site.

``TestBugsFoundAdversarially`` pins the five defects the 2026-09-01 adversarial
pass found, each with its minimal reproduction. None of them raised an
exception at the time; every one returned a confident wrong number.
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import rangedoppler as RD  # noqa: E402
import opsrangedoppler  # noqa: E402

C = RD.SPEED_OF_LIGHT_M_S


def _cfg(**kw):
    """A waveform configuration and its design table, kept in lockstep."""
    base = dict(n_samples=64, n_chirps=32, n_antennas=1,
                sample_rate_hz=1.0e7, slope_hz_per_s=2.0e13,
                chirp_period_s=5.0e-5, wavelength_m=3.8934e-3)
    base.update(kw)
    return base, RD.fmcw_design(**base)


def _cube(cfg, ranges, velocities, **kw):
    return RD.fmcw_beat_simulate(ranges_m=ranges, velocities_ms=velocities,
                                 **cfg, **kw)


# --------------------------------------------------------------------------- #
# 1. design — the closed-form limits, cross-checked against the transform      #
# --------------------------------------------------------------------------- #
class TestDesign:
    def test_formulas_are_the_textbook_ones(self):
        cfg, d = _cfg()
        assert d["sweep_bandwidth_hz"] == pytest.approx(
            cfg["slope_hz_per_s"] * cfg["n_samples"] / cfg["sample_rate_hz"])
        # dR = c/2B, and the bin spacing equals the resolution for an
        # unwindowed transform — those are the same number, not two.
        assert d["range_bin_m"] == pytest.approx(C / (2.0 * d["sweep_bandwidth_hz"]))
        assert d["range_resolution_m"] == d["range_bin_m"]
        assert d["max_unambiguous_range_m"] == pytest.approx(
            d["range_bin_m"] * cfg["n_samples"])
        assert d["velocity_bin_ms"] == pytest.approx(
            cfg["wavelength_m"] / (2.0 * cfg["n_chirps"] * cfg["chirp_period_s"]))
        assert d["max_unambiguous_velocity_ms"] == pytest.approx(
            d["velocity_bin_ms"] * cfg["n_chirps"] / 2.0)
        assert d["doppler_rad_per_chirp_per_ms"] == pytest.approx(
            4.0 * np.pi * cfg["chirp_period_s"] / cfg["wavelength_m"])

    def test_design_predicts_the_measured_peak(self):
        """The design table is only worth anything if the transform obeys it."""
        cfg, d = _cfg()
        for rbin, vbin in ((3, 4), (17, -9), (1, 0)):
            cube = _cube(cfg, [rbin * d["range_bin_m"]],
                         [vbin * d["velocity_bin_ms"]])
            m = RD.range_doppler_map(cube)
            i, j = np.unravel_index(int(np.argmax(m)), m.shape)
            assert (int(j), int(i) - cfg["n_chirps"] // 2) == (rbin, vbin)

    def test_two_slopes_and_two_periods_scale_as_the_formula_says(self):
        """Doubling S halves the range span; doubling T_c halves the velocity
        span. A unit error would have to be scale-free to survive both."""
        _, a = _cfg()
        _, b = _cfg(slope_hz_per_s=4.0e13)
        assert b["max_unambiguous_range_m"] == pytest.approx(
            a["max_unambiguous_range_m"] / 2.0)
        _, c2 = _cfg(chirp_period_s=1.0e-4)
        assert c2["max_unambiguous_velocity_ms"] == pytest.approx(
            a["max_unambiguous_velocity_ms"] / 2.0)
        _, e = _cfg(wavelength_m=2.0 * 3.8934e-3)
        assert e["max_unambiguous_velocity_ms"] == pytest.approx(
            2.0 * a["max_unambiguous_velocity_ms"])
        assert e["max_unambiguous_range_m"] == a["max_unambiguous_range_m"]

    def test_angular_resolution_is_none_when_there_is_no_aperture(self):
        """A formula that still evaluates is not the same as an answer. With one
        element 0.886*lambda/(N*d) returns 101.5 degrees, and for 8 elements at
        1e-12 m it returns 2.5e10 degrees — neither is a resolution."""
        assert RD.fmcw_design(n_antennas=1)["angular_resolution_deg"] is None
        assert RD.fmcw_design(n_antennas=8, element_spacing_m=1e-12)[
            "angular_resolution_deg"] is None
        got = RD.fmcw_design(n_antennas=8)["angular_resolution_deg"]
        assert got == pytest.approx(np.degrees(0.886 * 2.0 / 8.0))

    def test_cube_size_is_reported_before_it_is_allocated(self):
        d = RD.fmcw_design(n_samples=4096, n_chirps=1024, n_antennas=64)
        assert d["cube_elements"] == 4096 * 1024 * 64
        assert d["within_cube_cap"] is False
        assert RD.fmcw_design()["within_cube_cap"] is True


# --------------------------------------------------------------------------- #
# 2. the exact identities                                                      #
# --------------------------------------------------------------------------- #
class TestClosedFormGroundTruth:
    def test_bin_centred_target_is_bit_exact(self):
        """No tolerance here on purpose. A complex exponential whose frequency is
        an exact DFT bin transforms to a single non-zero bin of magnitude N, and
        both transforms are exact bin frequencies by construction, so the peak is
        exactly ``a*N_s*N_c`` in IEEE double."""
        cfg, d = _cfg()
        cube = _cube(cfg, [3 * d["range_bin_m"]], [4 * d["velocity_bin_ms"]])
        m = RD.range_doppler_map(cube)
        assert m[4 + 16, 3] == float(cfg["n_samples"] * cfg["n_chirps"])
        assert RD.range_doppler_map(cube, normalize=True)[20, 3] == 1.0
        # everything else is float round-off, not signal
        off = m.copy()
        off[20, 3] = 0.0
        assert off.max() / m[20, 3] < 1e-15

    def test_beat_frequency_is_2SR_over_c(self):
        """The identity itself, read straight off the range profile: the peak bin
        index must equal ``f_b*N_s/f_s`` with ``f_b = 2SR/c``."""
        cfg, d = _cfg()
        for rbin in (1, 7, 31, 63):
            R = rbin * d["range_bin_m"]
            f_b = 2.0 * cfg["slope_hz_per_s"] * R / C
            expected = f_b * cfg["n_samples"] / cfg["sample_rate_hz"]
            assert expected == pytest.approx(rbin, abs=1e-9)
            prof = RD.fmcw_range_profile(_cube(cfg, [R], [0.0]), normalize=True)
            assert int(np.argmax(prof)) == rbin
            assert prof[rbin] == pytest.approx(1.0, abs=1e-12)

    def test_doppler_phase_advance_is_4pi_v_Tc_over_lambda(self):
        """Measured directly on the raw cube: the phase difference between two
        consecutive chirps at the target's range bin."""
        cfg, d = _cfg()
        v = 3 * d["velocity_bin_ms"]
        cube = _cube(cfg, [5 * d["range_bin_m"]], [v])
        rng_fft = np.fft.fft(cube[0], axis=1)[:, 5]        # (n_chirps,)
        dphi = np.angle(rng_fft[1] * np.conj(rng_fft[0]))
        predicted = 4.0 * np.pi * v * cfg["chirp_period_s"] / cfg["wavelength_m"]
        assert dphi == pytest.approx(
            np.angle(np.exp(1j * predicted)), abs=1e-12)

    def test_multiple_targets_each_land_on_their_own_bin(self):
        """Superposition is what makes a multi-target cube a valid ground truth:
        the transform is linear, so each target's peak is unaffected by the
        others as long as they occupy different bins."""
        cfg, d = _cfg()
        truth = [(5, -6, 1.0), (12, 3, 0.6), (40, 11, 0.3)]
        cube = _cube(cfg,
                     [b * d["range_bin_m"] for b, _, _ in truth],
                     [k * d["velocity_bin_ms"] for _, k, _ in truth],
                     amplitudes=[a for _, _, a in truth])
        got = RD.range_doppler_peaks(
            RD.range_doppler_map(cube, normalize=True),
            d["range_bin_m"], d["velocity_bin_ms"], n_peaks=3)
        assert got["n_found"] == 3
        by_bin = {(p["range_bin"], p["doppler_bin"]): p for p in got["peaks"]}
        for b, k, a in truth:
            p = by_bin[(b, k)]
            assert p["range_m"] == b * d["range_bin_m"]        # exact
            assert p["velocity_ms"] == k * d["velocity_bin_ms"]
            assert p["magnitude"] == pytest.approx(a, abs=1e-12)

    def test_two_configurations_give_the_same_physical_answer(self):
        """The same target, two different waveforms. Bin indices differ; metres
        and metres per second must not."""
        R, v = 20.0, 5.0
        out = []
        for kw in (dict(), dict(n_samples=128, slope_hz_per_s=1.0e13,
                         n_chirps=64, chirp_period_s=2.5e-5)):
            cfg, d = _cfg(**kw)
            # snap to this configuration's grid so the comparison is exact
            rb = round(R / d["range_bin_m"])
            vb = round(v / d["velocity_bin_ms"])
            cube = _cube(cfg, [rb * d["range_bin_m"]], [vb * d["velocity_bin_ms"]])
            p = RD.range_doppler_peaks(RD.range_doppler_map(cube),
                                       d["range_bin_m"], d["velocity_bin_ms"]
                                       )["peaks"][0]
            out.append((p["range_m"], p["velocity_ms"], p["range_bin"]))
        assert out[0][2] != out[1][2]                          # different bins
        assert abs(out[0][0] - out[1][0]) < 1.2                # < 1 coarse bin
        assert abs(out[0][1] - out[1][1]) < 1.3


# --------------------------------------------------------------------------- #
# 3. sign conventions — invisible in a picture, so pinned by test              #
# --------------------------------------------------------------------------- #
class TestSignConventions:
    def test_receding_is_positive_doppler(self):
        """``v = dR/dt``. Swapping this convention produces a map that is the
        exact mirror image of the right one, which is why no plot can catch it.
        Checked on the raw phase too, so it is the physics being pinned and not
        just an internal agreement between two of my own functions."""
        cfg, d = _cfg()
        zero = cfg["n_chirps"] // 2
        away = RD.range_doppler_map(_cube(cfg, [10 * d["range_bin_m"]],
                                          [+4 * d["velocity_bin_ms"]]))
        toward = RD.range_doppler_map(_cube(cfg, [10 * d["range_bin_m"]],
                                            [-4 * d["velocity_bin_ms"]]))
        i_away = int(np.unravel_index(int(np.argmax(away)), away.shape)[0])
        i_toward = int(np.unravel_index(int(np.argmax(toward)), toward.shape)[0])
        assert i_away - zero == +4 and i_toward - zero == -4
        # the two maps are mirror images of each other about zero velocity
        assert np.allclose(away, np.roll(toward[::-1, :], 1, axis=0))
        # and the reported velocity keeps the sign
        pk = RD.range_doppler_peaks(away, d["range_bin_m"], d["velocity_bin_ms"])
        assert pk["peaks"][0]["velocity_ms"] > 0.0

    def test_a_receding_target_moves_away_between_chirps(self):
        """Independent of the FFT entirely: with v > 0 the round-trip delay must
        grow, so the beat phase at a fixed range bin must advance."""
        cfg, d = _cfg()
        cube = _cube(cfg, [8 * d["range_bin_m"]], [+2 * d["velocity_bin_ms"]])
        f = np.fft.fft(cube[0], axis=1)[:, 8]
        adv = np.angle(f[1] * np.conj(f[0]))
        assert adv > 0.0

    def test_array_phase_direction(self):
        """A positive arrival angle must come back positive. Mirroring the
        steering convention would report -20 for +20 with no other symptom."""
        cfg, d = _cfg(n_antennas=8)
        for th in (-60.0, -20.0, 0.0, 20.0, 60.0):
            cube = _cube(cfg, [6 * d["range_bin_m"]], [0.0], angles_deg=[th])
            assert RD.beamform_doa(cube)["angles_deg"] == [th]

    def test_offset_free_grid_sweep(self):
        """33 arrival angles from -80 to +80, all on the grid: exact recovery."""
        cfg, d = _cfg(n_antennas=8)
        for th in range(-80, 81, 5):
            cube = _cube(cfg, [6 * d["range_bin_m"]], [0.0],
                         angles_deg=[float(th)])
            assert RD.beamform_doa(cube)["angles_deg"][0] == float(th)


# --------------------------------------------------------------------------- #
# 4. beamforming                                                               #
# --------------------------------------------------------------------------- #
class TestBeamforming:
    def test_matched_steering_gives_the_full_aperture_gain(self):
        """``N_a`` in amplitude, ``N_a^2`` in power — exactly, for a target on
        the grid, because the steering vector is then the exact conjugate."""
        for na in (2, 4, 8, 16):
            cfg, d = _cfg(n_antennas=na)
            cube = _cube(cfg, [6 * d["range_bin_m"]], [0.0], angles_deg=[0.0])
            p = RD.beamform_delay_sum(cube)
            assert p.max() == float(na * cfg["n_chirps"] * cfg["n_samples"]) ** 2
            assert RD.beamform_delay_sum(cube, normalize=True).max() == 1.0

    def test_two_targets_in_one_cell_resolve_when_further_than_a_beamwidth(self):
        cfg, d = _cfg(n_antennas=8)
        r, v = 6 * d["range_bin_m"], 3 * d["velocity_bin_ms"]
        cube = _cube(cfg, [r, r], [v, v], angles_deg=[-30.0, 30.0])
        doa = RD.beamform_doa(cube, n_targets=2)
        assert sorted(doa["angles_deg"]) == [-30.0, 30.0]
        assert 60.0 > doa["angular_resolution_deg"] > 0.0

    def test_two_targets_inside_one_beamwidth_merge_and_are_not_faked(self):
        """The honest failure: delay-and-sum cannot separate them, so it must
        report one lobe rather than two invented directions."""
        cfg, d = _cfg(n_antennas=8)
        r = 6 * d["range_bin_m"]
        cube = _cube(cfg, [r, r], [0.0, 0.0], angles_deg=[-2.0, 2.0])
        doa = RD.beamform_doa(cube, n_targets=2)
        assert doa["n_found"] == 1
        assert abs(doa["angles_deg"][0]) <= 2.0

    def test_a_detection_can_be_handed_straight_back_in(self):
        """range_doppler_peaks reports a signed doppler_bin; beamform_doa takes
        the same convention, so the (R, v) -> angle handoff needs no arithmetic
        at the call site. If the two conventions drifted apart, this would
        beamform the wrong cell and return the other target's angle."""
        cfg, d = _cfg(n_antennas=8)
        cube = _cube(cfg, [3 * d["range_bin_m"], 20 * d["range_bin_m"]],
                     [4 * d["velocity_bin_ms"], -2 * d["velocity_bin_ms"]],
                     angles_deg=[10.0, -40.0], amplitudes=[1.0, 0.4])
        m = RD.range_doppler_map(cube, normalize=True)
        want = {(3, 4): 10.0, (20, -2): -40.0}
        found = {}
        for p in RD.range_doppler_peaks(m, d["range_bin_m"],
                                        d["velocity_bin_ms"], n_peaks=2)["peaks"]:
            doa = RD.beamform_doa(cube, range_bin=p["range_bin"],
                                  doppler_bin=p["doppler_bin"],
                                  range_bin_m=d["range_bin_m"],
                                  velocity_bin_ms=d["velocity_bin_ms"])
            found[(p["range_bin"], p["doppler_bin"])] = doa["angles_deg"][0]
            assert doa["range_m"] == p["range_m"]
            assert doa["velocity_ms"] == p["velocity_ms"]
        assert found == want


# --------------------------------------------------------------------------- #
# 5. windows and sidelobes                                                     #
# --------------------------------------------------------------------------- #
class TestWindows:
    #: Peak sidelobe level, dB, measured by transforming each window alone with
    #: 2^18-point zero padding — which is the definition (Harris 1978). The
    #: published figures are -13.3 / -31.5 / -42.7 / -58.1; Hamming differs by
    #: 0.25 dB because the published number is for the optimal 0.53836/0.46164
    #: pair, not the textbook 0.54/0.46 used here.
    PSL_DB = {"rect": -13.25, "hann": -31.47, "hamming": -42.45,
              "blackman": -58.11}
    #: -3 dB main-lobe width in bins, measured the same way.
    LOBE_BINS = {"rect": 0.885, "hann": 1.438, "hamming": 1.301,
                 "blackman": 1.641}

    def _psl_and_lobe(self, name, n=64, pad=1 << 18):
        w = RD._window_1d(name, n)
        s = np.abs(np.fft.fft(w, pad))
        s = s / s.max()
        k = 1
        while s[k + 1] < s[k]:                      # walk down to the first null
            k += 1
        psl = 20.0 * np.log10(s[k:pad // 2].max())
        half = int(np.flatnonzero(s[:pad // 2] < 10 ** (-3.0 / 20.0))[0])
        return psl, 2.0 * half * n / pad

    def test_measured_sidelobe_table(self):
        for name in RD.WINDOWS:
            psl, lobe = self._psl_and_lobe(name)
            assert psl == pytest.approx(self.PSL_DB[name], abs=0.01)
            assert lobe == pytest.approx(self.LOBE_BINS[name], abs=0.002)

    def test_sidelobes_fall_and_main_lobes_widen_monotonically(self):
        """The trade is the whole point of the op: every step down in sidelobe
        level costs main-lobe width. Ordered by sidelobe level, the widths must
        be ordered too (Hamming is the documented exception — it buys 11 dB over
        Hann while being *narrower*, which is why it exists)."""
        order = ["rect", "hann", "blackman"]
        psl = [self._psl_and_lobe(w)[0] for w in order]
        lobe = [self._psl_and_lobe(w)[1] for w in order]
        assert psl[0] > psl[1] > psl[2]
        assert lobe[0] < lobe[1] < lobe[2]

    def test_windows_are_periodic_not_symmetric(self):
        """``np.hanning`` returns the symmetric window, whose sidelobes do not
        match the published table. The difference is one sample and it is the
        difference between -31.5 dB and something else."""
        w = RD._window_1d("hann", 64)
        assert w[0] == 0.0
        assert not np.allclose(w, np.hanning(64))
        assert np.allclose(w, np.hanning(65)[:-1])

    def test_a_window_rescues_a_target_the_leakage_buries(self):
        """The end-to-end reason to have the op. A weak target 45 dB down and 10
        bins away from a half-bin-offset strong one is not even a local maximum
        without a window; with Hann it is a clean peak near its true level."""
        cfg, d = _cfg()
        weak = 10.0 ** (-45.0 / 20.0)
        cube = _cube(cfg, [10.5 * d["range_bin_m"], 20.0 * d["range_bin_m"]],
                     [0.0, 0.0], amplitudes=[1.0, weak])
        bare = RD.fmcw_range_profile(cube, normalize=True)
        won = RD.fmcw_range_profile(RD.fmcw_window_apply(cube, "hann"),
                                    normalize=True)
        assert not (bare[20] > bare[19] and bare[20] > bare[21])   # buried
        assert won[20] > won[19] and won[20] > won[21]             # recovered
        assert 20.0 * np.log10(bare[20] / bare.max()) > -30.0      # leakage
        assert 20.0 * np.log10(won[20] / won.max()) < -40.0        # near truth

    def test_rect_scalloping_loss_is_two_over_pi(self):
        """A half-bin-offset target loses exactly ``2/pi`` (-3.92 dB) of its
        peak with no window — the classic closed-form scalloping loss, and a
        direct check that ``rect`` really is the identity window."""
        cfg, d = _cfg()
        cube = _cube(cfg, [10.5 * d["range_bin_m"]], [0.0])
        p = RD.fmcw_range_profile(cube, normalize=True)
        assert p.max() == pytest.approx(2.0 / np.pi, abs=1e-4)
        assert np.array_equal(RD.fmcw_window_apply(cube, "rect"), cube)

    def test_window_axis_is_selected_by_role(self):
        cfg, d = _cfg()
        cube = _cube(cfg, [5 * d["range_bin_m"]], [3 * d["velocity_bin_ms"]])
        r = RD.fmcw_window_apply(cube, "hann", "range")
        v = RD.fmcw_window_apply(cube, "hann", "doppler")
        b = RD.fmcw_window_apply(cube, "hann", "both")
        assert not np.allclose(r, v)
        assert np.allclose(b, RD.fmcw_window_apply(r, "hann", "doppler"))
        # a window never moves the peak, it only reshapes it
        for c in (r, v, b):
            m = RD.range_doppler_map(c)
            assert np.unravel_index(int(np.argmax(m)), m.shape) == (19, 5)


# --------------------------------------------------------------------------- #
# 6. aliasing — the plausible-wrong answers, refused                           #
# --------------------------------------------------------------------------- #
class TestAliasingIsRefused:
    def test_range_past_the_unambiguous_limit(self):
        cfg, d = _cfg()
        r_max = d["max_unambiguous_range_m"]
        _cube(cfg, [r_max * 0.999], [0.0])                    # just inside: fine
        for bad in (r_max, r_max * 1.001, r_max * 3.0):
            with pytest.raises(ValueError, match="unambiguous range"):
                _cube(cfg, [bad], [0.0])

    def test_the_folded_answer_it_refuses_to_give(self):
        """Why it matters: at ``R_max + dR`` the beat frequency exceeds the
        sample rate and the target reappears at *one bin*, i.e. as a target 74 m
        closer. Constructed by hand here — the op will not produce it."""
        cfg, d = _cfg()
        folded = d["max_unambiguous_range_m"] + d["range_bin_m"]
        f_b = 2.0 * cfg["slope_hz_per_s"] * folded / C
        alias_bin = (f_b * cfg["n_samples"] / cfg["sample_rate_hz"]) % cfg["n_samples"]
        assert alias_bin == pytest.approx(1.0, abs=1e-6)      # 76 m looks like 1 m
        with pytest.raises(ValueError):
            _cube(cfg, [folded], [0.0])

    def test_velocity_past_the_unambiguous_limit(self):
        cfg, d = _cfg()
        v_max = d["max_unambiguous_velocity_ms"]
        _cube(cfg, [10.0], [v_max * 0.999])
        _cube(cfg, [10.0], [-v_max * 0.999])
        for bad in (v_max, -v_max, v_max * 1.5):
            with pytest.raises(ValueError, match="unambiguous velocity"):
                _cube(cfg, [10.0], [bad])

    def test_the_wrong_sign_it_refuses_to_give(self):
        """Past ``v_max`` the Doppler phase exceeds pi per chirp and the target
        comes back with the **opposite sign**: a car opening at 21 m/s would be
        reported as closing at 18. That is the worst kind of wrong."""
        cfg, d = _cfg()
        v = d["max_unambiguous_velocity_ms"] + 2.0 * d["velocity_bin_ms"]
        f_d = 2.0 * v / cfg["wavelength_m"]
        bin_ = (f_d * cfg["chirp_period_s"] * cfg["n_chirps"]) % cfg["n_chirps"]
        signed = bin_ - cfg["n_chirps"] if bin_ >= cfg["n_chirps"] / 2 else bin_
        assert signed < 0.0                                   # receding -> closing
        with pytest.raises(ValueError):
            _cube(cfg, [10.0], [v])

    def test_a_speed_in_km_per_hour_is_caught_by_the_velocity_limit(self):
        """The only mechanical guard against a km/h -> m/s mix-up, and it is a
        bound rather than a proof: 72 (km/h, meaning 20 m/s) exceeds v_max and
        raises, but 30 (km/h, meaning 8.3 m/s) is inside the window and cannot
        be distinguished from a genuine 30 m/s. Documented, not papered over."""
        cfg, d = _cfg()
        with pytest.raises(ValueError, match="km/h"):
            _cube(cfg, [10.0], [72.0])
        _cube(cfg, [10.0], [10.0])           # 36 km/h read as m/s: undetectable

    def test_angle_past_the_grating_lobe_limit(self):
        cfg, _ = _cfg(n_antennas=8, element_spacing_m=2.0 * 3.8934e-3)
        with pytest.raises(ValueError, match="grating lobe"):
            _cube(cfg, [10.0], [0.0], angles_deg=[40.0])
        _cube(cfg, [10.0], [0.0], angles_deg=[5.0])           # inside: fine


# --------------------------------------------------------------------------- #
# 7. fail-closed contract                                                      #
# --------------------------------------------------------------------------- #
class TestFailClosed:
    def _c(self, **kw):
        cfg, d = _cfg(**kw)
        return _cube(cfg, [6 * d["range_bin_m"]], [0.0])

    def test_a_real_cube_is_refused_because_the_sign_is_absent_not_noisy(self):
        cube = self._c()
        with pytest.raises(ValueError, match="real-valued"):
            RD.range_doppler_map(cube.real)
        with pytest.raises(ValueError, match="real-valued"):
            RD.fmcw_range_profile(np.abs(cube))
        # the reason, demonstrated: a real beat spectrum is conjugate symmetric,
        # so +v and -v are literally the same bin
        cfg, d = _cfg()
        up = _cube(cfg, [6 * d["range_bin_m"]], [+3 * d["velocity_bin_ms"]]).real
        dn = _cube(cfg, [6 * d["range_bin_m"]], [-3 * d["velocity_bin_ms"]]).real
        assert np.allclose(np.abs(np.fft.fft2(up[0])),
                           np.abs(np.fft.fft2(dn[0])))

    def test_a_voxel_volume_is_not_a_beat_cube(self):
        """The histcube/voxel lesson: both are 3-D float arrays. Here the dtype
        check catches it, which is the *only* reason the axis confusion cannot
        produce a plausible-wrong map."""
        with pytest.raises(ValueError, match="real-valued"):
            RD.range_doppler_map(np.random.default_rng(0).random((8, 8, 8)))

    @pytest.mark.parametrize("kw,match", [
        (dict(slope_hz_per_s=0.0), "slope_hz_per_s"),
        (dict(sample_rate_hz=-1.0), "sample_rate_hz"),
        (dict(chirp_period_s=0.0), "chirp_period_s"),
        (dict(n_samples=1), "n_samples"),
        (dict(n_chirps=1), "n_chirps"),
        (dict(n_antennas=0), "n_antennas"),
        (dict(wavelength_m=77e9), "wavelength_m"),
        (dict(sample_rate_hz="1e7"), "string"),
        (dict(n_samples=64.0), "must be an int"),
        (dict(seed=1.0), "non-negative int"),
    ])
    def test_degenerate_and_mistyped_waveform_parameters(self, kw, match):
        with pytest.raises(ValueError, match=match):
            RD.fmcw_beat_simulate([10.0], [0.0], **kw)

    @pytest.mark.parametrize("targets,match", [
        ((["10.0"], [0.0]), "strings"),
        (([True], [0.0]), "boolean"),
        (([10.0 + 1j], [0.0]), "complex"),
        (([np.nan], [0.0]), "non-finite"),
        (([np.inf], [0.0]), "non-finite"),
        (([0.0], [0.0]), "non-positive"),
        (([-5.0], [0.0]), "non-positive"),
        (([], []), "at least 1"),
        (([10.0, 20.0], [0.0]), "one velocity per target"),
    ])
    def test_target_lists(self, targets, match):
        with pytest.raises(ValueError, match=match):
            RD.fmcw_beat_simulate(*targets)

    def test_a_string_that_float_would_have_accepted(self):
        """``float("77")`` succeeds; that is the whole trap. The dtype of the
        *raw* input is inspected before any cast."""
        assert float("77") == 77.0
        with pytest.raises(ValueError, match="strings"):
            RD.fmcw_beat_simulate(["77"], [0.0])

    def test_size_cap_bites_before_the_complex128_promotion(self):
        """A complex64 array is half the width of the working dtype, so a cap
        applied after coercion would already have doubled the allocation. The
        check reads the declared shape and never touches the data — asserted by
        passing an array that could not be materialised at complex128."""
        big = np.empty((64, 1024, 4096), dtype=np.complex64)   # 2 GiB at c128
        with pytest.raises(ValueError, match="over the"):
            RD.range_doppler_map(big)
        with pytest.raises(ValueError, match="over the"):
            RD.fmcw_beat_simulate([10.0], [0.0], n_samples=4096, n_chirps=1024,
                                  n_antennas=64)

    def test_no_silent_nan_from_an_overflowing_transform(self):
        """A finite cube can transform to Inf and then NaN. numpy only warns."""
        cfg, d = _cfg()
        cube = _cube(cfg, [3 * d["range_bin_m"]], [0.0], amplitudes=[1e307])
        assert np.isfinite(cube).all()
        with pytest.raises(ValueError, match="overflow"):
            RD.range_doppler_map(cube)
        with pytest.raises(ValueError, match="overflow"):
            RD.fmcw_range_profile(cube)

    def test_nothing_to_detect_is_refused_not_reported_as_a_target(self):
        with pytest.raises(ValueError, match="nothing to detect"):
            RD.range_doppler_peaks(np.zeros((8, 8)))
        with pytest.raises(ValueError, match="negative"):
            RD.range_doppler_peaks(-np.ones((8, 8)))
        with pytest.raises(ValueError, match="complex"):
            RD.range_doppler_peaks(np.ones((8, 8), dtype=complex))
        with pytest.raises(ValueError, match="no cell to beamform"):
            RD.beamform_delay_sum(np.zeros((4, 8, 8), dtype=complex))
        # a flat map has no strict local maximum: an empty list, not a guess
        assert RD.range_doppler_peaks(np.ones((8, 8)))["n_found"] == 0

    def test_masked_and_malformed_arrays(self):
        cube = self._c(n_antennas=4)
        with pytest.raises(ValueError, match="masked"):
            RD.range_doppler_map(np.ma.masked_greater(cube.real + 0j, 0.5))
        with pytest.raises(ValueError, match="3-D beat cube"):
            RD.range_doppler_map(cube[0])
        with pytest.raises(ValueError, match="non-finite"):
            RD.range_doppler_map(np.full((2, 4, 4), np.nan + 0j))

    def test_mode_and_flag_arguments(self):
        cube = self._c(n_antennas=4)
        with pytest.raises(ValueError, match="window must be one of"):
            RD.fmcw_window_apply(cube, "kaiser")
        with pytest.raises(ValueError, match="axis must be one of"):
            RD.fmcw_window_apply(cube, "hann", "fast")
        with pytest.raises(ValueError, match="combine must be one of"):
            RD.range_doppler_map(cube, combine="beamformed")
        with pytest.raises(ValueError, match="must be a bool"):
            RD.range_doppler_map(cube, normalize=1)
        with pytest.raises(ValueError, match="antenna must be in"):
            RD.range_doppler_map(cube, antenna=99)
        with pytest.raises(ValueError, match="strictly increasing"):
            RD.beamform_doa(cube, angles_deg=[0.0, 25.0, -40.0])
        with pytest.raises(ValueError, match=r"\[-90, 90\]"):
            RD.beamform_doa(cube, angles_deg=[-100.0, 0.0, 100.0])

    def test_single_pixel_and_single_element_degeneracies(self):
        """Legitimate degeneracies must work (one antenna is a real sensor);
        impossible ones must raise."""
        cfg, d = _cfg(n_antennas=1)
        cube = _cube(cfg, [4 * d["range_bin_m"]], [2 * d["velocity_bin_ms"]])
        assert RD.range_doppler_map(cube).shape == (32, 64)     # fine
        assert RD.fmcw_range_profile(cube).shape == (64,)       # fine
        with pytest.raises(ValueError, match="antenna element"):
            RD.beamform_delay_sum(cube)                         # no aperture
        with pytest.raises(ValueError, match="antenna element"):
            RD.beamform_doa(cube)

    def test_static_scene_only(self):
        """All targets at v = 0 is a perfectly normal scene, not an error."""
        cfg, d = _cfg()
        cube = _cube(cfg, [3 * d["range_bin_m"], 9 * d["range_bin_m"]],
                     [0.0, 0.0])
        pk = RD.range_doppler_peaks(RD.range_doppler_map(cube),
                                    d["range_bin_m"], d["velocity_bin_ms"],
                                    n_peaks=2)
        assert {p["doppler_bin"] for p in pk["peaks"]} == {0}
        assert {p["range_bin"] for p in pk["peaks"]} == {3, 9}


# --------------------------------------------------------------------------- #
# 8. the bugs the adversarial pass found                                       #
# --------------------------------------------------------------------------- #
class TestBugsFoundAdversarially:
    """Five defects found on 2026-09-01. **None of them raised**; every one
    returned a confident wrong number, which is the failure mode this repository
    treats as the dangerous one."""

    def test_angle_outside_the_hemisphere_was_folded_by_sin(self):
        """``fmcw_beat_simulate(angles_deg=[95.0])`` produced a cube **bit
        identical** to ``angles_deg=[85.0]`` (max |diff| 0.0) and beamformed back
        as 85 degrees; 190 came back as -10. sin() folds the rear hemisphere onto
        the front one and there is no rear hemisphere for a linear array."""
        for bad in (95.0, 91.0, 190.0, -120.0):
            with pytest.raises(ValueError, match=r"outside \[-90, 90\]"):
                RD.fmcw_beat_simulate([10.0], [0.0], angles_deg=[bad],
                                      n_antennas=8)
        # the fold itself, still true of sin() — which is why the check is needed
        assert np.sin(np.radians(95.0)) == pytest.approx(np.sin(np.radians(85.0)))

    def test_a_sub_wavelength_array_reported_minus_ninety_degrees(self):
        """8 elements at 1e-12 m: the angle spectrum's peak-to-trough spread was
        exactly 0.0 and ``beamform_doa`` returned ``[-90.0]`` — the first grid
        point — while ``fmcw_design`` reported an angular resolution of 2.5e10
        degrees without comment."""
        cfg, d = _cfg(n_antennas=8, element_spacing_m=1e-12)
        cube = _cube(cfg, [6 * d["range_bin_m"]], [0.0])
        with pytest.raises(ValueError, match="no directivity"):
            RD.beamform_doa(cube, element_spacing_m=1e-12)
        with pytest.raises(ValueError, match="no directivity"):
            RD.beamform_delay_sum(cube, element_spacing_m=1e-12)
        assert d["angular_resolution_deg"] is None
        assert d["aperture_wavelengths"] < 1e-8

    def test_half_a_cell_address_was_silently_ignored(self):
        """With two targets, ``beamform_doa(cube, range_bin=20)`` returned the
        angle of the target in range bin 3 (the strongest cell) **and reported
        ``range_bin: 3``**. The caller asked about one target and was answered
        about another."""
        cfg, d = _cfg(n_antennas=8)
        cube = _cube(cfg, [3 * d["range_bin_m"], 20 * d["range_bin_m"]],
                     [4 * d["velocity_bin_ms"], -2 * d["velocity_bin_ms"]],
                     angles_deg=[10.0, -40.0], amplitudes=[1.0, 0.4])
        for kw in (dict(range_bin=20), dict(doppler_bin=-2)):
            with pytest.raises(ValueError, match="give both"):
                RD.beamform_doa(cube, **kw)
            with pytest.raises(ValueError, match="give both"):
                RD.beamform_delay_sum(cube, **kw)
        got = RD.beamform_doa(cube, range_bin=20, doppler_bin=-2)
        assert got["angles_deg"] == [-40.0] and got["range_bin"] == 20

    def test_a_target_in_the_last_range_bin_was_dropped(self):
        """The strongest cell in the map returned **zero** detections: the peak
        picker masked out the first and last range columns instead of comparing
        each edge cell against the neighbours it actually has."""
        cfg, d = _cfg()
        last = cfg["n_samples"] - 1
        cube = _cube(cfg, [last * d["range_bin_m"]], [0.0])
        m = RD.range_doppler_map(cube, normalize=True)
        assert np.unravel_index(int(np.argmax(m)), m.shape)[1] == last
        got = RD.range_doppler_peaks(m, d["range_bin_m"], d["velocity_bin_ms"])
        assert got["n_found"] == 1
        assert got["peaks"][0]["range_bin"] == last
        # and the first bin too, which the same mask also removed
        first = RD.range_doppler_peaks(
            RD.range_doppler_map(_cube(cfg, [1.0 * d["range_bin_m"]], [0.0])),
            d["range_bin_m"], d["velocity_bin_ms"])
        assert first["peaks"][0]["range_bin"] == 1

    def test_an_overflowing_fft_returned_a_map_full_of_nan(self):
        """``amplitudes=[1e307]`` gives a cube that passes every finiteness
        check; ``range_doppler_map`` then returned a map whose maximum was
        ``nan``, with only a numpy RuntimeWarning to say so."""
        cfg, d = _cfg()
        cube = _cube(cfg, [3 * d["range_bin_m"]], [0.0], amplitudes=[1e307])
        assert np.isfinite(cube).all()
        assert not np.isfinite(np.fft.fft(cube, axis=2)).all()   # the raw hazard
        with pytest.raises(ValueError, match="overflowed"):
            RD.range_doppler_map(cube)


# --------------------------------------------------------------------------- #
# 9. noise, determinism, and the ledger                                        #
# --------------------------------------------------------------------------- #
class TestNoiseAndDeterminism:
    def test_same_seed_same_cube(self):
        cfg, d = _cfg()
        kw = dict(noise_sigma=0.2, seed=7)
        a = _cube(cfg, [6 * d["range_bin_m"]], [0.0], **kw)
        b = _cube(cfg, [6 * d["range_bin_m"]], [0.0], **kw)
        assert np.array_equal(a, b)
        c = _cube(cfg, [6 * d["range_bin_m"]], [0.0], noise_sigma=0.2, seed=8)
        assert not np.array_equal(a, c)
        assert np.array_equal(_cube(cfg, [6 * d["range_bin_m"]], [0.0]),
                              _cube(cfg, [6 * d["range_bin_m"]], [0.0],
                                    noise_sigma=0.0, seed=999))

    def test_processing_gain_is_the_number_of_samples(self):
        """Coherent integration over ``N_c*N_s`` samples raises the signal by
        that factor in amplitude while noise grows as its square root, so the
        peak-to-median ratio must scale like ``sqrt(N_c*N_s)``. Checked as an
        order-of-magnitude identity (a factor-2 band around the prediction over
        20 seeds), because the median of a Rayleigh field is itself random."""
        cfg, d = _cfg()
        sigma = 0.5
        ratios = []
        for s in range(20):
            cube = _cube(cfg, [6 * d["range_bin_m"]], [3 * d["velocity_bin_ms"]],
                         noise_sigma=sigma, seed=s)
            m = RD.range_doppler_map(cube, normalize=True)
            ratios.append(m.max() / np.median(m))
        got = float(np.median(ratios))
        # signal 1.0 vs a noise floor ~ sigma*sqrt(2/(N_c*N_s)) after normalising
        predicted = 1.0 / (sigma * np.sqrt(2.0 / (cfg["n_chirps"] * cfg["n_samples"])))
        assert predicted / 2.0 < got < predicted * 2.0

    def test_noise_does_not_move_a_strong_peak(self):
        cfg, d = _cfg()
        for s in range(10):
            cube = _cube(cfg, [11 * d["range_bin_m"]], [-5 * d["velocity_bin_ms"]],
                         noise_sigma=0.05, seed=s)
            p = RD.range_doppler_peaks(RD.range_doppler_map(cube),
                                       d["range_bin_m"], d["velocity_bin_ms"]
                                       )["peaks"][0]
            assert (p["range_bin"], p["doppler_bin"]) == (11, -5)


class TestLedger:
    def test_every_declared_op_exists(self):
        assert opsrangedoppler.missing() == []
        assert len(opsrangedoppler.OPSRANGEDOPPLER) == len(RD.RANGEDOPPLER)
        assert set(opsrangedoppler.list_ops()) == set(RD.RANGEDOPPLER)
        assert set(RD.RANGEDOPPLER) == set(RD.__all__) & set(RD.RANGEDOPPLER)

    def test_declared_output_types_match_what_the_ops_return(self):
        """The same check the chain fuzzer's TYPEMISS pass makes, run here so a
        ledger drift fails in CI rather than in a fuzz report."""
        checks = {
            "table": lambda v: isinstance(v, (list, dict)),
            "image2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
            "signal": lambda v: isinstance(v, np.ndarray) and v.ndim == 1,
            "beatcube": lambda v: (isinstance(v, np.ndarray) and v.ndim == 3
                                   and v.dtype.kind == "c" and v.shape[1] >= 2
                                   and v.shape[2] >= 2),
        }
        cfg, d = _cfg(n_antennas=4)
        cube = _cube(cfg, [6 * d["range_bin_m"]], [2 * d["velocity_bin_ms"]],
                     angles_deg=[15.0])
        rdmap = RD.range_doppler_map(cube)
        args = {
            "fmcw_design": (), "fmcw_beat_simulate": (),
            "fmcw_window_apply": (cube,), "range_doppler_map": (cube,),
            "range_doppler_peaks": (rdmap,), "fmcw_range_profile": (cube,),
            "beamform_delay_sum": (cube,), "beamform_doa": (cube,),
        }
        for name in opsrangedoppler.list_ops():
            out = opsrangedoppler.info(name)["out"]
            got = opsrangedoppler.call(name, *args[name])
            assert checks[out](got), "%s declared %r, returned %r" % (
                name, out, type(got).__name__)

    def test_result_adapters_are_empty_because_returns_are_already_typed(self):
        assert opsrangedoppler.RESULT_ADAPTERS == {}

    def test_the_beatcube_type_is_disjoint_from_the_dtof_histcube_type(self):
        """The measured reason the two ranging families do not share a type.

        Raw, both directions already fail closed on dtype. But **one explicit
        cast defeats that**, and then both directions return a confident wrong
        answer — which is why the separation has to be at the declared-type
        level, exactly as histcube was separated from voxel."""
        import photoncount as PC
        cfg, d = _cfg(n_antennas=4)
        beat = _cube(cfg, [6 * d["range_bin_m"]], [2 * d["velocity_bin_ms"]])
        hist = PC.dtof_cube_simulate(
            0.5 + 0.8 * np.random.default_rng(0).random((4, 32)),
            bins=64, bin_ps=200.0, signal_photons=60.0, ambient_photons=10.0,
            seed=1)
        assert beat.shape == hist.shape                   # same shape, both 3-D
        assert beat.dtype.kind == "c" and hist.dtype.kind == "f"
        with pytest.raises(ValueError, match="complex"):
            PC.dtof_cube_depth(beat, 200.0)
        with pytest.raises(ValueError, match="real-valued"):
            RD.range_doppler_map(hist)
        # one cast each way, and both produce a plausible-wrong result silently
        depth = PC.dtof_cube_depth(np.abs(beat), 200.0)
        assert depth.shape == (4, 32) and np.isfinite(depth).all()
        faked = RD.range_doppler_map(hist.astype(complex))
        assert faked.shape == (32, 64) and faked.max() > 0.0
