"""Every typed ledger has the entry points ``fs.ledger.<op>`` relies on (call / get / info).

2026-11-03: ``opsfit`` had none of them, so ``fs.ledger.fit_circle_geometric`` and
``fs.ledger.phase_correlation_shift`` — the call line their op notes print — raised
``AttributeError: module 'opsfit' has no attribute 'call'``. The coverage recipes found it.
"""
import importlib
import os

import numpy as np
import pytest

os.environ.setdefault("FULLSEYE_DEVICE", "cpu")
import fullseye as fs  # noqa: E402
import opassist  # noqa: E402


@pytest.mark.parametrize("mod_name,table", opassist._LEDGERS)
def test_ledger_module_has_call_get_info(mod_name, table):
    mod = importlib.import_module(mod_name)
    for attr in ("call", "get", "info"):
        assert callable(getattr(mod, attr, None)), "%s has no %s()" % (mod_name, attr)
    ops = getattr(mod, table)
    assert ops, mod_name
    name = sorted(ops)[0]
    assert callable(mod.get(name)), (mod_name, name)


def test_fit_circle_geometric_through_the_ledger_recovers_a_circle():
    t = np.linspace(0, 2 * np.pi, 40, endpoint=False)
    pts = np.column_stack([3.0 + 2.5 * np.cos(t), -1.0 + 2.5 * np.sin(t)])
    out = fs.ledger.fit_circle_geometric(pts)
    vals = np.concatenate([np.ravel(np.asarray(v, dtype=float)) for v in
                           (out.values() if isinstance(out, dict) else out)])
    assert np.any(np.isclose(vals, 2.5, atol=1e-6)), out


def test_phase_correlation_shift_through_the_ledger():
    rng = np.random.default_rng(0)
    a = rng.random((64, 64))
    b = np.roll(a, (3, -5), axis=(0, 1))
    out = fs.ledger.phase_correlation_shift(a, b)
    vals = np.concatenate([np.ravel(np.asarray(v, dtype=float)) for v in
                           (out.values() if isinstance(out, dict) else out)
                           if np.asarray(v).dtype.kind in "fi"])
    assert np.any(np.isclose(np.abs(vals), 3.0, atol=0.05)) and np.any(np.isclose(np.abs(vals), 5.0, atol=0.05)), out
