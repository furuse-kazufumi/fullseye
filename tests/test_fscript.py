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
    Rows := [Rows, AC[1]]
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
# Closed semantic defects (increment I-2) — all one root cause: the language used
# to have no type model of its own and inherited numpy/Python semantics, so each
# returned a WRONG ANSWER SILENTLY.  Loading the language onto the typed fslib
# model (FImage carries its value range; Region/ObjectSet are distinct sorts with
# no truth value; Tuple '+' is element-wise) closes all five.  They are pinned
# here as regressions.  See docs/FSCRIPT_DECISION.md section 1.6.
# --------------------------------------------------------------------------- #
def test_threshold_is_independent_of_unrelated_bright_pixels():
    """Defect 2: `_norm01` divided by the frame maximum, so one specular highlight
    silently rescaled the whole image and flipped a threshold.  With the value
    range carried by FImage (from the dtype/sensor, not the pixels), a hot pixel
    brighter than the declared range changes nothing about the measured part."""
    part = np.zeros((32, 32), dtype=np.float32); part[8:24, 8:24] = 0.6
    hot = part.copy(); hot[0, 0] = 5.0                  # a specular highlight, out of 0..1 range
    src = "R := threshold(Image, 0.4, 1.0)\nA := area(R)"
    a = run(src, Image=part)["A"]
    b = run(src, Image=hot)["A"]
    assert a == b == 16 * 16


def test_numeric_tuple_plus_is_elementwise_like_halcon():
    """Defect 3: '+' concatenated numeric tuples (Python list semantics); HALCON's
    tuple '+' is element-wise and `[t1, t2]` is concatenation."""
    assert run("S := [1,2,3] + [10,20,30]")["S"] == [11, 22, 33]


def test_iconic_in_a_condition_is_a_type_error():
    """Defect 4: an iconic value was coerced to bool via ndarray.any() in a
    condition; it must force an explicit predicate instead."""
    with pytest.raises(fscript.FScriptError):
        fscript.run("R := threshold(Image, 0.5, 1.0)\nif (R)\n  F := 1\nendif",
                    images={"Image": _scene()})


def test_image_comparison_does_not_silently_reduce_with_any():
    """Defect 5: `if (Image = 0)` compared an image to a scalar and collapsed the
    array with .any(), reading as 'any pixel is 0'.  Comparing an iconic value is
    now a type error that demands an explicit reduction."""
    with pytest.raises(fscript.FScriptError):
        fscript.run("if (Image = 0)\n  C := 1\nendif", images={"Image": _scene()})


def test_chained_comparison_is_a_parse_error_not_a_wrong_boolean():
    # `0 <= X <= 10` would silently parse as `(0<=X)<=10` and be True for X=100.
    with pytest.raises(fscript.FScriptError):
        fscript.parse("if (0 <= X <= 10)\n  Y := 1\nendif")
    assert run("X := 5\nOK := (0 <= X) and (X <= 10)")["OK"] is True
    assert run("X := 100\nOK := (0 <= X) and (X <= 10)")["OK"] is False


def test_not_binds_looser_than_comparison():
    # `not 1 = 2` must read as `not (1 = 2)` = True, not `(not 1) = 2` = False.
    assert run("R := not 1 = 2")["R"] is True
    assert run("A := not (1 = 2) and (3 > 2)")["A"] is True


def test_arithmetic_on_an_iconic_value_is_a_type_error():
    # `-`, `*`, `/`, `%` were unguarded (only `+` was), letting silent pixel math in.
    for op in ("*", "-", "/"):
        with pytest.raises(fscript.FScriptError):
            fscript.run("Y := Image %s 2.0" % op,
                        images={"Image": np.zeros((4, 4, 3), np.uint8)})


def test_empty_body_loop_still_hits_the_step_limit():
    # An empty body runs zero statements, so the per-iteration tick must bound it.
    with pytest.raises(fscript.FScriptError):
        fscript.run("while (1 = 1)\nendwhile", max_steps=5000)
    with pytest.raises(fscript.FScriptError):
        fscript.run("repeat\nuntil (1 = 2)", max_steps=5000)


def test_extra_argument_to_a_registry_op_is_an_error_not_a_silent_drop():
    """The long-tail wrapper calls every registered op as RT[name](input, a, b).
    A 4th argument was dropped in silence, so `gaussian(Image, 0.3, 0.7, 999)`
    ran with the knobs of the 3-argument call and returned a wrong-by-omission
    result with no error."""
    img = _scene()
    with pytest.raises(fscript.FScriptError):
        fscript.run("R := gaussian(Image, 0.3, 0.7, 999)", images={"Image": img})
    # the (input, a, b) happy path is untouched
    assert fscript.value_kind(
        run("R := gaussian(Image, 0.3, 0.7)", Image=img)["R"]) == "image"


def test_binary_valued_image_is_not_mistaken_for_a_region():
    """The sort is carried by the type, not inferred from content: a grey image
    that happens to be binary-valued is still an image, never a Region."""
    assert fscript.value_kind(_scene()) == "image"
