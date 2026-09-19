# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Ground-truth tests for backends_texture (box-counting fractal dimension).

Each shape has a *known* box-counting dimension, so the op is checked against the
exact analytic value rather than for mere plausibility."""
import numpy as np
import pytest

import backends_texture as T


def _fd(img, a=0.5):
    return float(T.fractal_dimension(img, a, 0.5))


def test_sierpinski_matches_the_analytic_dimension():
    # Sierpinski triangle via the AND rule: pixel on iff (x & y) == 0.
    n = 256
    yy, xx = np.mgrid[0:n, 0:n]
    sp = np.zeros((n, n))
    sp[(xx & yy) == 0] = 1.0
    assert abs(_fd(sp) - np.log(3) / np.log(2)) < 0.03      # 1.585


def test_line_is_about_one_and_below_a_filled_area():
    line = np.zeros((256, 256))
    line[128, 16:240] = 1.0
    filled = np.zeros((256, 256))
    filled[32:224, 32:224] = 1.0
    d_line, d_fill = _fd(line), _fd(filled)
    assert 0.9 < d_line < 1.1
    assert d_fill > 1.7                                     # near 2 (finite-size underestimate)
    assert d_line < d_fill


def test_empty_and_single_point_are_zero():
    assert _fd(np.zeros((64, 64))) == 0.0
    pt = np.zeros((64, 64))
    pt[10, 10] = 1.0
    assert _fd(pt) == 0.0                                   # one box at every scale -> slope 0


def test_threshold_selects_structure():
    # a faint square below the threshold reads as empty; above, as a filled area.
    faint = np.zeros((128, 128))
    faint[32:96, 32:96] = 0.3
    assert _fd(faint, a=0.5) == 0.0                         # 0.3 < 0.5 -> nothing
    assert _fd(faint, a=0.1) > 1.7                          # 0.3 > 0.1 -> the square


def test_registered_in_the_facade_and_deterministic():
    import fullseye as fs
    assert fs.find_op("fractal_dimension") is not None
    n = 256
    yy, xx = np.mgrid[0:n, 0:n]
    sp = np.zeros((n, n))
    sp[(xx & yy) == 0] = 1.0
    d1 = float(fs.apply(sp, "fractal_dimension"))
    d2 = float(fs.apply(sp, "fractal_dimension"))
    assert d1 == d2 and abs(d1 - np.log(3) / np.log(2)) < 0.03


@pytest.mark.parametrize("bad", [0.5])
def test_non_finite_free(bad):
    d = _fd(np.clip(np.zeros((32, 32)) + 0.6, 0, 1))       # constant above threshold -> filled
    assert np.isfinite(d)
