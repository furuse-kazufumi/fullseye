# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Real-ray pupil aiming and vignetting factors of ``raytrace`` -- gates with values that do not go through the code.

* Aiming (``aim="stop"``): every pupil ray of the stock Cooke triplet crosses the stop surface at its own
  point, within 1e-11 of the stop radius (the paraxial launch loses 48 of 217 on axis); a thin ideal lens
  has no pupil aberration, so aiming changes nothing (1e-12); the chief ray still hits the stop centre.
* Vignetting factors VDX / VDY / VCX / VCY / VAN: the pupil on the stop is the compressed, decentred
  ellipse (measured from the traced rays); zero factors reproduce the old results bit for bit; the
  factors survive the ``.zmx`` round trip; a diffraction-limited lens with VCY = 0.3 has the textbook
  circular-pupil MTF along x and the same curve with the cutoff scaled by 0.7 along y.
* ``set_vignetting``: after setting, no ray of the grid is clipped; a system with nothing clipped gets 0.

The probes break each gate on purpose and require it to go red.
"""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import lensfile as LF  # noqa: E402
import lensimage as LI  # noqa: E402
import optics as O  # noqa: E402
import raytrace as RT  # noqa: E402

FIELDS = (0.0, 14.0, 20.0)


def _triplet():
    return LF.lens_file_read(None)["system"]


def _clipped_triplet():
    """The triplet with semi-apertures on the lens surfaces that clip off-axis rays."""
    s = _triplet()
    surf = [dict(x) for x in s["surfaces"]]
    for i, a in {0: 8.5, 1: 8.0, 2: 4.0, 4: 6.4, 5: 6.8}.items():
        surf[i]["ap"] = a
    return RT.lens_system(surf, stop=s["stop"], object_mm=s["object_mm"], wavelength_um=s["wavelength_um"],
                          image_mm=s["image_mm"])


# --------------------------------------------------------------------------- aiming
def test_default_launch_is_unchanged_and_loses_48_of_217_on_axis():
    s = _triplet()
    assert s["aim"] == "paraxial" and s["vignetting"] == ()
    b = RT.ray_bundle(s, field=0.0, rings=8)
    assert len(b["valid"]) == 217 and int((~b["valid"]).sum()) == 48
    st = RT.spot_stats(s, field=0.0)
    assert st["rms_radius"] == pytest.approx(5.068491343253448e-03, rel=1e-13)      # the value before this change


@pytest.mark.parametrize("field", FIELDS)
def test_every_ray_of_the_217_grid_reaches_the_stop_within_tolerance(field):
    s = _triplet()
    b = RT.ray_bundle(s, field=field, rings=8, aim="stop")
    ap = s["surfaces"][s["stop"]]["ap"]
    assert len(b["valid"]) == 217 and bool(b["valid"].all())
    want = b["pupil"] * ap
    assert float(np.max(np.hypot(*(b["stop_xy"] - want).T))) / ap < 1e-11
    assert b["aim_residual"] < 1e-11
    a = RT.ray_aiming(s, field=field)
    assert a["n_pass_stop"] == 217 and a["n_lost"] == 0
    assert a["stop_y"][1] == pytest.approx(1.0, abs=1e-11) and a["stop_y"][0] == pytest.approx(-1.0, abs=1e-11)


def test_probe_paraxial_aiming_fails_the_same_gate():
    s = _triplet()
    a = RT.ray_aiming(s, field=0.0, aim="paraxial")
    assert a["n_pass_stop"] == 169 and a["n_lost"] == 48 and a["max_residual"] is None


def test_system_level_aim_is_used_by_spot_fan_opd_and_chief():
    s = RT.with_aiming(_triplet(), "stop")
    assert s["aim"] == "stop"
    assert RT.spot_stats(s, field=0.0)["n_vignetted"] == 0
    assert RT.spot_stats(s, field=0.0)["rms_radius"] == pytest.approx(
        RT.spot_stats(_triplet(), field=0.0, aim="stop")["rms_radius"], rel=1e-12)
    fan = RT.ray_fan(s, field=14.0, n=21)
    assert np.isfinite(fan).all()                                  # the rim of the fan is no longer lost
    assert not np.isfinite(RT.ray_fan(_triplet(), field=0.0, n=21)).all()
    _px, _py, _w, valid = RT.opd_samples(s, field=0.0, size=33)
    _px, _py, _w0, valid0 = RT.opd_samples(_triplet(), field=0.0, size=33)
    assert valid.sum() > valid0.sum()
    assert RT.with_aiming(s, "paraxial")["aim"] == "paraxial"
    with pytest.raises(ValueError):
        RT.with_aiming(s, "bogus")


@pytest.mark.parametrize("field", (0.0, 14.0, 20.0))
def test_chief_ray_still_hits_the_stop_centre(field):
    s = RT.with_aiming(_triplet(), "stop")
    c = RT.chief_ray(s, field=field)
    sc = RT.chief_ray(_triplet(), field=field)
    assert c["valid"]
    tr = RT.trace_rays(s, *RT._launch_aimed(s, [0.0], [0.0], field, RT._para_at(s))[:2])
    assert float(np.hypot(*RT._stop_xy(s, tr)[0])) < 1e-11 * s["surfaces"][s["stop"]]["ap"]
    assert c["image_y"] == pytest.approx(sc["image_y"], abs=1e-9)


def test_thin_ideal_lens_aiming_changes_nothing():
    for obj in (RT.INF, 300.0):
        s = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0, object_mm=obj)
        fld = 3.0 if obj == RT.INF else 4.0
        a = RT.ray_bundle(s, field=fld, rings=6, aim="paraxial")
        b = RT.ray_bundle(s, field=fld, rings=6, aim="stop")
        assert float(np.nanmax(np.abs(a["image_xy"] - b["image_xy"]))) < 1e-12
        assert bool(a["valid"].all()) and bool(b["valid"].all())
    # an ideal lens in front of a stop behind it: the tan-law makes the stop an exact image of the pupil
    s = RT.lens_system([{"f": 40.0, "t": 10.0, "ap": 8.0}, {"R": RT.INF, "t": None, "n": 1.0, "ap": 3.0}], stop=1)
    a = RT.ray_bundle(s, field=5.0, rings=5, aim="paraxial")
    b = RT.ray_bundle(s, field=5.0, rings=5, aim="stop")
    assert float(np.nanmax(np.abs(a["image_xy"] - b["image_xy"]))) < 1e-9


def test_aiming_is_fail_closed_when_the_stop_cannot_be_reached():
    s = RT.with_aiming(_triplet(), "stop")
    with pytest.raises(ValueError, match="aiming did not converge|not converge"):
        RT.spot_stats(s, field=80.0)
    with pytest.raises(ValueError):
        RT.ray_bundle(s, field=0.0, aim="nope")


# --------------------------------------------------------------------------- vignetting factors
def test_zero_vignetting_reproduces_todays_results_exactly():
    base = _triplet()
    zero = RT.lens_system([dict(x) for x in base["surfaces"]], stop=base["stop"], object_mm=base["object_mm"],
                          wavelength_um=base["wavelength_um"], image_mm=base["image_mm"],
                          vignetting=[{"field": f} for f in FIELDS])
    for aim in ("paraxial", "stop"):
        for f in FIELDS:
            a = RT.ray_bundle(base, field=f, aim=aim)
            b = RT.ray_bundle(zero, field=f, aim=aim)
            assert np.array_equal(a["image_xy"], b["image_xy"], equal_nan=True)
            assert b["vignetting"] is None


def test_vcy_compresses_the_pupil_on_the_stop_to_0_7():
    s = _triplet()
    full = RT.ray_aiming(s, field=14.0, aim="stop", vignetting={})
    v = RT.ray_aiming(s, field=14.0, aim="stop", vignetting={"vcy": 0.3})
    ext = lambda a: a["stop_y"][1] - a["stop_y"][0]                  # noqa: E731
    assert ext(v) / ext(full) == pytest.approx(0.7, abs=1e-10)
    assert (v["stop_x"][1] - v["stop_x"][0]) / (full["stop_x"][1] - full["stop_x"][0]) == pytest.approx(1.0, abs=1e-10)
    assert v["n_lost"] == 0


def test_decentre_and_rotation_follow_the_documented_formula():
    s = _triplet()
    a = RT.ray_aiming(s, field=0.0, aim="stop", vignetting={"vdy": 0.1, "vcy": 0.2, "vdx": -0.05, "vcx": 0.1})
    assert a["stop_y"] == pytest.approx((0.1 - 0.8, 0.1 + 0.8), abs=1e-10)
    assert a["stop_x"] == pytest.approx((-0.05 - 0.9, -0.05 + 0.9), abs=1e-10)
    # VAN = 90 swaps the compression axes: VCX = 0.3 then shrinks y
    b = RT.ray_aiming(s, field=0.0, aim="stop", vignetting={"vcx": 0.3, "van": 90.0})
    assert b["stop_y"] == pytest.approx((-0.7, 0.7), abs=1e-10) and b["stop_x"] == pytest.approx((-1.0, 1.0), abs=1e-10)
    # the forward and inverse maps are inverses
    v = {"vdx": 0.03, "vdy": -0.04, "vcx": 0.1, "vcy": 0.25, "van": 33.0}
    x, y = np.array([0.3, -0.7]), np.array([0.2, 0.5])
    x2, y2 = RT._vig_inverse(*RT._vig_forward(x, y, v), v)
    assert np.allclose(x2, x, atol=1e-14) and np.allclose(y2, y, atol=1e-14)


def test_table_lookup_exact_interpolated_and_clamped():
    s = RT.lens_system(RT.example_system("doublet")["surfaces"], stop=0,
                       vignetting=[{"field": 0.0}, {"field": 10.0, "vcy": 0.4, "vdy": 0.2}])
    assert RT._vig_at(s, 0.0) is None
    assert RT._vig_at(s, 10.0)["vcy"] == 0.4
    mid = RT._vig_at(s, 5.0)
    assert mid["vcy"] == pytest.approx(0.2) and mid["vdy"] == pytest.approx(0.1)
    assert RT._vig_at(s, 30.0)["vcy"] == 0.4                          # beyond the last record: nearest
    for bad in ([{"field": 0.0, "vcy": 1.0}], [{"field": 0.0, "vcy": -0.1}], [{"field": 0.0, "bogus": 1}],
                [{"field": 1.0}, {"field": 1.0}], {"field": 0.0}, [{"field": 0.0, "vdx": 2.0}],
                [{"field": 0.0, "vcx": float("nan")}]):
        with pytest.raises(ValueError):
            RT.lens_system(RT.example_system("doublet")["surfaces"], stop=0, vignetting=bad)


def test_spot_uses_the_vignetted_pupil_and_chief_stays_unvignetted():
    s = _triplet()
    plain = RT.ray_bundle(s, field=14.0, aim="stop", vignetting={})
    vig = RT.ray_bundle(s, field=14.0, aim="stop", vignetting={"vdy": 0.3, "vcy": 0.3})
    assert np.allclose(vig["chief_xy"], plain["chief_xy"], atol=1e-12)
    assert len(vig["valid"]) == 217 and vig["vignetting"]["vcy"] == 0.3
    assert RT.spot_stats(s, field=14.0, aim="stop", vignetting={"vcy": 0.3})["rms_radius"] != \
        RT.spot_stats(s, field=14.0, aim="stop", vignetting={})["rms_radius"]


# --------------------------------------------------------------------------- .zmx
def _with_factors():
    t = LF.ZMX_EXAMPLE
    old = "FWGN 1 1 1 1 1 1 1 1 1 1 1 1\n"
    assert t.count(old) == 1
    return t.replace(old, old + "VDXN 0 0 0 0 0 0 0 0 0 0 0 0\nVDYN 0 0.05 0.1 0 0 0 0 0 0 0 0 0\n"
                     "VCXN 0 0.1 0.2 0 0 0 0 0 0 0 0 0\nVCYN 0 0.3 0.4 0 0 0 0 0 0 0 0 0\n"
                     "VANN 0 0 0 0 0 0 0 0 0 0 0 0\n")


def test_zmx_round_trip_keeps_the_factors():
    p = LF.lens_file_read(_with_factors())
    f = p["fields"]
    assert (f[1]["vdy"], f[1]["vcx"], f[1]["vcy"]) == (0.05, 0.1, 0.3) and f[2]["vcy"] == 0.4
    assert not p["approximate"]
    text = LF.lens_file_write(p)["text"]
    assert "VCYN 0 0.3 0.4" in text and "VDYN 0 0.05 0.1" in text
    q = LF.lens_file_read(text)
    assert q["system"]["vignetting"] == p["system"]["vignetting"]
    assert [(g["vdx"], g["vdy"], g["vcx"], g["vcy"], g["van"]) for g in q["fields"]] == \
        [(g["vdx"], g["vdy"], g["vcx"], g["vcy"], g["van"]) for g in f]
    # a field system carries them, and they act
    s1 = LF.lens_file_system(p, field_index=1)
    assert RT._vig_at(s1, 14.0)["vcy"] == 0.3
    a = RT.ray_aiming(s1, field=14.0)
    assert a["stop_y"] == pytest.approx((0.05 - 0.7, 0.05 + 0.7), abs=1e-10)


def test_zmx_without_factors_writes_no_vignetting_lines_and_edits_follow_the_system():
    p = LF.lens_file_read(None)
    text = LF.lens_file_write(p)["text"]
    assert "VDXN" not in text and p["system"]["vignetting"] == ()
    s = RT.set_vignetting(_clipped_triplet(), fields=FIELDS)
    q = LF.lens_file_read(LF.lens_file_write(p, system=s)["text"])
    assert q["system"]["vignetting"] == tuple(r for r in s["vignetting"])


def test_zmx_off_meridian_factors_need_allow_partial_and_a_clash_is_refused():
    t = _with_factors().replace("XFLN 0 0 0 0 0 0 0 0 0 0 0 0", "XFLN 0 5 0 0 0 0 0 0 0 0 0 0")
    with pytest.raises(ValueError, match="off-meridian|allow_partial"):
        LF.lens_file_read(t)
    assert LF.lens_file_read(t, allow_partial=True)["approximate"]
    clash = _with_factors().replace("YFLN 0 14 20 0 0 0 0 0 0 0 0 0", "YFLN 0 14 14 0 0 0 0 0 0 0 0 0")
    with pytest.raises(ValueError, match="same radial field"):
        LF.lens_file_read(clash, allow_partial=True)


# --------------------------------------------------------------------------- set vignetting
@pytest.mark.parametrize("rings", (8, 12))
def test_set_vignetting_leaves_no_clipped_ray(rings):
    s = _clipped_triplet()
    before = {f: RT.ray_aiming(s, field=f, rings=rings, aim="stop", vignetting={})["n_lost"] for f in FIELDS}
    assert before[14.0] > 0 and before[20.0] > 0                      # the apertures do clip
    out = RT.set_vignetting(s, fields=FIELDS, rings=8)
    assert out["aim"] == "stop"
    for f in FIELDS:
        a = RT.ray_aiming(out, field=f, rings=8)
        assert a["n_lost"] == 0 and a["n_rays"] == 217
    # the factors are non-trivial exactly where rays were clipped
    rec = {r["field"]: r for r in out["vignetting"]}
    assert all(v == 0.0 for k, v in rec[0.0].items() if k != "field")
    assert rec[20.0]["vcy"] > 0.05 and rec[14.0]["vcy"] > 0.0


def test_set_vignetting_on_a_system_without_vignetting_is_zero_to_1e_9():
    for s in (_triplet(), RT.example_system("doublet")):
        out = RT.set_vignetting(s, fields=[0.0, 5.0])
        for r in out["vignetting"]:
            assert all(abs(r[k]) < 1e-9 for k in ("vdx", "vdy", "vcx", "vcy", "van"))


def test_set_vignetting_refuses_when_the_chief_ray_is_clipped():
    s = _clipped_triplet()
    surf = [dict(x) for x in s["surfaces"]]
    surf[0]["ap"] = 3.0
    tight = RT.lens_system(surf, stop=s["stop"], object_mm=s["object_mm"], wavelength_um=s["wavelength_um"],
                           image_mm=s["image_mm"])
    with pytest.raises(ValueError, match="chief ray is clipped"):
        RT.set_vignetting(tight, fields=[20.0])
    with pytest.raises(ValueError):
        RT.set_vignetting(s, fields=[])
    with pytest.raises(ValueError):
        RT.set_vignetting(s, fields="14")


def test_probe_the_unvignetted_clipped_system_would_fail_the_clip_gate():
    s = RT.with_aiming(_clipped_triplet(), "stop")
    assert RT.ray_aiming(s, field=20.0)["n_lost"] > 0


# --------------------------------------------------------------------------- spot / MTF consume the pupil
def test_mtf_of_a_vignetted_diffraction_limited_pupil_matches_the_ellipse_closed_form():
    lens = RT.lens_system([{"f": 50.0, "t": None, "ap": 2.5}], stop=0)
    lens = RT.with_aiming(lens, "stop", vignetting=[{"field": 0.0, "vcy": 0.3}])
    lam, N = lens["wavelength_um"], 10.0
    psf = LI.psf_from_opd(lens, size=160, oversample=4)
    M = (160 - 1) * 4
    M += M % 2
    dx = lam * N * 159 / M
    m = O.mtf_tangential_sagittal(psf, dx)
    cut = 1e3 / (lam * N)

    def circ(x):
        x = np.clip(x, 0.0, 1.0)
        return (2 / math.pi) * (np.arccos(x) - x * np.sqrt(1 - x * x))

    for key, scale in (("sagittal", 1.0), ("tangential", 0.7)):
        fr, mt = m[key][:, 0], m[key][:, 1]
        ref = circ(fr / (cut * scale))
        sel = fr < 1.2 * cut
        assert float(np.max(np.abs(mt[sel] - ref[sel]))) < 6e-3, key
    # probe: the unvignetted lens does not have the shortened tangential cutoff
    plain = RT.with_aiming(lens, "stop", vignetting=[])
    m0 = O.mtf_tangential_sagittal(LI.psf_from_opd(plain, size=160, oversample=4), dx)
    k = int(np.argmin(np.abs(m0["tangential"][:, 0] - 0.85 * cut)))
    assert m0["tangential"][k, 1] > 0.02 and m["tangential"][k, 1] < 0.005


def test_aimed_vignetted_opd_of_an_ideal_lens_is_zero_and_psf_runs_on_the_triplet():
    lens = RT.with_aiming(RT.lens_system([{"f": 50.0, "t": None, "ap": 2.5}], stop=0), "stop",
                          vignetting=[{"field": 0.0, "vdy": 0.2, "vcy": 0.3, "vcx": 0.1}])
    _px, _py, w, valid = RT.opd_samples(lens, field=0.0, size=48)
    assert valid.sum() > 200 and float(np.max(np.abs(w[valid]))) < 1e-6
    s = RT.with_aiming(_triplet(), "stop")
    psf = LI.psf_from_opd(s, field=14.0, size=64)
    assert psf.shape[0] == psf.shape[1] and abs(float(psf.sum()) - 1.0) < 1e-9


def test_registered_ops_exist_and_have_help():
    for name in ("with_aiming", "set_vignetting", "ray_aiming"):
        fn = getattr(RT, name)
        assert fn.__doc__ and len(fn.__doc__) > 100
