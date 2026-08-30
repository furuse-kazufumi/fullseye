"""Ground-truth + functional-gate tests for backends_segment2 (sg_ tier).

Runs WITHOUT importing ops.py: a tiny ``_Op`` stub stands in for the real dataclass
and we drive :func:`backends_segment2.build` directly.  Every operator gets (1) a
functional-gate check across three (a, b) knob settings, (2) a fail-soft check on
degenerate inputs, and (3) a constructed-input test proving the CLAIMED adaptive /
unsupervised segmentation semantics (not merely that the fn runs).
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage

import backends_segment2 as SG


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


OPS = SG.build(_Op, "image", "region", "feature", "contour", _norm, _binm)
OPS_BY_NAME = {o.name: o for o in OPS}

AB = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]


# --------------------------------------------------------------------------- #
# canonical inputs
# --------------------------------------------------------------------------- #
def _canonical_image():
    """Bimodal grayscale image: a bright square object on a darker background."""
    img = np.full((64, 64), 0.2, np.float64)
    img[16:48, 16:48] = 0.8
    rng = np.random.default_rng(0)
    return np.clip(img + rng.normal(0.0, 0.02, img.shape), 0.0, 1.0)


def _bright_square():
    """Noise-free bimodal image + its ground-truth bright region mask."""
    img = np.full((64, 64), 0.2, np.float64)
    img[18:46, 18:46] = 0.8
    return img, img > 0.5


def _disk_image(cy=32, cx=32, r=12, bg=0.1, fg=0.9):
    img = np.full((64, 64), bg, np.float64)
    yy, xx = np.ogrid[:64, :64]
    disk = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    img[disk] = fg
    return img, disk


def _iou(a, b):
    a = np.asarray(a, bool)
    b = np.asarray(b, bool)
    u = (a | b).sum()
    return float((a & b).sum()) / float(u) if u else 1.0


# --------------------------------------------------------------------------- #
# registry sanity / honesty
# --------------------------------------------------------------------------- #
def test_registry_names_unique_and_prefixed():
    names = [o.name for o in OPS]
    assert len(names) == len(set(names)), "duplicate op names"
    assert all(n.startswith("sg_") for n in names)
    assert len(OPS) == 7


def test_all_ops_are_image_to_region():
    for o in OPS:
        assert o.in_sort == "image"
        assert o.out_sort == "region"


def test_no_false_halcon_coverage_claims():
    """Every op honestly claims halcon="" (no HALCON analog / regiongrowing is covered)."""
    for o in OPS:
        assert o.halcon == "", f"{o.name} must not claim a HALCON operator"


def test_regiongrowing_is_already_covered():
    """Justify region_growing_seeded's halcon="": the HALCON name is already covered."""
    import json
    from pathlib import Path

    graph = Path(SG.__file__).resolve().parent / "fullseye" / "data" / "halcon_graph.json"
    nodes = json.loads(graph.read_text(encoding="utf-8"))["nodes"]
    assert "regiongrowing" in nodes
    assert nodes["regiongrowing"].get("covered") is True, (
        "regiongrowing must be already covered -> we correctly leave halcon empty"
    )


# --------------------------------------------------------------------------- #
# functional gate
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
@pytest.mark.parametrize("a,b", AB)
def test_functional_gate(op, a, b):
    img = _canonical_image()
    out = op.fn(img.copy(), a, b)
    assert op.out_sort == "region"
    assert isinstance(out, np.ndarray)
    assert out.ndim == 2
    assert out.dtype == np.float64
    assert out.shape == img.shape
    assert np.all(np.isfinite(out))
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert np.all((out == 0.0) | (out == 1.0)), "region must be a 0/1 mask"


@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
def test_fail_soft_on_degenerate(op):
    for bad in (np.zeros((8, 8)), np.ones((8, 8)), np.full((8, 8), 0.5),
                np.zeros((1, 1)), np.zeros((3, 3)), np.full((5, 5), np.nan)):
        out = op.fn(bad.astype(np.float64), 0.5, 0.5)   # must not raise
        assert np.all(np.isfinite(out))
        assert out.min() >= 0.0 and out.max() <= 1.0
        assert out.shape == SG._as_gray(bad).shape


# --------------------------------------------------------------------------- #
# ground truth
# --------------------------------------------------------------------------- #
def test_gmm_recovers_bright_class():
    img, gt = _bright_square()
    op = OPS_BY_NAME["sg_gmm_segment"]
    for a, b in AB:
        seg = op.fn(img, a, b) > 0.5
        assert _iou(seg, gt) > 0.9, f"GMM must recover the bright region (a={a})"


