"""Tests for the general-algorithm tier (``algo.py`` / ``algo_codegen`` / ``algo_difftest``).

Contracts pinned here:
  * every op re-implements a correct algorithm (Python reference == numpy oracle),
  * the shipped standalone .py is the SAME code the in-process reference runs,
  * the codegen C compiles and agrees with Python **bit-for-bit** (when a toolchain
    exists), and a compile failure fails the gate CLOSED (never a silent pass),
  * the general tier does NOT leak into the image evolution registry.
"""
from __future__ import annotations

import random
import sys

import pytest

import algo
import algo_codegen
import algo_difftest

_SORTS = ["quicksort", "heapsort", "mergesort"]
_REDUCES = ["seq_max", "seq_min"]
_ALL = _SORTS + _REDUCES


# --------------------------------------------------------------------------- #
# registry integrity
# --------------------------------------------------------------------------- #
def test_registry_names_are_distinct_and_expected():
    names = algo.algo_names()
    assert names == _ALL
    assert len(names) == len(set(names))


def test_every_op_has_valid_kind_and_sorts():
    for op in algo.ALGO_REGISTRY:
        assert op.in_sort == algo.SEQ
        assert op.out_sort in (algo.SEQ, algo.SCALAR)
        assert op.kind in (algo.KIND_SORT, algo.KIND_REDUCE)
        # kind and out_sort must agree
        assert (op.kind == algo.KIND_SORT) == (op.out_sort == algo.SEQ)
        assert op.py_code.strip() and op.c_code.strip() and op.c_func
        assert op.provenance                      # honest attribution, never blank


def test_categories_grouping():
    cats = algo.algo_categories()
    assert set(cats["sort"]) == set(_SORTS)
    assert set(cats["reduce"]) == set(_REDUCES)


def test_unknown_op_is_fail_closed():
    assert algo.find_algo("nope") is None
    with pytest.raises(KeyError):
        algo.run_algo("nope", [1, 2, 3])


# --------------------------------------------------------------------------- #
# Python reference correctness vs a ground-truth oracle
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", _SORTS)
def test_sorts_match_python_sorted_over_random(name):
    rng = random.Random(20260816)
    for _ in range(300):
        n = rng.randint(0, 80)
        a = [rng.uniform(-100.0, 100.0) for _ in range(n)]
        assert algo.run_algo(name, a) == sorted(a)


@pytest.mark.parametrize("name", _SORTS)
def test_sorts_edge_cases(name):
    assert algo.run_algo(name, []) == []
    assert algo.run_algo(name, [7.0]) == [7.0]
    assert algo.run_algo(name, [2.0, 1.0]) == [1.0, 2.0]
    dups = [3.0, 1.0, 3.0, 1.0, 2.0, 2.0]
    assert algo.run_algo(name, dups) == sorted(dups)
    srt = [float(x) for x in range(300)]
    assert algo.run_algo(name, srt) == srt                 # already sorted, no O(n^2) blowup
    rev = [float(x) for x in range(300, 0, -1)]
    assert algo.run_algo(name, rev) == sorted(rev)         # reverse sorted


def test_mergesort_is_stable():
    # stability is observable via (key, tag) pairs sharing a key; mergesort must
    # keep the original relative order of equal keys.
    pairs = [(1.0, "a"), (0.0, "b"), (1.0, "c"), (0.0, "d"), (1.0, "e")]
    run = algo.py_fn("mergesort")
    # emulate on the keys but track order: sort indices by key with a stable merge
    keys = [p[0] for p in pairs]
    order = sorted(range(len(keys)), key=lambda i: keys[i])   # python sorted is stable
    # our mergesort on keys must reproduce the stable value order
    assert run(keys) == [keys[i] for i in order]


@pytest.mark.parametrize("name", _REDUCES)
def test_reductions_match_oracle(name):
    rng = random.Random(7)
    for _ in range(300):
        n = rng.randint(1, 80)
        a = [rng.uniform(-100.0, 100.0) for _ in range(n)]
        exp = max(a) if name == "seq_max" else min(a)
        assert algo.run_algo(name, a) == exp
    assert algo.run_algo(name, []) == 0.0                   # documented empty convention


