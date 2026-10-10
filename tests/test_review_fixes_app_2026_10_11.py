"""2026-10-11 アプリ層レビューの修正の門(速く・決定的)。

各節は「直す前の木で赤、直した木で緑」を確かめてある。``assert all(...)`` の前には
必ず別の ``assert xs``(空集合で all() が真になるのを防ぐ)。
"""
import warnings

import numpy as np
import pytest

import api
import engine
import graphengine

warnings.simplefilter("ignore")


def _img(seed=0, shape=(24, 24)):
    return np.random.default_rng(seed).random(shape)


@pytest.fixture
def spy(monkeypatch):
    """Replace RT[name] with a counting wrapper; returns the call log."""
    calls = []

    def install(name):
        real = api._ops.RT[name]

        def wrapped(v, a, b, _real=real, _name=name):
            calls.append(_name)
            return _real(v, a, b)
        monkeypatch.setitem(api._ops.RT, name, wrapped)
    return install, calls


# ---------------------------------------------------------------- 1. sort chain --
MISMATCHED = [
    (["gaussian", "vol_gaussian"], 2, "vol_gaussian", "image", "volume"),
    (["gaussian", "blob_count"], 2, "blob_count", "image", "region"),
    (["otsu", "blob_count", "gaussian"], 3, "gaussian", "feature", "image"),
    (["gaussian", "identity", "vol_gaussian"], 3, "vol_gaussian", "image", "volume"),
]


@pytest.mark.parametrize("policy", ["fallback", "warn", "raise"])
@pytest.mark.parametrize("chain,stage,op,got,want", MISMATCHED)
def test_run_pipeline_refuses_mismatched_chain_before_running(spy, policy, chain, stage, op, got, want):
    install, calls = spy
    install(chain[0])
    api.clear_fallbacks()
    with pytest.raises(ValueError) as ei:
        api.run_pipeline(_img(), chain, on_error=policy)
    msg = str(ei.value)
    assert "stage %d" % stage in msg and op in msg
    assert repr(got) in msg and repr(want) in msg
    assert calls == []                       # the first op never ran
    assert api.fallbacks() == []             # nothing was "degraded": it was refused


@pytest.mark.parametrize("chain", [["gaussian", "identity", "otsu"], ["identity", "gaussian"],
                                   ["gaussian", "identity"], ["otsu", "identity", "blob_count"],
                                   ["gaussian", "otsu", "blob_count"]])
def test_valid_chains_still_run_including_through_identity(spy, chain):
    install, calls = spy
    install(chain[0])
    out = api.run_pipeline(_img(), chain, on_error="raise")
    assert calls == [chain[0]]
    assert out is not None


def test_engine_mismatch_is_an_error_and_run_refuses(spy):
    install, calls = spy
    install("gaussian")
    eng = engine.FullseyeEngine.from_ops("gaussian,vol_gaussian")
    probs = eng.validate()
    assert probs and probs[0]["severity"] == "error" and probs[0]["kind"] == "sort_mismatch"
    assert not eng.is_runnable()
    with pytest.raises(ValueError, match="vol_gaussian"):
        eng.run(_img())
    with pytest.raises(ValueError, match="vol_gaussian"):
        eng.run_stepwise(_img())
    assert calls == []
    ok = engine.FullseyeEngine.from_ops("gaussian,identity,otsu")
    assert ok.is_runnable() and ok.validate() == []
    assert ok.run(_img()).shape == (24, 24)
    assert calls == ["gaussian"]


def test_graph_validate_and_run_refuse_mismatch_before_running(spy):
    install, calls = spy
    install("otsu")
    g = graphengine.FullseyeGraph()
    g.add("m", "otsu")
    g.add("n", "blob_count", ["m"])
    g.add("o", "vol_gaussian", ["n"])
    probs = g.validate()
    assert [p.get("kind") for p in probs] == ["sort_mismatch"]
    with pytest.raises(ValueError, match="vol_gaussian"):
        g.run(_img(), terminal="o")
    assert calls == []
    # through identity, the incoming sort is kept: image -> identity -> volume op is refused
    g2 = graphengine.FullseyeGraph()
    g2.add("g", "gaussian")
    g2.add("i", "identity", ["g"])
    g2.add("v", "vol_gaussian", ["i"])
    assert [p.get("kind") for p in g2.validate()] == ["sort_mismatch"]
    # a valid graph through identity runs
    g3 = graphengine.FullseyeGraph()
    g3.add("m", "otsu")
    g3.add("i", "identity", ["m"])
    g3.add("n", "blob_count", ["i"])
    assert g3.validate() == []
    out = g3.run(_img(), terminal="n")
    assert np.isfinite(float(out))
    assert calls == ["otsu"]


