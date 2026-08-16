"""Tests for the general-algorithm tier (``algo.py`` / ``algo_codegen`` / ``algo_difftest``).

Contracts pinned here:
  * every op re-implements a correct algorithm (Python reference == numpy oracle),
  * the shipped standalone .py is the SAME code the in-process reference runs,
  * the codegen C compiles and agrees with Python **bit-for-bit** (when a toolchain
    exists), and a compile failure fails the gate CLOSED (never a silent pass),
  * the general tier does NOT leak into the image evolution registry.
"""
from __future__ import annotations

import math
import random
import sys

import pytest

import algo
import algo_codegen
import algo_difftest

_SORTS = ["quicksort", "heapsort", "mergesort"]
_REDUCES = ["seq_max", "seq_min"]
# P2: oracle-tolerance ops. simpson/bisection/newton are seq -> scalar; gauss_solve
# is a variable-length seq -> seq map (KIND_MAP).
_NUMERIC = ["simpson", "bisection", "newton", "gauss_solve"]
_ALL = _SORTS + _REDUCES                            # the EXACT ops (bit/oracle == 0)
_ALL_OPS = _ALL + _NUMERIC


# --------------------------------------------------------------------------- #
# registry integrity
# --------------------------------------------------------------------------- #
def test_registry_names_are_distinct_and_expected():
    names = algo.algo_names()
    assert names == _ALL_OPS
    assert len(names) == len(set(names))


def test_every_op_has_valid_kind_and_sorts():
    for op in algo.ALGO_REGISTRY:
        assert op.in_sort == algo.SEQ
        assert op.out_sort in (algo.SEQ, algo.SCALAR)
        assert op.kind in (algo.KIND_SORT, algo.KIND_REDUCE, algo.KIND_MAP)
        # out_sort and kind must agree: a SEQ output comes from a seq-producing kind
        # (an in-place sort or a variable-length map); a SCALAR output from a reduction.
        assert (op.out_sort == algo.SEQ) == (op.kind in (algo.KIND_SORT, algo.KIND_MAP))
        assert (op.out_sort == algo.SCALAR) == (op.kind == algo.KIND_REDUCE)
        assert op.py_code.strip() and op.c_code.strip() and op.c_func
        assert op.provenance                      # honest attribution, never blank


def test_categories_grouping():
    cats = algo.algo_categories()
    assert set(cats["sort"]) == set(_SORTS)
    assert set(cats["reduce"]) == set(_REDUCES)
    assert set(cats["numeric"]) == set(_NUMERIC)


# --------------------------------------------------------------------------- #
# P2 numeric ops (Simpson integration + polynomial root finders)
# --------------------------------------------------------------------------- #
def test_numeric_known_answers():
    import math
    # integral of x^2 on [0,2] = 8/3 (samples at 0,.5,1,1.5,2, h=0.5)
    assert algo.run_algo("simpson", [0.5, 0.0, 0.25, 1.0, 2.25, 4.0]) == pytest.approx(8 / 3, abs=1e-9)
    # root of x^2 - 2 -> sqrt(2), by bisection in [1,2] and Newton from 1.5
    assert algo.run_algo("bisection", [1.0, 2.0, -2.0, 0.0, 1.0]) == pytest.approx(math.sqrt(2), abs=1e-9)
    assert algo.run_algo("newton", [1.5, -2.0, 0.0, 1.0]) == pytest.approx(math.sqrt(2), abs=1e-9)


def test_simpson_linear_is_exact_and_edges():
    # Simpson integrates a linear function exactly; integral of y=x on [0,1], h=0.25
    assert algo.run_algo("simpson", [0.25, 0.0, 0.25, 0.5, 0.75, 1.0]) == pytest.approx(0.5, abs=1e-12)
    assert algo.run_algo("simpson", []) == 0.0
    assert algo.run_algo("simpson", [0.5]) == 0.0            # no samples
    assert algo.run_algo("simpson", [0.5, 3.0]) == 0.0       # single sample -> 0


