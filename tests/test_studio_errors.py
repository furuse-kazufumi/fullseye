"""studio_errors(Studio 案 ⑦: 原因・場所・次の行動に分け、自動の修復を出さない)の門。

失敗は**本物の関数を本物の入力で呼んで**捕まえる(ステレオ・SPC・台帳の op・facade)。例外の文面を
こちらで書き写して照合すると、文面が変わっても緑のままになるため。文面を作るのは依存の欠落だけ
(環境に mujoco 等が入っているかで結果が変わるので、本物の ImportError の文面を写して投げる)。
"""
import numpy as np
import pytest

import api
import fullseye as fs
import opassist
import spc
import studio_errors as se

_RNG = np.random.default_rng(7)


def _catch(fn, *a, **k):
    with pytest.raises(Exception) as ei:
        fn(*a, **k)
    return ei.value


def _kinds(info):
    return [a["kind"] for a in info["actions"]]


# --------------------------------------------------------------------------- #
# 5 つの代表例                                                                 #
# --------------------------------------------------------------------------- #
def test_stereo_size_mismatch_names_both_sizes_and_never_resizes():
    left = np.zeros((1080, 1920))
    right = np.zeros((720, 1280))
    exc = _catch(fs.disparity_map, left, right)
    assert isinstance(exc, ValueError)            # 実在の関数が実際に投げる(文面はサイズを含まない)
    assert "1920" not in str(exc) and "1280" not in str(exc)
    info = se.explain_failure(exc, op_name="disparity_map", stage_index=2, inputs={
        "left": {"value": left, "file": "C:/shots/left.png"}, "right": {"value": right, "file": "right.png"}})
    assert info["class"] == "shape_mismatch"
    assert info["title"]["key"] == "err.shape_mismatch"
    ja, en = info["cause"]["ja"], info["cause"]["en"]
    for sz in ("1920×1080", "1280×720"):
        assert sz in ja and sz in en
    assert "left.png" in ja and "right.png" in ja
    rows = [e for e in info["evidence"] if e["kind"] == "input"]
    assert [r["shape"] for r in rows] == [(1080, 1920), (720, 1280)]
    assert [r["file"] for r in rows] == ["left.png", "right.png"]
    assert info["place"] == {"stage": 2, "op": "disparity_map", "arg": None}
    assert {"reselect_input", "show_inputs_side_by_side"} <= set(_kinds(info))
    assert info["raw"] == str(exc)
    # 自動で大きさを合わせる類は、種類にも文言にも無い
    blob = repr(info).lower()
    for bad in ("resize", "auto_fix", "autofix", "automatic", "自動"):
        assert bad not in blob, bad


def test_nan_input_reports_count_and_first_index():
    x = np.array([1.0, 2.0, np.nan, 4.0, np.inf])
    exc = _catch(spc.spc_cusum, x, target=2.0)
    info = se.explain_failure(exc, op_name="spc_cusum", stage_index=0, inputs=[x])
    assert info["class"] == "non_finite"
    f = info["evidence"][0]
    assert f["nonfinite"] == 2 and f["finite"] == 3 and f["first_nonfinite_index"] == (2,)
    assert "2" in info["cause"]["ja"] and "[2]" in info["cause"]["ja"]
    assert f["min"] == 1.0 and f["max"] == 4.0                    # 値域は有限な値だけから
    assert "reselect_input" in _kinds(info)
    # 2 次元でも位置は (行, 列)
    img = _RNG.random((6, 9))
    img[4, 7] = np.nan
    info2 = se.explain_failure(ValueError("x: has non-finite values (nan/inf)"), inputs=[img])
    assert info2["evidence"][0]["first_nonfinite_index"] == (4, 7)


def test_image_given_where_table_expected_names_both_sorts():
    img = _RNG.random((16, 16))
    exc = _catch(opassist.run, "gum_expanded", img)
    info = se.explain_failure(exc, op_name="gum_expanded", stage_index=1, inputs=[img])
    assert info["class"] == "wrong_sort"
    s = [e for e in info["evidence"] if e["kind"] == "sorts"][0]
    assert s == {"kind": "sorts", "expected": "table", "given": "image2d"}
    assert "table" in info["cause"]["en"] and "image2d" in info["cause"]["en"]
    assert "reselect_input" in _kinds(info)
    # 台帳の別の op でも、型の宣言(索引)から同じ判定になる
    exc2 = _catch(opassist.run, "chief_ray", img)
    info2 = se.explain_failure(exc2, op_name="chief_ray", inputs=[img])
    assert info2["class"] == "wrong_sort"


