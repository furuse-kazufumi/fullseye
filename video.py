"""video.py — read/write video & GIF clips as numpy frames (numpy-native, optional deps).

The temporal companion to :mod:`imgio`. Where ``imgio`` moves a single image in
and out, this turns a rendered *clip* — an onocollo physics video, an evis / hillco
pose capture, a stereo-pair sequence — into the frame arrays the :mod:`flow`,
:mod:`motion` and tracking stack consume, and writes annotated results back out.

Frames are float64 in ``[0, 1]``: grayscale ``(H, W)`` by default (what
:func:`flow.optical_flow_lk` expects) or RGB ``(H, W, 3)`` with ``gray=False``.

Reading and writing go through ``imageio`` (mp4 via the bundled
``imageio-ffmpeg`` plugin, GIF natively); if ``imageio`` is unavailable an
OpenCV (``cv2``) fallback covers mp4 reading. Both are optional — a clear
``RuntimeError`` is raised if neither is importable, so the numpy-only core of
the library never hard-depends on a video backend.

    import fullseye as fs
    frames = fs.read_frames("clip.mp4", max_frames=60, step=2)   # (T, H, W) gray [0,1]
    for a, b in fs.frame_pairs(frames):
        u, v = fs.optical_flow_lk(a, b)
"""
from __future__ import annotations

import os

import numpy as np

__all__ = [
    "read_frames", "iter_frames", "frame_pairs", "write_video", "probe",
]

# Container extensions handled by the ffmpeg/video path (everything else that is
# writable — .gif — goes through the Pillow animation path).
_VIDEO_EXTS = (".mp4", ".m4v", ".mov", ".avi", ".mkv", ".webm")

# Rec. 601 luma weights — the same gray convention imgio / the op registry use.
_LUMA = np.array([0.299, 0.587, 0.114], np.float64)


def _imageio():
    try:
        import imageio.v2 as imageio  # stable get_reader/mimsave API
        return imageio
    except Exception:
        try:
            import imageio  # very old installs
            return imageio
        except Exception:
            return None


def _cv2():
    try:
        import cv2
        return cv2
    except Exception:
        return None


def _to01(a: np.ndarray) -> np.ndarray:
    """Scale a raw decoded frame to float64 ``[0, 1]`` honestly by dtype.

    Unsigned-integer frames divide by their dtype max (uint8 → /255, uint16 →
    /65535). Signed-integer frames divide by the max and then clip (a negative
    sample maps to 0). Float frames are assumed already scaled and are clipped.
    """
    a = np.asarray(a)
    if np.issubdtype(a.dtype, np.integer):
        return np.clip(a.astype(np.float64) / float(np.iinfo(a.dtype).max), 0.0, 1.0)
    return np.clip(a.astype(np.float64), 0.0, 1.0)


def _coerce(frame, gray: bool) -> np.ndarray:
    """One decoded frame → float64 ``[0,1]``; grayscale ``(H,W)`` or RGB ``(H,W,3)``."""
    a = np.asarray(frame)
    if a.ndim == 3 and a.shape[2] == 4:          # RGBA → drop alpha
        a = a[:, :, :3]
    a = _to01(a)
    if gray:
        if a.ndim == 2:
            return a
        if a.ndim == 3 and a.shape[2] == 1:
            return a[:, :, 0]
        if a.ndim == 3 and a.shape[2] == 3:
            return a @ _LUMA
        raise ValueError("unexpected frame shape %r" % (a.shape,))
    # colour requested
    if a.ndim == 2:
        return np.repeat(a[:, :, None], 3, axis=2)
    if a.ndim == 3 and a.shape[2] == 1:
        return np.repeat(a, 3, axis=2)
    if a.ndim == 3 and a.shape[2] == 3:
        return a
    raise ValueError("unexpected frame shape %r" % (a.shape,))


def _iter_cv2(path):
    """Fallback frame iterator via OpenCV (BGR uint8 → RGB). Callers check the
    file exists first, so an open failure here means undecodable, not missing."""
    cv2 = _cv2()
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError("could not decode %s (corrupt or unsupported format)" % path)
    try:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            yield bgr[:, :, ::-1]                 # BGR → RGB
    finally:
        cap.release()


