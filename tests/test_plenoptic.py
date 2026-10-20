"""Closed-form and broken-probe gates for the prescription-based plenoptic camera."""
import math
import numpy as np
import pytest

import lensrender as LR
import lightfield as LF
import plenoptic as P
import raytrace as RT


def _lens(object_mm=1000.0, f=50.0, ap=5.0):
    return RT.lens_system([{"f": f, "t": None, "ap": ap}], stop=0, object_mm=object_mm)


def _system(ratio=1.0, size=(45, 45), rotation=False):
    main = _lens()
    pitch = 0.15
    nmain = 5.0
    mla = P.mla_surface(pitch, 0.75, (3, 3), f_number=nmain*ratio)
    sensor = {"size": size, "pixel_pitch_um": 10.0}
    return P.plenoptic_system(main, mla, sensor)


def test_f_number_matching_closed_form_and_mismatch_probe():
    matched = _system()
    assert abs(matched["microimage_diameter_mm"] / matched["mla"]["pitch_mm"] - 1) < 1e-12
    assert matched["gap_fraction"] == 0 and matched["overlap_fraction"] == 0
    mismatch = _system(1.5)
    assert abs(mismatch["overlap_fraction"] - 0.5) < 1e-12
    assert mismatch["gap_fraction"] == 0
    assert mismatch["f_number_ratio"] == pytest.approx(1.5)
    broken = dict(mismatch); broken["main_f_number"] *= 1.1
    assert broken["main_f_number"] != pytest.approx(mismatch["main_f_number"])


def test_mla_sag_normal_indices_and_boundary_fail_closed():
    m = P.mla_surface(1.0, 4.0, (3, 3), f_number=4.0)
    q = P.mla_sag_normal(m, [[0, 0], [0.25, 0], [1.1, -0.1]])
    assert q["lenslet_index"].shape == (3, 2)
    assert np.array_equal(q["lenslet_index"], [[0, 0], [0, 0], [0, 1]])
    expected = 4-math.sqrt(16-0.25**2)
    assert q["sag_mm"][1] == pytest.approx(expected, abs=1e-14)
    with pytest.raises(ValueError, match="boundary"):
        P.mla_sag_normal(m, [[0.5, 0]])
    hit = LR._intersect_mla_surface(m, [[0.25, 0, 1]], [[0, 0, -1]])
    assert hit["valid"].sum() == 1
    assert hit["point_mm"][0, 2] == pytest.approx(expected, abs=1e-12)


def test_capture_records_pixel_to_pupil_truth():
    sys = _system(size=(31, 31))
    scene = LR.lens_scene([{"type":"plane", "z_mm":-1000, "albedo":0.5}],
                          [{"type":"directional", "to_light":(0,0,1), "irradiance_W_m2_nm":1}])
    cap = P.plenoptic_capture(sys, scene, pupil_samples=1)
    assert cap["raw"].shape == (31, 31)
    assert cap["pupil_uv"].shape == (31, 31, 2)
    assert cap["lenslet_index"].shape == (31, 31, 2)
    assert cap["valid"].sum() > 100
    assert np.all(cap["white_image"][~cap["valid"]] == 0)
    assert np.all(np.isfinite(cap["pupil_uv"]))


def test_decode_exact_aligned_matches_existing_decode():
    rng=np.random.default_rng(2)
    lf=rng.random((5,5,4,4)); raw=LF.lf_to_mla(lf)
    # Centres are at block centres, basis vectors are one microimage pitch.
    cal={"origin_px":np.array([2.,2.]), "basis_px":np.array([[5.,0.],[0.,5.]]),
         "white_image":np.ones_like(raw)}
    got=P.plenoptic_decode(raw,cal,angular=(5,5))["lightfield"]
    assert got.shape == lf.shape
    assert np.max(np.abs(got-lf)) < 1e-12


def test_calibration_recovers_rotation_and_rejects_wrong_pitch_probe():
    h=w=101; yy,xx=np.indices((h,w)); p=15.; th=math.radians(0.5)
    e0=np.array([math.cos(th),math.sin(th)])*p; e1=np.array([-math.sin(th),math.cos(th)])*p
    white=np.zeros((h,w))
    for j in range(-4,5):
        for i in range(-4,5):
            x,y=np.array([50.,50.])+i*e0+j*e1
            white += np.exp(-((xx-x)**2+(yy-y)**2)/(2*1.2**2))
    cal=P.plenoptic_mla_calibrate(white,p,max_residual_px=0.25)
    assert cal["centres"].shape[0] >= 25
    assert abs(abs(cal["rotation_deg"])-0.5) < 0.02
    assert abs(cal["pitch_px"]-p) < 0.03
    with pytest.raises(ValueError):
        P.plenoptic_mla_calibrate(white,p*1.01,max_residual_px=1e-4)


def test_refocus_depth_has_true_conjugate_at_zero_and_finite_resolution():
    sys=_system(); lf=np.zeros((5,5,3,3))
    out=P.plenoptic_refocus_depth(lf,sys,np.array([-1.,0.,1.]))
    assert out["depth_m"].shape == (3,)
    assert out["depth_m"][1] == pytest.approx(1.0, rel=1e-12)
    assert np.all(out["depth_resolution_m"] > 0)
    bad=dict(sys); bad["mla_to_sensor_mm"] *= 1.01
    probe=P.plenoptic_refocus_depth(lf,bad,1.)["depth_m"]
    assert probe != pytest.approx(out["depth_m"][2], rel=1e-6)


def test_focused_conjugates_and_magnification_closed_form():
    main=_lens(); mla=P.mla_surface(.15,.75,(3,3),f_number=5.)
    sys=P.plenoptic_system(main,mla,{"size":(45,45),"pixel_pitch_um":10},kind="focused",
                            mla_to_sensor_mm=1.5,main_to_mla_mm=1.5)
    assert 1/sys["mla_focal_mm"] == pytest.approx(1/1.5+1/1.5)
    assert sys["magnification"] == pytest.approx(1.0)
