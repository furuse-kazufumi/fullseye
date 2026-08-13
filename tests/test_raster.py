"""Ground-truth tests for bit-depth-preserving raster I/O + metric depth import.

Every claim is proved by a real round-trip through a real backend: a 16-bit PNG
comes back with more than 256 levels (the core bug this module fixes), a float32
TIFF and a PFM come back bit-exact, and a metric depth map comes back in metres
with its invalid pixels masked. The PFM bottom-to-top ordering is checked
*independently* of the round-trip (a symmetric flip-on-write/flip-on-read bug
would round-trip fine yet still be wrong on disk), and the fail-closed paths
(garbage, oversized header, missing file, bad extension) are exercised.

Also pins the imgio.load() regression: an existing file OpenCV cannot decode must
NOT masquerade as FileNotFoundError, and 8-bit PNG must still load unchanged.
"""
import os
import sys

import numpy as np
import pytest

# imgevolve is a flat project: the package modules live one directory up.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import imageio.v2 as iio
import tifffile

import raster


def _rng():
    return np.random.default_rng(20260814)


def _write_bytes(tmp_path, name, content: bytes) -> str:
    p = tmp_path / name
    p.write_bytes(content)
    return str(p)


# --------------------------------------------------------------------------- #
# read_raster — the core bug: bit depth must survive                          #
# --------------------------------------------------------------------------- #
def test_read_raster_png16_preserves_bit_depth(tmp_path):
    """A 0..65535 ramp written as a 16-bit PNG must read back as uint16 with far
    more than the 256 levels an 8-bit demotion would leave."""
    ramp = np.linspace(0, 65535, 128 * 128).reshape(128, 128).astype(np.uint16)
    p = str(tmp_path / "ramp16.png")
    iio.imwrite(p, ramp)

    arr, meta = raster.read_raster(p)
    assert arr.dtype == np.uint16
    assert np.unique(arr).size > 256                 # <-- the regression this fixes
    assert meta["src_dtype"] == "uint16" and meta["channels"] == 1

    f = raster.to01(arr, meta)                       # explicit normalisation
    assert f.dtype == np.float64
    assert f.min() >= 0.0 and f.max() <= 1.0
    assert np.unique(f).size > 256                   # precision survives to01, too


def test_read_raster_float32_tiff_exact(tmp_path):
    a = (_rng().random((30, 40)).astype(np.float32) * 4.0 - 2.0)   # not in [0,1]
    p = str(tmp_path / "a.tif")
    tifffile.imwrite(p, a)

    arr, meta = raster.read_raster(p)
    assert arr.dtype == np.float32
    assert np.array_equal(arr, a)                    # bit-exact, no [0,1] scaling
    assert meta["backend"] == "tifffile" and meta["channels"] == 1


def test_read_raster_keep_dtype_false_normalises(tmp_path):
    ramp = np.linspace(0, 65535, 32 * 32).reshape(32, 32).astype(np.uint16)
    p = str(tmp_path / "r.png")
    iio.imwrite(p, ramp)
    arr, meta = raster.read_raster(p, keep_dtype=False)
    assert arr.dtype == np.float64 and meta.get("normalized") is True
    assert arr.max() <= 1.0 and np.unique(arr).size > 256


# --------------------------------------------------------------------------- #
# PFM — exact round-trip, both endian sign paths, real bottom-to-top ordering  #
# --------------------------------------------------------------------------- #
def test_pfm_roundtrip_both_endian_exact(tmp_path):
    a = (_rng().random((7, 5)).astype(np.float32) * 20.0 - 10.0)   # asymmetric
    for sc, tag in ((1.0, "big"), (-1.0, "little")):
        p = str(tmp_path / ("d_%s.pfm" % tag))
        raster.write_pfm(p, a, scale=sc)
        b, s = raster.read_pfm(p)
        assert b.dtype == np.float32 and b.shape == a.shape
        assert np.array_equal(b, a)                  # EXACT for both byte orders
        assert s == 1.0                              # magnitude returned, sign consumed
    # the sign on disk really flips between the two files
    big = open(str(tmp_path / "d_big.pfm"), "rb").read().splitlines()[2]
    little = open(str(tmp_path / "d_little.pfm"), "rb").read().splitlines()[2]
    assert not big.startswith(b"-") and little.startswith(b"-")


