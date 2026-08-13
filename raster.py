"""Bit-depth-preserving raster I/O and metric depth import (numpy + backends).

The *import* side of the perception stack for images that carry more than 8 bits
per sample. The rest of the library (``imgio.py``, the operator suite) speaks
float64 in ``[0, 1]``; that is the right contract for display and for 8-bit
photographs, but it silently destroys the extra precision of the sensors a
physical-AI / inspection project actually feeds in:

  * a **16-bit PNG** (medical, microscopy, HDR intermediate) has 65 536 levels;
  * a **float32 / 16-bit / tiled / multi-sample TIFF** (scientific camera, GIS,
    a rendered radiance buffer) is not ``[0, 1]`` at all;
  * a **metric depth map** (RealSense / Kinect give integer millimetres in a
    16-bit PNG; a renderer gives float metres in a TIFF or PFM) must come back in
    metres with the invalid pixels marked, not scaled into ``[0, 1]``.

This module reads those *without* demoting them, and exposes normalisation as an
**explicit** step (:func:`to01`) so a caller who wants the raw values keeps them.

Backends (all already installed; none GPL, none added as a hard dependency):

  ``imageio`` (v2 API)  8/16-bit PNG and other common rasters — keeps ``uint16``.
  ``tifffile``          TIFF: 8/16/32-bit, integer or float, multi-sample, tiled.
  ``opencv`` (``cv2``)  fallback decoder (``IMREAD_UNCHANGED`` keeps bit depth).
  PFM                   read/written here in pure numpy (~40 lines, no backend).

Provenance of the formats:

  * PNG bit depth — the PNG (Portable Network Graphics) spec, W3C/ISO 15948;
    16-bit-per-sample grayscale/RGB is part of the base spec.
  * TIFF sample formats — Adobe *TIFF 6.0* specification (``SampleFormat`` =
    unsigned / signed / IEEE float; ``BitsPerSample`` 8/16/32).
  * PFM (Portable Float Map) — Paul Debevec's HDRShop format, as used by the
    Middlebury stereo benchmark: header ``PF``/``Pf``, ``W H``, a signed scale
    whose sign is the byte order (negative = little-endian), then IEEE-754
    float32 samples stored **bottom row first**.
  * Depth-as-16-bit-millimetres — the convention of the Intel RealSense SDK and
    Microsoft Kinect: an unsigned 16-bit image whose integer values are depth in
    millimetres, with ``0`` reserved for "no reading".

Honest limitations (nothing here claims more than a round-trip test proves):

  * :func:`read_raster` returns the sample values and channel order the backend
    hands back (e.g. imageio/PNG gives RGB, ``cv2`` fallback is converted from
    BGR; no colour-space management is done).
  * :func:`to01` divides integers by their dtype maximum; **float** inputs are
    assumed already normalised and are only clipped into ``[0, 1]`` — it does not
    rescale radiance/metric floats.
  * :func:`save16` writing a float array to a 16-bit PNG **quantises** it to
    65 536 levels (documented, lossy); a float array to a ``.tif`` is written as
    ``float32`` and keeps full precision. 32-bit-float PNG is not a standard PNG
    sample format and is **not** produced.
  * Fail-closed on untrusted files: the pixel count is capped
    (:data:`MAX_PIXELS`) *before* the array is allocated where the format lets us
    read the dimensions cheaply (PNG ``IHDR``, TIFF directory, PFM header); a
    missing file raises ``FileNotFoundError``; an unknown extension or an
    undecodable/oversized file raises ``ValueError`` naming the path.
"""
from __future__ import annotations

import io
import os

import numpy as np

__all__ = [
    "read_raster", "to01", "read_depth", "read_pfm", "write_pfm", "save16",
    "RASTER_FORMATS", "DEPTH_FORMATS", "MAX_PIXELS",
]

