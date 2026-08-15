"""Language contracts for Fullseye Script (``fscript.py``).

The language is the layer a customer's inspection recipe is written in, so its
one non-negotiable property is that it never silently computes a wrong value:
anything it cannot express must be a parse/type error, never a quietly truncated
expression.  These tests pin that contract.

Regression at the head of the list: ``*`` was treated as a comment marker
*anywhere* on a line, so ``A := I * 2`` parsed as ``A := I`` and returned a wrong
result with no error.  HDevelop's ``*`` comment is a whole-line marker; mid-line
it is multiplication.
"""
from __future__ import annotations

import numpy as np
import pytest

import fscript


def run(src, **images):
    return fscript.run(src, images=images or None).vars


# --------------------------------------------------------------------------- #
# Lexer: comments vs multiplication  (regression)
# --------------------------------------------------------------------------- #
def test_multiplication_is_not_swallowed_as_a_comment():
    assert run("X := 6 * 7")["X"] == 42


def test_whole_line_star_is_still_a_comment():
    v = run("* a comment line\nX := 1\n   * indented comment\nY := 2")
    assert (v["X"], v["Y"]) == (1, 2)


def test_star_comment_after_code_is_multiplication_not_a_comment():
    # The old lexer dropped everything from the '*' on; the sum proves it does not.
    src = "S := 0\nfor I := 0 to 99\n  S := S + I * 2\nendfor"
    assert run(src)["S"] == 2 * sum(range(100))


@pytest.mark.parametrize("expr,want", [
    ("2*3", 6), ("2+3*4", 14), ("(2+3)*4", 20), ("7/2", 3.5),
    ("10%3", 1), ("2*3+4*5", 26), ("-3*2", -6),
])
def test_arithmetic_precedence(expr, want):
    assert run("X := %s" % expr)["X"] == pytest.approx(want)


# --------------------------------------------------------------------------- #
# Honest failure: unsupported syntax must raise, never guess
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("src", [
    "for Obj in Objects\nendfor",        # per-object 'for ... in' is not implemented
    "X := ",                             # incomplete expression
    "X := 1 1",                          # trailing token
    "if (1)\nX := 1",                    # missing endif
    "X := $",                            # illegal character
])
def test_unsupported_syntax_is_an_error(src):
    with pytest.raises(fscript.FScriptError):
        fscript.parse(src)


def test_check_reports_parse_errors_without_raising():
    assert fscript.check("X := 1") == []
    assert fscript.check("if (1)\nX := 1") != []


# --------------------------------------------------------------------------- #
# Control flow
# --------------------------------------------------------------------------- #
def test_if_elseif_else():
    src = ("if (X = 1)\n  R := 'one'\nelseif (X = 2)\n  R := 'two'\n"
           "else\n  R := 'many'\nendif")
    assert run(src, X=1)["R"] == "one"
    assert run(src, X=2)["R"] == "two"
    assert run(src, X=9)["R"] == "many"


def test_for_with_step_and_while_and_repeat():
    assert run("S := 0\nfor I := 0 to 10 by 2\n  S := S + I\nendfor")["S"] == 30
    assert run("I := 0\nwhile (I < 5)\n  I := I + 1\nendwhile")["I"] == 5
    assert run("I := 0\nrepeat\n  I := I + 1\nuntil (I >= 3)")["I"] == 3


def test_break_and_continue():
    assert run("S := 0\nfor I := 0 to 99\n  if (I >= 5)\n    break\n  endif\n"
               "  S := S + I\nendfor")["S"] == 10
    assert run("S := 0\nfor I := 0 to 5\n  if (I % 2 = 1)\n    continue\n  endif\n"
               "  S := S + I\nendfor")["S"] == 6


def test_step_budget_stops_runaway_loops():
    with pytest.raises(fscript.FScriptError):
        fscript.run("I := 0\nwhile (1)\n  I := I + 1\nendwhile", max_steps=5000)


