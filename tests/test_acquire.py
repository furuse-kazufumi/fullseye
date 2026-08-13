"""Tests for the acquisition layer (acquire.py) — the camera / framegrabber front end.

No hardware in CI, so the tests use the ``dir`` backend (a folder of images) and the
``callable`` backend (a supplied function); the OpenCV device path is exercised by
video.py's tests. They lock down frame coercion, iteration and the HALCON aliases."""
import numpy as np
import pytest

import acquire
from acquire import Camera


def _write_imgs(tmp_path, n=3):
    import imgio
    for i in range(n):
        a = np.full((16, 20), 0.1 + 0.2 * i, np.float64)
        imgio.save(str(tmp_path / ("f%02d.png" % i)), a)
    return str(tmp_path)


def test_dir_backend_serves_frames_in_order(tmp_path):
    d = _write_imgs(tmp_path, 3)
    cam = Camera(d)                                  # auto -> 'dir'
    assert cam.backend == "dir"
    f0 = cam.grab()
    assert f0.shape == (16, 20) and f0.dtype == np.float64
    assert 0.0 <= f0.min() and f0.max() <= 1.0
    means = [cam.grab().mean() for _ in range(2)]    # next two frames, brighter
    assert means[0] < means[1]
    cam.close()


def test_dir_backend_wraps_and_stream_stops(tmp_path):
    d = _write_imgs(tmp_path, 3)
    with Camera(d) as cam:
        assert len(cam.frames(5)) == 5               # frames() wraps around
    with Camera(d) as cam:
        got = list(cam.stream())                     # stream() stops after one pass
        assert len(got) == 3


def test_callable_backend_and_gray_rgb():
    frame = (np.random.default_rng(0).random((8, 10, 3)) * 255).astype(np.uint8)
    cam = Camera(lambda: frame, gray=True)
    assert cam.backend == "callable"
    g = cam.grab()
    assert g.shape == (8, 10)                         # RGB -> gray
    cam2 = Camera(lambda: frame, gray=False)
    assert cam2.grab().shape == (8, 10, 3)


def test_grab_raises_when_source_dry():
    box = {"n": 0}

    def once():
        box["n"] += 1
        return np.zeros((4, 4)) if box["n"] == 1 else None

    cam = Camera(once, retries=1)
    cam.grab()                                        # first ok
    with pytest.raises(RuntimeError):
        cam.grab()                                    # then dry -> raises


def test_missing_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        Camera(str(tmp_path / "empty"))              # no images


def test_halcon_aliases(tmp_path):
    d = _write_imgs(tmp_path, 2)
    cam = acquire.open_framegrabber(d)
    frame = acquire.grab_image(cam)
    assert isinstance(frame, np.ndarray)
    acquire.close_framegrabber(cam)


def test_facade_exposes_camera():
    import fullseye
    assert hasattr(fullseye, "Camera") and hasattr(fullseye, "grab_image")


def test_list_cameras_is_safe():
    # never raises; returns a list (may be empty on a machine with no camera)
    assert isinstance(acquire.list_cameras(max_index=0), list)


def test_backend_capabilities_catalog():
    caps = {c["name"]: c for c in acquire.capabilities()}
    assert caps["dir"]["kind"] == "native" and caps["dir"]["available"]
    assert caps["realsense"]["kind"] == "optional" and caps["realsense"]["pip"] == "pyrealsense2"
    assert caps["oak"]["pip"] == "depthai"                # Physical-AI depth cameras catalogued
