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


# --------------------------------------------------------------------------- #
# 2026-09 audit (docs/FSCRIPT_LANGUAGE.md section 2b) — each finding pinned
# --------------------------------------------------------------------------- #
def _err(src, **images):
    with pytest.raises(fscript.FScriptError) as ei:
        fscript.run(src, images=images or None)
    return ei.value


# F1: every arithmetic operator is element-wise on tuples; no Python repetition
@pytest.mark.parametrize("expr,want", [
    ("[1,2] * 2", [2, 4]), ("2 * [1,2]", [2, 4]), ("[1,2] - [1,1]", [0, 1]),
    ("[2,4] / 2", [1.0, 2.0]), ("[3,4] % 2", [1, 0]), ("-[1,2]", [-1, -2]),
    ("[1,2,3] * [2,2,2]", [2, 4, 6]),
])
def test_tuple_arithmetic_is_elementwise_for_every_operator(expr, want):
    assert run("X := %s" % expr)["X"] == want


def test_string_times_number_is_an_error_not_repetition():
    assert "'*'" in _err("X := 'ab' * 3").msg
    _err("X := 'a' + 1")
    _err("X := -'a'")
    assert run("X := 'a' + 'b'")["X"] == "ab"           # concatenation stays


def test_tuple_arithmetic_length_mismatch_is_an_error():
    _err("X := [1,2] * [1,2,3]")


# F2: one grey unit — statistics and threshold both relative to the declared range
def test_threshold_and_gray_statistics_share_one_unit_on_uint8():
    u8 = np.zeros((16, 16), np.uint8); u8[4:12, 4:12] = 200
    v = run("M := mean_gray(Image)\nMx := max_gray(Image)\nMn := min_gray(Image)\n"
            "R := threshold(Image, M, Mx)\nA := area(R)", Image=u8)
    assert v["Mx"] == pytest.approx(200 / 255)
    assert v["Mn"] == 0.0
    assert v["M"] == pytest.approx(u8.mean() / 255)
    assert v["A"] == 64                                # the bright square, not 0
    # the same script on the same scene as float 0..1 gives the same answers
    w = run("M := mean_gray(Image)\nMx := max_gray(Image)\nR := threshold(Image, M, Mx)\n"
            "A := area(R)", Image=u8.astype(np.float64) / 255.0)
    assert w["A"] == 64 and w["Mx"] == pytest.approx(v["Mx"])


# F3: morphology radius
def test_morphology_radius_zero_is_identity_and_bad_radii_are_errors():
    m = np.zeros((16, 16), bool); m[4:8, 4:8] = True
    v = run("D := dilation(R, 0)\nE := erosion(R, 0)\nD1 := dilation(R, 1)\n"
            "AD := area(D)\nAE := area(E)\nAD1 := area(D1)", R=m)
    assert v["AD"] == 16 and v["AE"] == 16 and v["AD1"] > 16
    assert "negative" in _err("D := dilation(R, -3)", R=m).msg
    assert "whole number" in _err("D := dilation(R, 0.4)", R=m).msg
    assert "whole number" in _err("E := erosion(R, 1.5)", R=m).msg
    assert run("D := dilation(R, 2.0)\nA := area(D)", R=m)["A"] > 16   # integral float is fine


# F4: a length-1 tuple is its scalar; longer tuples have no truth value
def test_length_one_tuple_behaves_as_its_scalar():
    assert run("X := [1] = 1")["X"] is True
    assert run("X := not [0]")["X"] is True
    assert run("if ([0])\n R := 1\nelse\n R := 0\nendif")["R"] == 0
    assert run("if ([1])\n R := 1\nelse\n R := 0\nendif")["R"] == 1
    e = _err("if ([1,2])\n R := 1\nendif")
    assert "length 2" in e.msg and e.line == 1
    _err("X := [1,2] < 1")


# F6: break/continue outside a loop
@pytest.mark.parametrize("src", ["break", "continue", "if (1)\n break\nendif",
                                 "for I := 0 to 2\nendfor\nbreak"])
def test_break_or_continue_outside_a_loop_is_a_parse_error(src):
    with pytest.raises(fscript.FScriptError) as ei:
        fscript.parse(src)
    assert "outside loop" in ei.value.msg


