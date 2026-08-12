"""Universal contracts every operator in the registry must honour.

These are parametrized over the ENTIRE registry, so adding an operator
automatically subjects it to the same guarantees. Four contracts:

  * runs without exception on the edge-input battery,
  * every ndarray/feature output is finite (no NaN/Inf) — even on degenerate
    (constant / empty) inputs,
  * repeated calls on identical input are bit-identical (determinism — the
    evolution's holdout scoring depends on it),
  * the output matches the operator's declared out_sort (and regions stay in
    the unit range).
"""
from __future__ import annotations

import numpy as np
import pytest

import ops
from conftest import KNOBS, copy_input, inputs_for

ALL_OPS = list(ops.REGISTRY)
OP_IDS = [op.name for op in ALL_OPS]


def _arrays(out):
    """Yield numeric ndarrays contained in an op output (handles contour dicts)."""
    if isinstance(out, np.ndarray):
        if out.size and np.issubdtype(out.dtype, np.number):
            yield out
    elif isinstance(out, dict):
        for c in out.get("cs", []):
            if isinstance(c, np.ndarray) and c.size:
                yield c


def _equal(x, y) -> bool:
    if isinstance(x, np.ndarray) and isinstance(y, np.ndarray):
        return x.shape == y.shape and np.array_equal(x, y, equal_nan=True)
    if isinstance(x, dict) and isinstance(y, dict):
        cs1, cs2 = x.get("cs", []), y.get("cs", [])
        return len(cs1) == len(cs2) and all(
            a.shape == b.shape and np.array_equal(a, b) for a, b in zip(cs1, cs2))
    try:
        return bool(np.all(np.asarray(x) == np.asarray(y)))
    except Exception:
        return repr(x) == repr(y)


@pytest.mark.parametrize("op", ALL_OPS, ids=OP_IDS)
def test_op_runs_without_exception(op):
    for iname, iv in inputs_for(op.in_sort):
        for a, b in KNOBS:
            op.fn(copy_input(iv), a, b)  # must not raise


@pytest.mark.parametrize("op", ALL_OPS, ids=OP_IDS)
def test_op_output_is_finite(op):
    """No NaN/Inf on ANY battery input — degenerate inputs are the acid test."""
    for iname, iv in inputs_for(op.in_sort):
        for a, b in KNOBS:
            out = op.fn(copy_input(iv), a, b)
            for arr in _arrays(out):
                bad = ~np.isfinite(arr)
                assert not bad.any(), (
                    f"{op.name} produced {int(bad.sum())} non-finite value(s) "
                    f"on input '{iname}' (a={a}, b={b})")
            if op.out_sort == "feature":
                f = np.asarray(out, np.float64).reshape(-1)
                assert f.size >= 1 and np.isfinite(f[0]), (
                    f"{op.name} feature non-finite on '{iname}' (a={a}, b={b})")


@pytest.mark.parametrize("op", ALL_OPS, ids=OP_IDS)
def test_op_is_deterministic(op):
    """Same input twice -> identical output (required for reproducible scoring).

    Iterate every battery input and repeat 3x: uninitialized-buffer bugs
    (e.g. cv2 warp on unmapped pixels) are flaky, so a single input/pair can
    miss them. A correct op is identical across all of them.
    """
    for iname, iv in inputs_for(op.in_sort):
        ref = op.fn(copy_input(iv), 0.5, 0.5)
        for _ in range(3):
            again = op.fn(copy_input(iv), 0.5, 0.5)
            assert _equal(ref, again), f"{op.name} is nondeterministic on input '{iname}'"


@pytest.mark.parametrize("op", ALL_OPS, ids=OP_IDS)
def test_op_honours_declared_sort(op):
    iv = next(iter(inputs_for(op.in_sort)), None)
    if iv is None:
        pytest.skip(f"no input bank for sort {op.in_sort}")
    out = op.fn(copy_input(iv[1]), 0.5, 0.5)
    os_ = op.out_sort
    if os_ in ("image", "region"):
        assert isinstance(out, np.ndarray) and out.ndim == 2, f"{op.name} {os_} not 2-D ndarray"
    elif os_ == "color":
        assert isinstance(out, np.ndarray) and out.ndim == 3 and out.shape[-1] == 3
    elif os_ == "volume":
        assert isinstance(out, np.ndarray) and out.ndim == 3
    elif os_ == "feature":
        assert np.asarray(out, np.float64).reshape(-1).size >= 1
    elif os_ == "contour":
        assert isinstance(out, dict) and "cs" in out and "shape" in out
    elif os_ == "match":
        assert isinstance(out, np.ndarray) and out.ndim == 1


@pytest.mark.parametrize("op", [o for o in ALL_OPS if o.out_sort == "region"],
                         ids=[o.name for o in ALL_OPS if o.out_sort == "region"])
def test_region_output_in_unit_range(op):
    for iname, iv in inputs_for(op.in_sort):
        out = op.fn(copy_input(iv), 0.5, 0.5)
        if isinstance(out, np.ndarray) and out.size:
            mn, mx = float(np.min(out)), float(np.max(out))
            assert mn >= -1e-9 and mx <= 1 + 1e-9, (
                f"{op.name} region out of [0,1] on '{iname}': min={mn} max={mx}")
