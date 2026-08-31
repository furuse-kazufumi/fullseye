# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""RLE 3-D regions: exact round trip, direct-on-runs queries, fail-closed decode."""
import numpy as np
import pytest

import volregion as vr


def _scene():
    m = np.zeros((12, 10, 16), np.float64)
    m[2:5, 3:7, 4:12] = 1.0           # box
    m[8, 1, 0] = 1.0                  # lone voxel at a low corner
    m[8, 1, 15] = 1.0                 # lone voxel at the x border (two runs, one row)
    m[11, 9, 5:9] = 1.0               # run touching the high z/y border
    return m


def test_round_trip_is_bit_exact():
    m = _scene()
    r = vr.vol_rle_encode(m)
    back = vr.vol_rle_decode(r)
    assert back.dtype == np.float64
    assert np.array_equal(back, m)
    # empty mask: zero runs, decodes to all-background
    r0 = vr.vol_rle_encode(np.zeros((3, 3, 3)))
    assert len(r0) == 0
    assert np.array_equal(vr.vol_rle_decode(r0), np.zeros((3, 3, 3)))
    # full mask: one run per plane row
    r1 = vr.vol_rle_encode(np.ones((3, 4, 5)))
    assert len(r1) == 3 * 4
    assert np.array_equal(vr.vol_rle_decode(r1), np.ones((3, 4, 5)))


def test_direct_queries_match_dense():
    import volops
    m = _scene()
    r = vr.vol_rle_encode(m)
    assert vr.vol_rle_volume(r) == int(m.sum())
    assert vr.vol_rle_bbox(r) == volops.vol_bounding_box(m)
    cz, cy, cx = vr.vol_rle_centroid(r)
    idx = np.argwhere(m > 0.5)
    assert np.allclose([cz, cy, cx], idx.mean(axis=0))
    # spacing gives physical coordinates
    cz2, cy2, cx2 = vr.vol_rle_centroid(r, spacing=(2.0, 3.0, 4.0))
    assert np.allclose([cz2, cy2, cx2], idx.mean(axis=0) * [2.0, 3.0, 4.0])


def test_memory_is_run_proportional():
    """The advertised claim: RLE cost tracks runs, not voxels."""
    m = np.zeros((64, 64, 64), np.float64)
    m[8:56, 8:56, 8:56] = 1.0                       # 110,592 voxels, 48*48 runs
    r = vr.vol_rle_encode(m)
    assert len(r) == 48 * 48
    assert r.nbytes < m.astype(bool).nbytes / 25    # measured 16x64x9? — well under
    assert vr.vol_rle_volume(r) == 48 ** 3


def test_empty_region_queries_fail_closed():
    r0 = vr.vol_rle_encode(np.zeros((3, 3, 3)))
    with pytest.raises(ValueError, match="empty"):
        vr.vol_rle_bbox(r0)
    with pytest.raises(ValueError, match="empty"):
        vr.vol_rle_centroid(r0)
    assert vr.vol_rle_volume(r0) == 0               # a count of 0 is a valid answer


def test_decode_rejects_corrupted_rle():
    """A hostile / corrupted RLE must never write out of bounds."""
    m = _scene()
    r = vr.vol_rle_encode(m)
    bad_row = vr.VolRLE(np.array([12 * 10], np.int64), np.array([0], np.int32),
                        np.array([4], np.int32), (12, 10, 16))
    with pytest.raises(ValueError, match="outside"):
        vr.vol_rle_decode(bad_row)
    bad_extent = vr.VolRLE(np.array([0], np.int64), np.array([4], np.int32),
                           np.array([99], np.int32), (12, 10, 16))
    with pytest.raises(ValueError, match="extent"):
        vr.vol_rle_decode(bad_extent)
    inverted = vr.VolRLE(np.array([0], np.int64), np.array([7], np.int32),
                         np.array([3], np.int32), (12, 10, 16))
    with pytest.raises(ValueError, match="extent"):
        vr.vol_rle_decode(inverted)
    absurd = vr.VolRLE(r.rows, r.starts, r.ends, (1 << 12, 1 << 12, 1 << 12))
    with pytest.raises(ValueError, match="cap"):
        vr.vol_rle_decode(absurd)
    with pytest.raises(ValueError, match="VolRLE"):
        vr.vol_rle_volume(m)                        # dense array is not a region


def test_encode_rejects_bad_input():
    with pytest.raises(ValueError, match="3-D"):
        vr.vol_rle_encode(np.zeros((4, 4)))
    bad = np.zeros((3, 3, 3))
    bad[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        vr.vol_rle_encode(bad)


def test_thresholding_convention_matches_volops():
    """> 0.5 binarisation — a gray 0.4 voxel is background, 0.6 is foreground."""
    m = np.zeros((2, 2, 4), np.float64)
    m[0, 0, 0] = 0.4
    m[0, 0, 1] = 0.6
    r = vr.vol_rle_encode(m)
    assert vr.vol_rle_volume(r) == 1
    assert vr.vol_rle_bbox(r) == (0, 0, 1, 1, 1, 2)
