"""Fail-closed guards of the n-ary capability tier (regression).

`build_nary` claims "names not in the scraped reference are dropped, never counted"
and `verify` claims an op counts only if it returns the declared sort. Both leaked:

* `_real_ops()` read only `data/halcon_operators.json`, absent from the wheel, and
  `if real and h not in real` short-circuits on an empty set -> fabricated names
  compiled in and were counted covered.
* the region check was `out.min() >= 0 and out.max() <= 1`, which any grayscale
  image passes, and an identity result was counted as a pass.
"""
from __future__ import annotations

import numpy as np
import pytest

import imgops_nary as N

_REAL = "union2"                            # a real HALCON name, so only the gate decides
_FAKE = "totally_fake_operator_xyz"


def _gray(io, a, b):
    return np.clip(np.asarray(io[0], np.float64) * 0.5 + 0.25, 0, 1)


def _identity(io, a, b):
    return np.asarray(io[0], np.float64)


def test_real_ops_survives_missing_flat_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(N, "HERE", str(tmp_path))           # simulate a wheel install
    real = N._real_ops()
    assert len(real) > 2000
    assert _REAL in real and _FAKE not in real


def test_build_nary_drops_fabricated_name(monkeypatch):
    monkeypatch.setattr(N, "_DEFS",
                        [("fake_op", _FAKE, 2, (N.IMG, N.IMG), N.IMG, N._add, "fake")])
    assert N.build_nary() == []
    assert N.build_nary.dropped == [_FAKE]


def test_build_nary_drops_everything_without_reference(monkeypatch):
    monkeypatch.setattr(N, "_real_ops", set)
    assert N.build_nary() == []
    assert len(N.build_nary.dropped) == len(N._DEFS)


def test_verify_rejects_grayscale_region(monkeypatch):
    monkeypatch.setattr(N, "_DEFS",
                        [("gray_as_region", _REAL, 2, (N.REG, N.REG), N.REG, _gray, "")])
    v = N.verify()
    assert v["pass"] == 0
    assert v["fail"] == ["%s:region not binary {0,1}" % _REAL]


def test_verify_rejects_identity(monkeypatch):
    monkeypatch.setattr(N, "_DEFS",
                        [("noop", "add_image", 2, (N.IMG, N.IMG), N.IMG, _identity, "")])
    v = N.verify()
    assert v["pass"] == 0
    assert v["fail"] == ["add_image:identity on canonical inputs"]


def test_real_nary_ops_still_pass():
    """Tightening must not cost a genuine op: all 17 still build and verify."""
    v = N.verify()
    assert v["fail"] == []
    assert v["pass"] == v["n"] == len(N._DEFS)


# ---- 2026-09-03 semantics regressions -------------------------------------- #
def test_convol_image_is_a_correlation_not_a_flipped_convolution():
    """HALCON convol_image lays the mask over the image as written. With the
    single weight at mask[1, 2] (one column RIGHT of centre), correlation reads
    the pixel to the right: an impulse at (5, 5) answers at (5, 4). scipy's
    `convolve` flips the mask and would answer at (5, 6)."""
    img = np.zeros((11, 11))
    img[5, 5] = 1.0
    mask = np.zeros((3, 3))
    mask[1, 2] = 1.0
    out = N._convol([img, mask], 0.5, 0.4)
    assert np.unravel_index(int(out.argmax()), out.shape) == (5, 4)
    assert out[5, 4] > 0.99 and out[5, 6] == 0.0 and out[5, 5] == 0.0
    # a symmetric mask is unaffected (box blur stays a box blur)
    box = np.ones((3, 3))
    sym = N._convol([img, box], 0.5, 0.4)
    assert np.allclose(sym[4:7, 4:7], 1.0 / 9.0) and sym.sum() == pytest.approx(1.0)


def test_paint_gray_paints_dark_source_pixels():
    """HALCON paint_gray copies the source's grey values over its whole domain;
    this tier's domain convention is 'non-zero'. A dark (0.1) source pixel must
    be painted, not dropped by a > 0.5 threshold."""
    dst = np.full((3, 3), 0.9)
    src = np.zeros((3, 3))
    src[0, 0] = 0.1
    src[2, 2] = 0.7
    out = N._paint_gray([dst, src], 0.5, 0.4)
    assert out[0, 0] == pytest.approx(0.1)
    assert out[2, 2] == pytest.approx(0.7)
    assert out[1, 1] == 0.9                                   # outside the source domain
