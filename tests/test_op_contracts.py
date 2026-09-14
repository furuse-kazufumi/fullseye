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


#: 探針バンク(``conftest.BANKS``)が持たない in_sort。ここに載る op は下の 3 つの
#: 契約ゲート(例外を投げない / 非有限を出さない / 決定的)を **一度も実行されない**。
#: ★2026-09-14 実測: 901 op 中 **151 本(16.8 %)** がこの状態で、空ループを 1 周
#: しただけで緑を返していた —— 「門が判定を計算した直後に捨てる」の親戚で、
#: こちらは **判定を一度も計算しない**。まず skip で見えるようにし、
#: ``test_probeless_ops_do_not_grow`` で本数を台帳に固定する(減る分には通る)。
PROBELESS_OPS_BUDGET = 151


def _probes(op):
    """この op に当てられる探針。空なら契約ゲートは何も検査できない。"""
    return list(inputs_for(op.in_sort))


@pytest.mark.parametrize("op", ALL_OPS, ids=OP_IDS)
def test_op_runs_without_exception(op):
    probes = _probes(op)
    if not probes:
        pytest.skip("in_sort '%s' に探針が無い(BANKS 未対応)" % op.in_sort)
    for iname, iv in probes:
        for a, b in KNOBS:
            op.fn(copy_input(iv), a, b)  # must not raise


@pytest.mark.parametrize("op", ALL_OPS, ids=OP_IDS)
def test_op_output_is_finite(op):
    """No NaN/Inf on ANY battery input — degenerate inputs are the acid test."""
    probes = _probes(op)
    if not probes:
        pytest.skip("in_sort '%s' に探針が無い(BANKS 未対応)" % op.in_sort)
    for iname, iv in probes:
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
    probes = _probes(op)
    if not probes:
        pytest.skip("in_sort '%s' に探針が無い(BANKS 未対応)" % op.in_sort)
    for iname, iv in probes:
        ref = op.fn(copy_input(iv), 0.5, 0.5)
        for _ in range(3):
            again = op.fn(copy_input(iv), 0.5, 0.5)
            assert _equal(ref, again), f"{op.name} is nondeterministic on input '{iname}'"


def test_probeless_ops_do_not_grow():
    """探針の当たらない op を**台帳で固定**する(減る分には通る)。

    上の 3 つの契約ゲートは、探針が無い op に対しては何も検査できない。skip に
    したので見えるようにはなったが、**skip は緑**なので放っておくと増える。
    ここで本数を上限として押さえ、新しい in_sort を足した人が探針も足すよう促す。
    ★本来の直しは ``conftest.BANKS`` を全 in_sort へ広げること(``op_probe`` の
    探針生成を流用できる)。この台帳はその作業までの見張りであって、代わりではない。
    """
    from collections import Counter
    probeless = Counter(op.in_sort for op in ALL_OPS if not _probes(op))
    total = sum(probeless.values())
    assert total <= PROBELESS_OPS_BUDGET, (
        "探針の無い op が %d 本に増えた(上限 %d)。内訳 %s —— "
        "新しい in_sort を足したなら conftest.BANKS に探針も足すこと"
        % (total, PROBELESS_OPS_BUDGET, dict(probeless)))


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
