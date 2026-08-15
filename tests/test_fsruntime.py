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
    with pytest.raises(FsNotReady, match="SHA-256 mismatch"):
        fsruntime.compile_recipe(tampered, profile="reference")


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
