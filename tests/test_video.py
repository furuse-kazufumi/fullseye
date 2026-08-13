"""Round-trip + coercion tests for the video I/O module (``video.py``).

Video codecs are lossy, so the round-trip assertions check *structure* (shape,
dtype, value range, frame count, per-frame brightness ordering) rather than exact
pixels. The dtype/shape coercion helpers are unit-tested exactly. mp4 uses the
bundled imageio-ffmpeg plugin; gif goes through Pillow — both ship with the test
environment, so these do not need external assets."""
import numpy as np
import pytest

import video


def _frames(t=6, h=32, w=40):
    """A clip whose per-frame mean brightness increases monotonically, with a
    moving bright block — survivable structure through lossy compression."""
    frames = []
    for i in range(t):
        f = np.full((h, w), 0.1 + 0.07 * i, np.float64)
        f[8:16, 4 + 3 * i: 10 + 3 * i] = 0.9
        frames.append(np.clip(f, 0, 1))
    return np.stack(frames)


# ---- exact unit tests of the coercion helpers ----------------------------- #
def test_to01_by_dtype():
    assert np.isclose(video._to01(np.array([255], np.uint8))[0], 1.0)
    assert np.isclose(video._to01(np.array([0], np.uint8))[0], 0.0)
    assert np.isclose(video._to01(np.array([65535], np.uint16))[0], 1.0)
    # a float frame is assumed already scaled — only clipped to [0, 1]
    assert np.allclose(video._to01(np.array([-0.5, 0.3, 2.0])), [0.0, 0.3, 1.0])


def test_coerce_gray_from_rgb_uses_luma():
    rgb = np.zeros((4, 5, 3), np.uint8)
    rgb[..., 0] = 255                                    # pure red
    g = video._coerce(rgb, gray=True)
    assert g.shape == (4, 5)
    assert np.allclose(g, 0.299)                         # Rec.601 luma of pure red


def test_coerce_gray_to_color_replicates():
    c = video._coerce(np.full((4, 5), 128, np.uint8), gray=False)
    assert c.shape == (4, 5, 3)
    assert np.allclose(c[..., 0], c[..., 1]) and np.allclose(c[..., 1], c[..., 2])


def test_coerce_rgba_drops_alpha():
    rgba = np.zeros((3, 3, 4), np.uint8)
    rgba[..., 3] = 255
    assert video._coerce(rgba, gray=False).shape == (3, 3, 3)


# ---- round-trip integration ---------------------------------------------- #
def test_roundtrip_gif(tmp_path):
    frames = _frames()
    p = str(tmp_path / "clip.gif")
    video.write_video(p, frames, fps=10)
    back = video.read_frames(p, gray=True)
    assert back.shape == frames.shape                    # gif preserves dims exactly
    assert back.dtype == np.float64
    assert back.min() >= 0.0 and back.max() <= 1.0
    means = back.reshape(len(back), -1).mean(1)
    assert np.all(np.diff(means) > -0.02)               # brightness ordering preserved


def test_roundtrip_mp4_preserves_dims(tmp_path):
    frames = _frames()                                   # 40x32, both even
    p = str(tmp_path / "clip.mp4")
    video.write_video(p, frames, fps=10)
    back = video.read_frames(p, gray=True)
    # macro_block_size=1 in write_video stops the silent ÷16 resize
    assert back.shape == frames.shape
    assert back.min() >= 0.0 and back.max() <= 1.0


def test_mp4_odd_dims_padded_not_resized(tmp_path):
    frames = _frames(t=4, h=31, w=41)                    # both odd
    p = str(tmp_path / "odd.mp4")
    video.write_video(p, frames, fps=10)
    back = video.read_frames(p, gray=True)
    # padded up by exactly one pixel per odd axis (not resized to a ÷16 multiple)
    assert back.shape == (4, 32, 42)


def test_read_step_start_maxframes(tmp_path):
    p = str(tmp_path / "clip.gif")
    video.write_video(p, _frames(t=10), fps=10)
    assert len(video.read_frames(p, max_frames=3)) == 3
    assert len(video.read_frames(p, step=2)) == 5        # 0,2,4,6,8
    assert len(video.read_frames(p, start=4, max_frames=2)) == 2


def test_iter_frames_matches_read(tmp_path):
    p = str(tmp_path / "clip.gif")
    frames = _frames(t=5)
    video.write_video(p, frames, fps=10)
    it = list(video.iter_frames(p, gray=True))
    assert len(it) == 5 and it[0].shape == frames[0].shape


def test_frame_pairs():
    fr = _frames(t=4)
    pairs = list(video.frame_pairs(fr))
    assert len(pairs) == 3
    assert pairs[0][0].shape == fr[0].shape
    # pairs are (prev, nxt): the second element of pair i is the first of pair i+1
    assert np.array_equal(pairs[0][1], pairs[1][0])


def test_color_read_roundtrip(tmp_path):
    rgb = np.random.default_rng(0).random((5, 16, 20, 3))
    p = str(tmp_path / "c.gif")
    video.write_video(p, rgb, fps=10)
    back = video.read_frames(p, gray=False)
    assert back.shape == (5, 16, 20, 3)


def test_probe_keys(tmp_path):
    p = str(tmp_path / "clip.mp4")
    video.write_video(p, _frames(), fps=12)
    meta = video.probe(p)
    assert set(meta) == {"fps", "size", "nframes"}
    assert meta["fps"] == pytest.approx(12.0, abs=0.5)
    assert meta["size"] == (40, 32)                      # (width, height)


def test_probe_missing_file_is_safe():
    meta = video.probe("does_not_exist.mp4")
    assert meta == {"fps": None, "size": None, "nframes": None}


def test_errors(tmp_path):
    with pytest.raises((FileNotFoundError, ValueError, RuntimeError)):
        video.read_frames(str(tmp_path / "nope.mp4"))
    with pytest.raises(ValueError):
        video.write_video(str(tmp_path / "empty.gif"), [])


def test_max_frames_zero_returns_empty(tmp_path):
    p = str(tmp_path / "clip.gif")
    video.write_video(p, _frames(t=5), fps=10)
    assert list(video.iter_frames(p, max_frames=0)) == []
