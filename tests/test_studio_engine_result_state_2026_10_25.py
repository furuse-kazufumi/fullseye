"""Engine-layer (Qt-free) stage cache + result state (2026-10-25).

The browser (Pyodide) Studio runs the same recipes without the Qt UI, so the stage cache and the
ran / valid / reasons result state must be reachable from the engine layer. This covers
``engine.FullseyeEngine.run_cached`` (the stage cache twin) and ``engine.pipeline_states`` /
``FullseyeEngine.stepwise_states`` (the result state), including the user's rules: an op with no
success information is never reported valid, NaN/Inf counts are shown, no automatic fix is offered.
"""
import numpy as np
import pytest

import api
import engine
import studio
import studio_result as sr


IMG = studio.demo_image(64).astype(np.float64)


def _counting(monkeypatch, names):
    counts = {}
    for n in names:
        real = api._ops.RT[n]

        def wrap(v, a, b, _real=real, _n=n):
            counts[_n] = counts.get(_n, 0) + 1
            return _real(v, a, b)
        monkeypatch.setitem(api._ops.RT, n, wrap)
    return counts


# ------------------------------ run_cached ------------------------------- #
def test_run_cached_equals_run():
    eng = engine.FullseyeEngine.from_ops("gaussian,sobel_amp,invert,median")
    assert np.array_equal(eng.run_cached(IMG), eng.run(IMG))
    assert np.array_equal(eng.run_cached(IMG), api.run_pipeline(IMG, eng.stages))


def test_run_cached_recomputes_only_from_the_edited_stage(monkeypatch):
    eng = engine.FullseyeEngine.from_ops("gaussian,sobel_amp,invert,median")
    c = sr.StageCache()
    counts = _counting(monkeypatch, ["gaussian", "sobel_amp", "invert", "median"])
    eng.run_cached(IMG, c)
    assert counts == {"gaussian": 1, "sobel_amp": 1, "invert": 1, "median": 1}
    eng.set_knobs(3, a=0.8)                                 # edit the last stage
    eng.run_cached(IMG, c)
    assert counts == {"gaussian": 1, "sobel_amp": 1, "invert": 1, "median": 2}
    eng.set_knobs(1, a=0.3)                                 # edit stage 1 -> 1..3 recompute, 0 reused
    eng.run_cached(IMG, c)
    assert counts == {"gaussian": 1, "sobel_amp": 2, "invert": 2, "median": 3}


def test_run_cached_keys_on_input_identity():
    eng = engine.FullseyeEngine.from_ops("gaussian,invert")
    c = sr.StageCache()
    a = eng.run_cached(IMG, c)
    b = eng.run_cached(IMG * 0.5, c)                        # different input -> different key
    assert not np.array_equal(a, b)
    assert np.array_equal(eng.run_cached(IMG * 0.5, c), b)


def test_run_cached_budget_bounds_memory():
    eng = engine.FullseyeEngine.from_ops(",".join(["gaussian"] * 12))
    per = IMG.nbytes
    c = sr.StageCache(budget_bytes=3 * per)
    out = eng.run_cached(IMG, c)
    assert c.nbytes() <= 3 * per
    assert np.array_equal(out, eng.run(IMG))               # still correct under eviction


# ---------------------------- result state ------------------------------- #
def test_stepwise_states_clean_is_not_judged_green():
    st = engine.FullseyeEngine.from_ops("gaussian,sobel_amp").stepwise_states(IMG)
    assert [s["op"] for s in st] == ["gaussian", "sobel_amp"]
    assert len(st) == 2                                      # counted first: an empty list passes all() vacuously
    assert all(s["ran"] is True for s in st)
    assert all(s["valid"] is None and s["reasons"] == [] for s in st)   # no success info -> not judged
    assert all("error" not in s for s in st)


def test_stepwise_states_nonfinite_is_valid_false_with_count(monkeypatch):
    real = api._ops.RT["invert"]

    def naninv(v, a, b):
        o = np.array(real(v, a, b), float)
        o[0, :3] = np.nan
        return o
    monkeypatch.setitem(api._ops.RT, "invert", naninv)
    st = engine.FullseyeEngine.from_ops("gaussian,invert").stepwise_states(IMG)
    assert st[0]["valid"] is None                            # gaussian: still not judged
    bad = st[1]
    assert bad["ran"] is True and bad["valid"] is False
    assert any("non-finite" in r for r in bad["reasons"])    # count shown, never blanked
    assert "error" not in bad                                # a warning, not an error


def test_stepwise_states_explicit_validity_keys_are_honored():
    assert sr.assess_validity({"converged": True}) == (True, [])
    assert sr.assess_validity({"converged": False})[0] is False
    # pipeline_states reflects assess_validity for an op returning a dict verdict is covered there;
    # here confirm the engine uses the SAME function (one source of the rule)
    assert engine.assess_validity is sr.assess_validity


def test_stepwise_states_refused_chain_reports_error_without_false_green():
    st = engine.FullseyeEngine.from_ops("otsu,invert").stepwise_states(IMG)   # region -> image mismatch
    assert len(st) == 2                                      # both stages reported, none silently dropped
    assert all(s["ran"] is False for s in st)
    assert all(s["valid"] is None for s in st)               # never green on a refused chain
    assert any(s.get("error") for s in st)


def test_stepwise_states_offers_no_automatic_fix():
    st = engine.FullseyeEngine.from_ops("gaussian,invert").stepwise_states(IMG)
    assert len(st) == 2
    for s in st:
        assert set(s) <= {"index", "op", "a", "b", "ran", "valid", "reasons", "error"}
        for key in s:
            assert "fix" not in key and "rerun" not in key and "suggest" not in key
