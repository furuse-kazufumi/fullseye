"""Truth gates for single-frame FTP and the exposed shape-from-focus op."""
import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

import fringe
import ops3d
import reconstruction


def _rmse_shape(a, b):
    a = np.asarray(a) - np.mean(a)
    b = np.asarray(b) - np.mean(b)
    return float(np.sqrt(np.mean((a - b) ** 2)))


@pytest.mark.parametrize("axis,name,cycles", [(1, "x", 12), (0, "y", 9)])
def test_ftp_smooth_truth_and_carrier_estimate(axis, name, cycles):
    h, w = 96, 128
    yy, xx = np.mgrid[:h, :w]
    truth = .25 * np.sin(2 * np.pi * xx / w) + .18 * np.cos(2 * np.pi * yy / h)
    gain = 2.0
    image = fringe.synthesize_fringes(
        truth, n_steps=3, freq=cycles, phase_gain=gain, axis=axis)[0]
    got, info = fringe.fringe_ftp_phase(
        image, name, bandwidth=.35, k=1 / gain, return_info=True)
    # Measured noiseless RMSE is 0.00795: 0.012 leaves 51% headroom for FFT/library drift.
    assert _rmse_shape(got, truth) < .012
    expected_period = (w if axis == 1 else h) / cycles
    assert info["estimated_carrier"] is True
    assert info["carrier_period"] == pytest.approx(expected_period, rel=.01)


def test_ftp_documents_bandwidth_limit_with_steep_phase():
    h, w = 96, 128
    xx = np.mgrid[:h, :w][1]
    smooth = .25 * np.sin(2 * np.pi * xx / w)
    steep = 2.0 * np.sin(2 * np.pi * xx / w)
    errors = []
    for truth in (smooth, steep):
        image = fringe.synthesize_fringes(
            truth, n_steps=3, freq=12, phase_gain=2.0, axis=1)[0]
        got, _ = fringe.fringe_ftp_phase(
            image, "x", bandwidth=.35, k=.5, return_info=True)
        errors.append(_rmse_shape(got, truth))
    # The steep field spills beyond the isolated sideband (measured 2.66 vs 0.0049).
    assert errors[1] > 100 * errors[0]
    assert errors[1] > 1.0


def test_ftp_rejects_constant_and_nonfringe_noise():
    with pytest.raises(ValueError, match="constant"):
        fringe.fringe_ftp_phase(np.ones((64, 64)))
    noise = np.random.default_rng(4).normal(size=(64, 64))
    with pytest.raises(ValueError, match="carrier peak"):
        fringe.fringe_ftp_phase(noise)


def _focus_stack():
    rng = np.random.default_rng(9)
    texture = gaussian_filter(rng.normal(size=(96, 96)), .6)
    yy, xx = np.mgrid[:96, :96]
    truth = np.where(xx < 32, 0, np.where(xx < 64, 1, 2))
    images = []
    for focus in range(3):
        frame = np.zeros_like(texture)
        for depth in range(3):
            blurred = gaussian_filter(texture, sigma=.25 + 1.8 * abs(depth - focus))
            frame[truth == depth] = blurred[truth == depth]
        images.append(frame)
    return images, truth


def test_depth_from_focus_truth_and_op_adapter():
    images, truth = _focus_stack()
    raw = reconstruction.depth_from_focus(images, [10., 20., 30.])
    # Ignore the 5-pixel SML support around synthetic depth discontinuities.
    valid = np.ones(truth.shape, bool)
    valid[:, 27:37] = False
    valid[:, 59:69] = False
    accuracy = np.mean(raw["index"][valid] == truth[valid])
    assert accuracy > .96
    assert np.array_equal(raw["depth"], np.array([10., 20., 30.])[raw["index"]])
    chained = ops3d.call("depth_from_focus", images, [10., 20., 30.])
    assert np.array_equal(chained, raw["depth"])


def test_depth_from_focus_textureless_limit_is_explicit():
    raw = reconstruction.depth_from_focus([np.ones((24, 24))] * 3)
    assert np.all(raw["index"] == 0)  # tie policy: first frame
    assert np.all(raw["sharpness"] == 0)  # confidence says the depth is unknowable


def test_new_ops_are_registered_with_chain_types():
    assert ops3d.info("fringe_ftp_phase")["in"] == ["image2d"]
    assert ops3d.info("fringe_ftp_phase")["out"] == "depth"
    assert ops3d.info("depth_from_focus")["in"] == ["images"]
    assert ops3d.info("depth_from_focus")["out"] == "depth"


def test_new_ops_execute_through_mcp_without_side_effects(tmp_path, monkeypatch):
    import os
    import time
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import call_tool

    monkeypatch.chdir(tmp_path)
    before_files = set(os.listdir(tmp_path))
    random_before = np.random.get_state()
    store = HandleStore(roots=[])
    cat = Catalog.load()

    h, w = 48, 64
    frame = fringe.synthesize_fringes(
        np.zeros((h, w)), n_steps=3, freq=8, phase_gain=2.0)[0]
    image_handle = store.put(frame, sort="image", provenance=[])["handle"]
    images, _ = _focus_stack()
    stack_handle = store.put(np.asarray(images), sort="images", provenance=[])["handle"]
    started = time.perf_counter()
    ftp = call_tool("fullseye_pipeline", {"handle": image_handle, "stages": [
        {"op": "fringe_ftp_phase", "inputs": [image_handle], "params": {"k": .5}}
    ]}, cat, store)
    sff = call_tool("fullseye_pipeline", {"handle": stack_handle, "stages": [
        {"op": "depth_from_focus", "inputs": [stack_handle], "params": {}}
    ]}, cat, store)
    assert time.perf_counter() - started < 2.0
    assert not ftp.get("isError") and not sff.get("isError")
    assert ftp["structuredContent"]["out_sort"] == "depth"
    assert sff["structuredContent"]["out_sort"] == "depth"
    assert set(os.listdir(tmp_path)) == before_files
    random_after = np.random.get_state()
    assert random_before[0] == random_after[0]
    assert np.array_equal(random_before[1], random_after[1])
    assert random_before[2:] == random_after[2:]


def test_business_phrases_find_and_plan_the_new_ops_first():
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import call_tool

    cat, store = Catalog.load(), HandleStore(roots=[])
    cases = [
        ("縞 1 枚から高さ", "image", "fringe_ftp_phase"),
        ("焦点を変えた画像から高さ", "images", "depth_from_focus"),
    ]
    for query, have, expected in cases:
        found = call_tool("fullseye_find_ops", {"query": query, "limit": 10}, cat, store)
        assert found["structuredContent"]["ops"][0]["name"] == expected
        planned = call_tool("fullseye_plan", {
            "have": have, "want": "depth", "goal": query}, cat, store)
        assert planned["structuredContent"]["plans"][0]["ops"] == [expected]
