# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""interferometry — closed-form ground truth, the phase-shifting comparison, and fail-closed.

Coherence-scanning interferometry is one of the corners of imaging where the
answer is known analytically, so this suite is built on exact identities rather
than golden files:

  * a synthesised scan of a surface at ``z0`` has its coherence envelope peak
    **at** ``z0``, so the estimators can be scored against the truth directly;
  * the log of a sampled Gaussian is exactly a parabola, so the ``"gaussian"``
    estimator is exact on the analytic envelope (measured 2.9e-14 um) and limited
    only by the Hilbert envelope on real data;
  * the source coherence length ``(4 ln2/pi) lambda^2/delta_lambda`` is checked
    against a direct numerical Fourier transform of the Gaussian source spectrum,
    at three settings, so the factor-of-two between OPD and scan axis is pinned
    numerically rather than asserted;
  * the fringe modulation of the forward model is exactly
    ``amplitude * reflectivity``, so :func:`csi_contrast_map` has an exact target;
  * the chromatic-confocal wavelength-to-height map is linear and its inversion
    is exact.

The centrepiece is ``test_phase_shifting_breaks_coherence_holds``. It drives the
**existing** :mod:`fringe` phase-shifting pipeline and the **new** coherence
pipeline from the same synthetic step, at the same wavelength, and shows the
crossover: below lambda/4 both are exact; above it, phase shifting is wrong by
exact multiples of lambda/2 and says nothing about it, while coherence scanning
stays exact. Adding a module because a diagram says the old one has a limitation
is not evidence; making the old one produce the wrong number on demand is.

Every randomised check fixes the seed and states its sample size. Scale
invariance is checked at two wavelengths and two step sizes so a unit mix-up
cannot hide behind one lucky constant.

The classes at the end pin the bugs the 2026-09-01 adversarial pass found, each
with the minimal reproduction that exposed it.
"""
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import dsp                                                    # noqa: E402
import fringe                                                 # noqa: E402
import interferometry as itf                                  # noqa: E402
import opsinterferometry                                      # noqa: E402

LAM = 0.60          # um, reference wavelength for the whole suite
SIGMA = 1.2         # um, reference envelope sigma (FWHM 2.8258 um)
FWHM = SIGMA * itf.FWHM_PER_SIGMA
DZ = 0.05           # um, reference scan step (below lambda/4 = 0.15)
NP = 241            # planes -> a 12.0 um scan


def scan(z0, noise=0.0, seed=0, n=NP, start=0.0, step=DZ, sigma=SIGMA,
         lam=LAM, refl=1.0):
    """A reference z scan of a surface at *z0*."""
    return itf.csi_signal_simulate(z0, start, step, n, lam,
                                   envelope_fwhm_um=None,
                                   envelope_sigma_um=sigma,
                                   reflectivity=refl, noise=noise, seed=seed)


def analytic_envelope(z0, n=NP, start=0.0, step=DZ, sigma=SIGMA, amp=0.4):
    z = start + step * np.arange(n)
    return amp * np.exp(-0.5 * ((z - z0) / sigma) ** 2)


# --------------------------------------------------------------------------- #
# 1. the forward model and the envelope                                        #
# --------------------------------------------------------------------------- #
class TestForwardModel:
    def test_signal_matches_the_written_model(self):
        """The docstring's formula is the code, checked term by term."""
        z0 = 6.025
        s = scan(z0)
        z = DZ * np.arange(NP)
        want = 0.5 + 0.4 * np.exp(-0.5 * ((z - z0) / SIGMA) ** 2) * np.cos(
            4.0 * np.pi * (z - z0) / LAM)
        assert np.allclose(s, want, atol=0, rtol=0)

    def test_fringe_period_is_half_the_wavelength(self):
        """The double pass: one fringe is lambda/2 of *height*, not lambda."""
        s = scan(6.0, sigma=40.0)                     # near-flat envelope
        # zero crossings of the AC part: consecutive ones are half a period apart
        ac = s - s.mean()
        cross = np.flatnonzero(np.sign(ac[:-1]) != np.sign(ac[1:]))
        period = 2.0 * np.mean(np.diff(cross)) * DZ
        assert abs(period - LAM / 2.0) < 2e-3

    def test_envelope_needs_the_pedestal_removed(self):
        """dsp.envelope on a raw interferogram returns the pedestal, not the envelope."""
        z0 = 6.025
        s = scan(z0)
        truth = analytic_envelope(z0)
        err_on = np.abs(itf.csi_envelope(s, remove_bias=True) - truth).max()
        err_off = np.abs(itf.csi_envelope(s, remove_bias=False) - truth).max()
        err_dsp = np.abs(dsp.envelope(s) - truth).max()
        assert err_on < 1e-6, err_on                  # measured 1.83e-07
        assert err_off > 0.4                          # measured 0.5 = the pedestal
        assert abs(err_dsp - err_off) < 1e-12         # ... and dsp.envelope is that case

    def test_csi_envelope_delegates_to_dsp(self):
        """The 1-D path *is* dsp.envelope, so the two cannot drift apart."""
        s = scan(6.0)
        assert np.array_equal(itf.csi_envelope(s, remove_bias=True),
                              dsp.envelope(s - s.mean()))

    def test_reflectivity_scales_but_does_not_shift(self):
        """A per-pixel reflectance changes the contrast, never the height."""
        z0 = 6.025
        base = itf.csi_peak_position(scan(z0), DZ, 0.0, LAM)
        for r in (0.05, 0.5, 3.0):
            got = itf.csi_peak_position(scan(z0, refl=r), DZ, 0.0, LAM)
            assert abs(got - base) < 1e-12
            assert np.allclose(itf.csi_envelope(scan(z0, refl=r)),
                               r * itf.csi_envelope(scan(z0)))


