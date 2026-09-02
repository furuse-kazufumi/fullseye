"""Ground-truth tests for PPF 6-DoF surface matching (ppf.py).

The scene is a known rigid transform of the model (an asymmetric ellipsoid with
distinct semi-axes, so its pose is unique — no rotational symmetry), so the
recovered (R, t) is checked against the exact transform used to build it."""
import numpy as np
import pytest

import ppf
import camera
import registration


def _ellipsoid(n=260, a=1.0, b=0.7, c=0.5, seed=0):
    """Points on an ellipsoid surface with exact outward unit normals."""
    rng = np.random.default_rng(seed)
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    P = d * np.array([a, b, c])                       # surface point
    N = P / np.array([a, b, c]) ** 2                  # gradient of x^2/a^2+... = normal
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    return P, N


def test_surface_match_recovers_known_pose():
    P, N = _ellipsoid(seed=1)
    R_true = camera.rodrigues([0.4, -0.6, 0.3])
    t_true = np.array([2.0, -1.0, 0.5])
    rng = np.random.default_rng(2)
    S = P @ R_true.T + t_true + rng.normal(0, 0.004, P.shape)
    SN = N @ R_true.T                                  # normals rotate with the body

    model = ppf.ppf_model(P, N, angle_bins=24)
    res = ppf.surface_match(model, S, SN, ref_fraction=0.4, topk=6, seed=3)

    # pose maps model -> scene; check it explains the scene
    moved = registration.apply_transform(P, res["R"], res["t"])
    assert res["inlier_fraction"] > 0.9
    assert res["rmse"] < 0.05
    ang = np.degrees(np.linalg.norm(camera.rotation_log(res["R"] @ R_true.T)))
    assert ang < 5.0
    assert np.linalg.norm(res["t"] - t_true) < 0.05
    assert np.allclose(moved.mean(0), S.mean(0), atol=0.05)


def test_find_surface_pose_one_shot_identity():
    # model matched against itself -> identity pose (sanity of the one-shot path)
    P, N = _ellipsoid(n=200, seed=5)
    res = ppf.find_surface_pose(P, P, N, N, ref_fraction=0.3, topk=4, seed=0)
    assert res["inlier_fraction"] > 0.95
    ang = np.degrees(np.linalg.norm(camera.rotation_log(res["R"])))
    assert ang < 3.0
    assert np.linalg.norm(res["t"]) < 0.05


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_voting_alone_recovers_random_so3_pose(seed):
    """Regression (2026-09-02): the vote used ``alpha_s - alpha_m``; the aligning
    rotation is ``Rx(alpha_m - alpha_s)`` (T = Ts^-1 Rx(a) Tm), so pure voting
    (refine=False) was 27-169 deg off on random rotations and even ICP refine
    could not recover 2 of 4. Pure voting must now land within the angular
    quantisation (2 bins) and ICP refine must finish below 1 deg."""
    from scipy.spatial.transform import Rotation
    P, N = _ellipsoid(seed=10 + seed)
    R_true = Rotation.random(random_state=seed).as_matrix()
    t_true = np.random.default_rng(seed).normal(size=3)
    S = P @ R_true.T + t_true
    SN = N @ R_true.T                                   # exact normals
    bins = 30
    res = ppf.find_surface_pose(P, S, N, SN, angle_bins=bins, ref_fraction=0.2,
                                topk=5, refine=False, seed=seed)
    ang = np.degrees(np.linalg.norm(camera.rotation_log(res["R"].T @ R_true)))
    assert ang < 2.0 * (180.0 / bins), f"vote-only rotation error {ang:.2f} deg"
    res = ppf.find_surface_pose(P, S, N, SN, angle_bins=bins, ref_fraction=0.2,
                                topk=5, refine=True, seed=seed)
    ang = np.degrees(np.linalg.norm(camera.rotation_log(res["R"].T @ R_true)))
    assert ang < 1.0, f"refined rotation error {ang:.3f} deg"
    assert np.linalg.norm(res["t"] - t_true) < 0.02


def test_ppf_model_builds_table():
    P, N = _ellipsoid(n=80, seed=7)
    model = ppf.ppf_model(P, N, angle_bins=20)
    assert model["points"].shape == (80, 3)
    assert len(model["table"]) > 0
    assert model["dist_step"] > 0


def test_surface_match_rejects_too_small():
    with pytest.raises(ValueError):
        ppf.ppf_model(np.zeros((3, 3)))
