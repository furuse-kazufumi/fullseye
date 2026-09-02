# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""videostream: ring buffer, stateful ops, pipeline, uint8 reader — pinned against closed forms and videops."""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import videostream as VS  # noqa: E402
import videops  # noqa: E402
import video  # noqa: E402
import opsvideostream  # noqa: E402


def _clip(t=12, h=16, w=20, seed=0):
    rng = np.random.default_rng(seed)
    base = rng.random((h, w))
    vid = np.empty((t, h, w))
    for i in range(t):
        vid[i] = np.clip(base + 0.05 * rng.standard_normal((h, w)), 0, 1)
        if 4 <= i < 8:                                  # a transient object
            vid[i, 4:9, 6:12] = 1.0
    return vid


def _u8(vid):
    return np.round(vid * 255).astype(np.uint8)


# --------------------------------------------------------------------------- ring
def test_ring_order_and_capacity():
    r = VS.FrameRing(3)
    for i in range(5):
        r.push(np.full((2, 2), i, np.uint8))
    assert len(r) == 3 and r.full and r.total == 5
    w = r.window()
    assert w.shape == (3, 2, 2) and [int(x[0, 0]) for x in w] == [2, 3, 4]
    assert int(r.latest[0, 0]) == 4
    assert r.nbytes() == 3 * 4
    r.reset()
    assert len(r) == 0 and r.nbytes() == 12          # allocation kept
    with pytest.raises(ValueError):
        r.window()


def test_ring_refuses_shape_and_dtype_change():
    r = VS.FrameRing(2)
    r.push(np.zeros((4, 4)))
    with pytest.raises(ValueError, match="does not match"):
        r.push(np.zeros((4, 5)))
    with pytest.raises(ValueError, match="does not match"):
        r.push(np.zeros((4, 4), np.uint8))
    with pytest.raises(ValueError, match="non-finite"):
        r.push(np.full((4, 4), np.nan))
    with pytest.raises(ValueError):
        VS.FrameRing(0)
    with pytest.raises(ValueError):
        VS.FrameRing(True)


def test_ring_partial_window_before_full():
    r = VS.FrameRing(4)
    r.push(np.ones((2, 2)))
    r.push(np.zeros((2, 2)))
    assert r.window().shape == (2, 2, 2) and not r.full


# --------------------------------------------------------------------------- window ops == explicit windows
def _ref_window(vid, n, fn):
    out = np.empty_like(vid)
    for t in range(vid.shape[0]):
        out[t] = fn(vid[max(0, t - n + 1):t + 1], axis=0)
    return out


def test_temporal_median_window_matches_explicit():
    vid = _clip()
    got = VS.temporal_median_window(vid, 5)
    np.testing.assert_allclose(got, _ref_window(vid, 5, np.median), atol=0, rtol=0)
    # window == T reproduces the whole-clip videops median on the last frame
    assert np.allclose(VS.temporal_median_window(vid, vid.shape[0])[-1], videops.temporal_median(vid))


def test_moving_average_window_matches_explicit_and_videops_interior():
    vid = _clip()
    got = VS.moving_average_window(vid, 3)
    np.testing.assert_allclose(got, _ref_window(vid, 3, np.mean), atol=1e-12)
    # causal window of 3 at t equals the centred videops window at t-1 (interior only)
    cen = videops.moving_average(vid, 3)
    np.testing.assert_allclose(got[2:], cen[1:-1], atol=1e-12)


def test_background_subtraction_window_matches_explicit():
    vid = _clip()
    got = VS.background_subtraction_window(vid, 5, 0.3)
    bg = _ref_window(vid, 5, np.median)
    np.testing.assert_array_equal(got, (np.abs(vid - bg) > 0.3).astype(np.float64))
    assert got[6, 5, 8] == 1.0 or got[4, 5, 8] == 1.0          # the transient object is found
    # window == T on the last frame equals videops on the last frame
    full = VS.background_subtraction_window(vid, vid.shape[0], 0.3)[-1]
    np.testing.assert_array_equal(full, videops.background_subtraction(vid, 0.3)[-1])