# --------------------------------------------------------------------------- #
# The end-to-end rule-based algorithm the language exists for
# --------------------------------------------------------------------------- #
def _scene():
    """Three discs: two large, one below the area threshold."""
    img = np.zeros((64, 64), dtype=np.float64)
    yy, xx = np.mgrid[0:64, 0:64]
    for (cy, cx, r) in [(16, 16, 6), (16, 48, 6), (48, 32, 2)]:
        img[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = 1.0
    return img


def test_detect_measure_filter_branch_accumulate():
    src = """
Region := threshold(Image, 0.5, 1.0)
Objects := connection(Region)
N := count_obj(Objects)
Kept := 0
Rows := []
for I := 0 to N - 1
  Obj := select_obj(Objects, I)
  A := area(Obj)
  if (A >= 50)
    AC := area_center(Obj)
    Rows := Rows + [AC[1]]
    Kept := Kept + 1
  endif
endfor
"""
    v = run(src, Image=_scene())
    assert v["N"] == 3                      # three blobs found
    assert v["Kept"] == 2                   # the small one is filtered out
    assert len(v["Rows"]) == 2
    assert all(10.0 < r < 22.0 for r in v["Rows"])   # both large discs sit at row ~16


def test_value_kind_classifies_iconic_and_control():
    grey = _scene() * 0.6 + np.linspace(0, 0.3, 64)[None, :]     # genuinely grey
    v = run("Region := threshold(Image, 0.5, 1.0)\nObjects := connection(Region)\n"
            "N := count_obj(Objects)", Image=grey)
    kinds = {k: fscript.value_kind(x) for k, x in v.items()}
    assert kinds["Image"] == "image"
    assert kinds["Region"] == "region"
    assert kinds["Objects"] == "object"
    assert kinds["N"] == "control"


# --------------------------------------------------------------------------- #
# Pinned semantic defects — all one root cause: the language has no type model of
# its own and inherits numpy/Python semantics.  Each of these returns a WRONG
# ANSWER SILENTLY, and each survives a rewrite in any implementation language,
# so they are the increment-1 blockers named in docs/FSCRIPT_LANGUAGE.md.
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=(
    "Known L1 defect: `_norm01` divides by the image maximum, so the meaning of a "
    "threshold depends on the image CONTENT — one specular highlight or hot pixel "
    "elsewhere in the frame silently changes the judgement. An inspection library "
    "must carry the value range in the image type (FImage: dtype + range + domain), "
    "not infer it per call. See docs/FSCRIPT_LANGUAGE.md section 2."))
def test_threshold_is_independent_of_unrelated_bright_pixels():
    part = np.zeros((32, 32)); part[8:24, 8:24] = 120.0
    hot = part.copy(); hot[0, 0] = 250.0
    a = run("R := threshold(Image, 0.5, 1.0)\nA := area(R)", Image=part)["A"]
    b = run("R := threshold(Image, 0.5, 1.0)\nA := area(R)", Image=hot)["A"]
    assert a == b


@pytest.mark.xfail(strict=True, reason=(
    "Known control-model defect: '+' concatenates two numeric tuples. HALCON's "
    "tuple '+' is element-wise (with broadcast); concatenation is `[t1, t2]`. "
    "Shipping Python list semantics as the language contract is the migration trap "
    "flagged in the design review. See docs/FSCRIPT_LANGUAGE.md section 2 (Tuple)."))
def test_numeric_tuple_plus_is_elementwise_like_halcon():
    assert run("S := [1,2,3] + [10,20,30]")["S"] == [11, 22, 33]


@pytest.mark.xfail(strict=True, reason=(
    "Known defect: an iconic value is implicitly coerced to a bool via ndarray.any() "
    "in a condition. The spec says iconic values must not be implicitly truthy — "
    "`if (Region)` should be a type error, forcing `if (|Objects| > 0)` or an "
    "explicit predicate. See docs/FSCRIPT_LANGUAGE.md section 2."))
def test_iconic_in_a_condition_is_a_type_error():
    with pytest.raises(fscript.FScriptError):
        fscript.run("R := threshold(Image, 0.5, 1.0)\nif (R)\n  F := 1\nendif",
                    images={"Image": _scene()})


@pytest.mark.xfail(strict=True, reason=(
    "Known defect: comparing an image against a scalar yields an ndarray, which a "
    "condition then collapses with .any() — so `if (Image = 0)` reads as 'any pixel "
    "is 0', not 'the image is 0'. Element-wise comparison of an iconic value must be "
    "a type error or an explicit reduction. See docs/FSCRIPT_LANGUAGE.md section 2."))
def test_image_comparison_does_not_silently_reduce_with_any():
    with pytest.raises(fscript.FScriptError):
        fscript.run("if (Image = 0)\n  C := 1\nendif", images={"Image": _scene()})


@pytest.mark.xfail(strict=True, reason=(
    "Known type-model defect: iconic sort is INFERRED from pixel content "
    "(`_is_region` = at most two distinct values), so a legitimate grey image "
    "that happens to be binary is reported as a Region. The fix is the typed "
    "L1 model (FImage(pixels, domain) / Region as distinct classes) in "
    "docs/FSCRIPT_LANGUAGE.md section 2 — the sort must be carried, not guessed."))
def test_binary_valued_image_is_not_mistaken_for_a_region():
    assert fscript.value_kind(_scene()) == "image"
