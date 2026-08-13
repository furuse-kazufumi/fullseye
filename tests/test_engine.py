"""Tests for FullseyeEngine — the pipeline runtime (the HDevEngine analog).

Load a pipeline (JSON / ops string / dict), introspect its sorts, validate it,
tune knobs, and execute it (whole / up-to / stepwise). These are the guarantees
another project (or the embedded runtime) relies on."""
import json

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


def test_sort_mismatch_is_a_warning():
    # otsu outputs a region; feeding it to gaussian (expects image) is a warning
    probs = diagnose_stages([("otsu", .5, .5), ("gaussian", .5, .5)])
    assert any(p["severity"] == "warning" for p in probs)
    # a clean chain has none
    assert diagnose_stages([("gaussian", .5, .5), ("otsu", .5, .5)]) == []


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
