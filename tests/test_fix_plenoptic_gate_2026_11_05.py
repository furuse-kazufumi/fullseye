# -*- coding: utf-8 -*-
"""The plenoptic PoC never prints PASS beside a focus peak or median it did not measure.

Before 2026-11-05, ``examples/poc_plenoptic_camera.py`` at its ``CI=1`` scale
(96 x 96 sensor, 6 x 6 MLA) decoded a 5 x 5 spatial field.  After the regional
erosion every plane had 0 samples, so the focus score was 0 at every slope;
``argmax`` returned the sweep's first slope and the run printed

    measured focus peak = -0.4000 / -0.4000 / -0.4000; region median slope = +nan / +nan / +nan

followed by ``PASS``.  The regional gate was skipped for ``CI=1`` instead of
being reported as not measured.

These tests check the output against invariants that do not come from the PoC's
own pass/fail logic: no ``nan`` / ``inf`` token on any printed line, a focus peak
strictly inside the slope sweep and within 0.03 lenslets/view of the
forward-traced truth the same run prints, and an explicit ``UNMEASURED`` line
whenever the regional gate cannot run.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
POC = ROOT / "examples" / "poc_plenoptic_camera.py"
#: The PoC's slope sweep is ``np.linspace(-.4, .4, 33)``; a peak on either end is truncated.
SWEEP_END = 0.4
NONFINITE = re.compile(r"(?<![A-Za-z_])[+-]?(nan|inf)(?![A-Za-z_])", re.IGNORECASE)
NUM = r"([+-]?\d+\.\d+)"


def _run(ci: bool) -> str:
    env = dict(os.environ, PYTHONUTF8="1", FULLSEYE_FIGURES="off")
    env.pop("PYTHONPATH", None)
    env.pop("FULLSEYE_FIGURE_DIR", None)
    env.pop("CI", None)
    if ci:
        env["CI"] = "1"
    r = subprocess.run([sys.executable, str(POC)], env=env, cwd=str(POC.parent),
                       capture_output=True, stdin=subprocess.DEVNULL, timeout=600)
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0, out[-3000:] + r.stderr.decode("utf-8", "replace")[-2000:]
    return out


def _line(out: str, head: str) -> str:
    hits = [ln for ln in out.splitlines() if ln.startswith(head)]
    assert len(hits) == 1, (head, hits)
    return hits[0]


def _three(text: str) -> np.ndarray:
    vals = re.findall(NUM, text)
    assert len(vals) >= 3, text
    return np.array([float(v) for v in vals[:3]])


@pytest.fixture(scope="module")
def reduced_out() -> str:
    return _run(ci=True)


@pytest.fixture(scope="module")
def full_out() -> str:
    return _run(ci=False)


@pytest.mark.parametrize("which", ["reduced_out", "full_out"])
def test_no_nonfinite_token_on_any_line(which, request):
    out = request.getfixturevalue(which)
    lines = out.splitlines()
    assert len(lines) >= 8, out
    bad = [ln for ln in lines if NONFINITE.search(ln)]
    assert bad == [], bad


def test_reduced_scale_reports_regional_gate_unmeasured(reduced_out):
    assert "scale=96x96" in reduced_out
    unmeasured = _line(reduced_out, "UNMEASURED: regional parallax gate")
    assert "5 x 5" in unmeasured
    # No focus peak / region median is printed for a gate that could not run ...
    assert not any(ln.startswith("measured focus peak") for ln in reduced_out.splitlines())
    assert not any(ln.startswith("region median depth error") for ln in reduced_out.splitlines())
    # ... and the PASS line says which gate it covers.
    pass_line = _line(reduced_out, "PASS")
    assert "UNMEASURED" in pass_line and "gate 1 only" in pass_line


def test_full_scale_focus_peaks_are_measured_and_inside_the_sweep(full_out):
    assert "scale=480x480" in full_out
    assert "UNMEASURED" not in full_out
    truth = _three(_line(full_out, "ray-traced slope (full pupil)").split("=", 1)[1])
    peak_line = _line(full_out, "measured focus peak")
    peaks = _three(peak_line.split("=", 1)[1].split(";")[0])
    medians = _three(peak_line.split("region median slope =", 1)[1])
    for vals in (peaks, medians):
        assert np.isfinite(vals).all(), vals
        assert np.all(np.abs(vals) < SWEEP_END - 1e-9), vals          # not on the sweep's end
        assert np.all(np.abs(vals - truth) <= 0.03), (vals, truth)    # matches the traced rays
    assert medians[0] > medians[1] > medians[2]
    errs = _three(_line(full_out, "region median depth error").split("=", 1)[1])
    assert np.isfinite(errs).all()
    assert _line(full_out, "PASS").startswith("PASS: captured raw causally feeds")


# --- the guarded helper, on inputs whose answer is known without the PoC ----------------

@pytest.fixture(scope="module")
def poc():
    sys.path.insert(0, str(ROOT / "examples"))
    try:
        import poc_plenoptic_camera as mod
    finally:
        sys.path.remove(str(ROOT / "examples"))
    return mod


def _masks(poc, n_px):
    """Three disjoint rectangular regions of ``n_px`` samples each on a 40 x 40 field."""
    masks = []
    for k in range(3):
        m = np.zeros((40, 40), bool)
        m.reshape(-1)[k * 400:k * 400 + n_px] = True
        masks.append(m)
    assert [int(m.sum()) for m in masks] == [n_px] * 3
    return masks


def _stack(sharpness):
    """Refocus stack whose Laplacian variance rises with ``sharpness[i]`` (noise amplitude)."""
    rng = np.random.default_rng(0)
    base = rng.standard_normal((40, 40))
    return np.stack([a * base for a in sharpness])


def test_helper_returns_none_for_regions_below_the_minimum(poc):
    slopes = np.linspace(-.4, .4, 5)
    small = _masks(poc, poc.MIN_REGION_PX - 1)
    flat = np.zeros((40, 40))
    assert poc.regional_parallax(slopes, _stack([1, 2, 3, 2, 1]), flat, flat + 1.0, small) is None


def test_helper_rejects_a_peak_on_the_sweep_end(poc):
    slopes = np.linspace(-.4, .4, 5)
    masks = _masks(poc, 100)
    flat = np.zeros((40, 40))
    with pytest.raises(AssertionError, match="sweep's end"):
        poc.regional_parallax(slopes, _stack([5, 4, 3, 2, 1]), flat, flat + 1.0, masks)


def test_helper_rejects_a_flat_focus_curve(poc):
    slopes = np.linspace(-.4, .4, 5)
    masks = _masks(poc, 100)
    flat = np.zeros((40, 40))
    with pytest.raises(AssertionError, match="flat focus"):
        poc.regional_parallax(slopes, _stack([1, 1, 1, 1, 1]), flat, flat + 1.0, masks)


def test_helper_rejects_a_nan_region_median(poc):
    slopes = np.linspace(-.4, .4, 5)
    masks = _masks(poc, 100)
    slope_map = np.full((40, 40), np.nan)
    with pytest.raises(AssertionError):
        poc.regional_parallax(slopes, _stack([1, 2, 3, 2, 1]), slope_map, np.ones((40, 40)), masks)


def test_helper_measures_an_interior_peak(poc):
    slopes = np.linspace(-.4, .4, 5)
    masks = _masks(poc, 100)
    slope_map = np.full((40, 40), 0.2)
    depth = np.full((40, 40), 1.0)
    got = poc.regional_parallax(slopes, _stack([1, 2, 3, 2, 1]), slope_map, depth, masks)
    assert got is not None
    np.testing.assert_allclose(got["peaks"], [0.0, 0.0, 0.0])
    np.testing.assert_allclose(got["region_slope"], [0.2, 0.2, 0.2])
    np.testing.assert_allclose(got["depth_median_error"], 1.0 - poc.DEPTHS_M)
