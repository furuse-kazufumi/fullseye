"""acquire.py — image acquisition from cameras and sources (HALCON framegrabber analog).

The front of a machine-vision loop: grab a frame from a source and hand it
straight to a pipeline / :class:`~engine.FullseyeEngine`. Mirrors HALCON's
``open_framegrabber`` / ``grab_image`` / ``close_framegrabber``.

Backends (chosen by ``backend=`` or auto-detected from *source*). ``capabilities()``
reports, per backend, whether the SDK is importable here (``available``) and whether this
module has an opener for it (``implemented``) — two different questions, see below:

- ``"opencv"``   — ``cv2.VideoCapture``: USB/UVC webcams (device index ``0,1,…``),
  IP / RTSP streams, and video files. Default for an int or a URL/path. Needs
  ``opencv-python``.
- ``"dir"``      — a folder or glob of images, served in filename order. The
  offline / batch-inspection path, and what the tests use (no hardware needed).
- ``"callable"`` — any ``fn() -> frame`` you supply: a custom SDK, a generator, or
  a mock. Nothing to install. Accepts ``pixel_format=`` / ``bit_depth=`` / ``unit=``
  so a mock can report what a real device would — which is how the 12-bit scaling
  and the metres contract stay testable without hardware.
- ``"genicam"``  — industrial GigE / USB3 Vision through the ``harvesters`` GenTL
  producer (**optional**: ``pip install harvesters`` + a vendor ``.cti``).
- ``"basler"``   — Basler via ``pypylon`` (**optional**).
- ``"vimba"``    — Allied Vision Vimba X via ``vmbpy`` (**optional**).
- ``"realsense"`` / ``"oak"`` / ``"zed"`` / ``"kinect"`` — depth cameras
  (``pyrealsense2`` / ``depthai`` / ``pyzed`` / ``pyk4a``, all **optional**).

**What a frame is.** Image backends return float64 in ``[0, 1]``: grayscale ``(H, W)``
by default or RGB ``(H, W, 3)`` with ``gray=False`` — the same convention as
:mod:`video` / the operator library, so ``engine.run(cam.grab())`` just works.
**Depth backends return float64 metres** and are NEVER rescaled to ``[0, 1]``: a
distance is a measurement, and 35 ledger operators take the ``depth`` sort expecting a
physical unit. ``capabilities()[i]["unit"]`` says which you get, and ``DEPTH_BACKENDS``
lists the metric ones.

**Two defects this module used to have** (both measured 2026-09-24, both fixed, both
now gated by ``tests/test_acquire_contract.py``):

1. The catalogue announced nine backends while ``Camera._open`` branched on five, so
   ``realsense`` / ``oak`` / ``zed`` / ``kinect`` answered ``ValueError: unknown backend``
   even with the SDK installed. ``_open`` now dispatches *through* the table and a gate
   asserts every declared backend has an opener.
2. Integer buffers were scaled by the **container** maximum, so a 12-bit sensor's frame
   in a uint16 buffer came out ``4095/65535`` — a factor of ``(2^16-1)/(2^12-1)`` =
   16.0037 too dark, with no exception, quietly wrong for every threshold downstream.
   Backends now report the pixel format, :func:`bit_depth_of` turns the GenICam SFNC
   name into significant bits, and nothing is guessed: an unknown format is refused.

``grab()`` returns a bare array (every existing caller keeps working); ``grab_frame()``
returns a :class:`Frame` carrying the pixel format, significant bits, device timestamp
and its source, frame id and effective exposure — the facts you need to notice a dropped
frame or align two cameras, which an array alone cannot express.

    import fullseye
    with fullseye.Camera(0) as cam:              # webcam / framegrabber
        frame = cam.grab()
        result = eng.run(frame)                  # inspect

    acquire.list_devices()                       # every available backend, not just OpenCV
    acquire.coverage()                           # {"declared": 10, "implemented": 10, ...}
"""
from __future__ import annotations

import glob
import os
import sys
import time

import numpy as np

#: ★公開面は**本体から数える**(`tests/test_acquire_contract.py` の門が AST で
#:   読み、ここと突き合わせる)。`dir()` は環境で変わるので一次情報はこちら。
#:   2026-09-25 まで 7 つ足りていなかった —— 追記のつもりが当たっていなかった。
__all__ = [
    # 装置を開く・撮る
    "Camera", "Frame", "list_cameras", "list_devices", "capabilities", "coverage",
    "open_framegrabber", "grab_image", "close_framegrabber",
    # 画素形式(PFNC を分母にした表)
    "PIXEL_BITS", "PACKED_FORMATS", "NOT_CARRIED", "bit_depth_of",
    "unpack", "unpack_lsb", "unpack_grouped",
    # 機能名(SFNC を分母にした表)
    "SFNC_FEATURES", "SFNC_REQUIRED",
    # webcam の機能名(UVC を分母にした表)
    "UVC_CONTROLS", "UVC_TO_SFNC", "UVC_EXPOSURE_STEP_US", "UVC_UNCOMPRESSED",
    "uvc_to_sfnc", "sfnc_to_uvc",
    # GenTL のプロデューサ探索
    "GENTL_PATH_VARS", "gentl_producers",
    # 8 軸の自己採点
    "COVERAGE_AXES", "axes",
    # 奥行き backend の単位
    "DEPTH_BACKENDS",
]

# Acquisition backends catalogue (native + optional industrial / Physical-AI sensors).
#
# ★2026-09-24: the table used to carry rows this module could not open. ``capabilities()``
# announced nine backends while ``Camera._open`` branched on five, so ``realsense``, ``oak``,
# ``zed`` and ``kinect`` answered ``ValueError: unknown backend`` even with the SDK installed —
# a declaration/implementation split of exactly the kind a "registered only" gate is blind to.
# Each row now names the opener, ``_open`` dispatches THROUGH the table, and
# ``test_acquire_contract.py`` asserts every declared backend has one.
#
# ``unit`` is the physical meaning of what ``grab()`` returns:
#   "normalised" -> float64 in [0, 1] (an image)
#   "m"          -> float64 metres   (a depth map; NEVER rescaled to [0, 1], which would
#                                     destroy the measurement — 35 ledger ops take `depth`)
# (name, module-to-probe, pip, kind, unit, opener, one-line desc)
_BACKENDS = [
    ("opencv", "cv2", "opencv-python", "optional", "normalised", "_open_opencv",
     "USB/UVC webcam, IP/RTSP stream, video file"),
    ("dir", None, None, "native", "normalised", "_open_dir",
     "a folder / glob of images (offline & tests)"),
    ("callable", None, None, "native", "normalised", "_open_callable",
     "a user-supplied fn() -> frame"),
    ("genicam", "harvesters", "harvesters", "optional", "normalised", "_open_genicam",
     "GigE/USB3 Vision via GenTL (industrial)"),
    ("basler", "pypylon", "pypylon", "optional", "normalised", "_open_basler",
     "Basler cameras (pypylon)"),
    ("vimba", "vmbpy", "vmbpy", "optional", "normalised", "_open_vimba",
     "Allied Vision Vimba X (vmbpy)"),
    ("realsense", "pyrealsense2", "pyrealsense2", "optional", "m", "_open_realsense",
     "Intel RealSense RGB-D (depth in metres)"),
    ("oak", "depthai", "depthai", "optional", "m", "_open_oak",
     "Luxonis OAK-D stereo depth (depth in metres)"),
    ("zed", "pyzed", "pyzed", "optional", "m", "_open_zed",
     "Stereolabs ZED stereo depth (depth in metres)"),
    ("kinect", "pyk4a", "pyk4a", "optional", "m", "_open_kinect",
     "Azure Kinect DK depth (discontinued; Orbbec is the successor)"),
]

#: Backends whose frames are a physical distance, not a picture.
DEPTH_BACKENDS = tuple(n for n, _m, _p, _k, unit, _o, _d in _BACKENDS if unit == "m")

