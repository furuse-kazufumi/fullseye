"""L1 contracts — the typed model, backend selection, and the differential gate.

These tests are the de-risking evidence for ``docs/FSCRIPT_DECISION.md``: they
prove that a native backend can be swapped in behind the same operator name and
*proven equivalent* to the numpy reference, which is the mechanism the whole
staged-native plan rests on.  If this stops holding, the plan's kill criteria
(section 6 of the decision doc) are triggered.
"""
from __future__ import annotations

import numpy as np
import pytest

import fslib
from fslib import FImage, ObjectSet, Region, FsBackendError, FsTypeError

HAVE_CV2 = "cv2" in fslib.backends_for("gauss")
needs_cv2 = pytest.mark.skipif(not HAVE_CV2, reason="OpenCV not installed")


def scene(h=256, w=256, n=12, seed=3):
    """Bright discs on a gradient — deterministic, 8-bit like a real camera."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    img = 40 + 20 * (xx / (w - 1))
    cols = int(np.ceil(np.sqrt(n)))
    rows = int(np.ceil(n / cols))
    k = 0
    for r in range(rows):
        for c in range(cols):
            if k >= n:
                break
            cy, cx = (r + 0.5) * h / rows, (c + 0.5) * w / cols
            rr = 7 * rng.uniform(0.8, 1.3)
            img[(yy - cy) ** 2 + (xx - cx) ** 2 <= rr * rr] = 220
            k += 1
    return FImage.from_u8(np.clip(img, 0, 255).astype(np.uint8))


# --------------------------------------------------------------------------- #
# Claim 1: the sort and the value range are carried, not guessed
# --------------------------------------------------------------------------- #
def _measured_part_area(frame: np.ndarray) -> float:
    """Area of the largest object — what an inspection actually reports."""
    objs = fslib.connection(fslib.threshold(FImage.from_u8(frame), 0.4, 1.0))
    areas, _, _ = fslib.region_features(objs)
    return float(areas.max())


def test_threshold_is_independent_of_unrelated_bright_pixels():
    """The defect `fscript._norm01` has (area 256 -> 1), fixed by construction.

    A hot pixel is still *detected* — that is correct, it is above threshold.
    What must not happen is the threshold's meaning shifting, which is what
    dividing by the frame maximum does: it rescales every other pixel.
    """
    part = np.zeros((32, 32), dtype=np.uint8); part[8:24, 8:24] = 120
    hot = part.copy(); hot[0, 0] = 250
    assert _measured_part_area(part) == 16 * 16
    assert _measured_part_area(hot) == 16 * 16, (
        "a hot pixel elsewhere in the frame must not change the measured part")

    # …and the same input through the current fscript path does change it, which
    # is why this model exists.  (Kept as an executable comparison, not a claim
    # about fslib.)
    import fscript
    old = fscript.run("R := threshold(Image, 0.4, 1.0)\nA := area(R)",
                      images={"Image": hot.astype(np.float64)}).vars["A"]
    assert old != 16 * 16


def test_value_range_comes_from_the_sensor_not_the_content():
    dark = np.full((8, 8), 100, dtype=np.uint8)
    img = FImage.from_u8(dark)
    assert img.absolute(0.5) == pytest.approx(127.5)      # 0..255, not 0..100


def test_a_binary_valued_image_is_still_an_image():
    binary_looking = np.zeros((16, 16), dtype=np.uint8); binary_looking[4:8, 4:8] = 255
    img = FImage.from_u8(binary_looking)
    assert isinstance(img, FImage) and not isinstance(img, Region)


@pytest.mark.parametrize("value", ["image", "region", "objectset"])
def test_iconic_values_have_no_truth_value(value):
    img = scene(64, 64, 4)
    v = {"image": img,
         "region": fslib.threshold(img, 0.5, 1.0),
         "objectset": fslib.connection(fslib.threshold(img, 0.5, 1.0))}[value]
    with pytest.raises(FsTypeError):
        bool(v)


def test_operators_reject_the_wrong_sort():
    img = scene(64, 64, 4)
    with pytest.raises(FsTypeError):
        fslib.connection(img)                      # an image is not a Region
    with pytest.raises(FsTypeError):
        fslib.gauss(fslib.threshold(img, 0.5, 1.0), 1.0)   # a Region is not an image


# --------------------------------------------------------------------------- #
# Claim 2: one operator, several backends, selected by profile
# --------------------------------------------------------------------------- #
def test_studio_runs_what_the_line_will_run():
    """What the designer sees must be what ships — studio prefers the native
    backend, not the oracle."""
    assert fslib.current_profile() == "studio"
    if HAVE_CV2:
        with fslib.profile("studio"):
            assert fslib.gauss(scene(64, 64, 4), 1.0).pixels is not None
        # studio and industrial must select the same backend when one exists
        img = scene(128, 128, 6)
        with fslib.profile("studio"):
            a = fslib.gauss(img, 1.5).pixels
        with fslib.profile("industrial"):
            b = fslib.gauss(img, 1.5).pixels
        assert np.array_equal(a, b), "studio must not diverge from what ships"


def test_reference_profile_is_the_oracle():
    with fslib.profile("reference"):
        assert fslib.gauss(scene(64, 64, 4), 1.0) is not None


@needs_cv2
def test_industrial_profile_uses_the_native_backend():
    with fslib.profile("industrial"):
        assert fslib.gauss(scene(64, 64, 4), 1.0) is not None


def test_industrial_profile_refuses_to_degrade_silently():
    """An operator with no native backend must fail loudly, not run slowly."""
    @fslib.op("numpy_only_demo", "numpy")
    def _impl(img):
        return img
    try:
        with fslib.profile("industrial"):
            with pytest.raises(FsBackendError, match="no backend for profile"):
                fslib._dispatch("numpy_only_demo", scene(32, 32, 1))
    finally:
        fslib._REGISTRY.pop("numpy_only_demo", None)


def test_profile_is_restored_after_the_block():
    with fslib.profile("industrial"):
        pass
    assert fslib.current_profile() == "studio"


# --------------------------------------------------------------------------- #
# Fail-closed vs fail-open — the difference between a search engine and a line
# --------------------------------------------------------------------------- #
def test_the_evolution_registry_is_fail_open_and_fslib_must_not_be():
    """The 650-op registry deliberately swallows op failures.

    ``backends._safe`` wraps every op in ``except Exception: out = None`` and
    ``backend_safe.sanitize`` then returns a *valid, benign value of the declared
    sort* — for a region that is an empty region.  For the evolution search this
    is right: a candidate that raises should score badly, not kill the run.

    On a production line the same behaviour means a missing dependency or a
    degenerate frame silently reports **no defects found**, and every part
    passes.  That is fail-open on the judgement itself.

    This test pins both halves: the registry's behaviour (so a change is noticed)
    and fslib's opposite guarantee.
    """
    import backend_safe

    # The registry's contract: a failed op becomes an empty region, not an error.
    empty = backend_safe.sanitize(None, np.zeros((16, 16)), "region")
    assert isinstance(empty, np.ndarray) and empty.sum() == 0.0
    assert backend_safe.fallback(np.zeros((16, 16)), "feature") == 0.0

    # fslib's contract: no result is an error, never a benign-looking value.
    # (see also test_missing_dependency_degrades_studio_but_stops_the_line)
    @fslib.op("always_raises_demo", "numpy")
    def _boom(img):
        raise RuntimeError("backend exploded")
    try:
        with fslib.profile("reference"):
            with pytest.raises(RuntimeError):
                fslib._dispatch("always_raises_demo", scene(32, 32, 1))
    finally:
        fslib._REGISTRY.pop("always_raises_demo", None)


# --------------------------------------------------------------------------- #
# Claim 3: the numpy implementation is the oracle — native must agree with it
# --------------------------------------------------------------------------- #
@needs_cv2
@pytest.mark.parametrize("sigma", [0.8, 1.5, 3.0])
def test_differential_gauss_native_agrees_with_oracle(sigma):
    img = scene(256, 256, 12)
    with fslib.profile("reference"):
        ref = fslib.gauss(img, sigma).pixels.astype(np.float64)
    with fslib.profile("industrial"):
        nat = fslib.gauss(img, sigma).pixels.astype(np.float64)
    # 8-bit rounding plus a different kernel truncation — the gate is a declared
    # tolerance, not bit-equality, and it is part of the operator's contract.
    assert np.max(np.abs(ref - nat)) <= 2.0


@needs_cv2
def test_differential_connection_and_features_agree_with_oracle():
    img = scene(256, 256, 12)
    reg = fslib.threshold(img, 0.5, 1.0)

    with fslib.profile("reference"):
        objs_ref = fslib.connection(reg)
        a_ref, r_ref, c_ref = fslib.region_features(objs_ref)
    with fslib.profile("industrial"):
        objs_nat = fslib.connection(reg)
        a_nat, r_nat, c_nat = fslib.region_features(objs_nat)

    assert len(objs_ref) == len(objs_nat) == 12

    # Label numbering differs between backends, so compare the feature SETS.
    def sort_key(a, r, c):
        order = np.lexsort((c, r))
        return a[order], r[order], c[order]

    a1, r1, c1 = sort_key(a_ref, r_ref, c_ref)
    a2, r2, c2 = sort_key(a_nat, r_nat, c_nat)
    assert np.array_equal(a1, a2)
    assert np.allclose(r1, r2, atol=1e-6)
    assert np.allclose(c1, c2, atol=1e-6)


@needs_cv2
def test_differential_select_shape_agrees_with_oracle():
    img = scene(256, 256, 12)
    reg = fslib.threshold(img, 0.5, 1.0)
    counts = []
    for prof in ("reference", "industrial"):
        with fslib.profile(prof):
            objs = fslib.connection(reg)
            counts.append(len(fslib.select_shape(objs, "area", 80, 1e12)))
    assert counts[0] == counts[1]


# --------------------------------------------------------------------------- #
# ObjectSet: masks are materialised only on demand
# --------------------------------------------------------------------------- #
def test_objectset_does_not_materialise_masks_up_front():
    img = scene(128, 128, 9)
    objs = fslib.connection(fslib.threshold(img, 0.5, 1.0))
    assert len(objs) == 9
    # the whole set is one label image, not nine masks
    assert objs.labels.shape == img.shape
    assert isinstance(objs.region(0), Region)


def test_select_shape_filters_ids_and_keeps_the_label_image():
    img = scene(128, 128, 9)
    objs = fslib.connection(fslib.threshold(img, 0.5, 1.0))
    kept = fslib.select_shape(objs, "area", 1e9, 1e12)      # impossible area
    assert len(kept) == 0
    assert kept.labels is objs.labels                       # no copy


def test_missing_dependency_degrades_studio_but_stops_the_line(monkeypatch):
    """A customer machine missing OpenCV must not quietly run a different pipeline.

    This is the direct answer to the registry's fail-open hazard: the designer can
    keep working (studio falls back to the numpy reference), but the line refuses
    to start rather than silently running a backend nobody validated.
    """
    monkeypatch.setattr(fslib, "_have_cv2", lambda: False)
    img = scene(64, 64, 4)

    with fslib.profile("studio"):
        assert isinstance(fslib.gauss(img, 1.5), FImage)      # degrades, keeps working

    with fslib.profile("industrial"):
        with pytest.raises(FsBackendError, match="no backend for profile"):
            fslib.gauss(img, 1.5)                             # refuses to run