def iter_frames(path: str, gray: bool = True, step: int = 1, start: int = 0,
                max_frames=None):
    """Yield frames from *path* one at a time (memory-friendly for long clips).

    Parameters
    ----------
    path       : mp4 / gif / any container the backend supports.
    gray       : grayscale ``(H, W)`` (default) or RGB ``(H, W, 3)``.
    step       : keep every *step*-th frame (``step=2`` halves the frame rate).
    start      : skip this many leading frames before the first kept frame.
    max_frames : stop after yielding this many kept frames (``None`` = all).

    Frames are float64 in ``[0, 1]``. Being a generator, errors surface when it is
    iterated (not at call): ``FileNotFoundError`` for a missing path, and
    ``RuntimeError`` if no video backend is available or the file cannot be
    decoded. Accepts a ``str`` or ``os.PathLike``.

    Resource note: the underlying reader is released when iteration finishes, the
    generator is ``.close()``-d, or it is garbage-collected. If you abandon it
    early (``break``) and need the file handle freed at once — relevant on Windows
    — call ``.close()`` on the generator, or use the eager :func:`read_frames`.
    """
    path = os.fspath(path)                      # accept str or pathlib.Path
    step = max(1, int(step))
    start = max(0, int(start))
    cap = None if max_frames is None else max(0, int(max_frames))
    if cap == 0:
        return
    # a truly-missing file is FileNotFoundError; a file that exists but fails to
    # decode surfaces the backend's real error (not a misleading "not found").
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    imageio = _imageio()
    if imageio is not None:
        reader = None
        try:
            reader = imageio.get_reader(path)
        except FileNotFoundError:
            raise
        except Exception as e:
            if _cv2() is None:
                raise RuntimeError("could not open %s: %s" % (path, e))
            reader = None                       # unopenable by imageio -> try cv2 below
        if reader is not None:
            kept = 0
            ok = True
            try:
                for i, fr in enumerate(reader):
                    if i < start or (i - start) % step:
                        continue
                    yield _coerce(fr, gray)
                    kept += 1
                    if cap is not None and kept >= cap:
                        break
            except Exception:
                ok = False                      # decode failure part-way through
            finally:
                reader.close()
            if ok:
                return
            if kept > 0:
                # already yielded frames — cannot cleanly restart from a different
                # backend without duplicating them, so surface the decode error.
                raise RuntimeError("decode error after %d frame(s) in %s" % (kept, path))
            # imageio decoded nothing before failing -> fall through to the cv2 path

    if _cv2() is not None:
        kept = 0
        for i, fr in enumerate(_iter_cv2(path)):
            if i < start or (i - start) % step:
                continue
            yield _coerce(fr, gray)
            kept += 1
            if cap is not None and kept >= cap:
                break
        return

    raise RuntimeError(
        "read_frames needs imageio (with imageio-ffmpeg for mp4) or opencv-python")


def read_frames(path: str, gray: bool = True, step: int = 1, start: int = 0,
                max_frames=None) -> np.ndarray:
    """Read a clip into a single array: ``(T, H, W)`` gray or ``(T, H, W, 3)`` RGB.

    A thin eager wrapper over :func:`iter_frames` (same arguments). Use
    :func:`iter_frames` instead when a clip will not fit comfortably in memory.
    Raises ``ValueError`` if the clip decodes to zero frames or the frames are
    not all the same shape.
    """
    frames = list(iter_frames(path, gray=gray, step=step, start=start,
                              max_frames=max_frames))
    if not frames:
        raise ValueError("no frames read from %s" % path)
    shapes = {f.shape for f in frames}
    if len(shapes) != 1:
        raise ValueError("frames have differing shapes: %r" % (sorted(shapes),))
    return np.stack(frames, axis=0)


def frame_pairs(frames):
    """Yield consecutive ``(prev, nxt)`` frame pairs from a sequence/array.

    ``for a, b in frame_pairs(read_frames("clip.mp4")): flow(a, b)`` — the
    canonical two-frame loop the flow/motion functions consume.
    """
    seq = frames if hasattr(frames, "__len__") else list(frames)
    for i in range(len(seq) - 1):
        yield seq[i], seq[i + 1]


