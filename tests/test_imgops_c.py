"""imgops.c (the image C runtime) vs the Python runtime (ops.RT + the per-stage clip
of ops._apply), compiled with whatever toolchain algo_difftest.find_c_compiler finds
(gcc/clang on PATH, else `python -m ziglang cc`). Skipped only when there is NO
compiler at all.

Regressions pinned (2026-09-03 review):
  * F1  `sharpen` (op unsharp) did not clip to [0,1] while ops._unsharp / ops._apply
        do, so any pipeline with unsharp followed by another op diverged (unsharp ->
        gaussian max|C-py| 6.7e-2; unsharp -> threshold(1.0) flipped 512 px) although
        codegen reported c_fully_supported.
  * F7  `box` with an EVEN k summed k+1 taps and divided by k (box(4) on a step edge
        peaked at 1.5625); it now mirrors scipy.ndimage.uniform_filter exactly.
"""
from __future__ import annotations

import shutil
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

import algo_difftest
import ops

_REPO = Path(__file__).resolve().parents[1]
_CC = algo_difftest.find_c_compiler()
pytestmark = pytest.mark.skipif(_CC is None, reason="no C toolchain (gcc/clang or ziglang)")

# argv: in out mode. Modes mirror the Python chains in _PY_MODES below.
_DRIVER = r"""
#include "imgops.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char** argv) {
    FILE* fi = fopen(argv[1], "rb"); FILE* fo = fopen(argv[2], "wb"); int mode = atoi(argv[3]);
    int w, h; fread(&w, 4, 1, fi); fread(&h, 4, 1, fi);
    float* img = (float*)malloc(sizeof(float) * w * h); fread(img, 4, w * h, fi);
    switch (mode) {
        case 0: sharpen(img, w, h, 1.5f, 0.5f); break;
        case 1: sharpen(img, w, h, 1.5f, 0.5f); gaussian(img, w, h, 1.0f); break;
        case 2: sharpen(img, w, h, 1.5f, 0.5f); sobel_mag(img, w, h); break;
        case 3: sharpen(img, w, h, 1.5f, 0.5f); threshold(img, w, h, 1.0f); break;
        case 4: box(img, w, h, 4); break;
        case 5: box(img, w, h, 3); break;
        case 6: box(img, w, h, 2); break;
        case 7: for (int i = 0; i < w * h; i++) img[i] = img[i] * 3.0f - 1.0f; clamp01(img, w, h); break;
    }
    fwrite(img, 4, w * h, fo); fclose(fi); fclose(fo); return 0;
}
"""

_GA = 0.7 / 2.7          # gaussian: 0.3 + 2.7 * a = 1.0  (matches the C call gaussian(..., 1.0f))
_RT = ops.RT


def _clip(v):
    return np.clip(v, 0.0, 1.0)


# unsharp: a=1.0 -> amount 1.5, b=0.0 -> sigma 0.5 (the c_stmt lambda in ops.py)
_PY_MODES = {
    0: lambda v: _clip(_RT["unsharp"](v, 1.0, 0.0)),
    1: lambda v: _clip(_RT["gaussian"](_clip(_RT["unsharp"](v, 1.0, 0.0)), _GA, 0.0)),
    2: lambda v: _clip(_RT["sobel_mag"](_clip(_RT["unsharp"](v, 1.0, 0.0)), 0.0, 0.0)),
    3: lambda v: _clip(_RT["threshold"](_clip(_RT["unsharp"](v, 1.0, 0.0)), 1.0, 0.0)),
    4: lambda v: ndimage.uniform_filter(v, size=4),
    5: lambda v: ndimage.uniform_filter(v, size=3),
    6: lambda v: ndimage.uniform_filter(v, size=2),
    7: lambda v: _clip(v * 3.0 - 1.0),
}


