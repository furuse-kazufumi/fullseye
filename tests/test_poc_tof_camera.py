"""PoC 2026.274 の場面真値と独立な閉形式の門。"""

import numpy as np

from examples import poc_tof_camera as P


def test_scene_truth_contains_all_inspection_targets_and_two_bounce_paths():
    scene = P.make_scene(48, 72)
    assert scene["depth"].shape == (48, 72)
    assert scene["path_depths"].shape[0] >= 2
    assert scene["path_depths"].shape[1:] == scene["depth"].shape
    assert set(np.unique(scene["labels"])) >= {0, 1, 2, 3, 4, 5}
    assert np.allclose(scene["path_depths"][0], scene["depth"])


def test_plane_ray_distance_matches_the_closed_form_and_broken_probe_fails():
    scene = P.make_scene(48, 72)
    yy, xx = np.indices(scene["depth"].shape)
    ray_z = 1.0 / np.sqrt(1.0 + scene["ray_x"] ** 2 + scene["ray_y"] ** 2)
    plane = scene["labels"] == 0
    expected = P.WALL_Z / ray_z
    assert int(plane.sum()) > 100
    assert float(np.max(np.abs(scene["depth"][plane] - expected[plane]))) < 1e-12
    broken = P.WALL_Z * np.ones_like(expected)
    assert float(np.max(np.abs(broken[plane] - expected[plane]))) > 0.01


def test_volume_closed_form_is_independent_of_camera_estimators():
    scene = P.make_scene(48, 72)
    truth = P.measure_box_volumes(scene["depth"], scene)
    assert len(truth) == 3
    assert np.allclose(truth, P.BOX_VOLUMES_M3, rtol=0.08)
