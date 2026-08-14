"""Ground-truth tests for scene flow / ego-motion (sceneflow.py).

Flow fields are built analytically (pure expansion, pure rotation, known FoE) and
the stereo+flow scene-flow case is a rigid translation of a plane, so divergence,
curl, FoE, time-to-contact, heading and 3-D motion all have exact expected values."""
import numpy as np

import sceneflow


def _grid(H=60, W=80):
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    return xx, yy


def test_divergence_of_pure_expansion():
    xx, yy = _grid()
    s = 0.03
    u = s * (xx - 40.0)
    v = s * (yy - 30.0)
    div = sceneflow.flow_divergence(u, v)
    assert np.allclose(div[2:-2, 2:-2], 2 * s, atol=1e-9)      # div = 2s everywhere


def test_curl_of_pure_rotation():
    xx, yy = _grid()
    w = 0.02
    u = -w * (yy - 30.0)
    v = w * (xx - 40.0)
    curl = sceneflow.flow_curl(u, v)
    assert np.allclose(curl[2:-2, 2:-2], 2 * w, atol=1e-9)     # curl = 2w
    assert np.allclose(sceneflow.flow_divergence(u, v)[2:-2, 2:-2], 0.0, atol=1e-9)


def test_focus_of_expansion_recovers_center():
    xx, yy = _grid()
    x0, y0 = 52.0, 21.0
    u = 0.05 * (xx - x0)
    v = 0.05 * (yy - y0)
    foe = sceneflow.focus_of_expansion(u, v)
    assert np.allclose(foe, (x0, y0), atol=1e-6)


def test_time_to_contact_uniform_expansion():
    xx, yy = _grid()
    s = 0.04                                            # expansion rate -> TTC = 1/s
    u = s * (xx - 40.0)
    v = s * (yy - 30.0)
    tau = sceneflow.time_to_contact(u, v, foe=(40.0, 30.0))
    core = tau[10:-10, 10:-10]
    core = core[np.isfinite(core)]
    assert np.allclose(core, 1.0 / s, atol=1e-6)


def test_looming_sign():
    xx, yy = _grid()
    approach = sceneflow.looming(0.03 * (xx - 40), 0.03 * (yy - 30))
    recede = sceneflow.looming(-0.03 * (xx - 40), -0.03 * (yy - 30))
    assert approach["expanding"] and approach["mean_divergence"] > 0
    assert np.isfinite(approach["ttc"]) and approach["ttc"] > 0
    assert not recede["expanding"] and recede["mean_divergence"] < 0
    assert recede["ttc"] == float("inf")


def test_ego_translation_forward_and_tilted():
    import camera
    xx, yy = _grid()
    K = camera.intrinsic_matrix(400.0, 400.0, 40.0, 30.0)    # principal point = (40,30)
    # FoE at principal point -> heading straight down +z
    u = 0.05 * (xx - 40.0); v = 0.05 * (yy - 30.0)
    t = sceneflow.ego_translation_from_flow(u, v, K)
    assert np.allclose(t, [0.0, 0.0, 1.0], atol=1e-6)
    # FoE shifted +8 px in x -> heading tilts toward +x by dx/fx
    u2 = 0.05 * (xx - 48.0); v2 = 0.05 * (yy - 30.0)
    t2 = sceneflow.ego_translation_from_flow(u2, v2, K)
    expect = np.array([8.0 / 400.0, 0.0, 1.0]); expect /= np.linalg.norm(expect)
    assert np.allclose(t2, expect, atol=1e-6)


def test_scene_flow_recovers_lateral_translation():
    # a fronto-parallel plane at depth Z moving sideways by dx: disparity unchanged,
    # optical flow u = fx*dx/Z constant, and scene flow must recover (dx, 0, 0).
    H, W = 40, 50
    fx, baseline, Z, dx = 400.0, 0.1, 5.0, 0.2
    d = np.full((H, W), fx * baseline / Z)          # uniform disparity both frames
    u = np.full((H, W), fx * dx / Z)
    v = np.zeros((H, W))
    sf = sceneflow.scene_flow(d, d, u, v, fx=fx, baseline=baseline)
    core = sf[5:-5, 5:-5]                            # interior (flow stays in-frame)
    assert np.allclose(core[..., 0], dx, atol=1e-6)
    assert np.allclose(core[..., 1], 0.0, atol=1e-6)
    assert np.allclose(core[..., 2], 0.0, atol=1e-6)