def test_wrong_sort_proposes_a_bridge_but_does_not_apply_it():
    mask = np.zeros((12, 12), bool)
    mask[3:6, 3:6] = True
    exc = TypeError("'float' object is not subscriptable")
    info = se.explain_failure(exc, op_name="sk_area_opening", inputs=[mask])
    assert info["class"] == "wrong_sort"
    ins = [a for a in info["actions"] if a["kind"] == "insert_stage"]
    assert ins and ins[0]["candidates"] and all(isinstance(c, str) for c in ins[0]["candidates"])


def test_out_of_range_knob_carries_the_range():
    sub = _RNG.random((5, 11))
    exc = _catch(spc.spc_xbar_r, sub)
    info = se.explain_failure(exc, op_name="spc_xbar_r", stage_index=3, inputs=[sub])
    assert info["class"] == "out_of_range"
    k = [e for e in info["evidence"] if e["kind"] == "knob"][0]
    assert k["arg"] == "n" and k["range"]["lo"] == 2.0 and k["range"]["hi"] == 10.0
    assert k["value"] == "11"
    assert info["place"]["arg"] == "n"
    assert "2..10" in info["cause"]["ja"] and "n" in info["cause"]["ja"]
    assert "edit_knob" in _kinds(info)
    # 開区間 (0, 1] の書き方も読む
    e2 = _catch(spc.spc_ewma, _RNG.random(30), target=0.0, sigma=1.0, lam=2.0) if hasattr(spc, "spc_ewma") else \
        ValueError("spc_ewma: lam (smoothing) must be in (0, 1], got 2.0")
    i2 = se.explain_failure(e2, op_name="spc_ewma")
    assert i2["class"] == "out_of_range"
    r = [e for e in i2["evidence"] if e["kind"] == "knob"][0]["range"]
    assert (r["lo"], r["hi"], r["lo_open"], r["hi_open"]) == (0.0, 1.0, True, False)


def test_missing_optional_dependency_names_the_extra_not_a_data_fix():
    exc = _catch(__import__, "fullseye_no_such_extra_module_xyz")
    assert isinstance(exc, ModuleNotFoundError)
    info = se.explain_failure(exc, op_name="some_op", inputs=[np.zeros((4, 4))])
    assert info["class"] == "dependency"
    dep = [e for e in info["evidence"] if e["kind"] == "dependency"][0]
    assert dep["package"] == "fullseye_no_such_extra_module_xyz"
    assert set(_kinds(info)) == {"open_log"}                     # 入力を直す提案は出さない
    # extra の名前: 既知の依存は ops.OPTIONAL_DEPS から
    e2 = ModuleNotFoundError("No module named 'skimage'", name="skimage")
    i2 = se.explain_failure(e2, op_name="sk_canny")
    dep2 = [e for e in i2["evidence"] if e["kind"] == "dependency"][0]
    assert dep2["extra"] == "skimage" and dep2["install"] == 'pip install "fullseye[skimage]"'
    assert "skimage" in i2["cause"]["ja"] and "skimage" in i2["cause"]["en"]
    # 本物の MissingBackendError(KeyError の子)も依存として読む
    e3 = api.MissingBackendError("operator 'sk_x' exists but is not available here; Install with "
                                 'pip install "fullseye[skimage]"')
    i3 = se.explain_failure(e3, op_name="sk_x")
    assert i3["class"] == "dependency" and i3["evidence"][0]["extra"] == "skimage"
    # 文面だけの ImportError(optional dependency mujoco)
    e4 = ImportError("pegsim: this function needs the optional dependency mujoco (pip install mujoco)")
    i4 = se.explain_failure(e4, op_name="peg_x")
    assert i4["class"] == "dependency" and i4["evidence"][0]["package"] == "mujoco"


def test_unknown_op_offers_the_nearest_names():
    exc = _catch(api.apply, np.zeros((8, 8)), "gausian")
    assert isinstance(exc, KeyError)
    info = se.explain_failure(exc, op_name="gausian", stage_index=0)
    assert info["class"] == "unknown_op"
    near = [e for e in info["evidence"] if e["kind"] == "nearest_ops"][0]["names"]
    assert "gaussian" in near
    from studio_search import nearest_op_names, search_zero_results_help
    assert near == nearest_op_names("gausian")                    # studio_search の助けと同じ答え
    assert "gaussian" in search_zero_results_help("gausian")["nearest_ops"]
    assert "gaussian" in info["actions"][0]["label"]["en"]
    assert info["actions"][0]["kind"] == "insert_stage"
    # 台帳側の未知の名前(ValueError)も同じ種類
    e2 = _catch(opassist.run, "no_such_ledger_op_zz", 1)
    assert se.explain_failure(e2, op_name="no_such_ledger_op_zz")["class"] == "unknown_op"