@pytest.fixture(scope="module")
def runtime(tmp_path_factory):
    """Compile imgops.c + the driver once per module."""
    wd = tmp_path_factory.mktemp("imgops_c")
    (wd / "imgdrv.c").write_text(_DRIVER, encoding="utf-8")
    exe = wd / ("imgdrv.exe" if sys.platform == "win32" else "imgdrv")
    r = subprocess.run(list(_CC) + ["-O2", "-std=c99", "-ffp-contract=off", "-I", str(_REPO),
                                    str(_REPO / "imgops.c"), str(wd / "imgdrv.c"), "-lm", "-o", str(exe)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]

    def run(img: np.ndarray, mode: int) -> np.ndarray:
        fin, fout = wd / "in.bin", wd / "out.bin"
        h, w = img.shape
        with open(fin, "wb") as f:
            f.write(struct.pack("ii", w, h))
            img.astype(np.float32).tofile(f)
        subprocess.run([str(exe), str(fin), str(fout), str(mode)], check=True, capture_output=True)
        return np.fromfile(fout, np.float32).reshape(h, w).astype(np.float64)

    return run


def _images():
    rng = np.random.default_rng(3)
    return {
        "delta": np.pad(np.ones((1, 1)), 15),                                    # the F1 reproduction
        "step": np.where(np.arange(32)[None, :] >= 16, 1.0, 0.0) * np.ones((32, 32)),
        "rand": rng.random((32, 32)),
        "checker": (np.indices((32, 32)).sum(0) % 2).astype(float),
        "one_col": np.zeros((32, 1)) + np.linspace(0, 1, 32)[:, None],
    }


def _maxdiff(run, mode):
    worst = 0.0
    for im in _images().values():
        worst = max(worst, float(np.max(np.abs(run(im, mode) - _PY_MODES[mode](im)))))
    return worst


# --------------------------------------------------------------------------- #
# F1 — sharpen clips at its exit, so chained stages agree with the Python runtime
# --------------------------------------------------------------------------- #
def test_sharpen_alone_is_clipped_to_unit_range(runtime):
    delta = np.pad(np.ones((1, 1)), 15)
    out = runtime(delta, 0)
    assert out.min() >= 0.0 and out.max() <= 1.0            # was [-0.126, 1.572]
    assert _maxdiff(runtime, 0) < 1e-6                       # float32 rounding only


@pytest.mark.parametrize("mode,name", [(1, "unsharp->gaussian"), (2, "unsharp->sobel_mag")])
def test_sharpen_then_image_op_matches_python(runtime, mode, name):
    delta = np.pad(np.ones((1, 1)), 15)
    d = float(np.max(np.abs(runtime(delta, mode) - _PY_MODES[mode](delta))))
    assert d < 1e-6, (name, d)                               # was 6.7e-2 for the gaussian chain
    assert _maxdiff(runtime, mode) < 1e-5, name              # sobel_mag re-normalises: float32 sum noise


def test_sharpen_then_threshold_is_bit_identical(runtime):
    # threshold(1.0) after an unclipped sharpen lit every overshooting pixel (512 px on a
    # step edge); after the clip nothing exceeds 1.0 in either backend -> exact 0 diff.
    for im in _images().values():
        assert np.array_equal(runtime(im, 3), _PY_MODES[3](im))


# --------------------------------------------------------------------------- #
# F7 — box with an even k has exactly k taps (scipy uniform_filter semantics)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("mode,k", [(4, 4), (6, 2), (5, 3)])
def test_box_matches_scipy_uniform_filter(runtime, mode, k):
    d = _maxdiff(runtime, mode)
    assert d < 1e-6, (k, d)                                  # box(4) on a step edge peaked at 1.5625


def test_box_even_k_never_exceeds_input_range(runtime):
    step = np.where(np.arange(32)[None, :] >= 16, 1.0, 0.0) * np.ones((32, 32))
    out = runtime(step, 4)
    assert out.max() <= 1.0 + 1e-6 and out.min() >= -1e-6


# --------------------------------------------------------------------------- #
# clamp01 — the inter-stage clip codegen.py emits after every image/region stage
# --------------------------------------------------------------------------- #
def test_clamp01_matches_numpy_clip(runtime):
    assert _maxdiff(runtime, 7) < 1e-6


def test_header_declares_clamp01():
    assert "void clamp01(float* buf, int w, int h);" in (_REPO / "imgops.h").read_text(encoding="utf-8")


def test_reference_scripts_toolchain_is_reported(tmp_path):
    # the label difftest.py records must name the compiler that was actually used
    assert algo_difftest.compiler_label(_CC)
    assert shutil.which(_CC[0]) or Path(_CC[0]).exists()