#: name -> row, so every lookup goes through the one catalogue.
_BACKEND_BY_NAME = {row[0]: row for row in _BACKENDS}


#: The eight axes a device SDK is scored on, and where this module answers each.
#:
#: The same eight are used to score published SDKs in a separate corpus, so the two
#: assessments can be compared. Scoring this module on a different list would make
#: "we cover more than SDK X" meaningless.
#:
#: ★No count of those SDKs is written here. The corpus lives in another tree, so a
#: number quoted here has no gate keeping it true -- it said "13" while the corpus
#: had grown to 28 (2026-09-25). A figure nothing can check is worse than no figure.
#:
#: Each value names **things that must exist** -- a test resolves every one of them,
#: so a rename or a deletion turns the claim red instead of leaving a stale boast.
COVERAGE_AXES = {
    "enumeration": ("list_devices", "_enumerate", "gentl_producers"),
    "acquisition_mode": ("Camera.grab", "Camera.frames", "Camera.stream",
                         "Camera.grab_frame"),
    "buffer": ("Camera._raw_grab",),
    "pixel_format": ("PIXEL_BITS", "PACKED_FORMATS", "NOT_CARRIED", "unpack"),
    "bit_depth": ("bit_depth_of", "_to01"),
    "metadata": ("Frame", "Camera.features"),
    "physical_unit": ("DEPTH_BACKENDS", "SFNC_FEATURES"),
    "teardown": ("Camera.close",),
}


def axes() -> dict:
    """Self-assessment on the eight axes, with the entry point that answers each.

    Returns:
        dict: axis -> ``{"entry": [names], "present": bool}``. ``present`` is False
        when any named entry point is missing, because a claim whose evidence has
        been renamed away is worse than no claim.
    """
    out = {}
    for axis, names in COVERAGE_AXES.items():
        ok = True
        for name in names:
            target = globals()
            obj = None
            for part in name.split("."):
                obj = (target.get(part) if isinstance(target, dict)
                       else getattr(target, part, None))
                if obj is None:
                    break
                target = obj
            ok = ok and obj is not None
        out[axis] = {"entry": list(names), "present": bool(ok)}
    return out


#: UVC 1.5 controls -- the vocabulary of the devices the ``opencv`` backend opens.
#:
#: A webcam is a USB Video Class device, and UVC names and (sometimes) dimensions its
#: controls exactly as SFNC does for GenICam cameras. Carrying the names means a
#: webcam's exposure can be read by its standard name instead of an integer index.
#:
#: Value is ``(interface, unit)``. ``interface`` is the standard's own grouping:
#: ``CT`` camera terminal, ``PU`` processing unit, ``VS`` video streaming.
#: ★``unit`` carries **only what the standard states in prose**. Where UVC does not
#: state a unit (``PU_GAIN_CONTROL`` says merely "the setting for the attribute of
#: the addressed Gain control") the entry is ``None`` -- inventing ``dB`` there would
#: be a claim the standard does not make.
UVC_CONTROLS = {
    "CT_SCANNING_MODE_CONTROL": ("CT", None),
    "CT_AE_MODE_CONTROL": ("CT", None),
    "CT_AE_PRIORITY_CONTROL": ("CT", None),
    "CT_EXPOSURE_TIME_ABSOLUTE_CONTROL": ("CT", "0.0001s"),
    "CT_EXPOSURE_TIME_RELATIVE_CONTROL": ("CT", None),
    "CT_FOCUS_ABSOLUTE_CONTROL": ("CT", "mm"),
    "CT_FOCUS_RELATIVE_CONTROL": ("CT", None),
    "CT_FOCUS_AUTO_CONTROL": ("CT", None),
    "CT_FOCUS_SIMPLE_CONTROL": ("CT", None),
    "CT_IRIS_ABSOLUTE_CONTROL": ("CT", "fstop*100"),
    "CT_IRIS_RELATIVE_CONTROL": ("CT", None),
    "CT_ZOOM_ABSOLUTE_CONTROL": ("CT", None),
    "CT_ZOOM_RELATIVE_CONTROL": ("CT", None),
    "CT_PANTILT_ABSOLUTE_CONTROL": ("CT", "arcsec"),
    "CT_PANTILT_RELATIVE_CONTROL": ("CT", None),
    "CT_ROLL_ABSOLUTE_CONTROL": ("CT", None),
    "CT_ROLL_RELATIVE_CONTROL": ("CT", None),
    "CT_PRIVACY_CONTROL": ("CT", None),
    "CT_WINDOW_CONTROL": ("CT", None),
    "CT_DIGITAL_WINDOW_CONTROL": ("CT", None),
    "CT_REGION_OF_INTEREST_CONTROL": ("CT", None),
    "PU_BACKLIGHT_COMPENSATION_CONTROL": ("PU", None),
    "PU_BRIGHTNESS_CONTROL": ("PU", None),
    "PU_CONTRAST_CONTROL": ("PU", None),
    "PU_CONTRAST_AUTO_CONTROL": ("PU", None),
    "PU_GAIN_CONTROL": ("PU", None),
    "PU_POWER_LINE_FREQUENCY_CONTROL": ("PU", None),
    "PU_HUE_CONTROL": ("PU", None),
    "PU_HUE_AUTO_CONTROL": ("PU", None),
    "PU_SATURATION_CONTROL": ("PU", None),
    "PU_SHARPNESS_CONTROL": ("PU", None),
    "PU_GAMMA_CONTROL": ("PU", None),
    "PU_WHITE_BALANCE_TEMPERATURE_CONTROL": ("PU", None),
    "PU_WHITE_BALANCE_TEMPERATURE_AUTO_CONTROL": ("PU", None),
    "PU_WHITE_BALANCE_COMPONENT_CONTROL": ("PU", None),
    "PU_WHITE_BALANCE_COMPONENT_AUTO_CONTROL": ("PU", None),
    "PU_DIGITAL_MULTIPLIER_CONTROL": ("PU", None),
    "PU_DIGITAL_MULTIPLIER_LIMIT_CONTROL": ("PU", None),
    "PU_ANALOG_VIDEO_STANDARD_CONTROL": ("PU", None),
    "PU_ANALOG_LOCK_STATUS_CONTROL": ("PU", None),
    "VS_PROBE_CONTROL": ("VS", None),
    "VS_COMMIT_CONTROL": ("VS", None),
    "VS_STILL_PROBE_CONTROL": ("VS", None),
    "VS_STILL_COMMIT_CONTROL": ("VS", None),
    "VS_STILL_IMAGE_TRIGGER_CONTROL": ("VS", None),
    "VS_STREAM_ERROR_CODE_CONTROL": ("VS", None),
    "VS_GENERATE_KEY_FRAME_CONTROL": ("VS", None),
    "VS_UPDATE_FRAME_SEGMENT_CONTROL": ("VS", None),
    "VS_SYNCH_DELAY_CONTROL": ("VS", None),
}

#: Controls whose value the standard dimensions, and how many SFNC units one step is.
#:
#: ★UVC 1.5 defines ``dwExposureTimeAbsolute`` as "1: 0.0001 sec ... 100000: 10 sec",
#: i.e. **100 us per step**, while SFNC gives ``ExposureTime`` in **us**. The same
#: number 5000 therefore means 5 ms under SFNC and 0.5 s under UVC -- a factor of 100
#: that raises no exception and only moves the picture.
UVC_EXPOSURE_STEP_US = 100.0

#: UVC control -> (SFNC feature, SFNC units per UVC step). ``None`` scale means the
#: two standards name the same quantity but **neither dimensions it**, so the number
#: is carried across unchanged and stays unitless.
UVC_TO_SFNC = {
    "CT_EXPOSURE_TIME_ABSOLUTE_CONTROL": ("ExposureTime", UVC_EXPOSURE_STEP_US),
    "PU_GAIN_CONTROL": ("Gain", None),
}


