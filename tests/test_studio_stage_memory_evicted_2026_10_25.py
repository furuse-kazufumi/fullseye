"""Studio slice ⑤ continued (2026-10-25): per-stage memory (idea 114) + the honest "evicted" state.

Thumbnails, the input→output panel and bypass landed as slice 2 (2026-10-20). What was still missing
once the stage cache got a memory budget: (a) the rows say how much each stage HOLDS (bytes) next to
its time, and the run status line shows the cache range (bytes / budget, live / evicted stages);
(b) a stage whose knobs did not change but whose array was dropped for the budget is reported as
``evicted`` — not as "recompute needed" (which would imply the user changed something) — and its small
thumbnail stays current (made before the array is dropped). Everything reads the cache; nothing here
computes a stage, draws a new widget or bypasses apply_display.
"""
import os

import numpy as np
import pytest

import api
import studio
import studio_result as sr

OPS = ["gaussian", "median", "unsharp", "gamma", "clahe", "highpass"]


def _counting(monkeypatch, names):
    counts = {}
    for n in names:
        real = api._ops.RT[n]

        def wrap(v, a, b, _real=real, _n=n):
            counts[_n] = counts.get(_n, 0) + 1
            return _real(v, a, b)
        monkeypatch.setitem(api._ops.RT, n, wrap)
    return counts


def _model(budget_stages=None):
    m = studio.PipelineModel(studio.demo_image(96))
    for n in OPS:
        m.add_stage(n, 0.4, 0.5)
    if budget_stages is not None:
        m.set_cache_budget(budget_stages * m.image.nbytes)
    return m


# ------------------------------ model API -------------------------------- #
def test_stage_memory_sums_to_cache_bytes_and_is_none_when_not_held():
    m = _model()
    assert m.stage_memory() == [None] * len(OPS)                 # nothing computed yet
    m.result_upto(len(OPS) - 1)
    mem = m.stage_memory()
    assert len(mem) == len(OPS)                                  # one entry per stage, counted first
    assert all(isinstance(b, int) and b > 0 for b in mem)
    assert sum(mem) == m.cache_bytes()
    m.set_knobs(2, a=0.7)                                        # stages 2.. are stale -> not held
    assert m.stage_memory()[:2] == mem[:2] and m.stage_memory()[2:] == [None] * (len(OPS) - 2)


def test_cache_summary_counts_live_and_evicted_without_computing(monkeypatch):
    m = _model(budget_stages=2)
    m.result_upto(len(OPS) - 1)
    counts = _counting(monkeypatch, OPS)
    s = m.cache_summary()
    assert s["stages"] == len(OPS) and s["live"] == 2 and s["evicted"] == len(OPS) - 2
    assert s["bytes"] == m.cache_bytes() <= s["budget_bytes"] == 2 * m.image.nbytes
    assert sum(m.stage_memory()[-2:]) == s["bytes"]
    assert counts == {}                                          # summary / memory never run a stage


def test_cache_summary_text_is_plain_and_omits_zero_evicted():
    t = sr.cache_summary_text({"bytes": 8 * 1024 * 1024, "budget_bytes": 256 * 1024 * 1024,
                               "live": 4, "evicted": 16, "stages": 20})
    assert t == "cache 8.0 / 256.0 MB · live 4/20 · evicted 16"
    assert "evicted" not in sr.cache_summary_text({"bytes": 0, "budget_bytes": 1, "live": 0, "stages": 0})
    # works straight from the engine-layer cache's stats() too
    c = sr.StageCache(budget_bytes=64)
    c.put(("k",), np.zeros(8, np.uint8))
    assert sr.cache_summary_text(c.stats()).startswith("cache 0.0 / 0.0 MB · live 1")


# ------------------------------ evicted state ---------------------------- #
def test_evicted_is_its_own_status_and_keeps_a_current_thumbnail(monkeypatch):
    m = _model(budget_stages=2)
    m.result_upto(len(OPS) - 1)                                  # eviction happens inside the run
    counts = _counting(monkeypatch, OPS)
    pv = m.stage_previews()
    assert [p["status"] for p in pv] == ["evicted"] * (len(OPS) - 2) + ["ready"] * 2
    ev = [p for p in pv if p["status"] == "evicted"]
    assert len(pv) == len(OPS)
    assert len(ev) == len(OPS) - 2                               # the evicted subset is counted, not assumed
    assert all(p["thumb"] is not None and p["kind"] == "image" for p in ev)
    assert all(p["thumb"].dtype == np.uint8 and p["thumb"].ndim == 3 for p in pv)
    assert counts == {}                                          # previews never compute
    # a knob change on an evicted stage makes it STALE (user changed something), not evicted
    m.set_knobs(1, a=0.9)
    assert m.stage_preview(1)["status"] == "stale" and m.stage_preview(1)["thumb"] is None


def test_evicted_stage_is_ready_again_after_being_read_and_rows_see_it():
    m = _model(budget_stages=2)
    m.result_upto(len(OPS) - 1)
    states = m.cached_step_states()
    assert states[0]["status"] == "evicted" and states[0]["state"] is None   # no state invented
    m.result_upto(0)                                             # the user looks at it -> recomputed
    assert m.stage_preview(0)["status"] == "ready"
    assert m.cache_summary()["live"] == 2                        # still within the budget


def test_set_cache_budget_turns_ready_into_evicted_with_thumbnails():
    m = _model()
    m.result_upto(len(OPS) - 1)
    m.stage_previews()                                           # thumbnails exist for all
    m.set_cache_budget(1 * m.image.nbytes)
    pv = m.stage_previews()
    assert len(pv) == len(OPS)
    assert pv[-1]["status"] == "ready"
    assert all(p["status"] == "evicted" and p["thumb"] is not None for p in pv[:-1])


# ------------------------------ Qt rows (offscreen) ---------------------- #
def _app():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_rows_show_memory_and_evicted_text_and_status_shows_cache_line(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(96)))
    for n in OPS:
        model.add_stage(n, 0.4, 0.5)
    model.set_cache_budget(2 * model.image.nbytes)
    win._do_run_all()
    msg = win.statusBar().currentMessage()
    assert "cache " in msg and "/ 0.1 MB" in msg and "live 2/6" in msg and "evicted 4" in msg
    assert "validity not judged" in msg                          # the validity fact is still there
    win._refresh_stage_list()
    rows = [win._stage_list.item(i).text() for i in range(win._stage_list.count())]
    assert all("evicted (budget)" in t for t in rows[:4])
    assert all("MB" in t and "ms" in t for t in rows[4:])        # held stages: time AND memory
    assert not any("MB" in t for t in rows[:4])                  # dropped stages: no memory claimed
    assert not any("recompute needed" in t for t in rows)        # nothing pretends the user changed a knob
    counts = _counting(monkeypatch, OPS)
    win._update_stage_icons()
    assert counts == {}                                          # icons from the cache only
    tips = [win._stage_list.item(i).toolTip() for i in range(4)]
    assert all("evicted (budget)" in t for t in tips)
    assert all(not win._stage_list.item(i).icon().isNull() for i in range(6))
    win.close()
