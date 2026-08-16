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