def test_frame_difference_causal_matches_videops_shifted():
    vid = _clip()
    got = VS.frame_difference_causal(vid)
    assert got.shape == vid.shape and np.all(got[0] == 0)
    np.testing.assert_allclose(got[1:], videops.frame_difference(vid), atol=1e-12)


def test_exponential_background_closed_form():
    vid = _clip(t=6)
    a = 0.2
    got = VS.exponential_background(vid, a)
    bg = vid[0].copy()
    for t in range(1, 6):
        bg = (1 - a) * bg + a * vid[t]
        np.testing.assert_allclose(got[t], bg, atol=1e-12)
    fg = VS.exponential_foreground(vid, a, 0.3)
    assert fg.shape == vid.shape and set(np.unique(fg)) <= {0.0, 1.0}
    assert fg[5].sum() > 0                                     # object 4..7 vs slow background
    with pytest.raises(ValueError):
        VS.exponential_background(vid, 1.5)


def test_running_mean_std_equals_numpy():
    vid = _clip()
    r = VS.running_mean_std(vid)
    assert r["n"] == vid.shape[0]
    np.testing.assert_allclose(r["mean"], vid.mean(0), atol=1e-12)
    np.testing.assert_allclose(r["std"], vid.std(0), atol=1e-12)


def test_optical_flow_stream_matches_videops_shifted():
    vid = _clip(t=4, h=24, w=24)
    got = VS.optical_flow_magnitude_stream(vid, window=7, levels=1)
    assert got.shape == vid.shape and np.all(got[0] == 0)
    ref = videops.optical_flow_sequence(vid)
    # videops uses default LK kwargs; compare with the same kwargs through the class
    op = VS.OpticalFlowStream()
    out = VS.stream_replay(vid, op)
    np.testing.assert_allclose(out[1:], ref, atol=1e-12)
    assert op.last_flow is not None and op.last_flow[0].shape == vid.shape[1:]


# --------------------------------------------------------------------------- integer rings
def test_uint8_ring_gives_the_same_answer_as_float():
    vid = _clip()
    u8 = _u8(vid)
    f = u8.astype(np.float64) / 255.0
    for n in (1, 3, 5):
        np.testing.assert_allclose(VS.temporal_median_window(u8, n), VS.temporal_median_window(f, n), atol=1e-12)
        np.testing.assert_allclose(VS.moving_average_window(u8, n), VS.moving_average_window(f, n), atol=1e-12)
    np.testing.assert_allclose(VS.frame_difference_causal(u8), VS.frame_difference_causal(f), atol=1e-12)
    r8, rf = VS.running_mean_std(u8), VS.running_mean_std(f)
    np.testing.assert_allclose(r8["mean"], rf["mean"], atol=1e-12)
    op = VS.TemporalMedianWindow(5)
    op.push(u8[0])
    assert op.ring.dtype == np.uint8 and op.ring.nbytes() == 5 * u8[0].nbytes   # 8x smaller than float64
    assert op.state["ring_bytes"] == op.ring.nbytes()


def test_uint16_and_bool_frames():
    vid = _clip(t=3)
    u16 = np.round(vid * 65535).astype(np.uint16)
    np.testing.assert_allclose(VS.moving_average_window(u16, 2), VS.moving_average_window(u16.astype(np.float64) / 65535, 2), atol=1e-12)
    b = vid > 0.5
    out = VS.frame_difference_causal(b)
    assert out.shape == vid.shape and set(np.unique(out)) <= {0.0, 1.0}


# --------------------------------------------------------------------------- stateful op contract
def test_stateful_reset_and_refusal():
    op = VS.TemporalMedianWindow(3)
    for t in range(4):
        op.push(np.full((3, 3), t / 4))
    assert op.frames == 4 and op.state["stored"] == 3
    with pytest.raises(ValueError, match="refused"):
        op.push(np.zeros((3, 4)))
    assert op.frames == 4                                       # the bad frame did not count
    op.reset()
    assert op.frames == 0 and op.state["stored"] == 0 and op.state["shape"] is None
    op.push(np.zeros((5, 5)))                                   # a new stream with a new shape is fine
    assert op.state["shape"] == (5, 5)