def test_stray_break_in_a_hand_built_ast_is_an_fscript_error():
    with pytest.raises(fscript.FScriptError):
        fscript.run([fscript.Break(1)])


# F7: index assignment, and tuples are values (no aliasing)
def test_index_assignment_works_and_does_not_alias():
    v = run("A := [1,2,3]\nB := A\nB[0] := 9\nC := B[0] + A[0]")
    assert v["A"] == [1, 2, 3] and v["B"] == [9, 2, 3] and v["C"] == 10
    seeded = [1, 2, 3]
    out = run("T[1] := 7", T=seeded)
    assert out["T"] == [1, 7, 3] and seeded == [1, 2, 3]   # the caller's list is untouched
    _err("T := [1,2]\nT[5] := 0")
    _err("T := [1,2]\nT[0] := [1,2]")
    _err("S := 'ab'\nS[0] := 'c'")
    with pytest.raises(fscript.FScriptError):
        fscript.parse("area(1) := 2")


# F8: indices are validated, never a raw ValueError/TypeError
@pytest.mark.parametrize("idx", ["-1", "1.9", "'1'", "'a'", "3", "true"])
def test_bad_indices_are_fscript_errors(idx):
    e = _err("T := [1,2,3]\nX := T[%s]" % idx)
    assert e.line == 2


def test_integral_float_index_is_accepted():
    assert run("T := [1,2,3]\nX := T[2.0]")["X"] == 3
    assert run("S := 'abc'\nX := S[1]")["X"] == "b"


def test_select_obj_index_is_validated():
    m = np.zeros((16, 16), bool); m[4:8, 4:8] = True
    e = _err("O := connection(R)\nS := select_obj(O, 0.9)", R=m)
    assert "integer" in e.msg and e.line == 2
    _err("O := connection(R)\nS := select_obj(O, 1)", R=m)     # only one object


# F9: numerals, raw exceptions, nesting, check()
@pytest.mark.parametrize("lit", ["1.2.3", "2e", "1e5e3", "1e400", "３", "²"])
def test_bad_numerals_are_fscript_errors(lit):
    with pytest.raises(fscript.FScriptError):
        fscript.parse("X := %s + 1" % lit)
    assert fscript.check("X := %s + 1" % lit) != []


@pytest.mark.parametrize("lit,want", [("12", 12), ("1.5", 1.5), (".5", 0.5), ("1.", 1.0),
                                      ("1e-3", 1e-3), ("2.5E+4", 2.5e4)])
def test_good_numerals(lit, want):
    assert run("X := %s" % lit)["X"] == want


def test_for_bounds_and_op_arguments_must_be_numbers():
    assert _err("for I := 'a' to 5\nendfor").line == 1
    _err("for I := 0 to [1,2]\nendfor")
    assert "must be a number" in _err("R := gaussian(Image, 'x')", Image=np.zeros((4, 4))).msg
    assert "must be a number" in _err("R := gauss_image(Image, 'x')", Image=np.zeros((4, 4))).msg


def test_deep_nesting_is_an_fscript_error_not_a_recursion_error():
    for src in ("X := " + "(" * 400 + "1" + ")" * 400,
                "X := " + "-" * 500 + "1",
                "X := " + "not " * 500 + "1",
                "X := 0\n" + "if (X >= 0)\n" * 300 + "X := 1\n" + "endif\n" * 300):
        with pytest.raises(fscript.FScriptError):
            fscript.parse(src)
        assert fscript.check(src)                     # a message, never a raise
    with pytest.raises(fscript.FScriptError):        # shallow to parse, deep to evaluate
        fscript.run("X := " + "1+" * 2000 + "1")
    assert run("X := " + "1+" * 150 + "1")["X"] == 151


# F10: string literals
def test_string_literal_cannot_span_lines_and_has_two_escapes():
    e = _err("X := 'abc\ndef'\nY := 1")
    assert "unterminated" in e.msg and e.line == 1
    BS = chr(92)
    assert run("X := 'a" + BS + "'b'")["X"] == "a'b"
    assert run("X := 'a" + BS + BS + "b'")["X"] == "a" + BS + "b"
    assert run("X := 'C:" + BS + "img" + BS + "a.png'")["X"] == "C:" + BS + "img" + BS + "a.png"