def uvc_to_sfnc(control: str, value):
    """Translate one UVC control reading into the SFNC name and unit.

    Args:
        control: a key of :data:`UVC_CONTROLS`.
        value: the raw value the device reported, in the standard's own steps.
    Returns:
        tuple: ``(sfnc_feature, value_in_sfnc_units)``.
    Raises:
        ValueError: the control is not in UVC 1.5, or the standards do not name the
            same quantity -- refusing here beats inventing a correspondence.
    """
    if control not in UVC_CONTROLS:
        raise ValueError("%r is not a UVC 1.5 control" % control)
    if control not in UVC_TO_SFNC:
        raise ValueError("UVC %s has no SFNC counterpart in this table -- add one "
                         "with the standard's own wording, do not guess" % control)
    name, scale = UVC_TO_SFNC[control]
    return name, (value if scale is None else value * scale)


def sfnc_to_uvc(feature: str, value):
    """The inverse of :func:`uvc_to_sfnc`, in the standard's own steps.

    Args:
        feature: an SFNC feature name that appears in :data:`UVC_TO_SFNC`.
        value: the value in SFNC units.
    Returns:
        tuple: ``(uvc_control, value_in_uvc_steps)``.
    Raises:
        ValueError: no UVC control names the same quantity.
    """
    for control, (name, scale) in UVC_TO_SFNC.items():
        if name == feature:
            return control, (value if scale is None else value / scale)
    raise ValueError("SFNC %s has no UVC counterpart in this table" % feature)


#: Uncompressed payload formats UVC 1.5 defines, with the GUIDs from its own table.
UVC_UNCOMPRESSED = {
    "YUY2": "32595559-0000-0010-8000-00AA00389B71",
    "NV12": "3231564E-0000-0010-8000-00AA00389B71",
    "M420": "3032344D-0000-0010-8000-00AA00389B71",
    "I420": "30323449-0000-0010-8000-00AA00389B71",
}


def capabilities() -> list:
    """Acquisition backends: ``{name, kind, available, implemented, unit, pip, desc}``.

    ``available`` = the SDK is importable here. ``implemented`` = this module has an
    opener for it — the two are different questions, and announcing the first while
    failing the second is what this table used to do (see the note on ``_BACKENDS``).
    ``unit`` says what ``grab()`` returns: ``"normalised"`` ([0, 1] picture) or
    ``"m"`` (metres — a depth map is a measurement and is never rescaled)."""
    import importlib.util
    out = []
    for name, module, pip, kind, unit, opener, desc in _BACKENDS:
        avail = (kind == "native") or (module is not None and
                                       importlib.util.find_spec(module) is not None
                                       if module else False)
        out.append({"name": name, "kind": kind, "available": bool(avail),
                    "implemented": hasattr(Camera, opener), "unit": unit,
                    "pip": pip, "desc": desc})
    return out


def coverage() -> dict:
    """How much of the declared catalogue this module actually implements.

    ``{"declared": n, "implemented": n, "available": n, "missing": [names]}`` —
    the number a "raise the device coverage" effort is trying to move, measured
    from the table rather than claimed in prose."""
    caps = capabilities()
    return {"declared": len(caps),
            "implemented": sum(1 for c in caps if c["implemented"]),
            "available": sum(1 for c in caps if c["available"]),
            "missing": [c["name"] for c in caps if not c["implemented"]]}

_LUMA = np.array([0.299, 0.587, 0.114], np.float64)
_IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".pgm", ".ppm", ".webp")
_VIDEO_EXTS = (".mp4", ".m4v", ".mov", ".avi", ".mkv", ".webm")


def _cv2():
    try:
        import cv2
        return cv2
    except Exception:
        return None


#: Pixel formats a backend can report, mapped to the number of SIGNIFICANT bits.
#: ★This is the fix for a silent defect: a 12-bit sensor hands back a uint16 buffer, and
#: dividing by the CONTAINER maximum (65535) instead of 4095 makes the whole image
#: **16x too dark** (measured: 4095 -> 0.0625) with no exception — every threshold
#: operator downstream is then wrong. The container cannot tell you the depth; the
#: pixel format can, so backends pass it in and this table decides.
PIXEL_BITS = {
    "Mono8": 8, "Mono10": 10, "Mono10p": 10, "Mono10Packed": 10,
    "Mono12": 12, "Mono12p": 12, "Mono12Packed": 12,
    "Mono14": 14, "Mono14p": 14, "Mono16": 16,
    "BayerRG8": 8, "BayerGB8": 8, "BayerGR8": 8, "BayerBG8": 8,
    "BayerRG10": 10, "BayerGB10": 10, "BayerGR10": 10, "BayerBG10": 10,
    "BayerRG10p": 10, "BayerGB10p": 10, "BayerGR10p": 10, "BayerBG10p": 10,
    "BayerRG10Packed": 10, "BayerGB10Packed": 10,
    "BayerGR10Packed": 10, "BayerBG10Packed": 10,
    "BayerRG12": 12, "BayerGB12": 12, "BayerGR12": 12, "BayerBG12": 12,
    "BayerRG12p": 12, "BayerGB12p": 12, "BayerGR12p": 12, "BayerBG12p": 12,
    "BayerRG12Packed": 12, "BayerGB12Packed": 12,
    "BayerGR12Packed": 12, "BayerBG12Packed": 12,
    "BayerRG14": 14, "BayerGB14": 14, "BayerGR14": 14, "BayerBG14": 14,
    "BayerRG14p": 14, "BayerGB14p": 14, "BayerGR14p": 14, "BayerBG14p": 14,
    "BayerRG16": 16, "BayerGB16": 16, "BayerGR16": 16, "BayerBG16": 16,
    "RGB8": 8, "BGR8": 8, "RGB8Packed": 8, "YCbCr422_8": 8, "YUV422_8": 8,
}


#: Packed pixel formats: the buffer is a bit stream, not one integer per pixel.
#:
#: Two different layouts share the word "packed", and mixing them up produces a
#: plausible picture rather than an error:
#:
#: * ``p`` -- lsb packed (PFNC 2.4 6.3.1). A gapless bit stream, least significant
#:   bit first. ``Mono10p`` is 4 pixels in 5 bytes, ``Mono12p`` 2 pixels in 3 bytes.
#: * ``Packed`` -- lsb grouped (PFNC 2.4 6.4.1; the GigE Vision 1.x spelling). The
#:   high byte of each pixel comes first and the low bits are gathered into a byte
#:   of their own: ``byte0 = P0[11:4]``, ``byte1 = P1[3:0] << 4 | P0[3:0]``,
#:   ``byte2 = P1[11:4]``.
#:
#: Values are ``(significant bits, layout)`` where layout is ``"p"`` or ``"g"``.
PACKED_FORMATS = {
    "Mono10p": (10, "p"), "Mono12p": (12, "p"), "Mono14p": (14, "p"),
    "Mono10Packed": (10, "g"), "Mono12Packed": (12, "g"),
    "BayerRG10p": (10, "p"), "BayerGB10p": (10, "p"),
    "BayerGR10p": (10, "p"), "BayerBG10p": (10, "p"),
    "BayerRG12p": (12, "p"), "BayerGB12p": (12, "p"),
    "BayerGR12p": (12, "p"), "BayerBG12p": (12, "p"),
    "BayerRG10Packed": (10, "g"), "BayerGB10Packed": (10, "g"),
    "BayerGR10Packed": (10, "g"), "BayerBG10Packed": (10, "g"),
    "BayerRG12Packed": (12, "g"), "BayerGB12Packed": (12, "g"),
    "BayerGR12Packed": (12, "g"), "BayerBG12Packed": (12, "g"),
    "BayerRG14p": (14, "p"), "BayerGB14p": (14, "p"),
    "BayerGR14p": (14, "p"), "BayerBG14p": (14, "p"),
}

