# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tomography — closed-form ground truth, the three break tables, and fail-closed.

Tomography is one of the corners of imaging where the answer is known
analytically, so this suite is built on exact identities rather than golden files:

  * the Radon transform of a uniform disc is the chord length
    ``2 sqrt(r^2 - s^2)``, and of a rotated ellipse it is
    ``2 rho a b sqrt(A^2 - s'^2) / A^2`` with
    ``A^2 = a^2 cos^2(t-phi) + b^2 sin^2(t-phi)``, so the discrete projector can
    be scored against the truth rather than against another implementation;
  * densities add, so the Shepp-Logan phantom has an **exact** sinogram and the
    reconstruction error belongs entirely to the reconstruction;
  * filtered back-projection of a uniform disc of density 1.0 must return 1.0,
    which is what pins the ordinary-versus-angular frequency convention in the
    ramp filter (the other convention is off by ``2*pi`` and looks identical);
  * the forward projector and the back-projector must be adjoints, which is a
    property no picture can show;
  * the beam-hardening model is monotone, so its inverse is exact and the round
    trip is a machine-precision identity;
  * the centre-of-mass identity ``s_cm(theta) = x0 cos t + y0 sin t + c`` is
    exact for any object inside the field of view.

The three ``TestBreak*`` classes are the ones that matter most: they re-derive the
tables printed in the module docstring, so a docstring number and the code can
never drift apart silently. They are marked slow-ish but kept in the default run,
because a break table nobody runs is a claim and not a measurement.

The classes at the end pin the bugs the 2026-09-02 adversarial pass found, each
with the minimal reproduction that exposed it. Every one of them was a *silent*
failure — a finite, plausible, wrong number — which is the only kind worth a
regression test in a module whose output nobody can check by eye.
"""
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import opstomography                                          # noqa: E402
import tomography as tg                                       # noqa: E402

N = 256               # reference reconstruction grid
R_DISC = 60.0         # px, reference disc radius
MU = 1.0 / 60.0       # attenuation scale giving a CT-realistic peak line integral
ANG180 = np.linspace(0.0, 180.0, 180, endpoint=False)

#: The Shepp-Logan phantom scaled to a peak line integral of ~1.18, i.e. the
#: e-folding count a real X-ray path has. The unscaled phantom in pixel units has
#: a peak line integral of 70.9, which is not wrong but makes every statement
#: about a *relative* detector error meaningless (see TestRings).
SL_CT = tuple((x0, y0, a, b, p, rho * MU) for (x0, y0, a, b, p, rho) in tg.SHEPP_LOGAN)

#: A uniform disc of density 1.0, in the normalised coordinates the phantom uses.
DISC = ((0.0, 0.0, R_DISC / (N / 2), R_DISC / (N / 2), 0.0, 1.0),)


def nrms(a, b):
    """RMS error normalised by the *truth's* dynamic range."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    return float(np.sqrt(((a - b) ** 2).mean()) / (b.max() - b.min()))


def disc_mask(size=N, radius=R_DISC, margin=8.0):
    c = (size - 1) / 2.0
    yy, xx = np.mgrid[0:size, 0:size]
    return np.hypot(xx - c, yy - c) < radius - margin


# --------------------------------------------------------------------------- #
# 1. the forward transform against the closed form                             #
# --------------------------------------------------------------------------- #
class TestClosedForm:
    def test_disc_sinogram_is_the_chord_length(self):
        """The analytic operator reproduces ``2 sqrt(r^2 - s^2)`` exactly."""
        sino = tg.ellipse_sinogram(N, DISC, ANG180)
        n_det = sino.shape[1]
        s = np.arange(n_det, dtype=float) - (n_det - 1) / 2.0
        chord = np.where(np.abs(s) < R_DISC,
                         2.0 * np.sqrt(np.maximum(R_DISC ** 2 - s ** 2, 0.0)), 0.0)
        # every angle must give the same row (a disc is rotationally symmetric)
        assert np.abs(sino - chord[None, :]).max() < 1e-9
        assert abs(sino.max() - 2.0 * R_DISC) < 1e-9

    def test_projector_matches_the_closed_form(self):
        """The module docstring's accuracy table, re-derived."""
        img = tg.ellipse_phantom(N, DISC, supersample=4)
        hard = tg.ellipse_phantom(N, DISC, supersample=1)
        sino = tg.radon_transform(img, ANG180)
        gt = tg.ellipse_sinogram(N, DISC, ANG180, sino.shape[1])
        peak = gt.max()
        n_det = sino.shape[1]
        s = np.arange(n_det, dtype=float) - (n_det - 1) / 2.0
        inner = np.abs(s) < R_DISC - 3.0

        all_rms = np.sqrt(((sino - gt) ** 2).mean()) / peak
        in_rms = np.sqrt(((sino - gt)[:, inner] ** 2).mean()) / peak
        assert in_rms == pytest.approx(0.00073, abs=5e-5)      # docstring 0.073 %
        assert all_rms == pytest.approx(0.00402, abs=3e-4)     # docstring 0.402 %

        # oversampling buys essentially nothing: 0.073 % -> 0.070 %
        fine = tg.radon_transform(img, ANG180, oversample=4)
        fine_rms = np.sqrt(((fine - gt)[:, inner] ** 2).mean()) / peak
        assert fine_rms == pytest.approx(0.00070, abs=5e-5)
        assert fine_rms > 0.5 * in_rms

        # anti-aliasing does: 0.276 % hard-edged against 0.073 %
        hard_rms = np.sqrt(((tg.radon_transform(hard, ANG180) - gt)[:, inner] ** 2
                            ).mean()) / peak
        assert hard_rms == pytest.approx(0.00276, abs=2e-4)
        assert hard_rms > 3.0 * in_rms

    def test_rotated_ellipse_is_not_symmetric_and_still_matches(self):
        """A rotated, off-centre ellipse: the case a sign error survives.

        A disc is invariant under every convention mistake there is — angle sign,
        detector sign, x/y swap — so it can only catch scale errors. This one
        cannot be reproduced by any of those mistakes.
        """
        ell = ((0.25, -0.15, 0.40, 0.15, 35.0, 1.0),)
        ang = np.linspace(0.0, 180.0, 60, endpoint=False)
        img = tg.ellipse_phantom(N, ell, supersample=4)
        sino = tg.radon_transform(img, ang)
        gt = tg.ellipse_sinogram(N, ell, ang, sino.shape[1])
        assert np.sqrt(((sino - gt) ** 2).mean()) / gt.max() < 0.02
        # the peak of each projection moves with the angle, and it must move the
        # way the analytic model says (this is the sign test)
        assert np.abs(np.argmax(sino, axis=1) - np.argmax(gt, axis=1)).max() <= 1

    def test_line_integrals_scale_with_the_grid(self):
        """Doubling the pixel grid doubles every line integral, exactly."""
        a = tg.ellipse_sinogram(128, DISC, ANG180, 400)
        b = tg.ellipse_sinogram(256, DISC, ANG180, 400)
        assert b.max() == pytest.approx(2.0 * a.max(), rel=1e-12)

    def test_projector_and_backprojector_are_adjoint(self):
        """``<A x, y> == <x, A^T y>`` — a property no picture can show."""
        rng = np.random.default_rng(0)
        x = rng.random((33, 33))
        ang = np.linspace(0.0, 180.0, 17, endpoint=False)
        rad = np.deg2rad(ang)
        n_det = tg._default_detectors(33, 33)
        y = rng.random((17, n_det))
        lhs = float((tg._project(x, rad, n_det, 1) * y).sum())
        rhs = float((x * tg._backproject(y, rad, 33)).sum())
        # not an exact adjoint pair: the forward uses a 2-D bilinear gather and
        # the back-projection a 1-D linear interpolation. Measured 1.2e-04.
        assert abs(lhs - rhs) / abs(lhs) < 1e-3


# --------------------------------------------------------------------------- #
# 2. the inversion, and its absolute scale                                     #
# --------------------------------------------------------------------------- #
class TestReconstruction:
    def test_fbp_returns_the_true_density(self):
        """A disc of density 1.0 must come back at 1.0, not at ``2*pi``.

        This is the whole ordinary-versus-angular-frequency question, and it is
        invisible in a picture because a CT slice has no absolute grey level.
        """
        sino = tg.ellipse_sinogram(N, DISC, ANG180)
        rec = tg.filtered_backprojection(sino, ANG180, size=N)
        m = disc_mask()
        assert rec[m].mean() == pytest.approx(0.9954, abs=2e-3)
        assert rec[m].std() < 0.005

    def test_fbp_converges_with_the_detector_not_the_views(self):
        """0.9954 at 363 bins, 0.9997 at 727 — and the same at 180/360/720 views."""
        m = disc_mask()
        coarse = {}
        for n_det in (363, 727):
            for n_v in (180, 360):
                a = np.linspace(0.0, 180.0, n_v, endpoint=False)
                rec = tg.filtered_backprojection(
                    tg.ellipse_sinogram(N, DISC, a, n_det), a, size=N)
                coarse[(n_det, n_v)] = rec[m].mean()
        assert coarse[(363, 180)] == pytest.approx(0.9954, abs=2e-3)
        assert coarse[(727, 180)] == pytest.approx(0.9997, abs=2e-3)
        # the view count changes nothing here
        assert coarse[(363, 180)] == pytest.approx(coarse[(363, 360)], abs=1e-6)
        assert coarse[(727, 180)] == pytest.approx(coarse[(727, 360)], abs=1e-6)

    def test_zero_padding_matters(self):
        """Without the 2x pad the ramp wraps and puts a 4 % cup in the interior."""
        sino = tg.ellipse_sinogram(N, DISC, ANG180)
        padded = tg.filtered_backprojection(sino, ANG180, size=N)
        n_det = sino.shape[1]
        h = tg._ramp_filter(n_det, "ramp", 1.0)
        unpadded_q = np.fft.irfft(np.fft.rfft(sino, axis=1) * h[None, :],
                                  n=n_det, axis=1)
        unpadded = tg._backproject(unpadded_q, np.deg2rad(ANG180), N) * (np.pi / 180)
        m = disc_mask()
        droop = 1.0 - unpadded[m].mean() / padded[m].mean()
        assert droop == pytest.approx(0.0405, abs=5e-3)

    def test_unfiltered_backprojection_has_no_absolute_scale(self):
        """Raw it is off by ~100x; affinely rescaled it is 6.8x worse than FBP."""
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        sino = tg.ellipse_sinogram(N, SL_CT, ANG180)
        bp = tg.backproject_sinogram(sino, ANG180, size=N)
        fbp = tg.filtered_backprojection(sino, ANG180, size=N)
        assert bp.min() > 0.5 and bp.max() > 2.0        # truth spans 0 .. 0.0167
        assert nrms(bp, truth) > 50.0

        def affine(a):
            design = np.column_stack([a.ravel(), np.ones(a.size)])
            k, *_ = np.linalg.lstsq(design, truth.ravel(), rcond=None)
            return nrms(a * k[0] + k[1], truth)

        assert affine(bp) == pytest.approx(0.168, abs=0.02)
        assert affine(fbp) == pytest.approx(0.0246, abs=3e-3)
        assert affine(bp) / affine(fbp) == pytest.approx(6.8, abs=1.0)

    def test_filter_names_all_run_and_order_by_sharpness(self):
        sino = tg.ellipse_sinogram(N, SL_CT, ANG180)
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        scores = {f: nrms(tg.filtered_backprojection(sino, ANG180, size=N,
                                                     filter_name=f), truth)
                  for f in ("ramp", "shepp-logan", "cosine", "hann", "hamming")}
        # with complete data the exact inverse and its gentlest apodisation win,
        # and the aggressive windows only blur
        assert scores["ramp"] == pytest.approx(0.0250, abs=3e-3)
        assert scores["shepp-logan"] < scores["cosine"] < scores["hamming"]
        assert scores["hann"] == pytest.approx(0.0358, abs=4e-3)
        # "ram-lak" is an accepted alias, and None means no filter at all
        assert np.array_equal(
            tg.filtered_backprojection(sino, ANG180, size=N, filter_name="ram-lak"),
            tg.filtered_backprojection(sino, ANG180, size=N, filter_name="ramp"))
        assert np.array_equal(
            tg.filtered_backprojection(sino, ANG180, size=N, filter_name=None),
            tg.backproject_sinogram(sino, ANG180, size=N))

    def test_sart_converges_and_the_constraint_is_worth_it(self):
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        sino = tg.ellipse_sinogram(N, SL_CT, ANG180)
        with_c = nrms(tg.sart_reconstruct(sino, ANG180, size=N, n_iter=10), truth)
        without = nrms(tg.sart_reconstruct(sino, ANG180, size=N, n_iter=10,
                                           nonnegative=False), truth)
        assert with_c == pytest.approx(0.0175, abs=3e-3)
        assert without == pytest.approx(0.0300, abs=4e-3)
        assert without > 1.4 * with_c
        # and it must actually be iterating: one sweep is worse than ten
        one = nrms(tg.sart_reconstruct(sino, ANG180, size=N, n_iter=1), truth)
        assert one > with_c

    def test_sart_starting_from_fbp_is_still_the_same_answer(self):
        """A solver whose answer depends on where it started is not solving."""
        truth = tg.ellipse_phantom(128, SL_CT, supersample=4)
        ang = np.linspace(0.0, 180.0, 60, endpoint=False)
        sino = tg.ellipse_sinogram(128, SL_CT, ang)
        cold = tg.sart_reconstruct(sino, ang, size=128, n_iter=12)
        warm = tg.sart_reconstruct(sino, ang, size=128, n_iter=12,
                                   initial=tg.filtered_backprojection(sino, ang,
                                                                      size=128))
        assert nrms(cold, truth) == pytest.approx(nrms(warm, truth), abs=0.01)


# --------------------------------------------------------------------------- #
# 3. break table 1 — how few views                                             #
# --------------------------------------------------------------------------- #
class TestBreakViewCount:
    """The module docstring's sparse-view table, re-derived."""

    EXPECTED = {          # views: (FBP ramp, SART x10)
        180: (0.0250, 0.0175),
        90: (0.0454, 0.0195),
        45: (0.1039, 0.0353),
        32: (0.1362, 0.0497),
        16: (0.2341, 0.0859),
        8: (0.3635, 0.1257),
    }

    def test_table(self):
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        got = {}
        for n_v in sorted(self.EXPECTED):
            a = np.linspace(0.0, 180.0, n_v, endpoint=False)
            sino = tg.ellipse_sinogram(N, SL_CT, a)
            got[n_v] = (nrms(tg.filtered_backprojection(sino, a, size=N), truth),
                        nrms(tg.sart_reconstruct(sino, a, size=N, n_iter=10), truth))
        for n_v, (f_exp, s_exp) in self.EXPECTED.items():
            f_got, s_got = got[n_v]
            assert f_got == pytest.approx(f_exp, rel=0.15), f"FBP at {n_v} views"
            assert s_got == pytest.approx(s_exp, rel=0.15), f"SART at {n_v} views"

        # the two claims the table is *for*
        assert got[8][0] / got[180][0] == pytest.approx(14.5, rel=0.25)
        assert got[8][1] / got[180][1] == pytest.approx(7.2, rel=0.25)
        # there is no crossing: SART leads everywhere
        for n_v in got:
            assert got[n_v][1] < got[n_v][0], f"SART lost at {n_v} views"
        assert got[180][0] / got[180][1] == pytest.approx(1.43, rel=0.2)
        assert got[8][0] / got[8][1] == pytest.approx(2.89, rel=0.2)

    def test_apodisation_flips_with_the_view_count(self):
        """Ramp wins with complete data; Hann wins once the data runs out."""
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        out = {}
        for n_v in (180, 45, 8):
            a = np.linspace(0.0, 180.0, n_v, endpoint=False)
            sino = tg.ellipse_sinogram(N, SL_CT, a)
            out[n_v] = tuple(
                nrms(tg.filtered_backprojection(sino, a, size=N, filter_name=f),
                     truth) for f in ("ramp", "hann"))
        assert out[180][0] < out[180][1]          # 0.0250 < 0.0358
        assert out[45][1] < out[45][0]            # 0.0740 < 0.1039
        assert out[8][1] < out[8][0]              # 0.3063 < 0.3635
        assert out[45][0] / out[45][1] == pytest.approx(1.40, rel=0.2)

    def test_noise_does_not_change_the_ranking(self):
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        rng = np.random.default_rng(7)
        i0 = 2e4
        for n_v, exp in ((180, (0.0360, 0.0291)), (16, (0.2481, 0.0864))):
            a = np.linspace(0.0, 180.0, n_v, endpoint=False)
            sino = tg.ellipse_sinogram(N, SL_CT, a)
            noisy = -np.log(np.maximum(rng.poisson(i0 * np.exp(-sino)), 1.0) / i0)
            f = nrms(tg.filtered_backprojection(noisy, a, size=N), truth)
            s = nrms(tg.sart_reconstruct(noisy, a, size=N, n_iter=10), truth)
            assert f == pytest.approx(exp[0], rel=0.2)
            assert s == pytest.approx(exp[1], rel=0.2)
            assert s < f


# --------------------------------------------------------------------------- #
# 4. break table 2 — the axis of rotation                                      #
# --------------------------------------------------------------------------- #
class TestBreakCentreOfRotation:
    EXPECTED = {          # shift px: (estimate, uncorrected nRMS)
        0.0: (0.0029, 0.0250),
        0.5: (0.5029, 0.0537),
        1.0: (1.0029, 0.1016),
        2.0: (2.0029, 0.1630),
    }

    def test_table(self):
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        sino = tg.ellipse_sinogram(N, SL_CT, ANG180)
        for shift, (est_exp, err_exp) in self.EXPECTED.items():
            bad = tg.sinogram_center_shift(sino, -shift, ANG180)
            est = tg.sinogram_center_of_rotation(bad, ANG180)
            assert est == pytest.approx(est_exp, abs=0.01), f"estimate at {shift}"
            rec = tg.filtered_backprojection(bad, ANG180, size=N)
            assert nrms(rec, truth) == pytest.approx(err_exp, rel=0.15)

    def test_half_a_pixel_doubles_the_error(self):
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        sino = tg.ellipse_sinogram(N, SL_CT, ANG180)
        clean = nrms(tg.filtered_backprojection(sino, ANG180, size=N), truth)
        half = tg.sinogram_center_shift(sino, -0.5, ANG180)
        assert nrms(tg.filtered_backprojection(half, ANG180, size=N),
                    truth) > 1.9 * clean

    def test_the_one_call_fix_repairs_integer_shifts_exactly(self):
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        sino = tg.ellipse_sinogram(N, SL_CT, ANG180)
        clean = nrms(tg.filtered_backprojection(sino, ANG180, size=N), truth)
        for shift, tol in ((1.0, 1e-3), (2.0, 1e-3)):
            bad = tg.sinogram_center_shift(sino, -shift, ANG180)
            fixed = tg.sinogram_center_shift(bad, None, ANG180)
            assert nrms(tg.filtered_backprojection(fixed, ANG180, size=N),
                        truth) == pytest.approx(clean, abs=tol)

    def test_fractional_shifts_are_not_information_preserving(self):
        """An integer round trip is exact; a fractional one costs 12 % of peak."""
        sino = tg.ellipse_sinogram(N, SL_CT, ANG180)
        exact = tg.sinogram_center_shift(tg.sinogram_center_shift(sino, 1.0), -1.0)
        assert np.abs(exact - sino).max() == 0.0
        half = tg.sinogram_center_shift(tg.sinogram_center_shift(sino, 0.5), -0.5)
        assert np.abs(half - sino).max() / sino.max() == pytest.approx(0.122,
                                                                      abs=0.03)

    def test_estimator_is_exact_on_a_known_centroid(self):
        """The identity itself, on an object whose centre of mass is known."""
        off = ((0.30, -0.20, 0.10, 0.10, 0.0, 1.0),)
        sino = tg.ellipse_sinogram(N, off, ANG180)
        assert tg.sinogram_center_of_rotation(sino, ANG180) == pytest.approx(
            0.0, abs=0.02)
        moved = tg.sinogram_center_shift(sino, -1.5, ANG180)
        assert tg.sinogram_center_of_rotation(moved, ANG180) == pytest.approx(
            1.5, abs=0.03)


# --------------------------------------------------------------------------- #
# 5. break table 3 — limited angle                                             #
# --------------------------------------------------------------------------- #
class TestBreakLimitedAngle:
    """The central-slice theorem, measured: a missing wedge deletes directions."""

    @staticmethod
    def sector_energy(rec, truth, size=N):
        f_r = np.abs(np.fft.fftshift(np.fft.fft2(rec)))
        f_t = np.abs(np.fft.fftshift(np.fft.fft2(truth)))
        fy, fx = np.mgrid[0:size, 0:size]
        phi = np.rad2deg(np.arctan2(fy - size // 2, fx - size // 2)) % 180.0
        rad = np.hypot(fx - size // 2, fy - size // 2)
        band = (rad > 4) & (rad < size // 2)
        return [f_r[band & (phi >= lo) & (phi < lo + 30)].sum()
                / f_t[band & (phi >= lo) & (phi < lo + 30)].sum()
                for lo in range(0, 180, 30)]

    def test_the_missing_wedge_is_exactly_the_missing_views(self):
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        for span, n_covered in ((180.0, 6), (120.0, 4), (90.0, 3), (60.0, 2)):
            n_v = int(round(span))
            a = np.linspace(0.0, span, n_v, endpoint=False)
            rec = tg.filtered_backprojection(
                tg.ellipse_sinogram(N, SL_CT, a), a, size=N, span_deg=span)
            keep = self.sector_energy(rec, truth)
            covered, missing = keep[:n_covered], keep[n_covered:]
            assert min(covered) > 0.85, f"span {span}: covered sectors {covered}"
            if missing:
                assert max(missing) < 0.30, f"span {span}: missing {missing}"
                assert min(covered) > 3.0 * max(missing)

    def test_limited_angle_loses_density_and_says_so(self):
        """A 90-degree scan reconstructs at ~0.49 of the truth, not at 1.0."""
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        m = disc_mask(N, 0.30 * N * 2, margin=0.0)
        for span, ratio in ((180.0, 0.974), (90.0, 0.489)):
            n_v = int(round(span))
            a = np.linspace(0.0, span, n_v, endpoint=False)
            rec = tg.filtered_backprojection(tg.ellipse_sinogram(N, SL_CT, a), a,
                                             size=N, span_deg=span)
            assert rec[m].mean() / truth[m].mean() == pytest.approx(ratio, rel=0.06)


# --------------------------------------------------------------------------- #
# 6. artefacts: the forward model and its correction                           #
# --------------------------------------------------------------------------- #
class TestBeamHardening:
    def test_cupping_appears_and_is_undone(self):
        ell = ((0.0, 0.0, R_DISC / (N / 2), R_DISC / (N / 2), 0.0, 1.0 / 60.0),)
        sino = tg.ellipse_sinogram(N, ell, ANG180)
        assert sino.max() == pytest.approx(2.0, abs=1e-9)
        hard = tg.beam_hardening_apply(sino, 0.5, 0.4)
        corr = tg.beam_hardening_correct(hard, 0.5, 0.4)

        def cup(sg):
            rec = tg.filtered_backprojection(sg, ANG180, size=N)
            c = (N - 1) / 2.0
            yy, xx = np.mgrid[0:N, 0:N]
            rr = np.hypot(xx - c, yy - c)
            centre = rec[int(c) - 3:int(c) + 4, int(c) - 3:int(c) + 4].mean()
            return centre / rec[(rr > R_DISC - 14) & (rr < R_DISC - 8)].mean()

        assert cup(sino) == pytest.approx(0.9981, abs=2e-3)
        assert cup(hard) == pytest.approx(0.9312, abs=8e-3)
        assert cup(corr) == pytest.approx(cup(sino), abs=2e-3)

    def test_the_model_inverse_is_exact(self):
        sino = tg.ellipse_sinogram(N, DISC, ANG180)
        for w, k in ((0.5, 0.4), (0.2, 0.8), (0.7, 0.1)):
            back = tg.beam_hardening_correct(tg.beam_hardening_apply(sino, w, k),
                                             w, k)
            assert np.abs(back - sino).max() / sino.max() < 1e-6

    def test_hardening_is_monotone_and_concave(self):
        p = np.linspace(0.0, 6.0, 401)[None, :].repeat(2, axis=0)
        q = tg.beam_hardening_apply(p, 0.5, 0.4)
        d1 = np.diff(q[0])
        assert (d1 > 0).all()                       # monotone
        assert (np.diff(d1) < 1e-12).all()          # concave -> cupping
        assert q[0, 0] == pytest.approx(0.0, abs=1e-12)

    def test_monochromatic_settings_are_the_identity(self):
        sino = tg.ellipse_sinogram(64, DISC, np.linspace(0, 180, 60, endpoint=False))
        assert np.allclose(tg.beam_hardening_apply(sino, 0.0, 0.4), sino)
        assert np.allclose(tg.beam_hardening_apply(sino, 0.5, 1.0), sino)

    def test_polynomial_route(self):
        sino = tg.ellipse_sinogram(64, DISC, np.linspace(0, 180, 60, endpoint=False))
        out = tg.beam_hardening_correct(sino, poly_coeffs=(1.0, 0.0))
        assert np.allclose(out, sino)
        out2 = tg.beam_hardening_correct(sino, poly_coeffs=(2.0,))
        assert np.allclose(out2, 2.0 * sino)


class TestRings:
    def test_a_gain_error_is_a_constant_offset_per_column(self):
        sino = tg.ellipse_sinogram(N, SL_CT, ANG180)
        ringed = tg.ring_artifact_apply(sino, 0.02, seed=0)
        delta = ringed - sino
        # identical at every angle, by construction and by measurement
        assert np.abs(delta - delta[0][None, :]).max() < 1e-12
        assert delta.std() == pytest.approx(0.02, rel=0.2)
        # deterministic
        assert np.array_equal(ringed, tg.ring_artifact_apply(sino, 0.02, seed=0))
        assert not np.array_equal(ringed, tg.ring_artifact_apply(sino, 0.02, seed=1))

    def test_removal_undoes_most_of_it_and_barely_touches_a_clean_scan(self):
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        sino = tg.ellipse_sinogram(N, SL_CT, ANG180)
        ringed = tg.ring_artifact_apply(sino, 0.02, seed=0)

        def err(sg):
            return nrms(tg.filtered_backprojection(sg, ANG180, size=N), truth)

        clean, damaged = err(sino), err(ringed)
        assert clean == pytest.approx(0.0250, abs=3e-3)
        assert damaged == pytest.approx(0.0643, abs=8e-3)
        fixed = err(tg.ring_artifact_remove(ringed))
        assert fixed == pytest.approx(0.0358, abs=5e-3)
        undone = (damaged - fixed) / (damaged - clean)
        assert undone == pytest.approx(0.72, abs=0.12)
        # and the collateral damage on a sinogram that had no rings is tiny
        assert err(tg.ring_artifact_remove(sino)) - clean < 0.001

    def test_a_wide_mean_window_is_worse_at_both_jobs(self):
        """Why the default is (5, median) and not (31, mean)."""
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        sino = tg.ellipse_sinogram(N, SL_CT, ANG180)
        ringed = tg.ring_artifact_apply(sino, 0.02, seed=0)

        def err(sg):
            return nrms(tg.filtered_backprojection(sg, ANG180, size=N), truth)

        default_damage = err(tg.ring_artifact_remove(sino)) - err(sino)
        wide_damage = err(tg.ring_artifact_remove(sino, 31, "mean")) - err(sino)
        assert wide_damage > 5.0 * max(default_damage, 1e-4)
        assert err(tg.ring_artifact_remove(ringed, 31, "mean")) > \
            err(tg.ring_artifact_remove(ringed))

    def test_the_error_only_matters_relative_to_the_line_integrals(self):
        """The same 2 % gain error is invisible on the raw-unit phantom."""
        truth = tg.ellipse_phantom(N, supersample=4)
        sino = tg.ellipse_sinogram(N, None, ANG180)
        assert sino.max() == pytest.approx(70.9, rel=0.05)

        def err(sg):
            return nrms(tg.filtered_backprojection(sg, ANG180, size=N), truth)

        assert abs(err(tg.ring_artifact_apply(sino, 0.02, seed=0))
                   - err(sino)) < 1e-4


class TestMetal:
    @staticmethod
    def setup_case(density):
        metal = ((0.30, 0.10, 6.0 / (N / 2), 6.0 / (N / 2), 0.0, density * MU),)
        sino = tg.ellipse_sinogram(N, SL_CT + metal, ANG180)
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        c = (N - 1) / 2.0
        yy, xx = np.mgrid[0:N, 0:N]
        outside = np.hypot(xx - (c + 0.30 * N / 2), yy - (c + 0.10 * N / 2)) > 12
        return sino, truth, outside

    @pytest.mark.parametrize("density,uncorrected", [(8.0, 0.0487),
                                                     (30.0, 0.1583),
                                                     (100.0, 0.5214)])
    def test_image_domain_trace_recovers_the_slice(self, density, uncorrected):
        sino, truth, outside = self.setup_case(density)
        rec = tg.filtered_backprojection(sino, ANG180, size=N)
        assert nrms(rec[outside], truth[outside]) == pytest.approx(uncorrected,
                                                                   rel=0.15)
        fixed = tg.filtered_backprojection(
            tg.metal_trace_interpolate(sino, ANG180), ANG180, size=N)
        assert nrms(fixed[outside], truth[outside]) == pytest.approx(0.0256,
                                                                     abs=4e-3)

    def test_the_sinogram_threshold_shortcut_is_worse_than_nothing(self):
        """Pinning the measurement that decided the operator's design.

        This is the failure that would otherwise be repeated: it looks like an
        obvious simplification, it produces a picture with fewer streaks, and it
        is *worse than not correcting at all* at every density.
        """
        for density in (8.0, 30.0, 100.0):
            sino, truth, outside = self.setup_case(density)
            rec = tg.filtered_backprojection(sino, ANG180, size=N)
            base = nrms(rec[outside], truth[outside])
            naive_mask = sino > (sino.mean() + 3.0 * sino.std())
            naive = tg.filtered_backprojection(
                tg.metal_trace_interpolate(sino, mask=naive_mask), ANG180, size=N)
            assert nrms(naive[outside], truth[outside]) > base

    def test_no_metal_is_a_no_op(self):
        sino = tg.ellipse_sinogram(128, SL_CT, np.linspace(0, 180, 90,
                                                           endpoint=False))
        out = tg.metal_trace_interpolate(
            sino, np.linspace(0, 180, 90, endpoint=False),
            image_threshold=1e9)
        assert np.array_equal(out, sino)

    def test_explicit_mask_interpolates_linearly(self):
        sino = np.tile(np.linspace(0.0, 10.0, 32), (8, 1))
        mask = np.zeros(sino.shape, bool)
        mask[:, 10:14] = True
        out = tg.metal_trace_interpolate(sino, mask=mask)
        # a linear ramp is exactly recovered by linear interpolation
        assert np.abs(out - sino).max() < 1e-12


# --------------------------------------------------------------------------- #
# 7. scan layout                                                               #
# --------------------------------------------------------------------------- #
class TestLayout:
    @pytest.mark.parametrize("scheme", tomo_schemes := list(tg.ANGLE_SCHEMES))
    @pytest.mark.parametrize("n", [1, 8, 17, 180, 181])
    def test_angles_are_distinct_and_inside_the_span(self, scheme, n):
        a = tg.projection_angles(n, 180.0, scheme)
        assert a.shape == (n,)
        assert len(np.unique(np.round(a, 9))) == n
        assert a.min() >= 0.0 and a.max() < 180.0

    def test_truncation_gap_table(self):
        """The docstring's table: uniform leaves a 149-degree hole, golden 10."""
        gaps = {}
        for scheme in tg.ANGLE_SCHEMES:
            full = tg.projection_angles(180, 180.0, scheme)
            for k in (32, 180):
                a = np.sort(np.mod(full[:k], 180.0))
                d = np.diff(np.concatenate([a, [a[0] + 180.0]]))
                gaps[(scheme, k)] = float(d.max())
        assert gaps[("uniform", 32)] == pytest.approx(149.0, abs=0.5)
        assert gaps[("golden", 32)] == pytest.approx(10.031, abs=0.05)
        assert gaps[("bit-reversed", 32)] == pytest.approx(8.0, abs=0.05)
        assert gaps[("uniform", 180)] == pytest.approx(1.0, abs=0.01)
        assert gaps[("golden", 180)] == pytest.approx(1.464, abs=0.02)
        assert gaps[("bit-reversed", 180)] == pytest.approx(1.0, abs=0.01)
        # the claim the schemes exist for
        assert gaps[("golden", 32)] < 0.10 * gaps[("uniform", 32)]

    def test_a_truncated_golden_scan_reconstructs_and_a_uniform_one_does_not(self):
        truth = tg.ellipse_phantom(N, SL_CT, supersample=4)
        img = truth
        out = {}
        for scheme in ("uniform", "golden"):
            a = tg.projection_angles(180, 180.0, scheme)[:32]
            sino = tg.radon_transform(img, a)
            out[scheme] = nrms(tg.filtered_backprojection(sino, a, size=N,
                                                          span_deg=180.0), truth)
        assert out["golden"] < out["uniform"]

    def test_design_reports_the_sampling_rule(self):
        d = tg.sinogram_design(n_angles=180, n_detectors=363, size=256)
        assert d["views_for_full_sampling"] == int(np.ceil(np.pi / 2 * 363))
        assert d["undersampling_factor"] == pytest.approx(571 / 180.0, rel=1e-3)
        assert d["verdict"] == "sparse view"
        assert d["streak_free_radius_px"] == pytest.approx(180.0 / np.pi, rel=1e-6)
        assert d["sinogram_bytes"] == 180 * 363 * 8
        full = tg.sinogram_design(n_angles=600, n_detectors=363, size=256)
        assert full["verdict"] == "fully sampled"
        assert tg.sinogram_design(n_angles=90, span_deg=90.0
                                  )["complete_angular_coverage"] is False


# --------------------------------------------------------------------------- #
# 8. the volume route, and the sort boundary it needs                          #
# --------------------------------------------------------------------------- #
class TestVolume:
    def test_round_trip_through_the_stack(self):
        vol = np.stack([tg.ellipse_phantom(64, SL_CT, 2) for _ in range(4)])
        ang = np.linspace(0.0, 180.0, 90, endpoint=False)
        stack = tg.radon_volume(vol, ang)
        assert stack.shape[0] == 4 and stack.shape[1] == 90
        back = tg.fbp_volume(stack, ang, size=64)
        assert back.shape == (4, 64, 64)
        for k in range(4):
            assert nrms(back[k], vol[k]) < 0.06

    def test_each_slice_is_independent(self):
        """Parallel beam: changing one slice must not move any other."""
        vol = np.stack([tg.ellipse_phantom(48, SL_CT, 2) for _ in range(3)])
        vol2 = vol.copy()
        vol2[1] *= 2.0
        ang = np.linspace(0.0, 180.0, 60, endpoint=False)
        a = tg.radon_volume(vol, ang)
        b = tg.radon_volume(vol2, ang)
        assert np.abs(a[0] - b[0]).max() < 1e-12
        assert np.abs(a[2] - b[2]).max() < 1e-12
        assert np.abs(a[1] - b[1]).max() > 1e-6

    def test_a_stack_and_a_volume_are_structurally_indistinguishable(self):
        """The measurement that made ``sinostack`` its own sort.

        Both are 3-D float arrays; every predicate the existing 3-D sorts use is
        satisfied by both; and passing each to the other's consumer returns a
        finite, plausible array rather than raising.
        """
        vol = np.stack([tg.ellipse_phantom(32, SL_CT, 2) for _ in range(6)])
        stack = tg.radon_volume(vol, np.linspace(0.0, 180.0, 32, endpoint=False))
        for v in (vol, stack):
            assert v.ndim == 3 and v.dtype.kind == "f"
            assert v.shape[0] >= 3 and v.shape[1] >= 4 and v.shape[2] >= 4
        wrong = tg.fbp_volume(vol)             # a volume fed to the stack consumer
        assert np.isfinite(wrong).all()        # silently accepted, meaningless
        assert wrong.ndim == 3


# --------------------------------------------------------------------------- #
# 9. the ledger                                                                #
# --------------------------------------------------------------------------- #
class TestLedger:
    def test_every_declared_op_exists(self):
        assert opstomography.missing() == []
        assert len(opstomography.OPSTOMOGRAPHY) == len(tg.TOMOGRAPHY)
        assert set(opstomography.OPSTOMOGRAPHY) == set(tg.TOMOGRAPHY)

    def test_every_op_is_exported(self):
        for name in tg.TOMOGRAPHY:
            assert name in tg.__all__
            assert callable(getattr(tg, name))

    def test_new_sorts_are_produced_and_consumed(self):
        """A sort with no producer is unreachable; with no consumer, a dead end."""
        produced, consumed = {}, {}
        for name, meta in opstomography.OPSTOMOGRAPHY.items():
            produced.setdefault(meta["out"], []).append(name)
            for t in meta["in"]:
                consumed.setdefault(t, []).append(name)
        for sort in ("sinogram", "sinostack"):
            assert produced.get(sort), f"{sort} has no producer"
            assert consumed.get(sort), f"{sort} has no consumer"
        # and the entries must be reachable from sorts that already exist
        entries = [n for n in produced["sinogram"]
                   if set(opstomography.OPSTOMOGRAPHY[n]["in"]) <= {"image2d"}]
        assert entries, "sinogram is only produced from sinogram"
        assert "radon_volume" in produced["sinostack"]
        assert opstomography.OPSTOMOGRAPHY["radon_volume"]["in"] == ["voxel"]
        assert opstomography.OPSTOMOGRAPHY["fbp_volume"]["out"] == "voxel"

    def test_result_adapters_are_unnecessary(self):
        """Declared out-type == raw return type, for every op, checked."""
        assert opstomography.RESULT_ADAPTERS == {}
        sino = tg.ellipse_sinogram(64, DISC, np.linspace(0, 180, 45,
                                                         endpoint=False))
        assert isinstance(tg.sinogram_design(), dict)
        assert isinstance(tg.sinogram_center_of_rotation(sino), float)
        assert isinstance(tg.projection_angles(8), np.ndarray)
        assert tg.filtered_backprojection(sino).ndim == 2


# --------------------------------------------------------------------------- #
# 10. fail-closed                                                              #
# --------------------------------------------------------------------------- #
class TestFailClosed:
    @staticmethod
    def sino(n_a=60, n_d=None, size=64):
        return tg.ellipse_sinogram(size, None,
                                   np.linspace(0, 180, n_a, endpoint=False), n_d)

    def test_non_finite_is_refused(self):
        with pytest.raises(ValueError, match="non-finite"):
            tg.filtered_backprojection(np.full((8, 16), np.nan))
        with pytest.raises(ValueError, match="non-finite"):
            tg.radon_transform(np.full((8, 8), np.inf))

    def test_zero_projections(self):
        with pytest.raises(ValueError, match="empty"):
            tg.radon_transform(np.ones((8, 8)), np.array([]))

    def test_detector_narrower_than_the_phantom(self):
        with pytest.raises(ValueError, match="do not cover"):
            tg.radon_transform(np.ones((64, 64)), n_detectors=32)

    def test_angle_count_must_match_the_rows(self):
        with pytest.raises(ValueError, match="but the sinogram has"):
            tg.filtered_backprojection(self.sino(60), np.linspace(0, 180, 7))

    @pytest.mark.parametrize("call", [
        lambda: tg.ellipse_phantom(20000),
        lambda: tg.ellipse_phantom(4000, supersample=16),
        lambda: tg.filtered_backprojection(TestFailClosed.sino(), size=100000),
        lambda: tg.sinogram_design(n_angles=60000, n_detectors=60000),
    ])
    def test_the_small_argument_that_asks_for_gigabytes(self, call):
        """Caps read off the *requested output*, not off the input's size."""
        with pytest.raises(ValueError):
            call()

    def test_relaxation_must_be_inside_the_convergence_bound(self):
        with pytest.raises(ValueError, match=r"relaxation must be in \(0, 2\)"):
            tg.sart_reconstruct(self.sino(), relaxation=2.0)
        with pytest.raises(ValueError):
            tg.sart_reconstruct(self.sino(), relaxation=0.0)

    def test_even_smoothing_window(self):
        with pytest.raises(ValueError, match="must be odd"):
            tg.ring_artifact_remove(self.sino(), 30)

    def test_shift_off_the_detector(self):
        with pytest.raises(ValueError, match="half the detector width"):
            tg.sinogram_center_shift(self.sino(), 1e6)

    def test_negative_line_integrals_cannot_be_hardened(self):
        with pytest.raises(ValueError, match="negative value"):
            tg.beam_hardening_apply(self.sino() - 5.0)

    def test_hardening_beyond_what_the_beam_can_produce(self):
        with pytest.raises(ValueError, match="saturat"):
            tg.beam_hardening_correct(self.sino() * 1e6, 0.5, 0.4)

    def test_a_float_mask_is_refused(self):
        with pytest.raises(ValueError, match="boolean"):
            tg.metal_trace_interpolate(self.sino(),
                                       mask=np.ones(self.sino().shape))

    def test_a_mask_that_eats_a_whole_view(self):
        s = self.sino()
        m = np.zeros(s.shape, bool)
        m[3] = True
        with pytest.raises(ValueError, match="entirely flagged"):
            tg.metal_trace_interpolate(s, mask=m)

    @pytest.mark.parametrize("call", [
        lambda: tg.projection_angles(180.0),
        lambda: tg.projection_angles(180, "180"),
        lambda: tg.projection_angles(180, 180.0, "spiral"),
        lambda: tg.projection_angles(180, -5.0),
        lambda: tg.ring_artifact_apply(TestFailClosed.sino(), 0.02, True),
        lambda: tg.radon_transform(np.ones((8, 8), complex)),
        lambda: tg.radon_transform(np.array([["1.0", "2.0"], ["3.0", "4.0"]])),
        lambda: tg.filtered_backprojection(np.ones(64)),
        lambda: tg.filtered_backprojection(TestFailClosed.sino(),
                                           filter_name="butterworth"),
        lambda: tg.filtered_backprojection(TestFailClosed.sino(), cutoff=0.0),
        lambda: tg.ellipse_phantom(32, ((0.0, 0.0, 0.0, 0.5, 0.0, 1.0),)),
        lambda: tg.fbp_volume(np.ones((8, 8))),
        lambda: tg.radon_volume(np.ones((4, 4))),
        lambda: tg.beam_hardening_apply(TestFailClosed.sino(), 1.0, 0.4),
        lambda: tg.beam_hardening_apply(TestFailClosed.sino(), 0.5, 1.5),
        lambda: tg.sart_reconstruct(TestFailClosed.sino(), size=64,
                                    initial=np.ones((5, 5))),
    ])
    def test_the_refusal_matrix(self, call):
        with pytest.raises(ValueError):
            call()

    def test_masked_arrays_are_not_silently_unmasked(self):
        s = self.sino()
        m = np.ma.masked_array(s, mask=(s > s.mean()))
        with pytest.raises(ValueError, match="masked"):
            tg.filtered_backprojection(m)


# --------------------------------------------------------------------------- #
# 11. regressions — the 2026-09-02 adversarial pass                            #
#                                                                              #
# Every one of these was a finite, plausible, wrong answer. None of them raised #
# anything before the fix, and none of them is visible in a picture.            #
# --------------------------------------------------------------------------- #
class TestAdversarialRegressions:
    def test_a_360_degree_scan_does_not_double_the_density(self):
        """Measured before the fix: 2.12x the true density, silently.

        Parallel-beam views at ``theta`` and ``theta+180`` are mirror images, so
        a full-turn scan measures every line twice. The naive
        ``median_step * n_angles`` quadrature summed both copies. A doubled CT
        slice is perfectly sharp and has no reference grey level to fail against.
        """
        truth = tg.ellipse_phantom(128, SL_CT, supersample=4)
        c = 63.5
        yy, xx = np.mgrid[0:128, 0:128]
        skull = np.hypot(xx - c, yy - c) < 0.30 * 128
        means = {}
        for span, n_v in ((180.0, 180), (360.0, 360), (360.0, 180), (270.0, 270)):
            a = np.linspace(0.0, span, n_v, endpoint=False)
            rec = tg.filtered_backprojection(tg.ellipse_sinogram(128, SL_CT, a), a,
                                             size=128)
            means[(span, n_v)] = rec[skull].mean() / truth[skull].mean()
        assert means[(180.0, 180)] == pytest.approx(0.974, abs=0.02)
        for key, val in means.items():
            assert val == pytest.approx(0.974, abs=0.02), key

    def test_radians_passed_as_degrees_are_refused(self):
        """Measured before the fix: a finite slice with values 39x too small.

        ``filtered_backprojection(sino, np.deg2rad(angles))`` returned a smooth,
        plausible picture. Nothing downstream could have caught it, so the angle
        list is checked at the door.
        """
        sino = tg.ellipse_sinogram(128, SL_CT, ANG180)
        with pytest.raises(ValueError, match="radians"):
            tg.filtered_backprojection(sino, np.deg2rad(ANG180))
        # and a genuinely narrow *degree* span is refused by the same rule, on
        # purpose: 6.28 degrees of coverage reconstructs nothing anyway
        with pytest.raises(ValueError, match="radians"):
            tg.filtered_backprojection(sino, np.linspace(0.0, 3.0, 180))
        # a legitimate limited-angle scan is not affected
        a30 = np.linspace(0.0, 30.0, 30, endpoint=False)
        tg.filtered_backprojection(tg.ellipse_sinogram(128, SL_CT, a30), a30,
                                   size=64)

    def test_a_narrow_span_centre_of_rotation_is_refused(self):
        """Measured before the fix: -6.98 px returned for a true +1.00 px.

        Over a narrow wedge ``cos(theta)`` and the constant column of the design
        matrix are nearly the same vector, so the fit puts the object's own
        offset into the axis offset. The answer is finite, the sign is wrong, and
        the magnitude is eight times the error being measured.
        """
        sino = tg.ellipse_sinogram(128, SL_CT, ANG180)
        for span in (45.0, 20.0, 10.0):
            n_v = max(6, int(span))
            a = np.linspace(0.0, span, n_v, endpoint=False)
            narrow = tg.ellipse_sinogram(128, SL_CT, a)
            with pytest.raises(ValueError, match="linearly dependent"):
                tg.sinogram_center_of_rotation(narrow, a)
        # 60 degrees is admitted, and is accurate to 0.11 px
        a60 = np.linspace(0.0, 60.0, 60, endpoint=False)
        shifted = tg.sinogram_center_shift(tg.ellipse_sinogram(128, SL_CT, a60),
                                           -1.0)
        assert tg.sinogram_center_of_rotation(shifted, a60) == pytest.approx(
            1.0, abs=0.15)
        assert tg.sinogram_center_of_rotation(sino, ANG180) == pytest.approx(
            0.0, abs=0.02)

    def test_a_filtered_sinogram_is_refused_by_the_centre_estimator(self):
        """The centre-of-mass identity needs raw line integrals, not filtered ones."""
        sino = tg.ellipse_sinogram(128, SL_CT, ANG180)
        filtered = tg._filter_projections(sino, "ramp", 1.0)
        with pytest.raises(ValueError, match="zero or negative total mass"):
            tg.sinogram_center_of_rotation(filtered, ANG180)

    def test_offsets_of_the_wrong_length_are_refused(self):
        """A per-*angle* array would broadcast into a smooth shading, not rings."""
        sino = tg.ellipse_sinogram(64, None, np.linspace(0, 180, 60,
                                                         endpoint=False))
        with pytest.raises(ValueError, match="one per detector bin"):
            tg.ring_artifact_apply(sino, offsets=np.zeros(sino.shape[0]))
        ok = tg.ring_artifact_apply(sino, offsets=np.zeros(sino.shape[1]))
        assert np.allclose(ok, sino)