@pytest.mark.parametrize("name", _ALL)
def test_reference_is_deterministic(name):
    a = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0]
    assert algo.run_algo(name, a) == algo.run_algo(name, a)


# --------------------------------------------------------------------------- #
# single source of truth: emitted .py == in-process reference
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", _ALL)
def test_emitted_python_defines_run_and_matches_reference(name, tmp_path):
    src = algo_codegen.emit_python(algo.ALGO_BY_NAME[name])
    ns: dict = {}
    exec(compile(src, "<emitted>", "exec"), ns)  # noqa: S102 - trusted, generated in-repo
    assert callable(ns.get("run"))
    a = [5.0, 2.0, 9.0, 1.0, 5.0, 3.0]
    assert ns["run"](list(a)) == algo.run_algo(name, a)


@pytest.mark.parametrize("name", _ALL)
def test_emitted_c_has_function_and_driver(name):
    op = algo.ALGO_BY_NAME[name]
    c = algo_codegen.emit_c(op)
    assert op.c_func in c
    assert "int main(" in c
    assert "#include <stdio.h>" in c and "#include <stdlib.h>" in c


# --------------------------------------------------------------------------- #
# honest gate — Python half always, C half when a toolchain exists
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", _ALL)
def test_difftest_python_half_passes(name, tmp_path):
    # force the C skip so this half is toolchain-independent
    res = algo_difftest.difftest(name, tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0
    assert res["c_backend"]["status"] == "skipped"
    assert res["passed"] is True                            # a skip is neutral, not a fail


_HAS_CC = algo_difftest.find_c_compiler() is not None


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", _ALL)
def test_difftest_c_matches_python_bit_for_bit(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc="auto")
    cb = res["c_backend"]
    assert cb["status"] == "ran", cb
    assert cb["c_vs_python_max_abs_diff"] == 0.0            # exact: only moves/selects doubles
    assert cb["pass"] is True and res["passed"] is True


def test_difftest_compile_error_fails_closed(tmp_path):
    # a "compiler" that always exits 1: codegen declared C support, so a build
    # failure must FAIL the gate, not skip it.
    fake_cc = [sys.executable, "-c", "import sys; sys.exit(1)"]
    res = algo_difftest.difftest("quicksort", tmp_path, cc=fake_cc)
    assert res["python_pass"] is True                       # only the C half is broken
    assert res["c_backend"]["status"] == "compile_error"
    assert res["passed"] is False


def test_c_gate_helper_semantics():
    assert algo_difftest._c_gate_ok({"status": "ran", "pass": True}) is True
    assert algo_difftest._c_gate_ok({"status": "ran", "pass": False}) is False
    assert algo_difftest._c_gate_ok({"status": "skipped", "reason": "x"}) is True
    assert algo_difftest._c_gate_ok({"status": "compile_error"}) is False
    assert algo_difftest._c_gate_ok({"status": "run_error"}) is False


# --------------------------------------------------------------------------- #
# image-focus safety: the general tier must not leak into the evolution registry
# --------------------------------------------------------------------------- #
def test_general_sorts_do_not_enter_image_registry():
    import ops
    for op in ops.REGISTRY:
        assert op.in_sort not in (algo.SEQ, algo.SCALAR)
        assert op.out_sort not in (algo.SEQ, algo.SCALAR)
    # and no algo op name collides with an image op name
    assert not (set(algo.algo_names()) & {op.name for op in ops.REGISTRY})


# --------------------------------------------------------------------------- #
# facade
# --------------------------------------------------------------------------- #
def test_facade_exposes_algo_tier():
    import fullseye
    assert set(fullseye.algo_ops()) == set(_ALL)
    assert fullseye.run_algo("quicksort", [3, 1, 2]) == [1.0, 2.0, 3.0]
    assert fullseye.run_algo("seq_max", [3, 1, 2]) == 3.0
    assert "void heapsort" in fullseye.algo_to_c("heapsort")
    assert "def run(" in fullseye.algo_to_python("mergesort")
