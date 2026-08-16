"""algo_difftest — the honest-correctness gate for the general-algorithm tier.

Two independent checks, both real measurements (not deferred skips) whenever a C
toolchain is present:

  Python vs oracle : the Python reference (``algo.py_fn``) is compared to a
                     ground-truth oracle — ``numpy.sort`` for sorts, ``numpy.max`` /
                     ``numpy.min`` for reductions. These reorder / select the same
                     values regardless of algorithm, so a correct reference must
                     agree EXACTLY. Catches a wrong reimplementation.
  C vs Python      : the codegen C (``algo_codegen.emit_c``) is compiled and run on
                     the same holdout, then compared **bit-for-bit** to the Python
                     reference. Catches a codegen / C-reimplementation bug. Because
                     these ops only move or select existing IEEE-754 doubles, a
                     correct C backend agrees to the bit (max abs diff 0.0).

C toolchain: ``gcc`` / ``cc`` / ``clang`` on PATH, else ``python -m ziglang cc``
(the pip-installable, self-contained clang). If none is found the C half SKIPs
with an honest reason; a compile/run FAILURE is a gate failure, never a skip
(fail-closed, matching image ``difftest.py``).

Deterministic. Writes ``algo_difftest_<op>.json``.
"""
from __future__ import annotations

import argparse
import json
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
    except Exception:
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
    ]
    for _ in range(n_random):
        n = rng.randint(0, max_len)
        cases.append([rng.uniform(-1000.0, 1000.0) for _ in range(n)])
    return cases


# --------------------------------------------------------------------------- #
# oracle / backends
# --------------------------------------------------------------------------- #
def _oracle(op: "algo.AlgoOp", arr: list[float]):
    a = np.asarray(arr, np.float64)
    if op.kind == algo.KIND_SORT:
        return np.sort(a, kind="stable").tolist()
    if op.name == "seq_max":
        return float(a.max()) if a.size else 0.0
    if op.name == "seq_min":
        return float(a.min()) if a.size else 0.0
    raise ValueError(f"no oracle for op {op.name!r}")


def _max_diff_sort(ref: list[list[float]], got: list[list[float]]) -> float:
    if len(ref) != len(got):
        return float("inf")
    d = 0.0
    for r, g in zip(ref, got):
        if len(r) != len(g):
            return float("inf")
        for x, y in zip(r, g):
            d = max(d, abs(float(x) - float(y)))
    return d


def _max_diff_scalar(ref: list[float], got: list[float]) -> float:
    if len(ref) != len(got):
        return float("inf")
    return max((abs(float(x) - float(y)) for x, y in zip(ref, got)), default=0.0)


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
        if kind == algo.KIND_SORT:
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
        subprocess.run(cc + ["-O2", "-std=c99", str(c_path), "-o", str(exe)],
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
    if status == "skipped":
        return True
    return False                              # compile_error / run_error -> fail


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

    holdout = make_holdout(seed)
    ref = algo.py_fn(name)
    py_out = [ref([float(x) for x in arr]) for arr in holdout]
    oracle = [_oracle(op, arr) for arr in holdout]

    if op.kind == algo.KIND_SORT:
        py_vs_oracle = _max_diff_sort(oracle, py_out)
    else:
        py_vs_oracle = _max_diff_scalar(oracle, py_out)
    python_pass = py_vs_oracle <= tol

    result = {
        "op": name, "kind": op.kind, "provenance": op.provenance,
        "n_cases": len(holdout), "tol": tol,
        "python_max_abs_diff": py_vs_oracle, "python_pass": python_pass,
        "compiler": compiler_label(cc), "c_backend": None,
    }

    if cc is None:
        result["c_backend"] = {"status": "skipped",
                               "reason": "no C toolchain (gcc/clang or 'pip install ziglang')"}
    else:
        cb = run_c_backend(op, holdout, wd, cc)
        if cb["status"] == "ran":
            if op.kind == algo.KIND_SORT:
                c_diff = _max_diff_sort(py_out, cb["outputs"])
            else:
                c_diff = _max_diff_scalar(py_out, cb["outputs"])
            cb = {"status": "ran", "c_vs_python_max_abs_diff": c_diff, "pass": c_diff <= tol}
        result["c_backend"] = cb

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
