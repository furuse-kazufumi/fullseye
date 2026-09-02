"""Difftest (S2) — the honest-correctness gate must be fail-closed.

Two regressions are pinned here: (1) a champion whose emitted C does not compile
while codegen declared it c_fully_supported used to exit 0 (PASS), because the
gate only looked at status == "ran"; (2) the C tolerance was hardcoded at 1e-3,
so tightening it was impossible — it is now --c-tol and is recorded in the JSON.
"""
import json
import os
import sys

import numpy as np

import codegen
import difftest
import ops


def _fake_failing_cc(tmp_path):
    """A gcc shim on PATH that always exits 1, so the C branch records a real
    compile_error without a toolchain in this environment."""
    binp = tmp_path / "fakebin"
    binp.mkdir()
    if sys.platform == "win32":
        (binp / "gcc.bat").write_text("@echo off\r\necho fake gcc: error 1>&2\r\nexit /b 1\r\n", encoding="ascii")
    else:
        sh = binp / "gcc"
        sh.write_text("#!/bin/sh\necho 'fake gcc: error' >&2\nexit 1\n", encoding="ascii")
        sh.chmod(0o755)
    return binp


def _workdir(tmp_path, c_fully_supported, problem="edge", seed=0):
    """A minimal S2 workdir: real codegen output (so the Python backend matches
    ops.run_genome exactly) + a codegen json whose C-support flag we control."""
    g = np.random.default_rng(seed).random(ops.GENOME_LEN)
    (tmp_path / f"champion_{problem}.json").write_text(json.dumps(
        {"genome": [float(v) for v in g], "pipeline": problem,
         "config": {"n_holdout": 2, "size": 32, "seed": 0}}), encoding="utf-8")
    info = codegen.emit(problem, tmp_path)
    info["c_fully_supported"] = c_fully_supported
    (tmp_path / f"codegen_{problem}.json").write_text(json.dumps(info), encoding="utf-8")
    return tmp_path


