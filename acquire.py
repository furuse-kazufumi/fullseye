"""acquire.py — image acquisition from cameras and sources (HALCON framegrabber analog).

The front of a machine-vision loop: grab a frame from a source and hand it
straight to a pipeline / :class:`~engine.FullseyeEngine`. Mirrors HALCON's
``open_framegrabber`` / ``grab_image`` / ``close_framegrabber``.

Backends (chosen by ``backend=`` or auto-detected from *source*):

- ``"opencv"``  — ``cv2.VideoCapture``: USB/UVC webcams (device index ``0,1,…``),
  IP / RTSP streams, and video files. Default for an int or a URL/path. Needs
  ``opencv-python``.
- ``"dir"``     — a folder or glob of images, served in filename order. The
  offline / batch-inspection path, and what the tests use (no hardware needed).
- ``"callable"``— any ``fn() -> frame`` you supply: a custom SDK, a generator, or
  a mock. Nothing to install.
- ``"genicam"`` — industrial GigE / USB3 Vision through the ``harvesters`` GenTL
  producer (**optional**: ``pip install harvesters`` + a vendor ``.cti``).
- ``"basler"``  — Basler cameras via ``pypylon`` (**optional**).

Frames are float64 in ``[0, 1]``: grayscale ``(H, W)`` by default or RGB
``(H, W, 3)`` with ``gray=False`` — the same convention as :mod:`video` / the
operator library, so ``engine.run(cam.grab())`` just works.

    import fullseye
    with fullseye.Camera(0) as cam:              # webcam / framegrabber
        frame = cam.grab()
        result = eng.run(frame)                  # inspect
"""
from __future__ import annotations

import glob
import os

import numpy as np

__all__ = [
    "Camera", "list_cameras",
    "open_framegrabber", "grab_image", "close_framegrabber",
]

_LUMA = np.array([0.299, 0.587, 0.114], np.float64)
_IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".pgm", ".ppm", ".webp")
_VIDEO_EXTS = (".mp4", ".m4v", ".mov", ".avi", ".mkv", ".webm")


def _cv2():
    try:
        import cv2
        return cv2
    except Exception:
        return None


def _to01(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a)
    if np.issubdtype(a.dtype, np.integer):
        return np.clip(a.astype(np.float64) / float(np.iinfo(a.dtype).max), 0.0, 1.0)
    return np.clip(a.astype(np.float64), 0.0, 1.0)


def _coerce(frame, gray: bool) -> np.ndarray:
    """One raw frame -> float64 [0,1]; grayscale (H,W) or RGB (H,W,3)."""
    a = np.asarray(frame)
    if a.ndim == 3 and a.shape[2] == 4:
        a = a[:, :, :3]
    a = _to01(a)
    if gray:
        if a.ndim == 2:
            return a
        if a.ndim == 3 and a.shape[2] == 1:
            return a[:, :, 0]
        if a.ndim == 3 and a.shape[2] == 3:
            return a @ _LUMA
    else:
        if a.ndim == 2:
            return np.repeat(a[:, :, None], 3, axis=2)
        if a.ndim == 3 and a.shape[2] == 1:
            return np.repeat(a, 3, axis=2)
        if a.ndim == 3 and a.shape[2] == 3:
            return a
    raise ValueError("unexpected frame shape %r" % (a.shape,))


def _auto_backend(source) -> str:
    if callable(source):
        return "callable"
    if isinstance(source, int):
        return "opencv"                              # a camera device index
    s = os.fspath(source) if not isinstance(source, str) else source
    if "://" in s:
        return "opencv"                              # a URL / RTSP / HTTP stream
    if any(ch in s for ch in "*?["):
        return "dir"                                 # a glob of images
    ext = os.path.splitext(s)[1].lower()
    if ext in _VIDEO_EXTS:
        return "opencv"                              # a video file
    # a still image, a directory, or an extension-less local path -> the 'dir'
    # server (a missing one then raises FileNotFoundError, not a vague open error)
    return "dir"