def test_pfm_color_three_channel_roundtrip(tmp_path):
    a = _rng().random((4, 6, 3)).astype(np.float32)
    p = str(tmp_path / "c.pfm")
    raster.write_pfm(p, a, scale=1.0)
    b, _ = raster.read_pfm(p)
    assert b.shape == (4, 6, 3)
    assert np.array_equal(b, a)


def test_pfm_is_bottom_to_top_on_disk(tmp_path):
    """Prove ordering independently of the round-trip: the FIRST row of samples on
    disk is the BOTTOM row of the image (a flip-on-both bug would still round-trip
    but store the wrong row first)."""
    a = np.arange(6, dtype=np.float32).reshape(3, 2)        # rows 0,1,2 distinct
    p = str(tmp_path / "order.pfm")
    raster.write_pfm(p, a, scale=1.0)                       # big-endian

    raw = open(p, "rb").read()
    idx = 0
    for _ in range(3):                                      # skip 3 header lines
        idx = raw.index(b"\n", idx) + 1
    on_disk = np.frombuffer(raw[idx:], dtype=">f4").reshape(3, 2)
    assert np.array_equal(on_disk[0], a[-1])               # bottom row stored first
    assert np.array_equal(on_disk[-1], a[0])               # top row stored last
    b, _ = raster.read_pfm(p)
    assert np.array_equal(b, a)                            # ...and read back upright


# --------------------------------------------------------------------------- #
# read_depth — metric metres + invalid mask                                    #
# --------------------------------------------------------------------------- #
def test_read_depth_png_millimetres(tmp_path):
    """16-bit PNG of integer millimetres (RealSense/Kinect): 0 = invalid."""
    mm = np.array([[1000, 2000, 0], [500, 0, 1500]], np.uint16)
    p = str(tmp_path / "depth16.png")
    iio.imwrite(p, mm)

    depth, valid = raster.read_depth(p, scale=0.001, invalid_value=0)
    exp_valid = mm != 0
    assert valid.dtype == bool and np.array_equal(valid, exp_valid)
    assert np.isnan(depth[~exp_valid]).all()                       # invalid -> NaN
    assert np.allclose(depth[exp_valid], mm[exp_valid].astype(np.float64) * 0.001)
    assert depth[0, 0] == pytest.approx(1.0)                       # 1000 mm -> 1.0 m


def test_read_depth_tiff_float_passthrough(tmp_path):
    d = (_rng().random((8, 8)).astype(np.float32) + 0.5)           # metres, all > 0
    p = str(tmp_path / "depth.tif")
    tifffile.imwrite(p, d)
    depth, valid = raster.read_depth(p)
    assert valid.all()
    assert np.allclose(depth, d.astype(np.float64))                # already metric


def test_read_depth_pfm(tmp_path):
    d = np.array([[1.0, 2.0], [3.0, 4.0]], np.float32)
    p = str(tmp_path / "depth.pfm")
    raster.write_pfm(p, d, scale=1.0)
    depth, valid = raster.read_depth(p)
    assert valid.all()
    assert np.allclose(depth, d)


# --------------------------------------------------------------------------- #
# save16 — a real high-precision writer, round-tripped                          #
# --------------------------------------------------------------------------- #
def test_save16_png_from_float_roundtrip(tmp_path):
    f01 = np.linspace(0.0, 1.0, 64 * 64).reshape(64, 64)
    p = str(tmp_path / "s.png")
    raster.save16(p, f01)
    arr, _ = raster.read_raster(p)
    assert arr.dtype == np.uint16
    assert np.unique(arr).size > 256                              # 16-bit, not 8-bit


def test_save16_tiff_float32_roundtrip(tmp_path):
    a = _rng().random((16, 16)).astype(np.float32)
    p = str(tmp_path / "s.tif")
    raster.save16(p, a)
    arr, _ = raster.read_raster(p)
    assert arr.dtype == np.float32
    assert np.array_equal(arr, a)                                 # float precision kept