#: Extensions :func:`read_raster` accepts.
RASTER_FORMATS = (".png", ".tif", ".tiff", ".pfm", ".jpg", ".jpeg", ".bmp")
#: Extensions :func:`read_depth` accepts.
DEPTH_FORMATS = (".png", ".tif", ".tiff", ".pfm")
#: Refuse an image with more than this many pixels (H*W) before allocating it.
MAX_PIXELS = 1 << 28              # 268_435_456 px = a 16384 x 16384 image
#: Guard for whole-file reads (PFM is read whole to parse its header).
_MAX_FILE_BYTES = 1 << 30         # 1 GiB


# ---- low-level guards ------------------------------------------------------ #
def _ext(path) -> str:
    return os.path.splitext(str(path))[1].lower()


def _channels(a: np.ndarray) -> int:
    return 1 if a.ndim == 2 else int(a.shape[-1])


def _check_pixels(shape, src: str) -> int:
    """Refuse a declared image size over the cap *before* the buffer is made."""
    dims = [int(x) for x in shape]
    if len(dims) >= 2:
        px = dims[0] * dims[1]
    elif len(dims) == 1:
        px = dims[0]
    else:
        px = 1
    if px < 0:
        raise ValueError("%s: negative pixel count (%d)" % (src, px))
    if px > MAX_PIXELS:
        raise ValueError("%s: %d pixels over the %d cap (raster.MAX_PIXELS)"
                         % (src, px, MAX_PIXELS))
    return px


def _png_dims(path: str):
    """(h, w) from a PNG IHDR without decoding, or None if not a PNG header."""
    try:
        with open(path, "rb") as f:
            head = f.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    w = int.from_bytes(head[16:20], "big")
    h = int.from_bytes(head[20:24], "big")
    return (h, w)


def _cv2():
    try:
        import cv2
        return cv2
    except Exception:
        return None


# ---- normalisation (explicit, never automatic) ----------------------------- #
def to01(arr, meta=None) -> np.ndarray:
    """Return a float64 view of *arr* in ``[0, 1]`` **without** touching the raw
    read.

    Integer samples are divided by their dtype maximum (``uint16`` -> /65535,
    ``uint8`` -> /255), ``bool`` maps to 0/1, and **float** samples are assumed
    already normalised and merely clipped into ``[0, 1]`` (see the module
    limitations — this does not rescale metric/radiance floats). *meta* is
    accepted for symmetry with :func:`read_raster` but the dtype of *arr* is
    authoritative.
    """
    a = np.asarray(arr)
    if a.dtype == bool:
        return a.astype(np.float64)
    if a.dtype.kind in "ui":
        return a.astype(np.float64) / float(np.iinfo(a.dtype).max)
    return np.clip(a.astype(np.float64), 0.0, 1.0)


# ---- TIFF ------------------------------------------------------------------ #
def _read_tiff(path: str):
    import tifffile
    try:
        tf = tifffile.TiffFile(path)
    except Exception as e:
        raise ValueError("cannot open TIFF: %s (%s)" % (path, e))
    try:
        series = tf.series[0]
        _check_pixels(series.shape, path)          # ValueError on oversize
        page = tf.pages[0]
        photometric, resolution = None, None
        try:
            photometric = int(page.photometric)
        except Exception:
            pass
        try:
            xr = page.tags.get("XResolution")
            yr = page.tags.get("YResolution")
            if xr is not None:
                resolution = (xr.value, yr.value if yr is not None else None)
        except Exception:
            pass
        try:
            arr = series.asarray()
        except Exception as e:
            raise ValueError("cannot decode TIFF: %s (%s)" % (path, e))
    finally:
        tf.close()
    arr = np.asarray(arr)
    meta = {"src_dtype": str(arr.dtype), "channels": _channels(arr),
            "shape": tuple(int(x) for x in arr.shape), "backend": "tifffile"}
    if photometric is not None:
        meta["photometric"] = photometric
    if resolution is not None:
        meta["resolution"] = resolution
    return arr, meta


