"""Smoke tests: the example scripts run end-to-end on synthetic data and produce
sane results, so the cross-project templates stay working."""
import importlib.util
import os

import pytest

_EX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_EX, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_perception_pipeline_runs():
    r = _load("perception_pipeline").run()
    assert r["n_points"] > 0
    assert 0.0 <= r["walkable_frac"] <= 1.0
    assert r["depth_valid_frac"] > 0.0


def test_segment_and_classify_runs():
    labelled = _load("segment_and_classify").run()
    assert len(labelled) == 3                       # two disks + one square
    names = [name for name, *_ in labelled]
    assert names.count("disk") == 2 and names.count("square") == 1


def test_motion_analysis_runs():
    r = _load("motion_analysis").run()
    assert r["motion_energy"] > 0.0
    assert abs(r["global_u"] - 1.5) < 0.5           # recovers the ~1.5 px global drift
    assert r["n_moving_segments"] >= 1              # the independently moving object


def test_grasp_pose_runs():
    r = _load("grasp_pose").run()
    assert r["n_downsampled"] <= r["n_observed"] < r["n_model"]
    assert r["rmse"] < 0.02                         # converges to ~sensor-noise level
    assert r["rot_error_deg"] < 2.0                # recovers the object's orientation


def test_perception_on_video_synthetic():
    r = _load("perception_on_video").run()          # synthetic pan + burst + object
    assert r["n_frames"] >= 8
    assert r["recon_gain"] > 0.3                     # flow explains the global pan
    assert r["n_events"] >= 1                        # the speed burst is an event
    assert abs(r["global_translation_px"][0] - 8.0) < 2.5    # ~8 px burst pan
    assert r["tracked_survived"] >= r["tracked_points"] * 0.7


# Real FullSense render clips (onocollo / hillco), if present on this machine — a
# genuine (non-synthetic) end-to-end check. Skipped where the assets are absent
# so the suite stays portable.
_REAL_CLIPS = [
    r"C:\dev\projects\onocollo-complete\out\media\rocket_arc.mp4",
    r"C:\dev\projects\onocollo-complete\out\chopstick\box_grasp.mp4",
]
_present = [p for p in _REAL_CLIPS if os.path.exists(p)]


@pytest.mark.skipif(not _present, reason="local FullSense render clips not present")
def test_perception_on_video_real_clip():
    r = _load("perception_on_video").run(clip_path=_present[0], max_frames=40)
    assert r["n_frames"] >= 2
    assert r["recon_gain"] > 0.0                     # real coherent motion is explained
    assert r["tracked_survived"] >= 1
