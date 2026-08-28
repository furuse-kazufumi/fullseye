# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Every operator must have a worked example — and the coverage galleries must run.

This is the invariant that keeps op coverage at 100% as the library grows: the moment
a new op is added to ``ops.REGISTRY`` or ``ops3d`` without any example calling it, this
test fails, so op help / OP_CATALOG never advertises "· 例: なし". The 2-D category
gallery examples (``examples/gallery2d_*.py``) are also executed end-to-end so their
per-op behavior checks stay honest.
"""
import glob
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import op_example_index as OEI  # noqa: E402


def test_no_3d_op_lacks_an_example():
    idx3d, _ = OEI.build_index(split=True)
    uncovered = sorted(n for n, ex in idx3d.items() if not ex)
    assert not uncovered, f"{len(uncovered)} ops3d op(s) have no worked example: {uncovered}"


def test_no_2d_op_lacks_an_example():
    _, idx2d = OEI.build_index(split=True)
    uncovered = sorted(n for n, ex in idx2d.items() if not ex)
    assert not uncovered, f"{len(uncovered)} 2-D registry op(s) have no worked example: {uncovered}"


_GALLERIES = sorted(
    os.path.basename(p)[:-3]
    for p in glob.glob(os.path.join(ROOT, "examples", "gallery2d_*.py"))
)


@pytest.mark.parametrize("gallery", _GALLERIES)
def test_coverage_gallery_runs(gallery):
    """Each 2-D category gallery runs to a passing self-check (exit 0, PASS line)."""
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1")
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "examples", f"{gallery}.py")],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, f"{gallery} exited {r.returncode}\nstderr tail:\n{r.stderr[-1500:]}"
    assert "PASS" in r.stdout, f"{gallery} produced no PASS line\nstdout tail:\n{r.stdout[-800:]}"
