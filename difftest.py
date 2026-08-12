"""S2 — differential test across backends (the honest-correctness gate).

Verifies the emitted backends reproduce the typed-IR reference on holdout inputs:

  Python backend : ALWAYS run. import gen_<problem>.py, apply pipeline() to each
                   holdout image, compare to ops.apply_genome(champion) -> max abs
                   diff. PASS if < --tol.
  C backend      : run ONLY if a C compiler is found AND every op is in the C
                   runtime. Compile imgops.c + gen_<problem>.c + a generated driver,
                   run on the same inputs, compare to Python. Otherwise SKIP with an
                   honest reason (this environment has no gcc — verification deferred).

Writes difftest_<problem>.json + report line. Deterministic.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

import ops
import problems

_DRIVER_C = r"""
#include "imgops.h"
#include <stdio.h>
#include <stdlib.h>
void pipeline(float* buf, int w, int h);
int main(int argc, char** argv) {
    FILE* fi = fopen(argv[1], "rb"); FILE* fo = fopen(argv[2], "wb");
    int n, w, h; fread(&n, 4, 1, fi); fread(&w, 4, 1, fi); fread(&h, 4, 1, fi);
    float* img = (float*)malloc(sizeof(float) * w * h);
    for (int k = 0; k < n; k++) { fread(img, 4, w*h, fi); pipeline(img, w, h); fwrite(img, 4, w*h, fo); }
    free(img); fclose(fi); fclose(fo); return 0;
}
"""


def _import_gen(path: Path):
    spec = importlib.util.spec_from_file_location("gen_pipeline", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _maxdiff(ref, got):
    """Max abs difference between two pipeline outputs. Handles array (image/
    region) and scalar (feature) finals; returns nan for non-numeric finals (a
    contour dict), which are recorded as non-comparable rather than silently passed."""
    if isinstance(ref, np.ndarray) and isinstance(got, np.ndarray):
        return float("inf") if ref.shape != got.shape else float(np.max(np.abs(ref - got)))
    try:
        return abs(float(ref) - float(got))
    except (TypeError, ValueError):
        return float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--problem", default="edge")
    ap.add_argument("--workdir", default="out/worklog/imgevolve")
    ap.add_argument("--tol", type=float, default=1e-6)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    wd = Path(a.workdir)
    champ = json.loads((wd / f"champion_{a.problem}.json").read_text(encoding="utf-8"))
    info = json.loads((wd / f"codegen_{a.problem}.json").read_text(encoding="utf-8"))
    cfg = champ["config"]
    prob = problems.PROBLEMS[a.problem]
    ho = prob.make(cfg["n_holdout"], cfg["size"], cfg["seed"] + 10_000)
    inp = ho["input"]
    genome = np.asarray(champ["genome"], np.float64)

    # --- Python backend vs IR reference ------------------------------------- #
    gen = _import_gen(wd / f"gen_{a.problem}.py")
    py_max, n_noncomparable = 0.0, 0
    for i in range(len(inp)):
        ref = ops.apply_genome(genome, inp[i])
        got = gen.pipeline(inp[i].astype(np.float64))    # RAW — re-clipping here would hide a codegen clip bug
        d = _maxdiff(ref, got)
        if np.isnan(d):
            n_noncomparable += 1
        else:
            py_max = max(py_max, d)
    n_comparable = len(inp) - n_noncomparable
    py_pass = n_comparable > 0 and py_max < a.tol

    result = {"problem": a.problem, "python_max_abs_diff": py_max, "python_pass": py_pass,
              "tol": a.tol, "n_noncomparable_final": n_noncomparable, "c_backend": None}

    # --- C backend (compile-gated) ------------------------------------------ #
    cc = shutil.which("gcc") or shutil.which("cc") or shutil.which("clang")
    if not info["c_fully_supported"]:
        result["c_backend"] = {"status": "skipped", "reason": "champion uses ops not yet in the C runtime"}
    elif not cc:
        result["c_backend"] = {"status": "skipped", "reason": "no C toolchain (gcc/clang) in this environment"}
    else:
        try:
            (wd / "driver.c").write_text(_DRIVER_C, encoding="utf-8")
            here = Path(__file__).resolve().parent
            exe = wd / ("cbackend.exe" if sys.platform == "win32" else "cbackend")
            subprocess.run([cc, "-O2", "-I", str(here), "-I", str(wd),
                            str(here / "imgops.c"), str(wd / f"gen_{a.problem}.c"), str(wd / "driver.c"),
                            "-lm", "-o", str(exe)], check=True, capture_output=True, text=True)
            n, sz = len(inp), cfg["size"]
            fin, fout = wd / "in.bin", wd / "out.bin"
            with open(fin, "wb") as f:
                np.array([n, sz, sz], np.int32).tofile(f)
                inp.astype(np.float32).tofile(f)
            subprocess.run([str(exe), str(fin), str(fout)], check=True, capture_output=True)
            cout = np.fromfile(fout, np.float32).reshape(n, sz, sz)
            c_max = 0.0
            for i in range(n):
                got = np.clip(gen.pipeline(inp[i].astype(np.float64)), 0.0, 1.0)
                c_max = max(c_max, float(np.max(np.abs(got - cout[i]))))
            result["c_backend"] = {"status": "ran", "c_vs_python_max_abs_diff": c_max,
                                   "pass": c_max < 1e-3}  # float32 + kernel rounding tolerance
        except subprocess.CalledProcessError as e:
            result["c_backend"] = {"status": "compile_error", "detail": (e.stderr or str(e))[-400:]}

    (wd / f"difftest_{a.problem}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if a.out:
        p = a.out if a.out.endswith(".json") else a.out + ".json"
        Path(p).write_text(json.dumps(result, indent=2), encoding="utf-8")
    cb = result["c_backend"]
    print(f"[difftest:{a.problem}] python diff {py_max:.2e} (pass={py_pass}) | "
          f"C: {cb.get('status')}" + (f" reason={cb.get('reason')}" if cb.get("reason") else ""))
    return 0 if py_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
