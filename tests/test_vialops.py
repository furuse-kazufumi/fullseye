"""Truth checks for the vial spin-stop simulator and projected-object tracker."""
from __future__ import annotations

import numpy as np

from vialops import track_moving_particles, vial_spin_stop_sequence


def _object_rows(truth, kind):
    return truth["row_px"][truth["object_type"] == kind]


def test_spin_stop_is_seed_reproducible_and_angular_speed_decays():
    frames_a, truth_a = vial_spin_stop_sequence(seed=71)
    frames_b, truth_b = vial_spin_stop_sequence(seed=71)
    assert np.array_equal(frames_a, frames_b)
    assert np.array_equal(truth_a["row_px"], truth_b["row_px"])
    assert np.all(np.diff(truth_a["omega_rad_s"]) < 0.0)


def test_heavier_particle_settles_faster_than_light_particle():
    common = dict(seed=12, initial_omega_rad_s=0.0, n_bubbles=0, n_scratches=0,
                  particle_diameter_um=120.0, n_frames=20, noise_sigma=0.0)
    _, light = vial_spin_stop_sequence(particle_density_kg_m3=1050.0, **common)
    _, heavy = vial_spin_stop_sequence(particle_density_kg_m3=1800.0, **common)
    light_drop = _object_rows(light, "particle")[-1] - _object_rows(light, "particle")[0]
    heavy_drop = _object_rows(heavy, "particle")[-1] - _object_rows(heavy, "particle")[0]
    assert heavy_drop > light_drop > 0.0


def test_scratches_are_truth_stationary_and_bubbles_are_upward_without_swirl():
    _, truth = vial_spin_stop_sequence(seed=22, initial_omega_rad_s=0.0, n_particles=0,
                                       n_bubbles=1, n_scratches=2, noise_sigma=0.0)
    scratch = truth["object_type"] == "scratch"
    bubble = _object_rows(truth, "bubble")
    assert np.ptp(truth["row_px"][scratch]) > 0.0  # two distinct scratches exist
    for oid in np.unique(truth["object_id"][scratch]):
        q = truth["object_id"] == oid
        assert np.allclose(truth["row_px"][q], truth["row_px"][q][0])
        assert np.allclose(truth["col_px"][q], truth["col_px"][q][0])
    assert bubble[-1] < bubble[0]


def test_tracker_matches_bright_particle_truth_and_marks_upward_bubble():
    frames, truth = vial_spin_stop_sequence(seed=4, initial_omega_rad_s=0.0,
                                             particle_diameter_um=160.0, particle_contrast=0.40,
                                             n_particles=1, n_bubbles=1, n_scratches=1,
                                             noise_sigma=0.003)
    tracks = track_moving_particles(frames, threshold=0.025, max_displacement_px=5.0)
    particle = truth["object_type"] == "particle"
    matched = 0
    for frame, row, col in zip(truth["frame"][particle], truth["row_px"][particle], truth["col_px"][particle]):
        q = (tracks["frame"].astype(int) == int(frame)) & (tracks["object_class"] != "scratch")
        if np.any(q) and np.min(np.hypot(tracks["row_px"][q].astype(float) - row,
                                         tracks["col_px"][q].astype(float) - col)) <= 3.0:
            matched += 1
    assert matched >= frames.shape[0] - 2
    assert "scratch" in set(tracks["object_class"])
    assert "bubble" in set(tracks["object_class"])


def test_both_ops_are_reachable_through_the_typed_ledger():
    import fullseye as fs

    frames = fs.ledger.vial_spin_stop_sequence(shape=(40, 32), n_frames=3, seed=1)
    result = fs.ledger.track_moving_particles(frames, threshold=0.02)
    assert frames.shape == (3, 40, 32)
    assert {"frame", "track_id", "object_class"} <= set(result)
