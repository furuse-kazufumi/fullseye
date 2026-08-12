"""Ground-truth regression test for the NCC template-matching defect (audit #13).

`ncc_locate` / `shape_locate` advertise HALCON's find_ncc_model / find_shape_model,
i.e. *normalized* cross-correlation (catalog.py maps them to cv2.matchTemplate /
skimage.feature.match_template / normxcorr2, references.py cites Lewis 1995).
Before the fix they computed RAW correlation - only the template was mean-subtracted
and nothing was divided by the local window energy - so the match locked onto the
brightest/largest structure instead of the best matching one, and the returned score
was unbounded and grew with image brightness.

Ground truth used here: a 96x96 scene holding the EXACT template at moderate contrast
at (24,24) plus a larger and brighter distractor disc at (64,64).  The window at
(24,24) is an exact affine map (a*T + b) of the template, so Pearson NCC there is
1.0 *by definition*, it is the global maximum, and it cannot depend on brightness.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops
import problems

TRUE_RC = (24, 24)          # centre of the exact template instance
DISTRACTOR_RC = (64, 64)    # centre of the larger/brighter blob


@pytest.fixture(autouse=True)
def _restore_match_template():
    prev = ops._MATCH_CTX.get("template")
    yield
    ops._MATCH_CTX["template"] = prev


def _disc(size: int, r: int) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size]
    c = size // 2
    return ((xx - c) ** 2 + (yy - c) ** 2 <= r * r).astype(np.float64)


def _scene(T: np.ndarray, brightness: float = 1.0, contrast: float = 0.35) -> np.ndarray:
    """Exact template at TRUE_RC (moderate contrast) + a bigger, brighter blob."""
    img = np.full((96, 96), 0.10, np.float64)
    h = T.shape[0] // 2
    r, c = TRUE_RC
    img[r - h:r + h + 1, c - h:c + h + 1] = np.maximum(
        img[r - h:r + h + 1, c - h:c + h + 1], 0.10 + contrast * T)
    r, c = DISTRACTOR_RC
    img[r - 7:r + 8, c - 7:c + 8] = np.maximum(
        img[r - 7:r + 8, c - 7:c + 8], 0.10 + 0.90 * _disc(15, 5))
    return np.clip(img, 0, 1) * brightness


def _err_px(res) -> float:
    return float(np.hypot(res[1] - TRUE_RC[0], res[2] - TRUE_RC[1]))


DISC_T = _disc(11, 4)                  # == problems._template(11), the locate model
L_T = problems._template_L(11)         # the locate_rot (shape-based) model


def test_scene_uses_the_shipped_locate_template():
    """The anchor must exercise the template the locate task really uses."""
    assert np.array_equal(DISC_T, problems._template(11))


# --- ncc_locate --------------------------------------------------------------- #
def test_ncc_locate_peaks_on_the_template_not_on_the_brightest_blob():
    ops.set_match_template(DISC_T)
    res = ops.RT["ncc_locate"](_scene(DISC_T), 0.0, 0.0)
    assert res.shape == (3,)
    assert _err_px(res) <= 2.0, (
        f"ncc_locate returned (row,col)=({res[1]},{res[2]}), expected ~{TRUE_RC}: "
        "raw (unnormalized) correlation locks onto the brightest/largest structure")


def test_ncc_locate_score_is_a_bounded_correlation_coefficient():
    ops.set_match_template(DISC_T)
    score = float(ops.RT["ncc_locate"](_scene(DISC_T), 0.0, 0.0)[0])
    assert -1.0 - 1e-9 <= score <= 1.0 + 1e-9, (
        f"ncc_locate score {score} is not a correlation coefficient in [-1,1]")
    # the window at TRUE_RC is an exact affine map of the template -> NCC == 1
    assert score >= 0.999, f"exact template match must score ~1.0, got {score}"


@pytest.mark.parametrize("brightness", [0.4, 0.6, 0.9])
def test_ncc_locate_is_invariant_to_image_brightness(brightness):
    ops.set_match_template(DISC_T)
    ref = ops.RT["ncc_locate"](_scene(DISC_T), 0.0, 0.0)
    dim = ops.RT["ncc_locate"](_scene(DISC_T, brightness=brightness), 0.0, 0.0)
    assert abs(float(dim[0]) - float(ref[0])) <= 1e-6, (
        f"ncc_locate score changed {ref[0]} -> {dim[0]} when the image was scaled by "
        f"{brightness}; a normalized score must be contrast/brightness invariant")
    assert (dim[1], dim[2]) == (ref[1], ref[2])


# --- shape_locate (rotation-invariant sibling) -------------------------------- #
def test_shape_locate_peaks_on_the_template_not_on_the_brightest_blob():
    ops.set_match_template(L_T)
    res = ops.RT["shape_locate"](_scene(L_T), 0.0, 0.0)
    assert res.shape == (4,)
    assert _err_px(res) <= 2.0, (
        f"shape_locate returned (row,col)=({res[1]},{res[2]}), expected ~{TRUE_RC}")


def test_shape_locate_score_is_a_bounded_correlation_coefficient():
    ops.set_match_template(L_T)
    score = float(ops.RT["shape_locate"](_scene(L_T), 0.0, 0.0)[0])
    assert -1.0 - 1e-9 <= score <= 1.0 + 1e-9, (
        f"shape_locate score {score} is not a correlation coefficient in [-1,1]")
    assert score >= 0.999, f"exact template match must score ~1.0, got {score}"


@pytest.mark.parametrize("brightness", [0.5, 0.8])
def test_shape_locate_is_invariant_to_image_brightness(brightness):
    ops.set_match_template(L_T)
    ref = ops.RT["shape_locate"](_scene(L_T), 0.0, 0.0)
    dim = ops.RT["shape_locate"](_scene(L_T, brightness=brightness), 0.0, 0.0)
    assert abs(float(dim[0]) - float(ref[0])) <= 1e-6, (
        f"shape_locate score changed {ref[0]} -> {dim[0]} when the image was scaled "
        f"by {brightness}")