def test_root_finders_fail_soft():
    # bracket with no sign change -> a point in [lo,hi], not a root, and no crash
    r = algo.run_algo("bisection", [0.0, 1.0, 1.0, 0.0, 1.0])   # p=x^2+1 > 0 everywhere
    assert 0.0 <= r <= 1.0
    # newton with a vanishing derivative at x0 -> returns x0 (no divide-by-zero crash)
    assert algo.run_algo("newton", [0.0, -1.0, 0.0, 1.0]) == 0.0   # p'=2x=0 at x0=0


def test_simpson_even_sample_trapezoid_tail():
    # EVEN sample count (odd interval count) exercises the trapezoid-tail branch.
    # y=x on [0,1] with 4 samples (h=1/3) -> exact 0.5 (both Simpson and trapezoid
    # are exact on a line), so this pins the tail branch to a known answer.
    third = 1.0 / 3.0
    got = algo.run_algo("simpson", [third, 0.0, third, 2 * third, 1.0])
    assert got == pytest.approx(0.5, abs=1e-12)
    # a non-linear even-m case: y=x^2 on [0,1], 4 samples -> Simpson[0,2/3] + trap tail
    ys = [(i * third) ** 2 for i in range(4)]
    got2 = algo.run_algo("simpson", [third] + ys)
    assert got2 > 0.0 and math.isfinite(got2)


def test_newton_non_convergence_is_fail_soft():
    # x^3 - 2x + 2 from x0=0 is a classic Newton 2-cycle -> returns a non-root, no crash
    r = algo.run_algo("newton", [0.0, 2.0, -2.0, 0.0, 1.0])
    assert math.isfinite(r)                                  # fail-soft: finite, no exception
    residual = 2.0 - 2.0 * r + r ** 3
    assert abs(residual) > 1e-3                              # honestly NOT a root (documented)


# --------------------------------------------------------------------------- #
# P2 gauss_solve — variable-length seq -> seq (KIND_MAP): linear system solve
# --------------------------------------------------------------------------- #
def _pack_system(A, b):
    """Pack an n x n matrix A and RHS b into the gauss input seq [n, aug row-major]."""
    n = len(b)
    seq = [float(n)]
    for i in range(n):
        seq.extend(float(v) for v in A[i])
        seq.append(float(b[i]))
    return seq


def test_gauss_is_kind_map():
    op = algo.ALGO_BY_NAME["gauss_solve"]
    assert op.kind == algo.KIND_MAP           # the new variable-length seq->seq kind
    assert op.out_sort == algo.SEQ and op.in_sort == algo.SEQ


def test_gauss_known_answers():
    # 1x1: 4x = 8 -> x = 2
    assert algo.run_algo("gauss_solve", [1.0, 4.0, 8.0]) == pytest.approx([2.0], abs=1e-12)
    # 2x2: x + y = 3 ; x - y = 1  -> x=2, y=1
    got = algo.run_algo("gauss_solve", _pack_system([[1.0, 1.0], [1.0, -1.0]], [3.0, 1.0]))
    assert got == pytest.approx([2.0, 1.0], abs=1e-12)
    # 3x3 identity -> solution is the RHS itself
    ident = algo.run_algo("gauss_solve", _pack_system(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], [5.0, -2.0, 7.0]))
    assert ident == pytest.approx([5.0, -2.0, 7.0], abs=1e-12)


def test_gauss_matches_numpy_over_random():
    np = pytest.importorskip("numpy")
    rng = random.Random(20260816)
    for _ in range(200):
        n = rng.randint(1, 6)
        A = [[rng.uniform(-5.0, 5.0) for _ in range(n)] for _ in range(n)]
        for i in range(n):                      # diagonal dominance -> well-conditioned
            A[i][i] = sum(abs(A[i][j]) for j in range(n)) + rng.uniform(1.0, 3.0)
        x = [rng.uniform(-10.0, 10.0) for _ in range(n)]
        b = [sum(A[i][j] * x[j] for j in range(n)) for i in range(n)]
        got = algo.run_algo("gauss_solve", _pack_system(A, b))
        ref = np.linalg.solve(np.asarray(A), np.asarray(b)).tolist()
        assert got == pytest.approx(ref, abs=1e-9)


