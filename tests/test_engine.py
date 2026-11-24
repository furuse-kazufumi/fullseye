"""Tests for FullseyeEngine — the pipeline runtime (the HDevEngine analog).

Load a pipeline (JSON / ops string / dict), introspect its sorts, validate it,
tune knobs, and execute it (whole / up-to / stepwise). These are the guarantees
another project (or the embedded runtime) relies on."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

import engine
from engine import FullseyeEngine, diagnose_stages


def _img(n=48):
    rng = np.random.default_rng(0)
    return np.clip(rng.random((n, n)), 0, 1)


def test_from_ops_and_introspection():
    eng = FullseyeEngine.from_ops("gaussian,sobel_amp,otsu", name="edge")
    assert eng.op_names() == ["gaussian", "sobel_amp", "otsu"]
    assert eng.input_sort() == "image" and eng.output_sort() == "region"
    assert len(eng) == 3
    d = eng.describe()
    assert d[0]["in_sort"] == "image" and d[2]["out_sort"] == "region"
    assert all(s["known"] for s in d)


def test_run_matches_run_pipeline():
    import api
    eng = FullseyeEngine.from_ops("gaussian,otsu")
    img = _img()
    out = eng.run(img)
    ref = api.run_pipeline(img, [("gaussian", 0.5, 0.5), ("otsu", 0.5, 0.5)])
    assert np.array_equal(out, ref)                       # engine == direct API
    assert set(np.unique(out)).issubset({0.0, 1.0})       # otsu -> binary region


def test_run_stepwise_and_upto():
    eng = FullseyeEngine.from_ops("gaussian,sobel_amp,otsu")
    img = _img()
    steps = eng.run_stepwise(img)
    assert len(steps) == 3
    # the last stepwise result equals the full run; upto=1 equals stepwise[1]
    assert np.array_equal(steps[-1], eng.run(img))
    assert np.array_equal(steps[1], eng.run(img, upto=1))


def test_empty_pipeline_is_identity():
    eng = FullseyeEngine([])
    img = _img()
    assert np.array_equal(eng.run(img), img)
    assert eng.run_stepwise(img) == []
    assert eng.input_sort() is None and eng.output_sort() is None


def test_validate_good_and_bad():
    assert FullseyeEngine.from_ops("gaussian,otsu").validate() == []
    bad = FullseyeEngine([("gaussian", .5, .5), ("nope_op", .5, .5)])
    probs = bad.validate()
    assert any(p["severity"] == "error" and p["op"] == "nope_op" for p in probs)
    assert not bad.is_runnable()
    assert FullseyeEngine.from_ops("gaussian").is_runnable()


def test_sort_mismatch_is_an_error():
    # otsu outputs a region; feeding it to gaussian (expects image) is an ERROR since
    # 2026-10-11 (it was a "warning", so is_runnable() said True and run() executed it).
    probs = diagnose_stages([("otsu", .5, .5), ("gaussian", .5, .5)])
    assert any(p["severity"] == "error" and p.get("kind") == "sort_mismatch" for p in probs)
    assert not FullseyeEngine([("otsu", .5, .5), ("gaussian", .5, .5)]).is_runnable()
    # a clean chain has none
    assert diagnose_stages([("gaussian", .5, .5), ("otsu", .5, .5)]) == []


def test_sort_mismatch_message_numbers_stages_1_based():
    """Regression (2026-09-02): a single rendered Problems line mixed two
    numbering conventions. ``diagnose_stages`` embedded the upstream stage
    0-based (``i - 1``) while the panel renders the line's own index 1-based
    (``index + 1``), so the reported line read

        ! stage 5 (circularity_xld): stage 3 (sk_clear_border) ...

    for a pipeline where sk_clear_border is the **4th** stage on screen. The
    prose is now 1-based throughout; the machine-readable indices stay 0-based
    and the upstream stage is exposed as prev_index / prev_op.
    """
    stages = [("gaussian", .5, .5), ("gaussian", .5, .5), ("otsu", .5, .5),
              ("sk_clear_border", .5, .5), ("circularity_xld", .5, .5)]
    probs = [p for p in diagnose_stages(stages) if p.get("kind") == "sort_mismatch"]
    assert len(probs) == 1
    p = probs[0]
    assert p["index"] == 4 and p["op"] == "circularity_xld"      # 0-based, unchanged
    assert p["prev_index"] == 3 and p["prev_op"] == "sk_clear_border"
    # the prose names the upstream stage the way the UI numbers it: 3 + 1 = 4
    assert p["message"].startswith("stage 4 (sk_clear_border)")
    assert "stage 3 (" not in p["message"]
    # the whole rendered line is now internally consistent
    line = "! stage %d (%s): %s" % (p["index"] + 1, p["op"], p["message"])
    assert line.startswith("! stage 5 (circularity_xld): stage 4 (sk_clear_border)")


def test_sort_mismatch_prev_index_survives_an_unknown_op():
    """An unknown op resets the sort chain but still counts as a stage, so the
    NEXT mismatch must point at it by its own index (not at i-1 by accident)."""
    stages = [("otsu", .5, .5), ("nope_op", .5, .5), ("gaussian", .5, .5)]
    probs = diagnose_stages(stages)
    errs = [p for p in probs if p["severity"] == "error"]
    assert len(errs) == 1 and errs[0]["index"] == 1
    # 'nope_op' sets prev_out to "any", which pairs with everything -> no sort mismatch
    assert [p for p in probs if p.get("kind") == "sort_mismatch"] == []


def test_set_knobs_and_chaining():
    eng = FullseyeEngine.from_ops("gaussian")
    assert eng.set_knobs(0, a=0.9, b=0.1) is eng                # chainable
    assert eng.get_knobs(0) == (0.9, 0.1)


def test_save_load_and_dict_roundtrip(tmp_path):
    eng = FullseyeEngine.from_ops("gaussian,otsu", name="edge")
    p = str(tmp_path / "edge.json")
    eng.save(p)
    loaded = FullseyeEngine.load(p)
    assert loaded.to_ops() == "gaussian,otsu" and loaded.name == "edge"
    # from_dict accepts what to_dict/Studio's Save pipeline writes
    d = json.loads(open(p, encoding="utf-8").read())
    assert FullseyeEngine.from_dict(d).op_names() == ["gaussian", "otsu"]


def test_from_dict_rejects_non_pipeline():
    with pytest.raises(ValueError):
        FullseyeEngine.from_dict({"not": "a pipeline"})


def test_to_python_is_valid_and_names_safely():
    eng = FullseyeEngine.from_ops("gaussian,otsu", name="1 weird/name")
    src = eng.to_python()
    # compiles, and the function name is a safe identifier (not starting with a digit)
    ns = {}
    compile(src, "<gen>", "exec")
    assert "def pipeline_1_weird_name(frame):" in src
    assert "run_pipeline" in src and "gaussian" in src


def test_to_python_keyword_and_unicode_safe():
    # names that are Python keywords / non-ASCII must still yield compilable code
    for nm in ("class", "return", "if", "step²", "1x", ""):
        code = FullseyeEngine.from_dict({"name": nm, "stages": []}).to_python()
        compile(code, "<gen>", "exec")


def test_empty_run_returns_input_unchanged():
    import numpy as np
    a = np.array([[255]], np.uint8)
    out = FullseyeEngine([]).run(a)
    assert out.dtype == np.uint8 and out is a          # unchanged, per the docstring


def test_empty_or_short_stage_entries():
    eng = FullseyeEngine.from_dict({"stages": [[], ["gaussian", 0.5, 0.5], ["otsu"]]})
    assert eng.op_names() == ["gaussian", "otsu"]      # empty skipped, short padded
    assert eng.get_knobs(1) == (0.5, 0.5)


def test_run_file(tmp_path):
    import imgio
    src = tmp_path / "in.png"
    imgio.save(str(src), _img())
    eng = FullseyeEngine.from_ops("gaussian,otsu")
    out = tmp_path / "out.png"
    result = eng.run_file(str(src), str(out))
    assert out.exists()
    assert isinstance(result, np.ndarray) and result.ndim == 2


def test_identity_threads_the_sort_instead_of_matching_everything():
    """Regression (2026-09-02 review): ``identity`` declares out_sort 'any', which
    ``diagnose_stages`` read as 'matches everything' — so [gaussian, identity,
    vol_gaussian] passed while [gaussian, vol_gaussian] warned, and output_sort()
    said 'any' for a pipeline that produces an image. 'any' out means pass-through:
    keep the incoming sort (same rule as ops._effective_out_sort)."""
    without = diagnose_stages([("gaussian", .5, .5), ("vol_gaussian", .5, .5)])
    assert [p["severity"] for p in without] == ["error"]
    with_id = diagnose_stages([("gaussian", .5, .5), ("identity", .5, .5), ("vol_gaussian", .5, .5)])
    assert [p["severity"] for p in with_id] == ["error"]
    assert with_id[0]["index"] == 2 and with_id[0]["prev_index"] == 1
    assert "outputs 'image'" in with_id[0]["message"]
    # a sort-consistent chain through identity stays clean
    assert diagnose_stages([("gaussian", .5, .5), ("identity", .5, .5), ("otsu", .5, .5)]) == []
    assert FullseyeEngine.from_ops("gaussian,identity").output_sort() == "image"
    assert FullseyeEngine.from_ops("gaussian,otsu,identity").output_sort() == "region"
    assert FullseyeEngine.from_ops("identity").output_sort() == "any"   # nothing to thread


def test_public_saved_pipeline_loader_and_cli_share_the_closed_validation_gate(tmp_path):
    """Studio JSON has one strict public reader / Python と CLI の保存ファイル門を共有する。"""
    import imgevolve
    import fullseye

    good = tmp_path / "inspect.json"
    good.write_text(json.dumps({"fullseye_pipeline": 1, "name": "inspect",
                                "stages": [["gaussian", 0.2, 0.5], ["threshold", 0.5, 0.5]]}),
                    encoding="utf-8")
    loaded = fullseye.load_pipeline(good)
    assert fullseye.pipeline_interface(loaded) == {
        "inputs": [{"name": "image", "sort": "image"}],
        "outputs": [{"name": "result", "sort": "region"}],
    }
    assert np.array_equal(loaded.run(_img()), FullseyeEngine.from_dict(json.loads(good.read_text())).run(_img()))

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"stages": [["not_an_operator", 0.5, 0.5]], "typo": True}), encoding="utf-8")
    with pytest.raises(ValueError) as raised:
        fullseye.load_pipeline(bad)
    message = str(raised.value)
    assert "unsupported key" in message and "'typo'" in message and "save the pipeline again from Studio" in message
    args = SimpleNamespace(pipeline=str(bad), a=0.5, b=0.5, describe=True, to_python=False,
                           inp=None, stepwise=False, out=None, upto=None)
    with pytest.raises(ValueError, match="unsupported key"):
        imgevolve.cmd_run(args)


def test_saved_pipeline_name_is_a_string_and_stage_aliases_are_unambiguous():
    """Saved JSON never coerces its name or silently chooses one conflicting stage alias.

    保存名は文字列だけを受け、dict stage が ``op`` と ``name`` を併記するときは同値だけを
    受ける。こうして C/C++ SDK を含む全保存JSON入口で同じ意味になる。
    """
    non_string_name = json.dumps({"fullseye_pipeline": 1, "name": 17,
                                  "stages": [["gaussian", 0.5, 0.5]]})
    with pytest.raises(ValueError) as raised:
        engine.load_pipeline_text(non_string_name)
    message = str(raised.value)
    assert all(fragment in message for fragment in ("'name' must be a JSON string", "17", "str()", "は JSON 文字列"))

    same_alias = engine.load_pipeline_text(json.dumps({
        "fullseye_pipeline": 1,
        "name": "same-alias",
        "stages": [{"op": "gaussian", "name": "gaussian", "a": 0.2, "b": 0.5}],
    }))
    assert same_alias.name == "same-alias" and same_alias.op_names() == ["gaussian"]

    conflicting_alias = json.dumps({
        "fullseye_pipeline": 1,
        "name": "conflict",
        "stages": [{"op": "gaussian", "name": "threshold", "a": 0.2, "b": 0.5}],
    })
    with pytest.raises(ValueError) as raised:
        engine.load_pipeline_text(conflicting_alias)
    message = str(raised.value)
    assert all(fragment in message for fragment in ("'op' is 'gaussian'", "'name' is 'threshold'", "one stage", "operator は 1 つ"))
