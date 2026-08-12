"""Named regression tests for defects found in the 2026-08-12 audit.

Each test reproduces one confirmed bug and fails on the pre-fix code (RED),
passing once the fix lands (GREEN). Keep them as pinpoint regression guards
even though the parametrized contracts in test_op_contracts.py also cover them.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops

RNG = np.random.default_rng(20260812)


def _img(n=48):
    return np.clip(RNG.random((n, n)), 0, 1)


def _region(n=48):
    return (RNG.random((n, n)) > 0.4).astype(np.float64)


# --- Bug A: cv2.warpPolar left the unmapped Cartesian corners uninitialised, --- #
#            making the whole polar family nondeterministic (and forward polar    #
#            unclamped, producing values far outside [0,1]).                      #
POLAR_OPS = ["polar_trans_image", "polar_trans_image_ext",
             "polar_trans_image_inv", "polar_trans_region_inv"]


@pytest.mark.parametrize("name", POLAR_OPS)
def test_polar_ops_are_deterministic(name):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered (cv2 backend absent)")
    src = _region() if "region" in name else _img()
    ref = np.asarray(fn(src.copy(), 0.5, 0.5), np.float64)
    for _ in range(8):
        again = np.asarray(fn(src.copy(), 0.5, 0.5), np.float64)
        assert np.array_equal(ref, again), f"{name} is nondeterministic (stale buffer)"


@pytest.mark.parametrize("name", POLAR_OPS)
def test_polar_ops_stay_in_unit_range(name):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered (cv2 backend absent)")
    src = _region() if "region" in name else _img()
    out = np.asarray(fn(src.copy(), 0.5, 0.5), np.float64)
    assert np.all(np.isfinite(out)), f"{name} produced non-finite values"
    assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, (
        f"{name} out of [0,1]: min={out.min()} max={out.max()}")


# --- Bug B: skimage.medial_axis breaks ties with an unseeded RNG. -------------- #
def test_sk_medial_is_deterministic():
    fn = ops.RT.get("sk_medial")
    if fn is None:
        pytest.skip("sk_medial not registered (skimage backend absent)")
    reg = _region()
    ref = np.asarray(fn(reg.copy(), 0.5, 0.5), np.float64)
    for _ in range(5):
        assert np.array_equal(ref, np.asarray(fn(reg.copy(), 0.5, 0.5), np.float64)), (
            "sk_medial is nondeterministic (medial_axis needs a fixed rng)")


# --- Bug C: restoration/denoise ops returned NaN on constant (zero-variance) --- #
#            input, which np.clip does not strip.                                 #
NAN_OPS = ["sk_wavelet", "xsp_wiener", "xsitk_laplacian_sharpen"]


@pytest.mark.parametrize("name", NAN_OPS)
@pytest.mark.parametrize("const", [0.0, 0.5, 1.0])
def test_denoise_ops_finite_on_constant_image(name, const):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered (backend absent)")
    v = np.full((32, 32), const, np.float64)
    out = np.asarray(fn(v, 0.5, 0.5), np.float64)
    assert np.all(np.isfinite(out)), (
        f"{name} produced NaN/Inf on a constant={const} image")


# --- Bug D: binary_closing (reg_close / convex_fill) used border_value=0, which --- #
#            erodes and DELETES region pixels that touch the image border.         #
@pytest.mark.parametrize("name", ["reg_close", "convex_fill"])
def test_closing_does_not_delete_border_region(name):
    reg = np.zeros((20, 20)); reg[0:6, 0:6] = 1.0   # square in the corner, touches border
    out = ops.RT[name](reg, 0.5, 0.0)
    assert out.sum() >= reg.sum(), f"{name} deleted border-touching region pixels"


# --- Bug E: evolve.run crashed (np.vstack on empty children) for pop <= 2. ------- #
@pytest.mark.parametrize("pop", [1, 2, 3])
def test_evolve_runs_for_tiny_populations(tmp_path, pop):
    import evolve
    champ = evolve.run("denoise", workdir=str(tmp_path), gens=2, pop=pop, seed=0, verbose=False)
    assert "genome" in champ and np.isfinite(champ["train"])


# --- Bug F: apply_genome called np.mean on a contour dict -> TypeError. ---------- #
def test_apply_genome_handles_contour_ending_pipeline():
    img = np.clip(RNG.random((32, 32)), 0, 1)
    # a genome whose first slot selects a contour-producing op still coerces to 2-D
    for seed in range(40):
        g = np.random.default_rng(seed).random(ops.GENOME_LEN)
        out = ops.apply_genome(g, img)   # must never raise
        assert isinstance(out, np.ndarray) and out.ndim == 2


# --- Bug G: robust.py read the wrong baseline keys and never persisted the ------- #
#            train-selected champion (champion_<problem>.json held the LAST seed).  #
def test_robust_persists_train_selected_champion(tmp_path):
    import json
    import robust
    import baseline
    import sys
    wd = tmp_path
    # produce a real baseline (writes baseline_denoise.json with hand/trivial holdout)
    sys.argv = ["baseline.py", "--problem", "denoise", "--workdir", str(wd),
                "--random-samples", "20", "--n-train", "6", "--n-holdout", "4", "--size", "32"]
    baseline.main()
    sys.argv = ["robust.py", "--problem", "denoise", "--workdir", str(wd),
                "--seeds", "3", "--gens", "3", "--pop", "8"]
    robust.main()
    champ = json.loads((wd / "champion_denoise.json").read_text(encoding="utf-8"))
    summary = json.loads((wd / "robust_denoise.json").read_text(encoding="utf-8"))
    # the persisted champion must be the train-selected one from the summary
    assert champ["train"] == summary["selected_by_train"]["train"]
    # and the baseline comparison must no longer be dead (keys were 'holdout', not 'score')
    assert summary["baseline_hand"] is not None and summary["n_beat_hand"] is not None


# --- Bug H: knob ranges let low_threshold > high_threshold (canny / firm). ------- #
@pytest.mark.parametrize("name", ["xkor_canny", "xwt_firm_denoise"])
def test_threshold_ops_handle_inverted_knobs(name):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered (backend absent)")
    img = np.clip(RNG.random((32, 32)), 0, 1)
    # a=1.0, b=0.0 is exactly the knob corner where low would exceed high
    out = np.asarray(fn(img, 1.0, 0.0), np.float64)
    assert np.all(np.isfinite(out)) and out.ndim == 2
