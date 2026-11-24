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


def test_tracker_matches_dark_backlight_and_bright_sidelight_particle_truth():
    for illumination in ("back", "side"):
        frames, truth = vial_spin_stop_sequence(seed=4, initial_omega_rad_s=0.0,
                                                 particle_diameter_um=160.0, particle_contrast=0.40,
                                                 illumination=illumination, n_particles=1, n_bubbles=1,
                                                 n_scratches=1, noise_sigma=0.003)
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


def test_backlight_particle_is_dark_and_sidelight_particle_is_bright():
    common = dict(shape=(220, 180), seed=91, initial_omega_rad_s=0.0, particle_diameter_um=220.0,
                  particle_contrast=0.30, n_bubbles=0, n_scratches=0, noise_sigma=0.0)
    back, truth = vial_spin_stop_sequence(illumination="back", **common)
    side, _ = vial_spin_stop_sequence(illumination="side", **common)
    particle = truth["object_type"] == "particle"
    row, col = (int(round(x)) for x in (truth["row_px"][particle][0], truth["col_px"][particle][0]))
    neighbourhood = np.s_[max(0, row - 5):row + 6, max(0, col - 5):col + 6]
    annulus = np.ones((11, 11), dtype=bool)
    annulus[4:7, 4:7] = False
    back_local = back[0][neighbourhood]
    side_local = side[0][neighbourhood]
    assert back[0, row, col] < np.median(back_local[annulus])
    assert side[0, row, col] > np.median(side_local[annulus])


def test_actionable_invalid_input_message_has_value_reason_and_fix():
    with np.testing.assert_raises_regex(ValueError, r"shape=.*expected.*How to fix.*不正"):
        vial_spin_stop_sequence(shape=(31, 23))
    with np.testing.assert_raises_regex(ValueError, r"threshold=.*expected.*How to fix.*対処"):
        track_moving_particles(np.zeros((3, 12, 12)), threshold=0.0)


def test_both_ops_are_reachable_through_the_typed_ledger():
    import fullseye as fs

    frames = fs.ledger.vial_spin_stop_sequence(shape=(40, 32), n_frames=3, seed=1)
    result = fs.ledger.track_moving_particles(frames, threshold=0.02)
    assert frames.shape == (3, 40, 32)
    assert {"frame", "track_id", "object_class"} <= set(result)
