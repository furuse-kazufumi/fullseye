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
# P3: string ops (code-point sequences). strfind is a variable-length KIND_MAP (match
# positions); edit_distance/lcs_length fold to an exact integer (KIND_REDUCE, tol 0).
_STRING = ["strfind", "edit_distance", "lcs_length"]
# P4: graph ops (packed [n, m, (u,v,w)*m]). graph_dijkstra is a KIND_MAP distance vector;
# graph_components/graph_mst_weight are KIND_REDUCE. Independent oracle = scipy.csgraph.
_GRAPH = ["graph_components", "graph_mst_weight", "graph_dijkstra"]
# P5: number theory / compression / hashing (integers carried as float64, exact). gcd_seq /
# pow_mod / crc32 are KIND_REDUCE; sieve_primes / rle_encode are KIND_MAP (output can exceed
# the input). All exact (tol 0). Independent oracles = math.gcd / trial division / builtin pow
# / zlib.crc32 / itertools.groupby.
_NUMTHEORY = ["gcd_seq", "sieve_primes", "pow_mod"]
_HASH = ["crc32"]
_COMPRESS = ["rle_encode"]
_P5 = _NUMTHEORY + _HASH + _COMPRESS
# P6: computational geometry (integer coords, exact). polygon_area2 / point_in_polygon are
# KIND_REDUCE; convex_hull is a KIND_MAP. Independent oracles = numpy shoelace / the winding-number
# algorithm / scipy.spatial.ConvexHull (vertex-set comparison).
_GEOMETRY = ["polygon_area2", "point_in_polygon", "convex_hull", "segments_intersect"]
# P8: search / selection (comparison-based, exact). binary_search / kth_smallest are KIND_REDUCE.
# Independent oracles = bisect_left + presence check / full-sort-then-index.
_SEARCH = ["binary_search", "kth_smallest"]
# P9: statistics (comparison-based, exact). count_distinct / mode_value are KIND_REDUCE.
# Independent oracles = len(set(...)) / collections.Counter.
_STAT = ["count_distinct", "mode_value"]
# P10: number theory part 2 (category "numtheory", but appended at the END of the registry).
# is_prime = deterministic Miller-Rabin; modular_inverse = extended Euclid. KIND_REDUCE, exact.
_NUMTHEORY2 = ["is_prime", "modular_inverse"]
# P11: bit manipulation (non-negative integers in [0, 2^53-1]). xor_reduce / popcount_total are
# KIND_REDUCE. Independent oracles = functools.reduce(xor) / sum(bin(x).count('1')).
_BITS = ["xor_reduce", "popcount_total"]
# P12: extended Euclidean algorithm (Bezout coefficients). KIND_MAP: [a, b] -> [g, x, y] (exactly 3
# values, or [] fail-soft). Non-negative integers <= 2^53. Independent oracle = the RECURSIVE extended
# Euclid (_ext_gcd_rec), element-wise (g, x, y). Shares the "numtheory" category with P5 + P10.
_EXTGCD = ["extended_gcd"]
# P13: closest pair of points by divide & conquer. KIND_REDUCE: [x0,y0,x1,y1,...] -> min squared
# distance (exact integer, coords in [-1e5, 1e5]), or -1.0 fail-soft. Independent oracle = brute-force
# O(n^2). Shares the "geometry" category with P6 + P7.
_GEOMETRY2 = ["closest_pair"]
# P14: Huffman optimal-prefix-code cost. KIND_REDUCE: [f0,f1,...] -> min total weighted code length
# (tie-invariant exact integer), or -1.0 fail-soft. Independent oracle = a heapq min-heap Huffman merge.
# Shares the "compress" category with P5 (rle_encode).
_COMPRESS2 = ["huffman_cost"]
# P15: longest strictly-increasing subsequence length by patience sorting. KIND_REDUCE: arbitrary
# NaN-free doubles -> LIS length (exact integer), or -1.0 on a NaN. Independent oracle = O(n^2) DP.
# Shares the "search" category with P8 (binary_search, kth_smallest).
_SEARCH2 = ["lis_length"]
# P16: inversion count by a counting merge sort. KIND_REDUCE: arbitrary NaN-free doubles -> the number
# of inversions (exact integer), or -1.0 on a NaN. Independent oracle = O(n^2) brute count. Shares the
# "stat" category with P9 (count_distinct, mode_value).
_STAT2 = ["count_inversions"]
# P17: maximum subarray sum by Kadane's O(n) reset scan. KIND_REDUCE: integer-valued doubles ->
# max contiguous subarray sum with the EMPTY subarray allowed (so the result is >= 0, exact
# integer), or -1.0 fail-soft on a NaN / inf / non-integer / overflow. Independent oracle = the
# O(n^2) brute over all subarrays. Shares the "search" category with P8 + P15.
_SEARCH3 = ["max_subarray"]
# P18: longest palindromic contiguous subarray length by Manacher's O(n) algorithm. KIND_REDUCE:
# arbitrary NaN-free doubles -> the palindrome length (exact integer), or -1.0 on a NaN. Independent
# oracle = O(n^2) expand-around-center. Shares the "search" category with P8 + P15 + P17.
_SEARCH4 = ["longest_palindrome"]
_ALL = _SORTS + _REDUCES                            # the EXACT ops (bit/oracle == 0)
# every registered op, in registry order
_ALL_OPS = (_ALL + _NUMERIC + _STRING + _GRAPH + _P5 + _GEOMETRY + _SEARCH + _STAT
            + _NUMTHEORY2 + _BITS + _EXTGCD + _GEOMETRY2 + _COMPRESS2 + _SEARCH2 + _STAT2 + _SEARCH3
            + _SEARCH4)

_HAS_CC = algo_difftest.find_c_compiler() is not None   # gate C-backend tests on a toolchain


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
    assert set(cats["string"]) == set(_STRING)
    assert set(cats["graph"]) == set(_GRAPH)
    assert set(cats["numtheory"]) == set(_NUMTHEORY) | set(_NUMTHEORY2) | set(_EXTGCD)  # P5 + P10 + P12
    assert set(cats["hash"]) == set(_HASH)
    assert set(cats["compress"]) == set(_COMPRESS) | set(_COMPRESS2)   # P5 + P14
    assert set(cats["geometry"]) == set(_GEOMETRY) | set(_GEOMETRY2)   # P6/P7 + P13
    assert set(cats["search"]) == set(_SEARCH) | set(_SEARCH2) | set(_SEARCH3)   # P8 + P15 + P17
    assert set(cats["stat"]) == set(_STAT) | set(_STAT2)   # P9 + P16


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
    assert "int cap =" in c and "int out_len =" in c        # two-phase: size probe + fill
    assert "out_len < 0 || out_len > cap" in c              # fail-closed clamp to the probed cap
    assert "(double*)0" in c                                # size-probe call (out = NULL)
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


# --------------------------------------------------------------------------- #
# P3 string ops — strfind (KMP, KIND_MAP), edit_distance / lcs_length (KIND_REDUCE)
# --------------------------------------------------------------------------- #
def _find_pack(pat: str, text: str):
    return [float(len(pat))] + algo.text_to_seq(pat) + algo.text_to_seq(text)


def _pair_pack(a: str, b: str):
    return [float(len(a))] + algo.text_to_seq(a) + algo.text_to_seq(b)


def _naive_find(pat: str, text: str):
    m = len(pat)
    return [float(i) for i in range(len(text) - m + 1) if text[i:i + m] == pat]