#: PFNC formats this module deliberately does not carry, and why. Leaving them out
#: silently would look the same as not having measured; each line is a decision.
#:
#: * ``Mono1p`` / ``Mono2p`` / ``Mono4p`` / ``Bayer*4p`` -- fewer than 8 significant
#:   bits. They unpack fine, but every consumer here assumes a byte-or-wider sample.
#: * ``Mono8s`` -- signed. ``_to01`` divides by ``2**bits - 1``, which is wrong for a
#:   range of -128..127; a signed sensor needs its own mapping, not a table row.
#: * ``Mono32`` -- 32 significant bits. Representable, but nothing here produces or
#:   consumes it, so claiming it would be a claim without a test behind it.
#: * ``YUV*`` / ``YCbCr*`` / ``Coord3D_*`` / ``Confidence*`` -- not one integer per
#:   pixel in a single plane; they need a colour or 3-D decode, not a bit count.
NOT_CARRIED = {
    "Mono1p": "1 bit", "Mono2p": "2 bits", "Mono4p": "4 bits",
    "BayerRG4p": "4 bits", "BayerGB4p": "4 bits",
    "BayerGR4p": "4 bits", "BayerBG4p": "4 bits",
    "Mono8s": "signed", "Mono32": "32 bits, no producer or consumer here",
}


def unpack_lsb(buf, bits: int, count: int) -> np.ndarray:
    """lsb-packed bit stream -> one ``uint16`` per pixel (PFNC 2.4 6.3.1).

    Args:
        buf: the raw bytes the device delivered (any shape; read as ``uint8``).
        bits: significant bits per pixel, e.g. 10 for ``Mono10p``.
        count: how many pixels to read.
    Returns:
        np.ndarray: ``uint16``, length *count*.
    Raises:
        ValueError: when the buffer holds fewer bits than *count* pixels need --
            a short buffer is a dropped packet, never a reason to return a
            half-filled image.
    """
    b = np.unpackbits(np.asarray(buf, dtype=np.uint8).ravel(), bitorder="little")
    need = int(bits) * int(count)
    if b.size < need:
        raise ValueError("unpack_lsb: %d pixels x %d bits need %d bits, buffer has %d"
                         % (count, bits, need, b.size))
    w = b[:need].reshape(int(count), int(bits))
    return (w * (1 << np.arange(int(bits), dtype=np.uint32))).sum(axis=1).astype(np.uint16)


def unpack_grouped(buf, bits: int, count: int) -> np.ndarray:
    """lsb-grouped bit stream -> one ``uint16`` per pixel (PFNC 2.4 6.4.1).

    Two pixels occupy three bytes for both the 10-bit and the 12-bit variants; the
    difference is how many low bits live in the shared middle byte.

    Args:
        buf: the raw bytes the device delivered.
        bits: 10 or 12 -- the only widths the grouped layout is defined for here.
        count: how many pixels to read.
    Returns:
        np.ndarray: ``uint16``, length *count*.
    Raises:
        ValueError: for an unsupported width, or a buffer too short for *count*.
    """
    bits = int(bits)
    if bits not in (10, 12):
        raise ValueError("unpack_grouped: %d-bit grouped layout is not defined here"
                         % bits)
    low = bits - 8
    a = np.asarray(buf, dtype=np.uint8).ravel()
    pairs = (int(count) + 1) // 2
    if a.size < pairs * 3:
        raise ValueError("unpack_grouped: %d pixels need %d bytes, buffer has %d"
                         % (count, pairs * 3, a.size))
    a = a[:pairs * 3].reshape(pairs, 3).astype(np.uint16)
    mid = a[:, 1]
    out = np.empty(pairs * 2, dtype=np.uint16)
    out[0::2] = (a[:, 0] << low) | (mid & ((1 << low) - 1))
    out[1::2] = (a[:, 2] << low) | ((mid >> 4) & ((1 << low) - 1))
    return out[:int(count)]


def unpack(buf, pixel_format, shape) -> np.ndarray:
    """Raw buffer -> ``uint16`` image for a packed *pixel_format*.

    Args:
        buf: the bytes the device delivered.
        pixel_format: a packed GenICam format name, e.g. ``"Mono12p"``.
        shape: ``(height, width)`` of the image to build.
    Returns:
        np.ndarray: ``uint16`` of *shape*.
    Raises:
        ValueError: when *pixel_format* is not a packed format this module knows,
            or the buffer is too short. Guessing here is the defect this prevents.
    """
    name = str(pixel_format)
    if name not in PACKED_FORMATS:
        raise ValueError("unpack: %r is not a packed format (known: %s)"
                         % (name, ", ".join(sorted(PACKED_FORMATS))))
    bits, layout = PACKED_FORMATS[name]
    h, w = int(shape[0]), int(shape[1])
    fn = unpack_lsb if layout == "p" else unpack_grouped
    return fn(buf, bits, h * w).reshape(h, w)


#: GenICam SFNC v2.8 feature names this module drives, with the level and unit the
#: standard itself assigns. ``R`` means the standard requires every compliant device
#: to have it, ``O`` that it may be absent -- which is why a missing ``O`` feature is
#: reported rather than treated as a broken camera.
#:
#: These are *standard* names, not vendor names: one table covers every GenTL
#: producer. ``examples/data/sfnc_acquire_vocabulary.json`` carries the same rows
#: straight from EMVA's published PDF, and a test compares the two.
#:
#: The unit column is SFNC 1.2 Standard Units. ``ExposureTime`` is microseconds and
#: ``AcquisitionFrameRate`` is hertz because the standard says so. ``Gain`` has no
#: unit in the standard -- only the device's own node does -- so this module never
#: calls it dB.
SFNC_FEATURES = {
    "PixelFormat": ("R", "IEnumeration", None),
    "Width": ("R", "IInteger", None),
    "Height": ("R", "IInteger", None),
    "OffsetX": ("R", "IInteger", None),
    "OffsetY": ("R", "IInteger", None),
    "AcquisitionMode": ("R", "IEnumeration", None),
    "AcquisitionStart": ("R", "ICommand", None),
    "AcquisitionStop": ("R", "ICommand", None),
    "AcquisitionFrameRate": ("R", "IFloat", "Hz"),
    "TriggerSelector": ("R", "IEnumeration", None),
    "TriggerMode": ("R", "IEnumeration", None),
    "TriggerSource": ("R", "IEnumeration", None),
    "TriggerActivation": ("R", "IEnumeration", None),
    "ExposureMode": ("R", "IEnumeration", None),
    "ExposureTime": ("R", "IFloat", "us"),
    "ExposureAuto": ("O", "IEnumeration", None),
    "GainSelector": ("O", "IEnumeration", None),
    "Gain": ("O", "IFloat", None),
    "GainAuto": ("O", "IEnumeration", None),
    "BlackLevel": ("O", "IFloat", None),
    "DeviceVendorName": ("R", "IString", None),
    "DeviceModelName": ("R", "IString", None),
    "DeviceSerialNumber": ("R", "IString", None),
    "DeviceFirmwareVersion": ("R", "IString", None),
    "PayloadSize": ("R", "IInteger", "B"),
    "TimestampLatch": ("O", "ICommand", None),
    "TimestampLatchValue": ("O", "IInteger", "ns"),
    "ReverseX": ("R", "IBoolean", None),
    "ReverseY": ("R", "IBoolean", None),
    "BinningHorizontal": ("O", "IInteger", None),
    "BinningVertical": ("O", "IInteger", None),
}

#: Feature names the standard requires, so their absence is a real finding.
SFNC_REQUIRED = tuple(n for n, (lvl, _i, _u) in sorted(SFNC_FEATURES.items())
                      if lvl == "R")