def test_empty_input_class():
    empty = np.zeros((0, 4))
    info = se.explain_failure(ValueError("spc_xbar_r: subgroups is empty"), op_name="spc_xbar_r", inputs=[empty])
    assert info["class"] == "empty"
    assert "reselect_input" in _kinds(info)
    # 空の配列は、文面が何であっても事実として見える
    info2 = se.explain_failure(RuntimeError("boom"), inputs=[empty])
    assert info2["class"] == "empty" and info2["evidence"][0]["shape"] == (0, 4)


def test_dimension_class():
    exc = _catch(spc.spc_cusum, _RNG.random((4, 4)), target=0.0)
    info = se.explain_failure(exc, op_name="spc_cusum", inputs=[_RNG.random((4, 4))])
    assert info["class"] == "dimension"
    assert "1" in info["cause"]["en"] and "2-D" in info["cause"]["en"]


# --------------------------------------------------------------------------- #
# 全例外で: 種類の外の行動が無い・落ちない・文面                               #
# --------------------------------------------------------------------------- #
class _BrokenStr(Exception):
    def __str__(self):                                           # noqa: D105
        raise RuntimeError("str() is broken")


class _Custom(Exception):
    pass


def _thirty():
    img = _RNG.random((8, 8))
    return [
        (ValueError("left/right must be equal-shape 2-D arrays"), "disparity_map", [img, np.zeros((4, 4))]),
        (ValueError("a: has non-finite values (nan/inf)"), "spc_cusum", [np.array([np.nan])]),
        (ValueError("subgroup size n must be 2..10, got n=11"), "spc_xbar_r", None),
        (ValueError("alpha must be in (0, 1), got 3"), None, None),
        (ValueError("window must be odd and >= 3"), "census", None),
        (ValueError("raytrace: radius must be > 0, got -1"), None, None),
        (ValueError("aim must be one of ('a', 'b'), got 'c'"), None, None),
        (ImportError("needs the optional dependency mujoco (pip install mujoco)"), None, None),
        (ModuleNotFoundError("No module named 'cv2'", name="cv2"), "cv_open", None),
        (KeyError("unknown operator 'zzz' — try the op name"), "zzz", None),
        (KeyError("not-a-op"), None, None),
        (ValueError("opassist: unknown op 'q' (not in any ledger)"), "q", None),
        (TypeError("'NoneType' object is not subscriptable"), "gum_expanded", [img]),
        (IndexError("only integers, slices"), "chief_ray", [img]),
        (AttributeError("'numpy.ndarray' object has no attribute 'keys'"), "gum_expanded", [img]),
        (ValueError("expected the dict returned by lens_system(), got 'ndarray'"), "chief_ray", [img]),
        (ValueError("img must be 2-D"), None, [np.zeros(5)]),
        (ValueError("disp must be a 2-D (H, W) map"), None, None),
        (ValueError("subgroups is empty"), None, [np.zeros((0,))]),
        (RuntimeError("something odd"), "x", None),
        (ZeroDivisionError("division by zero"), None, None),
        (MemoryError(), None, None),
        (OSError(2, "No such file or directory"), None, None),
        (UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"), None, None),
        (Exception(), None, None),
        (Exception("多言語の文面: 非有限(NaN/Inf)を含む入力は扱えない"), None, [np.array([np.nan, 1.0])]),
        (_Custom("custom"), "x", [{"a": 1}]),
        (_BrokenStr(), "x", None),
        (ValueError(b"bytes message", 3, None), None, None),
        (ValueError("x" * 5000), None, None),
    ]


def test_no_action_kind_outside_the_allowed_set_for_30_exceptions():
    cases = _thirty()
    assert len(cases) == 30
    seen_classes = set()
    for exc, op, inputs in cases:
        info = se.explain_failure(exc, op_name=op, stage_index=4, inputs=inputs)
        assert len(info["actions"]) >= 1, exc
        for a in info["actions"]:
            assert a["kind"] in se.ACTION_KINDS, (exc, a)
            assert a["kind"] in {"reselect_input", "show_inputs_side_by_side", "open_log", "edit_knob", "insert_stage"}
            assert not any(w in a["kind"] for w in ("auto", "resize", "fix", "match"))
        assert info["place"]["stage"] == 4 and info["place"]["op"] == op
        assert isinstance(info["raw"], str) and info["exc_type"] == type(exc).__name__
        assert info["class"] in se.FAILURE_CLASSES
        assert info["title"]["key"] == "err." + info["class"]
        seen_classes.add(info["class"])
    assert seen_classes >= {"shape_mismatch", "non_finite", "out_of_range", "dependency", "unknown_op",
                            "wrong_sort", "empty", "dimension", "generic"}


def test_fallback_never_raises_on_arbitrary_exception_subclasses():
    cases = _thirty()
    assert len(cases) == 30
    for exc, op, inputs in cases:
        info = se.explain_failure(exc, op_name=op, inputs=inputs)
        assert se.format_failure(info, "ja") and se.format_failure(info, "en")
    info = se.explain_failure(_BrokenStr(), op_name="x", stage_index=1)
    assert info["class"] == "generic" and info["place"] == {"stage": 1, "op": "x", "arg": None}
    assert "BrokenStr" in info["raw"] or "unprintable" in info["raw"]
    # 例外でない値・壊れた入力でも落ちない
    assert se.explain_failure("plain text", op_name="y")["raw"] == "plain text"
    assert se.explain_failure(None)["class"] == "generic"
    assert se.explain_failure(ValueError("v"), inputs=object())["place"]["op"] is None
    weird = se.explain_failure(ValueError("v"), inputs={"a": np.array(["x", "y"]), "b": object(), "c": None})
    assert [e["type"] for e in weird["evidence"] if e["kind"] == "input"] == ["ndarray", "object", "NoneType"]


def test_generic_still_fills_place_and_raw():
    info = se.explain_failure(RuntimeError("something odd\nsecond line"), op_name="blur", stage_index=0)
    assert info["class"] == "generic"
    assert info["place"] == {"stage": 0, "op": "blur", "arg": None}
    assert info["raw"] == "something odd\nsecond line"
    assert "something odd" in info["cause"]["ja"] and "second line" not in info["cause"]["ja"]
    assert _kinds(info) == ["open_log"]


# --------------------------------------------------------------------------- #
# Problems 欄の文面                                                            #
# --------------------------------------------------------------------------- #
def _stereo_info():
    left, right = np.zeros((1080, 1920)), np.zeros((720, 1280))
    exc = _catch(fs.disparity_map, left, right)
    return se.explain_failure(exc, op_name="disparity_map", stage_index=2, inputs={
        "left": {"value": left, "file": "left.png"}, "right": {"value": right, "file": "right.png"}})


def test_format_failure_has_three_headers_and_the_evidence_table():
    info = _stereo_info()
    ja = se.format_failure(info, "ja")
    en = se.format_failure(info, "en")
    for h in ("原因", "場所", "次にできること"):
        assert h in ja
    for h in ("Cause", "Place", "What you can do next"):
        assert h in en
    assert ja.index("原因") < ja.index("場所") < ja.index("次にできること")
    assert en.index("Cause") < en.index("Place") < en.index("What you can do next")
    for txt in (ja, en):
        assert "1920×1080" in txt and "1280×720" in txt and "left.png" in txt and "right.png" in txt
        assert "disparity_map" in txt
        assert "left/right must be equal-shape 2-D arrays" in txt          # 生の文面も末尾に残す
    assert "段 3" in ja and "stage 3" in en
    for txt in (ja, en):
        low = txt.lower()
        assert "自動" not in txt and "automatic" not in low and "automatically" not in low


def test_format_failure_for_every_class_has_no_automatic_wording():
    for exc, op, inputs in _thirty():
        info = se.explain_failure(exc, op_name=op, stage_index=0, inputs=inputs)
        for lg in ("ja", "en"):
            txt = se.format_failure(info, lg)
            # 例外の生の文面(raw)は利用者の入力なので除き、こちらの書いた文だけを調べる
            mine = txt.split("\n詳細\n")[0].split("\nDetail\n")[0]
            assert "自動" not in mine and "automatic" not in mine.lower(), (lg, exc)


def test_localize_helper():
    assert se.localize({"ja": "あ", "en": "a"}, "en") == "a"
    assert se.localize({"ja": "あ"}, "en") == "あ"
    assert se.localize("plain") == "plain" and se.localize(None) == ""


def test_proposals_only_no_input_is_modified():
    left, right = np.zeros((10, 20)), np.zeros((5, 8))
    before = (left.copy(), right.copy())
    se.explain_failure(ValueError("left/right must be equal-shape 2-D arrays"), inputs=[left, right])
    assert left.shape == (10, 20) and right.shape == (5, 8)
    assert np.array_equal(left, before[0]) and np.array_equal(right, before[1])
