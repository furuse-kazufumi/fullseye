import inspect

import numpy as np

import fvbench as F
import fvbench_layer as L


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
    assert np.asarray(F.read_baseline2017(image.copy(), c)["force_N"]).shape == (3,)


def test_truth_is_not_on_estimator_path():
    assert "Truth" not in inspect.signature(F.read_tactile).parameters
    assert "Truth" not in inspect.signature(F.read_baseline).parameters
    src = inspect.getsource(F.read_tactile) + inspect.getsource(F.read_baseline)
    assert "truth" not in src.lower()


def test_public_formula_axes_percentile_and_affine_calibration():
    # Paper coordinates are [tangent-x, normal, tangent-y].  The 2016
    # aggregation discards the largest |.| 20 percent without losing sign.
    v = np.array([[-4., 1., 2.], [-3., 2., 1.], [-2., 3., 0.], [-1., 4., -1.], [99., 99., 99.]])
    got = F._aggregate_signed(v)
    assert np.allclose(got, [-2.5, 2.5, .5])
    c, _ = _calib()
    assert c.coef2016.shape == (2, 3) and c.coef2017.shape == (2, 3)
    # Both include a fitted intercept, not an origin-forced slope.
    assert np.isfinite(c.coef2016).all() and np.isfinite(c.coef2017).all()


def test_forward_model_does_not_use_estimator_coefficients():
    src = inspect.getsource(F._physical_displacement) + inspect.getsource(F.synthesize)
    assert "coef2016" not in src and "coef2017" not in src
    assert "layer.normal_kernel" in src and "_cerruti_point" in src


def test_bonded_layer_mesh_converges_and_near_incompressible_lateral_motion_survives():
    conv = L.convergence(.48)
    assert conv[-1][-1] < .03
    ratios = []
    for nu in (.40, .45, .48, .49, .499):
        r, ur, _ = L.axisymmetric_bonded_layer(nu, 96, 18)
        uh, _ = L.halfspace_normal(r, nu)
        ratios.append(np.max(np.abs(ur)) / np.max(np.abs(uh)))
    assert ratios[-1] > 20 * ratios[0]


def test_baselines_report_no_rotation_output_and_slip_tuning_budget_is_shared():
    c, ref = _calib()
    frames=[]
    for k,q in enumerate(np.linspace(0,1.2*F.MU*8,8)):
        frames.append((F.synthesize(F.Truth((q,0,8)),phase=k/2,seed=80+k),q>=F.MU*8))
    F.tune_slip_thresholds(c,frames,budget=11)
    assert F.read_baseline2016(ref,c)["angle_deg"] is None
    assert F.read_baseline2017(ref,c)["angle_deg"] is None
    assert np.isfinite([c.slip_threshold2016,c.slip_threshold2017,c.proposed_ca_threshold]).all()


def test_fixed_seed_is_repeatable_and_dark_failure_is_exposed():
    t = F.Truth((1, 0.5, 8))
    assert np.array_equal(F.synthesize(t, seed=7), F.synthesize(t, seed=7))
    c, _ = _calib()
    dark = F.synthesize(t, brightness=0.025, color="black", seed=8)
    assert F.read_tactile(dark, c)["matched"] < 6