class _NodeMap:
    """One way to read and write GenICam features across the SDKs that expose them.

    Only the *access* differs between SDKs; the names, units and required/optional
    status come from the standard. Keeping the difference in one small class is what
    lets a single vocabulary cover every GenTL producer.
    """

    __slots__ = ("kind", "obj")

    def __init__(self, kind, obj):
        self.kind = kind
        self.obj = obj

    def has(self, name: str) -> bool:
        try:
            return self._node(name) is not None
        except Exception:                                   # noqa: BLE001
            return False

    def _node(self, name):
        if self.kind == "vmbpy":
            return self.obj.get_feature_by_name(name)
        return getattr(self.obj, name)

    def get(self, name: str):
        n = self._node(name)
        if self.kind == "pypylon":
            return n.GetValue()
        if self.kind == "vmbpy":
            return n.get()
        return n.value                                      # GenICam / harvesters

    def set(self, name: str, value):
        n = self._node(name)
        if self.kind == "pypylon":
            n.SetValue(value)
        elif self.kind == "vmbpy":
            n.set(value)
        else:
            n.value = value

    def execute(self, name: str) -> None:
        n = self._node(name)
        for attr in ("execute", "Execute", "run"):
            fn = getattr(n, attr, None)
            if callable(fn):
                fn()
                return
        raise ValueError("_NodeMap: %r is not executable on a %s node map"
                         % (name, self.kind))


def bit_depth_of(pixel_format) -> int | None:
    """Significant bits for a GenICam-style pixel format name, or ``None`` if unknown.

    Names follow the EMVA GenICam PFNC, so one table covers every GenTL producer
    rather than one table per vendor. The spellings and their significant-bit counts
    come from EMVA's published "GenICam Pixel Format Names and Values" (free), not
    from a vendor manual -- 285 formats are listed there, 24 of which this table
    carries verbatim.

    Args:
        pixel_format: the format name a backend reports (e.g. ``"Mono12"``).
    Returns:
        int | None: significant bits, or ``None`` when the name is not known — in which
        case the caller must NOT guess (guessing is the defect this replaces).
    """
    if pixel_format is None:
        return None
    return PIXEL_BITS.get(str(pixel_format))


def _to01(a: np.ndarray, bits: int | None = None) -> np.ndarray:
    """Integer buffer -> float64 [0, 1]. *bits* = significant bits when the backend
    knows them; without it the container width is the only information available."""
    a = np.asarray(a)
    if np.issubdtype(a.dtype, np.integer):
        full = float((1 << int(bits)) - 1) if bits else float(np.iinfo(a.dtype).max)
        return np.clip(a.astype(np.float64) / full, 0.0, 1.0)
    return np.clip(a.astype(np.float64), 0.0, 1.0)


class Frame:
    """One acquisition with the facts a measurement needs, not just the pixels.

    ``Camera.grab()`` still returns a bare array (every existing caller keeps working);
    ``Camera.grab_frame()`` returns this, because six of the eight things that differ
    between camera SDKs — pixel format, significant bits, device timestamp, frame id,
    effective exposure and gain — cannot be expressed by an array alone, and dropping
    them is how a pipeline silently loses the ability to detect a dropped frame or to
    interpret a 12-bit buffer.

    Attributes:
        data: the pixels (float64) — ``[0, 1]`` when ``unit == "normalised"``,
            metres when ``unit == "m"``.
        unit: ``"normalised"`` or ``"m"``.
        backend: which backend produced it.
        pixel_format: the format name the device reported, or ``None``.
        bit_depth: significant bits, or ``None`` when the device did not say.
        timestamp_s: device timestamp in seconds when available, else host time.
        timestamp_source: ``"device"`` or ``"host"`` — a host clock cannot be used
            to align two cameras, so the difference has to be visible.
        frame_id: the device's frame counter, or ``None``. Gaps mean dropped frames.
        exposure_us: the exposure the device actually used, in microseconds (SFNC 1.2 fixes that unit), or ``None``.
        gain / gain_unit: the gain the device actually used and the unit it reported it in, or ``None``. SFNC v2.8 gives ``Gain`` no unit of its own -- only the device's own node does -- so naming the field ``gain_db`` would claim more than the standard says.
    """

    __slots__ = ("data", "unit", "backend", "pixel_format", "bit_depth",
                 "timestamp_s", "timestamp_source", "frame_id", "exposure_us", "gain", "gain_unit")

    def __init__(self, data, unit="normalised", backend="", pixel_format=None,
                 bit_depth=None, timestamp_s=None, timestamp_source="host",
                 frame_id=None, exposure_us=None, gain=None, gain_unit=None):
        self.data = data
        self.unit = unit
        self.backend = backend
        self.pixel_format = pixel_format
        self.bit_depth = bit_depth
        self.timestamp_s = timestamp_s
        self.timestamp_source = timestamp_source
        self.frame_id = frame_id
        self.exposure_us = exposure_us
        self.gain = gain
        #: SFNC v2.8 gives Gain no unit -- only the device's own node does, so
        #: the unit travels with the value instead of being baked into the name.
        self.gain_unit = gain_unit

    @property
    def shape(self):
        return np.shape(self.data)

    def __array__(self, dtype=None):
        """A Frame can stand in for its array, so ``eng.run(cam.grab_frame())`` works."""
        a = np.asarray(self.data)
        return a if dtype is None else a.astype(dtype)

    def __repr__(self):
        return ("Frame(%r, unit=%s, backend=%s, pixel_format=%s, bit_depth=%s, "
                "frame_id=%s, t=%s(%s))"
                % (self.shape, self.unit, self.backend, self.pixel_format,
                   self.bit_depth, self.frame_id, self.timestamp_s, self.timestamp_source))