def test_stream_replay_validation():
    with pytest.raises(ValueError, match="StatefulOp"):
        VS.stream_replay(np.zeros((2, 3, 3)), lambda f: f)
    with pytest.raises(ValueError, match="\\(T, H, W\\)"):
        VS.stream_replay(np.zeros((3, 3)), VS.FrameDifference())
    with pytest.raises(ValueError, match="non-finite"):
        VS.stream_replay(np.full((2, 3, 3), np.inf), VS.FrameDifference())
    with pytest.raises(ValueError):
        VS.stream_replay([], VS.FrameDifference())
    with pytest.raises(ValueError, match="image per frame"):
        VS.stream_replay(np.zeros((2, 3, 3)), VS.RunningStats())
    # a frame list is accepted
    out = VS.stream_replay([np.zeros((3, 3)), np.ones((3, 3))], VS.FrameDifference())
    assert out[1].max() == 1.0


# --------------------------------------------------------------------------- pipeline
def test_pipeline_mixes_facade_ops_and_state():
    vid = _clip()
    pipe = VS.VideoPipeline([("gaussian", 0.2, 0.5), VS.BackgroundSubtractionWindow(5, 0.3)])
    outs = list(pipe.run(vid))
    assert len(outs) == vid.shape[0] and outs[6].shape == vid.shape[1:]
    st = pipe.stats()
    assert st["frames"] == 12 and st["stages"] == ["gaussian", "background_subtraction_window"]
    assert st["ring_bytes"] == 5 * vid[0].nbytes and st["ms_per_frame"] > 0
    # equals: facade op per frame, then the batch op
    import api
    g = np.stack([api.apply(f, "gaussian", 0.2, 0.5) for f in vid])
    np.testing.assert_array_equal(np.stack(outs), VS.background_subtraction_window(g, 5, 0.3))


def test_pipeline_uint8_input_converted_once_before_first_op():
    vid = _clip()
    u8 = _u8(vid)
    pipe = VS.VideoPipeline(["invert"])
    out = pipe.push(u8[0])
    import api
    np.testing.assert_allclose(out, api.apply(u8[0] / 255.0, "invert"), atol=1e-12)
    # a stateful first stage keeps the integer ring
    pipe2 = VS.VideoPipeline([VS.TemporalMedianWindow(3), "invert"])
    pipe2.push(u8[0])
    assert pipe2._stages[0][4].ring.dtype == np.uint8


def test_pipeline_refuses_shape_change_and_resets_state_on_failure():
    pipe = VS.VideoPipeline([VS.FrameDifference()])
    pipe.push(np.zeros((4, 4)))
    with pytest.raises(ValueError, match="refused"):
        pipe.push(np.zeros((4, 5)))
    pipe.reset()
    assert pipe.frames == 0 and pipe._stages[0][4].prev is None
    pipe.push(np.zeros((6, 6)))

    class Boom(VS.StatefulOp):
        name = "boom"

        def _update(self, raw):
            raise RuntimeError("kaboom")

    import backend_safe as bs
    p2 = VS.VideoPipeline([Boom()])
    with pytest.raises(RuntimeError):
        p2.push(np.zeros((2, 2)))                               # facade default is raise? then strict
    # explicit fail-soft: recorded with source="stream", returns None, state reset
    p3 = VS.VideoPipeline([Boom()], on_error="fallback")
    before = len(bs.fallbacks()) if hasattr(bs, "fallbacks") else None
    with bs.quiet_warnings() if hasattr(bs, "quiet_warnings") else _null():
        r = p3.push(np.zeros((2, 2)))
    assert r is None and p3._stages[0][4].frames == 0
    if before is not None:
        evs = bs.fallbacks()
        assert len(evs) == before + 1 and evs[-1]["source"] == "stream" and evs[-1]["name"] == "boom"
    p4 = VS.VideoPipeline([Boom()], on_error="raise")
    with pytest.raises(RuntimeError):
        p4.push(np.zeros((2, 2)))