# ---- imageio / cv2 (PNG, JPG, BMP) ----------------------------------------- #
def _read_imageio(path: str, ext: str):
    # Cheap pixel pre-check where the header exposes the dimensions.
    dims = None
    try:
        import imageio.v3 as iio3
        dims = tuple(int(x) for x in iio3.improps(path).shape)
    except Exception:
        dims = _png_dims(path) if ext == ".png" else None
    if dims is not None:
        _check_pixels(dims, path)                  # ValueError on oversize

    arr = None
    try:
        import imageio.v2 as iio
        arr = np.asarray(iio.imread(path))
    except Exception:
        arr = None
    if arr is None:                                # fall back to cv2 (keeps depth)
        cv2 = _cv2()
        if cv2 is not None:
            im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if im is not None:
                if im.ndim == 3 and im.shape[-1] >= 3:
                    im = im[:, :, ::-1]            # BGR -> RGB
                arr = np.asarray(im)
    if arr is None:
        raise ValueError("cannot decode image: %s (no imageio / opencv backend "
                         "could read it)" % path)
    _check_pixels(arr.shape, path)                 # post-decode safety net
    meta = {"src_dtype": str(arr.dtype), "channels": _channels(arr),
            "shape": tuple(int(x) for x in arr.shape), "backend": "imageio"}
    return arr, meta


# ---- public raster reader --------------------------------------------------- #
def read_raster(path, keep_dtype: bool = True):
    """Read a raster **preserving its native bit depth** -> ``(arr, meta)``.

    16-bit PNG comes back as ``uint16`` (not demoted to ``uint8``); a float or
    16-bit or tiled or multi-sample TIFF comes back in its own dtype; PFM comes
    back as ``float32``. *meta* is a dict with ``src_dtype``, ``channels``,
    ``shape`` and ``backend`` (plus ``photometric`` / ``resolution`` for TIFF and
    ``pfm_scale`` for PFM when available).

    With ``keep_dtype=False`` the array is passed through :func:`to01` and
    returned as float64 ``[0, 1]`` (``meta['normalized']`` is set); the default
    ``keep_dtype=True`` never rescales — call :func:`to01` yourself.

    Raises ``FileNotFoundError`` for a missing file, ``ValueError`` for an
    unsupported extension, an undecodable file, or a pixel count over
    :data:`MAX_PIXELS`.
    """
    p = str(path)
    ext = _ext(p)
    if ext not in RASTER_FORMATS:
        raise ValueError("unsupported raster format %r for %s — read_raster handles %s"
                         % (ext, p, ", ".join(RASTER_FORMATS)))
    if not os.path.isfile(p):
        raise FileNotFoundError(p)
    if ext == ".pfm":
        arr, scale = read_pfm(p)
        meta = {"src_dtype": str(arr.dtype), "channels": _channels(arr),
                "shape": tuple(int(x) for x in arr.shape), "backend": "pfm",
                "pfm_scale": scale}
    elif ext in (".tif", ".tiff"):
        arr, meta = _read_tiff(p)
    else:
        arr, meta = _read_imageio(p, ext)
    if not keep_dtype:
        arr = to01(arr, meta)
        meta = dict(meta, normalized=True)
    return arr, meta


