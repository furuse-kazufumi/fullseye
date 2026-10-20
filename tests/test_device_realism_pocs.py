import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    path = ROOT / "examples" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_event_stream_static_is_background_only_and_probe_fails():
    mod = _load("poc_xyt_event_surface")
    frames = np.full((12, 96, 128), 0.4)
    ev = mod.simulate_event_stream(frames, dt_s=1e-3, contrast=0.18,
                                   background_rate_hz=0.02, seed=7)
    expected = 96 * 128 * 11e-3 * 0.02
    assert abs(len(ev) - expected) <= 4.0 * np.sqrt(expected + 1.0)
    assert mod.event_resemblance_gates(frames, ev, dt_s=1e-3)["edge_fraction"] < 0.10


def test_event_stream_moving_edges_and_polarity_balance():
    mod = _load("poc_xyt_event_surface")
    frames, edges = mod.make_event_scene(height=128, width=160, n_frames=41)
    ev = mod.simulate_event_stream(frames, dt_s=1e-3, contrast=0.16,
                                   background_rate_hz=0.001, seed=11)
    gates = mod.event_resemblance_gates(frames, ev, dt_s=1e-3, edge_truth=edges)
    assert len(ev) > 1000
    assert gates["edge_fraction"] >= 0.90
    assert abs(gates["on_off_ratio"] - 1.0) <= 0.10
