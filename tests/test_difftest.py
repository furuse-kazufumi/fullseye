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
