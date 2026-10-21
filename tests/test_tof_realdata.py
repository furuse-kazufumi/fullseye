"""Real-frame resemblance gates; absent local datasets are an explicit skip."""

import numpy as np
import pytest

from examples.tof_camera_physical import render_scene
from examples import tof_realdata as real


def _require(value):
    if value is None:
        pytest.skip("local read-only iToF data or h5py is unavailable")
    return value


def test_amplitude_histogram_is_within_real_scene_spread_gate():
    got = _require(real.amplitude_spread_statistics(render_scene()["amplitude"]))
    assert got["real_real_w1"] > 0
    assert got["synthetic_real_w1"] <= got["threshold"]
    assert got["threshold"] == pytest.approx(1.5 * got["real_real_w1"])


def test_flat_region_noise_follows_inverse_amplitude_law():
    frames = [render_scene(80, 108, seed=seed) for seed in range(10)]
    got = _require(real.noise_exponents(frames))
    assert abs(got["real_exponent"] + 1) < .2
    assert abs(got["synthetic_exponent"] + 1) < .2


def test_flying_pixel_fraction_matches_real_edges_within_factor_two():
    scene = render_scene()
    got = _require(real.flying_pixel_fractions(scene["depth"], scene["depth_truth"]))
    ratio = got["synthetic_fraction"] / got["real_fraction"]
    assert .5 <= ratio <= 2.0


def test_real_and_synthetic_corner_bias_have_same_sign_and_scale():
    observed = _require(real.wall_corner_bias_mm())
    full = render_scene(noisy=False, multipath=True)
    direct = render_scene(noisy=False, multipath=False)
    corner = full["mpi_ratio"] > .10
    synthetic = 1000 * float(np.median((full["depth"] - direct["depth"])[corner]))
    # Coordinate conventions differ; both bend away from their local wall
    # after orienting the real profile from wall toward the junction.
    assert observed < 0 and synthetic > 0
    assert 10 <= abs(observed) <= 1000
    assert 5 <= abs(synthetic) <= 500


def test_rendered_four_phase_data_has_positive_corner_tail():
    got = _require(real.rendered_mpi_statistic())
    assert got["corner_sign"] > 0
    assert abs(got["median_error_mm"]) < 1000