def _run(monkeypatch, wd, *extra, problem="edge"):
    monkeypatch.setattr(sys, "argv", ["difftest.py", "--problem", problem, "--workdir", str(wd), *extra])
    rc = difftest.main()
    return rc, json.loads((wd / f"difftest_{problem}.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# gate unit tests                                                             #
# --------------------------------------------------------------------------- #
def test_compile_error_fails_the_gate_when_c_was_expected():
    # codegen said every op is in the C runtime, yet the backend did not build:
    # that is a correctness failure, not a neutral skip.
    assert difftest._c_gate_ok({"status": "compile_error", "detail": "..."}, True) is False


def test_not_attempted_c_stays_neutral():
    assert difftest._c_gate_ok({"status": "skipped", "reason": "no C toolchain"}, True) is True
    assert difftest._c_gate_ok({"status": "skipped", "reason": "ops not in C runtime"}, False) is True
    assert difftest._c_gate_ok({"status": "compile_error"}, False) is True


def test_ran_c_uses_the_pass_flag():
    assert difftest._c_gate_ok({"status": "ran", "pass": True}, True) is True
    assert difftest._c_gate_ok({"status": "ran", "pass": False}, True) is False


# --------------------------------------------------------------------------- #
# end-to-end                                                                  #
# --------------------------------------------------------------------------- #
def test_uncompilable_c_backend_exits_nonzero(tmp_path, monkeypatch):
    wd = _workdir(tmp_path, c_fully_supported=True)
    monkeypatch.setenv("PATH", str(_fake_failing_cc(tmp_path)) + os.pathsep + os.environ["PATH"])
    rc, res = _run(monkeypatch, wd)
    assert res["python_pass"] is True                      # only the C half is broken
    assert res["c_backend"]["status"] == "compile_error"
    assert rc == 1                                          # previously 0 — the fail-open


def test_c_tol_defaults_to_1e_3_and_is_overridable(tmp_path, monkeypatch):
    wd = _workdir(tmp_path, c_fully_supported=False)
    rc, res = _run(monkeypatch, wd)
    assert rc == 0 and res["c_tol"] == 1e-3                 # unchanged default behaviour
    rc, res = _run(monkeypatch, wd, "--c-tol", "5e-4")
    assert rc == 0 and res["c_tol"] == 5e-4                 # decoupled from --tol
    assert res["tol"] == 1e-6


# --------------------------------------------------------------------------- #
# 2026-09-03 review: (F2) compiler discovery is shared with the algo tier, so the C
# half RUNS wherever `python -m ziglang cc` exists instead of silently skipping;
# (F1) it catches an unclipped C stage; (F8) a NaN in either output is a FAILURE.
# --------------------------------------------------------------------------- #
import shutil                                               # noqa: E402

import algo_difftest                                        # noqa: E402
from test_codegen import genome_for                         # noqa: E402

_CC = algo_difftest.find_c_compiler()
_REPO = Path(__file__).resolve().parents[1]


def _c_champion(tmp_path, specs, problem="edge"):
    """An S2 workdir whose champion uses ONLY C-runtime ops (real codegen output)."""
    g = genome_for(specs)
    (tmp_path / f"champion_{problem}.json").write_text(json.dumps(
        {"genome": [float(v) for v in g], "pipeline": problem,
         "config": {"n_train": 4, "n_holdout": 4, "size": 32, "seed": 0}}), encoding="utf-8")
    info = codegen.emit(problem, tmp_path)
    assert info["c_fully_supported"] is True
    (tmp_path / f"codegen_{problem}.json").write_text(json.dumps(info), encoding="utf-8")
    return tmp_path


def _mutant_runtime(tmp_path, monkeypatch, old, new):
    """Point difftest at a copy of the C runtime with ``old`` replaced by ``new`` (so the
    pre-fix behaviour can be re-created without touching the repo file)."""
    rt = tmp_path / "rt"
    rt.mkdir()
    src = (_REPO / "imgops.c").read_text(encoding="utf-8")
    assert old in src, "runtime text changed: update the mutant"
    (rt / "imgops.c").write_text(src.replace(old, new), encoding="utf-8")
    shutil.copy(_REPO / "imgops.h", rt / "imgops.h")
    monkeypatch.setattr(difftest, "__file__", str(rt / "difftest.py"))   # `here` = rt


_UNSHARP_GAUSS = [("unsharp", 1.0, 0.0), ("gaussian", 0.7 / 2.7, 0.5)]
_SHARPEN_CLIPPED = "buf[i] = clampf(buf[i] + amount * (buf[i] - blur[i]), 0.0f, 1.0f);"


def test_compiler_discovery_is_shared_with_algo_tier():
    # the old gcc/cc/clang-only lookup returned None on a ziglang-only machine
    assert difftest.find_c_compiler is algo_difftest.find_c_compiler


@pytest.mark.skipif(_CC is None, reason="no C toolchain (gcc/clang or ziglang)")
def test_c_gate_runs_here_and_passes_on_unsharp_chain(tmp_path, monkeypatch):
    wd = _c_champion(tmp_path, _UNSHARP_GAUSS)
    rc, res = _run(monkeypatch, wd)
    cb = res["c_backend"]
    assert cb["status"] == "ran", cb                        # NOT "skipped" on this machine
    assert cb["compiler"] == algo_difftest.compiler_label(_CC)
    assert cb["pass"] is True and cb["c_vs_python_max_abs_diff"] < 1e-5, cb
    assert rc == 0


@pytest.mark.skipif(_CC is None, reason="no C toolchain (gcc/clang or ziglang)")
def test_c_gate_catches_unclipped_sharpen(tmp_path, monkeypatch):
    # Re-create F1: sharpen without its exit clip AND codegen without the inter-stage
    # clamp -> the C pipeline diverges from Python and the gate must FAIL (rc 1).
    _mutant_runtime(tmp_path, monkeypatch, _SHARPEN_CLIPPED,
                    "buf[i] = buf[i] + amount * (buf[i] - blur[i]);")
    wd = _c_champion(tmp_path, _UNSHARP_GAUSS)
    c_path = wd / "gen_edge.c"
    c_path.write_text("\n".join(ln for ln in c_path.read_text(encoding="utf-8").splitlines()
                                if "clamp01" not in ln), encoding="utf-8")
    rc, res = _run(monkeypatch, wd)
    cb = res["c_backend"]
    assert cb["status"] == "ran" and cb["pass"] is False, cb
    assert cb["c_vs_python_max_abs_diff"] > 1e-2            # measured 6.7e-2 before the fix
    assert rc == 1


@pytest.mark.skipif(_CC is None, reason="no C toolchain (gcc/clang or ziglang)")
def test_codegen_clamp_alone_rescues_an_unclipped_op(tmp_path, monkeypatch):
    # belt and braces: with the op's own clip removed, the emitted clamp01 still keeps
    # the C pipeline equal to the Python runtime.
    _mutant_runtime(tmp_path, monkeypatch, _SHARPEN_CLIPPED,
                    "buf[i] = buf[i] + amount * (buf[i] - blur[i]);")
    wd = _c_champion(tmp_path, _UNSHARP_GAUSS)
    rc, res = _run(monkeypatch, wd)
    assert res["c_backend"]["status"] == "ran" and res["c_backend"]["pass"] is True
    assert rc == 0


def test_nan_never_folds_to_zero_diff():
    nan = float("nan")
    assert difftest._maxdiff(np.array([[nan, 0.0]]), np.zeros((1, 2))) == float("inf")
    assert difftest._maxdiff(np.zeros((1, 2)), np.array([[0.0, nan]])) == float("inf")
    assert difftest._maxdiff(np.array([[0.0, float("inf")]]), np.zeros((1, 2))) == float("inf")
    assert difftest._maxdiff(nan, 0.0) == float("inf")      # scalar (feature) finals too
    assert difftest._maxdiff(np.zeros((2, 2)), np.zeros((2, 2))) == 0.0
    assert difftest._maxdiff(np.zeros((2, 2)), np.zeros((3, 2))) == float("inf")
    assert np.isnan(difftest._maxdiff({"cs": []}, {"cs": []}))   # non-numeric stays non-comparable
    assert difftest._finite_maxdiff(np.array([nan]), np.array([nan])) == float("inf")


@pytest.mark.skipif(_CC is None, reason="no C toolchain (gcc/clang or ziglang)")
def test_nan_in_c_output_fails_the_gate(tmp_path, monkeypatch):
    _mutant_runtime(tmp_path, monkeypatch, _SHARPEN_CLIPPED, "buf[i] = NAN;")
    wd = _c_champion(tmp_path, _UNSHARP_GAUSS)
    rc, res = _run(monkeypatch, wd)
    cb = res["c_backend"]
    assert cb["status"] == "ran" and cb["pass"] is False, cb   # was pass=True with diff 0.0
    assert cb["c_vs_python_max_abs_diff"] == float("inf")
    assert rc == 1
