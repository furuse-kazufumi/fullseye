"""Measurement primitives on known inputs."""
import numpy as np

import measure


def test_line_profile_on_ramp_is_linear():
    ramp = np.tile(np.linspace(0, 1, 100), (10, 1))       # varies along columns
    prof = measure.line_profile(ramp, (5, 0), (5, 99))
    assert len(prof) == 100
    assert np.isclose(prof[0], 0, atol=1e-6) and np.isclose(prof[-1], 1, atol=1e-6)
    assert np.all(np.diff(prof) >= -1e-9)                  # monotincreasing


def test_line_profile_finds_step_edge():
    img = np.zeros((20, 40)); img[:, 20:] = 1.0            # a vertical step at col 20
    prof = measure.line_profile(img, (10, 0), (10, 39))
    st = measure.profile_stats(prof)
    assert abs(st["edge_at"] - 20) <= 1                    # edge located at the step


def test_distance_and_angle():
    assert np.isclose(measure.distance((0, 0), (3, 4)), 5.0)
    assert np.isclose(measure.angle((0, 0), (0, 5)), 0.0)      # horizontal
    assert np.isclose(measure.angle((0, 0), (5, 0)), 90.0)     # straight down


def test_color_profile_shape():
    img = np.zeros((8, 8, 3)); img[:, :, 0] = 1.0
    prof = measure.line_profile(img, (0, 0), (7, 7))
    assert prof.ndim == 2 and prof.shape[1] == 3
