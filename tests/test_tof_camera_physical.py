"""Physical rendering gates for the ToF camera exhibit."""

import numpy as np

from examples.tof_camera_physical import C, make_stages, render_scene


def test_scene_is_ray_cast_at_320_by_240_with_required_targets():
    scene = render_scene(240, 320, noisy=False)
    assert scene["depth"].shape == (240, 320)
    assert set(np.unique(scene["labels"])) >= {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
    assert float(np.ptp(scene["depth_truth"])) > 2.0
    assert float(np.ptp(scene["reflectivity"])) > 0.6


def test_nine_subrays_create_phasor_mixed_edge_pixels():
    scene = render_scene(80, 108, noisy=False)
    mixed = scene["edge_mix"] > 0.01
    assert int(mixed.sum()) > 30
    assert float(np.max(scene["edge_mix"])) > 0.08


def test_falloff_noise_and_multipath_are_discriminative():
    ideal, falloff, noisy, full = make_stages(60, 80)
    assert np.corrcoef(falloff["signal"].ravel(), falloff["depth_truth"].ravel())[0, 1] < -0.25
    assert float(np.std(noisy["depth"] - noisy["clean_depth"])) > 0.001
    corner = full["mpi_ratio"] > 0.10
    assert int(corner.sum()) > 20
    assert float(np.median(full["depth"][corner] - noisy["depth"][corner])) > 0.005


def test_single_frequency_wraps_at_the_closed_form_range():
    scene = render_scene(48, 64, noisy=False, frequency_hz=20e6)
    ambiguity = C / (2 * 20e6)
    assert float(scene["depth"].max()) < ambiguity
    assert np.allclose(scene["depth"], np.mod(scene["depth"], ambiguity))