# --------------------------------------------------------------------------- #
# 2. the estimators, and their measured biases                                 #
# --------------------------------------------------------------------------- #
class TestEstimators:
    def test_gaussian_fit_is_exact_on_an_analytic_envelope(self):
        """The log of a sampled Gaussian is exactly a parabola. Nothing else is
        being tested here — the Hilbert transform is taken out of the loop."""
        for frac in (0.0, 0.25, 0.5, 0.75):
            z0 = 6.0 + frac * DZ
            env = analytic_envelope(z0)
            k = int(np.argmax(env))
            off = float(itf._refine(env, np.asarray(k), "gaussian"))
            assert abs(DZ * (k + off) - z0) < 1e-13

    def test_estimator_bias_table(self):
        """The table in the module docstring, recomputed. Noiseless."""
        want = {"peak": 2.50e-02, "centroid": 4.55e-07,
                "parabolic": 4.21e-06, "gaussian": 1.43e-07}
        got = {}
        for mode in itf.ESTIMATORS:
            errs = [itf.csi_peak_position(scan(6.0 + f * DZ), DZ, 0.0, LAM,
                                          mode=mode) - (6.0 + f * DZ)
                    for f in (0.0, 0.25, 0.5, 0.75)]
            got[mode] = max(abs(e) for e in errs)
        for mode, ref in want.items():
            assert got[mode] <= ref * 1.5, (mode, got[mode], ref)
        assert got["peak"] == pytest.approx(DZ / 2.0, abs=1e-12)
        assert got["gaussian"] < got["parabolic"] / 10.0

    def test_noise_inverts_the_estimator_ranking(self):
        """Under noise the centroid wins and the local fits lose — the opposite
        of the noiseless order. 200 trials at sigma_n = 0.01, seeds 0..199."""
        rms = {}
        for mode in itf.ESTIMATORS:
            errs = [itf.csi_peak_position(scan(6.0 + (t % 13) * DZ / 13.0,
                                               noise=0.01, seed=t),
                                          DZ, 0.0, LAM, mode=mode)
                    - (6.0 + (t % 13) * DZ / 13.0) for t in range(200)]
            # the edge guard never fires here: the surface is centred, and the
            # baseline-referenced edge level reads 0.0000 even at 5 % noise
            rms[mode] = float(np.sqrt(np.mean(np.square(errs))))
        assert rms["centroid"] < 0.03                      # measured 0.0219
        assert rms["parabolic"] > 0.10                     # measured 0.1403
        assert rms["parabolic"] / rms["centroid"] > 4.0    # measured 6.4x
        # ... while noiseless the ranking is the other way round
        assert rms["gaussian"] > rms["centroid"]

    def test_centroid_window_bias(self):
        """The centroid's own failure: it is pulled toward the middle of the scan."""
        # the surfaces at 2 and 10 um sit where the edge guard fires (that is a
        # separate, correct refusal); lift it so the *centroid's* bias is what is
        # being measured here rather than the guard
        clean = {z0: itf.csi_peak_position(scan(z0), DZ, 0.0, LAM,
                                           mode="centroid",
                                           max_edge_envelope=1.0) - z0
                 for z0 in (2.0, 6.0, 10.0)}
        assert clean[2.0] > 0.15 and clean[10.0] < -0.15   # measured +-0.189
        assert abs(clean[6.0]) < 1e-4                      # centred: unbiased
        noisy = {z0: itf.csi_peak_position(scan(z0, noise=0.02, seed=1), DZ, 0.0,
                                           LAM, mode="centroid",
                                           max_edge_envelope=1.0) - z0
                 for z0 in (2.0, 10.0)}
        assert noisy[2.0] > 0.5 and noisy[10.0] < -0.5     # measured +0.87/-0.85
        # the local estimators do not have this bias at all
        for z0 in (2.0, 10.0):
            assert abs(itf.csi_peak_position(scan(z0), DZ, 0.0, LAM,
                                             mode="gaussian",
                                             max_edge_envelope=1.0) - z0) < 0.05

    def test_accuracy_is_a_property_of_the_scan_layout(self):
        """Centre the surface and the estimator is exact; push it to the end of
        the scan and the same estimator loses six decades — to envelope
        truncation, not to the fit."""
        centred = itf.csi_peak_position(scan(6.0, start=0.0), DZ, 0.0, LAM)
        assert abs(centred - 6.0) < 1e-12                    # measured 3e-14
        near = itf.csi_peak_position(scan(2.0), DZ, 0.0, LAM,
                                     max_edge_envelope=1.0)  # guard off
        assert 1e-3 < abs(near - 2.0) < 0.1                  # measured 2.67e-02