def _coerce(frame, gray: bool, bits: int | None = None,
            pixel_format=None) -> np.ndarray:
    """One raw frame -> float64 [0,1]; grayscale (H,W) or RGB (H,W,3).

    *bits* = significant bits reported by the device. Pass it whenever the backend
    knows the pixel format — without it a 12-bit buffer in a 16-bit container is
    scaled by 65535 and comes out 16x too dark.

    *pixel_format* lets this refuse a packed buffer instead of scaling it. A packed
    format carries a bit stream, so dividing it by ``2**bits - 1`` produces a
    picture that looks like an image and is not one; :func:`unpack` is the way in."""
    if pixel_format is not None and str(pixel_format) in PACKED_FORMATS:
        a = np.asarray(frame)
        #: An already-unpacked buffer is wider than 8 bits; a raw packed one is not.
        if a.dtype == np.uint8:
            raise ValueError(
                "_coerce: %r is packed (PFNC 2.4) -- call acquire.unpack(buf, %r, "
                "(h, w)) first. Scaling the packed bytes would return a picture "
                "that is not the image." % (str(pixel_format), str(pixel_format)))
    a = np.asarray(frame)
    if a.ndim == 3 and a.shape[2] == 4:
        a = a[:, :, :3]
    a = _to01(a, bits)
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
        row = _BACKEND_BY_NAME.get(self.backend)
        if row is None:
            raise ValueError("unknown backend %r; known: %s"
                             % (self.backend, ", ".join(n for n, *_ in _BACKENDS)))
        #: "normalised" (a picture in [0,1]) or "m" (a depth map in metres).
        self.unit = row[4]
        #: what the device said about the last frame (pixel format, timestamp, ids)
        self._meta = {}
        self._open()

    # ------------------------------------------------------------------ open --
    def _open(self):
        """Dispatch THROUGH the catalogue so a declared backend cannot lack an opener."""
        opener = getattr(self, _BACKEND_BY_NAME[self.backend][5], None)
        if opener is None:                           # pragma: no cover - the gate forbids it
            raise ValueError("backend %r is declared in _BACKENDS but has no opener"
                             % (self.backend,))
        opener()

    def _open_callable(self):
        """A user function as a source — and the one path where the device facts can be
        supplied by hand.

        ``pixel_format=`` / ``bit_depth=`` / ``unit=`` in *opts* let a mock stand in for a
        camera that reports them, so the 12-bit scaling and the metres contract are
        testable **without hardware**. A vendor SDK reports the same facts through
        :meth:`_raw_grab`; this is the same contract, filled in by the caller.
        """
        if not callable(self.source):
            raise ValueError("callable backend needs a callable source")
        unit = self.opts.get("unit")
        if unit is not None:
            if unit not in ("normalised", "m"):
                raise ValueError("callable backend: unit must be 'normalised' or 'm', got %r"
                                 % (unit,))
            self.unit = unit
        fmt = self.opts.get("pixel_format")
        bits = self.opts.get("bit_depth")
        if fmt is not None and bits is None:
            bits = bit_depth_of(fmt)
            if bits is None:
                raise ValueError("callable backend: unknown pixel_format %r; pass bit_depth= "
                                 "explicitly rather than letting the container decide" % (fmt,))
        self._mock_meta = {k: v for k, v in
                           (("pixel_format", fmt), ("bit_depth", bits)) if v is not None}
        self._handle = self.source

    def _open_dir(self):
        self._dir_files = self._list_dir(self.source)
        if not self._dir_files:
            raise FileNotFoundError("no images found for %r" % (self.source,))

    def _open_opencv(self):
        cv2 = _cv2()
        if cv2 is None:
            raise RuntimeError("opencv backend needs opencv-python")
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            raise RuntimeError("could not open camera/source %r" % (self.source,))
        self._handle = cap

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

    def _open_vimba(self):  # pragma: no cover - needs an Allied Vision camera
        """Allied Vision Vimba X. ``VmbSystem`` and the camera are context managers, so
        the entered contexts are kept on the handle and exited in :meth:`close` — leaving
        them to the garbage collector loses the transport layer."""
        try:
            from vmbpy import VmbSystem
        except Exception as e:
            raise RuntimeError("vimba backend needs 'vmbpy': %s" % e)
        vmb = VmbSystem.get_instance()
        vmb.__enter__()
        try:
            cams = vmb.get_all_cameras()
            if not cams:
                raise RuntimeError("vimba: no camera found")
            cam = cams[int(self.opts.get("index", 0))]
            cam.__enter__()
        except Exception:
            vmb.__exit__(None, None, None)
            raise
        self._handle = ("vimba", vmb, cam)

    def _open_realsense(self):  # pragma: no cover - needs a RealSense device
        """Intel RealSense. The device reports depth in its own integer units; the scale
        that converts them to metres comes from ``get_depth_scale()``, so it is read once
        here rather than assumed to be 0.001."""
        try:
            import pyrealsense2 as rs
        except Exception as e:
            raise RuntimeError("realsense backend needs 'pyrealsense2': %s" % e)
        pipe = rs.pipeline()
        cfg = rs.config()
        w, h = self.opts.get("size", (640, 480))
        fps = int(self.opts.get("fps", 30))
        cfg.enable_stream(rs.stream.depth, int(w), int(h), rs.format.z16, fps)
        profile = pipe.start(cfg)
        scale = float(profile.get_device().first_depth_sensor().get_depth_scale())
        self._handle = ("realsense", rs, pipe, scale)

    def _open_oak(self):  # pragma: no cover - needs a Luxonis OAK device
        """Luxonis OAK-D. StereoDepth publishes a uint16 depth map in millimetres; the
        queue is non-blocking with a small backlog so ``grab`` returns the newest frame
        rather than draining a stale one."""
        try:
            import depthai as dai
        except Exception as e:
            raise RuntimeError("oak backend needs 'depthai': %s" % e)
        pipeline = dai.Pipeline()
        left = pipeline.create(dai.node.MonoCamera)
        right = pipeline.create(dai.node.MonoCamera)
        stereo = pipeline.create(dai.node.StereoDepth)
        left.setBoardSocket(dai.CameraBoardSocket.LEFT)
        right.setBoardSocket(dai.CameraBoardSocket.RIGHT)
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
        left.out.link(stereo.left)
        right.out.link(stereo.right)
        xout = pipeline.create(dai.node.XLinkOut)
        xout.setStreamName("depth")
        stereo.depth.link(xout.input)
        dev = dai.Device(pipeline)
        q = dev.getOutputQueue(name="depth", maxSize=4, blocking=False)
        self._handle = ("oak", dev, q)

    def _open_zed(self):  # pragma: no cover - needs a ZED camera + the ZED SDK
        """Stereolabs ZED. The unit is a runtime choice, so METER is set explicitly —
        the default differs between SDK versions and a silent millimetre map would be a
        thousand times too large."""
        try:
            import pyzed.sl as sl
        except Exception as e:
            raise RuntimeError("zed backend needs 'pyzed' and the ZED SDK: %s" % e)
        cam = sl.Camera()
        params = sl.InitParameters()
        params.coordinate_units = sl.UNIT.METER
        status = cam.open(params)
        if status != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError("zed: could not open camera (%s)" % status)
        self._handle = ("zed", sl, cam, sl.Mat(), sl.RuntimeParameters())

    def _open_kinect(self):  # pragma: no cover - needs an Azure Kinect DK
        """Azure Kinect DK. Depth arrives in millimetres. ★Microsoft discontinued the
        hardware; Orbbec's Femto line is the successor for new work."""
        try:
            from pyk4a import Config, PyK4A
        except Exception as e:
            raise RuntimeError("kinect backend needs 'pyk4a' + the Azure Kinect SDK: %s" % e)
        k4a = PyK4A(Config())
        k4a.start()
        self._handle = ("kinect", k4a)

    # ------------------------------------------------------------------ grab --
    def _raw_grab(self):
        """One raw frame plus what the device said about it, as ``(array, meta)``.

        *meta* keys (all optional): ``pixel_format``, ``bit_depth``, ``timestamp_s``,
        ``timestamp_source``, ``frame_id``, ``exposure_us``, ``gain``, ``gain_unit``.
        A backend that
        knows nothing returns ``{}`` — an empty dict is honest, a fabricated timestamp
        is not.
        """
        b = self.backend
        if b == "callable":
            meta = dict(getattr(self, "_mock_meta", {}))
            meta.setdefault("frame_id", self._dir_pos)
            self._dir_pos += 1
            return self._handle(), meta
        if b == "dir":
            if not self._dir_files:
                return None, {}
            path = self._dir_files[self._dir_pos % len(self._dir_files)]
            self._dir_pos += 1
            cv2 = _cv2()
            if cv2 is not None:
                im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                if im is None:
                    return None, {}
                if im.ndim == 3 and im.shape[2] >= 3:
                    im = im[:, :, :3][:, :, ::-1]        # BGR -> RGB
                return im, {"frame_id": self._dir_pos - 1}
            from PIL import Image
            return np.asarray(Image.open(path)), {"frame_id": self._dir_pos - 1}
        if b == "opencv":
            ok, bgr = self._handle.read()
            if not ok or bgr is None:
                return None, {}
            frame = bgr[:, :, ::-1] if bgr.ndim == 3 else bgr   # BGR -> RGB
            return frame, {"timestamp_s": time.time(), "timestamp_source": "host"}
        if b == "genicam":  # pragma: no cover
            _, _h, ia = self._handle
            with ia.fetch() as buf:
                comp = buf.payload.components[0]
                fmt = getattr(comp, "data_format", None)
                return (np.array(comp.data.reshape(comp.height, comp.width)),
                        {"pixel_format": fmt, "bit_depth": bit_depth_of(fmt),
                         "timestamp_s": _ns_to_s(getattr(buf, "timestamp_ns", None)),
                         "timestamp_source": "device",
                         "frame_id": getattr(buf, "frame_id", None)})
        if b == "basler":  # pragma: no cover
            _, cam, pylon = self._handle
            res = cam.RetrieveResult(2000, pylon.TimeoutHandling_ThrowException)
            try:
                if not res.GrabSucceeded():
                    return None, {}
                fmt = str(cam.PixelFormat.GetValue()) if hasattr(cam, "PixelFormat") else None
                return (np.array(res.Array),
                        {"pixel_format": fmt, "bit_depth": bit_depth_of(fmt),
                         "timestamp_s": _ns_to_s(getattr(res, "TimeStamp", None)),
                         "timestamp_source": "device",
                         "frame_id": getattr(res, "ImageNumber", None)})
            finally:
                res.Release()
        if b == "vimba":  # pragma: no cover
            _, _vmb, cam = self._handle
            frame = cam.get_frame(timeout_ms=int(self.opts.get("timeout_ms", 2000)))
            fmt = str(frame.get_pixel_format())
            #: ★``as_numpy_ndarray()`` はフレームのバッファを**そのまま指す**
            #:   (vmbpy 同梱の例が「同じメモリを使う」と書いている)。vmbpy の取得は
            #:   フレームを再キューして**バッファを使い回す**ので、複製しないと
            #:   次の 1 枚が前の 1 枚を書き換える —— 例外は出ず、絵だけが入れ替わる。
            return (np.array(frame.as_numpy_ndarray()),
                    {"pixel_format": fmt, "bit_depth": bit_depth_of(fmt),
                     "timestamp_s": _ns_to_s(frame.get_timestamp()),
                     "timestamp_source": "device", "frame_id": frame.get_id()})
        if b == "realsense":  # pragma: no cover
            _, _rs, pipe, scale = self._handle
            fs = pipe.wait_for_frames()
            df = fs.get_depth_frame()
            if not df:
                return None, {}
            #: device units -> metres. The scale is read from the device, not assumed.
            return (np.asanyarray(df.get_data()).astype(np.float64) * scale,
                    {"timestamp_s": _ms_to_s(df.get_timestamp()),
                     "timestamp_source": "device", "frame_id": df.get_frame_number()})
        if b == "oak":  # pragma: no cover
            _, _dev, q = self._handle
            msg = q.get()
            if msg is None:
                return None, {}
            return (np.asarray(msg.getFrame()).astype(np.float64) * 1e-3,   # mm -> m
                    {"timestamp_s": getattr(msg.getTimestamp(), "total_seconds", lambda: None)(),
                     "timestamp_source": "device", "frame_id": msg.getSequenceNum()})
        if b == "zed":  # pragma: no cover
            _, sl, cam, mat, runtime = self._handle
            if cam.grab(runtime) != sl.ERROR_CODE.SUCCESS:
                return None, {}
            cam.retrieve_measure(mat, sl.MEASURE.DEPTH)     # already METER (set at open)
            return (np.asarray(mat.get_data()).astype(np.float64),
                    {"timestamp_s": _ns_to_s(cam.get_timestamp(sl.TIME_REFERENCE.IMAGE)
                                             .get_nanoseconds()),
                     "timestamp_source": "device",
                     "frame_id": cam.get_svo_position() if cam.is_opened() else None})
        if b == "kinect":  # pragma: no cover
            k4a = self._handle[1]
            cap = k4a.get_capture()
            if cap is None or cap.depth is None:
                return None, {}
            return (np.asarray(cap.depth).astype(np.float64) * 1e-3,        # mm -> m
                    {"timestamp_s": _us_to_s(getattr(cap, "depth_timestamp_usec", None)),
                     "timestamp_source": "device"})
        return None, {}

    def grab(self):
        """Grab one frame. Image backends return float64 ``[0, 1]`` (gray or RGB);
        **depth backends return float64 metres** — a distance is a measurement and is
        never squeezed into ``[0, 1]``. Retries a few times, then raises ``RuntimeError``
        if the source yields nothing (disconnected camera, exhausted single-shot source).
        """
        return self.grab_frame().data

    def grab_frame(self):
        """Grab one frame as a :class:`Frame` — the pixels plus what the device reported
        (pixel format, significant bits, timestamp and its source, frame id, exposure).

        Use this rather than :meth:`grab` when the pipeline needs to detect dropped
        frames, align two cameras, or interpret a 12-bit buffer correctly.
        """
        last, meta = None, {}
        for _ in range(self.retries):
            last, meta = self._raw_grab()
            if last is not None:
                break
        if last is None:
            raise RuntimeError("no frame from source %r (backend %s)"
                               % (self.source, self.backend))
        self._meta = meta
        bits = meta.get("bit_depth")
        if self.unit == "m":
            data = np.asarray(last, dtype=np.float64)
        else:
            data = _coerce(last, self.gray, bits,
                           meta.get("pixel_format"))
        return Frame(data, unit=self.unit, backend=self.backend,
                     pixel_format=meta.get("pixel_format"), bit_depth=bits,
                     timestamp_s=meta.get("timestamp_s"),
                     timestamp_source=meta.get("timestamp_source", "host"),
                     frame_id=meta.get("frame_id"),
                     exposure_us=meta.get("exposure_us"), gain=meta.get("gain"), gain_unit=meta.get("gain_unit"))


    def node_map(self):
        """The device's GenICam node map, or ``None`` when the backend has none.

        Returns:
            _NodeMap | None: ``None`` for ``callable``, ``dir`` and the depth
            backends, which are not GenICam devices at all -- saying so is better
            than raising, because "this source has no features" is a fact a caller
            may want to branch on.
        """
        h = self._handle
        if h is None:
            return None
        if self.backend == "genicam":
            return _NodeMap("genicam", h[2].remote_device.node_map)
        if self.backend == "basler":
            return _NodeMap("pypylon", h[1])
        if self.backend == "vimba":
            return _NodeMap("vmbpy", h[2])
        if self.backend == "callable":
            #: A mock node map makes the SFNC path testable with no hardware at all.
            nm = self.opts.get("node_map")
            return _NodeMap("genicam", nm) if nm is not None else None
        return None

    def features(self, names=None) -> dict:
        """Read SFNC features from the device.

        Args:
            names: which features to read; ``None`` reads every name in
                :data:`SFNC_FEATURES` that the device actually exposes.
        Returns:
            dict: name -> value for the features present. A feature the standard
            marks optional and the device does not have is simply absent; a
            **required** one that is missing is reported as ``None`` so the gap is
            visible rather than silently skipped.
        Raises:
            RuntimeError: when the backend has no node map.
            ValueError: for a name that is not an SFNC feature -- a vendor-specific
                name is a real thing, but it does not belong in a table that claims
                to be the standard's.
        """
        nm = self.node_map()
        if nm is None:
            raise RuntimeError("features: backend %r has no GenICam node map"
                               % self.backend)
        wanted = tuple(SFNC_FEATURES) if names is None else tuple(names)
        bad = [n for n in wanted if n not in SFNC_FEATURES]
        if bad:
            raise ValueError("features: not SFNC v2.8 feature names: %s"
                             % ", ".join(sorted(bad)))
        out = {}
        for name in wanted:
            level = SFNC_FEATURES[name][0]
            if SFNC_FEATURES[name][1] == "ICommand":
                continue                                    # a command has no value
            if not nm.has(name):
                if level == "R":
                    out[name] = None                        # required and absent
                continue
            try:
                out[name] = nm.get(name)
            except Exception:                               # noqa: BLE001
                if level == "R":
                    out[name] = None
        return out

    def configure(self, **features) -> dict:
        """Set SFNC features by their standard names and report what the device took.

        Cameras clamp: ask for 100000 us on a sensor whose maximum is 33000 and you
        get 33000. Returning the requested value would be a small lie that turns into
        a wrong exposure in a measurement, so every value is read back.

        Args:
            **features: SFNC feature names and values, e.g.
                ``configure(ExposureTime=5000.0, TriggerMode="Off")``.
                ``ExposureTime`` is in microseconds and ``AcquisitionFrameRate`` in
                hertz because SFNC 1.2 fixes those units.
        Returns:
            dict: name -> the value the device reports **after** the write.
        Raises:
            RuntimeError: when the backend has no node map.
            ValueError: for a name outside :data:`SFNC_FEATURES`, or a feature the
                device does not expose. Writing a name the device does not have
                would otherwise fail somewhere deeper with a vendor-specific error.
        """
        nm = self.node_map()
        if nm is None:
            raise RuntimeError("configure: backend %r has no GenICam node map"
                               % self.backend)
        bad = [n for n in features if n not in SFNC_FEATURES]
        if bad:
            raise ValueError("configure: not SFNC v2.8 feature names: %s"
                             % ", ".join(sorted(bad)))
        absent = [n for n in features if not nm.has(n)]
        if absent:
            raise ValueError("configure: the device does not expose %s"
                             % ", ".join(sorted(absent)))
        for name, value in features.items():
            nm.set(name, value)
        return self.features(tuple(features))

    def missing_required_features(self) -> list:
        """SFNC features the standard requires but this device does not expose.

        Returns:
            list: the missing names, sorted. An empty list is the expected answer;
            a non-empty one is a finding about the device, not about this module.
        """
        nm = self.node_map()
        if nm is None:
            raise RuntimeError("missing_required_features: backend %r has no "
                               "GenICam node map" % self.backend)
        return sorted(n for n in SFNC_REQUIRED if not nm.has(n))

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
            if h is None:
                return
            if b == "opencv":
                h.release()
            elif b == "genicam":  # pragma: no cover
                _, harv, ia = h
                ia.stop(); ia.destroy(); harv.reset()
            elif b == "basler":  # pragma: no cover
                _, cam, _pylon = h
                cam.StopGrabbing(); cam.Close()
            elif b == "vimba":  # pragma: no cover
                _, vmb, cam = h
                cam.__exit__(None, None, None); vmb.__exit__(None, None, None)
            elif b == "realsense":  # pragma: no cover
                h[2].stop()
            elif b == "oak":  # pragma: no cover
                h[1].close()
            elif b == "zed":  # pragma: no cover
                h[2].close()
            elif b == "kinect":  # pragma: no cover
                h[1].stop()
        finally:
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def __repr__(self):
        return "Camera(%r, backend=%s, gray=%s)" % (self.source, self.backend, self.gray)


