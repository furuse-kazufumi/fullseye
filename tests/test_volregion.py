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
    """The advertised claim: RLE cost tracks runs, not voxels — so the saving
    grows with run length. Measured: 1/9.5 on a 64^3 cube (short runs), 1/145
    on the realistic 384^3 part in the module docstring (long runs)."""
    m = np.zeros((64, 64, 64), np.float64)
    m[8:56, 8:56, 8:56] = 1.0                       # 110,592 voxels, 48*48 runs
    r = vr.vol_rle_encode(m)
    assert len(r) == 48 * 48
    assert r.nbytes == 48 * 48 * 12                 # 12 bytes per run, exactly
    assert r.nbytes < m.astype(bool).nbytes / 9     # measured 1/9.48
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


# --------------------------------------------------------------------------- #
# set algebra on runs                                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_set_algebra_matches_dense_boolean(seed):
    """decode(op(A, B)) must equal the dense boolean op — for random masks."""
    rng = np.random.default_rng(seed)
    a = (rng.random((9, 7, 11)) > 0.6).astype(np.float64)
    b = (rng.random((9, 7, 11)) > 0.6).astype(np.float64)
    ra, rb = vr.vol_rle_encode(a), vr.vol_rle_encode(b)
    assert np.array_equal(vr.vol_rle_decode(vr.vol_rle_union(ra, rb)),
                          ((a > 0.5) | (b > 0.5)).astype(np.float64))
    assert np.array_equal(vr.vol_rle_decode(vr.vol_rle_intersect(ra, rb)),
                          ((a > 0.5) & (b > 0.5)).astype(np.float64))
    assert np.array_equal(vr.vol_rle_decode(vr.vol_rle_difference(ra, rb)),
                          ((a > 0.5) & ~(b > 0.5)).astype(np.float64))


def test_set_algebra_edge_cases_and_canonical_runs():
    m = _scene()
    r = vr.vol_rle_encode(m)
    empty = vr.vol_rle_encode(np.zeros(m.shape))
    # identities with the empty region
    assert vr.vol_rle_volume(vr.vol_rle_union(r, empty)) == vr.vol_rle_volume(r)
    assert vr.vol_rle_volume(vr.vol_rle_intersect(r, empty)) == 0
    assert vr.vol_rle_volume(vr.vol_rle_difference(r, r)) == 0
    assert vr.vol_rle_volume(vr.vol_rle_intersect(r, r)) == vr.vol_rle_volume(r)
    # adjacent runs merge to canonical form: [4,8) ∪ [8,12) = one run [4,12)
    a = np.zeros((1, 1, 16), np.float64); a[0, 0, 4:8] = 1.0
    b = np.zeros((1, 1, 16), np.float64); b[0, 0, 8:12] = 1.0
    u = vr.vol_rle_union(vr.vol_rle_encode(a), vr.vol_rle_encode(b))
    assert len(u) == 1 and (int(u.starts[0]), int(u.ends[0])) == (4, 12)
    # ...but runs of NEIGHBOURING plane rows must never merge (the +1 stride)
    c = np.zeros((1, 2, 16), np.float64); c[0, 0, 12:16] = 1.0; c[0, 1, 0:4] = 1.0
    rc = vr.vol_rle_encode(c)
    u2 = vr.vol_rle_union(rc, empty)
    assert len(u2) == 2
    assert np.array_equal(vr.vol_rle_decode(u2), c)
    # different shapes are refused
    other = vr.vol_rle_encode(np.zeros((2, 2, 2)))
    with pytest.raises(ValueError, match="different volumes"):
        vr.vol_rle_union(r, other)


def test_components_respect_connectivity_and_conserve_volume():
    v = np.zeros((8, 8, 8), np.float64)
    v[1:3, 1:3, 1:3] = 1.0                          # corner at (2,2,2)
    v[3:5, 3:5, 3:5] = 1.0                          # corner at (3,3,3) — diagonal touch
    c6 = vr.vol_rle_components(v, connectivity=6)
    c26 = vr.vol_rle_components(v, connectivity=26)
    assert len(c6) == 2 and len(c26) == 1           # same GT as volops.vol_label
    total = int(v.sum())
    assert sum(vr.vol_rle_volume(c) for c in c6) == total
    assert vr.vol_rle_volume(c26[0]) == total
    # each component decodes to a disjoint sub-mask whose union is the input
    u = np.zeros(v.shape)
    for c in c6:
        d = vr.vol_rle_decode(c)
        assert np.all(u + d <= 1.0)                 # disjoint
        u += d
    assert np.array_equal(u, v)
    assert vr.vol_rle_components(np.zeros((3, 3, 3))) == []
    with pytest.raises(ValueError, match="connectivity"):
        vr.vol_rle_components(v, connectivity=6.5)
