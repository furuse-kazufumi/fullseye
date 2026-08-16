"""Fail-closed name guard in backends_auto (regression).

`build()` documents "a spec whose `halcon` name is not a real HALCON operator is
dropped". That promise used to evaporate exactly where it mattered: `_real_ops()`
read only `data/halcon_operators.json`, which is NOT shipped in the wheel, and the
guard `if real and name not in real` short-circuits on an empty set — so on a
pip-installed package every fabricated / mistyped name was compiled in and counted.
"""
from __future__ import annotations

import backends_auto as BA

_FAKE_SPEC = [{"halcon": "totally_fake_operator_xyz", "category": "misc",
               "in_sort": "image", "out_sort": "image",
               "shape": "pointwise", "params": {"func": "tan"}}]


class _Op:                                  # minimal stand-in for ops.Op
    def __init__(self, name, category, halcon, in_sort, out_sort, fn):
        self.name, self.halcon = name, halcon


def _build():
    return BA.build(_Op, "image", "region", "feature", "contour", BA._norm, BA._bin)


def test_real_ops_survives_missing_flat_data_dir(tmp_path, monkeypatch):
    """The reference set must ship as code, not only as data/halcon_operators.json."""
    monkeypatch.setattr(BA, "HERE", str(tmp_path))          # simulate a wheel install
    real = BA._real_ops()
    assert len(real) > 2000
    assert "affine_trans_region" in real and "totally_fake_operator_xyz" not in real


def test_build_drops_fabricated_name(monkeypatch):
    monkeypatch.setattr(BA, "load_specs", lambda: list(_FAKE_SPEC))
    assert _build() == []
    assert BA.build.dropped == [("fake_name", "totally_fake_operator_xyz")]


def test_build_drops_everything_when_reference_unavailable(monkeypatch):
    """No reference => nothing is verified => nothing is admitted (fail-closed)."""
    monkeypatch.setattr(BA, "_real_ops", set)
    monkeypatch.setattr(BA, "load_specs", lambda: list(_FAKE_SPEC))
    assert _build() == []
    assert BA.build.dropped == [("unverified_name", "totally_fake_operator_xyz")]


def test_real_specs_still_build():
    """Guard tightening must not cost a single genuine op."""
    ops = _build()
    assert len(ops) == len(BA.load_specs())
    assert BA.build.dropped == []
