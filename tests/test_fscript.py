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
    v = run("Region := threshold(Image, 0.5, 1.0)\nObjects := connection(Region)\n"
            "N := count_obj(Objects)", Image=_scene())
    kinds = {k: fscript.value_kind(x) for k, x in v.items()}
    assert kinds["Image"] == "image"
    assert kinds["Region"] == "region"
    assert kinds["Objects"] == "object"
    assert kinds["N"] == "control"