def test_graph_nary_input_sorts_are_checked():
    g = graphengine.FullseyeGraph()
    g.add("c", "blob_count")                       # feature
    g.add("s", "add_image", ["$in", "c"])          # add_image takes two images
    probs = g.validate()
    assert any(p.get("kind") == "sort_mismatch" for p in probs)
    with pytest.raises(ValueError):
        g.run(_img(), terminal="s")


# --------------------------------------------------------- 2. knobs per stage --
@pytest.mark.parametrize("policy", ["fallback", "warn", "raise"])
def test_run_pipeline_refuses_nan_knob_before_running(spy, policy):
    install, calls = spy
    install("gaussian")
    with pytest.raises(ValueError, match="non-finite"):
        api.run_pipeline(_img(), [("gaussian", 0.5, 0.5), ("threshold", float("nan"), 0.5)],
                         on_error=policy)
    with pytest.raises(ValueError, match="non-finite"):
        engine.FullseyeEngine([("gaussian", 0.5, 0.5), ("threshold", float("nan"), 0.5)]).run(_img())
    assert calls == []


def test_run_pipeline_out_of_range_knob_matches_apply():
    img = _img()
    with pytest.raises(ValueError, match="outside 0..1"):
        api.run_pipeline(img, [("threshold", 5.0, 0.5)], on_error="raise")
    api.clear_fallbacks()
    out = api.run_pipeline(img, [("threshold", 5.0, 0.5)], on_error="fallback")
    recs = api.fallbacks()
    assert recs and recs[0]["source"] == "input" and recs[0]["name"] == "threshold"
    assert np.array_equal(out, api.apply(img, "threshold", 1.0, 0.5))   # clamped, like apply


# ------------------------------------------------------ 7. stepwise == run --
def test_run_stepwise_last_equals_run_for_uint8():
    u8 = (_img() * 255).astype(np.uint8)
    e = engine.FullseyeEngine.from_ops("gaussian,threshold")
    steps = e.run_stepwise(u8)
    assert len(steps) == 2
    assert np.array_equal(steps[-1], e.run(u8))
    assert np.array_equal(steps[0], api.apply(u8, "gaussian"))
    assert engine.FullseyeEngine([]).run_stepwise(u8) == []


# -------------------------------------------- 8. graph runs the facade runner --
@pytest.mark.parametrize("op", ["threshold", "gaussian", "invert"])
def test_graph_uint8_matches_apply(op):
    u8 = (_img() * 255).astype(np.uint8)
    g = graphengine.FullseyeGraph()
    g.add("t", op)
    got = np.asarray(g.run(u8, terminal="t"))
    want = np.asarray(api.apply(u8, op))
    assert got.dtype == want.dtype == np.float64
    assert np.array_equal(got, want)


def test_graph_refuses_arity_error_and_checks_knobs(spy):
    install, calls = spy
    install("gaussian")
    g = graphengine.FullseyeGraph()
    g.add("x", "gaussian", ["$in", "$other"])
    with pytest.raises(ValueError, match="got 2 inputs"):
        g.run({"$in": _img(), "$other": _img(1)}, terminal="x")
    assert calls == []
    g = graphengine.FullseyeGraph()
    g.add("t", "threshold", a=7.0)
    with pytest.raises(ValueError, match="outside 0..1"):
        g.run(_img(), terminal="t", on_error="raise")
    g = graphengine.FullseyeGraph()
    g.add("t", "threshold", a=float("nan"))
    assert any("non-finite" in p["msg"] for p in g.validate())
    with pytest.raises(ValueError):
        g.run(_img(), terminal="t")


def test_graph_to_python_keyword_name_compiles_and_matches():
    img = _img(4)
    g = graphengine.FullseyeGraph("class")
    g.add("blur", "gaussian", a=0.5)
    g.add("resid", "abs_diff_image", ["$in", "blur"])
    src = g.to_python()
    ns = {}
    exec(compile(src, "<g>", "exec"), ns)            # noqa: S102 - generated code smoke test
    fn = engine._py_ident("class")
    v = ns[fn](**{"$in": img})
    assert np.allclose(v["resid"], g.run(img, terminal="resid"))
