"""Runtime load-time gate — a recipe must PROVE it is safe before it may judge.

These pin the fail-closed contract of ``fsruntime`` (docs/FSCRIPT_DECISION.md
judgment 4/5, R4/R5): ABI major, source hash, backend availability, and golden
"same judgement" each block a load, and nothing degrades.
"""
from __future__ import annotations

import numpy as np
import pytest

import fslib
import fsruntime
from fsruntime import FsNotReady, GoldenVector, Recipe

HAVE_CV2 = "cv2" in fslib.backends_for("gauss")
needs_cv2 = pytest.mark.skipif(not HAVE_CV2, reason="OpenCV not installed")


RECIPE_SRC = """
Region := threshold(Image, 0.4, 1.0)
Objects := connection(Region)
N := count_obj(Objects)
"""


def scene(n=64):
    """Three bright discs on a dark field (float 0..1)."""
    img = np.zeros((n, n), dtype=np.float32)
    yy, xx = np.mgrid[0:n, 0:n]
    for (cy, cx, r) in [(16, 16, 6), (16, 48, 6), (48, 32, 6)]:
        img[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = 1.0
    return img


def golden(n_expected=3):
    return GoldenVector(inputs={"Image": scene()}, expect={"N": n_expected})


def test_a_valid_recipe_loads_and_runs():
    ready = fsruntime.compile_recipe(
        fsruntime.sign(RECIPE_SRC, goldens=[golden(3)]), profile="reference")
    out = ready.run({"Image": scene()})
    assert out["N"] == 3
    assert ready.source_sha256


def test_abi_major_mismatch_is_refused():
    r = Recipe(RECIPE_SRC, abi_major=fsruntime.ABI_VERSION_MAJOR + 1, goldens=(golden(),))
    with pytest.raises(FsNotReady, match="ABI major"):
        fsruntime.compile_recipe(r, profile="reference")


def test_a_tampered_source_is_refused():
    signed = fsruntime.sign(RECIPE_SRC, goldens=[golden()])
    tampered = Recipe(RECIPE_SRC + "\nN := 0\n", abi_major=signed.abi_major,
                      goldens=signed.goldens, source_sha256=signed.source_sha256)
    with pytest.raises(FsNotReady, match="digest mismatch"):
        fsruntime.compile_recipe(tampered, profile="reference")


def test_swapping_goldens_on_a_signed_recipe_is_refused():
    # goldens are inside the digest now, so gutting them (goldens=()) after signing
    # must break the hash rather than silently pass.
    signed = fsruntime.sign(RECIPE_SRC, goldens=[golden(3)])
    gutted = Recipe(RECIPE_SRC, abi_major=signed.abi_major, goldens=(),
                    source_sha256=signed.source_sha256)
    with pytest.raises(FsNotReady, match="digest mismatch"):
        fsruntime.compile_recipe(gutted, profile="reference")


def test_a_wrong_golden_is_refused():
    r = fsruntime.sign(RECIPE_SRC, goldens=[golden(99)])       # claims N should be 99
    with pytest.raises(FsNotReady, match="golden mismatch"):
        fsruntime.compile_recipe(r, profile="reference")


def test_a_syntax_error_is_refused():
    with pytest.raises(FsNotReady, match="does not parse"):
        fsruntime.compile_recipe(Recipe("N := ", goldens=()), profile="reference")


def test_missing_native_backend_stops_the_line_but_not_the_studio(monkeypatch):
    """A machine missing OpenCV must refuse the industrial load, not run numpy."""
    monkeypatch.setattr(fslib, "_have_cv2", lambda: False)
    r = fsruntime.sign(RECIPE_SRC, goldens=[golden(3)])
    with pytest.raises(FsNotReady, match="no working backend"):
        fsruntime.compile_recipe(r, profile="industrial")
    ready = fsruntime.compile_recipe(r, profile="studio")     # degrades to numpy
    assert ready.run({"Image": scene()})["N"] == 3


def test_unsigned_recipe_loads_when_goldens_pass():
    r = Recipe(RECIPE_SRC, goldens=(golden(3),))              # no source_sha256
    ready = fsruntime.compile_recipe(r, profile="reference")
    assert ready.op_names.issuperset({"threshold", "connection", "count_obj"})


def test_golden_missing_variable_is_refused():
    r = fsruntime.sign(RECIPE_SRC, goldens=[GoldenVector({"Image": scene()}, {"Missing": 1})])
    with pytest.raises(FsNotReady, match="did not produce"):
        fsruntime.compile_recipe(r, profile="reference")


def test_a_signed_recipe_that_matches_loads():
    signed = fsruntime.sign(RECIPE_SRC, goldens=[golden(3)], build_id="build-2026.08")
    ready = fsruntime.compile_recipe(signed, profile="reference")
    assert ready.build_id == "build-2026.08"
    assert ready.source_sha256 == signed.digest()


# --------------------------------------------------------------------------- #
# The resident Runtime — PLC verdicts + tail mitigations + the READY gate.
# --------------------------------------------------------------------------- #
ERR_SRC = """
R := threshold(Image, 0.5, 1.0)
Objs := connection(R)
X := area(select_obj(Objs, 99))
"""


def test_runtime_starts_ready_and_returns_ok():
    rt = fsruntime.FullseyeRuntime.start(
        fsruntime.sign(RECIPE_SRC, goldens=[golden(3)]), profile="reference")
    v = rt.inspect({"Image": scene()})
    assert v.status == "ok"
    assert v.result["N"] == 3
    assert v.elapsed_ms > 0.0


def test_runtime_ng_verdict_via_judge():
    rt = fsruntime.FullseyeRuntime.start(
        fsruntime.sign(RECIPE_SRC, goldens=[golden(3)]), profile="reference")
    v = rt.inspect({"Image": scene()}, judge=lambda out: out["N"] > 2)
    assert v.status == "ng"


def test_runtime_error_on_operator_failure():
    # No goldens (the failure is input-independent, so it would block the load);
    # the operator error must surface as ERROR, never a benign value.
    rt = fsruntime.FullseyeRuntime.start(Recipe(ERR_SRC, goldens=()), profile="reference")
    v = rt.inspect({"Image": scene()})
    assert v.status == "error"
    assert "operator error" in v.detail


def test_runtime_timeout_when_deadline_exceeded():
    rt = fsruntime.FullseyeRuntime.start(
        fsruntime.sign(RECIPE_SRC, goldens=[golden(3)]),
        profile="reference", deadline_ms=0.0001)
    v = rt.inspect({"Image": scene()})
    assert v.status == "timeout"
    assert v.result["N"] == 3          # the late result is attached for the PLC
    assert v.elapsed_ms > 0.0001


def test_runtime_refuses_to_start_on_a_failed_load():
    with pytest.raises(FsNotReady, match="golden mismatch"):
        fsruntime.FullseyeRuntime.start(
            fsruntime.sign(RECIPE_SRC, goldens=[golden(99)]), profile="reference")


def test_verdict_status_is_validated():
    with pytest.raises(ValueError):
        fsruntime.Verdict("bogus")
    assert fsruntime.Verdict("ok").status == "ok"


def test_runtime_applies_cv2_thread_bound_when_asked():
    # The tail-mitigation knob is applied at start (no-op flagged False if cv2 or
    # the platform can't honour it); it never raises.
    rt = fsruntime.FullseyeRuntime.start(
        Recipe(RECIPE_SRC, goldens=()), profile="reference", cv2_threads=1)
    assert isinstance(rt.cv2_threads_bounded, bool)


# --------------------------------------------------------------------------- #
# Industrial fail-closed hardening (from the adversarial gate review).
# --------------------------------------------------------------------------- #
def test_industrial_refuses_an_unsigned_recipe():
    with pytest.raises(FsNotReady, match="signed recipe"):
        fsruntime.compile_recipe(Recipe(RECIPE_SRC, goldens=(golden(3),)),
                                 profile="industrial")


def test_industrial_requires_at_least_one_golden():
    with pytest.raises(FsNotReady, match="at least one golden"):
        fsruntime.compile_recipe(fsruntime.sign(RECIPE_SRC), profile="industrial")


def test_industrial_forbids_registry_longtail_ops():
    # `emboss` is not a curated builtin; on a line it would dispatch through the
    # fail-open registry, so the industrial gate must refuse it at load — whether
    # or not the op happens to exist.
    src = "Out := emboss(Image)\nM := mean_gray(Out)"
    r = fsruntime.sign(src, goldens=[GoldenVector({"Image": scene()}, {"M": 0.0}, tol=1e9)])
    with pytest.raises(FsNotReady, match="un-vetted operator"):
        fsruntime.compile_recipe(r, profile="industrial")


def test_a_golden_with_empty_expect_is_refused():
    r = fsruntime.sign(RECIPE_SRC, goldens=[GoldenVector({"Image": scene()}, {})])
    with pytest.raises(FsNotReady, match="asserts nothing"):
        fsruntime.compile_recipe(r, profile="reference")


def test_a_nan_result_does_not_pass_a_golden():
    # A NaN would sail through `abs(got-exp) > tol` (IEEE); it must be rejected.
    src = "M := mean_gray(Image)"
    nan_img = np.full((16, 16), np.nan, dtype=np.float32)
    r = fsruntime.sign(src, goldens=[GoldenVector({"Image": nan_img}, {"M": 0.5}, tol=1e9)])
    with pytest.raises(FsNotReady, match="golden mismatch"):
        fsruntime.compile_recipe(r, profile="reference")


def test_a_numpy_scalar_expectation_honours_tolerance():
    # expect authored as a numpy scalar must still use the tolerance branch,
    # not fall through to an exact compare.
    src = "M := mean_gray(Image)"
    img = np.full((16, 16), 0.5, np.float32)
    r = fsruntime.sign(src, goldens=[GoldenVector({"Image": img},
                                                  {"M": np.float32(0.5001)}, tol=1e-2)])
    ready = fsruntime.compile_recipe(r, profile="reference")   # must NOT raise
    assert ready.run({"Image": img})["M"] == pytest.approx(0.5, abs=1e-3)


@needs_cv2
def test_industrial_loads_a_signed_recipe_with_a_golden_and_only_builtins():
    # The happy path for the strict profile: signed, ≥1 golden, only fslib ops.
    r = fsruntime.sign(RECIPE_SRC, goldens=[golden(3)])
    ready = fsruntime.compile_recipe(r, profile="industrial")
    v = fsruntime.FullseyeRuntime(ready).inspect({"Image": scene()})
    assert v.status == "ok" and v.result["N"] == 3
