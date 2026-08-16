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
    from functools import lru_cache

    @lru_cache(maxsize=None)
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
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def c(i: int, j: int) -> int:
        if i == 0 or j == 0:
            return 0
        if a[i - 1] == b[j - 1]:
            return c(i - 1, j - 1) + 1
        return max(c(i - 1, j), c(i, j - 1))

    return float(c(len(a), len(b)))


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
