"""Studio slice 1 continued (2026-10-25): stage-cache MEMORY BUDGET + LRU eviction (idea 113 / 116).

The keyed, prefix-valid stage cache already recomputes only from the edited stage (see
test_studio_stage_cache_validity_input_2026_10_19.py). This file adds the missing bound: the cache
holds at most a documented byte budget of stage-output arrays, evicting the least-recently-used
stage *values* (keys/timing kept) past it. Eviction must never change a result and never break the
"editing stage k invalidates k..n only" rule — it only changes how much is kept hot.

Two layers are covered: the pure engine-layer :class:`studio_result.StageCache` (what the browser
version consumes) and :class:`studio.PipelineModel`'s in-place budget.
"""
import numpy as np
import pytest

import api
import studio
import studio_result as sr


OPS = ["gaussian", "median", "bilateral", "unsharp", "gamma", "clahe", "equalize", "highpass"]


def _counting(monkeypatch, names):
    counts = {n: 0 for n in names}
    for n in names:
        real = api._ops.RT[n]

        def wrap(v, a, b, _real=real, _n=n):
            counts[_n] += 1
            return _real(v, a, b)
        monkeypatch.setitem(api._ops.RT, n, wrap)
    return counts


def _model(img, ops, budget=None):
    m = studio.PipelineModel(img)
    if budget is not None:
        m.set_cache_budget(budget)
    for n in ops:
        m.add_stage(n, 0.4, 0.5)
    return m


# ----------------------- StageCache (engine layer) ----------------------- #
def test_stagecache_lru_and_budget():
    c = sr.StageCache(budget_bytes=20)                 # room for 5 of 4 B each
    for i in range(10):
        c.put(("k", i), np.zeros(4, np.uint8), float(i))   # 4 bytes each
    assert c.nbytes() <= 20
    assert ("k", 9) in c and ("k", 0) not in c         # newest kept, oldest evicted
    # reading refreshes recency: touch k5, add until only one survivor besides it
    tiny = sr.StageCache(budget_bytes=8)
    tiny.put(("a",), np.zeros(4, np.uint8))
    tiny.put(("b",), np.zeros(4, np.uint8))
    assert tiny.get(("a",)) is not None                # a touched -> most recent
    tiny.put(("c",), np.zeros(4, np.uint8))            # evicts LRU = b, not a
    assert ("a",) in tiny and ("b",) not in tiny


def test_stagecache_protect_and_min_one():
    c = sr.StageCache(budget_bytes=4)                  # room for one
    c.put(("x", 0), np.zeros(4, np.uint8))
    c.put(("x", 1), np.zeros(4, np.uint8), protect=[("x", 0)])
    assert ("x", 0) in c                               # protected survives even though LRU
    # a single value larger than the whole budget is still kept (never drop below one)
    big = sr.StageCache(budget_bytes=1)
    big.put(("only",), np.zeros(100, np.uint8))
    assert ("only",) in big and len(big) == 1


def test_stagecache_set_budget_shrinks_immediately():
    c = sr.StageCache(budget_bytes=1 << 30)
    for i in range(5):
        c.put(("s", i), np.zeros(8, np.uint8))
    assert c.nbytes() == 40
    c.set_budget(16)
    assert c.nbytes() <= 16 and len(c) <= 2


# ------------------- PipelineModel in-place budget ----------------------- #
def test_model_budget_bounds_memory_and_keeps_results_exact():
    img = studio.demo_image(96).astype(np.float64)
    per = img.nbytes
    m = _model(img, OPS, budget=3 * per)               # keep ~3 stage arrays
    out = m.result_upto(len(OPS) - 1)
    assert m.cache_bytes() <= 3 * per                  # bounded
    assert len(m._lru) < len(OPS)                      # not every stage is held live
    # bit-identical to a fresh unbounded recompute, every intermediate included
    fresh = studio.PipelineModel(img)
    fresh.stages = [list(s) for s in m.stages]
    assert np.array_equal(out, fresh.result_upto(len(OPS) - 1))
    for i in range(len(OPS)):
        assert np.array_equal(m.result_upto(i), fresh.result_upto(i))


def test_model_budget_preserves_invalidation_rule(monkeypatch):
    img = studio.demo_image(96).astype(np.float64)
    per = img.nbytes
    ops = ["gaussian", "median", "unsharp", "gamma", "clahe", "highpass"]
    m = studio.PipelineModel(img)
    m.set_cache_budget(2 * per)
    for n in ops:
        m.add_stage(n, 0.4, 0.5)
    m.result_upto(len(ops) - 1)
    counts = _counting(monkeypatch, set(ops))
    # editing the LAST stage recomputes only it (its predecessor is still hot)
    m.set_knobs(len(ops) - 1, a=0.7)
    m.result_upto(len(ops) - 1)
    assert counts[ops[-1]] == 1
    assert sum(counts.values()) == 1, counts           # k..n only, with n == k here


def test_model_evicted_predecessor_recomputes_from_base(monkeypatch):
    img = studio.demo_image(96).astype(np.float64)
    per = img.nbytes
    m = _model(img, OPS, budget=2 * per)               # tiny: early stages get evicted
    m.result_upto(len(OPS) - 1)
    # stage 0's value is evicted (LRU); editing stage 1 must still be correct
    m.set_knobs(1, a=0.6)
    got = m.result_upto(len(OPS) - 1)
    fresh = studio.PipelineModel(img)
    fresh.stages = [list(s) for s in m.stages]
    assert np.array_equal(got, fresh.result_upto(len(OPS) - 1))
    assert m.cache_bytes() <= 2 * per


def test_default_budget_is_documented_and_large():
    # the default keeps ordinary pipelines fully cached; the constant is the single source
    assert studio.CACHE_BUDGET_BYTES == sr.CACHE_BUDGET_BYTES == 256 * 1024 * 1024
    m = studio.PipelineModel(studio.demo_image(64))
    assert m.cache_budget() == sr.CACHE_BUDGET_BYTES


def test_set_cache_budget_shrinks_live_set():
    img = studio.demo_image(96).astype(np.float64)
    per = img.nbytes
    m = _model(img, OPS)                                # default budget -> all held
    m.result_upto(len(OPS) - 1)
    assert m.cache_bytes() > 4 * per
    m.set_cache_budget(2 * per)                         # user turns the cache size down (idea 116)
    assert m.cache_bytes() <= 2 * per
    # and results are still correct afterwards
    fresh = studio.PipelineModel(img)
    fresh.stages = [list(s) for s in m.stages]
    assert np.array_equal(m.result_upto(len(OPS) - 1), fresh.result_upto(len(OPS) - 1))
