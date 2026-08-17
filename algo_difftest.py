"""algo_difftest — the honest-correctness gate for the general-algorithm tier.

Two independent checks, both real measurements (not deferred skips) whenever a C
toolchain is present:

  Python vs oracle : the Python reference (``algo.py_fn``) is compared **by value**
                     to a ground-truth oracle — ``numpy.sort`` for sorts,
                     ``numpy.max`` / ``numpy.min`` for reductions. Fail-closed: a
                     structural mismatch or any non-finite value yields ``inf`` and
                     is never tolerance-gated (so ``--tol inf`` cannot pass a
                     malformed result). Catches a wrong reimplementation.
  C vs Python      : the codegen C (``algo_codegen.emit_c``) is compiled and run on
                     the same holdout, then compared **bit-for-bit** (raw IEEE-754
                     float64 bytes, so +0.0 vs -0.0 and NaN payloads are visible —
                     an abs-diff of 0.0 would not be). Because C and Python run the
                     same algorithm, a correct backend is byte-identical; the abs
                     diff is still reported as a secondary metric.

``c_verified`` in the result is True only when the C artifact was actually
compiled, run and bit-compared here; a toolchain-less pass is honest but
UNVERIFIED (surfaced so CI can require verification).

C toolchain: ``gcc`` / ``cc`` / ``clang`` on PATH, else ``python -m ziglang cc``
(the pip-installable, self-contained clang). If none is found the C half SKIPs
with an honest reason; a compile/run FAILURE is a gate failure, never a skip
(fail-closed, matching image ``difftest.py``).

Deterministic. Writes ``algo_difftest_<op>.json``.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

import algo
import algo_codegen


# --------------------------------------------------------------------------- #
# toolchain discovery
# --------------------------------------------------------------------------- #
def find_c_compiler() -> list[str] | None:
    """A C compiler command (as an argv list), or ``None`` if none is available.

    Prefers a system compiler; falls back to ``python -m ziglang cc`` (a
    self-contained clang installable with ``pip install ziglang``).
    """
    for cc in ("gcc", "cc", "clang"):
        p = shutil.which(cc)
        if p:
            return [p]
    try:
        import ziglang  # noqa: F401
        return [sys.executable, "-m", "ziglang", "cc"]
    except ImportError:
        return None


def compiler_label(cc: list[str] | None) -> str:
    if not cc:
        return "none"
    if len(cc) >= 3 and cc[1:3] == ["-m", "ziglang"]:
        return "ziglang cc"
    return Path(cc[0]).name


# --------------------------------------------------------------------------- #
# holdout — deterministic, edge cases first then random
# --------------------------------------------------------------------------- #
def make_holdout(seed: int = 0, n_random: int = 40, max_len: int = 257) -> list[list[float]]:
    """A deterministic list of test sequences: structured edge cases + random."""
    rng = random.Random(seed)
    cases: list[list[float]] = [
        [],                                        # empty
        [3.5],                                     # singleton
        [2.0, 1.0],                                # pair, reversed
        [1.0, 1.0, 1.0, 1.0],                      # all equal
        [1.0, 2.0, 3.0, 4.0, 5.0],                 # already sorted
        [5.0, 4.0, 3.0, 2.0, 1.0],                 # reverse sorted
        [3.0, 1.0, 3.0, 1.0, 2.0, 2.0],            # duplicates
        [-2.0, 0.0, -1.0, 5.0, -3.0, 4.0],         # signs
        [0.0, -0.0, 1.0, -1.0],                    # +0 / -0 (compare equal)
        [1e-9, 1e9, -1e9, 3.14159, -2.71828],      # wide magnitude
        [7.0] * 300,                               # large all-equal (3-way partition path)
        [float(i % 2) for i in range(300)],        # two-valued (a flattened binary mask)
        [float(rng.randint(0, 3)) for _ in range(300)],   # few-distinct, duplicate-heavy
    ]
    for _ in range(n_random):
        n = rng.randint(0, max_len)
        cases.append([rng.uniform(-1000.0, 1000.0) for _ in range(n)])
    # a couple of duplicate-heavy larger randoms (small value range -> many ties)
    for _ in range(3):
        n = rng.randint(0, max_len)
        cases.append([float(rng.randint(0, 5)) for _ in range(n)])
    return cases


def _poly_at(coeffs, x: float) -> float:
    r = 0.0
    for c in reversed(coeffs):
        r = r * x + c
    return r


def _lev_recursive(a: tuple, b: tuple) -> float:
    """Levenshtein by TOP-DOWN memoized recursion — an independent oracle for the
    op's bottom-up two-row DP (different code path, same definition)."""
    from functools import cache

    @cache
    def d(i: int, j: int) -> int:
        if i == 0:
            return j
        if j == 0:
            return i
        cost = 0 if a[i - 1] == b[j - 1] else 1
        return min(d(i - 1, j) + 1, d(i, j - 1) + 1, d(i - 1, j - 1) + cost)

    return float(d(len(a), len(b)))


def _lcs_recursive(a: tuple, b: tuple) -> float:
    """LCS length by TOP-DOWN memoized recursion — independent oracle for the op's DP."""
    from functools import cache

    @cache
    def c(i: int, j: int) -> int:
        if i == 0 or j == 0:
            return 0
        if a[i - 1] == b[j - 1]:
            return c(i - 1, j - 1) + 1
        return max(c(i - 1, j), c(i, j - 1))

    return float(c(len(a), len(b)))


def _int_in(x: float, lo: float, hi: float) -> bool:
    """True iff x is a finite, integer-valued double in [lo, hi] — the NaN-safe raw-value +
    integrality guard the P5 data-value ops use. The P5 oracles call this to mirror each op's
    declared domain, so an out-of-domain holdout case makes the oracle return the op's fail-soft
    value (0.0 / []) — which the op must also return — instead of crashing (zlib.crc32 / pow() /
    int(nan) all raise on out-of-domain input). That lets the honest gate itself FALSIFY a broken
    guard (a divergent op no longer matches the oracle), not only the one parity unit test."""
    return math.isfinite(x) and lo <= x <= hi and x == float(int(x))


def _winding_number_inside(px: int, py: int, xs: list[int], ys: list[int]) -> bool:
    """Winding-number != 0 point-in-polygon test (Sunday) — an INDEPENDENT oracle for the
    crossing-number op (a different algorithm; both integer-exact and agree at strict interior/
    exterior points of a simple polygon)."""
    n = len(xs)
    wn = 0
    for i in range(n):
        x1, y1 = xs[i], ys[i]
        j = (i + 1) % n
        x2, y2 = xs[j], ys[j]
        if y1 <= py:
            if y2 > py and (x2 - x1) * (py - y1) - (px - x1) * (y2 - y1) > 0:
                wn += 1                                     # upward crossing, P left of edge
        else:
            if y2 <= py and (x2 - x1) * (py - y1) - (px - x1) * (y2 - y1) < 0:
                wn -= 1                                     # downward crossing, P right of edge
    return wn != 0


def _on_segment_int(px: int, py: int, x1: int, y1: int, x2: int, y2: int) -> bool:
    """True iff integer point (px,py) lies on the closed segment (x1,y1)-(x2,y2)."""
    if (x2 - x1) * (py - y1) - (px - x1) * (y2 - y1) != 0:   # not collinear
        return False
    return min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2)


def _on_boundary(px: int, py: int, xs: list[int], ys: list[int]) -> bool:
    """True iff (px,py) lies on any edge of the polygon — such points are excluded from the
    point_in_polygon holdout (boundary is implementation-defined; crossing vs winding can differ)."""
    n = len(xs)
    return any(_on_segment_int(px, py, xs[i], ys[i], xs[(i + 1) % n], ys[(i + 1) % n])
               for i in range(n))


def _is_prime_trial(p: int) -> bool:
    """Primality by trial division — an INDEPENDENT oracle for sieve_primes (a wholly
    different code path from the sieve: per-candidate division vs. a marking pass)."""
    if p < 2:
        return False
    if p < 4:
        return True
    if p % 2 == 0:
        return False
    i = 3
    while i * i <= p:
        if p % i == 0:
            return False
        i += 2
    return True


