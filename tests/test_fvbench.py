import inspect

import numpy as np

import fvbench as F


def _calib():
    ref = F.synthesize(F.Truth((0, 0, 0)), seed=1)
    rows = []
    for z in (2, 6, 12, 18):
        t = F.Truth((0.15*z, 0.08*z, z), torque_Nm=0.0002*z)
        rows.append((F.synthesize(t, seed=z), t.force_N, t.torque_Nm))
    return F.calibrate(rows, ref), ref


def test_same_image_enters_both_estimators_and_api_shape():
    c, _ = _calib()
    image = F.synthesize(F.Truth((2, 1, 10), slip=True), seed=22)
    a = F.read_baseline(image.copy(), c)
    c.previous = None
    b = F.read_tactile(image.copy(), c)
    assert np.asarray(a["force_N"]).shape == (3,)
    assert np.asarray(b["force_N"]).shape == (3,)
    assert {"torque", "slip", "slip_dir", "proximity"} <= b.keys()


def test_truth_is_not_on_estimator_path():
    assert "Truth" not in inspect.signature(F.read_tactile).parameters
    assert "Truth" not in inspect.signature(F.read_baseline).parameters
    src = inspect.getsource(F.read_tactile) + inspect.getsource(F.read_baseline)
    assert "truth" not in src.lower()


def test_fixed_seed_is_repeatable_and_dark_failure_is_exposed():
    t = F.Truth((1, 0.5, 8))
    assert np.array_equal(F.synthesize(t, seed=7), F.synthesize(t, seed=7))
    c, _ = _calib()
    dark = F.synthesize(t, brightness=0.025, color="black", seed=8)
    assert F.read_tactile(dark, c)["matched"] < 6