# --------------------------------------------------------------------------- #
# 3. the stack                                                                 #
# --------------------------------------------------------------------------- #
def tilted(lo=5.0, hi=7.0, n=32):
    return lo + (hi - lo) * np.mgrid[0:n, 0:n][1] / (n - 1.0)


def stack_of(height, **kw):
    kw.setdefault("envelope_sigma_um", SIGMA)
    return itf.csi_stack_simulate(height, 0.0, DZ, NP, LAM,
                                  envelope_fwhm_um=None, **kw)


class TestStack:
    def test_height_map_ground_truth(self):
        h = tilted()
        st = stack_of(h)
        assert st.shape == (NP, 32, 32)
        want = {"peak": 1.42e-02, "centroid": 3.81e-05,
                "parabolic": 4.02e-06, "gaussian": 2.08e-06}
        for mode, ref in want.items():
            hm = itf.csi_height_map(st, DZ, 0.0, LAM, mode=mode)
            rms = float(np.sqrt(np.mean((hm - h) ** 2)))
            assert rms <= ref * 1.5, (mode, rms, ref)

    def test_stack_agrees_with_the_1d_operator_bit_for_bit(self):
        """The vectorised path is the same computation, not a lookalike."""
        h = tilted(5.0, 7.0, 8)
        st = stack_of(h)
        hm = itf.csi_height_map(st, DZ, 0.0, LAM)
        for r in range(0, 8, 3):
            for c in range(0, 8, 3):
                one = itf.csi_peak_position(st[:, r, c], DZ, 0.0, LAM)
                assert hm[r, c] == pytest.approx(one, abs=1e-12)

    def test_truncation_costs_three_decades(self):
        """Same estimator, same pixels, wider surface -> far worse. The number to
        look at when a real measurement disappoints."""
        inner = float(np.sqrt(np.mean(
            (itf.csi_height_map(stack_of(tilted(5.0, 7.0)), DZ, 0.0, LAM)
             - tilted(5.0, 7.0)) ** 2)))
        outer = float(np.sqrt(np.mean(
            (itf.csi_height_map(stack_of(tilted(2.0, 10.0)), DZ, 0.0, LAM,
                                max_edge_envelope=1.0)
             - tilted(2.0, 10.0)) ** 2)))
        assert inner < 1e-5 and outer > 1e-3
        assert outer / inner > 100.0                       # measured ~3400x

    def test_contrast_map_recovers_reflectivity(self):
        h = tilted()
        refl = 0.3 + 0.6 * np.mgrid[0:32, 0:32][0] / 31.0
        st = stack_of(h, reflectivity=refl)
        cm = itf.csi_contrast_map(st)
        assert np.abs(cm - 0.4 * refl).max() < 2e-4        # measured 7.32e-05
        # ... and the height is untouched by the varying reflectance
        hm = itf.csi_height_map(st, DZ, 0.0, LAM)
        assert float(np.sqrt(np.mean((hm - h) ** 2))) < 5e-6

    def test_scan_axis_is_first_and_what_that_check_can_actually_see(self):
        """Honest scope. A 3-D array with fewer than 3 leading planes is named
        exactly (the transposed-stack case); a 3-D array with the axes swapped
        but enough of them is **not detectable from the array alone**, which is
        the whole reason the ledger declares a separate ``zscan`` type instead of
        relying on a runtime check."""
        st = stack_of(tilted(5.0, 7.0, 8))
        with pytest.raises(ValueError, match="scan axis last, transpose it"):
            itf.csi_height_map(np.moveaxis(st, 0, -1)[:2], DZ)
        with pytest.raises(ValueError, match="3-D"):
            itf.csi_height_map(st[0], DZ)
        # the undetectable case: (H, W, Z) with H >= 3 passes every structural
        # test and is rejected only by the *content* checks, which is luck, not
        # a contract
        swapped = np.moveaxis(st, 0, -1)
        assert swapped.shape == (8, 8, NP)
        with pytest.raises(ValueError, match="no usable coherence peak"):
            itf.csi_height_map(swapped, DZ, 0.0, LAM)