def _ext_gcd_rec(a: int, b: int) -> tuple[int, int, int]:
    """Extended Euclidean algorithm by RECURSION — an INDEPENDENT oracle for extended_gcd
    (a wholly different code path from the op's iterative two-variable sweep). Returns the
    same canonical (g, x, y) with a*x + b*y == g; the recursion unrolls to the iteration,
    so element-wise equality is a valid check (the coefficients are deterministic here,
    unlike the non-unique Bezout identity that only an a*x+b*y==g check would allow)."""
    if b == 0:
        return (a, 1, 0)
    g, x1, y1 = _ext_gcd_rec(b, a % b)
    return (g, y1, x1 - (a // b) * y1)


def holdout_for(name: str, seed: int = 0) -> list[list[float]]:
    """Per-op holdout. Numeric ops need VALID structured inputs (samples for
    Simpson, sign-bracketed / near-root polynomials for the root finders)."""
    rng = random.Random(seed + 777)
    if name == "simpson":
        cases = []
        for _ in range(20):
            m = rng.choice([3, 5, 7, 9, 11])                 # odd sample count (clean Simpson)
            h = rng.uniform(0.05, 0.5)
            coeffs = [rng.uniform(-2.0, 2.0) for _ in range(rng.randint(1, 5))]
            cases.append([h] + [_poly_at(coeffs, i * h) for i in range(m)])
        for _ in range(6):                                   # EVEN sample count -> trapezoid tail
            m = rng.choice([4, 6, 8, 10])
            h = rng.uniform(0.05, 0.5)
            coeffs = [rng.uniform(-2.0, 2.0) for _ in range(rng.randint(1, 5))]
            cases.append([h] + [_poly_at(coeffs, i * h) for i in range(m)])
        return cases
    if name in ("bisection", "newton"):
        cases = []
        for _ in range(24):
            root = rng.uniform(-3.0, 3.0)
            other = root + rng.choice([-1.0, 1.0]) * rng.uniform(1.5, 3.0)  # far from root
            c = [root * other, -(root + other), 1.0]         # (x-root)(x-other), ascending
            if len(cases) % 3 == 0:                          # every 3rd: multiply by (x^2+1)
                c = [c[0], c[1], c[2] + c[0], c[1], c[2]]    # (a+bx+x^2)(1+x^2), degree 4, same real root
            if name == "bisection":
                cases.append([root - 0.3, root + 0.3] + c)   # bracket straddles only `root`
            else:
                cases.append([root + rng.uniform(-0.4, 0.4)] + c)   # x0 near root
        return cases
    if name == "gauss_solve":
        # WELL-CONDITIONED augmented systems only (a singular / ill-conditioned holdout
        # would make np.linalg.solve unstable or raise, i.e. a holdout bug rather than a
        # backend fault). Diagonal dominance guarantees a unique, well-conditioned
        # solution; a few row-permuted cases force the partial-pivoting path.
        cases = []

        def _pack(matrix: list[list[float]], x: list[float]) -> list[float]:
            nn = len(x)
            b = [sum(matrix[i][j] * x[j] for j in range(nn)) for i in range(nn)]
            flat: list[float] = [float(nn)]
            for i in range(nn):
                flat.extend(matrix[i])
                flat.append(b[i])
            return flat

        def _diag_dominant(nn: int) -> list[list[float]]:
            mat = [[rng.uniform(-5.0, 5.0) for _ in range(nn)] for _ in range(nn)]
            for i in range(nn):
                mag = sum(abs(mat[i][j]) for j in range(nn)) + rng.uniform(1.0, 3.0)
                mat[i][i] = -mag if rng.random() < 0.5 else mag
            return mat

        cases.append([1.0, 4.0, 8.0])                        # 1x1: 4x = 8 -> x = 2
        for _ in range(24):                                  # diagonally dominant, sizes 1..7
            nn = rng.randint(1, 7)
            x = [rng.uniform(-10.0, 10.0) for _ in range(nn)]
            cases.append(_pack(_diag_dominant(nn), x))
        for _ in range(6):                                   # row-permuted (a swap occurs, but is
            nn = rng.randint(2, 5)                            # NOT required for correctness — the
            mat = _diag_dominant(nn)                          # pivot-REQUIRED cases below are what
            mat[0], mat[nn - 1] = mat[nn - 1], mat[0]        # falsify a missing-pivot defect)
            x = [rng.uniform(-10.0, 10.0) for _ in range(nn)]
            cases.append(_pack(mat, x))
        # PIVOT-REQUIRED cases: all well-conditioned (np.linalg.solve stays a valid oracle),
        # but a gauss WITHOUT partial pivoting gives a wrong answer / divides by zero here — so
        # the gate can now actually FALSIFY a missing-pivot defect, which the diag-dominant cases
        # (min |A[0,0]| ~ 0.7, never zero) cannot. (2026-08-16 review, feedback_no_solo_ai_judgment.)
        cases.append(_pack([[0.0, 1.0], [1.0, 0.0]], [2.0, 1.0]))          # exact-zero (0,0) pivot
        cases.append(_pack([[0.0, 2.0, 1.0], [1.0, 0.0, 3.0], [2.0, 1.0, 0.0]],
                           [1.0, -2.0, 3.0]))                             # 3x3, zero (0,0), det!=0
        cases.append(_pack([[1e-14, 1.0], [1.0, 1.0]], [3.0, 5.0]))        # tiny (0,0): no-pivot blows up
        return cases
    if name == "strfind":
        # small alphabet -> many (overlapping) matches; codes are exact-integer float64.
        cases = [
            [1.0, 65.0, 65.0, 65.0, 65.0],                     # "A" in "AAA" -> 0,1,2 (overlap)
            [2.0, 65.0, 65.0, 65.0, 65.0, 65.0],               # "AA" in "AAA" -> 0,1 (overlap)
            [3.0, 65.0, 66.0, 67.0, 68.0, 69.0, 70.0],         # "ABC" in "DEF" -> [] (no match)
            [2.0, 65.0, 66.0, 65.0, 66.0, 65.0, 66.0],         # "AB" in "ABAB" -> 0,2
            [4.0, 65.0, 66.0, 67.0, 68.0, 65.0, 66.0, 67.0, 68.0],  # pattern == text -> 0
        ]
        for _ in range(30):
            alpha = rng.randint(2, 4)                          # 2..4 distinct symbols -> ties/matches
            m = rng.randint(1, 4)
            k = rng.randint(m, 24)
            pat = [float(65 + rng.randint(0, alpha - 1)) for _ in range(m)]
            text = [float(65 + rng.randint(0, alpha - 1)) for _ in range(k)]
            cases.append([float(m)] + pat + text)
        return cases
    if name in ("edit_distance", "lcs_length"):
        # pairs of small strings over a tiny alphabet, incl. empty / identical / disjoint.
        cases = [
            [0.0],                                             # both empty -> 0
            [3.0, 65.0, 66.0, 67.0],                           # A="ABC", B="" -> 3 / lcs 0
            [3.0, 65.0, 66.0, 67.0, 65.0, 66.0, 67.0],         # identical "ABC" -> 0 / lcs 3
            [3.0, 65.0, 66.0, 67.0, 68.0, 69.0, 70.0],         # disjoint "ABC" vs "DEF" -> 3 / lcs 0
        ]
        for _ in range(30):
            alpha = rng.randint(2, 4)
            na = rng.randint(0, 9)
            nb = rng.randint(0, 9)
            sa = [float(65 + rng.randint(0, alpha - 1)) for _ in range(na)]
            sb = [float(65 + rng.randint(0, alpha - 1)) for _ in range(nb)]
            cases.append([float(na)] + sa + sb)
        return cases
    if name == "graph_components":
        # undirected graphs [n, m, (u,v,w)*m]; connectivity-only, so self-loops & multi-
        # edges are fine (integer weights, ignored). Mix of isolated / path / 2-component.
        cases = [
            [1.0, 0.0],                                        # single isolated node
            [3.0, 0.0],                                        # 3 isolated -> 3 components
            [4.0, 3.0, 0.0, 1.0, 2.0, 1.0, 2.0, 3.0, 2.0, 3.0, 5.0],   # path -> 1 component
            [6.0, 6.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 0.0, 3.0,    # two triangles -> 2
             3.0, 4.0, 1.0, 4.0, 5.0, 2.0, 5.0, 3.0, 3.0],
        ]
        for _ in range(26):
            n = rng.randint(1, 10)
            m = rng.randint(0, 16)
            edges: list[float] = []
            for _ in range(m):
                edges += [float(rng.randint(0, n - 1)), float(rng.randint(0, n - 1)),
                          float(rng.randint(1, 20))]
            cases.append([float(n), float(m)] + edges)
        return cases

    def _simple_graph(nn: int):
        """A random SIMPLE undirected edge set (no self-loops/multi-edges) with DISTINCT
        integer weights — so a scipy csr matches it exactly (no duplicate-summing) and the
        MST / shortest paths are unambiguous."""
        pairs = [(u, v) for u in range(nn) for v in range(u + 1, nn)]
        rng.shuffle(pairs)
        mm = rng.randint(0, len(pairs))
        chosen = pairs[:mm]
        wts = rng.sample(range(1, 400), len(chosen)) if chosen else []
        flat: list[float] = []
        for (u, v), w in zip(chosen, wts):
            flat += [float(u), float(v), float(w)]
        return len(chosen), flat

    if name == "graph_mst_weight":
        cases = [
            [1.0, 0.0],                                        # single node -> 0
            [3.0, 0.0],                                        # forest of isolated -> 0
            [3.0, 3.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0, 0.0, 2.0, 3.0],   # triangle -> 1+2 = 3
        ]
        for _ in range(26):
            n = rng.randint(1, 9)
            m, flat = _simple_graph(n)
            cases.append([float(n), float(m)] + flat)
        return cases
    if name == "graph_dijkstra":
        # CONNECTED simple graphs [n, m, src, (u,v,w)*m]: a spanning path guarantees
        # reachability; extra edges are distinct non-path simple pairs. Integer weights.
        cases = [
            [1.0, 0.0, 0.0],                                   # single node, dist [0]
            [3.0, 2.0, 0.0, 0.0, 1.0, 5.0, 1.0, 2.0, 3.0],     # path 0-1-2 from src 0
        ]
        for _ in range(28):
            n = rng.randint(1, 9)
            used = {(i, i + 1) for i in range(n - 1)}          # spanning path (connected)
            edges: list[float] = []
            for i in range(n - 1):
                edges += [float(i), float(i + 1), float(rng.randint(1, 9))]
            spare = [(u, v) for u in range(n) for v in range(u + 1, n) if (u, v) not in used]
            rng.shuffle(spare)
            for (u, v) in spare[:rng.randint(0, min(6, len(spare)))]:
                edges += [float(u), float(v), float(rng.randint(1, 9))]
            m = len(edges) // 3
            cases.append([float(n), float(m), float(rng.randint(0, n - 1))] + edges)
        return cases
    if name == "gcd_seq":
        cases = [
            [],                                            # empty -> 0
            [0.0],                                         # gcd(0) = 0
            [0.0, 0.0],                                    # gcd(0,0) = 0
            [12.0],                                        # gcd(12) = 12
            [12.0, 18.0],                                  # gcd = 6
            [12.0, 18.0, 24.0],                            # gcd = 6
            [17.0, 5.0],                                   # coprime -> 1
            [0.0, 7.0],                                    # gcd(0,7) = 7
            [1000000000.0, 999999999.0],                   # large coprime -> 1
            [2.0 ** 40, 2.0 ** 35],                        # powers of two -> 2^35
            [9007199254740992.0, 4503599627370496.0],      # AT the 2^53 guard edge -> 2^52
            [9007199254740992.0, 9007199254740991.0],      # 2^53 vs 2^53-1 (coprime) -> 1
            # out-of-domain -> op fail-softs 0.0 (exercises the guard; oracle mirrors it):
            [12.0, -6.0],                                  # negative
            [12.0, 6.5],                                   # non-integer
            [float("nan"), 6.0],                           # NaN header value
            [1e300],                                       # > 2^53
        ]
        for _ in range(30):
            k = rng.randint(0, 6)
            cases.append([float(rng.randint(0, 100000)) for _ in range(k)])
        for _ in range(6):                                 # share a common factor -> gcd > 1
            g = rng.randint(2, 50)
            cases.append([float(g * rng.randint(1, 5000)) for _ in range(rng.randint(2, 5))])
        return cases
    if name == "sieve_primes":
        cases = [[float(n)] for n in (0, 1, 2, 3, 4, 5, 10, 11, 12, 30, 97, 100, 541, 1000)]
        for _ in range(20):
            cases.append([float(rng.randint(0, 2000))])
        # out-of-domain / boundary -> op fail-softs [] (over cap / NaN / negative) or truncates a
        # fractional header. (The AT-cap accept edge n=5,000,000 is slow in the Python reference, so
        # it lives in a dedicated C-only test, not this shared holdout — see test_algo.py.)
        cases += [[float("nan")], [-3.0], [5000001.0], [1e9], [30.5]]
        return cases
    if name == "pow_mod":
        cases = [
            [2.0, 10.0, 1000.0],                           # 1024 mod 1000 = 24
            [3.0, 0.0, 7.0],                               # exp 0 -> 1
            [0.0, 5.0, 7.0],                               # 0
            [5.0, 3.0, 1.0],                               # mod 1 -> 0
            [7.0, 128.0, 13.0],                            # large exp
            [123456.0, 65537.0, 1000000007.0],             # RSA-flavoured (< 2^32 modulus)
            # AT the declared base/exp domain edge (2^53) — pins the honest-domain disclosure so an
            # exp->uint32 / base->uint32 C truncation regression is caught by the gate, not just docs:
            [2.0, 9007199254740992.0, 7.0],                # base small, exp = 2^53
            [9007199254740992.0, 9007199254740992.0, 4294967295.0],   # base=exp=2^53, mod=2^32-1
            [9007199254740991.0, 9007199254740991.0, 4294967291.0],   # 2^53-1, near-max mod
            [9007199254740992.0, 3.0, 1000003.0],          # base > mod -> reduction path
            # the '1 % mod' special case (exp == 0 AND mod == 1): unfalsifiable without BOTH together
            [7.0, 0.0, 1.0],                               # pow(7,0,1) = 0
            [0.0, 0.0, 1.0],                               # pow(0,0,1) = 0
            # short / empty (falsifies the C `n < 3` guard, which else OOB-reads freed heap):
            [], [2.0], [2.0, 3.0],
            # out-of-domain -> op fail-softs 0.0 (exercises base/exp/mod guards in the gate):
            [2.0, 3.0, 0.0],                               # mod 0
            [2.0, -1.0, 7.0],                              # negative exp
            [2.0, 3.0, 5e9],                               # mod > 2^32-1
            [2.5, 3.0, 7.0],                               # non-integer base
            [float("nan"), 3.0, 7.0],                      # NaN
        ]
        for _ in range(30):
            cases.append([float(rng.randint(0, 1000000)),
                          float(rng.randint(0, 100000)),
                          float(rng.randint(1, 4294967295))])
        return cases
    if name == "crc32":
        cases = [
            [],                                            # crc32(b'') = 0
            [0.0],
            [255.0],
            [72.0, 101.0, 108.0, 108.0, 111.0],            # "Hello"
            [float(i) for i in range(256)],                # every byte value
            # out-of-domain -> op fail-softs 0.0 (exercises the byte guard in the gate):
            [256.0], [-1.0], [1.5], [float("nan")],
        ]
        for _ in range(30):
            k = rng.randint(0, 40)
            cases.append([float(rng.randint(0, 255)) for _ in range(k)])
        return cases
    if name == "rle_encode":
        cases = [
            [],                                            # empty
            [5.0],                                         # single run
            [7.0, 7.0, 7.0, 7.0],                          # one long run
            [1.0, 2.0, 3.0, 4.0],                          # all distinct -> output 2x input
            [1.0, 1.0, 2.0, 2.0, 2.0, 3.0],                # mixed runs
            [0.0, -0.0, 0.0],                              # +0/-0 compare equal -> one run
        ]
        for _ in range(30):
            k = rng.randint(0, 30)
            cases.append([float(rng.randint(0, 3)) for _ in range(k)])   # small alphabet -> runs
        return cases
    if name == "polygon_area2":
        rng2 = random.Random(seed + 202)
        cases = [
            [3.0, 0.0, 0.0, 4.0, 0.0, 0.0, 3.0],            # CCW triangle -> 2*area = 12
            [3.0, 0.0, 0.0, 0.0, 3.0, 4.0, 0.0],            # CW triangle -> -12
            [4.0, 0.0, 0.0, 4.0, 0.0, 4.0, 4.0, 0.0, 4.0],  # CCW square -> 32
            [4.0, 0.0, 0.0, 0.0, 4.0, 4.0, 4.0, 4.0, 0.0],  # CW square -> -32
            # out-of-domain -> op fail-softs 0.0 (exercises the guard)
            [2.0, 0.0, 0.0, 1.0, 1.0],                       # n < 3
            [3.0, 0.0, 0.0, 4.0, 0.0, 200000.0, 3.0],        # coord out of range
            [3.0, 0.0, 0.0, 4.0, 0.0, 0.5, 3.0],             # non-integer coord
        ]
        for _ in range(30):                                  # any vertex sequence: shoelace is defined
            n = rng2.randint(3, 8)
            flat = [float(n)]
            for _ in range(n):
                flat += [float(rng2.randint(-500, 500)), float(rng2.randint(-500, 500))]
            cases.append(flat)
        return cases
    if name == "point_in_polygon":
        rng2 = random.Random(seed + 303)
        cases = []
        square = [0, 0, 6, 0, 6, 6, 0, 6]
        for (px, py) in [(3, 3), (1, 1), (5, 5), (10, 3), (-2, 3), (3, 10)]:
            cases.append([float(px), float(py), 4.0] + [float(v) for v in square])
        tri = [0, 0, 8, 0, 4, 6]
        for (px, py) in [(4, 2), (1, 1), (4, 5), (7, 5), (-1, -1)]:
            cases.append([float(px), float(py), 3.0] + [float(v) for v in tri])
        lshape = [0, 0, 6, 0, 6, 2, 2, 2, 2, 6, 0, 6]        # concave 'L'
        for (px, py) in [(1, 1), (4, 1), (1, 4), (4, 4), (3, 5)]:
            cases.append([float(px), float(py), 6.0] + [float(v) for v in lshape])
        try:                                                 # random convex polygons (scipy hull)
            from scipy.spatial import ConvexHull
            for _ in range(20):
                pool = list(dict.fromkeys(
                    (rng2.randint(-40, 40), rng2.randint(-40, 40)) for _ in range(rng2.randint(6, 12))))
                if len(pool) < 3:
                    continue
                try:
                    verts = [pool[i] for i in ConvexHull(pool).vertices]     # CCW hull vertices
                except Exception:  # noqa: BLE001, S112 - degenerate point sets are expected; skip
                    continue
                if len(verts) < 3:
                    continue
                xs = [v[0] for v in verts]
                ys = [v[1] for v in verts]
                for _ in range(3):
                    px, py = rng2.randint(-50, 50), rng2.randint(-50, 50)
                    if _on_boundary(px, py, xs, ys):
                        continue                             # skip boundary (implementation-defined)
                    cases.append([float(px), float(py), float(len(verts))]
                                 + [float(c) for v in verts for c in v])
        except ImportError:
            pass
        cases += [                                           # out-of-domain -> fail-soft 0.0
            [1.0, 1.0, 2.0, 0.0, 0.0, 5.0, 5.0],             # n < 3
            [1.5, 1.0, 3.0] + [float(v) for v in tri],       # non-integer query point
            [1.0, 1.0, 3.0, 0.0, 0.0, 200000.0, 0.0, 4.0, 6.0],  # coord out of range
        ]
        return cases
    if name == "convex_hull":
        rng2 = random.Random(seed + 404)
        cases = [
            [4.0, 0, 0, 4, 0, 4, 4, 0, 4],                   # square (all 4 corners)
            [5.0, 0, 0, 2, 0, 4, 0, 4, 4, 0, 4],             # square + collinear midpoint (excluded)
            [5.0, 0, 0, 4, 0, 4, 4, 0, 4, 2, 2],             # square + interior point (excluded)
            [3.0, 0, 0, 4, 0, 2, 3],                         # triangle
            [3.0, 0, 0, 1, 1, 2, 2],                         # collinear -> degenerate []
            [3.0, 5, 5, 5, 5, 5, 5],                         # all identical (< 3 distinct) -> []
            [2.0, 0, 0, 1, 1],                               # n < 3 -> []
            [3.0, 0, 0, 4, 0, 200000, 3],                    # coord out of range -> []
            [3.0, 0, 0, 4, 0, 0.5, 3],                       # non-integer -> []
        ]
        for _ in range(30):                                  # random point sets
            n = rng2.randint(3, 15)
            flat = [float(n)]
            for _ in range(n):
                flat += [float(rng2.randint(-100, 100)), float(rng2.randint(-100, 100))]
            cases.append(flat)
        for _ in range(6):                                   # duplicate-heavy / small range (ties, collinear)
            n = rng2.randint(4, 12)
            flat = [float(n)]
            for _ in range(n):
                flat += [float(rng2.randint(-3, 3)), float(rng2.randint(-3, 3))]
            cases.append(flat)
        return cases
    if name == "segments_intersect":
        rng2 = random.Random(seed + 505)
        cases = [
            [0, 0, 4, 4, 0, 4, 4, 0],                        # X crossing -> 1
            [0, 0, 4, 0, 0, 1, 4, 1],                        # parallel disjoint -> 0
            [0, 0, 4, 0, 2, 0, 6, 0],                        # collinear overlap -> 1
            [0, 0, 1, 0, 2, 0, 3, 0],                        # collinear disjoint -> 0
            [0, 0, 2, 0, 2, 0, 2, 2],                        # T-junction endpoint -> 1
            [0, 0, 4, 0, 2, 1, 2, 3],                        # near miss -> 0
            [0, 0, 3, 3, 3, 3, 5, 0],                        # shared endpoint -> 1
            # each on-segment special case as the SOLE reason for a 1.0 (an endpoint strictly INTERIOR
            # to the other segment, no shared endpoint, no proper crossing) — so dropping any one of the
            # four collinear branches flips a holdout verdict and the gate can falsify it (review 2026-08-17):
            [3, 0, 3, 5, 0, 0, 10, 0],                       # A-endpoint 1 on B interior -> d1
            [3, 5, 3, 0, 0, 0, 10, 0],                       # A-endpoint 2 on B interior -> d2
            [0, 0, 10, 0, 3, 0, 3, 5],                       # B-endpoint 1 on A interior -> d3
            [0, 0, 10, 0, 3, 5, 3, 0],                       # B-endpoint 2 on A interior -> d4
            [3, 3, 3, 8, 0, 0, 6, 6],                        # diagonal: A-endpoint on B interior -> d1
            [0, 0, 6, 6, 3, 3, 8, 3],                        # diagonal: B-endpoint on A interior -> d3
            [0, 0, 4, 4, 0, 4, 4],                           # < 8 values -> fail-soft 0.0
            [0, 0, 4, 4, 0, 4, 200000, 0],                   # coord out of range -> 0.0
            [0, 0, 4, 4, 0, 4, 4, 0.5],                      # non-integer -> 0.0
        ]
        for _ in range(40):                                  # small coord range -> many crossings/misses
            while True:
                p = [rng2.randint(-6, 6) for _ in range(8)]
                if (p[0], p[1]) != (p[2], p[3]) and (p[4], p[5]) != (p[6], p[7]):
                    break                                    # non-degenerate segments (sympy needs both)
            cases.append([float(v) for v in p])
        return cases
    if name == "binary_search":
        rng2 = random.Random(seed + 606)
        cases = [
            [3.0, 1, 2, 3, 4, 5],                            # present -> 2
            [2.0, 1, 2, 2, 2, 3],                            # first of duplicates -> 1
            [9.0, 1, 2, 3],                                  # absent (above) -> -1
            [5.0],                                           # empty sequence -> -1
            [1.0, 1, 2, 3],                                  # first element -> 0
            [3.0, 1, 2, 3],                                  # last element -> 2
            [0.0, 1, 2, 3],                                  # below all -> -1
        ]
        for _ in range(30):
            n = rng2.randint(0, 30)
            seq = sorted(float(rng2.randint(-20, 20)) for _ in range(n))
            cases.append([float(rng2.randint(-22, 22))] + seq)   # present or not
        for _ in range(6):                                   # float values (sorted), target present
            seq = sorted(rng2.uniform(-50.0, 50.0) for _ in range(rng2.randint(1, 15)))
            cases.append([rng2.choice(seq)] + seq)
        return cases
    if name == "kth_smallest":
        rng2 = random.Random(seed + 707)
        cases = [
            [0.0, 5, 3, 1, 4, 2],                            # min -> 1
            [2.0, 5, 3, 1, 4, 2],                            # median -> 3
            [4.0, 5, 3, 1, 4, 2],                            # max -> 5
            [0.0, 7, 7, 7],                                  # all equal -> 7
            [9.0, 1, 2, 3],                                  # k out of range -> 0.0
            [1.5, 1, 2, 3],                                  # non-integer k -> 0.0
            [0.0],                                           # empty -> 0.0
        ]
        for _ in range(30):
            n = rng2.randint(1, 30)
            cases.append([float(rng2.randint(0, n - 1))]
                         + [float(rng2.randint(-30, 30)) for _ in range(n)])
        for _ in range(8):                                   # duplicate-heavy / small alphabet
            n = rng2.randint(1, 20)
            cases.append([float(rng2.randint(0, n - 1))]
                         + [float(rng2.randint(0, 3)) for _ in range(n)])
        return cases
    if name in ("count_distinct", "mode_value"):
        rng2 = random.Random(seed + 808)
        cases: list[list[float]] = [
            [],                                              # empty -> 0.0
            [5.0],                                           # single
            [3.0, 3.0, 3.0],                                 # all equal
            [1.0, 2.0, 3.0, 4.0],                            # all distinct
            [1.0, 1.0, 2.0, 3.0, 3.0, 3.0],                  # a clear mode (3)
            [2.0, 2.0, 1.0, 1.0],                            # tie -> mode picks the smallest (1)
            [0.0, -0.0, 0.0],                                # +0/-0 compare equal -> 1 distinct
            # -0.0 NOT last in the equal run: falsifies dropping mode_value's +0.0 canonicalization
            # (Python stable sort vs an unstable qsort would return a different zero sign; include both
            # orderings so at least one diverges regardless of the qsort tie order). Review 2026-08-17.
            [0.0, -0.0],
            [-0.0, 0.0],
        ]
        for _ in range(30):
            n = rng2.randint(0, 25)
            cases.append([float(rng2.randint(0, 5)) for _ in range(n)])   # small alphabet -> ties
        for _ in range(6):
            n = rng2.randint(1, 15)
            cases.append([rng2.uniform(-50.0, 50.0) for _ in range(n)])   # mostly-distinct floats
        return cases
    if name == "is_prime":
        rng2 = random.Random(seed + 909)
        cases = [[float(n)] for n in
                 (0, 1, 2, 3, 4, 5, 17, 97, 100, 561, 1105, 1729, 2465, 7919,   # incl Carmichael numbers
                  104729, 4294967291, 4294967295)]                              # large prime / 2^32-1
        for _ in range(40):
            cases.append([float(rng2.randint(0, 200000))])
        for _ in range(10):
            cases.append([float(rng2.randint(4000000000, 4294967295))])         # near 2^32
        cases += [[float("nan")], [-3.0], [1.5], [5e9]]                         # out-of-domain -> 0.0
        return cases
    if name == "modular_inverse":
        rng2 = random.Random(seed + 1010)
        cases = [
            [3.0, 11.0], [10.0, 17.0], [123456.0, 1000000007.0],               # coprime -> inverse
            [6.0, 9.0], [4.0, 8.0], [10.0, 15.0],                              # gcd != 1 -> -1.0
            [0.0, 5.0], [7.0, 1.0], [1.0, 7.0], [2.0, 4.0],                    # edges (a=0, m=1)
            # 2^53-domain-edge cases: exercise the wide-integer Bezout arithmetic (|q*s| ~ 2m ~ 2^54)
            # so a long-long->int width narrowing of the C mirror is FALSIFIED by the gate, matching the
            # pow_mod / gcd_seq discipline (review 2026-08-17):
            [2.0, 9007199254740991.0],                                        # a=2, m=2^53-1 (coprime) -> inverse
            [9007199254740891.0, 9007199254740992.0],                         # large coprime near 2^53
            [4503599627370496.0, 9007199254740992.0],                         # both even (gcd 2^52) -> -1.0
            [3.0], [3.0, 0.0], [2.5, 7.0], [3.0, 1e16], [-1.0, 7.0],           # out-of-domain -> -1.0
        ]
        for _ in range(40):
            cases.append([float(rng2.randint(0, 100000)), float(rng2.randint(1, 100000))])
        return cases
    if name == "extended_gcd":
        rng2 = random.Random(seed + 1212)
        cases = [
            [35.0, 15.0], [240.0, 46.0], [17.0, 5.0], [1071.0, 462.0],          # ordinary coprime / non-coprime
            [7.0, 7.0],                                                          # equal -> (7, 0, 1)
            [0.0, 5.0], [5.0, 0.0], [0.0, 0.0],                                  # zero edges -> (b,0,1)/(a,1,0)/(0,1,0)
            [1.0, 1.0], [1.0, 999983.0],                                         # a=1 (coprime, x=1)
            # 2^53-domain-edge cases: the Bezout coefficients (|q*s| ~ 2*max ~ 2^54) exercise the WIDE
            # long-long arithmetic in the C mirror, so a long-long->int narrowing is FALSIFIED (P10 lesson):
            [2.0, 9007199254740991.0],                                          # a=2, b=2^53-1 (coprime)
            [9007199254740891.0, 9007199254740992.0],                           # large coprime near 2^53
            [4503599627370496.0, 9007199254740992.0],                           # 2^52 and 2^53 -> gcd 2^52
            [9007199254740992.0, 6.0],                                          # a=2^53 (inclusive upper edge)
            # out-of-domain -> [] fail-soft: short / >2^53 / non-int / negative / NaN.
            # BOTH operands' guard clauses must be driven as a SOLE reason (a/b guards are copy-paste
            # symmetric, so a one-sided b regression is plausible; review 2026-08-17 CONFIRMED the
            # b-guard was unfalsifiable when only a-side bad cases existed). a-side bad:
            [3.0], [9007199254740994.0, 3.0], [2.5, 7.0], [-1.0, 7.0], [7.0, float("nan")],
            # b-side bad (valid a, finite out-of-domain b) — each isolates one b-guard clause:
            [3.0, 9007199254740994.0],       # b > 2^53 (drives bd <= 2^53: a coefficient > 2^53 would
                                             #           lose float64 exactness -> a*x+b*y != g)
            [7.0, -1.0],                     # b < 0     (drives bd >= 0.0)
            [7.0, 2.5],                      # b non-integer (drives bd == (long long)bd)
        ]
        for _ in range(40):
            cases.append([float(rng2.randint(0, 200000)), float(rng2.randint(0, 200000))])
        for _ in range(8):                                                       # near the 2^53 edge
            cases.append([float(rng2.randint(0, 9007199254740992)),
                          float(rng2.randint(0, 9007199254740992))])
        return cases
    if name in ("xor_reduce", "popcount_total"):
        rng2 = random.Random(seed + 1111)
        cases: list[list[float]] = [
            [],                                              # empty -> 0
            [0.0], [255.0], [7.0, 3.0, 1.0],
            [9007199254740991.0],                            # 2^53 - 1 (all 53 bits set)
            [9007199254740991.0, 9007199254740991.0],        # xor -> 0; popcount -> 106
            [1099511627776.0, 1.0],                          # 2^40 + 1
            # out-of-domain -> fail-soft 0.0
            [-1.0], [1.5], [float("nan")], [9007199254740992.0],  # -1 / non-int / NaN / 2^53
        ]
        for _ in range(30):
            n = rng2.randint(0, 20)
            cases.append([float(rng2.randint(0, 2 ** 40)) for _ in range(n)])
        for _ in range(6):                                   # near the 53-bit edge
            n = rng2.randint(1, 8)
            cases.append([float(rng2.randint(0, 9007199254740991)) for _ in range(n)])
        return cases
    return make_holdout(seed)


def py_oracle_error(op: algo.AlgoOp, holdout: list[list[float]], py_out: list) -> float:
    """Max error of the Python reference vs an INDEPENDENT oracle (fail-closed)."""
    name = op.name
    if name == "simpson":
        from scipy import integrate
        errs = []
        for arr, got in zip(holdout, py_out):
            m = len(arr) - 1                          # sample count
            if m < 3 or m % 2 == 0:
                continue                              # even m: scipy's tail convention differs
                #        from our trapezoid tail -> not an independent oracle here.
                #        The C-vs-Python bit check still covers the even-m branch.
            ref = float(integrate.simpson(np.asarray(arr[1:], np.float64), dx=arr[0]))
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name in ("bisection", "newton"):
        # independent check: the returned value must actually be a root -> |p(x)| ~ 0
        errs = []
        for arr, got in zip(holdout, py_out):
            coeffs = arr[2:] if name == "bisection" else arr[1:]
            errs.append(_diff01(_poly_at(coeffs, float(got)), 0.0))
        return max(errs, default=0.0)
    if name == "gauss_solve":
        # independent oracle: numpy's LAPACK solve (a different partial-pivot LU).
        # Both are backward-stable, so on a well-conditioned holdout they agree to
        # ~1e-13; compare element-wise IN ORDER. Fail-closed on a structural mismatch
        # or a singular holdout row (LinAlgError -> inf, never tolerance-gated).
        errs = []
        for arr, got in zip(holdout, py_out):
            n = int(arr[0])
            w = n + 1
            aug = np.asarray(arr[1:1 + n * w], np.float64).reshape(n, w)
            try:
                ref = np.linalg.solve(aug[:, :n], aug[:, n]).tolist()
            except np.linalg.LinAlgError:
                return float("inf")                  # singular holdout = a holdout bug
            if len(got) != len(ref):
                return float("inf")
            for x, y in zip(got, ref):
                errs.append(_diff01(float(x), float(y)))
        return max(errs, default=0.0)
    if name == "strfind":
        # independent oracle: a NAIVE all-occurrences scan (no failure function) vs KMP.
        errs = []
        for arr, got in zip(holdout, py_out):
            m = int(arr[0])
            pat, text = arr[1:1 + m], arr[1 + m:]
            naive = [float(i) for i in range(len(text) - m + 1) if text[i:i + m] == pat]
            if len(got) != len(naive):
                return float("inf")
            for x, y in zip(got, naive):
                errs.append(_diff01(float(x), float(y)))
        return max(errs, default=0.0)
    if name in ("edit_distance", "lcs_length"):
        oracle_fn = _lev_recursive if name == "edit_distance" else _lcs_recursive
        errs = []
        for arr, got in zip(holdout, py_out):
            na = int(arr[0])
            ref = oracle_fn(tuple(arr[1:1 + na]), tuple(arr[1 + na:]))
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name in ("graph_components", "graph_mst_weight", "graph_dijkstra"):
        # INDEPENDENT oracle: scipy.sparse.csgraph (a different implementation entirely).
        from scipy.sparse import csgraph as _csg
        from scipy.sparse import csr_matrix
        base = 3 if name == "graph_dijkstra" else 2
        errs = []
        for arr, got in zip(holdout, py_out):
            n, m = int(arr[0]), int(arr[1])
            rows, cols, data = [], [], []
            for k in range(m):
                u, v = int(arr[base + 3 * k]), int(arr[base + 3 * k + 1])
                w = float(arr[base + 3 * k + 2])
                rows += [u, v]
                cols += [v, u]
                data += [1.0, 1.0] if name == "graph_components" else [w, w]
            mtx = csr_matrix((data, (rows, cols)), shape=(n, n)) if data else csr_matrix((n, n))
            if name == "graph_components":
                ncomp = _csg.connected_components(mtx, directed=False)[0]
                errs.append(_diff01(float(got), float(ncomp)))
            elif name == "graph_mst_weight":
                errs.append(_diff01(float(got), float(_csg.minimum_spanning_tree(mtx).sum())))
            else:  # graph_dijkstra: my op returns -1.0 for unreachable, scipy inf
                d = _csg.dijkstra(mtx, directed=False, indices=int(arr[2]))
                if len(got) != n:
                    return float("inf")
                for i in range(n):
                    reach_g, reach_r = float(got[i]) >= 0.0, math.isfinite(float(d[i]))
                    if reach_g != reach_r:
                        return float("inf")            # disagree on reachability
                    if reach_g:
                        errs.append(_diff01(float(got[i]), float(d[i])))
        return max(errs, default=0.0)
    if name == "gcd_seq":
        # independent oracle: math.gcd (CPython's C-level GCD). Domain-aware: an out-of-domain
        # element (negative / non-integer / > 2^53) mirrors the op's fail-soft 0.0 (also empty).
        errs = []
        for arr, got in zip(holdout, py_out):
            if arr and all(_int_in(x, 0.0, 9007199254740992.0) for x in arr):
                ref = float(math.gcd(*[int(x) for x in arr]))
            else:
                ref = 0.0
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "sieve_primes":
        # independent oracle: per-candidate trial division (a different code path). Domain-aware:
        # n out of [0, 5,000,000] (or a NaN header) mirrors the op's fail-soft []; n is a truncated
        # header (no integrality), so n=int(nd) — matching the op — and n<2 yields [] naturally.
        errs = []
        for arr, got in zip(holdout, py_out):
            if arr and math.isfinite(arr[0]) and 0.0 <= arr[0] <= 5000000.0:
                n = int(arr[0])
                primes = [float(p) for p in range(2, n + 1) if _is_prime_trial(p)]
            else:
                primes = []
            if len(got) != len(primes):
                return float("inf")
            for x, y in zip(got, primes):
                errs.append(_diff01(float(x), float(y)))
        return max(errs, default=0.0)
    if name == "pow_mod":
        # independent oracle: Python's built-in three-arg pow. Domain-aware: short input or a
        # base/exp/mod outside the declared domain mirrors the op's fail-soft 0.0 (and keeps pow()
        # off mod == 0, which would raise).
        errs = []
        for arr, got in zip(holdout, py_out):
            if (len(arr) >= 3 and _int_in(arr[0], 0.0, 9007199254740992.0)
                    and _int_in(arr[1], 0.0, 9007199254740992.0)
                    and _int_in(arr[2], 1.0, 4294967295.0)):
                ref = float(pow(int(arr[0]), int(arr[1]), int(arr[2])))
            else:
                ref = 0.0
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "crc32":
        # independent oracle: zlib.crc32 (the zlib C library). Domain-aware: a non-byte value
        # (out of [0,255] / non-integer / NaN) mirrors the op's fail-soft 0.0 and keeps the bytes()
        # call in range (it raises otherwise). Empty stays crc32(b'') = 0.
        import zlib
        errs = []
        for arr, got in zip(holdout, py_out):
            if all(_int_in(x, 0.0, 255.0) for x in arr):
                ref = float(zlib.crc32(bytes(int(x) for x in arr)) & 0xFFFFFFFF)
            else:
                ref = 0.0
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "rle_encode":
        # independent oracle: itertools.groupby (a different grouping mechanism).
        from itertools import groupby
        errs = []
        for arr, got in zip(holdout, py_out):
            pairs: list[float] = []
            for val, grp in groupby(arr):
                pairs.append(float(val))
                pairs.append(float(sum(1 for _ in grp)))
            if len(got) != len(pairs):
                return float("inf")
            for x, y in zip(got, pairs):
                errs.append(_diff01(float(x), float(y)))
        return max(errs, default=0.0)
    if name == "polygon_area2":
        # independent oracle: a numpy vectorized shoelace (roll + dot), a different code path from
        # the op's scalar C-mirror loop. Domain-aware (out-of-domain / n<3 -> op fail-soft 0.0).
        errs = []
        for arr, got in zip(holdout, py_out):
            ref = 0.0
            if arr and _int_in(arr[0], 3.0, 100000.0) and len(arr) >= 1 + 2 * int(arr[0]):
                n = int(arr[0])
                coords = arr[1:1 + 2 * n]
                if all(_int_in(c, -100000.0, 100000.0) for c in coords):
                    x = np.asarray(coords[0::2], np.float64)
                    y = np.asarray(coords[1::2], np.float64)
                    ref = float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "point_in_polygon":
        # independent oracle: the WINDING-NUMBER algorithm (vs the op's crossing number) — a
        # different method, integer-exact, agreeing at strict interior/exterior of a simple polygon.
        errs = []
        for arr, got in zip(holdout, py_out):
            ref = 0.0
            if (len(arr) >= 3 and _int_in(arr[0], -100000.0, 100000.0)
                    and _int_in(arr[1], -100000.0, 100000.0) and _int_in(arr[2], 3.0, 100000.0)
                    and len(arr) >= 3 + 2 * int(arr[2])):
                n = int(arr[2])
                coords = arr[3:3 + 2 * n]
                if all(_int_in(c, -100000.0, 100000.0) for c in coords):
                    xs = [int(coords[2 * i]) for i in range(n)]
                    ys = [int(coords[2 * i + 1]) for i in range(n)]
                    ref = 1.0 if _winding_number_inside(int(arr[0]), int(arr[1]), xs, ys) else 0.0
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "convex_hull":
        # independent oracle: scipy.spatial.ConvexHull (qhull). Compare the SET of hull vertices
        # (order is enforced separately by the C-vs-Python bit check); a degenerate point set
        # (< 3 distinct / all collinear) raises in qhull and mirrors the op's fail-soft []. The
        # count guard rejects a hull with duplicate vertices. Domain-aware (out-of-domain -> []).
        from scipy.spatial import ConvexHull
        errs = []
        for arr, got in zip(holdout, py_out):
            ref_set: frozenset = frozenset()
            if arr and _int_in(arr[0], 3.0, 100000.0) and len(arr) >= 1 + 2 * int(arr[0]):
                n = int(arr[0])
                coords = arr[1:1 + 2 * n]
                if all(_int_in(c, -100000.0, 100000.0) for c in coords):
                    pts = list({(int(coords[2 * i]), int(coords[2 * i + 1])) for i in range(n)})
                    if len(pts) >= 3:
                        try:
                            ref_set = frozenset(tuple(pts[i]) for i in ConvexHull(pts).vertices)
                        except Exception:  # noqa: BLE001 - qhull raises on collinear/degenerate -> []
                            ref_set = frozenset()
            got_set = frozenset((int(got[2 * i]), int(got[2 * i + 1])) for i in range(len(got) // 2))
            ok = got_set == ref_set and len(got) // 2 == len(ref_set)   # same vertices, no duplicates
            errs.append(0.0 if ok else float("inf"))
        return max(errs, default=0.0)
    if name == "segments_intersect":
        # independent oracle: sympy.geometry (symbolic exact intersection) — a wholly different method
        # from the op's integer orientation tests. Domain-aware: malformed / out-of-domain -> op's 0.0.
        from sympy.geometry import Point, Segment
        errs = []
        for arr, got in zip(holdout, py_out):
            if len(arr) < 8 or not all(_int_in(c, -100000.0, 100000.0) for c in arr[:8]):
                ref = 0.0
            else:
                p = [int(arr[i]) for i in range(8)]
                a_seg = Segment(Point(p[0], p[1]), Point(p[2], p[3]))
                b_seg = Segment(Point(p[4], p[5]), Point(p[6], p[7]))
                ref = 1.0 if a_seg.intersection(b_seg) else 0.0
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "binary_search":
        # independent oracle: Python's bisect_left (a different, C-level lower-bound impl) + a presence
        # check. The holdout sequences are sorted (the op's precondition), so both agree.
        import bisect
        errs = []
        for arr, got in zip(holdout, py_out):
            if not arr:
                ref = -1.0
            else:
                target = arr[0]
                seq = arr[1:]
                i = bisect.bisect_left(seq, target)
                ref = float(i) if (i < len(seq) and seq[i] == target) else -1.0
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "kth_smallest":
        # independent oracle: full sort then index (Timsort, a different algorithm from quickselect).
        # Domain-aware: k out of [0, n-1] / non-integer / empty -> the op's fail-soft 0.0.
        errs = []
        for arr, got in zip(holdout, py_out):
            ref = 0.0
            if len(arr) >= 2:
                n = len(arr) - 1
                if _int_in(arr[0], 0.0, float(n - 1)):
                    ref = float(sorted(arr[1:])[int(arr[0])])
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "count_distinct":
        # independent oracle: len(set(...)) (a hash set, a different mechanism from sort+scan).
        errs = []
        for arr, got in zip(holdout, py_out):
            errs.append(_diff01(float(got), float(len(set(arr)))))
        return max(errs, default=0.0)
    if name == "mode_value":
        # independent oracle: collections.Counter, smallest value winning ties.
        from collections import Counter
        errs = []
        for arr, got in zip(holdout, py_out):
            if not arr:
                ref = 0.0
            else:
                counts = Counter(arr)
                top = max(counts.values())
                ref = float(min(v for v, c in counts.items() if c == top))
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "is_prime":
        # independent oracle: sympy.isprime (a full, different primality implementation).
        from sympy import isprime
        errs = []
        for arr, got in zip(holdout, py_out):
            ref = 1.0 if (arr and _int_in(arr[0], 0.0, 4294967295.0) and isprime(int(arr[0]))) else 0.0
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "modular_inverse":
        # independent oracle: Python's built-in three-arg pow(a, -1, m) (a different, C-level impl).
        errs = []
        for arr, got in zip(holdout, py_out):
            ref = -1.0
            if (len(arr) >= 2 and _int_in(arr[0], 0.0, 9007199254740992.0)
                    and _int_in(arr[1], 1.0, 9007199254740992.0)):
                m = int(arr[1])
                if m == 1:
                    ref = 0.0
                else:
                    try:
                        ref = float(pow(int(arr[0]), -1, m))
                    except ValueError:
                        ref = -1.0
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name in ("xor_reduce", "popcount_total"):
        # independent oracles: functools.reduce(xor) / sum(bin(x).count('1')). Domain-aware (a negative
        # / non-integer / >= 2^53 value -> the op's fail-soft 0.0).
        import functools
        import operator
        errs = []
        for arr, got in zip(holdout, py_out):
            if all(_int_in(x, 0.0, 9007199254740991.0) for x in arr):
                ints = [int(x) for x in arr]
                if name == "xor_reduce":
                    ref = float(functools.reduce(operator.xor, ints, 0))
                else:
                    ref = float(sum(v.bit_count() for v in ints))    # builtin popcount, independent of Kernighan
            else:
                ref = 0.0
            errs.append(_diff01(float(got), ref))
        return max(errs, default=0.0)
    if name == "extended_gcd":
        # independent oracle: the RECURSIVE extended Euclid (_ext_gcd_rec), element-wise (g,x,y).
        # Domain-aware: len<2 or a value outside [0, 2^53] / non-integer -> the op's [] fail-soft.
        # A structural mismatch (wrong output length) is fail-closed inf, never tol-gated.
        vec_errs: list[float] = []
        for arr, got in zip(holdout, py_out):
            if len(arr) >= 2 and all(_int_in(x, 0.0, 9007199254740992.0) for x in arr[:2]):
                g, x, y = _ext_gcd_rec(int(arr[0]), int(arr[1]))
                bezout: list[float] = [float(g), float(x), float(y)]
            else:
                bezout = []
            got_list = got if isinstance(got, list) else [got]
            if len(got_list) != len(bezout):
                return float("inf")                              # structural: fail-closed
            vec_errs.extend(_diff01(float(gv), float(rv)) for gv, rv in zip(got_list, bezout))
        return max(vec_errs, default=0.0)
    oracle = [_oracle(op, arr) for arr in holdout]
    if op.kind == algo.KIND_SORT:
        return _max_diff_sort(oracle, py_out)
    return _max_diff_scalar(oracle, py_out)


# --------------------------------------------------------------------------- #
# oracle / backends
# --------------------------------------------------------------------------- #
def _oracle(op: algo.AlgoOp, arr: list[float]):
    a = np.asarray(arr, np.float64)
    if op.kind == algo.KIND_SORT:
        return np.sort(a, kind="stable").tolist()
    if op.name == "seq_max":
        return float(a.max()) if a.size else 0.0
    if op.name == "seq_min":
        return float(a.min()) if a.size else 0.0
    raise ValueError(f"no oracle for op {op.name!r}")


def _diff01(x: float, y: float) -> float:
    """abs(x-y), but **inf** if either value is non-finite — so a NaN/inf can never
    silently fold to 0.0 (``max(0.0, nan)`` is 0.0 in Python). Fail-closed."""
    if not (math.isfinite(x) and math.isfinite(y)):
        return float("inf")
    return abs(x - y)


def _max_diff_sort(ref: list[list[float]], got: list[list[float]]) -> float:
    if len(ref) != len(got):
        return float("inf")                      # structural mismatch — never tol-gated
    d = 0.0
    for r, g in zip(ref, got):
        if len(r) != len(g):
            return float("inf")
        for x, y in zip(r, g):
            d = max(d, _diff01(float(x), float(y)))
    return d


def _max_diff_scalar(ref: list[float], got: list[float]) -> float:
    if len(ref) != len(got):
        return float("inf")
    return max((_diff01(float(x), float(y)) for x, y in zip(ref, got)), default=0.0)


def _bits_equal_sort(ref: list[list[float]], got: list[list[float]]) -> bool:
    """True iff every output array is **byte-identical** as IEEE-754 float64 — the
    real bit-for-bit check (catches NaN payloads and +0.0 vs -0.0, which an
    abs-diff of 0.0 would miss). C and Python run the same algorithm, so a correct
    backend is byte-identical."""
    if len(ref) != len(got):
        return False
    for r, g in zip(ref, got):
        ra, ga = np.asarray(r, np.float64), np.asarray(g, np.float64)
        if ra.shape != ga.shape or ra.tobytes() != ga.tobytes():
            return False
    return True


def _bits_equal_scalar(ref: list[float], got: list[float]) -> bool:
    if len(ref) != len(got):
        return False
    return np.asarray(ref, np.float64).tobytes() == np.asarray(got, np.float64).tobytes()


# --- binary I/O (must mirror algo_codegen._driver_c exactly) ----------------- #
def _write_input(path: Path, holdout: list[list[float]]) -> None:
    with open(path, "wb") as f:
        np.array([len(holdout)], np.int32).tofile(f)
        for arr in holdout:
            np.array([len(arr)], np.int32).tofile(f)
            if arr:
                np.asarray(arr, np.float64).tofile(f)


def _read_output(path: Path, kind: str):
    with open(path, "rb") as f:
        n = int(np.fromfile(f, np.int32, 1)[0])
        # SEQ-producing kinds (sort in place, variable-length map) write per-array
        # {int32 len, len * float64}; a reduction writes n_arrays flat float64s.
        if kind in (algo.KIND_SORT, algo.KIND_MAP):
            out = []
            for _ in range(n):
                length = int(np.fromfile(f, np.int32, 1)[0])
                out.append(np.fromfile(f, np.float64, length).tolist())
            return out
        return np.fromfile(f, np.float64, n).tolist()


def run_c_backend(op, holdout, wd: Path, cc: list[str]) -> dict:
    """Compile + run the codegen C on ``holdout``; return its outputs and status."""
    wd = Path(wd)
    c_path = wd / f"gen_{op.name}.c"
    c_path.write_text(algo_codegen.emit_c(op), encoding="utf-8")
    exe = wd / (f"algo_{op.name}.exe" if sys.platform == "win32" else f"algo_{op.name}")
    try:
        # -ffp-contract=off: forbid FMA contraction so the C does the SAME separate
        # mul+add the Python reference does -> numeric ops stay bit-identical.
        subprocess.run(cc + ["-O2", "-std=c99", "-ffp-contract=off", str(c_path), "-o", str(exe)],
                       check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        return {"status": "compile_error", "detail": (e.stderr or str(e))[-500:]}
    fin, fout = wd / f"in_{op.name}.bin", wd / f"out_{op.name}.bin"
    _write_input(fin, holdout)
    try:
        subprocess.run([str(exe), str(fin), str(fout)], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        return {"status": "run_error", "detail": (e.stderr or str(e))[-500:]}
    return {"status": "ran", "outputs": _read_output(fout, op.kind)}


# --------------------------------------------------------------------------- #
# gate
# --------------------------------------------------------------------------- #
def _c_gate_ok(cb: dict) -> bool:
    """C half, fail-closed: an emitted C backend that fails to build or run is a
    FAILURE (these ops always declare full C support); only 'skipped' stays neutral."""
    status = cb.get("status")
    if status == "ran":
        return bool(cb.get("pass"))
    # 'skipped' = neutral (no toolchain); compile_error / run_error = fail-closed
    return status == "skipped"


def difftest(name: str, wd: Path, seed: int = 0, tol: float = 0.0,
             cc: list[str] | None = "auto") -> dict:
    """Run both halves of the gate for op ``name``; return the result dict.

    ``tol`` defaults to 0.0 — these ops move / select existing doubles, so a
    correct backend agrees to the bit. ``cc="auto"`` auto-discovers a compiler;
    pass an explicit argv list, or ``None`` to force the honest skip.
    """
    op = algo.ALGO_BY_NAME[name]
    wd = Path(wd)
    wd.mkdir(parents=True, exist_ok=True)
    if cc == "auto":
        cc = find_c_compiler()

    holdout = holdout_for(name, seed)
    ref = algo.py_fn(name)
    py_out = [ref([float(x) for x in arr]) for arr in holdout]

    # Python vs oracle: an INDEPENDENT reference (np.sort / np.max / np.min for
    # sorts/reductions; scipy.integrate.simpson for Simpson; the residual |p(root)|
    # for the root finders). Fail-closed: a non-finite / structural error yields inf,
    # never tol-gated. Numeric ops accumulate, so they use the op's own tolerance
    # while sorts/reductions stay exact (op.tol == 0.0).
    py_vs_oracle = py_oracle_error(op, holdout, py_out)
    otol = max(tol, op.tol)
    python_pass = math.isfinite(py_vs_oracle) and py_vs_oracle <= otol

    result = {
        "op": name, "kind": op.kind, "provenance": op.provenance,
        "n_cases": len(holdout), "tol": otol,
        "python_max_abs_diff": py_vs_oracle, "python_pass": python_pass,
        "compiler": compiler_label(cc), "c_verified": False, "c_backend": None,
    }

    if cc is None:
        result["c_backend"] = {"status": "skipped",
                               "reason": "no C toolchain (gcc/clang or 'pip install ziglang')"}
    else:
        cb = run_c_backend(op, holdout, wd, cc)
        if cb["status"] == "ran":
            # C vs Python: true BIT-for-bit (pass criterion) + abs diff for the report.
            # Key on out_sort: any SEQ-producing op (sort or variable-length map) is
            # compared per-array (the helpers already handle differing array lengths).
            if op.out_sort == algo.SEQ:
                bit_ok = _bits_equal_sort(py_out, cb["outputs"])
                c_diff = _max_diff_sort(py_out, cb["outputs"])
            else:
                bit_ok = _bits_equal_scalar(py_out, cb["outputs"])
                c_diff = _max_diff_scalar(py_out, cb["outputs"])
            cb = {"status": "ran", "c_vs_python_max_abs_diff": c_diff,
                  "c_vs_python_bit_identical": bit_ok, "pass": bit_ok}
        result["c_backend"] = cb

    # c_verified = the C artifact was actually compiled, run and bit-compared here
    # (a 'skipped' pass is honest but UNVERIFIED — surfaced so CI can require it).
    result["c_verified"] = result["c_backend"].get("status") == "ran"
    result["passed"] = bool(python_pass and _c_gate_ok(result["c_backend"]))
    (wd / f"algo_difftest_{name}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--op", default="all", choices=algo.algo_names() + ["all"])
    ap.add_argument("--workdir", default="out/algo")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tol", type=float, default=0.0)
    ap.add_argument("--no-c", action="store_true", help="force the honest C skip")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    cc = None if a.no_c else "auto"
    names = algo.algo_names() if a.op == "all" else [a.op]
    results = [difftest(n, Path(a.workdir), seed=a.seed, tol=a.tol, cc=cc) for n in names]
    all_pass = all(r["passed"] for r in results)
    if a.out:
        p = a.out if a.out.endswith(".json") else a.out + ".json"
        Path(p).write_text(json.dumps(results, indent=2), encoding="utf-8")
    for r in results:
        cb = r["c_backend"]
        extra = (f" C {cb['status']}"
                 + (f" diff={cb.get('c_vs_python_max_abs_diff'):.2e}" if cb.get("status") == "ran" else "")
                 + (f" reason={cb.get('reason')}" if cb.get("reason") else ""))
        print(f"[algo_difftest:{r['op']}] python diff {r['python_max_abs_diff']:.2e} "
              f"(pass={r['python_pass']}) |{extra} | compiler={r['compiler']} -> passed={r['passed']}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
