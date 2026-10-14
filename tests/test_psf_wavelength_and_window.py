# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""psf_from_opd: the wavelength override, the pupil-width convention and the PSF window.

Three silent defects found 2026-10-14 (a private aberration-depth PoC), each
checked here against an independent route rather than a golden file:

* **wavelength override** — ``psf_from_opd(system@0.55, wavelength_um=0.46)``
  refracted at 0.46 µm but aimed its rays with the 0.55 µm pupils and scaled
  the PSF with the 0.55 µm f-number; it must equal the system rebuilt at
  0.46 µm with the same sensor plane (stop on either surface, on and off axis).
* **pupil width** — ``opd_samples`` puts the outer sample centres on the pupil
  edge (``n − 1`` cells across) while ``optics.pupil_psf`` takes ``n`` cells
  as the diameter; with ``f_number = N·(n−1)/n`` the two routes give the same
  PSF size, without it they differ by ``n/(n−1)``.
* **window** — the automatic pupil grid left a PSF window only 1.25x the
  geometric spot and folded 1–2 % of the energy back in; the automatic PSF
  must now be within 1 % (total variation) of one from a 3x finer pupil.
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import lensimage as LI  # noqa: E402
import optics  # noqa: E402
import raytrace as RT  # noqa: E402

SENSOR_MM = 23.5375          # fixed image plane: 1000 mm in focus at 0.55 µm


def _singlet(wl, stop=0, object_mm=1000.0):
    return RT.lens_system([{"R": 12.9, "t": 3.0, "n": "N-BK7", "ap": 3.1},
                           {"R": np.inf, "t": SENSOR_MM, "n": 1.0}],
                          stop=stop, object_mm=object_mm, wavelength_um=wl)


def _tv(a, b):
    h = max(a.shape[0], b.shape[0])
    pa = np.pad(a, (h - a.shape[0]) // 2)
    pb = np.pad(b, (h - b.shape[0]) // 2)
    return 0.5 * float(np.abs(pa - pb).sum())


def _rms_radius(psf, dx):
    n = psf.shape[0]
    y, x = (np.mgrid[:n, :n] - n // 2) * dx
    w = psf / psf.sum()
    cx, cy = (w * x).sum(), (w * y).sum()
    return float(np.sqrt((w * ((x - cx) ** 2 + (y - cy) ** 2)).sum()))


@pytest.mark.parametrize("stop", [0, 1])
@pytest.mark.parametrize("field", [0.0, 30.0])
def test_wavelength_override_equals_the_system_rebuilt_at_that_wavelength(stop, field):
    over = LI.psf_from_opd(_singlet(0.55, stop), field=field, wavelength_um=0.46, size=160, pixel_pitch_um=5)
    built = LI.psf_from_opd(_singlet(0.46, stop), field=field, size=160, pixel_pitch_um=5)
    assert over.shape == built.shape
    assert float(np.abs(over - built).max()) < 1e-12
    sa = RT.spot_stats(_singlet(0.55, stop), field=field, wavelength_um=0.46)
    sb = RT.spot_stats(_singlet(0.46, stop), field=field)
    assert sa["rms_radius"] == pytest.approx(sb["rms_radius"], rel=1e-12, abs=1e-15)


def test_psf_field_grid_reports_f_number_and_spot_at_the_requested_wavelength():
    g = LI.psf_field_grid(_singlet(0.55), fields=(0.0,), wavelength_um=0.46, size=160)
    b = LI.psf_field_grid(_singlet(0.46), fields=(0.0,), size=160)
    assert g["fno"] == pytest.approx(b["fno"], rel=1e-12)
    assert g["rms_spot_mm"][0] == pytest.approx(b["rms_spot_mm"][0], rel=1e-12)


def test_opd_samples_map_through_pupil_psf_needs_the_n_minus_1_f_number():
    s = _singlet(0.55)
    n, os_ = 64, 8
    fno = LI._working_fno(RT.paraxial_trace(s))
    psf_a, _ref, dx_a, _n = LI._psf_core(s, size=n, oversample=os_)
    mask, W = LI._pupil(s, s["field"], n, 0.55)
    r_a = _rms_radius(psf_a, dx_a)

    def via_pupil_psf(f_number):
        p = optics.pupil_psf(mask.astype(float), wavelength_um=0.55, f_number=f_number,
                             oversample=os_, opd_waves=W)
        M = p.shape[0]
        return _rms_radius(p, 0.55 * f_number * n / M)

    assert via_pupil_psf(fno * (n - 1) / n) / r_a == pytest.approx(1.0, abs=1e-3)
    # the naive call is off by the cell count: n/(n-1) = 1.016 at n = 64
    assert via_pupil_psf(fno) / r_a == pytest.approx(n / (n - 1), abs=2e-3)


@pytest.mark.parametrize("object_mm,wl", [(700.0, 0.55), (2000.0, 0.62), (300.0, 0.46)])
def test_automatic_pupil_grid_leaves_no_folded_energy(object_mm, wl):
    s = _singlet(wl, object_mm=object_mm)
    n = LI._auto_size(s, s["field"], wl)
    assert n >= 128
    auto = LI.psf_from_opd(s, pixel_pitch_um=5)
    fine = LI.psf_from_opd(s, size=min(LI.MAX_PUPIL_SAMPLES, 3 * n), pixel_pitch_um=5)
    assert _tv(auto, fine) < 0.01
    # the rule before 2026-10-15 (phase only, floor 64) fails this gate: the gate can fail
    mask, W = LI._pupil(s, s["field"], 32, wl)
    g = LI._max_phase_step(mask, W) * 31 / 2.0
    n_old = max(64, int(np.ceil(g * 2.0 / 0.4)) + 1)
    old = LI.psf_from_opd(s, size=n_old, pixel_pitch_um=5)
    assert _tv(old, fine) > 0.01
