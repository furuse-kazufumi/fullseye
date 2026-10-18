# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Ideal (paraxial) lens surface of ``raytrace.lens_system`` -- closed-form gates.

The surface ``{"f": ...}`` turns every ray by the thin-lens law exactly. Every number below
has a closed form that does not go through the code under test: a collimated beam crosses the
axis at ``f``; a finite object images at the Gaussian conjugate ``s' = f s/(s - f)`` with
``m = -s'/s``; two ideal lenses combine to ``f1 f2/(f1 + f2 - d)``; and an aberration-free lens
reads zero OPD, so its PSF is the Airy pattern.

The probes break each gate on purpose (a wrong sign, a wrong conjugate) and require it to go
red, so a gate that stopped looking would show up here.
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import raytrace as RT  # noqa: E402
import optdraw as OD  # noqa: E402

F = 50.0


def _lens(f=F, ap=10.0, **kw):
    return RT.lens_system([{"f": f, "t": None, "ap": ap}], stop=0, **kw)


def _crossing_error(system, heights, expect=F):
    """Largest gap between where a real collimated ray crosses the axis and the expected focus *expect* (mm)."""
    P = np.array([[h, 0.0, -5.0] for h in heights])
    D = np.tile([0.0, 0.0, 1.0], (len(heights), 1))
    tr = RT.trace_rays(system, P, D, image_mm=0.0)
    out = tr["dirs"][:, 1, :]
    x0 = tr["points"][:, 1, 0]
    z_cross = -x0 / (out[:, 0] / out[:, 2])
    return float(np.max(np.abs(z_cross - expect)))


def test_collimated_beam_focuses_at_f_to_machine_precision():
    sysm = _lens()
    err = _crossing_error(sysm, [0.5, 2.0, 5.0, 9.99])
    assert err < 1e-12, err
    para = RT.paraxial_trace(sysm)
    assert abs(para["efl"] - F) < 1e-12 and abs(para["bfl"] - F) < 1e-12
    st = RT.spot_stats(sysm)
    assert st["rms_radius"] < 1e-12 and st["n_vignetted"] == 0


def test_negative_lens_diverges_from_a_virtual_focus():
    sysm = _lens(f=-F)
    para = RT.paraxial_trace(sysm)
    assert abs(para["efl"] + F) < 1e-12
    P = np.array([[4.0, 0.0, -5.0]])
    tr = RT.trace_rays(sysm, P, np.array([[0.0, 0.0, 1.0]]), image_mm=10.0)
    d = tr["dirs"][0, 1]
    assert d[0] / d[2] == pytest.approx(4.0 / F, abs=1e-14)       # +x slope: diverging
    z_virtual = -tr["points"][0, 1, 0] / (d[0] / d[2])
    assert abs(z_virtual - (-F)) < 1e-12                            # the ray comes from z = -F


@pytest.mark.parametrize("s", [120.0, 200.0, 75.0])
def test_finite_object_images_at_the_gaussian_conjugate(s):
    sysm = _lens(object_mm=s, field=2.0)
    sp = F * s / (s - F)
    para = RT.paraxial_trace(sysm)
    assert abs(para["image_mm"] - sp) < 1e-12
    assert abs(para["magnification"] + sp / s) < 1e-12
    # real rays of the object height 2 mm all land on y = m * 2
    st = RT.spot_stats(sysm, field=2.0)
    assert st["rms_radius"] < 1e-12, st
    assert abs(st["centroid_y"] - (-sp / s * 2.0)) < 1e-12
    assert abs(st["centroid_x"]) < 1e-12


def test_two_ideal_lenses_combine_by_the_gullstrand_formula():
    d, f1, f2 = 50.0, 100.0, 80.0
    sysm = RT.lens_system([{"f": f1, "t": d, "ap": 10.0}, {"f": f2, "t": None}], stop=0)
    para = RT.paraxial_trace(sysm)
    efl = f1 * f2 / (f1 + f2 - d)
    assert abs(para["efl"] - efl) < 1e-10
    assert abs(para["bfl"] - efl * (1.0 - d / f1)) < 1e-10          # back focal distance of two thin lenses
    assert RT.spot_stats(sysm)["rms_radius"] < 1e-10                  # still stigmatic through both


def test_ideal_lens_has_no_aberration_in_opd_and_seidel():
    for sysm, fields in ((_lens(), (0.0, 3.0)), (_lens(object_mm=200.0), (0.0, 3.0))):
        for fl in fields:
            _, _, w, v = RT.opd_samples(sysm, field=fl, size=33)
            assert float(np.nanmax(np.abs(w[v]))) < 1e-8, (fl, sysm["object_mm"])
    tot = RT.seidel_coefficients(_lens())["total"]
    assert all(abs(v) < 1e-12 for v in tot.values())


