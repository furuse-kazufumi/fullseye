"""Ground-truth + contract tests for backends_measure1d (1-D caliper measurement).

These deliberately do NOT import ops.py: they exercise ``build()`` directly via a
tiny stub Op, so the module's semantics are verified in isolation.  Two layers:

  1. FUNCTIONAL GATE — every op, on a canonical battery of images and a knob grid,
     returns its declared sort (finite scalar FEATURE, or a well-formed CONTOUR
     dict with in-domain points).
  2. GROUND TRUTH — a bright bar with analytically known edges: measure_thresh
     counts exactly 2 crossings across it, measure_pos / fuzzy_measure_pos return
     the two edges at the expected sub-pixel positions, measure_pairs counts 1
     rising->falling pair, and measure_projection returns the known profile mean.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backends_measure1d as m1

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


OPS = m1.build(_Op, IMAGE, REGION, FEATURE, CONTOUR, _norm, _binm)
BY_NAME = {op.name: op for op in OPS}
GATE_KNOBS = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]


# --- canonical input battery (IMAGE sort) ----------------------------------- #
def _battery():
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    col_ramp = xx / (n - 1)
    diag = np.clip((xx + yy) / (2 * (n - 1)), 0, 1)
    bar = np.zeros((n, n)); bar[:, 14:26] = 1.0
    checker = ((yy.astype(int) // 4 + xx.astype(int) // 4) % 2).astype(np.float64)
    return {
        "col_ramp": col_ramp,
        "diag": diag,
        "bar": bar,
        "checker": checker,
        "const0": np.zeros((n, n)),
        "const1": np.ones((n, n)),
        "const_mid": np.full((n, n), 0.42),
        "tiny2": np.array([[0.2, 0.8], [0.6, 0.1]]),
        "tiny3": (np.arange(9, dtype=np.float64) / 8.0).reshape(3, 3),
    }


def _assert_feature(out):
    assert np.ndim(out) == 0, "FEATURE op must return a scalar"
    val = np.asarray(out, np.float64)
    assert val.dtype == np.float64
    assert np.isfinite(val), "FEATURE must be finite"


def _assert_contour(out, H, W):
    assert isinstance(out, dict), "CONTOUR op must return a dict"
    assert set(out) >= {"shape", "cs"}, "dict needs 'shape' and 'cs'"
    sh = out["shape"]
    assert isinstance(sh, tuple) and len(sh) == 2
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
        "m1_measure_projection", "m1_measure_pos", "m1_measure_thresh",
        "m1_measure_pairs", "m1_fuzzy_measure_pos",
    }
    for op in OPS:
        assert op.name.startswith("m1_")
        assert op.in_sort == IMAGE


def test_declared_sorts():
    assert BY_NAME["m1_measure_projection"].out_sort == FEATURE
    assert BY_NAME["m1_measure_thresh"].out_sort == FEATURE
    assert BY_NAME["m1_measure_pairs"].out_sort == FEATURE
    assert BY_NAME["m1_measure_pos"].out_sort == CONTOUR
    assert BY_NAME["m1_fuzzy_measure_pos"].out_sort == CONTOUR


def test_halcon_names_nonempty_and_prefixed():
    # Every op in this module claims a real HALCON measure operator.
    for op in OPS:
        assert op.halcon != "", f"{op.name} should carry a HALCON name"


@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
def test_functional_gate(op):
    for iv in _battery().values():
        H, W = iv.shape
        for a, b in GATE_KNOBS:
            out = op.fn(np.array(iv, copy=True), a, b)
            if op.out_sort == FEATURE:
                _assert_feature(out)
            else:
                _assert_contour(out, H, W)


@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
def test_determinism(op):
    img = _battery()["diag"]
    o1 = op.fn(img.copy(), 0.3, 0.4)
    o2 = op.fn(img.copy(), 0.3, 0.4)
    if op.out_sort == FEATURE:
        assert float(o1) == float(o2)
    else:
        assert len(o1["cs"]) == len(o2["cs"])
        for x, y in zip(o1["cs"], o2["cs"]):
            assert np.array_equal(x, y)


@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
def test_fail_soft_on_bad_input(op):
    for bad in (np.zeros((0, 0)), np.array([[np.nan, np.inf], [1.0, -np.inf]]),
                np.array([5.0])):
        out = op.fn(bad, 0.3, 0.4)
        if op.out_sort == FEATURE:
            _assert_feature(out)
        else:
            assert isinstance(out, dict) and "cs" in out


# --------------------------------------------------------------------------- #
# 2. GROUND TRUTH — a bright bar with analytically known edges.              #
# --------------------------------------------------------------------------- #
def _bar_image(n=41, lo=15, hi=26, val=1.0, bg=0.0):
    """Vertical bright bar: columns [lo, hi) = val, else bg.

    Sampled along the centred horizontal line (a=0) the profile steps
    bg->val at col lo-0.5 and val->bg at col hi-0.5, so edges sit at
    (row=(n-1)/2, col=lo-0.5) and (col=hi-0.5)."""
    img = np.full((n, n), bg, np.float64)
    img[:, lo:hi] = val
    return img


# a = 0  ->  theta = 0  ->  horizontal caliper line through the centre row.
def test_measure_thresh_counts_two_crossings_across_bar():
    img = _bar_image()
    val = float(m1.m1_measure_thresh(img, 0.0, 0.5))   # level 0.5 between bg=0 and val=1
    assert val == 2.0, f"a bright bar crosses level 0.5 exactly twice; got {val}"


def test_measure_thresh_zero_when_level_above_bar():
    img = _bar_image(val=0.6)
    # level 0.9 is never reached -> no crossings.
    assert float(m1.m1_measure_thresh(img, 0.0, 0.9)) == 0.0


def test_measure_pos_returns_two_bar_edges_subpixel():
    img = _bar_image(lo=15, hi=26)          # edges at col 14.5 and 25.5
    out = m1.m1_measure_pos(img, 0.0, 0.2)
    pts = np.array([c[0] for c in out["cs"]])
    assert len(pts) == 2, f"the bar has exactly two edges; got {len(pts)}"
    cols = np.sort(pts[:, 1])
    assert abs(cols[0] - 14.5) < 0.1, f"rising edge off: {cols[0]:.3f}"
    assert abs(cols[1] - 25.5) < 0.1, f"falling edge off: {cols[1]:.3f}"
    # both edges lie on the centre row (row 20 of a 41-row image).
    assert np.allclose(pts[:, 0], 20.0, atol=1e-6)


def test_measure_pos_count_is_primary():
    # measure_pos's primary result is the edge count == number of sub-contours.
    img = _bar_image()
    assert len(m1.m1_measure_pos(img, 0.0, 0.2)["cs"]) == 2


def test_measure_pos_empty_on_constant_image():
    img = np.full((30, 30), 0.4)
    assert len(m1.m1_measure_pos(img, 0.0, 0.2)["cs"]) == 0


def test_measure_pairs_counts_one_pair_for_one_bar():
    img = _bar_image()
    assert float(m1.m1_measure_pairs(img, 0.0, 0.2)) == 1.0


def test_measure_pairs_counts_two_pairs_for_two_bars():
    img = np.zeros((41, 61), np.float64)
    img[:, 10:18] = 1.0        # bar 1: edges 9.5, 17.5
    img[:, 34:44] = 1.0        # bar 2: edges 33.5, 43.5
    assert float(m1.m1_measure_pairs(img, 0.0, 0.2)) == 2.0


def test_fuzzy_measure_pos_returns_bar_edges():
    img = _bar_image(lo=15, hi=26)
    out = m1.m1_fuzzy_measure_pos(img, 0.0, 0.5)
    pts = np.array([c[0] for c in out["cs"]])
    assert len(pts) == 2
    cols = np.sort(pts[:, 1])
    assert abs(cols[0] - 14.5) < 0.15 and abs(cols[1] - 25.5) < 0.15


def test_fuzzy_measure_pos_threshold_prunes_weaker_edges():
    # A bar with one strong (full-contrast) edge and one weak (low-contrast) edge:
    # the fuzzy amplitude membership rejects the weak edge at a high threshold.
    img = np.zeros((41, 61), np.float64)
    img[:, :20] = 0.0
    img[:, 20:40] = 1.0        # strong rising edge at col 19.5 (amp large)
    img[:, 40:] = 0.9          # weak falling edge at col 39.5 (amp small)
    strict = m1.m1_fuzzy_measure_pos(img, 0.0, 0.9)   # keep only near-max membership
    loose = m1.m1_fuzzy_measure_pos(img, 0.0, 0.0)    # keep all
    strong_cols = sorted(c[0][1] for c in strict["cs"])
    all_cols = sorted(c[0][1] for c in loose["cs"])
    assert any(abs(c - 19.5) < 0.3 for c in strong_cols), "strong edge must survive"
    assert all(abs(c - 39.5) > 1.0 for c in strong_cols), "weak edge must be pruned"
    assert any(abs(c - 39.5) < 0.6 for c in all_cols), "weak edge present when kept"


def test_measure_projection_mean_of_column_ramp():
    # Column ramp img[r,c] = c/(W-1); centred horizontal line -> profile is the
    # ramp itself, mean = 0.5 (band-averaging over rows leaves columns unchanged).
    n = 41
    _, xx = np.mgrid[0:n, 0:n]
    ramp = xx.astype(np.float64) / (n - 1)
    val = float(m1.m1_measure_projection(ramp, 0.0, 0.5))
    assert abs(val - 0.5) < 0.02, f"projection mean off: {val:.4f}"


def test_measure_projection_constant_image():
    img = np.full((30, 30), 0.37)
    assert abs(float(m1.m1_measure_projection(img, 0.3, 0.5)) - 0.37) < 1e-3


def test_measure_projection_offset_selects_different_line():
    # A half-bright / half-dark image split at the centre row; the perpendicular
    # offset b moves the horizontal caliper line into the bright or dark half.
    img = np.zeros((41, 41), np.float64)
    img[:20, :] = 1.0          # top half (rows < 20) bright, bottom half dark
    # n = (-cos0, sin0) = (-1, 0): b > 0.5 shifts the line toward row 0 (bright),
    # b < 0.5 toward the last row (dark).
    bright = float(m1.m1_measure_projection(img, 0.0, 0.9))  # line near row 4
    dark = float(m1.m1_measure_projection(img, 0.0, 0.1))    # line near row 36
    assert bright > 0.8 and dark < 0.2, f"offset failed: bright={bright}, dark={dark}"
