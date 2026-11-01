"""Artifact promotion and video parameter separation retain examplefig as the base."""

import numpy as np

from fullseye.evaluation.artifacts import artifacts_from_manifest
from fullseye.evaluation.video import VideoSpec, save_video


def test_artifacts_promote_the_existing_figure_manifest():
    rows = [
        {"name": "depth", "caption": "Depth", "file": "01_depth.png"},
        {"name": "sweep", "caption": "Sweep", "file": "02_sweep.gif", "animated": True},
    ]
    specs = artifacts_from_manifest(rows, units={"depth": "mm"}, truth_overlays={"depth": "depth"})
    assert [(spec.name, spec.kind) for spec in specs] == [("depth", "image"), ("sweep", "video")]
    assert specs[0].units == "mm"
    assert specs[0].truth_overlay == "depth"


def test_video_adapter_separates_capture_playback_hold_stride_and_scale(monkeypatch):
    called = {}

    def fake_save(name, frames, **kwargs):
        called.update(name=name, frames=list(frames), kwargs=kwargs)
        return "saved"

    monkeypatch.setattr("examplefig.save_video", fake_save)
    frames = [np.zeros((4, 8), np.uint8), np.ones((4, 8), np.uint8)]
    out = save_video(
        "sweep",
        frames,
        caption="caption",
        capture_fps=120.0,
        playback_fps=12.0,
        hold_frames=2,
        gif_stride=3,
        display_scale=0.5,
        interpolation="linear",
    )
    assert out == "saved"
    assert len(called["frames"]) == 4
    assert called["kwargs"]["fps"] == 12.0
    assert called["kwargs"]["gif_every"] == 3
    assert called["kwargs"]["gif_width"] == 4
    assert VideoSpec(120, 12, 2, 3, 0.5, "linear").capture_fps == 120