# --------------------------------------------------------------------------- #
# 4. THE comparison: phase shifting breaks, coherence scanning holds           #
# --------------------------------------------------------------------------- #
class TestAgainstPhaseShifting:
    """The one place the old family and the new one are driven from one surface."""

    @staticmethod
    def _phase_shift_step(h_um, lam=LAM, shape=(16, 32)):
        """The existing fringe pipeline, run as an interferometer: the height to
        phase gain of a double pass is 4*pi/lambda."""
        gain = 4.0 * np.pi / lam
        rows, cols = shape
        height = np.zeros(shape)
        height[:, cols // 2:] = h_um
        imgs = fringe.synthesize_fringes(height, n_steps=4, freq=0.0,
                                         phase_gain=gain, bias=0.5,
                                         amplitude=0.4)
        rec = fringe.decode_fringe(imgs, k=1.0 / gain)
        return float(rec[:, cols // 2:].mean() - rec[:, :cols // 2].mean())

    @staticmethod
    def _coherence_step(h_um, lam=LAM, shape=(16, 32)):
        rows, cols = shape
        height = np.full(shape, 5.0)
        height[:, cols // 2:] = 5.0 + h_um
        st = itf.csi_stack_simulate(height, 0.0, DZ, NP, lam,
                                    envelope_fwhm_um=None,
                                    envelope_sigma_um=SIGMA)
        hm = itf.csi_height_map(st, DZ, 0.0, lam)
        return float(hm[:, cols // 2:].mean() - hm[:, :cols // 2].mean())

    def test_both_agree_below_a_quarter_wavelength(self):
        for h in (0.05, 0.10, 0.15):                   # lambda/4 = 0.15
            assert self._phase_shift_step(h) == pytest.approx(h, abs=1e-6)
            assert self._coherence_step(h) == pytest.approx(h, abs=1e-4)

    def test_phase_shifting_breaks_coherence_holds(self):
        """Above lambda/4 the phase method returns a *plausible wrong number* and
        the coherence method stays exact. The errors are exact fringe orders."""
        for h in (0.20, 0.30, 0.50, 1.00):
            psi = self._phase_shift_step(h)
            csi = self._coherence_step(h)
            # coherence scanning: still exact
            assert csi == pytest.approx(h, abs=1e-4), (h, csi)
            # phase shifting: wrong, and wrong by a whole number of lambda/2
            err = psi - h
            assert abs(err) > 0.29, (h, psi)
            orders = err / (LAM / 2.0)
            assert abs(orders - round(orders)) < 1e-6, (h, err, orders)
            # ... and it did not raise, did not return NaN, did not warn
            assert np.isfinite(psi)
            assert abs(psi) <= LAM / 4.0 + 1e-9        # folded into one fringe

    def test_the_crossover_is_exactly_a_quarter_wavelength(self):
        ok = [h for h in np.arange(0.05, 0.40, 0.01)
              if abs(self._phase_shift_step(h) - h) < 1e-6]
        assert max(ok) == pytest.approx(0.15, abs=0.011)     # lambda/4
        # at a different wavelength the crossover moves with it
        ok2 = [h for h in np.arange(0.05, 0.40, 0.01)
               if abs(self._phase_shift_step(h, lam=0.8) - h) < 1e-6]
        assert max(ok2) == pytest.approx(0.20, abs=0.011)    # 0.8/4


# --------------------------------------------------------------------------- #
# 5. chromatic confocal                                                        #
# --------------------------------------------------------------------------- #
class TestChromaticConfocal:
    def test_height_is_exact(self):
        for z in (-15.0, -3.7, 0.0, 4.25, 18.0):
            sp = itf.chromatic_confocal_simulate(z, 500.0, 0.5, 401, 0.20, 600.0,
                                                 peak_fwhm_nm=4.0)
            got = itf.chromatic_confocal_height(sp, 500.0, 0.5, 0.20, 600.0)
            assert got == pytest.approx(z, abs=1e-12), (z, got)

    def test_exact_even_when_undersampled_or_near_the_band_edge(self):
        """No Hilbert transform here, so the truncation failure that limits the
        coherence side does not exist on this one — a peak two bins from the edge
        and a peak narrower than one bin are both inverted exactly."""
        for fw in (0.4, 1.0, 8.0):
            sp = itf.chromatic_confocal_simulate(3.0, 500.0, 1.0, 301, 0.20,
                                                 600.0, peak_fwhm_nm=fw)
            got = itf.chromatic_confocal_height(sp, 500.0, 1.0, 0.20, 600.0,
                                                min_peak_bins=0.0)
            assert got == pytest.approx(3.0, abs=1e-11), (fw, got)
        sp = itf.chromatic_confocal_simulate(19.8, 500.0, 0.5, 401, 0.20, 600.0,
                                             peak_fwhm_nm=4.0)
        assert itf.chromatic_confocal_height(sp, 500.0, 0.5, 0.20,
                                             600.0) == pytest.approx(19.8, abs=1e-9)

    def test_dispersion_and_reference_are_linear_and_signed(self):
        sp = itf.chromatic_confocal_simulate(4.0, 500.0, 0.5, 401, 0.20, 600.0)
        # doubling the dispersion doubles the height read from the same spectrum
        a = itf.chromatic_confocal_height(sp, 500.0, 0.5, 0.20, 600.0)
        b = itf.chromatic_confocal_height(sp, 500.0, 0.5, 0.40, 600.0)
        assert b == pytest.approx(2.0 * a, rel=1e-12)
        # moving the reference wavelength shifts the height by exactly disp*delta
        c = itf.chromatic_confocal_height(sp, 500.0, 0.5, 0.20, 610.0)
        assert c == pytest.approx(a - 10.0 * 0.20, abs=1e-9)

    def test_undersampled_peak_is_refused(self):
        sp = itf.chromatic_confocal_simulate(3.0, 500.0, 1.0, 301, 0.20, 600.0,
                                             peak_fwhm_nm=0.5)
        with pytest.raises(ValueError, match="undersampled"):
            itf.chromatic_confocal_height(sp, 500.0, 1.0, 0.20, 600.0)

    def test_noise_rejection_peaks_at_two_bins(self):
        """"More samples is better" is false here, and the operator says so.
        100 trials per width, seeds 0..99, 1 % noise."""
        rms = {}
        for fw in (0.5, 2.0, 8.0):
            errs = []
            for t in range(100):
                zt = 0.13 * (t % 17) - 1.0
                sp = itf.chromatic_confocal_simulate(
                    zt, 500.0, 1.0, 301, 0.20, 600.0, peak_fwhm_nm=fw,
                    peak_counts=1000.0, background=10.0, noise=10.0, seed=t)
                errs.append(itf.chromatic_confocal_height(
                    sp, 500.0, 1.0, 0.20, 600.0, min_peak_bins=0.0) - zt)
            rms[fw] = float(np.sqrt(np.mean(np.square(errs))))
        assert rms[2.0] < rms[0.5] / 10.0                # measured 25x
        assert rms[2.0] < rms[8.0] / 5.0                 # broad peaks are bad too


# --------------------------------------------------------------------------- #
# 6. design                                                                    #
# --------------------------------------------------------------------------- #
class TestDesign:
    def test_coherence_length_against_a_numerical_fourier_transform(self):
        """The factor of two between OPD and scan axis, pinned numerically."""
        for lam0, dlam in ((0.60, 0.10), (0.60, 0.05), (0.85, 0.04)):
            d = itf.csi_design(lam0, dlam, z_range_um=1.0, width_px=1,
                               height_px=1)
            sk = (dlam / lam0 ** 2) / itf.FWHM_PER_SIGMA
            k0 = 1.0 / lam0
            k = np.linspace(k0 - 6 * sk, k0 + 6 * sk, 40001)
            spec = np.exp(-0.5 * ((k - k0) / sk) ** 2)
            x = np.linspace(0.0, 6.0 * d["coherence_length_um"], 4001)
            g = np.array([abs(np.trapezoid(spec * np.exp(2j * np.pi * k * xi), k))
                          for xi in x])
            g /= g.max()
            half = float(np.interp(0.5, g[::-1], x[::-1]))
            assert 2.0 * half == pytest.approx(d["coherence_length_um"], rel=1e-5)
            assert d["envelope_fwhm_um"] == pytest.approx(
                0.5 * d["coherence_length_um"], rel=1e-15)

    def test_envelope_fwhm_is_what_the_simulator_takes(self):
        """The design output feeds the forward model without a unit conversion,
        and the resulting envelope really has that width."""
        d = itf.csi_design(LAM, 0.06, z_range_um=12.0, width_px=1, height_px=1)
        s = itf.csi_signal_simulate(6.0, 0.0, DZ, NP, LAM,
                                    envelope_fwhm_um=d["envelope_fwhm_um"])
        env = itf.csi_envelope(s)
        z = DZ * np.arange(NP)
        above = z[env >= 0.5 * env.max()]
        assert (above[-1] - above[0]) == pytest.approx(d["envelope_fwhm_um"],
                                                       rel=0.02)

    def test_nyquist_and_fringe_period(self):
        d = itf.csi_design(LAM, 0.1)
        assert d["fringe_period_um"] == pytest.approx(LAM / 2)
        assert d["max_z_step_um"] == pytest.approx(LAM / 4)
        assert d["phase_unambiguous_step_um"] == pytest.approx(LAM / 4)
        assert d["recommended_z_step_um"] < d["max_z_step_um"]
        assert d["stack_within_cap"] is False               # 640x480x161

    def test_capture_range_matches_the_measured_envelope(self):
        """capture_range_um says where the contrast falls below min_visibility;
        the forward model is asked whether that is true."""
        d = itf.csi_design(LAM, 0.06, min_visibility=0.30, width_px=1,
                           height_px=1)
        sigma = d["envelope_sigma_um"]
        half = 0.5 * d["capture_range_um"]
        assert np.exp(-0.5 * (half / sigma) ** 2) == pytest.approx(0.30, rel=1e-9)


# --------------------------------------------------------------------------- #
# 7. fail-closed contract                                                      #
# --------------------------------------------------------------------------- #
class TestFailClosed:
    def test_step_past_nyquist_is_refused_not_folded(self):
        for step in (0.15, 0.16, 0.20, 0.30):               # lambda/4 = 0.15
            with pytest.raises(ValueError, match="Nyquist"):
                itf.csi_peak_position(scan(6.0), step, 0.0, LAM)
            with pytest.raises(ValueError, match="Nyquist"):
                itf.csi_signal_simulate(6.0, 0.0, step, NP, LAM,
                                        envelope_sigma_um=SIGMA,
                                        envelope_fwhm_um=None)
        # ... and it scales with the wavelength rather than being a constant
        itf.csi_peak_position(scan(6.0, lam=0.8), 0.16, 0.0, 0.8)

    def test_undersampling_really_does_lie(self):
        """The justification for the refusal above, measured: past Nyquist the
        answer is *intermittently* wrong, so being lucky is indistinguishable
        from being right."""
        errs = {}
        for step in (0.16, 0.20):
            n = int(12.0 / step)
            z = step * np.arange(n)
            z0 = 6.037
            s = 0.5 + 0.4 * np.exp(-0.5 * ((z - z0) / SIGMA) ** 2) * np.cos(
                4 * np.pi * (z - z0) / LAM)
            env = itf.csi_envelope(s)
            k = int(np.argmax(env))
            off = float(itf._refine(env, np.asarray(k), "gaussian"))
            errs[step] = step * (k + off) - z0
        assert abs(errs[0.16]) > 0.10                       # measured 0.107
        assert abs(errs[0.20]) < 1e-6                       # ... and this one is fine

    def test_surface_outside_the_scan_is_refused(self):
        with pytest.raises(ValueError, match="outside the scan range"):
            itf.csi_signal_simulate(20.0, 0.0, DZ, NP, LAM,
                                    envelope_sigma_um=SIGMA, envelope_fwhm_um=None)
        with pytest.raises(ValueError, match="outside the scan range"):
            itf.csi_stack_simulate(np.full((4, 4), 20.0), 0.0, DZ, NP, LAM,
                                   envelope_sigma_um=SIGMA, envelope_fwhm_um=None)

    def test_peak_on_the_first_or_last_plane_is_refused(self):
        # A surface *outside* the scan; the forward model refuses to synthesise
        # it (that check is tested elsewhere), so the signal is built by hand —
        # which is also what a real instrument would hand you.
        z = DZ * np.arange(NP)
        for z0 in (-3.0, 15.0):
            s = 0.5 + 0.4 * np.exp(-0.5 * ((z - z0) / SIGMA) ** 2) * np.cos(
                4.0 * np.pi * (z - z0) / LAM)
            with pytest.raises(ValueError, match="first or last plane"):
                itf.csi_peak_position(s, DZ, 0.0, LAM, max_edge_envelope=1.0)
        # Honest scope: at a surface exactly *on* the boundary plane the Hilbert
        # envelope peaks one plane inside (measured argmax 1 of 241 for z0 = 0),
        # so this check alone does not catch it — max_edge_envelope does, and
        # that is why both exist.
        s = scan(0.0, n=NP)
        assert int(np.argmax(itf.csi_envelope(s))) == 1
        with pytest.raises(ValueError, match="max_edge_envelope"):
            itf.csi_peak_position(s, DZ, 0.0, LAM)

    def test_truncated_envelope_is_refused_because_it_lies(self):
        """The nastiest one: an *interior* argmax, no NaN, no warning, 76 % wrong."""
        s = scan(0.5)
        with pytest.raises(ValueError, match="max_edge_envelope"):
            itf.csi_peak_position(s, DZ, 0.0, LAM)
        got = itf.csi_peak_position(s, DZ, 0.0, LAM, max_edge_envelope=1.0)
        assert np.isfinite(got) and 0.0 < got < 0.2         # measured 0.1189
        assert abs(got - 0.5) > 0.3                         # ... and it is wrong

    def test_flat_and_constant_signals_are_refused(self):
        with pytest.raises(ValueError, match="prominence"):
            itf.csi_peak_position(np.full(64, 3.0), DZ, 0.0, LAM)
        rng = np.random.default_rng(0)
        carrier = np.sin(np.linspace(0, 8 * np.pi, 256)) + 0.1 * rng.standard_normal(256)
        with pytest.raises(ValueError, match="prominence"):
            itf.csi_peak_position(carrier, DZ, 0.0, LAM)

    def test_degenerate_scalars(self):
        s = scan(6.0)
        with pytest.raises(ValueError, match="z_step_um must be > 0"):
            itf.csi_peak_position(s, 0.0, 0.0, LAM)
        with pytest.raises(ValueError, match="z_step_um must be > 0"):
            itf.csi_peak_position(s, -DZ, 0.0, LAM)
        with pytest.raises(ValueError, match="wavelength_um must be > 0"):
            itf.csi_peak_position(s, DZ, 0.0, 0.0)
        with pytest.raises(ValueError, match="envelope_sigma_um must be > 0"):
            itf.csi_signal_simulate(6.0, 0.0, DZ, NP, LAM, envelope_fwhm_um=None,
                                    envelope_sigma_um=0.0)
        with pytest.raises(ValueError, match="either envelope_fwhm_um"):
            itf.csi_signal_simulate(6.0, 0.0, DZ, NP, LAM, envelope_fwhm_um=None)
        with pytest.raises(ValueError, match="not both"):
            itf.csi_signal_simulate(6.0, 0.0, DZ, NP, LAM, envelope_fwhm_um=2.8,
                                    envelope_sigma_um=1.2)

    @pytest.mark.parametrize("bad", ["0.55", b"0.55", True, 1 + 2j,
                                     np.complex128(1 + 2j), np.True_])
    def test_strings_bools_and_complex_are_refused_not_coerced(self, bad):
        """float('0.55') succeeds, so an unparsed config string must be caught
        by type, not by value."""
        with pytest.raises(ValueError):
            itf.csi_peak_position(scan(6.0), bad, 0.0, LAM)
        with pytest.raises(ValueError):
            itf.csi_design(bad, 0.1)

    def test_non_finite_arrays_are_refused(self):
        s = scan(6.0)
        for bad in (np.nan, np.inf, -np.inf):
            poisoned = s.copy()
            poisoned[100] = bad
            with pytest.raises(ValueError, match="non-finite"):
                itf.csi_envelope(poisoned)
        with pytest.raises(ValueError, match="complex"):
            itf.csi_envelope(s.astype(np.complex128))
        with pytest.raises(ValueError, match="masked"):
            itf.csi_envelope(np.ma.array(s, mask=(np.arange(s.size) == 3)))

    def test_no_output_is_ever_silently_non_finite(self):
        h = tilted()
        st = stack_of(h)
        for mode in itf.ESTIMATORS:
            assert np.isfinite(itf.csi_height_map(st, DZ, 0.0, LAM, mode=mode)).all()
        assert np.isfinite(itf.csi_contrast_map(st)).all()
        assert all(np.isfinite(v) for v in itf.csi_design().values()
                   if isinstance(v, float))

    def test_nan_fill_is_opt_in_only(self):
        h = tilted(0.2, 11.8)                          # both ends bad
        st = stack_of(h)
        with pytest.raises(ValueError, match="no usable coherence peak"):
            itf.csi_height_map(st, DZ, 0.0, LAM)
        filled = itf.csi_height_map(st, DZ, 0.0, LAM, on_invalid="fill")
        assert np.isnan(filled).any()
        assert not np.isnan(itf.csi_height_map(stack_of(tilted()), DZ, 0.0,
                                               LAM)).any()
        with pytest.raises(ValueError, match="on_invalid"):
            itf.csi_height_map(st, DZ, 0.0, LAM, on_invalid="clamp")

    def test_size_caps_fire_before_the_float64_promotion(self):
        """A small uint8 input must not become a large float64 one on the way to
        being rejected. The cap is read off the shape, so a zero-strided view
        (0 bytes on disk, 2^25 logical elements) is refused without allocating."""
        huge = np.broadcast_to(np.uint8(1), (1 << 13, 1 << 12))   # 32 M elements
        assert huge.base.nbytes <= 8                              # nothing is stored
        with pytest.raises(ValueError, match="before"):
            itf.csi_envelope(np.broadcast_to(np.uint8(1), (1 << 21,)))
        with pytest.raises(ValueError, match="over the"):
            itf.csi_stack_simulate(huge, 0.0, DZ, NP, LAM, envelope_sigma_um=SIGMA,
                                   envelope_fwhm_um=None)
        with pytest.raises(ValueError, match="over the"):
            itf.csi_stack_simulate(np.full((256, 256), 6.0), 0.0, DZ, NP, LAM,
                                   envelope_sigma_um=SIGMA, envelope_fwhm_um=None)

    def test_chromatic_fail_closed(self):
        sp = itf.chromatic_confocal_simulate(3.0, 500.0, 0.5, 401, 0.20, 600.0)
        with pytest.raises(ValueError, match="negative"):
            itf.chromatic_confocal_height(-sp, 500.0, 0.5, 0.20, 600.0)
        with pytest.raises(ValueError, match="prominence"):
            itf.chromatic_confocal_height(np.full(64, 5.0), 500.0, 0.5, 0.20, 600.0)
        with pytest.raises(ValueError, match="outside the spectrometer band"):
            itf.chromatic_confocal_simulate(40.0, 500.0, 0.5, 401, 0.20, 600.0)
        with pytest.raises(ValueError, match="first or last bin"):
            edge = np.zeros(64)
            edge[0] = 10.0
            edge[1] = 1.0
            itf.chromatic_confocal_height(edge, 500.0, 0.5, 0.20, 600.0,
                                          min_peak_bins=0.0)

    def test_design_fail_closed(self):
        with pytest.raises(ValueError, match="not below wavelength_um"):
            itf.csi_design(0.6, 0.6)
        with pytest.raises(ValueError, match="min_visibility"):
            itf.csi_design(0.6, 0.1, min_visibility=0.0)
        with pytest.raises(ValueError, match="step_divisor"):
            itf.csi_design(0.6, 0.1, step_divisor=3.0)
        with pytest.raises(ValueError, match="must be an int"):
            itf.csi_design(0.6, 0.1, width_px=640.5)

    def test_determinism(self):
        for _ in range(3):
            assert np.array_equal(scan(6.0, noise=0.01, seed=5),
                                  scan(6.0, noise=0.01, seed=5))
        with pytest.raises(ValueError, match="non-negative int"):
            itf.csi_signal_simulate(6.0, 0.0, DZ, NP, LAM, envelope_sigma_um=SIGMA,
                                    envelope_fwhm_um=None, noise=0.01, seed=None)


# --------------------------------------------------------------------------- #
# 8. the type vocabulary, measured rather than asserted                        #
# --------------------------------------------------------------------------- #
class TestTypeVocabulary:
    def test_ledger_is_complete_and_consistent(self):
        assert opsinterferometry.missing() == []
        names = set(opsinterferometry.list_ops())
        assert names == set(itf.INTERFEROMETRY)
        assert names == {n for n in itf.__all__ if n in names}
        for name in names:
            meta = opsinterferometry.info(name)
            assert meta["doc"]
            assert meta["out"] in ("signal", "zscan", "depth", "image2d",
                                   "measurement", "table")

    def test_declared_output_types_are_what_the_ops_actually_return(self):
        """No RESULT_ADAPTERS, so this is the strictest possible check."""
        h = tilted()
        st = stack_of(h)
        s = scan(6.0)
        got = {
            "csi_signal_simulate": s,
            "csi_stack_simulate": st,
            "chromatic_confocal_simulate":
                itf.chromatic_confocal_simulate(3.0, 500.0, 0.5, 401, 0.20, 600.0),
            "csi_envelope": itf.csi_envelope(s),
            "csi_peak_position": itf.csi_peak_position(s, DZ, 0.0, LAM),
            "csi_height_map": itf.csi_height_map(st, DZ, 0.0, LAM),
            "csi_contrast_map": itf.csi_contrast_map(st),
            "chromatic_confocal_height": itf.chromatic_confocal_height(
                itf.chromatic_confocal_simulate(3.0, 500.0, 0.5, 401, 0.20, 600.0),
                500.0, 0.5, 0.20, 600.0),
            "csi_design": itf.csi_design(),
        }
        check = {
            "signal": lambda v: isinstance(v, np.ndarray) and v.ndim == 1,
            "zscan": lambda v: (isinstance(v, np.ndarray) and v.ndim == 3
                                and v.dtype.kind == "f" and v.shape[0] >= 3),
            "depth": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
            "image2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
            "measurement": lambda v: isinstance(v, (int, float, np.floating,
                                                    np.integer)),
            "table": lambda v: isinstance(v, (list, dict)),
        }
        assert opsinterferometry.RESULT_ADAPTERS == {}
        for name, value in got.items():
            declared = opsinterferometry.info(name)["out"]
            assert check[declared](value), (name, declared, type(value))

    def test_zscan_must_not_share_the_video_pool(self):
        """Measured, not assumed. A scan stack handed to the motion-magnification
        family produces results with no exception and no NaN — it reads distance
        as time — which is why the ledger declares a separate ``zscan``."""
        import motionmag
        h = 1.4 + 0.4 * np.mgrid[0:32, 0:32][1] / 31.0
        z = itf.csi_stack_simulate(h, 0.0, 0.045, 64, LAM, envelope_fwhm_um=0.9)
        out = motionmag.motion_magnify(z, alpha=2.0, f_lo=3.0, f_hi=5.0, fps=32.0)
        assert np.isfinite(out["video"]).all()             # silently plausible
        assert np.isfinite(out["phase_shift_rms_rad"])
        power = motionmag.temporal_band_power(z, f_lo=3.0, f_hi=5.0, fps=32.0)
        assert np.isfinite(power).all()

    def test_zscan_must_not_share_the_histcube_pool(self):
        """The other direction of the same argument: photoncount reads axis 2 as
        time and returns a depth map in metres from a stack of interferograms."""
        import photoncount
        h = tilted(1.2, 1.8, 16)
        st = itf.csi_stack_simulate(h, 0.0, DZ, 64, LAM, envelope_sigma_um=0.3,
                                    envelope_fwhm_um=None)
        d = photoncount.dtof_cube_depth(st)
        assert np.isfinite(d).all() and (d > 0).any()      # plausible, meaningless

    def test_a_video_handed_to_the_csi_family_is_refused(self):
        """The reverse direction is safe, and this is why the ``signal`` and
        ``depth`` pools could be shared while ``zscan`` could not: here the
        fail-closed checks really do fire, on every seed tried."""
        import motionmag
        for seed in range(4):
            v = motionmag.synthesize_translation(
                (32, 32), 32, amplitude_px=0.1 + 0.1 * seed, frequency_hz=4.0,
                fps=32.0, direction_deg=30.0 * seed, noise_sigma=0.01, seed=seed)
            with pytest.raises(ValueError, match="no usable coherence peak"):
                itf.csi_height_map(v, DZ, 0.0, LAM)

    def test_the_generic_signal_pool_is_refused_not_misread(self):
        """The chain fuzzer's ``signal`` seed (a sinusoid plus noise) has no
        coherence envelope, and both signal-consuming ops say so rather than
        returning a height."""
        rng = np.random.default_rng(7)
        sig = np.sin(np.linspace(0, 8 * np.pi, 256)) + 0.1 * rng.standard_normal(256)
        with pytest.raises(ValueError, match="prominence"):
            itf.csi_peak_position(sig, DZ, 0.0, LAM)
        with pytest.raises(ValueError, match="negative"):
            itf.chromatic_confocal_height(sig, 500.0, 0.5, 0.20, 600.0)

    def test_the_simulate_ops_seed_the_signal_pool_with_real_data(self):
        """... and that is what keeps the shared ``signal`` sort from being a
        vocabulary the family can never actually be exercised through."""
        s = itf.csi_signal_simulate()
        assert isinstance(s, np.ndarray) and s.ndim == 1
        assert itf.csi_peak_position(s, 0.05, 0.0, 0.6) == pytest.approx(6.0,
                                                                        abs=1e-9)
        sp = itf.chromatic_confocal_simulate()
        assert itf.chromatic_confocal_height(sp) == pytest.approx(0.0, abs=1e-9)