# F11: parenthesised comparisons and condition headers
def test_parenthesised_comparison_is_not_a_chain():
    assert run("X := 5\nOK := (X > 3) = true")["OK"] is True
    assert run("OK := (1 < 2) = (2 < 3)")["OK"] is True
    with pytest.raises(fscript.FScriptError):
        fscript.parse("OK := 0 <= X <= 10")


def test_condition_header_is_one_expression_up_to_end_of_line():
    assert run("X := 1\nY := 0\nif (X = 1) or (Y = 1)\n R := 'yes'\nendif")["R"] == "yes"
    assert run("X := 1\nY := 0\nif (X = 1) and not (Y = 1)\n R := 'yes'\nendif")["R"] == "yes"
    assert run("I := 0\nwhile (I < 3) and (I >= 0)\n I := I + 1\nendwhile")["I"] == 3
    assert run("I := 0\nrepeat\n I := I + 1\nuntil (I >= 2) or (I < 0)")["I"] == 2
    for bad in ("X := 1\nif (X = 1) -1\n R := 'yes'\nendif",
                "for I := 0 to 2 X := I\nendfor",
                "if (1) X := 2\nendif"):
        with pytest.raises(fscript.FScriptError):
            fscript.parse(bad)


# F13: read_image is confined to base_dir
def test_read_image_cannot_leave_base_dir(tmp_path):
    """脱出を試みるパスは base_dir の外を読めない。

    ★2026-09-05 修正: 以前は `"C:/Windows/win.ini"` を脱出例に入れていたが、
    POSIX では `os.path.isabs("C:/...")` が False なので**相対パスとして
    base_dir の中に閉じ込められる**(= 安全側)。「outside」が出ないのは
    実装の穴ではなくテストの Windows 前提であり、Linux CI ではこれが赤に
    なっていた。脱出例は**どの OS でも脱出になる形**で書く。
    """
    escapes = ["../../x.png", "../../../../etc/passwd", str(tmp_path.parent / "x.png")]
    escapes.append("C:/Windows/win.ini" if os.name == "nt" else "/etc/passwd")
    for p in escapes:
        e = _err_with_base("I := read_image(%r)" % p, str(tmp_path))
        assert "outside" in e.msg and e.line == 1, f"{p!r} が拒否されていない: {e.msg}"
    inside = tmp_path / "sub"; inside.mkdir()
    e = _err_with_base("I := read_image('sub/missing.png')", str(tmp_path))
    assert "outside" not in e.msg                    # resolved inside, then a decode error


def test_a_windows_drive_path_stays_inside_the_sandbox_on_posix(tmp_path):
    """POSIX で `"C:/..."` は絶対パスではないので、**中に閉じ込められる**。

    脱出しないことが要点。エラー文言は「外に出ようとした」ではなく
    「そんなファイルは無い」側になる —— それが正しい。
    """
    if os.name == "nt":
        pytest.skip("Windows では C:/ は本物の絶対パス(上のテストが見ている)")
    e = _err_with_base("I := read_image('C:/Windows/win.ini')", str(tmp_path))
    assert "outside" not in e.msg, "POSIX で脱出扱いになっている: " + e.msg


def _err_with_base(src, base_dir):
    with pytest.raises(fscript.FScriptError) as ei:
        fscript.run(src, base_dir=base_dir)
    return ei.value


# F14: builtin/type errors carry the calling line
def test_builtin_and_truth_errors_carry_their_line():
    assert _err("X := 1\nY := 2\nZ := area(5)").line == 3
    assert _err("X := 1\nif (Image)\n Y := 1\nendif", Image=np.zeros((4, 4))).line == 2
    assert _err("X := 1\nwhile (Image)\nendwhile", Image=np.zeros((4, 4))).line == 2
    assert _err("O := connection(R)\nS := select_shape(O, 'Area', 1, 100)",
                R=np.zeros((4, 4), bool)).line == 2