class Camera:
    """A frame source. Open, :meth:`grab`, :meth:`close` — or use as a context
    manager. See the module docstring for backends and *source* forms."""

    def __init__(self, source, backend: str = "auto", gray: bool = True,
                 retries: int = 3, **opts):
        self.source = source
        self.gray = bool(gray)
        self.retries = max(1, int(retries))
        self.opts = opts
        self.backend = _auto_backend(source) if backend in (None, "auto") else backend
        self._handle = None                          # backend-specific handle
        self._dir_files = None
        self._dir_pos = 0
        self._open()

    # ------------------------------------------------------------------ open --
    def _open(self):
        b = self.backend
        if b == "callable":
            if not callable(self.source):
                raise ValueError("callable backend needs a callable source")
            self._handle = self.source
        elif b == "dir":
            self._dir_files = self._list_dir(self.source)
            if not self._dir_files:
                raise FileNotFoundError("no images found for %r" % (self.source,))
        elif b == "opencv":
            cv2 = _cv2()
            if cv2 is None:
                raise RuntimeError("opencv backend needs opencv-python")
            cap = cv2.VideoCapture(self.source)
            if not cap.isOpened():
                raise RuntimeError("could not open camera/source %r" % (self.source,))
            self._handle = cap
        elif b == "genicam":
            self._open_genicam()
        elif b == "basler":
            self._open_basler()
        else:
            raise ValueError("unknown backend %r" % (b,))

    @staticmethod
    def _list_dir(source):
        s = os.fspath(source) if not isinstance(source, str) else source
        if os.path.isdir(s):
            files = [os.path.join(s, f) for f in sorted(os.listdir(s))
                     if os.path.splitext(f)[1].lower() in _IMG_EXTS]
        elif any(ch in s for ch in "*?["):
            files = sorted(glob.glob(s))
        else:
            files = [s] if os.path.isfile(s) else []
        return files

    def _open_genicam(self):  # pragma: no cover - needs hardware + a GenTL producer
        try:
            from harvesters.core import Harvester
        except Exception as e:
            raise RuntimeError("genicam backend needs 'harvesters' + a GenTL .cti: %s" % e)
        h = Harvester()
        for cti in self.opts.get("cti", []) or []:
            h.add_file(cti)
        h.update()
        ia = h.create(self.opts.get("index", 0))
        ia.start()
        self._handle = ("genicam", h, ia)

    def _open_basler(self):  # pragma: no cover - needs a Basler camera
        try:
            from pypylon import pylon
        except Exception as e:
            raise RuntimeError("basler backend needs 'pypylon': %s" % e)
        cam = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        cam.Open()
        cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        self._handle = ("basler", cam, pylon)

    # ------------------------------------------------------------------ grab --
    def _raw_grab(self):
        b = self.backend
        if b == "callable":
            return self._handle()
        if b == "dir":
            if not self._dir_files:
                return None
            path = self._dir_files[self._dir_pos % len(self._dir_files)]
            self._dir_pos += 1
            cv2 = _cv2()
            if cv2 is not None:
                im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                if im is None:
                    return None
                if im.ndim == 3 and im.shape[2] >= 3:
                    im = im[:, :, :3][:, :, ::-1]        # BGR -> RGB
                return im
            from PIL import Image
            return np.asarray(Image.open(path))
        if b == "opencv":
            ok, bgr = self._handle.read()
            if not ok or bgr is None:
                return None
            return bgr[:, :, ::-1] if bgr.ndim == 3 else bgr   # BGR -> RGB
        if b == "genicam":  # pragma: no cover
            _, _h, ia = self._handle
            with ia.fetch() as buf:
                comp = buf.payload.components[0]
                return np.array(comp.data.reshape(comp.height, comp.width))
        if b == "basler":  # pragma: no cover
            _, cam, pylon = self._handle
            res = cam.RetrieveResult(2000, pylon.TimeoutHandling_ThrowException)
            try:
                return np.array(res.Array) if res.GrabSucceeded() else None
            finally:
                res.Release()
        return None

    def grab(self):
        """Grab one frame as float64 ``[0,1]`` (gray or RGB). Retries a few times,
        then raises ``RuntimeError`` if the source yields nothing (disconnected
        camera, exhausted single-shot source)."""
        last = None
        for _ in range(self.retries):
            last = self._raw_grab()
            if last is not None:
                return _coerce(last, self.gray)
        raise RuntimeError("no frame from source %r (backend %s)" % (self.source, self.backend))

    def frames(self, n: int) -> list:
        """Grab *n* frames (list). For the ``dir`` backend it wraps around."""
        return [self.grab() for _ in range(int(n))]

    def stream(self, limit=None):
        """Yield frames until *limit* (or forever / until the source is exhausted).
        For the ``dir`` backend, stops after one pass rather than looping."""
        i = 0
        n_dir = len(self._dir_files) if self.backend == "dir" and self._dir_files else None
        while limit is None or i < int(limit):
            if n_dir is not None and i >= n_dir:
                return
            try:
                yield self.grab()
            except RuntimeError:
                return
            i += 1

    # ----------------------------------------------------------------- close --
    def close(self):
        b, h = self.backend, self._handle
        try:
            if b == "opencv" and h is not None:
                h.release()
            elif b == "genicam" and h is not None:  # pragma: no cover
                _, harv, ia = h
                ia.stop(); ia.destroy(); harv.reset()
            elif b == "basler" and h is not None:  # pragma: no cover
                _, cam, _pylon = h
                cam.StopGrabbing(); cam.Close()
        finally:
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def __repr__(self):
        return "Camera(%r, backend=%s, gray=%s)" % (self.source, self.backend, self.gray)


def list_cameras(max_index: int = 8) -> list:
    """Best-effort list of openable OpenCV device indices (``[0, 1, …]``).

    Probes indices ``0..max_index-1`` by opening and immediately closing them.
    Returns ``[]`` if OpenCV is unavailable. (Industrial GenICam/Basler devices
    are enumerated by their own SDKs, not here.)"""
    cv2 = _cv2()
    if cv2 is None:
        return []
    found = []
    for i in range(max(0, int(max_index))):
        cap = cv2.VideoCapture(i)
        try:
            if cap.isOpened():
                found.append(i)
        finally:
            cap.release()
    return found


# HALCON-style aliases ------------------------------------------------------- #
def open_framegrabber(source, backend: str = "auto", gray: bool = True, **opts) -> Camera:
    """Open a frame source (alias of :class:`Camera`; HALCON ``open_framegrabber``)."""
    return Camera(source, backend=backend, gray=gray, **opts)


def grab_image(cam: Camera):
    """Grab one frame from *cam* (HALCON ``grab_image``)."""
    return cam.grab()


def close_framegrabber(cam: Camera) -> None:
    """Close a frame source (HALCON ``close_framegrabber``)."""
    cam.close()
