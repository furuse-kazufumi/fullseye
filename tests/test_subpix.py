"""Ground-truth + contract tests for backends_subpix (sub-pixel critical points).

These deliberately do NOT import ops.py: they exercise ``build()`` directly via a
tiny stub Op, so the module's semantics are verified in isolation.  Two layers:

  1. FUNCTIONAL GATE — every op returns a well-formed CONTOUR dict (finite points
     inside the image domain) on a canonical battery of edge inputs.
  2. GROUND TRUTH — each op is proven on a constructed input whose answer is known
     analytically (a Gaussian peak's centre, a saddle's centre, flat-region
     centroids, a basin centre).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backends_subpix as sp

# --- stub Op / helpers as mandated by the harness --------------------------- #
IMAGE, REGION, FEATURE, CONTOUR = "image", "region", "feature", "contour"


class _Op:
    def __init__(self, *a):
        self.name = a[0]
        self.halcon = a[2]
        self.in_sort = a[3]
        self.out_sort = a[4]
        self.fn = a[5]


def _norm(x):
    m = float(np.max(np.abs(x)))
    return (x / m) if m > 1e-8 else x


def _binm(v):
    return np.asarray(v) > 0.5


OPS = sp.build(_Op, IMAGE, REGION, FEATURE, CONTOUR, _norm, _binm)
BY_NAME = {op.name: op for op in OPS}
GATE_KNOBS = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]


# --- canonical input battery (IMAGE sort) ----------------------------------- #
def _battery():
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    bump = np.exp(-(((yy - 19.4) ** 2 + (xx - 21.6) ** 2) / (2 * 2.0 ** 2)))
    normal = np.clip(0.4 * grad + 0.6 * bump, 0, 1)
    single = np.zeros((n, n)); single[n // 2, n // 2] = 1.0
    saddle = np.clip(0.5 + 0.01 * ((xx - 20) ** 2 - (yy - 20) ** 2), 0, 1)
    return {
        "normal": normal,
        "bump": np.clip(bump, 0, 1),
        "saddle": saddle,
        "const0": np.zeros((n, n)),
        "const1": np.ones((n, n)),
        "const_mid": np.full((n, n), 0.42),
        "single_bright": single,
        "tiny4": (np.arange(16, dtype=np.float64) / 15.0).reshape(4, 4),
        "tiny2": np.array([[0.2, 0.8], [0.6, 0.1]]),
    }


def _assert_contour(out, H, W):
    assert isinstance(out, dict), "op must return a dict"
    assert set(out) >= {"shape", "cs"}, "dict needs 'shape' and 'cs'"
    sh = out["shape"]
    assert isinstance(sh, tuple) and len(sh) == 2
    assert all(isinstance(int(s), int) for s in sh)
    for c in out["cs"]:
        assert isinstance(c, np.ndarray)
        assert c.dtype == np.float64
        assert c.ndim == 2 and c.shape[1] == 2
        assert np.isfinite(c).all()
        assert (c[:, 0] >= -1e-9).all() and (c[:, 0] <= H - 1 + 1e-9).all()
        assert (c[:, 1] >= -1e-9).all() and (c[:, 1] <= W - 1 + 1e-9).all()


# --------------------------------------------------------------------------- #
# 1. FUNCTIONAL GATE                                                          #
# --------------------------------------------------------------------------- #
def test_expected_ops_present():
    assert set(BY_NAME) == {
        "sp_local_max_sub_pix", "sp_local_min_sub_pix", "sp_saddle_points_sub_pix",
        "sp_critical_points_sub_pix", "sp_plateaus", "sp_lowlands_center",
    }
    for op in OPS:
        assert op.name.startswith("sp_")
        assert op.in_sort == IMAGE and op.out_sort == CONTOUR


@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
def test_functional_gate(op):
    for iv in _battery().values():
        H, W = iv.shape
        for a, b in GATE_KNOBS:
            out = op.fn(np.array(iv, copy=True), a, b)
            _assert_contour(out, H, W)


@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
def test_determinism(op):
    img = _battery()["normal"]
    o1 = op.fn(img.copy(), 0.3, 0.4)
    o2 = op.fn(img.copy(), 0.3, 0.4)
    assert len(o1["cs"]) == len(o2["cs"])
    for x, y in zip(o1["cs"], o2["cs"]):
        assert np.array_equal(x, y)


@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
def test_fail_soft_on_bad_input(op):
    for bad in (np.zeros((0, 0)), np.array([[np.nan, np.inf], [1.0, -np.inf]])):
        out = op.fn(bad, 0.3, 0.4)
        assert isinstance(out, dict) and "cs" in out


# --------------------------------------------------------------------------- #
# 2. GROUND TRUTH                                                             #
# --------------------------------------------------------------------------- #
def _gauss(cr, cc, s=2.0, n=41):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    return np.clip(np.exp(-(((yy - cr) ** 2 + (xx - cc) ** 2) / (2 * s * s))), 0, 1)


def test_local_max_sub_pix_recovers_gaussian_centre():
    cr, cc = 20.37, 18.62
    img = _gauss(cr, cc)
    out = BY_NAME["sp_local_max_sub_pix"].fn(img, 0.1, 0.0)
    assert len(out["cs"]) == 1, "a single Gaussian bump -> exactly one maximum"
    r, c = out["cs"][0][0]
    err = float(np.hypot(r - cr, c - cc))
    assert err < 0.3, f"sub-pixel max off by {err:.3f}px"


def test_local_min_sub_pix_recovers_valley_centre():
    cr, cc = 22.6, 17.3
    img = 1.0 - 0.9 * _gauss(cr, cc)      # a single valley at (cr, cc)
    out = BY_NAME["sp_local_min_sub_pix"].fn(img, 0.1, 0.0)
    assert len(out["cs"]) == 1
    r, c = out["cs"][0][0]
    err = float(np.hypot(r - cr, c - cc))
    assert err < 0.3, f"sub-pixel min off by {err:.3f}px"


def test_local_max_finds_no_max_on_valley():
    # An image that only has a minimum must yield no maxima (and vice versa).
    img = 1.0 - 0.9 * _gauss(20.0, 20.0)
    assert len(BY_NAME["sp_local_max_sub_pix"].fn(img, 0.1, 0.0)["cs"]) == 0


def test_saddle_points_sub_pix_at_known_centre():
    m = 15
    yy, xx = np.mgrid[0:m, 0:m].astype(np.float64)
    scr, scc = 7.0, 7.0
    z = np.clip(0.5 + 0.01 * ((xx - scc) ** 2 - (yy - scr) ** 2), 0, 1)  # z = x^2 - y^2
    out = BY_NAME["sp_saddle_points_sub_pix"].fn(z, 0.1, 0.0)
    assert len(out["cs"]) >= 1, "the quadratic saddle must be detected"
    pts = np.array([c[0] for c in out["cs"]])
    d = np.hypot(pts[:, 0] - scr, pts[:, 1] - scc)
    assert d.min() < 0.3, f"saddle off by {d.min():.3f}px"


def test_saddle_has_no_extrema():
    # A pure saddle image must have no strict local max or min.
    m = 15
    yy, xx = np.mgrid[0:m, 0:m].astype(np.float64)
    z = np.clip(0.5 + 0.01 * ((xx - 7.0) ** 2 - (yy - 7.0) ** 2), 0, 1)
    assert len(BY_NAME["sp_local_max_sub_pix"].fn(z, 0.1, 0.0)["cs"]) == 0
    assert len(BY_NAME["sp_local_min_sub_pix"].fn(z, 0.1, 0.0)["cs"]) == 0


def test_critical_points_is_union_of_types():
    # Build an image with one clear max, one clear min and one saddle region;
    # critical = max ∪ min ∪ saddle (concatenation), so its count is the sum.
    n = 31
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    img = np.clip(0.5 + 0.25 * np.sin(xx / 2.2) * np.cos(yy / 2.2), 0, 1)
    a = 0.05
    nmax = len(BY_NAME["sp_local_max_sub_pix"].fn(img, a, 0.0)["cs"])
    nmin = len(BY_NAME["sp_local_min_sub_pix"].fn(img, a, 0.0)["cs"])
    nsad = len(BY_NAME["sp_saddle_points_sub_pix"].fn(img, a, 0.0)["cs"])
    ncrit = len(BY_NAME["sp_critical_points_sub_pix"].fn(img, a, 0.0)["cs"])
    assert ncrit == nmax + nmin + nsad
    assert nmax >= 1 and nmin >= 1 and nsad >= 1, "the test image must exercise all three"


def test_critical_points_contains_the_gaussian_peak():
    cr, cc = 20.4, 19.7
    img = _gauss(cr, cc)
    out = BY_NAME["sp_critical_points_sub_pix"].fn(img, 0.1, 0.0)
    pts = np.array([c[0] for c in out["cs"]])
    d = np.hypot(pts[:, 0] - cr, pts[:, 1] - cc)
    assert d.min() < 0.3


def test_plateaus_returns_flat_region_centroids():
    img = np.zeros((30, 30))
    img[5:12, 6:13] = 0.5          # 7x7 plateau centred at (8, 9)
    img[20:27, 18:25] = 0.8        # 7x7 plateau centred at (23, 21)
    out = BY_NAME["sp_plateaus"].fn(img, 0.2, 0.0)
    pts = np.array([c[0] for c in out["cs"]])
    assert len(pts) >= 2

    def _near(target):
        d = np.hypot(pts[:, 0] - target[0], pts[:, 1] - target[1])
        return d.min() < 0.6
    assert _near((8.0, 9.0)) and _near((23.0, 21.0))


def test_plateaus_absent_on_strictly_varying_image():
    # An image varying in BOTH directions has no equal-valued 4-neighbours -> no
    # plateaus (a plain vertical gradient would legitimately be per-column plateaus).
    n = 24
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = (xx + 2.0 * yy) / (3.0 * (n - 1))    # every 4-neighbour differs
    assert len(BY_NAME["sp_plateaus"].fn(grad, 0.0, 0.0)["cs"]) == 0


def test_lowlands_center_finds_basin_not_peak():
    img = np.ones((30, 30)) * 0.7
    img[11:17, 11:17] = 0.2        # a low basin, centre (13.5, 13.5)
    img[3:8, 20:25] = 0.95         # a high plateau, must NOT be a lowland
    out = BY_NAME["sp_lowlands_center"].fn(img, 0.1, 0.0)
    pts = np.array([c[0] for c in out["cs"]])
    # the basin centroid is present ...
    dbasin = np.hypot(pts[:, 0] - 13.5, pts[:, 1] - 13.5)
    assert dbasin.min() < 0.6
    # ... and the high plateau centroid is absent.
    dpeak = np.hypot(pts[:, 0] - 5.0, pts[:, 1] - 22.0)
    assert dpeak.min() > 1.0


def test_lowlands_depth_threshold_respects_a():
    # A shallow basin (depth 0.05) is rejected when the depth threshold (a) is high.
    img = np.ones((24, 24)) * 0.5
    img[10:14, 10:14] = 0.45       # depth 0.05
    shallow = BY_NAME["sp_lowlands_center"].fn(img, 0.9, 0.0)   # min_depth ~0.37
    deep = BY_NAME["sp_lowlands_center"].fn(img, 0.0, 0.0)      # min_depth ~0.01
    got_shallow = any(np.hypot(c[0][0] - 11.5, c[0][1] - 11.5) < 0.6 for c in shallow["cs"])
    got_deep = any(np.hypot(c[0][0] - 11.5, c[0][1] - 11.5) < 0.6 for c in deep["cs"])
    assert got_deep and not got_shallow


def test_constant_image_has_extrema_empty_but_one_plateau():
    img = np.full((20, 20), 0.3)
    assert len(BY_NAME["sp_local_max_sub_pix"].fn(img, 0.2, 0.0)["cs"]) == 0
    assert len(BY_NAME["sp_local_min_sub_pix"].fn(img, 0.2, 0.0)["cs"]) == 0
    assert len(BY_NAME["sp_saddle_points_sub_pix"].fn(img, 0.2, 0.0)["cs"]) == 0
    plat = BY_NAME["sp_plateaus"].fn(img, 0.2, 0.0)["cs"]
    assert len(plat) == 1               # the whole image is one flat region
    r, c = plat[0][0]
    assert abs(r - 9.5) < 1e-6 and abs(c - 9.5) < 1e-6