def test_afocal_conjugate_is_collimated_and_equal_path():
    sysm = _lens(object_mm=F)                                         # object on the focal plane
    assert RT.paraxial_trace(sysm)["efl"] == pytest.approx(F)
    py = np.linspace(-0.2, 0.2, 9) * 10.0
    P = np.array([[0.0, 0.0, -F]] * 9)
    D = np.stack([np.zeros(9), py / F, np.full(9, F)], 1)
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    # rays from the on-axis object point at several angles: the output is a plane wave along +z
    D = np.stack([np.zeros(9), np.linspace(-0.2, 0.2, 9), np.ones(9)], 1)
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    tr = RT.trace_rays(sysm, P, D, image_mm=300.0)
    out = tr["dirs"][:, -1, :]
    assert np.max(np.abs(out - [0.0, 0.0, 1.0])) < 1e-12              # collimated, parallel to the axis
    assert np.ptp(tr["opl"]) < 1e-10                                  # equal optical path to a plane


def test_quadratic_phase_is_the_small_height_limit():
    """The path the lens adds is  -h^2/(2f)  at small h (and exactly f - sqrt(h^2 + f^2) on axis)."""
    h = np.array([0.05, 0.2, 1.0])
    P0 = np.array([[x, 0.0, -5.0] for x in h])
    D0 = np.tile([0.0, 0.0, 1.0], (3, 1))
    Q = np.array([[x, 0.0, 0.0] for x in h])
    phi = RT._ideal_phase(P0, D0, Q, F, 1.0)
    assert np.allclose(phi, F - np.sqrt(h ** 2 + F ** 2), atol=1e-15)
    assert abs(phi[0] - (-h[0] ** 2 / (2 * F))) < 1e-8


def test_a_wrong_sign_turns_the_focus_gate_red():
    good = _crossing_error(_lens(f=F), [2.0, 5.0])
    assert good < 1e-12
    # the gate checks the crossing against +f; a lens built with the wrong sign fails it by 2 f
    bad = _crossing_error(_lens(f=-F), [2.0, 5.0], expect=F)
    assert bad > 1.5 * F


def test_a_wrong_conjugate_turns_the_imaging_gate_red():
    sysm = _lens(object_mm=200.0, field=2.0)
    wrong = dict(sysm)
    wrong["image_mm"] = F                                             # focus for an object at infinity
    st = RT.spot_stats(wrong, field=2.0, image_mm=F)
    assert st["rms_radius"] > 1e-3


def test_ideal_lens_input_validation():
    with pytest.raises(ValueError, match="f != 0"):
        RT.lens_system([{"f": 0.0, "t": None, "ap": 5}])
    with pytest.raises(ValueError, match="no radius"):
        RT.lens_system([{"f": 50.0, "R": 40.0, "t": None, "ap": 5}])
    with pytest.raises(ValueError, match="mirror"):
        RT.lens_system([{"f": 50.0, "mirror": True, "t": None, "ap": 5}])
    with pytest.raises(ValueError, match="one medium"):
        RT.lens_system([{"f": 50.0, "n": 1.5, "t": None, "ap": 5}])
    with pytest.raises(ValueError):
        RT.lens_system([{"f": float("nan"), "t": None, "ap": 5}])
    with pytest.raises(ValueError):
        RT.lens_system([{"f": float("inf"), "t": None, "ap": 5}])


def test_rebuilding_a_system_keeps_the_ideal_lens():
    sysm = _lens()
    again = RT.lens_system(sysm["surfaces"], stop=sysm["stop"], object_mm=sysm["object_mm"])
    assert again["surfaces"][0]["f"] == F
    other = RT.with_wavelength(sysm, 0.4861)
    assert other["surfaces"][0]["f"] == F


def test_section_drawing_shows_a_thin_line_with_arrowheads():
    for f, outward in ((F, True), (-F, False)):
        sysm = RT.lens_system([{"f": f, "t": 50.0, "ap": 10.0}, {"R": "inf", "t": None, "n": 1.0}], stop=0)
        d = OD.lens_section_drawing(sysm)
        tags = [e.get("tag") for e in d["entities"]]
        line = [e for e in d["entities"] if e.get("tag") == "surface:0"][0]
        assert line["layer"] == "THIN"
        ys = sorted(p[1] for p in line["points"])
        assert ys[0] == pytest.approx(-10.0) and ys[-1] == pytest.approx(10.0)
        arrows = [e for e in d["entities"] if e["type"] == "polyline" and e.get("tag") == "arrow"
                  and e["layer"] == "THIN"]
        assert len(arrows) == 2, tags
        for a in arrows:                                               # points[0] is the tip, the other two the base
            tip_y, base_y = abs(a["points"][0][1]), abs(0.5 * (a["points"][1][1] + a["points"][2][1]))
            assert (tip_y > base_y) == outward                         # converging: heads point away from the axis
            assert max(tip_y, base_y) == pytest.approx(10.0, abs=1e-9)
        assert d["values"]["surfaces"][0]["f"] == f


def test_ideal_lens_in_psf_is_airy_with_unit_strehl():
    import lensimage as LI
    sysm = _lens(ap=5.0)                                              # f/5
    psf = LI.psf_from_opd(sysm, size=64, oversample=8)
    ref = LI._psf_core(sysm, size=64, oversample=8)
    assert abs(ref[0].max() / ref[1].max() - 1.0) < 1e-6              # same peak as the unaberrated pupil
    assert psf.shape[0] == psf.shape[1] and abs(psf.sum() - 1.0) < 1e-12
