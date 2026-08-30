"""Ground-truth + functional-gate tests for backends_regions3 (r3_ tier).

Runs WITHOUT importing ops.py: a tiny ``_Op`` stub stands in for the real dataclass
and we drive :func:`backends_regions3.build` directly.  Every operator gets (1) a
functional-gate check across three (a, b) knob settings, (2) a fail-soft check on
degenerate inputs, and (3) a constructed-input test proving the CLAIMED semantics
(not merely that the fn runs).
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage

import backends_regions3 as R3


class _Op:
    def __init__(self, *a):
        self.name = a[0]
        self.halcon = a[2]
        self.in_sort = a[3]
        self.out_sort = a[4]
        self.fn = a[5]


def _norm(x):
    m = float(np.max(np.abs(x)))
    return x / m if m > 1e-8 else x


def _binm(v):
    return np.asarray(v) > 0.5


OPS = R3.build(_Op, "image", "region", "feature", "contour", _norm, _binm)
OPS_BY_NAME = {o.name: o for o in OPS}


# --------------------------------------------------------------------------- #
# canonical inputs
# --------------------------------------------------------------------------- #
def _canonical_region():
    """Mask with a disk, a rectangle blob and a small blob (multi-component)."""
    m = np.zeros((60, 60), np.float64)
    yy, xx = np.ogrid[:60, :60]
    m[(yy - 15) ** 2 + (xx - 15) ** 2 <= 9 ** 2] = 1.0     # disk
    m[35:50, 30:55] = 1.0                                  # rectangle
    m[5:9, 45:49] = 1.0                                    # small blob
    return m


AB = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]


# --------------------------------------------------------------------------- #
# registry sanity
# --------------------------------------------------------------------------- #
def test_registry_names_unique_and_prefixed():
    names = [o.name for o in OPS]
    assert len(names) == len(set(names)), "duplicate op names"
    assert all(n.startswith("r3_") for n in names)
    assert all(isinstance(o.halcon, str) and o.halcon for o in OPS), "every op claims a real name"
    assert len(OPS) == 10


def test_halcon_names_are_real_and_uncovered():
    """Every claimed HALCON name exists in the graph and was uncovered."""
    import json
    from pathlib import Path
    graph_path = Path(R3.__file__).resolve().parent / "fullseye" / "data" / "halcon_graph.json"
    nodes = json.loads(graph_path.read_text(encoding="utf-8"))["nodes"]
    for o in OPS:
        assert o.halcon in nodes, f"{o.halcon} not a real HALCON operator"
        assert nodes[o.halcon].get("covered") is False, f"{o.halcon} already covered"


# --------------------------------------------------------------------------- #
# functional gate
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
@pytest.mark.parametrize("a,b", AB)
def test_functional_gate(op, a, b):
    m = _canonical_region()
    out = op.fn(m.copy(), a, b)
    if op.out_sort == "region":
        assert isinstance(out, np.ndarray)
        assert out.ndim == 2
        assert out.dtype == np.float64
        assert out.shape == m.shape
        assert np.all(np.isfinite(out))
        assert out.min() >= 0.0 and out.max() <= 1.0
        assert np.all((out == 0.0) | (out == 1.0)), "region must be a 0/1 mask"
    elif op.out_sort == "feature":
        f = np.asarray(out)
        assert f.dtype == np.float64
        assert np.isfinite(float(f))
    else:
        raise AssertionError(f"unexpected out_sort {op.out_sort}")


@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
def test_fail_soft_on_degenerate(op):
    for bad in (np.zeros((8, 8)), np.ones((8, 8)), np.zeros((1, 1)), np.zeros((3, 3)),
                np.full((5, 5), np.nan)):
        out = op.fn(bad.astype(np.float64), 0.5, 0.5)     # must not raise
        if op.out_sort == "region":
            assert np.all(np.isfinite(out))
            assert out.min() >= 0.0 and out.max() <= 1.0
        else:
            assert np.isfinite(float(out))


# --------------------------------------------------------------------------- #
# ground truth
# --------------------------------------------------------------------------- #
def _annulus(h, w, cy, cx, r_in, r_out):
    yy, xx = np.ogrid[:h, :w]
    d2 = (yy - cy) ** 2 + (xx - cx) ** 2
    return ((d2 >= r_in * r_in) & (d2 <= r_out * r_out)).astype(np.float64)


def test_background_seg_full_is_complement_and_filters_small():
    # ring (annulus) => background has 2 components: outer (border) + inner hole
    m = _annulus(40, 40, 20, 20, 8, 15)
    op = OPS_BY_NAME["r3_background_seg"]
    full = op.fn(m, 0.0, 0.0)                              # a=0 -> exact background_seg
    assert np.array_equal(full > 0.5, ~(m > 0.5)), "a=0 returns the full background"
    _, n = ndimage.label(full > 0.5)
    assert n == 2, f"annulus background has an outer + a hole component (got {n})"
    # relative area filter drops the small enclosed hole, keeps the large outer bg
    filt = op.fn(m, 0.5, 0.0)
    _, n2 = ndimage.label(filt > 0.5)
    assert n2 == 1, "area filter drops the small hole component"
    assert filt[20, 20] == 0.0, "the enclosed hole was removed"
    assert filt[0, 0] == 1.0, "the large outer background survives"


def test_clip_region_keeps_only_central_window():
    m = np.ones((40, 40), np.float64)
    out = OPS_BY_NAME["r3_clip_region"].fn(m, 0.5, 0.5)    # central 20x20
    assert out[10:30, 10:30].mean() == 1.0, "central window kept"
    assert out[:10, :].sum() == 0.0 and out[30:, :].sum() == 0.0
    assert out[:, :10].sum() == 0.0 and out[:, 30:].sum() == 0.0
    assert out.sum() == 20 * 20


def test_eliminate_runs_severs_thin_bridge():
    m = np.zeros((40, 30), np.float64)
    m[2:12, 5:26] = 1.0                                    # top blob (wide runs)
    m[28:38, 5:26] = 1.0                                   # bottom blob (wide runs)
    m[12:28, 15] = 1.0                                     # 1-px vertical bridge (len-1 runs)
    _, n_before = ndimage.label(m > 0.5)
    assert n_before == 1, "blobs are joined by the bridge"
    out = OPS_BY_NAME["r3_eliminate_runs"].fn(m, 0.0, 0.0)  # min_len = 2
    _, n_after = ndimage.label(out > 0.5)
    assert n_after == 2, "removing len-1 runs severs the thin bridge"
    assert out[20, 15] == 0.0, "bridge pixels are gone"
    assert out[5, 15] == 1.0, "wide blob runs survive"


def test_rank_region_is_erosion_and_dilation():
    m = np.zeros((40, 40), np.float64)
    m[10:30, 10:30] = 1.0                                  # 20x20 solid square (area 400)
    op = OPS_BY_NAME["r3_rank_region"]
    erosion = op.fn(m, 0.0, 1.0)                           # sz=3, number=9 -> erosion
    dilation = op.fn(m, 0.0, 0.0)                          # sz=3, number=1 -> dilation
    assert erosion.sum() < 400.0, "full-count rank == erosion (shrinks)"
    assert dilation.sum() > 400.0, "number=1 rank == dilation (grows)"
    assert erosion.sum() == 18 * 18, "3x3 erosion removes a 1-px border"
    # dilation of a lone pixel fills the whole 3x3 window
    p = np.zeros((11, 11), np.float64)
    p[5, 5] = 1.0
    grown = op.fn(p, 0.0, 0.0)
    assert grown[4:7, 4:7].sum() == 9.0


def test_region_features_area_and_compactness():
    op = OPS_BY_NAME["r3_region_features"]
    m = np.zeros((40, 40), np.float64)
    m[10:30, 10:30] = 1.0                                  # area 400, size 1600
    assert abs(float(op.fn(m, 0.0, 0.0)) - 0.25) < 1e-9, "a<0.5 -> normalised area"
    comp_sq = float(op.fn(m, 0.9, 0.0))                    # a>=0.5 -> compactness
    assert abs(comp_sq - 16.0 / (4.0 * np.pi)) < 1e-6, "square compactness == 16/(4pi)"
    bar = np.zeros((40, 60), np.float64)
    bar[18:22, 5:55] = 1.0                                 # elongated bar
    comp_bar = float(op.fn(bar, 0.9, 0.0))
    assert comp_bar > 3.0, "an elongated bar is far less compact than a square"
    assert comp_bar > comp_sq


def test_runlength_distribution_variance_and_entropy():
    op = OPS_BY_NAME["r3_runlength_distribution"]
    # rows each carrying two runs of length 5 and 9 -> {5,9}: mean 7, variance 4
    m = np.zeros((10, 40), np.float64)
    m[3:7, 2:7] = 1.0                                      # run length 5
    m[3:7, 20:29] = 1.0                                    # run length 9
    assert abs(float(op.fn(m, 0.0, 0.0)) - 4.0) < 1e-9, "variance of {5,9} is 4"
    # equal counts of two distinct lengths -> entropy == 1 bit
    assert abs(float(op.fn(m, 0.9, 0.0)) - 1.0) < 1e-9, "entropy of two equal bins is 1"
    # constant run width -> zero variance
    solid = np.zeros((6, 20), np.float64)
    solid[1:5, 3:15] = 1.0                                 # every row width 12
    assert abs(float(op.fn(solid, 0.0, 0.0))) < 1e-12, "constant width -> variance 0"


def test_select_region_point_isolates_hit_component():
    m = np.zeros((40, 40), np.float64)
    m[2:12, 2:12] = 1.0                                    # component A
    m[20:30, 20:30] = 1.0                                  # component B
    op = OPS_BY_NAME["r3_select_region_point"]
    # point (7,7) is inside A: a=7/39, b=7/39
    a = 7.0 / 39.0
    out = op.fn(m, a, a)
    assert np.array_equal(out > 0.5, _blockmask(2, 12, 2, 12)), "only component A survives"
    assert out[2:12, 2:12].mean() == 1.0, "component A is kept"
    assert out[20:30, 20:30].sum() == 0.0, "component B is dropped"
    # a point in the background yields an empty region
    empty = op.fn(m, 0.4, 0.4)                             # (16,16) is background
    assert empty.sum() == 0.0


def _blockmask(r0, r1, c0, c1, shape=(40, 40)):
    z = np.zeros(shape, dtype=bool)
    z[r0:r1, c0:c1] = True
    return z


def test_partition_dynamic_cuts_neck_and_is_identity_when_uniform():
    op = OPS_BY_NAME["r3_partition_dynamic"]
    # dumbbell: two dense blobs joined by a low-density neck
    m = np.zeros((40, 40), np.float64)
    m[10:30, 2:12] = 1.0                                   # left blob, col density 20
    m[19:21, 12:20] = 1.0                                  # neck, col density 2
    m[10:30, 20:30] = 1.0                                  # right blob, col density 20
    _, n_before = ndimage.label(m > 0.5)
    assert n_before == 1
    cut = op.fn(m, 0.3, 0.0)                               # thresh = 6 -> neck (2) cut
    _, n_after = ndimage.label(cut > 0.5)
    assert n_after == 2, "region is split at the neck"
    assert cut[:, 12:20].sum() == 0.0, "neck columns cleared"
    assert cut[10:30, 2:12].mean() == 1.0, "blobs untouched"
    # uniform-density rectangle has no neck -> identity
    solid = np.zeros((30, 30), np.float64)
    solid[5:25, 5:25] = 1.0
    same = op.fn(solid, 0.3, 0.0)
    assert np.array_equal(same > 0.5, solid > 0.5), "uniform region is unchanged"


def test_polar_trans_region_maps_annulus_to_radial_band():
    h = w = 61
    ring = _annulus(h, w, 30, 30, 10, 20)
    out = OPS_BY_NAME["r3_polar_trans_region"].fn(ring, 1.0, 1.0)
    # small radius (top rows) samples the empty inner disk -> empty
    assert out[: h // 3, :].sum() == 0.0, "inner radii are background"
    # radii inside the ring form a filled horizontal band spanning all angles
    band = out[h // 2 + 2:, :]
    assert band.mean() > 0.9, "ring radii map to a filled band across angles"


def test_label_to_region_extracts_selected_gray_level():
    arr = np.zeros((40, 40), np.float64)
    arr[2:12, 2:12] = 0.25                                 # label 0
    arr[2:12, 20:30] = 0.5                                 # label 1
    arr[20:30, 2:12] = 1.0                                 # label 2
    op = OPS_BY_NAME["r3_label_to_region"]
    lo = op.fn(arr, 0.0, 0.0)                              # -> 0.25 block
    mid = op.fn(arr, 0.5, 0.0)                             # -> 0.5 block
    hi = op.fn(arr, 1.0, 0.0)                              # -> 1.0 block
    assert np.array_equal(lo > 0.5, _blockmask(2, 12, 2, 12))
    assert np.array_equal(mid > 0.5, _blockmask(2, 12, 20, 30))
    assert np.array_equal(hi > 0.5, _blockmask(20, 30, 2, 12))
    # a plain 0/1 mask has one label -> returns its foreground
    binary = _blockmask(5, 15, 5, 15).astype(np.float64)
    assert np.array_equal(op.fn(binary, 0.0, 0.0) > 0.5, binary > 0.5)