# ---- metric depth ----------------------------------------------------------- #
def read_depth(path, scale: float = 0.001, invalid_value=0):
    """Read a metric depth map -> ``(depth, valid)``.

    *depth* is float64 ``(H, W)`` in metres with ``NaN`` at invalid pixels;
    *valid* is a bool mask (``True`` where a real reading exists).

    Handled by extension:

      * **16-bit PNG** — integer *millimetres* (the RealSense / Kinect
        convention). Values are multiplied by *scale* (default ``0.001`` =
        mm -> m); pixels equal to *invalid_value* (default ``0``) become ``NaN``.
      * **TIFF** — a float TIFF is already metric and is passed through; an
        integer TIFF is treated like the PNG case (scaled by *scale*).
      * **PFM** — already-metric float32 (a renderer's depth buffer), passed
        through.

    Non-finite samples and samples equal to *invalid_value* are always marked
    invalid. A multi-channel source uses channel 0.
    """
    p = str(path)
    ext = _ext(p)
    if ext not in DEPTH_FORMATS:
        raise ValueError("unsupported depth format %r for %s — read_depth handles %s"
                         % (ext, p, ", ".join(DEPTH_FORMATS)))
    if ext == ".pfm":
        arr, _ = read_pfm(p)
        src_int = False
    else:
        arr, _ = read_raster(p, keep_dtype=True)
        src_int = np.asarray(arr).dtype.kind in "ui"
    a = np.asarray(arr)
    if a.ndim == 3:                                # depth is single-channel
        a = a[..., 0]
    if a.ndim != 2:
        raise ValueError("%s: expected a 2-D depth image, got shape %r" % (p, (a.shape,)))

    if src_int:
        invalid = (a == invalid_value)
        depth = a.astype(np.float64) * float(scale)
    else:
        depth = a.astype(np.float64)
        invalid = (depth == float(invalid_value))
    invalid = invalid | ~np.isfinite(depth)
    depth = depth.copy()
    depth[invalid] = np.nan
    return depth, ~invalid


# ---- PFM (Portable Float Map, pure numpy) ---------------------------------- #
def read_pfm(path):
    """Read a PFM (Portable Float Map) -> ``(arr, scale)``.

    *arr* is float32 ``(H, W)`` for a ``Pf`` (grayscale) file or ``(H, W, 3)`` for
    a ``PF`` (colour) file, restored to **top-to-bottom** row order (PFM stores
    the bottom row first). *scale* is the header's absolute scale factor; the
    header's *sign* selects the byte order (negative = little-endian) per the
    Debevec / Middlebury spec and is consumed here.

    Fail-closed: a bad identifier, a non-integer/non-positive dimension, a
    zero/non-finite scale, a pixel count over :data:`MAX_PIXELS`, or a declared
    size larger than the bytes actually present all raise ``ValueError``. A
    missing file raises ``FileNotFoundError``.
    """
    p = str(path)
    if not os.path.isfile(p):
        raise FileNotFoundError(p)
    size = os.path.getsize(p)
    if size == 0:
        raise ValueError("%s: empty PFM file" % p)
    if size > _MAX_FILE_BYTES:
        raise ValueError("%s: %d bytes over the %d-byte cap (raster)" % (p, size, _MAX_FILE_BYTES))
    with open(p, "rb") as fh:
        raw = fh.read()
    f = io.BytesIO(raw)

    ident = f.readline().strip()
    if ident == b"PF":
        channels = 3
    elif ident == b"Pf":
        channels = 1
    else:
        raise ValueError("%s: not a PFM file (identifier %r, expected 'PF' or 'Pf')"
                         % (p, ident[:8]))

    dim_toks = f.readline().decode("ascii", "replace").split()
    if len(dim_toks) != 2:
        raise ValueError("%s: malformed PFM dimension line %r" % (p, dim_toks))
    try:
        w, h = int(dim_toks[0]), int(dim_toks[1])
    except ValueError:
        raise ValueError("%s: non-integer PFM dimensions %r" % (p, dim_toks)) from None
    if w <= 0 or h <= 0:
        raise ValueError("%s: non-positive PFM dimensions %d x %d" % (p, w, h))
    _check_pixels((h, w), p)

    scale_tok = f.readline().decode("ascii", "replace").strip()
    try:
        scale = float(scale_tok)
    except ValueError:
        raise ValueError("%s: non-numeric PFM scale %r" % (p, scale_tok)) from None
    if not np.isfinite(scale) or scale == 0.0:
        raise ValueError("%s: invalid PFM scale %r (must be non-zero and finite)" % (p, scale))

    endian = "<" if scale < 0 else ">"
    count = w * h * channels
    need = count * 4
    data = raw[f.tell():]
    if len(data) < need:
        raise ValueError("%s: PFM declares %dx%dx%d (%d float bytes) but only %d bytes remain"
                         % (p, h, w, channels, need, len(data)))
    flat = np.frombuffer(data[:need], dtype=endian + "f4")
    arr = np.array(flat, dtype=np.float32)         # owned, native-endian float32
    arr = arr.reshape(h, w, channels) if channels == 3 else arr.reshape(h, w)
    arr = np.ascontiguousarray(arr[::-1])          # bottom-to-top on disk -> top-to-bottom
    return arr, abs(scale)