class _null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_pipeline_validation_and_callables():
    with pytest.raises(ValueError):
        VS.VideoPipeline([])
    with pytest.raises(ValueError):
        VS.VideoPipeline([42])
    pipe = VS.VideoPipeline([lambda f: f.sum()])
    assert pipe.push(np.ones((2, 2))) == 4.0
    assert list(pipe.run(np.ones((3, 2, 2)), max_frames=2)) == [4.0, 4.0]
    assert list(pipe.run(np.ones((3, 2, 2)), max_frames=0)) == []


# --------------------------------------------------------------------------- ledger
def test_ledger_is_connected():
    assert not opsvideostream.missing()
    assert len(opsvideostream.OPSVIDEOSTREAM) == 8 and opsvideostream.categories() == ["window", "recursive", "flow"]
    for n, m in opsvideostream.OPSVIDEOSTREAM.items():
        assert m["in"] == ["video"] and m["out"] in ("video", "table") and m["doc"]
        assert n in VS.__all__
    vid = _clip(t=4)
    out = opsvideostream.call("temporal_median_window", vid, window=2)
    assert out.shape == vid.shape
    assert set(opsvideostream.call("running_mean_std", vid)) == {"mean", "std", "n"}
    import api
    for n in opsvideostream.OPSVIDEOSTREAM:
        assert hasattr(api, n), n
    assert hasattr(api, "VideoPipeline") and hasattr(api, "FrameRing")


# --------------------------------------------------------------------------- reader uint8 pass-through
def test_gray_u8_matches_rec601_and_cv2_within_1lsb():
    rng = np.random.default_rng(1)
    rgb = rng.integers(0, 256, (8, 9, 3), np.uint8)
    g_np = video._gray_u8(rgb, "numpy")
    ref = (299 * rgb[..., 0].astype(np.uint32) + 587 * rgb[..., 1] + 114 * rgb[..., 2] + 500) // 1000
    np.testing.assert_array_equal(g_np, ref.astype(np.uint8))
    assert g_np.dtype == np.uint8
    g_auto = video._gray_u8(rgb, "auto")
    assert np.abs(g_auto.astype(int) - g_np.astype(int)).max() <= 1
    with pytest.raises(ValueError):
        video._gray_u8(rgb, "gpu")
    # float64 path and uint8 path agree within 1/255
    f = video._coerce(rgb, True)
    u = video._coerce(rgb, True, "uint8", "numpy")
    assert np.abs(f - u / 255.0).max() <= 1.0 / 255.0 + 1e-12
    assert video._coerce(rgb, False, "uint8") is rgb or np.shares_memory(video._coerce(rgb, False, "uint8"), rgb)
    with pytest.raises(ValueError):
        video._coerce(rgb, True, "int8")
    # a float frame asked for as uint8 is honoured
    assert video._coerce(np.full((2, 2), 0.5), True, "uint8").dtype == np.uint8


def test_iter_frames_uint8_pass_through(tmp_path):
    rng = np.random.default_rng(2)
    frames = [rng.integers(0, 256, (12, 16, 3), np.uint8) for _ in range(4)]
    path = str(tmp_path / "clip.gif")
    try:
        video.write_video(path, frames, fps=5)
    except RuntimeError as e:                                   # no Pillow/imageio in this env
        pytest.skip(str(e))
    u8 = list(video.iter_frames(path, gray=True, dtype="uint8"))
    assert len(u8) == 4 and u8[0].dtype == np.uint8 and u8[0].shape == (12, 16)
    f64 = video.read_frames(path, gray=True)
    assert f64.dtype == np.float64
    assert np.abs(f64 - np.stack(u8) / 255.0).max() <= 1.0 / 255.0 + 1e-12
    rgb = video.read_frames(path, gray=False, dtype="uint8")
    assert rgb.shape == (4, 12, 16, 3) and rgb.dtype == np.uint8
    with pytest.raises(ValueError):
        list(video.iter_frames(path, dtype="float32"))
    with pytest.raises(ValueError):
        list(video.iter_frames(path, gray_backend="cuda"))
    # the stream end to end
    pipe = VS.VideoPipeline([VS.FrameDifference()])
    outs = list(pipe.run(video.iter_frames(path, dtype="uint8")))
    assert len(outs) == 4 and outs[0].max() == 0.0 and outs[1].dtype == np.float64
