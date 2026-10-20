"""Studio slice 5: asynchronous runs keep settings and displayed results attributable."""
import os
import threading
import time

import numpy as np
import pytest

import studio

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _app():
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _wait(predicate, timeout=5000):
    from PySide6 import QtTest
    end = time.monotonic() + timeout / 1000.0
    while time.monotonic() < end:
        _app().processEvents()
        if predicate():
            return
        QtTest.QTest.qWait(10)
    assert predicate(), "condition was not reached before timeout"


def _window(stages=2):
    _app()
    studio.ERROR_HOOK = lambda *_args: None
    studio._UI_LANG["code"] = "ja"
    model = studio.PipelineModel(studio.demo_image(32))
    model.stages = [["gaussian", 0.2 + i * 0.1, 0.5] for i in range(stages)]
    win, built_model = studio.build_window(model)
    assert built_model is model
    studio._UI_LANG["code"] = "ja"
    return win, model


def test_worker_keeps_event_loop_alive_and_reports_stage_progress(monkeypatch):
    win, _model = _window(2)
    entered, release = threading.Event(), threading.Event()
    calls = []

    def slow(value, stages, **_kwargs):
        calls.append(stages[0][0])
        if len(calls) == 1:
            entered.set()
            assert release.wait(5)
        return np.asarray(value) + 1

    monkeypatch.setattr(studio.api, "run_pipeline", slow)
    ticks = {"n": 0}
    from PySide6 import QtCore
    timer = QtCore.QTimer(win)
    timer.timeout.connect(lambda: ticks.__setitem__("n", ticks["n"] + 1))
    timer.start(5)
    win._buttons["run_all"].click()
    _wait(entered.is_set)
    _wait(lambda: ticks["n"] >= 2)
    assert "実行中 1/2 段" in win._run_ui["status"].text()
    release.set()
    _wait(lambda: not win._run_controller.running)
    assert len(calls) == 2
    win.close()


def test_older_generation_finishing_late_never_applies(monkeypatch):
    win, model = _window(1)
    first_entered, release_first = threading.Event(), threading.Event()
    lock = threading.Lock()
    ordinal = {"n": 0}

    def ordered(value, _stages, **_kwargs):
        with lock:
            ordinal["n"] += 1
            n = ordinal["n"]
        if n == 1:
            first_entered.set()
            assert release_first.wait(5)
        return np.full_like(value, n)

    monkeypatch.setattr(studio.api, "run_pipeline", ordered)
    g1 = win._start_run_async()
    _wait(first_entered.is_set)
    g2 = win._start_run_async()
    _wait(lambda: model.displayed_generation == g2)
    applied = model.applied_run_results
    release_first.set()
    _wait(lambda: not win._run_controller.running)
    assert (g1, g2) == (1, 2)
    assert model.displayed_generation == g2
    assert model.applied_run_results == applied
    assert np.all(model.displayed_result == 2)
    win.close()


def test_stop_is_requested_then_acknowledged_between_stages(monkeypatch):
    win, _model = _window(3)
    entered, release = threading.Event(), threading.Event()
    calls = []

    def slow(value, stages, **_kwargs):
        calls.append(stages[0][0])
        if len(calls) == 1:
            entered.set()
            assert release.wait(5)
        return value

    monkeypatch.setattr(studio.api, "run_pipeline", slow)
    win._start_run_async()
    _wait(entered.is_set)
    win._run_ui["stop"].click()
    assert "停止要求済み" in win._run_ui["status"].text()
    assert "停止済み" not in win._run_ui["status"].text()
    release.set()
    _wait(lambda: not win._run_controller.running)
    assert len(calls) == 1
    assert any("停止要求済み" in s for s in win._run_controller.status_history)
    assert any("停止しました" in s for s in win._run_controller.status_history)
    win.close()


def test_changed_settings_banner_and_actions(monkeypatch):
    win, model = _window(1)
    entered, release = threading.Event(), threading.Event()

    def slow(value, _stages, **_kwargs):
        entered.set()
        assert release.wait(5)
        return value

    monkeypatch.setattr(studio.api, "run_pipeline", slow)
    g1 = win._start_run_async()
    _wait(entered.is_set)
    model.set_knobs(0, a=0.9)
    win._settings_changed()
    try:
        assert "変更あり" in win._run_ui["attribution"].text()
    finally:
        release.set()
    _wait(lambda: not win._run_controller.running)
    assert "完了した結果は変更前の設定による" in win._run_ui["banner"].text()
    assert not win._run_ui["show_result"].isHidden()
    assert not win._run_ui["run_current"].isHidden()
    win._run_ui["show_result"].click()
    assert win._run_controller.generation == g1
    win._run_ui["run_current"].click()
    assert win._run_controller.generation == g1 + 1
    win._run_controller.request_stop()
    _wait(lambda: not win._run_controller.running)
    win.close()


def test_worker_failure_uses_actionable_problem_and_leaves_running_state(monkeypatch):
    win, _model = _window(1)

    def broken(*_args, **_kwargs):
        raise ValueError("input has non-finite values")

    monkeypatch.setattr(studio.api, "run_pipeline", broken)
    win._start_run_async()
    _wait(lambda: not win._run_controller.running)
    assert win._problems_list.count() >= 1
    text = win._problems_list.item(win._problems_list.count() - 1).text()
    assert "原因" in text and "場所" in text and "次にできること" in text
    assert not win._run_ui["stop"].isEnabled()
    win.close()


def test_run_worker_i18n_keys_are_complete():
    keys = studio.RUN_WORKER_I18N_KEYS
    assert len(keys) >= 10
    assert len(studio.LANGUAGES) == 7
    for key in keys:
        assert key in studio.STRINGS_I18N
        row = studio.STRINGS_I18N[key]
        assert len(row) == 6
        assert all(row.get(code) for code in studio.LANGUAGES if code != "en")
