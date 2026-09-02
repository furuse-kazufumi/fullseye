# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Closed loop: designed lens → synthetic calibration views → calib.camera_calibration → K_true.

* Distortion-free lens (paraboloid mirror, stop on it): Zhang's method recovers
  fx = fy = EFL / pitch to 1e-6 relative and the principal point to 1e-6 px —
  the calibration module and the projection agree exactly when there is
  nothing to disagree about.
* Barrel-distorted singlet: the recovered focal length is biased (the fit
  absorbs the distortion), the reprojection RMS is non-zero, and both are
  larger than the paraboloid's — the numbers a real chart would show.
* Noise is deterministic per seed; every bad input is a ``ValueError``.
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import calib  # noqa: E402
import lensimage  # noqa: E402
import raytrace as RT  # noqa: E402


def _recover(v):
    k = calib.camera_calibration(v["object_points"], v["image_points"])
    return k


def test_distortion_free_lens_calibrates_exactly():
    v = lensimage.calibration_views(RT.example_system("paraboloid"), image_size=(800, 1000), pixel_pitch_um=5.0)
    assert v["n_views"] == 6 and all(f > 0.9 for f in v["visible_fraction"])
    assert abs(v["distortion"]["max_distortion_pct"]) < 1e-6
    k = _recover(v)
    fx_true = v["K_true"]["fx"]
    assert abs(k["fx"] - fx_true) / fx_true < 1e-6, (k["fx"], fx_true)
    assert abs(k["fy"] - fx_true) / fx_true < 1e-6
    assert abs(k["cx"] - v["K_true"]["cx"]) < 1e-5
    assert abs(k["cy"] - v["K_true"]["cy"]) < 1e-5
    assert max(k["reproj_rms"]) < 1e-6


def test_barrel_distortion_biases_the_focal_length_and_reprojection():
    sg = RT.lens_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5},
                         {"R": float("inf"), "t": None, "n": 1.0}], stop=0)
    # a wide sensor so the corners see real distortion (~-0.6 % at 15 deg)
    v = lensimage.calibration_views(sg, image_size=(2000, 3000), pixel_pitch_um=10.0)
    assert v["distortion"]["max_distortion_pct"] < -0.01
    k = _recover(v)
    clean = _recover(lensimage.calibration_views(RT.example_system("paraboloid"), image_size=(2000, 3000), pixel_pitch_um=10.0))
    bias = abs(k["fx"] - v["K_true"]["fx"]) / v["K_true"]["fx"]
    assert bias > 1e-5                                          # the distortion is visible ...
    assert bias < 0.02                                          # ... but Zhang is not wrecked by it
    assert max(k["reproj_rms"]) > 10 * max(clean["reproj_rms"])


def test_noise_is_deterministic_and_reported():
    sg = RT.example_system("doublet")
    a = lensimage.calibration_views(sg, noise_px=0.3, seed=3)
    b = lensimage.calibration_views(sg, noise_px=0.3, seed=3)
    c = lensimage.calibration_views(sg, noise_px=0.3, seed=4)
    assert all(np.array_equal(x, y) for x, y in zip(a["image_points"], b["image_points"]))
    assert not np.array_equal(a["image_points"][0], c["image_points"][0])
    assert a["noise_px"] == 0.3 and a["seed"] == 3
    k = _recover(a)
    assert abs(k["fx"] - a["K_true"]["fx"]) / a["K_true"]["fx"] < 0.02


def test_output_shapes_and_conventions():
    v = lensimage.calibration_views(RT.example_system("doublet"), target=(6, 4, 8.0))
    assert v["object_points"].shape == (24, 2)
    assert all(ip.shape == (24, 2) for ip in v["image_points"])
    # frontal pose: the target centre projects to the sensor centre (row, col)
    r, c = v["image_points"][0].mean(0)
    assert abs(r - v["K_true"]["cy"]) < 1e-9 and abs(c - v["K_true"]["cx"]) < 1e-9
    assert v["target"] == {"cols": 6, "rows": 4, "pitch_mm": 8.0}


@pytest.mark.parametrize("bad", [
    lambda s: lensimage.calibration_views({"x": 1}),
    lambda s: lensimage.calibration_views(s, target=(1, 4, 5.0)),
    lambda s: lensimage.calibration_views(s, target=(6, 4, 0.0)),
    lambda s: lensimage.calibration_views(s, poses=[(0, 0, 0, 0, 0, 100)]),           # < 3 views
    lambda s: lensimage.calibration_views(s, poses=[(0, 0, 0, 0, 0, -100)] * 3),      # behind the camera
    lambda s: lensimage.calibration_views(s, poses=[(0, 0, 0, 0, 0)] * 3),            # 5-tuple
    lambda s: lensimage.calibration_views(s, distance_mm=1.0),                        # target off the sensor
    lambda s: lensimage.calibration_views(s, noise_px=-1.0),
    lambda s: lensimage.calibration_views(s, image_size=(0, 10)),
])
def test_invalid_inputs_are_value_errors(bad):
    s = RT.example_system("doublet")
    with pytest.raises(ValueError):
        bad(s)
