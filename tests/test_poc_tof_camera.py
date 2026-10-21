"""ToF camera PoC composability and physical-scene gates."""

import numpy as np

from examples import poc_tof_camera as P


def test_scene_truth_contains_all_ray_cast_targets():
    scene = P.make_scene(48, 72)
    assert scene["depth"].shape == (48, 72)
    assert scene["path_depths"].shape == (2, 48, 72)
    assert set(np.unique(scene["labels"])) >= {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}


def test_chained_facade_call_needs_no_conversion():
    scene = P.make_scene(48, 72)
    filtered, points = P.depth_to_points_chain(scene["depth"])
    assert filtered.shape == scene["depth"].shape
    assert points.shape == (48 * 72, 3)
    assert np.isfinite(points).all()


def test_volume_measurement_is_stable_on_truth():
    scene = P.make_scene(80, 108)
    truth = P.measure_box_volumes(scene["depth_truth"], scene)
    assert truth.shape == (3,)
    assert np.all(truth > 0)
