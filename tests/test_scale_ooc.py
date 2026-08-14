"""Ground-truth tests for out-of-core / multithreaded large-image tiling (scale.py).

A tile-safe local operator must give the SAME result whether run whole-image,
serially tiled, in parallel, or out-of-core through a memmap — checked exactly on
the interior (where the receptive field fits inside the halo)."""
import numpy as np
from scipy import ndimage

import scale


def _op(arr, a=0.5, b=0.5):
    """A tile-safe local op: a 5x5 box filter (receptive field 2, needs halo >= 2)."""
    return ndimage.uniform_filter(np.asarray(arr, np.float64), 5, mode="nearest")


def _img(h=200, w=260, seed=0):
    return np.clip(ndimage.gaussian_filter(
        np.random.default_rng(seed).random((h, w)), 1.5), 0, 1)


def test_process_tiled_mt_matches_serial_and_whole():
    img = _img()
    whole = _op(img)
    serial = scale.process_tiled(_op, img, tile=64, halo=4)
    par = scale.process_tiled_mt(_op, img, tile=64, halo=4, workers=4)
    assert np.array_equal(serial, par)                 # parallel == serial, bit-identical
    # interior matches whole-image (halo 4 >= receptive field 2)
    assert np.allclose(par[8:-8, 8:-8], whole[8:-8, 8:-8], atol=1e-9)


def test_process_tiled_mt_single_worker():
    img = _img(seed=1)
    a = scale.process_tiled_mt(_op, img, tile=50, halo=4, workers=1)
    b = scale.process_tiled(_op, img, tile=50, halo=4)
    assert np.array_equal(a, b)


def test_open_memmap_roundtrip(tmp_path):
    p = str(tmp_path / "arr.npy")
    m = scale.open_memmap(p, shape=(30, 40), dtype=np.float64, mode="w+")
    m[:] = np.arange(30 * 40).reshape(30, 40)
    m.flush()
    del m
    r = scale.open_memmap(p, mode="r")
    assert r.shape == (30, 40)
    assert r[5, 7] == 5 * 40 + 7


def test_process_tiled_memmap_out_of_core(tmp_path):
    img = _img(h=180, w=220, seed=2)
    src_p = str(tmp_path / "src.npy")
    dst_p = str(tmp_path / "dst.npy")
    m = scale.open_memmap(src_p, shape=img.shape, dtype=np.float64, mode="w+")
    m[:] = img
    m.flush(); del m
    out = scale.process_tiled_memmap(_op, src_p, dst_p, tile=64, halo=4, workers=2)
    whole = _op(img)
    assert out.shape == img.shape
    assert np.allclose(out[8:-8, 8:-8], whole[8:-8, 8:-8], atol=1e-9)
    # and it equals the in-memory tiled result exactly
    assert np.allclose(np.asarray(out), scale.process_tiled(_op, img, tile=64, halo=4),
                       atol=1e-12)


def test_tile_specs_cover_everything():
    specs = scale._tile_specs(100, 130, tile=32, halo=4)
    covered = np.zeros((100, 130), bool)
    for y0, y1, x0, x1, *_ in specs:
        covered[y0:y1, x0:x1] = True
    assert covered.all()                               # every pixel written exactly once