def test_gauss_partial_pivoting_needed():
    # a[0][0] == 0 forces a pivot swap; the (permuted) system is still non-singular.
    #   0*x + 1*y = 1 ; 1*x + 0*y = 2  -> x=2, y=1
    got = algo.run_algo("gauss_solve", _pack_system([[0.0, 1.0], [1.0, 0.0]], [1.0, 2.0]))
    assert got == pytest.approx([2.0, 1.0], abs=1e-12)


def test_gauss_variable_length_output():
    # the whole point of KIND_MAP: output length (n) != input length (1 + n*(n+1)).
    seq = _pack_system([[2.0, 0.0], [0.0, 2.0]], [4.0, 6.0])
    out = algo.run_algo("gauss_solve", seq)
    assert len(seq) == 7 and len(out) == 2                  # 1 + 2*3 = 7 in, 2 out
    assert out == pytest.approx([2.0, 3.0], abs=1e-12)


def test_gauss_fail_soft_malformed_and_singular():
    assert algo.run_algo("gauss_solve", []) == []           # empty
    assert algo.run_algo("gauss_solve", [0.0]) == []        # n < 1
    assert algo.run_algo("gauss_solve", [2.0, 1.0, 2.0]) == []   # too few values for 2x2
    # singular: two identical rows -> no unique solution -> [] (fail-soft, no crash)
    assert algo.run_algo("gauss_solve", _pack_system([[1.0, 1.0], [1.0, 1.0]], [2.0, 2.0])) == []
    # a zero column (whole variable absent) is also singular
    assert algo.run_algo("gauss_solve", _pack_system([[0.0, 1.0], [0.0, 2.0]], [1.0, 2.0])) == []


def test_gauss_does_not_mutate_input():
    seq = _pack_system([[1.0, 1.0], [1.0, -1.0]], [3.0, 1.0])
    snapshot = list(seq)
    algo.py_fn("gauss_solve")(seq)
    assert seq == snapshot


def test_gauss_codegen_emits_varlen_driver():
    c = algo_codegen.emit_c(algo.ALGO_BY_NAME["gauss_solve"])
    assert "int gauss_solve(const double* a, int n_in, double* out)" in c
    assert "int out_len =" in c                             # variable-length wire header
    assert "out_len < 0 || out_len > len" in c             # fail-closed clamp
    assert "int main(" in c


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_gauss_c_fail_soft_matches_python(tmp_path):
    # The difftest holdout is well-conditioned ONLY (its oracle np.linalg.solve cannot
    # handle singular/malformed rows), so the C fail-soft path is verified HERE directly
    # against Python — no oracle. C must return empty (out_len 0) EXACTLY where Python
    # returns [], and a real solution where Python solves: this pins both the variable-
    # length KIND_MAP wire (including the empty-array case) and the fail-soft branch.
    op = algo.ALGO_BY_NAME["gauss_solve"]
    cases = [
        _pack_system([[1.0, 1.0], [1.0, -1.0]], [3.0, 1.0]),   # valid -> [2, 1]
        _pack_system([[1.0, 1.0], [1.0, 1.0]], [2.0, 2.0]),    # singular -> []
        [2.0, 1.0, 2.0],                                       # malformed (too short) -> []
        [0.0],                                                 # n < 1 -> []
        [],                                                    # empty -> []
    ]
    cc = algo_difftest.find_c_compiler()
    res = algo_difftest.run_c_backend(op, cases, tmp_path, cc)
    assert res["status"] == "ran", res
    py = [algo.py_fn("gauss_solve")([float(x) for x in a]) for a in cases]
    assert res["outputs"] == py                             # C == Python on every case
    assert res["outputs"][1] == [] and res["outputs"][2] == []   # fail-soft genuinely exercised