def write_pfm(path, arr, scale: float = 1.0) -> None:
    """Write a PFM (Portable Float Map). *arr* is ``(H, W)`` (writes ``Pf``) or
    ``(H, W, 3)`` (writes ``PF``); it is cast to float32.

    The **sign of** *scale* selects the byte order written (negative =
    little-endian, positive = big-endian, per the Debevec / Middlebury spec); its
    magnitude is the scale factor recorded in the header. Rows are written
    bottom-first, so :func:`read_pfm` restores the original orientation exactly.
    """
    a = np.asarray(arr)
    if a.dtype != np.float32:
        a = a.astype(np.float32)
    if a.ndim == 2:
        color = False
    elif a.ndim == 3 and a.shape[2] == 3:
        color = True
    else:
        raise ValueError("write_pfm needs (H, W) or (H, W, 3), got %r" % (a.shape,))
    if not np.isfinite(scale) or scale == 0.0:
        raise ValueError("write_pfm scale must be non-zero and finite, got %r" % (scale,))
    little = scale < 0.0
    endian = "<" if little else ">"
    signed = -abs(scale) if little else abs(scale)
    header = ("PF\n" if color else "Pf\n") + ("%d %d\n" % (a.shape[1], a.shape[0])) \
        + ("%f\n" % signed)
    body = np.ascontiguousarray(a[::-1], dtype=endian + "f4")   # bottom row first
    with open(str(path), "wb") as fh:
        fh.write(header.encode("ascii"))
        fh.write(body.tobytes())


# ---- 16-bit / float writer -------------------------------------------------- #
def save16(path, arr) -> None:
    """Write *arr* at high precision, choosing the container by extension.

    ``.png`` -> a 16-bit PNG (``imageio``). A ``uint16`` array is written as-is; a
    float array in ``[0, 1]`` is scaled to ``uint16`` (``round(x * 65535)``) —
    this **quantises** to 65 536 levels (documented, lossy).

    ``.tif`` / ``.tiff`` -> a TIFF (``tifffile``). A float array is written as
    ``float32`` and keeps full precision; a ``uint16`` array is written as
    ``uint16``.

    32-bit-float PNG is not a standard PNG sample format and is not produced —
    use a ``.tif`` to keep float precision.
    """
    p = str(path)
    ext = _ext(p)
    a = np.asarray(arr)
    if ext == ".png":
        import imageio.v2 as iio
        if a.dtype == np.uint16:
            out = a
        elif a.dtype == np.uint8:
            out = a.astype(np.uint16) * 257                     # 0..255 -> 0..65535
        elif a.dtype.kind == "f":
            out = (np.clip(a, 0.0, 1.0) * 65535.0 + 0.5).astype(np.uint16)
        else:
            out = np.clip(a, 0, 65535).astype(np.uint16)
        iio.imwrite(p, out)
    elif ext in (".tif", ".tiff"):
        import tifffile
        if a.dtype.kind == "f":
            out = a.astype(np.float32)                          # preserve precision
        elif a.dtype == np.uint16:
            out = a
        else:
            out = a.astype(np.uint16)
        tifffile.imwrite(p, out)
    else:
        raise ValueError("unsupported save16 format %r for %s — save16 handles "
                         ".png (16-bit), .tif/.tiff (16-bit or float32)" % (ext, p))