def _ns_to_s(v):
    """Device nanoseconds -> seconds, or ``None``. A missing timestamp stays missing."""
    return None if v in (None, 0) else float(v) * 1e-9


def _us_to_s(v):
    return None if v in (None, 0) else float(v) * 1e-6


def _ms_to_s(v):
    return None if v in (None, 0) else float(v) * 1e-3


#: GenTL 1.6 names the variable a producer's installer must extend. 32- and 64-bit
#: producers live in separate variables so both can be installed at once; this module
#: is 64-bit unless the interpreter says otherwise.
GENTL_PATH_VARS = ("GENICAM_GENTL64_PATH", "GENICAM_GENTL32_PATH")


def gentl_producers(env=None) -> list:
    """Every GenTL producer (``.cti``) installed on this machine, in the order the
    standard's path variable lists them.

    A producer registers itself at install time by extending
    ``GENICAM_GENTL{32,64}_PATH`` (GenTL 1.6). Reading that variable is why one code
    path reaches every vendor that ships a GenTL producer -- there is no per-vendor
    table here, and there does not need to be.

    Args:
        env: mapping to read instead of ``os.environ`` (for tests).
    Returns:
        list[str]: absolute paths to ``.cti`` files, de-duplicated, order preserved.
            Empty when no producer is installed -- which is a fact about the machine,
            not an error.
    """
    env = os.environ if env is None else env
    #: 64-bit first: a 64-bit interpreter must not load a 32-bit producer.
    names = GENTL_PATH_VARS if sys.maxsize > 2 ** 32 else GENTL_PATH_VARS[::-1]
    out, seen = [], set()
    for var in names:
        for part in (env.get(var) or "").split(os.pathsep):
            part = part.strip()
            if not part or not os.path.isdir(part):
                continue
            for fn in sorted(os.listdir(part)):
                if not fn.lower().endswith(".cti"):
                    continue
                full = os.path.join(part, fn)
                if full not in seen:
                    seen.add(full)
                    out.append(full)
    return out