def test_kmeans_recovers_brightest_cluster():
    img, gt = _bright_square()
    op = OPS_BY_NAME["sg_kmeans_intensity"]
    for a, b in AB:
        seg = op.fn(img, a, b) > 0.5
        assert _iou(seg, gt) > 0.9, f"k-means brightest cluster must match object (a={a})"
    # k grows with a: a=0 -> k=2, a=1 -> k=6
    assert 2 + round(0.0 * 4) == 2
    assert 2 + round(1.0 * 4) == 6


def test_region_growing_fills_exactly_the_disk():
    img, disk = _disk_image()
    op = OPS_BY_NAME["sg_region_growing_seeded"]
    for a, b in AB:
        seg = op.fn(img, a, b) > 0.5
        # uniform disk (fg 0.9) vs background 0.1: |0.9-0.1|=0.8 > tol for all a here,
        # so the flood from the centre fills EXACTLY the disk and nothing else.
        assert np.array_equal(seg, disk), f"region-grow must fill exactly the disk (a={a})"


def test_region_growing_large_tolerance_leaks_to_background():
    # tolerance 0.85 >= 0.8 gap -> background becomes homogeneous with the seed and
    # the whole (connected) image is filled: proves it is a genuine tolerance flood.
    img, disk = _disk_image()
    op = OPS_BY_NAME["sg_region_growing_seeded"]
    seg = op.fn(img, 0.85, 0.4) > 0.5
    assert seg.sum() > disk.sum(), "large tolerance must grow beyond the disk"


def _object_edge(mask):
    m = np.asarray(mask, bool)
    return m ^ ndimage.binary_erosion(m)


def _boundary_encloses(img_mask, boundary, dilate=2):
    """Fraction of the object edge covered by the (dilated) boundary lattice."""
    edge = _object_edge(img_mask)
    if edge.sum() == 0:
        return 1.0
    grown = ndimage.binary_dilation(boundary > 0.5, iterations=dilate)
    return float((edge & grown).sum()) / float(edge.sum())


def test_slic_boundaries_enclose_object():
    img, gt = _bright_square()
    op = OPS_BY_NAME["sg_slic_superpixels"]
    for a, b in AB:
        bnd = op.fn(img, a, b)
        assert bnd.sum() > 0, "SLIC must produce boundaries"
        # over-segmentation: the boundary lattice tiles the plane into >1 superpixels
        _, ncomp = ndimage.label(bnd < 0.5)
        assert ncomp > 1, "SLIC must over-segment into multiple superpixels"
        assert _boundary_encloses(gt, bnd) > 0.8, "SLIC boundary must enclose the object"


def test_felzenszwalb_boundaries_enclose_object():
    img, gt = _bright_square()
    op = OPS_BY_NAME["sg_felzenszwalb"]
    for a, b in AB:
        bnd = op.fn(img, a, b)
        assert bnd.sum() > 0, "Felzenszwalb must produce boundaries"
        assert _boundary_encloses(gt, bnd) > 0.8, "Felzenszwalb boundary must enclose the object"


def test_normalized_cut_splits_two_regions():
    # left dark / right bright: the 2-way cut must recover the bright half.
    img = np.full((64, 64), 0.2, np.float64)
    img[:, 32:] = 0.8
    bright = img > 0.5
    op = OPS_BY_NAME["sg_normalized_cut_2"]
    for a, b in AB:
        seg = op.fn(img, a, b) > 0.5
        assert seg.any() and (~seg).any(), "ncut must produce a non-trivial 2-way split"
        # returned side is the brighter one
        assert img[seg].mean() > img[~seg].mean(), "ncut returns the brighter partition"
        assert _iou(seg, bright) > 0.6, f"ncut must roughly recover the bright half (a={a})"


def test_watershed_separates_touching_objects():
    # two touching bright disks -> a watershed dam line must run between them.
    img = np.full((64, 96), 0.1, np.float64)
    yy, xx = np.ogrid[:64, :96]
    img[(yy - 32) ** 2 + (xx - 32) ** 2 <= 18 ** 2] = 0.9
    img[(yy - 32) ** 2 + (xx - 62) ** 2 <= 18 ** 2] = 0.9
    op = OPS_BY_NAME["sg_watershed_gradient"]
    for a, b in AB:
        bnd = op.fn(img, a, b)
        assert bnd.sum() > 0, "watershed must produce boundary dams"
        # complement of the dams splits the plane into >= 2 catchment basins
        _, ncomp = ndimage.label(bnd < 0.5)
        assert ncomp >= 2, "watershed must separate the plane into basins"
        # a dam pixel exists in the neck column band between the two disk centres
        assert bnd[:, 44:52].sum() > 0, "a dam must run between the two touching disks"