def test_string_ops_are_registered_kinds():
    assert algo.ALGO_BY_NAME["strfind"].kind == algo.KIND_MAP        # variable-length positions
    assert algo.ALGO_BY_NAME["edit_distance"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["lcs_length"].kind == algo.KIND_REDUCE
    assert algo.text_to_seq("AB") == [65.0, 66.0]
    assert algo.seq_to_text([65.0, 66.0]) == "AB"


def test_strfind_known_answers():
    assert algo.run_algo("strfind", _find_pack("A", "AAA")) == [0.0, 1.0, 2.0]   # overlap
    assert algo.run_algo("strfind", _find_pack("AB", "ABAB")) == [0.0, 2.0]
    assert algo.run_algo("strfind", _find_pack("ABC", "xxABCyyABC")) == [2.0, 7.0]
    assert algo.run_algo("strfind", _find_pack("ABC", "DEF")) == []              # no match
    assert algo.run_algo("strfind", _find_pack("ABCD", "ABCD")) == [0.0]         # whole text


def test_strfind_variable_length_output():
    seq = _find_pack("A", "AAAAA")                          # in = 1+1+5 = 7, out = 5 matches
    out = algo.run_algo("strfind", seq)
    assert len(seq) == 7 and out == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_strfind_fail_soft():
    assert algo.run_algo("strfind", []) == []
    assert algo.run_algo("strfind", [0.0, 65.0]) == []       # empty pattern (m < 1)
    assert algo.run_algo("strfind", _find_pack("ABCD", "AB")) == []   # pattern longer than text


def test_strfind_matches_naive_over_random():
    rng = random.Random(4242)
    for _ in range(400):
        alpha = "ABCD"[:rng.randint(2, 4)]
        m = rng.randint(1, 5)
        pat = "".join(rng.choice(alpha) for _ in range(m))
        text = "".join(rng.choice(alpha) for _ in range(rng.randint(0, 30)))
        got = algo.run_algo("strfind", _find_pack(pat, text))
        assert got == _naive_find(pat, text)


def test_edit_distance_known_and_random():
    assert algo.run_algo("edit_distance", _pair_pack("", "")) == 0.0
    assert algo.run_algo("edit_distance", _pair_pack("ABC", "ABC")) == 0.0
    assert algo.run_algo("edit_distance", _pair_pack("ABC", "")) == 3.0
    assert algo.run_algo("edit_distance", _pair_pack("kitten", "sitting")) == 3.0   # classic
    assert algo.run_algo("edit_distance", _pair_pack("flaw", "lawn")) == 2.0
    rng = random.Random(99)
    for _ in range(300):
        alpha = "AB"
        a = "".join(rng.choice(alpha) for _ in range(rng.randint(0, 8)))
        b = "".join(rng.choice(alpha) for _ in range(rng.randint(0, 8)))
        got = algo.run_algo("edit_distance", _pair_pack(a, b))
        assert got == algo_difftest._lev_recursive(tuple(algo.text_to_seq(a)),
                                                    tuple(algo.text_to_seq(b)))


def test_lcs_length_known_and_random():
    assert algo.run_algo("lcs_length", _pair_pack("ABCBDAB", "BDCAB")) == 4.0   # classic (BCAB/BDAB)
    assert algo.run_algo("lcs_length", _pair_pack("ABC", "DEF")) == 0.0
    assert algo.run_algo("lcs_length", _pair_pack("ABC", "ABC")) == 3.0
    rng = random.Random(101)
    for _ in range(300):
        alpha = "ABC"
        a = "".join(rng.choice(alpha) for _ in range(rng.randint(0, 8)))
        b = "".join(rng.choice(alpha) for _ in range(rng.randint(0, 8)))
        got = algo.run_algo("lcs_length", _pair_pack(a, b))
        assert got == algo_difftest._lcs_recursive(tuple(algo.text_to_seq(a)),
                                                    tuple(algo.text_to_seq(b)))


def test_string_reductions_fail_soft():
    assert algo.run_algo("edit_distance", []) == 0.0
    assert algo.run_algo("lcs_length", []) == 0.0
    assert algo.run_algo("edit_distance", [5.0, 65.0]) == 0.0    # na=5 but too few values
    assert algo.run_algo("lcs_length", [5.0, 65.0]) == 0.0


@pytest.mark.parametrize("name", _STRING)
def test_string_reference_does_not_mutate_input(name):
    a = _pair_pack("ABAB", "BABA") if name != "strfind" else _find_pack("AB", "ABAB")
    snap = list(a)
    algo.py_fn(name)(a)
    assert a == snap


@pytest.mark.parametrize("name", _STRING)
def test_string_difftest_python_half_is_exact(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0                 # positions/distances are exact integers


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", _STRING)
def test_string_c_is_bit_identical(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P4 graph ops — components / mst_weight (KIND_REDUCE), dijkstra (KIND_MAP)
# --------------------------------------------------------------------------- #
def test_graph_ops_are_registered_kinds():
    assert algo.ALGO_BY_NAME["graph_components"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["graph_mst_weight"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["graph_dijkstra"].kind == algo.KIND_MAP
    assert set(algo.algo_categories()["graph"]) == {"graph_components", "graph_mst_weight", "graph_dijkstra"}


def test_graph_components_known():
    assert algo.run_algo("graph_components", [1.0, 0.0]) == 1.0            # single node
    assert algo.run_algo("graph_components", [3.0, 0.0]) == 3.0            # 3 isolated
    # path 0-1-2 -> 1 component; adding node 3 isolated -> 2
    assert algo.run_algo("graph_components", [3.0, 2.0, 0.0, 1.0, 1.0, 1.0, 2.0, 1.0]) == 1.0
    assert algo.run_algo("graph_components", [4.0, 2.0, 0.0, 1.0, 1.0, 1.0, 2.0, 1.0]) == 2.0


def test_graph_mst_weight_known():
    # triangle with weights 1,2,3 -> MST picks 1+2 = 3
    assert algo.run_algo("graph_mst_weight",
                         [3.0, 3.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0, 0.0, 2.0, 3.0]) == 3.0
    assert algo.run_algo("graph_mst_weight", [3.0, 0.0]) == 0.0            # forest of isolated -> 0


def test_graph_dijkstra_known():
    # path 0-1-2 with weights 5, 3 from src 0 -> [0, 5, 8]
    assert algo.run_algo("graph_dijkstra",
                         [3.0, 2.0, 0.0, 0.0, 1.0, 5.0, 1.0, 2.0, 3.0]) == [0.0, 5.0, 8.0]
    # a disconnected node is unreachable -> -1.0
    assert algo.run_algo("graph_dijkstra",
                         [3.0, 1.0, 0.0, 0.0, 1.0, 5.0]) == [0.0, 5.0, -1.0]


def test_graph_components_matches_scipy_over_random():
    csr = pytest.importorskip("scipy.sparse").csr_matrix
    cc = pytest.importorskip("scipy.sparse.csgraph").connected_components
    rng = random.Random(31)
    for _ in range(150):
        n = rng.randint(1, 9)
        m = rng.randint(0, 14)
        edges = []
        for _ in range(m):
            edges += [float(rng.randint(0, n - 1)), float(rng.randint(0, n - 1)), 1.0]
        got = algo.run_algo("graph_components", [float(n), float(m)] + edges)
        rows = [int(edges[3 * k]) for k in range(m)] + [int(edges[3 * k + 1]) for k in range(m)]
        cols = [int(edges[3 * k + 1]) for k in range(m)] + [int(edges[3 * k]) for k in range(m)]
        mtx = csr((([1.0] * len(rows)), (rows, cols)), shape=(n, n)) if rows else csr((n, n))
        assert got == float(cc(mtx, directed=False)[0])


def test_graph_dijkstra_matches_scipy_over_random():
    import numpy as np
    csr = pytest.importorskip("scipy.sparse").csr_matrix
    dij = pytest.importorskip("scipy.sparse.csgraph").dijkstra
    rng = random.Random(77)
    for _ in range(150):
        n = rng.randint(1, 8)
        used = {(i, i + 1) for i in range(n - 1)}
        edges = []
        for i in range(n - 1):
            edges += [float(i), float(i + 1), float(rng.randint(1, 9))]
        spare = [(u, v) for u in range(n) for v in range(u + 1, n) if (u, v) not in used]
        rng.shuffle(spare)
        for (u, v) in spare[:rng.randint(0, min(5, len(spare)))]:
            edges += [float(u), float(v), float(rng.randint(1, 9))]
        m = len(edges) // 3
        src = rng.randint(0, n - 1)
        got = algo.run_algo("graph_dijkstra", [float(n), float(m), float(src)] + edges)
        rows = [int(edges[3 * k]) for k in range(m)] + [int(edges[3 * k + 1]) for k in range(m)]
        cols = [int(edges[3 * k + 1]) for k in range(m)] + [int(edges[3 * k]) for k in range(m)]
        data = [edges[3 * k + 2] for k in range(m)] * 2
        mtx = csr((data, (rows, cols)), shape=(n, n)) if rows else csr((n, n))
        ref = dij(mtx, directed=False, indices=src)
        assert len(got) == n
        for i in range(n):
            if np.isfinite(ref[i]):
                assert abs(got[i] - float(ref[i])) < 1e-9
            else:
                assert got[i] == -1.0


def test_graph_fail_soft():
    assert algo.run_algo("graph_components", [0.0]) == 0.0                 # malformed
    assert algo.run_algo("graph_components", [2.0, 1.0, 5.0, 0.0, 1.0]) == 0.0   # edge u=5 out of range
    assert algo.run_algo("graph_mst_weight", [2.0, 1.0, 9.0, 0.0, 1.0]) == 0.0   # bad endpoint
    assert algo.run_algo("graph_dijkstra", []) == []
    assert algo.run_algo("graph_dijkstra", [3.0, 0.0, 9.0]) == []          # src out of range
    assert algo.run_algo("graph_dijkstra", [2.0, 1.0, 0.0, 0.0, 1.0, -3.0]) == []   # negative weight
    # fractional node-count header: src must be bounded by int(n), not raw n_d (else src==n
    # slips past `sd < n_d` and writes out[n] OOB). n_d=3.5 -> n=3, src_d=3.0 must be rejected.
    assert algo.run_algo("graph_dijkstra", [3.5, 0.0, 3.0]) == []
    assert algo.run_algo("graph_dijkstra", [3.5, 0.0, 3.4]) == []


@pytest.mark.parametrize("name", _GRAPH)
def test_graph_difftest_python_half(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] <= algo.ALGO_BY_NAME[name].tol


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", _GRAPH)
def test_graph_c_is_bit_identical(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_graph_dijkstra_c_sparse_output_larger_than_input(tmp_path):
    # A SPARSE graph makes the KIND_MAP output (n distances) LARGER than the input length
    # (3 + 3m): n=5, m=0 -> input len 3, output len 5. The two-phase driver (size-probe
    # out=NULL -> n, then allocate n) must handle this WITHOUT a heap overflow. Verify the
    # emitted C == Python and returns the -1.0 sentinels for the isolated nodes.
    op = algo.ALGO_BY_NAME["graph_dijkstra"]
    cases = [
        [5.0, 0.0, 0.0],                                # 5 nodes, no edges: [0, -1, -1, -1, -1]
        [4.0, 1.0, 2.0, 2.0, 3.0, 7.0],                 # src=2, edge 2-3: node 2,3 reached, 0,1 not
        [3.5, 0.0, 3.0],                                # fractional n_d, src==int(n): fail-soft, no OOB
    ]
    cc = algo_difftest.find_c_compiler()
    res = algo_difftest.run_c_backend(op, cases, tmp_path, cc)
    assert res["status"] == "ran", res                  # C did NOT crash (no heap OOB write)
    py = [algo.py_fn("graph_dijkstra")([float(x) for x in c]) for c in cases]
    assert res["outputs"] == py
    assert res["outputs"][0] == [0.0, -1.0, -1.0, -1.0, -1.0]
    assert res["outputs"][2] == []                      # fractional-n_d src rejected -> empty


def test_string_ops_fail_soft_on_bad_header_no_crash():
    # regression for the P3 review: int(a[0]) once ran BEFORE the range check, so a
    # fractional-negative header slipped through (int(-0.5)==0) and a NaN header crashed
    # (int(nan) -> ValueError). The raw-value guard now fail-softs on both, in Python.
    nan = float("nan")
    assert algo.run_algo("edit_distance", [-0.5, 65.0, 66.0]) == 0.0     # was int(-0.5)=0 -> 2.0
    assert algo.run_algo("edit_distance", [nan, 65.0, 66.0]) == 0.0      # was a ValueError crash
    assert algo.run_algo("edit_distance", [3.0e9, 65.0, 66.0]) == 0.0    # oversized
    assert algo.run_algo("lcs_length", [-0.5, 65.0, 66.0]) == 0.0
    assert algo.run_algo("lcs_length", [nan, 65.0, 66.0]) == 0.0
    assert algo.run_algo("strfind", [-0.5, 65.0, 65.0]) == []
    assert algo.run_algo("strfind", [nan, 65.0, 65.0]) == []             # was a ValueError crash
    assert algo.run_algo("strfind", [0.5, 65.0, 65.0]) == []             # 0 < m < 1


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", _STRING)
def test_string_c_python_parity_on_bad_headers(name, tmp_path):
    # The oracle-checked holdout uses only VALID headers (the recursive oracle would
    # compute a different value on a truncated-negative header, exactly the bug this pins),
    # so the raw-value guard boundary (fractional / negative / NaN / oversized a[0]) is
    # verified HERE directly C-vs-Python — proving Python now fail-softs identically to C.
    nan = float("nan")
    if name == "strfind":
        cases = [
            [1.0, 65.0, 65.0, 65.0],        # valid control -> [0, 1]
            [-0.5, 65.0, 65.0],             # fractional-negative -> []
            [nan, 65.0, 65.0],              # NaN -> [] (was a Python crash)
            [0.5, 65.0, 65.0],              # 0 < m < 1 -> []
            [3.0e9, 65.0, 65.0],            # oversized -> []
        ]
    else:
        cases = [
            [1.0, 65.0, 66.0],              # valid control (edit 1 / lcs 0)
            [-0.5, 65.0, 66.0],             # fractional-negative -> 0.0 (was Py 2.0 vs C 0.0)
            [nan, 65.0, 66.0],              # NaN -> 0.0 (was a Python crash)
            [3.0e9, 65.0, 66.0],            # oversized -> 0.0
        ]
    op = algo.ALGO_BY_NAME[name]
    cc = algo_difftest.find_c_compiler()
    res = algo_difftest.run_c_backend(op, cases, tmp_path, cc)
    assert res["status"] == "ran", res
    py = [algo.py_fn(name)([float(x) for x in c]) for c in cases]
    assert res["outputs"] == py             # C == Python on every header (incl. NaN / fractional)


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
@pytest.mark.parametrize("name", _ALL_OPS)
def test_emitted_c_cross_compiles_for_macos(name, tmp_path):
    # regression guard for the BSD <stdlib.h> name clash: heapsort()/mergesort()
    # are declared by BSD libc, so the emitted C must not export those plain names.
    # Covers every op (incl. numeric / gauss_solve) so no future op regresses portability.
    import subprocess
    c_path = tmp_path / f"gen_{name}.c"
    c_path.write_text(algo_codegen.emit_c(algo.ALGO_BY_NAME[name]), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "ziglang", "cc", "-target", "x86_64-macos",
                        "-O2", "-std=c99", "-c", str(c_path), "-o", str(tmp_path / "o.o")],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr[-400:]


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", ["gcd_seq", "pow_mod", "crc32"])
def test_emitted_c_refuses_finite_math_build(name, tmp_path):
    # -ffast-math / -ffinite-math-only elide the NaN guards (verified: gcd_seq([NaN,6]) -> 2.0
    # instead of the fail-soft 0.0 when built with -ffinite-math-only). The codegen emits an #error
    # so the shipped artifact FAILS TO BUILD under that assumption rather than miscompile silently.
    import subprocess
    c_path = tmp_path / f"gen_{name}.c"
    c_path.write_text(algo_codegen.emit_c(algo.ALGO_BY_NAME[name]), encoding="utf-8")
    o = tmp_path / "o.o"
    bad = subprocess.run([sys.executable, "-m", "ziglang", "cc", "-std=c99", "-ffinite-math-only",
                          "-c", str(c_path), "-o", str(o)], capture_output=True, text=True, check=False)
    assert bad.returncode != 0                                    # the #error fires
    assert "IEEE semantics" in bad.stderr
    ok = subprocess.run([sys.executable, "-m", "ziglang", "cc", "-std=c99", "-ffp-contract=off",
                         "-c", str(c_path), "-o", str(o)], capture_output=True, text=True, check=False)
    assert ok.returncode == 0, ok.stderr[-400:]                  # the gate's own flag builds clean


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
# P5 number theory / compression / hashing (gcd, primes, modular exponentiation,
# CRC-32, run-length encoding). All exact (tol 0); independent oracles.
# --------------------------------------------------------------------------- #
def test_p5_ops_are_registered_kinds():
    assert algo.ALGO_BY_NAME["gcd_seq"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["sieve_primes"].kind == algo.KIND_MAP
    assert algo.ALGO_BY_NAME["pow_mod"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["crc32"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["rle_encode"].kind == algo.KIND_MAP
    assert algo.ALGO_BY_NAME["crc32"].c_func == "crc32_ieee"     # BSD/zlib-safe C symbol
    for name in _P5:                                             # exact: no tolerance
        assert algo.ALGO_BY_NAME[name].tol == 0.0


def test_gcd_seq_known():
    assert algo.run_algo("gcd_seq", []) == 0.0                  # empty
    assert algo.run_algo("gcd_seq", [0.0, 0.0]) == 0.0          # gcd(0,0) = 0
    assert algo.run_algo("gcd_seq", [12.0]) == 12.0
    assert algo.run_algo("gcd_seq", [12.0, 18.0, 24.0]) == 6.0
    assert algo.run_algo("gcd_seq", [17.0, 5.0]) == 1.0         # coprime
    assert algo.run_algo("gcd_seq", [0.0, 7.0]) == 7.0


def test_gcd_seq_matches_math_gcd_over_random():
    rng = random.Random(11)
    for _ in range(300):
        vals = [rng.randint(0, 1_000_000) for _ in range(rng.randint(0, 6))]
        got = algo.run_algo("gcd_seq", [float(v) for v in vals])
        assert got == float(math.gcd(*vals)) if vals else got == 0.0


def test_gcd_seq_fail_soft():
    assert algo.run_algo("gcd_seq", [12.0, -6.0]) == 0.0        # negative -> fail-soft
    assert algo.run_algo("gcd_seq", [12.0, 6.5]) == 0.0         # non-integer -> fail-soft
    assert algo.run_algo("gcd_seq", [float("nan"), 6.0]) == 0.0  # NaN -> fail-soft (no crash)
    assert algo.run_algo("gcd_seq", [1e300]) == 0.0            # > 2^53 -> fail-soft


def test_sieve_primes_known():
    assert algo.run_algo("sieve_primes", [1.0]) == []
    assert algo.run_algo("sieve_primes", [2.0]) == [2.0]
    assert algo.run_algo("sieve_primes", [12.0]) == [2.0, 3.0, 5.0, 7.0, 11.0]
    assert algo.run_algo("sieve_primes", [30.0])[-1] == 29.0


def test_sieve_primes_matches_trial_division_over_random():
    rng = random.Random(23)
    for _ in range(60):
        n = rng.randint(0, 3000)
        got = algo.run_algo("sieve_primes", [float(n)])
        ref = [float(p) for p in range(2, n + 1) if algo_difftest._is_prime_trial(p)]
        assert got == ref


def test_sieve_primes_fail_soft():
    assert algo.run_algo("sieve_primes", []) == []
    assert algo.run_algo("sieve_primes", [0.0]) == []
    assert algo.run_algo("sieve_primes", [1.5]) == []          # 1 < n < 2 -> []
    assert algo.run_algo("sieve_primes", [1e9]) == []          # over the memory cap -> []
    assert algo.run_algo("sieve_primes", [float("nan")]) == []


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_sieve_primes_c_output_larger_than_input(tmp_path):
    # KIND_MAP: input [n] is length 1 but the output (pi(n) primes) is far larger — the
    # two-phase driver (out=NULL -> n/2+1 upper bound, then allocate) must not heap-overflow.
    op = algo.ALGO_BY_NAME["sieve_primes"]
    cases = [[97.0], [100.0], [541.0], [2.0], [1.0]]
    cc = algo_difftest.find_c_compiler()
    res = algo_difftest.run_c_backend(op, cases, tmp_path, cc)
    assert res["status"] == "ran", res
    py = [algo.py_fn("sieve_primes")([float(x) for x in c]) for c in cases]
    assert res["outputs"] == py
    assert res["outputs"][0][-1] == 97.0                       # primes <= 97, last is 97 (prime)
    assert len(res["outputs"][2]) == 100                       # pi(541) = 100 (541 is the 100th prime)


def test_pow_mod_known():
    assert algo.run_algo("pow_mod", [2.0, 10.0, 1000.0]) == 24.0     # 1024 mod 1000
    assert algo.run_algo("pow_mod", [3.0, 0.0, 7.0]) == 1.0         # exp 0 -> 1
    assert algo.run_algo("pow_mod", [0.0, 5.0, 7.0]) == 0.0
    assert algo.run_algo("pow_mod", [5.0, 3.0, 1.0]) == 0.0         # mod 1 -> 0
    # the '1 % mod' special case needs exp == 0 AND mod == 1 TOGETHER (else it is unfalsifiable):
    assert algo.run_algo("pow_mod", [7.0, 0.0, 1.0]) == 0.0        # pow(7,0,1) = 0, not 1
    assert algo.run_algo("pow_mod", [0.0, 0.0, 1.0]) == 0.0
    # at the declared base/exp domain edge (2^53): a C exp->uint32 truncation would give 1.0 here.
    assert algo.run_algo("pow_mod", [2.0, 9007199254740992.0, 7.0]) == float(pow(2, 2**53, 7))
    assert algo.run_algo("pow_mod", [123456.0, 65537.0, 1000000007.0]) == float(
        pow(123456, 65537, 1000000007))


def test_pow_mod_matches_builtin_over_random():
    rng = random.Random(37)
    for _ in range(400):
        # draw base/exp across the FULL declared domain [0, 2^53] (values with float(v)==v), not
        # just small magnitudes, so a C truncation of the upper ~33 bits is exercised (finding 0).
        b = rng.randint(0, 2**53)
        e = rng.randint(0, 2**53)
        m = rng.randint(1, 4294967295)
        assert algo.run_algo("pow_mod", [float(b), float(e), float(m)]) == float(pow(b, e, m))


def test_pow_mod_fail_soft():
    assert algo.run_algo("pow_mod", [2.0, 3.0]) == 0.0             # too short
    assert algo.run_algo("pow_mod", [2.0, 3.0, 0.0]) == 0.0        # mod 0 -> fail-soft
    assert algo.run_algo("pow_mod", [2.0, -1.0, 7.0]) == 0.0       # negative exp -> fail-soft
    assert algo.run_algo("pow_mod", [2.0, 3.0, 5e9]) == 0.0        # mod > 2^32-1 -> fail-soft
    assert algo.run_algo("pow_mod", [2.0, 3.0, float("nan")]) == 0.0
    assert algo.run_algo("pow_mod", [2.5, 3.0, 7.0]) == 0.0        # non-integer base -> fail-soft
    assert algo.run_algo("pow_mod", [2.0, 3.0, 7.5]) == 0.0        # non-integer mod -> fail-soft


def test_crc32_known_matches_zlib():
    import zlib
    assert algo.run_algo("crc32", []) == 0.0                       # crc32(b'') = 0
    for s in (b"", b"a", b"Hello", b"The quick brown fox", bytes(range(256))):
        got = algo.run_algo("crc32", [float(x) for x in s])
        assert got == float(zlib.crc32(s) & 0xFFFFFFFF)


def test_crc32_fail_soft_on_non_byte():
    assert algo.run_algo("crc32", [256.0]) == 0.0                  # > 255 -> fail-soft
    assert algo.run_algo("crc32", [-1.0]) == 0.0
    assert algo.run_algo("crc32", [1.5]) == 0.0                    # non-integer byte
    assert algo.run_algo("crc32", [float("nan")]) == 0.0


def _rle_decode(pairs):
    """Decode [val, count, ...] back to the original sequence (losslessness check)."""
    out = []
    for i in range(0, len(pairs), 2):
        out.extend([pairs[i]] * int(pairs[i + 1]))
    return out


def test_rle_encode_known_and_lossless():
    assert algo.run_algo("rle_encode", []) == []
    assert algo.run_algo("rle_encode", [5.0]) == [5.0, 1.0]
    assert algo.run_algo("rle_encode", [7.0, 7.0, 7.0]) == [7.0, 3.0]
    assert algo.run_algo("rle_encode", [1.0, 2.0, 3.0]) == [1.0, 1.0, 2.0, 1.0, 3.0, 1.0]
    rng = random.Random(41)
    for _ in range(200):
        seq = [float(rng.randint(0, 3)) for _ in range(rng.randint(0, 30))]
        enc = algo.run_algo("rle_encode", seq)
        assert _rle_decode(enc) == seq                            # lossless round-trip
        # matches itertools.groupby (the difftest oracle), independently
        from itertools import groupby
        ref = []
        for v, g in groupby(seq):
            ref += [float(v), float(sum(1 for _ in g))]
        assert enc == ref


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_rle_encode_c_output_larger_than_input(tmp_path):
    # all-distinct input -> output is exactly 2x the input length (2 doubles per run): the
    # size-probe (out=NULL -> 2*n) must allocate enough that the C write does not overflow.
    op = algo.ALGO_BY_NAME["rle_encode"]
    cases = [[1.0, 2.0, 3.0, 4.0, 5.0], [9.0], [], [7.0, 7.0, 8.0]]
    cc = algo_difftest.find_c_compiler()
    res = algo_difftest.run_c_backend(op, cases, tmp_path, cc)
    assert res["status"] == "ran", res
    py = [algo.py_fn("rle_encode")([float(x) for x in c]) for c in cases]
    assert res["outputs"] == py
    assert len(res["outputs"][0]) == 10                           # 5 distinct -> 2*5


def test_rle_encode_signed_zero_collapses_documented():
    # Runs use ==, under which -0.0 == +0.0, so a mixed-sign zero run collapses to the FIRST sign.
    # The tier's equality standard is bit-for-bit, so this is lossy by the tier's own definition —
    # documented as "lossless up to ==-equality (signed zeros collapse; NaN-free)". Pin it as a
    # tested contract so the honest limit is deliberate, not accidental (review finding).
    import math
    enc = algo.run_algo("rle_encode", [-0.0, 0.0])
    assert enc == [-0.0, 2.0]                                     # one run of length 2
    assert math.copysign(1.0, enc[0]) == -1.0                    # surviving value keeps the FIRST sign
    assert math.copysign(1.0, algo.run_algo("rle_encode", [0.0, -0.0])[0]) == 1.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_sieve_primes_c_accepts_at_cap_rejects_over(tmp_path):
    # The 5,000,000 memory cap is never reached by the shared holdout (max n = 2000; the Python
    # reference is slow at the cap), so measure the cap EDGE with the C backend alone: n=5,000,000
    # is accepted (pi = 348513, verified with an independent numpy sieve), n=5,000,001 is rejected.
    op = algo.ALGO_BY_NAME["sieve_primes"]
    cc = algo_difftest.find_c_compiler()
    res = algo_difftest.run_c_backend(op, [[5000000.0], [5000001.0]], tmp_path, cc)
    assert res["status"] == "ran", res
    assert len(res["outputs"][0]) == 348513                      # pi(5_000_000): the cap is ACCEPTED
    assert res["outputs"][1] == []                               # one past the cap -> fail-soft


@pytest.mark.parametrize("name", _P5)
def test_p5_reference_does_not_mutate_input(name):
    # a valid, in-domain input for each op (headers already satisfy the raw-value guards)
    inputs = {
        "gcd_seq": [12.0, 18.0, 24.0], "sieve_primes": [30.0], "pow_mod": [2.0, 10.0, 1000.0],
        "crc32": [72.0, 105.0], "rle_encode": [1.0, 1.0, 2.0],
    }
    arg = list(inputs[name])
    before = list(arg)
    algo.run_algo(name, arg)
    assert arg == before


@pytest.mark.parametrize("name", _P5)
def test_p5_difftest_python_half_is_exact(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0                      # exact vs the independent oracle


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", _P5)
def test_p5_c_is_bit_identical(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_p5_c_python_parity_on_out_of_domain(tmp_path):
    # the oracle-checked holdout uses only IN-DOMAIN inputs, so the raw-value guard boundary
    # (negative / non-integer / NaN / oversized) is verified HERE directly C-vs-Python: Python
    # must fail-soft IDENTICALLY to C (the P3 int()-before-guard bug class, for the P5 ops).
    nan = float("nan")
    per_op = {
        "gcd_seq": [[12.0, 6.0], [12.0, -6.0], [12.0, 6.5], [nan, 6.0], [1e300],
                    [9007199254740992.0, 4503599627370496.0]],       # at 2^53 edge (accepted)
        # incl. short/empty (the C `n < 3` guard is otherwise never exercised = admits an OOB read):
        "pow_mod": [[2.0, 3.0, 7.0], [2.0, 3.0, 0.0], [2.0, -1.0, 7.0], [2.0, 3.0, 5e9],
                    [2.0, 3.0, nan], [2.5, 3.0, 7.0], [7.0, 0.0, 1.0],
                    [], [2.0], [2.0, 3.0], [2.0, 9007199254740992.0, 7.0]],   # short + 2^53 edge
        "crc32": [[65.0, 66.0], [256.0], [-1.0], [1.5], [nan]],
        # incl. empty (the C `n_in < 1` guard) and over-cap (5,000,001):
        "sieve_primes": [[30.0], [1.5], [5000001.0], [1e9], [nan], [-3.0], []],
        "rle_encode": [[1.0, 1.0, 2.0], [7.0], [-0.0, 0.0]],         # signed-zero collapse (finding 2)
    }
    cc = algo_difftest.find_c_compiler()
    for name, cases in per_op.items():
        op = algo.ALGO_BY_NAME[name]
        res = algo_difftest.run_c_backend(op, cases, tmp_path, cc)
        assert res["status"] == "ran", (name, res)
        py = [algo.py_fn(name)([float(x) for x in c]) for c in cases]
        assert res["outputs"] == py, name                        # C fail-softs identically


# --------------------------------------------------------------------------- #
# P6 computational geometry (polygon area, point-in-polygon; integer coords, exact).
# --------------------------------------------------------------------------- #
def test_geometry_ops_registered_kinds():
    assert algo.ALGO_BY_NAME["polygon_area2"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["point_in_polygon"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["convex_hull"].kind == algo.KIND_MAP
    assert algo.ALGO_BY_NAME["segments_intersect"].kind == algo.KIND_REDUCE
    assert set(algo.algo_categories()["geometry"]) == set(_GEOMETRY) | set(_GEOMETRY2)
    for name in _GEOMETRY:
        assert algo.ALGO_BY_NAME[name].tol == 0.0


def test_polygon_area2_known():
    assert algo.run_algo("polygon_area2", [3.0, 0, 0, 4, 0, 0, 3]) == 12.0    # CCW tri -> 2*area
    assert algo.run_algo("polygon_area2", [3.0, 0, 0, 0, 3, 4, 0]) == -12.0   # CW tri (sign flips)
    assert algo.run_algo("polygon_area2", [4.0, 0, 0, 4, 0, 4, 4, 0, 4]) == 32.0   # square
    assert algo.run_algo("polygon_area2", [6.0, 0, 0, 6, 0, 6, 2, 2, 2, 2, 6, 0, 6]) == 40.0  # concave L


def test_polygon_area2_matches_numpy_shoelace_over_random():
    import numpy as np
    rng = random.Random(51)
    for _ in range(200):
        n = rng.randint(3, 10)
        pts = [(rng.randint(-500, 500), rng.randint(-500, 500)) for _ in range(n)]
        got = algo.run_algo("polygon_area2", [float(n)] + [float(c) for p in pts for c in p])
        x = np.array([p[0] for p in pts], float)
        y = np.array([p[1] for p in pts], float)
        assert got == float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def test_polygon_area2_fail_soft():
    assert algo.run_algo("polygon_area2", [2.0, 0, 0, 1, 1]) == 0.0          # n < 3
    assert algo.run_algo("polygon_area2", [3.0, 0, 0, 4, 0, 200000, 3]) == 0.0   # coord out of range
    assert algo.run_algo("polygon_area2", [3.0, 0, 0, 4, 0, 0.5, 3]) == 0.0      # non-integer coord
    assert algo.run_algo("polygon_area2", [3.0, 0, 0, 4, 0]) == 0.0          # truncated


def test_point_in_polygon_known():
    square = [float(v) for v in (0, 0, 6, 0, 6, 6, 0, 6)]
    assert algo.run_algo("point_in_polygon", [3.0, 3.0, 4.0] + square) == 1.0
    assert algo.run_algo("point_in_polygon", [10.0, 3.0, 4.0] + square) == 0.0
    lshape = [float(v) for v in (0, 0, 6, 0, 6, 2, 2, 2, 2, 6, 0, 6)]
    assert algo.run_algo("point_in_polygon", [4.0, 4.0, 6.0] + lshape) == 0.0   # the concave notch
    assert algo.run_algo("point_in_polygon", [1.0, 1.0, 6.0] + lshape) == 1.0


def test_point_in_polygon_matches_matplotlib_over_random():
    # a THIRD independent check (matplotlib Path, beyond the winding-number difftest oracle):
    # convex polygons via scipy hull, integer query points filtered off-boundary.
    path_mod = pytest.importorskip("matplotlib.path")
    hull = pytest.importorskip("scipy.spatial").ConvexHull
    rng = random.Random(63)
    checked = 0
    for _ in range(120):
        pool = list(dict.fromkeys((rng.randint(-30, 30), rng.randint(-30, 30))
                                  for _ in range(rng.randint(6, 12))))
        if len(pool) < 3:
            continue
        try:
            verts = [pool[i] for i in hull(pool).vertices]
        except Exception:  # noqa: BLE001, S112 - degenerate point set is expected; skip
            continue
        if len(verts) < 3:
            continue
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        path = path_mod.Path([(float(x), float(y)) for x, y in verts])
        for _ in range(5):
            px, py = rng.randint(-40, 40), rng.randint(-40, 40)
            if algo_difftest._on_boundary(px, py, xs, ys):
                continue                                        # boundary is implementation-defined
            got = algo.run_algo("point_in_polygon", [float(px), float(py), float(len(verts))]
                                + [float(c) for v in verts for c in v])
            assert got == (1.0 if path.contains_point((px, py)) else 0.0)
            checked += 1
    assert checked > 50                                         # a meaningful number of comparisons


def test_point_in_polygon_fail_soft():
    tri = [float(v) for v in (0, 0, 8, 0, 4, 6)]
    assert algo.run_algo("point_in_polygon", [1.0, 1.0, 2.0, 0, 0, 5, 5]) == 0.0   # n < 3
    assert algo.run_algo("point_in_polygon", [1.5, 1.0, 3.0] + tri) == 0.0          # non-integer point
    assert algo.run_algo("point_in_polygon", [1.0, 1.0, 3.0, 0, 0, 200000, 0, 4, 6]) == 0.0  # range
    assert algo.run_algo("point_in_polygon", [1.0, 1.0, 3.0, 0, 0, 8, 0]) == 0.0    # truncated


def test_convex_hull_known():
    # square: all 4 corners, CCW from lex-min (0,0)
    assert algo.run_algo("convex_hull", [4.0, 0, 0, 4, 0, 4, 4, 0, 4]) == [0, 0, 4, 0, 4, 4, 0, 4]
    # square + a collinear edge midpoint (2,0) + an interior point (2,2): both EXCLUDED
    assert algo.run_algo("convex_hull", [6.0, 0, 0, 2, 0, 4, 0, 4, 4, 0, 4, 2, 2]) == [0, 0, 4, 0, 4, 4, 0, 4]
    # triangle
    assert algo.run_algo("convex_hull", [3.0, 0, 0, 4, 0, 2, 3]) == [0, 0, 4, 0, 2, 3]


def test_convex_hull_matches_scipy_over_random():
    hull_of = pytest.importorskip("scipy.spatial").ConvexHull
    rng = random.Random(71)
    checked = 0
    for _ in range(300):
        n = rng.randint(3, 20)
        pts = [(rng.randint(-40, 40), rng.randint(-40, 40)) for _ in range(n)]
        got = algo.run_algo("convex_hull", [float(n)] + [float(c) for p in pts for c in p])
        got_set = {(int(got[2 * i]), int(got[2 * i + 1])) for i in range(len(got) // 2)}
        uniq = list(set(pts))
        try:
            ref = {tuple(uniq[i]) for i in hull_of(uniq).vertices} if len(uniq) >= 3 else set()
        except Exception:  # noqa: BLE001 - degenerate (collinear) -> []
            ref = set()
        assert got_set == ref and len(got) // 2 == len(ref)     # same vertices, no duplicates
        checked += 1
    assert checked == 300


def test_convex_hull_is_valid_ccw_polygon():
    # independent structural validation (no scipy): the output is a strictly-convex CCW polygon whose
    # vertices are all input points, and every input point is inside or on it.
    rng = random.Random(89)
    for _ in range(100):
        n = rng.randint(5, 25)
        pts = [(rng.randint(-50, 50), rng.randint(-50, 50)) for _ in range(n)]
        got = algo.run_algo("convex_hull", [float(n)] + [float(c) for p in pts for c in p])
        hull = [(int(got[2 * i]), int(got[2 * i + 1])) for i in range(len(got) // 2)]
        if not hull:
            continue
        assert set(hull) <= set(pts)                            # hull vertices are input points
        assert hull[0] == min(hull)                             # starts at the lex-min vertex
        h = len(hull)
        for i in range(h):                                      # every turn is a strict LEFT turn (CCW, convex)
            o, p, q = hull[i], hull[(i + 1) % h], hull[(i + 2) % h]
            assert (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0]) > 0
        for (px, py) in pts:                                    # every input point is inside or on the hull
            for i in range(h):
                o, p = hull[i], hull[(i + 1) % h]
                assert (p[0] - o[0]) * (py - o[1]) - (p[1] - o[1]) * (px - o[0]) >= 0


def test_convex_hull_fail_soft():
    assert algo.run_algo("convex_hull", [3.0, 0, 0, 1, 1, 2, 2]) == []       # collinear -> degenerate
    assert algo.run_algo("convex_hull", [3.0, 5, 5, 5, 5, 5, 5]) == []       # < 3 distinct points
    assert algo.run_algo("convex_hull", [2.0, 0, 0, 1, 1]) == []             # n < 3
    assert algo.run_algo("convex_hull", [3.0, 0, 0, 4, 0, 200000, 3]) == []  # coord out of range
    assert algo.run_algo("convex_hull", [3.0, 0, 0, 4, 0, 0.5, 3]) == []     # non-integer
    assert algo.run_algo("convex_hull", [3.0, 0, 0, 4, 0]) == []             # truncated


def test_segments_intersect_known():
    f = lambda *v: algo.run_algo("segments_intersect", [float(x) for x in v])
    assert f(0, 0, 4, 4, 0, 4, 4, 0) == 1.0        # X crossing
    assert f(0, 0, 4, 0, 0, 1, 4, 1) == 0.0        # parallel, disjoint
    assert f(0, 0, 4, 0, 2, 0, 6, 0) == 1.0        # collinear overlap
    assert f(0, 0, 1, 0, 2, 0, 3, 0) == 0.0        # collinear, disjoint
    assert f(0, 0, 2, 0, 2, 0, 2, 2) == 1.0        # T-junction (endpoint touch)
    assert f(0, 0, 4, 0, 2, 1, 2, 3) == 0.0        # near miss
    assert f(0, 0, 3, 3, 3, 3, 5, 0) == 1.0        # shared endpoint
    # an endpoint strictly INTERIOR to the other segment (no shared endpoint, no proper crossing) —
    # each exercises one of the 4 collinear on-segment special cases (review 2026-08-17):
    assert f(3, 0, 3, 5, 0, 0, 10, 0) == 1.0       # A-endpoint 1 on B interior (d1)
    assert f(3, 5, 3, 0, 0, 0, 10, 0) == 1.0       # A-endpoint 2 on B interior (d2)
    assert f(0, 0, 10, 0, 3, 0, 3, 5) == 1.0       # B-endpoint 1 on A interior (d3)
    assert f(0, 0, 10, 0, 3, 5, 3, 0) == 1.0       # B-endpoint 2 on A interior (d4)


def test_segments_intersect_matches_sympy_over_random():
    geom = pytest.importorskip("sympy.geometry")
    rng = random.Random(97)
    checked = 0
    for _ in range(400):
        p = [rng.randint(-6, 6) for _ in range(8)]
        if (p[0], p[1]) == (p[2], p[3]) or (p[4], p[5]) == (p[6], p[7]):
            continue                                    # skip degenerate (sympy needs real segments)
        got = algo.run_algo("segments_intersect", [float(v) for v in p])
        ref = 1.0 if geom.Segment(geom.Point(p[0], p[1]), geom.Point(p[2], p[3])).intersection(
            geom.Segment(geom.Point(p[4], p[5]), geom.Point(p[6], p[7]))) else 0.0
        assert got == ref, p
        checked += 1
    assert checked > 200


def test_segments_intersect_fail_soft():
    assert algo.run_algo("segments_intersect", [0, 0, 4, 4, 0, 4, 4]) == 0.0        # < 8 values
    assert algo.run_algo("segments_intersect", [0, 0, 4, 4, 0, 4, 200000, 0]) == 0.0  # coord range
    assert algo.run_algo("segments_intersect", [0, 0, 4, 4, 0, 4, 4, 0.5]) == 0.0   # non-integer


@pytest.mark.parametrize("name", _GEOMETRY)
def test_geometry_reference_does_not_mutate_input(name):
    inputs = {"polygon_area2": [4.0, 0, 0, 4, 0, 4, 4, 0, 4],
              "point_in_polygon": [3.0, 3.0, 4.0, 0, 0, 6, 0, 6, 6, 0, 6],
              "convex_hull": [5.0, 0, 0, 4, 0, 4, 4, 0, 4, 2, 2],
              "segments_intersect": [0.0, 0, 4, 4, 0, 4, 4, 0]}
    arg = [float(x) for x in inputs[name]]
    before = list(arg)
    algo.run_algo(name, arg)
    assert arg == before


@pytest.mark.parametrize("name", _GEOMETRY)
def test_geometry_difftest_python_half_is_exact(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", _GEOMETRY)
def test_geometry_c_is_bit_identical(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P8 search / selection (binary_search, kth_smallest; comparison-based, exact).
# --------------------------------------------------------------------------- #
def test_search_ops_registered_kinds():
    assert algo.ALGO_BY_NAME["binary_search"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["kth_smallest"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["max_subarray"].kind == algo.KIND_REDUCE
    assert set(algo.algo_categories()["search"]) == set(_SEARCH) | set(_SEARCH2) | set(_SEARCH3)
    for name in _SEARCH:
        assert algo.ALGO_BY_NAME[name].tol == 0.0


def test_binary_search_known():
    bs = lambda t, *v: algo.run_algo("binary_search", [float(t)] + [float(x) for x in v])
    assert bs(3, 1, 2, 3, 4, 5) == 2.0
    assert bs(2, 1, 2, 2, 2, 3) == 1.0          # FIRST occurrence (lower bound)
    assert bs(1, 1, 2, 3) == 0.0                # first element
    assert bs(3, 1, 2, 3) == 2.0               # last element
    assert bs(9, 1, 2, 3) == -1.0              # absent (above)
    assert bs(0, 1, 2, 3) == -1.0              # absent (below)
    assert algo.run_algo("binary_search", [5.0]) == -1.0        # empty sequence


def test_binary_search_matches_bisect_over_random():
    import bisect
    rng = random.Random(131)
    for _ in range(2000):
        n = rng.randint(0, 40)
        v = sorted(rng.randint(-25, 25) for _ in range(n))
        t = rng.randint(-27, 27)
        got = algo.run_algo("binary_search", [float(t)] + [float(x) for x in v])
        i = bisect.bisect_left(v, t)
        assert got == (float(i) if i < n and v[i] == t else -1.0)


def test_kth_smallest_known():
    ks = lambda k, *v: algo.run_algo("kth_smallest", [float(k)] + [float(x) for x in v])
    assert ks(0, 5, 3, 1, 4, 2) == 1.0         # minimum
    assert ks(2, 5, 3, 1, 4, 2) == 3.0         # median
    assert ks(4, 5, 3, 1, 4, 2) == 5.0         # maximum
    assert ks(1, 7, 7, 7) == 7.0               # all equal


def test_kth_smallest_matches_sorted_over_random():
    rng = random.Random(151)
    for _ in range(2000):
        n = rng.randint(1, 40)
        v = [rng.uniform(-100, 100) for _ in range(n)]
        k = rng.randint(0, n - 1)
        assert algo.run_algo("kth_smallest", [float(k)] + v) == sorted(v)[k]


def test_kth_smallest_fast_on_adversarial_inputs():
    # median-of-three + a 3-way (Dutch-flag) partition keeps quickselect O(n) on sorted, reverse, AND
    # all-equal / few-distinct inputs. A single-pivot Lomuto quickselect is O(n^2) on all-equal (review
    # 2026-08-17), so the all-equal timing is the real guard here.
    import time
    n = 40001
    cases = {
        "sorted": [float(i) for i in range(n)],
        "reverse": [float(n - i) for i in range(n)],
        "all_equal": [7.0] * n,
        "few_distinct": [float(i % 3) for i in range(n)],
    }
    for label, v in cases.items():
        t0 = time.perf_counter()
        algo.run_algo("kth_smallest", [float(n // 2)] + v)
        assert time.perf_counter() - t0 < 2.0, f"{label} took too long (quadratic?)"
    assert algo.run_algo("kth_smallest", [20000.0] + [7.0] * n) == 7.0


def test_kth_smallest_fail_soft():
    assert algo.run_algo("kth_smallest", [9.0, 1, 2, 3]) == 0.0     # k out of range
    assert algo.run_algo("kth_smallest", [1.5, 1, 2, 3]) == 0.0     # non-integer k
    assert algo.run_algo("kth_smallest", [-1.0, 1, 2, 3]) == 0.0    # negative k
    assert algo.run_algo("kth_smallest", [0.0]) == 0.0             # empty sequence


@pytest.mark.parametrize("name", _SEARCH)
def test_search_reference_does_not_mutate_input(name):
    inputs = {"binary_search": [3.0, 1, 2, 3, 4, 5], "kth_smallest": [2.0, 5, 3, 1, 4, 2]}
    arg = [float(x) for x in inputs[name]]
    before = list(arg)
    algo.run_algo(name, arg)
    assert arg == before                        # quickselect works on a COPY, does not reorder the input


@pytest.mark.parametrize("name", _SEARCH)
def test_search_difftest_python_half_is_exact(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", _SEARCH)
def test_search_c_is_bit_identical(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P9 statistics (count_distinct, mode_value; comparison-based, exact).
# --------------------------------------------------------------------------- #
def test_stat_ops_registered_kinds():
    assert algo.ALGO_BY_NAME["count_distinct"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["mode_value"].kind == algo.KIND_REDUCE
    assert set(algo.algo_categories()["stat"]) == set(_STAT) | set(_STAT2)
    for name in _STAT:
        assert algo.ALGO_BY_NAME[name].tol == 0.0


def test_count_distinct_known_and_random():
    assert algo.run_algo("count_distinct", []) == 0.0
    assert algo.run_algo("count_distinct", [3, 3, 3]) == 1.0
    assert algo.run_algo("count_distinct", [1, 2, 3, 4]) == 4.0
    assert algo.run_algo("count_distinct", [0.0, -0.0, 0.0]) == 1.0     # +0/-0 are one value
    rng = random.Random(211)
    for _ in range(2000):
        v = [float(rng.randint(0, 6)) for _ in range(rng.randint(0, 25))]
        assert algo.run_algo("count_distinct", v) == float(len(set(v)))


def test_mode_value_known_and_random():
    from collections import Counter
    assert algo.run_algo("mode_value", [1, 1, 2, 3, 3, 3]) == 3.0
    assert algo.run_algo("mode_value", [2, 2, 1, 1]) == 1.0             # tie -> smallest
    assert algo.run_algo("mode_value", [5]) == 5.0
    rng = random.Random(233)
    for _ in range(2000):
        n = rng.randint(1, 25)
        v = [float(rng.randint(0, 5)) for _ in range(n)]
        counts = Counter(v)
        top = max(counts.values())
        assert algo.run_algo("mode_value", v) == min(x for x, c in counts.items() if c == top)


@pytest.mark.parametrize("name", _STAT)
def test_stat_difftest_python_half_is_exact(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", _STAT)
def test_stat_c_is_bit_identical(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P10 number theory 2 (is_prime deterministic Miller-Rabin, modular_inverse ext. Euclid).
# --------------------------------------------------------------------------- #
def test_p10_ops_registered_kinds():
    assert algo.ALGO_BY_NAME["is_prime"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["modular_inverse"].kind == algo.KIND_REDUCE
    assert {"is_prime", "modular_inverse"} <= set(algo.algo_categories()["numtheory"])
    for name in _NUMTHEORY2:
        assert algo.ALGO_BY_NAME[name].tol == 0.0


def test_is_prime_known():
    ip = lambda n: algo.run_algo("is_prime", [float(n)])
    assert [ip(n) for n in (0, 1, 2, 3, 4, 5, 17)] == [0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0]
    assert ip(561) == 0.0 and ip(1105) == 0.0          # Carmichael numbers (composite; MR must reject)
    assert ip(7919) == 1.0 and ip(4294967291) == 1.0   # large primes
    assert ip(4294967295) == 0.0                       # 2^32-1 = 3*5*17*257*65537


def test_is_prime_matches_sympy_over_random():
    isprime = pytest.importorskip("sympy").isprime
    rng = random.Random(311)
    for n in range(1500):                               # exhaustive small
        assert algo.run_algo("is_prime", [float(n)]) == (1.0 if isprime(n) else 0.0), n
    for _ in range(3000):                               # random incl. near 2^32
        n = rng.randint(0, 4294967295)
        assert algo.run_algo("is_prime", [float(n)]) == (1.0 if isprime(n) else 0.0), n


def test_is_prime_fail_soft():
    assert algo.run_algo("is_prime", []) == 0.0
    assert algo.run_algo("is_prime", [float("nan")]) == 0.0
    assert algo.run_algo("is_prime", [-3.0]) == 0.0
    assert algo.run_algo("is_prime", [2.5]) == 0.0
    assert algo.run_algo("is_prime", [5e9]) == 0.0     # > 2^32-1 -> fail-soft


def test_modular_inverse_known_and_random():
    mi = lambda a, m: algo.run_algo("modular_inverse", [float(a), float(m)])
    assert mi(3, 11) == 4.0                             # 3*4 = 12 == 1 mod 11
    assert mi(10, 17) == 12.0                           # 10*12 = 120 == 1 mod 17
    assert mi(6, 9) == -1.0                             # gcd(6,9)=3 -> no inverse
    assert mi(0, 5) == -1.0
    assert mi(7, 1) == 0.0                              # everything is 0 mod 1
    rng = random.Random(331)
    for _ in range(3000):
        m = rng.randint(1, 10 ** 9)
        a = rng.randint(0, 10 ** 9)
        got = mi(a, m)
        try:
            ref = float(pow(a, -1, m)) if m > 1 else 0.0
        except ValueError:
            ref = -1.0
        assert got == ref, (a, m)


def test_modular_inverse_fail_soft():
    assert algo.run_algo("modular_inverse", [3.0]) == -1.0        # too short
    assert algo.run_algo("modular_inverse", [3.0, 0.0]) == -1.0   # m < 1
    assert algo.run_algo("modular_inverse", [2.5, 7.0]) == -1.0   # non-integer a
    assert algo.run_algo("modular_inverse", [3.0, 1e16]) == -1.0  # m > 2^53


@pytest.mark.parametrize("name", _NUMTHEORY2)
def test_p10_difftest_python_half_is_exact(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", _NUMTHEORY2)
def test_p10_c_is_bit_identical(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P11 bit manipulation (xor_reduce, popcount_total; non-negative integers, exact).
# --------------------------------------------------------------------------- #
def test_bits_ops_registered_kinds():
    assert algo.ALGO_BY_NAME["xor_reduce"].kind == algo.KIND_REDUCE
    assert algo.ALGO_BY_NAME["popcount_total"].kind == algo.KIND_REDUCE
    assert set(algo.algo_categories()["bits"]) == set(_BITS)
    for name in _BITS:
        assert algo.ALGO_BY_NAME[name].tol == 0.0


def test_xor_reduce_known_and_random():
    import functools
    import operator
    assert algo.run_algo("xor_reduce", []) == 0.0
    assert algo.run_algo("xor_reduce", [7, 3, 1]) == 5.0            # 7^3=4, 4^1=5
    assert algo.run_algo("xor_reduce", [5, 5]) == 0.0
    assert algo.run_algo("xor_reduce", [9007199254740991.0, 9007199254740991.0]) == 0.0
    rng = random.Random(411)
    for _ in range(3000):
        v = [rng.randint(0, 2 ** 52) for _ in range(rng.randint(0, 20))]
        assert algo.run_algo("xor_reduce", [float(x) for x in v]) == float(
            functools.reduce(operator.xor, v, 0))


def test_popcount_total_known_and_random():
    assert algo.run_algo("popcount_total", []) == 0.0
    assert algo.run_algo("popcount_total", [255]) == 8.0
    assert algo.run_algo("popcount_total", [7, 3, 1]) == 6.0        # 3+2+1
    assert algo.run_algo("popcount_total", [9007199254740991.0]) == 53.0   # 2^53-1 = 53 ones
    rng = random.Random(433)
    for _ in range(3000):
        v = [rng.randint(0, 2 ** 52) for _ in range(rng.randint(0, 20))]
        assert algo.run_algo("popcount_total", [float(x) for x in v]) == float(
            sum(x.bit_count() for x in v))


@pytest.mark.parametrize("name", _BITS)
def test_bits_fail_soft(name):
    assert algo.run_algo(name, [-1.0]) == 0.0
    assert algo.run_algo(name, [1.5]) == 0.0
    assert algo.run_algo(name, [float("nan")]) == 0.0
    assert algo.run_algo(name, [9007199254740992.0]) == 0.0        # 2^53 -> out of domain


@pytest.mark.parametrize("name", _BITS)
def test_bits_difftest_python_half_is_exact(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
@pytest.mark.parametrize("name", _BITS)
def test_bits_c_is_bit_identical(name, tmp_path):
    res = algo_difftest.difftest(name, tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P12 extended Euclidean algorithm (extended_gcd; [a, b] -> [g, x, y], KIND_MAP).
# --------------------------------------------------------------------------- #
def test_extended_gcd_registered_kind():
    op = algo.ALGO_BY_NAME["extended_gcd"]
    assert op.kind == algo.KIND_MAP
    assert op.out_sort == algo.SEQ
    assert op.category == "numtheory"
    assert op.tol == 0.0


def test_extended_gcd_known_values():
    assert algo.run_algo("extended_gcd", [35, 15]) == [5.0, 1.0, -2.0]   # 35*1 + 15*(-2) = 5
    assert algo.run_algo("extended_gcd", [0, 5]) == [5.0, 0.0, 1.0]
    assert algo.run_algo("extended_gcd", [5, 0]) == [5.0, 1.0, 0.0]
    assert algo.run_algo("extended_gcd", [0, 0]) == [0.0, 1.0, 0.0]
    assert algo.run_algo("extended_gcd", [7, 7]) == [7.0, 0.0, 1.0]


def test_extended_gcd_bezout_identity_random():
    """a*x + b*y == g == gcd(a, b), exactly, over random inputs incl. the 2^53 domain edge."""
    rng = random.Random(1212)
    for _ in range(5000):
        a = rng.randint(0, 2 ** 53)
        b = rng.randint(0, 2 ** 53)
        got = algo.run_algo("extended_gcd", [float(a), float(b)])
        assert len(got) == 3
        g, x, y = int(got[0]), int(got[1]), int(got[2])
        assert a * x + b * y == g == math.gcd(a, b)


def test_extended_gcd_matches_independent_recursive_oracle():
    """The iterative op agrees element-wise with the RECURSIVE extended Euclid (different code path)."""
    rng = random.Random(4848)
    for _ in range(5000):
        a = rng.randint(0, 2 ** 53)
        b = rng.randint(0, 2 ** 53)
        got = algo.run_algo("extended_gcd", [float(a), float(b)])
        g, x, y = algo_difftest._ext_gcd_rec(a, b)
        assert got == [float(g), float(x), float(y)]


def test_extended_gcd_fail_soft():
    assert algo.run_algo("extended_gcd", [3]) == []                     # too short
    # bad a (first operand):
    assert algo.run_algo("extended_gcd", [2.5, 7.0]) == []              # a non-integer
    assert algo.run_algo("extended_gcd", [-1.0, 7.0]) == []             # a negative
    assert algo.run_algo("extended_gcd", [9007199254740994.0, 3.0]) == []   # a > 2^53
    # bad b (second operand) — the guard clauses are copy-paste symmetric, so cover both sides:
    assert algo.run_algo("extended_gcd", [7.0, 2.5]) == []              # b non-integer
    assert algo.run_algo("extended_gcd", [7.0, -1.0]) == []             # b negative
    assert algo.run_algo("extended_gcd", [3.0, 9007199254740994.0]) == []   # b > 2^53
    assert algo.run_algo("extended_gcd", [7.0, float("nan")]) == []     # NaN
    # 2^53 itself is IN domain (exactly representable; coefficients stay exact):
    assert algo.run_algo("extended_gcd", [9007199254740992.0, 6.0])[0] == 2.0


def test_extended_gcd_difftest_python_half_is_exact(tmp_path):
    res = algo_difftest.difftest("extended_gcd", tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_extended_gcd_c_is_bit_identical(tmp_path):
    res = algo_difftest.difftest("extended_gcd", tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P13 closest pair of points (closest_pair; min squared distance, divide & conquer, KIND_REDUCE).
# --------------------------------------------------------------------------- #
def _brute_closest_sq(coords):
    """Independent brute-force min squared distance oracle (mirrors the difftest oracle)."""
    n = len(coords)
    if n < 4 or n % 2 != 0 or not all(
            -100000 <= v <= 100000 and v == int(v) for v in coords):
        return -1.0
    pts = [(int(coords[2 * i]), int(coords[2 * i + 1])) for i in range(n // 2)]
    best = None
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            dx = pts[i][0] - pts[j][0]
            dy = pts[i][1] - pts[j][1]
            d = dx * dx + dy * dy
            best = d if best is None or d < best else best
    return float(best)


def test_closest_pair_registered_kind():
    op = algo.ALGO_BY_NAME["closest_pair"]
    assert op.kind == algo.KIND_REDUCE
    assert op.out_sort == algo.SCALAR
    assert op.category == "geometry"
    assert op.tol == 0.0


def test_closest_pair_known_values():
    assert algo.run_algo("closest_pair", [0, 0, 3, 4]) == 25.0            # single pair
    assert algo.run_algo("closest_pair", [0, 0, 1, 0, 5, 5]) == 1.0
    assert algo.run_algo("closest_pair", [0, 0, 5, 5, 0, 0]) == 0.0       # duplicate points
    assert algo.run_algo("closest_pair", [0, 0, 0, 3, 0, 7, 0, 12]) == 9.0   # collinear
    # the closest pair straddles the divide-and-conquer mid line (exercises the strip):
    assert algo.run_algo("closest_pair", [-5, -5, -1, 0, 1, 0, 5, 5]) == 4.0
    # closest strip pair is NOT adjacent in the y-sorted strip (a truncated y-scan would miss it):
    assert algo.run_algo("closest_pair", [0, -6, -2, -2, 4, -3, -5, 3]) == 20.0
    assert algo.run_algo("closest_pair", [-1, -6, -1, 0, -5, -4, 1, -4, 4, 4]) == 8.0
    # extreme in-domain coords: max squared distance still exact (< 2^53):
    assert algo.run_algo("closest_pair", [100000, 100000, -100000, -100000]) == 80000000000.0


def test_closest_pair_matches_brute_force_random():
    """Divide & conquer == brute-force O(n^2), incl. clustered points that stress the strip scan."""
    rng = random.Random(1313)
    for _ in range(4000):
        npn = rng.randint(2, 40)
        rr = rng.choice([3, 8, 30, 100000])
        coords = []
        for _ in range(npn):
            coords.append(float(rng.randint(-rr, rr)))
            coords.append(float(rng.randint(-rr, rr)))
        assert algo.run_algo("closest_pair", coords) == _brute_closest_sq(coords)


def test_closest_pair_fail_soft():
    assert algo.run_algo("closest_pair", [5, 7]) == -1.0                  # 1 point (n < 4)
    assert algo.run_algo("closest_pair", [0, 0, 5]) == -1.0              # odd length
    # non-integer / out-of-range in BOTH the x and the y slot (guard covers every coord):
    assert algo.run_algo("closest_pair", [0.5, 0, 1, 1]) == -1.0         # non-integer x
    assert algo.run_algo("closest_pair", [0, 0.5, 1, 1]) == -1.0         # non-integer y
    assert algo.run_algo("closest_pair", [200000, 0, 1, 1]) == -1.0      # x > 1e5
    assert algo.run_algo("closest_pair", [0, 200000, 1, 1]) == -1.0      # y > 1e5
    assert algo.run_algo("closest_pair", [-200000, 0, 1, 1]) == -1.0     # x < -1e5
    assert algo.run_algo("closest_pair", [0, -200000, 1, 1]) == -1.0     # y < -1e5
    assert algo.run_algo("closest_pair", [float("nan"), 0, 1, 1]) == -1.0


def test_closest_pair_difftest_python_half_is_exact(tmp_path):
    res = algo_difftest.difftest("closest_pair", tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_closest_pair_c_is_bit_identical(tmp_path):
    res = algo_difftest.difftest("closest_pair", tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P14 Huffman optimal-prefix-code cost (huffman_cost; two-queue, tie-invariant, KIND_REDUCE).
# --------------------------------------------------------------------------- #
def _heap_huffman_cost(freqs):
    """Independent heapq (min-heap) Huffman cost oracle (different code path from two-queue)."""
    import heapq
    if len(freqs) == 0:
        return 0.0
    if not all(0 <= v <= 1099511627776 and v == int(v) for v in freqs):
        return -1.0
    if sum(int(v) for v in freqs) > 9007199254740992:
        return -1.0
    if len(freqs) == 1:
        return 0.0
    heap = [int(v) for v in freqs]
    heapq.heapify(heap)
    total = 0
    while len(heap) > 1:
        s = heapq.heappop(heap) + heapq.heappop(heap)
        total += s
        if total > 9007199254740992:
            return -1.0
        heapq.heappush(heap, s)
    return float(total)


def test_huffman_cost_registered_kind():
    op = algo.ALGO_BY_NAME["huffman_cost"]
    assert op.kind == algo.KIND_REDUCE
    assert op.out_sort == algo.SCALAR
    assert op.category == "compress"
    assert op.tol == 0.0


def test_huffman_cost_known_values():
    assert algo.run_algo("huffman_cost", [1, 1, 1, 1]) == 8.0     # 4 equal -> 2 bits each
    assert algo.run_algo("huffman_cost", [1, 2, 3]) == 9.0
    assert algo.run_algo("huffman_cost", [3, 3]) == 6.0
    assert algo.run_algo("huffman_cost", []) == 0.0              # no symbols
    assert algo.run_algo("huffman_cost", [5]) == 0.0            # single symbol -> 0 cost
    assert algo.run_algo("huffman_cost", [0, 0, 0, 5]) == 5.0   # zero frequencies


def test_huffman_cost_matches_heapq_oracle_random():
    """Two-queue Huffman == heapq Huffman (the optimal cost is tie-invariant), incl. many equal freqs."""
    rng = random.Random(1414)
    for _ in range(5000):
        n = rng.randint(0, 40)
        rr = rng.choice([1, 3, 10, 1000, 2 ** 40])
        freqs = [float(rng.randint(0, rr)) for _ in range(n)]
        assert algo.run_algo("huffman_cost", freqs) == _heap_huffman_cost(freqs)


def test_huffman_cost_fail_soft_and_overflow():
    assert algo.run_algo("huffman_cost", [1.5, 2]) == -1.0                    # non-integer
    assert algo.run_algo("huffman_cost", [-1, 2]) == -1.0                     # negative
    assert algo.run_algo("huffman_cost", [1099511627777.0, 1]) == -1.0        # > 2^40
    assert algo.run_algo("huffman_cost", [float("nan"), 2]) == -1.0           # NaN
    assert algo.run_algo("huffman_cost", [1099511627776.0, 1]) == 1099511627777.0   # 2^40 edge, valid
    # merge-total bail pinned around 2^53: *837 is just under (valid, exact), *838 just over:
    assert algo.run_algo("huffman_cost", [1099511627776.0] * 837) == 8997303650091008.0
    assert algo.run_algo("huffman_cost", [1099511627776.0] * 838) == -1.0
    assert algo.run_algo("huffman_cost", [1099511627776.0] * 1024) == -1.0    # larger over-2^53
    # WITNESS: 2^16 symbols of freq 2^33 cost EXACTLY 2^53 (= 2^16 * 2^33 * 16), which IS representable
    # and must be returned (not bailed) -> pins the '>' vs '>=' boundary of the merge-total guard:
    assert algo.run_algo("huffman_cost", [float(2 ** 33)] * 65536) == 9007199254740992.0


def test_huffman_cost_difftest_python_half_is_exact(tmp_path):
    res = algo_difftest.difftest("huffman_cost", tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_huffman_cost_c_is_bit_identical(tmp_path):
    res = algo_difftest.difftest("huffman_cost", tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P15 longest increasing subsequence length (lis_length; patience sorting, KIND_REDUCE).
# --------------------------------------------------------------------------- #
def _dp_lis_length(a):
    """Independent O(n^2) DP LIS-length oracle (different code path from patience sorting)."""
    if any(math.isnan(v) for v in a):
        return -1.0
    if not a:
        return 0.0
    dp = [1] * len(a)
    for i in range(len(a)):
        for j in range(i):
            if a[j] < a[i] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
    return float(max(dp))


def test_lis_length_registered_kind():
    op = algo.ALGO_BY_NAME["lis_length"]
    assert op.kind == algo.KIND_REDUCE
    assert op.out_sort == algo.SCALAR
    assert op.category == "search"
    assert op.tol == 0.0


def test_lis_length_known_values():
    assert algo.run_algo("lis_length", [3, 1, 2, 4]) == 3.0        # 1,2,4
    assert algo.run_algo("lis_length", [5, 4, 3, 2, 1]) == 1.0     # strictly decreasing
    assert algo.run_algo("lis_length", [1, 2, 3, 4, 5]) == 5.0
    assert algo.run_algo("lis_length", []) == 0.0
    assert algo.run_algo("lis_length", [7]) == 1.0
    assert algo.run_algo("lis_length", [2, 2, 2, 2]) == 1.0        # strict: duplicates don't extend
    assert algo.run_algo("lis_length", [1, 3, 2, 3, 4]) == 4.0
    assert algo.run_algo("lis_length", [0.0, -0.0, 1.0]) == 2.0    # -0.0 == 0.0 (not strictly increasing)


def test_lis_length_matches_dp_oracle_random():
    """Patience sorting == O(n^2) DP over integer and float sequences (with ties)."""
    rng = random.Random(1515)
    for _ in range(4000):
        n = rng.randint(0, 40)
        rr = rng.choice([3, 8, 50, 10 ** 9])
        a = [float(rng.randint(-rr, rr)) for _ in range(n)]
        assert algo.run_algo("lis_length", a) == _dp_lis_length(a)
    for _ in range(1000):
        n = rng.randint(0, 30)
        a = [rng.uniform(-100.0, 100.0) for _ in range(n)]
        assert algo.run_algo("lis_length", a) == _dp_lis_length(a)


def test_lis_length_nan_fail_soft():
    assert algo.run_algo("lis_length", [float("nan"), 1, 2]) == -1.0
    assert algo.run_algo("lis_length", [1, float("nan"), 2]) == -1.0
    assert algo.run_algo("lis_length", [1, 2, float("nan")]) == -1.0


def test_lis_length_difftest_python_half_is_exact(tmp_path):
    res = algo_difftest.difftest("lis_length", tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_lis_length_c_is_bit_identical(tmp_path):
    res = algo_difftest.difftest("lis_length", tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P16 inversion count (count_inversions; counting merge sort, KIND_REDUCE).
# --------------------------------------------------------------------------- #
def _brute_inversions(a):
    """Independent O(n^2) brute-force inversion count (different code path from merge sort)."""
    if any(math.isnan(v) for v in a):
        return -1.0
    c = 0
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            if a[i] > a[j]:
                c += 1
    return float(c)


def test_count_inversions_registered_kind():
    op = algo.ALGO_BY_NAME["count_inversions"]
    assert op.kind == algo.KIND_REDUCE
    assert op.out_sort == algo.SCALAR
    assert op.category == "stat"
    assert op.tol == 0.0


def test_count_inversions_known_values():
    assert algo.run_algo("count_inversions", [1, 2, 3, 4]) == 0.0       # sorted
    assert algo.run_algo("count_inversions", [4, 3, 2, 1]) == 6.0       # reversed: n(n-1)/2
    assert algo.run_algo("count_inversions", [2, 1, 3]) == 1.0
    assert algo.run_algo("count_inversions", [3, 1, 2]) == 2.0
    assert algo.run_algo("count_inversions", []) == 0.0
    assert algo.run_algo("count_inversions", [5]) == 0.0
    assert algo.run_algo("count_inversions", [2, 2, 2]) == 0.0          # strict: equal is not an inversion
    assert algo.run_algo("count_inversions", [2, 1, 2, 1]) == 3.0
    assert algo.run_algo("count_inversions", [-0.0, 0.0]) == 0.0        # -0.0 == 0.0
    assert algo.run_algo("count_inversions", [float("inf"), 1.0, float("-inf")]) == 3.0  # all 3 pairs
    # long-long width: a strictly-decreasing n=65537 has 65537*65536/2 inversions, just over INT_MAX:
    assert algo.run_algo("count_inversions", [float(x) for x in range(65537, 0, -1)]) == 2147516416.0


def test_count_inversions_matches_brute_random():
    """Counting merge sort == O(n^2) brute over integer and float sequences (with ties)."""
    rng = random.Random(1616)
    for _ in range(4000):
        n = rng.randint(0, 40)
        rr = rng.choice([2, 5, 40, 10 ** 9])
        a = [float(rng.randint(-rr, rr)) for _ in range(n)]
        assert algo.run_algo("count_inversions", a) == _brute_inversions(a)
    for _ in range(1000):
        n = rng.randint(0, 30)
        a = [rng.uniform(-50.0, 50.0) for _ in range(n)]
        assert algo.run_algo("count_inversions", a) == _brute_inversions(a)


def test_count_inversions_nan_fail_soft():
    assert algo.run_algo("count_inversions", [float("nan"), 1, 2]) == -1.0
    assert algo.run_algo("count_inversions", [1, float("nan"), 2]) == -1.0
    assert algo.run_algo("count_inversions", [1, 2, float("nan")]) == -1.0


def test_count_inversions_difftest_python_half_is_exact(tmp_path):
    res = algo_difftest.difftest("count_inversions", tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_count_inversions_c_is_bit_identical(tmp_path):
    res = algo_difftest.difftest("count_inversions", tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["passed"] is True


# --------------------------------------------------------------------------- #
# P17 maximum subarray sum (max_subarray; Kadane's O(n) reset scan, KIND_REDUCE).
# --------------------------------------------------------------------------- #
def _brute_max_subarray(a):
    """Independent O(n^2) brute-force max subarray sum, empty allowed (different code path from
    Kadane). Same integer domain as the op: NaN / inf / non-integer / |x| > 2^52 / overflow -> -1.0."""
    lim = 4503599627370496.0                                  # 2^52
    sum_abs = 0
    for x in a:
        if not (-lim <= x <= lim) or x != float(int(x)):      # short-circuits before int() on NaN/inf
            return -1.0
        v = int(x)
        sum_abs += -v if v < 0 else v
        if sum_abs > 4503599627370496:
            return -1.0
    best = 0                                                  # empty subarray allowed
    for i in range(len(a)):
        s = 0
        for j in range(i, len(a)):
            s += int(a[j])
            best = max(best, s)
    return float(best)


def test_max_subarray_registered_kind():
    op = algo.ALGO_BY_NAME["max_subarray"]
    assert op.kind == algo.KIND_REDUCE
    assert op.out_sort == algo.SCALAR
    assert op.category == "search"
    assert op.tol == 0.0


def test_max_subarray_known_values():
    assert algo.run_algo("max_subarray", [1, 2, 3]) == 6.0
    assert algo.run_algo("max_subarray", [-1, -2, -3]) == 0.0          # all-negative -> empty subarray
    assert algo.run_algo("max_subarray", []) == 0.0
    assert algo.run_algo("max_subarray", [5]) == 5.0
    assert algo.run_algo("max_subarray", [-5]) == 0.0
    assert algo.run_algo("max_subarray", [-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6.0   # classic [4,-1,2,1]
    assert algo.run_algo("max_subarray", [3, -1, 4]) == 6.0
    assert algo.run_algo("max_subarray", [2, -1, 2, -1, 2]) == 4.0     # whole array
    assert algo.run_algo("max_subarray", [0.0, 0.0]) == 0.0
    assert algo.run_algo("max_subarray", [-0.0, 5.0]) == 5.0           # signed zero
    assert algo.run_algo("max_subarray", [5, -10, 5]) == 5.0           # a mid drop resets cur
    # overflow boundary pinned at 2^52 (running sum of |x|): exactly 2^52 is VALID, 2^52+1 bails:
    assert algo.run_algo("max_subarray", [4503599627370496.0]) == 4503599627370496.0    # sum_abs == 2^52
    assert algo.run_algo("max_subarray", [2251799813685248.0, 2251799813685248.0]) == 4503599627370496.0
    assert algo.run_algo("max_subarray", [4503599627370496.0, 1.0]) == -1.0             # 2^52+1 overflow


def test_max_subarray_matches_brute_random():
    """Kadane's O(n) reset scan == O(n^2) brute over integer sequences (mixed signs, ties)."""
    rng = random.Random(1717)
    for _ in range(5000):
        n = rng.randint(0, 40)
        rr = rng.choice([2, 5, 40, 10 ** 6])
        a = [float(rng.randint(-rr, rr)) for _ in range(n)]
        assert algo.run_algo("max_subarray", a) == _brute_max_subarray(a)


def test_max_subarray_fail_soft_and_overflow():
    assert algo.run_algo("max_subarray", [1.5, 2]) == -1.0                          # non-integer
    assert algo.run_algo("max_subarray", [float("inf"), 1]) == -1.0                 # +inf
    assert algo.run_algo("max_subarray", [1, float("-inf")]) == -1.0               # -inf
    assert algo.run_algo("max_subarray", [float("nan"), 1]) == -1.0                # NaN first
    assert algo.run_algo("max_subarray", [1, float("nan")]) == -1.0               # NaN mid
    assert algo.run_algo("max_subarray", [4503599627370497.0]) == -1.0            # single |x| = 2^52+1
    assert algo.run_algo("max_subarray", [2251799813685248.0, 2251799813685248.0, 1.0]) == -1.0  # sum overflow


def test_max_subarray_difftest_python_half_is_exact(tmp_path):
    res = algo_difftest.difftest("max_subarray", tmp_path, cc=None)
    assert res["python_pass"] is True
    assert res["python_max_abs_diff"] == 0.0


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_max_subarray_c_is_bit_identical(tmp_path):
    res = algo_difftest.difftest("max_subarray", tmp_path, cc="auto")
    assert res["c_backend"]["c_vs_python_bit_identical"] is True
    assert res["c_backend"].get("ubsan") in ("ok", "unsupported")   # shipped op is UBSan-clean
    assert res["passed"] is True


@pytest.mark.skipif(not _HAS_CC, reason="no C toolchain (gcc/clang or ziglang)")
def test_ubsan_pass_catches_nan_slip_through_cast(tmp_path):
    """The gate compiles C a 2nd time under -fsanitize=undefined. A domain guard that rejects a
    NaN only via (long long)NaN UB -- which -O2 may silently accept, but a UBSan/safe build
    hard-traps -- FAILS the gate. A De Morgan rewrite of max_subarray's C range guard lets NaN slip
    to the cast: the -O2 bit-compare still matches Python, but the UBSan pass traps. (P17 review.)"""
    op = algo.ALGO_BY_NAME["max_subarray"]
    orig = op.c_code
    mutated = orig.replace("if (!(x >= -LIM && x <= LIM)) return -1.0;",
                           "if (x < -LIM || x > LIM) return -1.0;")
    assert mutated != orig, "mutation anchor not found (op C source changed?)"
    try:
        object.__setattr__(op, "c_code", mutated)
        res = algo_difftest.difftest("max_subarray", tmp_path / "mut", cc="auto")
    finally:
        object.__setattr__(op, "c_code", orig)
    cb = res["c_backend"]
    if cb.get("ubsan") == "unsupported":
        pytest.skip("toolchain has no UBSan; the -O2 bit-compare cannot pin reject-before-cast")
    assert cb.get("ubsan") == "trap"            # NaN reached (long long)NaN under UBSan
    assert cb.get("c_vs_python_bit_identical") is True   # -O2 was fooled...
    assert res["passed"] is False               # ...but the UBSan pass fails the gate


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
    # a fresh (no prior marker) unknown op fails closed by raising, writing no marker
    with pytest.raises(SystemExit):
        gate.gate("nope", tmp_path, use_c=False)
    assert not (tmp_path / "gate_ok.json").exists()


def test_algo_gate_unknown_op_removes_stale_marker(tmp_path):
    # an unresolvable op must NOT inherit a prior run's pass: the stale marker is removed
    # BEFORE the unknown-op guard, so the work-graph node fails closed (produces gone + exit 1).
    gate = _load_algo_gate()
    stale = tmp_path / "gate_ok.json"
    stale.write_text('{"op": "gauss_solve", "passed": true}', encoding="utf-8")  # prior pass
    with pytest.raises(SystemExit):
        gate.gate("nope", tmp_path, use_c=False)
    assert not stale.exists()


def test_algo_gate_requires_c_by_default_when_toolchain_absent(tmp_path, monkeypatch):
    # With C required (the default the work-graph node uses) and NO toolchain, an
    # honest-but-UNVERIFIED Python pass must NOT write gate_ok.json — so the node fails
    # closed instead of turning green on C that was never compiled.
    gate = _load_algo_gate()
    monkeypatch.setattr(algo_difftest, "find_c_compiler", lambda: None)  # simulate C-less venv
    res = gate.gate("gauss_solve", tmp_path, use_c=True)   # require_c defaults to True
    assert res["passed"] is True                           # Python half still passes
    assert res["c_verified"] is False                      # but C was skipped (unverified)
    assert res["gate_marker_written"] is False
    assert not (tmp_path / "gate_ok.json").exists()        # no success signal for the graph
    assert (tmp_path / "gate_unverified.json").exists()    # honest diagnostic instead


def test_algo_gate_allow_unverified_c_writes_marker(tmp_path, monkeypatch):
    # the explicit opt-out lets a C-less pass count (deliberate, not silent)
    gate = _load_algo_gate()
    monkeypatch.setattr(algo_difftest, "find_c_compiler", lambda: None)
    res = gate.gate("gauss_solve", tmp_path, use_c=True, require_c=False)
    assert res["gate_marker_written"] is True
    assert (tmp_path / "gate_ok.json").exists()