# --------------------------------------------------------------------------- #
# imgio.load() bug regression                                                  #
# --------------------------------------------------------------------------- #
def test_imgio_load_float_tiff_is_not_false_filenotfound(tmp_path):
    """A float32 TIFF exists but OpenCV's GRAYSCALE decoder returns None. load()
    must NOT raise FileNotFoundError for the existing file — it must decode it via
    fallback or raise a clear ValueError."""
    import imgio
    a = _rng().random((12, 15)).astype(np.float32)
    p = str(tmp_path / "float.tif")
    tifffile.imwrite(p, a)
    assert os.path.exists(p)

    out = None
    try:
        out = imgio.load(p)
    except FileNotFoundError:
        pytest.fail("imgio.load raised FileNotFoundError for an existing file")
    except ValueError:
        out = None                                                # acceptable outcome
    if out is not None:                                           # decoded via fallback
        out = np.asarray(out)
        assert out.dtype == np.float64
        assert out.ndim == 2 and np.isfinite(out).all()


def test_imgio_load_8bit_png_unchanged(tmp_path):
    """The contract the operator suite depends on must not move: 8-bit PNG loads
    as float64 in [0, 1]."""
    import imgio
    img = (_rng().random((10, 10)) * 255).astype(np.uint8)
    p = str(tmp_path / "g8.png")
    iio.imwrite(p, img)
    out = imgio.load(p)
    assert out.dtype == np.float64
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert np.allclose(out, img.astype(np.float64) / 255.0, atol=1e-6)


def test_imgio_load_missing_file_raises_filenotfound(tmp_path):
    import imgio
    with pytest.raises(FileNotFoundError):
        imgio.load(str(tmp_path / "nope.png"))


# --------------------------------------------------------------------------- #
# fail-closed on untrusted input                                               #
# --------------------------------------------------------------------------- #
def test_read_raster_garbage_bytes_raise(tmp_path):
    junk = bytes(range(256)) + bytes(range(256))          # deterministic, not any format
    for name in ("junk.png", "junk.tif", "junk.pfm"):
        with pytest.raises(ValueError):
            raster.read_raster(_write_bytes(tmp_path, name, junk))


def test_read_raster_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        raster.read_raster(str(tmp_path / "nope.png"))


def test_read_raster_unsupported_extension_raises(tmp_path):
    p = _write_bytes(tmp_path, "x.xyz", b"whatever")
    with pytest.raises(ValueError, match="unsupported raster format"):
        raster.read_raster(p)


def test_pfm_oversized_header_is_refused(tmp_path):
    """Declared size (1000x1000 floats) far exceeds the bytes present -> refuse."""
    content = b"Pf\n1000 1000\n-1.0\n" + b"\x00" * 16
    p = _write_bytes(tmp_path, "big.pfm", content)
    with pytest.raises(ValueError, match="bytes remain"):
        raster.read_pfm(p)


def test_pfm_bogus_headers_are_refused(tmp_path):
    cases = {
        "badid.pfm": b"XY\n1 1\n-1.0\n\x00\x00\x00\x00",       # bad identifier
        "negdim.pfm": b"Pf\n-3 4\n-1.0\n",                     # non-positive dim
        "zeroscale.pfm": b"Pf\n2 2\n0\n" + b"\x00" * 16,       # zero scale
        "words.pfm": b"Pf\ntwo three\n-1.0\n",                 # non-integer dims
    }
    for name, content in cases.items():
        with pytest.raises(ValueError):
            raster.read_pfm(_write_bytes(tmp_path, name, content))


def test_pfm_pixel_cap_is_refused(tmp_path):
    huge = 1 << 20                                             # 1M x 1M >> MAX_PIXELS
    content = ("Pf\n%d %d\n-1.0\n" % (huge, huge)).encode("ascii")
    p = _write_bytes(tmp_path, "huge.pfm", content)
    with pytest.raises(ValueError, match="MAX_PIXELS"):
        raster.read_pfm(p)


def test_module_exports_match_all():
    for name in raster.__all__:
        assert hasattr(raster, name), name
