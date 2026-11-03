"""Second-stage golden manifest round trips and detects drift."""

import numpy as np

from fullseye.evaluation.manifest import (
    build_manifest,
    compare_manifests,
    read_manifest,
    summarize_video_frames,
    write_manifest,
)
from fullseye.evaluation.result import GateResult
from fullseye.evaluation.truth import TruthBundle


def _truth():
    return TruthBundle(
        fields={"depth": np.arange(6, dtype=np.float32).reshape(2, 3)},
        units={"depth": "mm"},
        frames={"depth": "image-row-col-isp"},
        masks={"valid": np.ones((2, 3), bool)},
        provenance={"processing_stage": "isp-post", "generator": "unit-test"},
        seed=11,
    )


def test_manifest_roundtrip_preserves_shapes_truth_gates_figures_and_video(tmp_path):
    frames = [np.full((2, 3), value, np.uint8) for value in range(3)]
    manifest = build_manifest(
        "demo",
        metrics={"rmse": 0.25},
        arrays={"estimate": np.ones((2, 3), np.float64)},
        truth=_truth(),
        gates=[GateResult("rmse", True, 0.25, 0.0, 0.5, "<=", "")],
        figures=[{"file": "01_demo.png", "name": "demo", "caption": "caption", "shape": [2, 3]}],
        videos={"sweep": summarize_video_frames(frames, capture_fps=30.0, playback_fps=10.0)},
        seed=11,
    )
    path = write_manifest(tmp_path / "evaluation.json", manifest)
    restored = read_manifest(path)
    assert compare_manifests(restored, manifest) == []
    assert restored["arrays"]["estimate"]["shape"] == [2, 3]
    assert restored["truth"]["fields"]["depth"]["dtype"] == "<f4"
    assert set(restored["videos"]["sweep"]["frame_hashes"]) == {"first", "middle", "last"}


def test_manifest_comparison_reports_exact_path_and_supports_allclose():
    expected = {"evaluation_manifest_schema": 1, "metrics": {"x": 1.0}}
    actual = {"evaluation_manifest_schema": 1, "metrics": {"x": 1.0001}}
    assert compare_manifests(actual, expected) == ["$.metrics.x: 1.0001 != 1.0"]
    assert compare_manifests(actual, expected, atol=0.001) == []