@pytest.mark.parametrize("name", _NUMERIC)
def test_numeric_difftest_python_half(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc=None)
    assert res["python_pass"] is True                        # within the op's tolerance
    assert res["python_max_abs_diff"] <= algo.ALGO_BY_NAME[name].tol


@pytest.mark.skipif(not algo_difftest.find_c_compiler(), reason="no C toolchain")
@pytest.mark.parametrize("name", _NUMERIC)
def test_numeric_c_is_bit_identical(name, tmp_path):
    # same algorithm + -ffp-contract=off -> C matches Python to the bit
    res = algo_difftest.difftest(name, tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


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


def test_mergesort_is_stable_observable_via_signed_zero():
    # Stability of a bare-float sort is only OBSERVABLE through equal-but-bit-
    # distinguishable elements: +0.0 and -0.0 compare equal (<=) yet have different
    # bit patterns. A stable merge keeps their INPUT order; an unstable `<` merge
    # would reorder them. This pins stability where the old value-only test could not.
    import math
    run = algo.py_fn("mergesort")
    out = run([0.0, -0.0, 0.0, -0.0])              # all equal under <=, order must survive
    signs = [math.copysign(1.0, x) for x in out]
    assert signs == [1.0, -1.0, 1.0, -1.0]         # preserved -> stable; would fail if unstable
    # and an UNstable merge is genuinely detected here (guards against a `<=`->`<` regression)
    unstable_src = algo._PY_MERGESORT.replace("if a[i] <= a[j]:", "if a[i] < a[j]:")
    ns: dict = {}
    exec(compile(unstable_src, "<unstable>", "exec"), ns)  # noqa: S102 - test fixture
    bad = [math.copysign(1.0, x) for x in ns["run"]([0.0, -0.0, 0.0, -0.0])]
    assert bad != [1.0, -1.0, 1.0, -1.0]           # the mutation IS observable


@pytest.mark.parametrize("name", _ALL)
def test_reference_does_not_mutate_input(name):
    # the "in place on a copy" contract: run(a) must not mutate the caller's list.
    a = [3.0, 1.0, 2.0, 1.0, 5.0]
    snapshot = list(a)
    algo.py_fn(name)(a)
    assert a == snapshot


def test_quicksort_handles_duplicates_in_reasonable_time():
    # 3-way partition keeps all-equal / few-distinct inputs at O(n log n). A Lomuto
    # regression would be ~O(n^2): 20000 all-equal elements would take seconds.
    import time
    big_equal = [1.0] * 20000
    t = time.perf_counter()
    out = algo.run_algo("quicksort", big_equal)
    dt = time.perf_counter() - t
    assert out == big_equal
    assert dt < 2.0, f"quicksort on 20000 equal keys took {dt:.2f}s (expected O(n log n))"
    binary = [float(i % 2) for i in range(20000)]  # a flattened binary mask
    t = time.perf_counter()
    assert algo.run_algo("quicksort", binary) == sorted(binary)
    assert time.perf_counter() - t < 2.0


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
    assert cb["c_vs_python_bit_identical"] is True          # true bit-for-bit
    assert cb["c_vs_python_max_abs_diff"] == 0.0
    assert cb["pass"] is True and res["passed"] is True
    assert res["c_verified"] is True                        # actually compiled + compared


def test_diff_helpers_fail_closed_on_nonfinite():
    inf, nan = float("inf"), float("nan")
    # a NaN/inf difference must never silently fold to 0.0 (the old fail-open)
    assert algo_difftest._diff01(1.0, nan) == inf
    assert algo_difftest._diff01(1.0, inf) == inf
    assert algo_difftest._max_diff_sort([[1.0, 2.0]], [[1.0, nan]]) == inf
    assert algo_difftest._max_diff_scalar([1.0], [nan]) == inf
    # structural mismatch (wrong length / count) is also inf -> never tol-gated
    assert algo_difftest._max_diff_sort([[1.0, 2.0]], [[1.0]]) == inf
    assert algo_difftest._max_diff_sort([[1.0]], [[1.0], [2.0]]) == inf


def test_bit_check_catches_what_absdiff_misses():
    # the bit comparison catches signed-zero and NaN divergences that an abs-diff
    # of 0.0 would certify as "equal" — exactly the fail-open the review found.
    assert algo_difftest._max_diff_sort([[0.0]], [[-0.0]]) == 0.0        # abs-diff: blind
    assert algo_difftest._bits_equal_sort([[0.0]], [[-0.0]]) is False    # bits: caught
    assert algo_difftest._bits_equal_scalar([1.0], [float("nan")]) is False
    assert algo_difftest._bits_equal_sort([[1.0, 2.0]], [[1.0, float("nan")]]) is False
    assert algo_difftest._bits_equal_sort([[1.0, 2.0]], [[1.0, 2.0]]) is True   # match


def test_tol_inf_cannot_pass_nonfinite(tmp_path, monkeypatch):
    # --tol inf must NOT rescue a non-finite / structurally-broken reference.
    monkeypatch.setattr(algo, "py_fn", lambda name: (lambda a: [float("nan")] * len(a)))
    res = algo_difftest.difftest("quicksort", tmp_path, tol=float("inf"), cc=None)
    assert res["python_pass"] is False and res["passed"] is False


def test_difftest_reports_c_verified(tmp_path):
    skipped = algo_difftest.difftest("quicksort", tmp_path, cc=None)
    assert skipped["c_verified"] is False                    # honest: pass but UNVERIFIED
    if _HAS_CC:
        assert algo_difftest.difftest("quicksort", tmp_path, cc="auto")["c_verified"] is True


_HAS_ZIG = (algo_difftest.find_c_compiler() is not None
            and "ziglang" in " ".join(algo_difftest.find_c_compiler() or []))


@pytest.mark.skipif(not _HAS_ZIG, reason="needs ziglang cc for cross-target compile")
@pytest.mark.parametrize("name", _ALL)
def test_emitted_c_cross_compiles_for_macos(name, tmp_path):
    # regression guard for the BSD <stdlib.h> name clash: heapsort()/mergesort()
    # are declared by BSD libc, so the emitted C must not export those plain names.
    import subprocess
    c_path = tmp_path / f"gen_{name}.c"
    c_path.write_text(algo_codegen.emit_c(algo.ALGO_BY_NAME[name]), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "ziglang", "cc", "-target", "x86_64-macos",
                        "-O2", "-std=c99", "-c", str(c_path), "-o", str(tmp_path / "o.o")],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr[-400:]


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_difftest_catches_semantically_wrong_c(tmp_path, monkeypatch):
    # a C backend that COMPILES but does not actually sort (no-op) must FAIL the
    # gate — proving the bit-for-bit comparison is a meaningful check, not a
    # rubber stamp that any compilable C passes.
    op = algo.ALGO_BY_NAME["quicksort"]
    broken = ("#include <stdio.h>\n#include <stdlib.h>\n#include <stdint.h>\n"
              "void quicksort(double* a, int n) { (void)a; (void)n; }\n"   # no-op: wrong
              + algo_codegen._driver_c(op))
    monkeypatch.setattr(algo_codegen, "emit_c", lambda o: broken)
    res = algo_difftest.difftest("quicksort", tmp_path, cc="auto")
    assert res["python_pass"] is True                       # Python reference still correct
    assert res["c_backend"]["status"] == "ran"
    assert res["c_backend"]["c_vs_python_bit_identical"] is False
    assert res["c_backend"]["c_vs_python_max_abs_diff"] > 0.0
    assert res["passed"] is False                           # the wrong C fails the gate


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
    assert set(fullseye.algo_ops()) == set(_ALL_OPS)
    assert fullseye.run_algo("quicksort", [3, 1, 2]) == [1.0, 2.0, 3.0]
    assert fullseye.run_algo("seq_max", [3, 1, 2]) == 3.0
    assert "void heapsort_asc" in fullseye.algo_to_c("heapsort")   # BSD-safe C symbol
    assert "def run(" in fullseye.algo_to_python("mergesort")


# --------------------------------------------------------------------------- #
# CLI subcommand (imgevolve.py algo ...)
# --------------------------------------------------------------------------- #
def test_cli_algo_subcommand(capsys):
    import types

    import imgevolve
    imgevolve.cmd_algo(types.SimpleNamespace(action="list", op=None))
    assert "quicksort" in capsys.readouterr().out
    imgevolve.cmd_algo(types.SimpleNamespace(action="run", op="quicksort", seq="3,1,2"))
    assert "[1.0, 2.0, 3.0]" in capsys.readouterr().out
    imgevolve.cmd_algo(types.SimpleNamespace(action="emit-c", op="heapsort"))
    assert "void heapsort_asc" in capsys.readouterr().out


def test_cli_algo_difftest_action(tmp_path, capsys):
    import types

    import imgevolve
    rc = imgevolve.cmd_algo(types.SimpleNamespace(
        action="difftest", op="all", workdir=str(tmp_path), no_c=(not _HAS_CC)))
    out = capsys.readouterr().out
    assert rc == 0 and "passed=True" in out
    for name in _ALL_OPS:
        assert name in out


# --------------------------------------------------------------------------- #
# algo_gate — work-graph gated-stage runner (marker-only-on-pass, exit=verdict)
# --------------------------------------------------------------------------- #
def _load_algo_gate():
    import importlib.util
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "tools" / "algo_gate.py"
    spec = importlib.util.spec_from_file_location("algo_gate", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_algo_gate_passes_and_writes_marker(tmp_path):
    gate = _load_algo_gate()
    # use_c=False keeps this toolchain-independent: gauss's Python half is within tol,
    # the C half skips (neutral) -> passed True -> marker written.
    res = gate.gate("gauss_solve", tmp_path, use_c=False)
    assert res["passed"] is True
    marker = tmp_path / "gate_ok.json"
    assert marker.is_file()
    import json
    m = json.loads(marker.read_text())
    assert m["op"] == "gauss_solve" and m["passed"] is True


def test_algo_gate_fails_closed_writes_no_marker(tmp_path, monkeypatch):
    gate = _load_algo_gate()
    # a FAILED gate must leave NO marker so the work-graph node fails closed (the
    # CommandWorker's `produces` points at the marker, so its absence == node failure).
    monkeypatch.setattr(algo_difftest, "difftest", lambda *a, **k: {
        "passed": False, "python_max_abs_diff": float("inf"),
        "c_backend": None, "c_verified": False, "compiler": "none"})
    res = gate.gate("gauss_solve", tmp_path, use_c=False)
    assert res["passed"] is False
    assert not (tmp_path / "gate_ok.json").exists()


def test_algo_gate_removes_stale_marker_on_failure(tmp_path, monkeypatch):
    gate = _load_algo_gate()
    stale = tmp_path / "gate_ok.json"
    stale.write_text('{"op": "gauss_solve", "passed": true}', encoding="utf-8")  # prior pass
    monkeypatch.setattr(algo_difftest, "difftest", lambda *a, **k: {
        "passed": False, "python_max_abs_diff": float("inf"),
        "c_backend": None, "c_verified": False, "compiler": "none"})
    gate.gate("gauss_solve", tmp_path, use_c=False)
    assert not stale.exists()                       # stale pass never survives a later failure


def test_algo_gate_unknown_op_fail_closed(tmp_path):
    gate = _load_algo_gate()
    with pytest.raises(SystemExit):
        gate.gate("nope", tmp_path, use_c=False)