def list_devices(backends=None) -> list:
    """Enumerate devices across every AVAILABLE backend, not just OpenCV indices.

    Each entry is ``{"backend", "id", "label"}`` where ``id`` is what to hand to
    :class:`Camera` (an index, a serial, or an opts key). Backends whose SDK is not
    installed are skipped silently; a backend whose enumeration raises is reported with
    ``"error"`` rather than dropped, because a device that is present but unreachable
    (permissions, a busy handle) must not look identical to no device at all.

    Args:
        backends: restrict to these backend names, or ``None`` for all available ones.
    Returns:
        list[dict]: one entry per device found.
    """
    caps = {c["name"]: c for c in capabilities()}
    want = [b for b in (backends or list(caps)) if caps.get(b, {}).get("available")]
    out = []
    for b in want:
        try:
            out.extend(_enumerate(b))
        except Exception as exc:                     # noqa: BLE001 - report, never drop
            out.append({"backend": b, "id": None, "label": "enumeration failed",
                        "error": "%s: %s" % (type(exc).__name__, str(exc)[:120])})
    return out


def _enumerate(backend: str) -> list:
    """Per-backend device enumeration. Hardware paths are exercised only where a device
    is present; with no SDK installed the caller never reaches them."""
    if backend == "opencv":
        return [{"backend": "opencv", "id": i, "label": "OpenCV device %d" % i}
                for i in list_cameras()]
    if backend == "basler":  # pragma: no cover - needs pypylon
        from pypylon import pylon
        return [{"backend": "basler", "id": d.GetSerialNumber(),
                 "label": "%s %s" % (d.GetModelName(), d.GetSerialNumber())}
                for d in pylon.TlFactory.GetInstance().EnumerateDevices()]
    if backend == "vimba":  # pragma: no cover - needs vmbpy
        from vmbpy import VmbSystem
        with VmbSystem.get_instance() as vmb:
            return [{"backend": "vimba", "id": c.get_id(),
                     "label": "%s %s" % (c.get_model(), c.get_id())}
                    for c in vmb.get_all_cameras()]
    if backend == "realsense":  # pragma: no cover - needs pyrealsense2
        import pyrealsense2 as rs
        return [{"backend": "realsense", "id": d.get_info(rs.camera_info.serial_number),
                 "label": d.get_info(rs.camera_info.name)}
                for d in rs.context().devices]
    if backend == "oak":  # pragma: no cover - needs depthai
        import depthai as dai
        return [{"backend": "oak", "id": d.getMxId(), "label": "OAK %s" % d.getMxId()}
                for d in dai.Device.getAllAvailableDevices()]
    if backend == "genicam":  # pragma: no cover - needs harvesters + a .cti
        #: ★以前はここが [] を返していた。GenTL を出す全ベンダを覆える唯一の経路
        #:   だけが列挙できない、という穴だった。プロデューサは GenTL 1.6 の
        #:   GENICAM_GENTL{32,64}_PATH に自分を登録するので、こちらはそれを読む。
        ctis = gentl_producers()
        if not ctis:
            return []
        from harvesters.core import Harvester
        h = Harvester()
        try:
            for cti in ctis:
                h.add_file(cti)
            h.update()
            out = []
            for i, d in enumerate(h.device_info_list):
                sn = getattr(d, "serial_number", None)
                model = getattr(d, "model", None) or getattr(d, "display_name", None)
                out.append({"backend": "genicam", "id": sn or i,
                            "label": "%s %s" % (model or "GenTL device", sn or i),
                            "vendor": getattr(d, "vendor", None),
                            "index": i})
            return out
        finally:
            #: プロデューサを開いたまま抜けると、次に開く側が掴めなくなる。
            h.reset()
    return []


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