def _to_uint8_frame(f) -> np.ndarray:
    """A gray/RGB frame → uint8 for encoding.

    uint8 passes through; any other integer dtype (uint16, int) is scaled by its
    dtype range (so a real 16-bit frame is not silently crushed to 0/1); a float
    frame is treated as already in ``[0, 1]`` and clipped.
    """
    a = np.asarray(f)
    if a.dtype == np.uint8:
        return a
    a01 = _to01(a) if np.issubdtype(a.dtype, np.integer) else np.clip(
        np.asarray(a, np.float64), 0.0, 1.0)
    return np.round(a01 * 255.0).astype(np.uint8)


def write_video(path: str, frames, fps: float = 30.0) -> None:
    """Encode a sequence of frames to *path* (``.mp4`` or ``.gif``).

    *frames* is any iterable of gray ``(H, W)`` or RGB ``(H, W, 3)`` arrays, each
    float ``[0, 1]`` or already uint8. mp4 needs even width/height (H.264): odd
    dimensions are padded by one pixel (edge-replicated) so encoding never fails
    silently. Raises ``RuntimeError`` if imageio is unavailable and ``ValueError``
    for an empty sequence.
    """
    path = os.fspath(path)
    imageio = _imageio()
    if imageio is None:
        raise RuntimeError("write_video needs imageio (with imageio-ffmpeg for mp4)")
    seq = [_to_uint8_frame(f) for f in frames]
    if not seq:
        raise ValueError("no frames to write")
    if path.lower().endswith(_VIDEO_EXTS):
        padded = []
        for a in seq:
            ph = a.shape[0] % 2
            pw = a.shape[1] % 2
            if ph or pw:
                pad = [(0, ph), (0, pw)] + ([(0, 0)] if a.ndim == 3 else [])
                a = np.pad(a, pad, mode="edge")
            padded.append(a)
        seq = padded
        # macro_block_size=1 stops imageio-ffmpeg from silently resizing the frame
        # up to a multiple of 16 (which would change the array's width/height); the
        # even-padding above already satisfies libx264's yuv420p ÷2 requirement.
        imageio.mimsave(path, seq, fps=float(fps), macro_block_size=1)
    else:
        # GIF (Pillow plugin): the per-frame delay is `duration` in MILLISECONDS.
        # Passing duration=1/fps (seconds) truncates to a 0 ms delay (fps inert);
        # `fps=` works but is deprecated in imageio 2.28+. Convert explicitly.
        imageio.mimsave(path, seq, duration=1000.0 / float(fps))


def probe(path: str) -> dict:
    """Best-effort clip metadata: ``{"fps", "size" (w, h), "nframes"}``.

    Values the container/plugin does not advertise are ``None`` — ``nframes`` is
    commonly ``None`` for mp4 (the backend will not count without decoding the
    whole stream). For GIF, ``fps`` is derived from the per-frame delay and
    ``size`` from the first frame. Never raises: an unreadable/absent path yields
    all-``None`` rather than an error. Accepts a ``str`` or ``os.PathLike``.
    """
    out = {"fps": None, "size": None, "nframes": None}
    imageio = _imageio()
    if imageio is None:
        return out
    try:
        reader = imageio.get_reader(os.fspath(path))
    except Exception:
        return out
    try:
        meta = reader.get_meta_data() or {}
        fps = meta.get("fps")
        if not fps and meta.get("duration"):        # GIF: per-frame delay in ms
            try:
                fps = 1000.0 / float(meta["duration"])
            except Exception:
                fps = None
        out["fps"] = float(fps) if fps else None
        size = meta.get("size")
        if not size:                                # GIF meta often lacks size
            try:
                fr = np.asarray(reader.get_data(0))
                size = (fr.shape[1], fr.shape[0])   # (width, height)
            except Exception:
                size = None
        out["size"] = (int(size[0]), int(size[1])) if size else None
        n = meta.get("nframes")
        if isinstance(n, (int, float)) and np.isfinite(n) and n > 0:
            out["nframes"] = int(n)
    except Exception:
        pass
    finally:
        reader.close()
    return out
