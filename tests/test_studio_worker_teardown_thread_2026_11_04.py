"""Studio の実行ワーカー(QObject)は GUI スレッドで壊す(2026-11-04、Linux CI の 2 回の固まり)。

固まりの正体(WSL Ubuntu 24.04 + PySide6 6.12.0 で 3330 反復中 3 回再現し、gdb で全スレッドを取った):

- ワーカーのスレッド: QThread の終了処理が DeferredDelete を配り、ワーカーの ``~QObject`` が走る。
  ``~QObject`` は自分の signal-slot mutex(Qt は 131 個の mutex を**アドレスで共有**する)を
  握ったまま送信元の QThread に ``disconnectNotify`` を呼び、PySide の override 探索が **GIL** を待つ。
- GUI スレッド: GIL を握ったまま ``QPlainTextEdit.setPlainText`` の中で
  ``QMetaObject::disconnect`` → **同じ番号の mutex** を待つ(文書と文書制御のアドレスが偶然同じ番号)。

両者が相手の持つものを待つので永久に止まる(Python のスタックは ``_render`` の setPlainText 行で
止まって見える)。直し方は、ワーカーが ``run`` の最後に自分を GUI スレッドへ戻し、
``~QObject`` が GIL を持つ GUI スレッドで走るようにすること。ここでは**壊れたスレッド**を数えて、
衝突の運に頼らずに旧い配線を落とす。
"""
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


def _wait(predicate, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        _app().processEvents()
        if predicate():
            return
        time.sleep(0.005)
    assert predicate(), "condition was not reached before timeout"


def _flush_deletes():
    from PySide6 import QtCore
    _app().processEvents()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    _app().processEvents()


def _assert_thread_not_connected_to_worker(thread):
    """The worker must not be a receiver of its QThread: a receiver's ~QObject calls the
    sender's disconnectNotify (a GIL wait in PySide) while holding a shared Qt mutex."""
    from PySide6 import QtCore
    assert thread.receivers(QtCore.SIGNAL("started()")) == 0
    # finished() feeds only the GUI-side finish bridge and the thread's own deleteLater.
    assert thread.receivers(QtCore.SIGNAL("finished()")) == 2


def _watch_destruction(worker):
    """Record the OS thread that runs the worker's ~QObject (the ``destroyed`` emitter)."""
    from PySide6 import QtCore
    seen = []
    # DirectConnection: the lambda runs in whichever thread emits destroyed(), i.e. the
    # thread that runs ~QObject (an auto connection could queue it somewhere else).
    worker.destroyed.connect(lambda *_args: seen.append(threading.get_ident()),
                             QtCore.Qt.DirectConnection)
    return seen


def _close(win):
    win.quiesce()
    win.close_guard = None
    win.close()
    win.deleteLater()
    _flush_deletes()


def test_run_worker_is_destroyed_on_the_gui_thread(monkeypatch):
    _app()
    studio.ERROR_HOOK = lambda *_args: None
    model = studio.PipelineModel(studio.demo_image(16))
    model.stages = [["gaussian", 0.2, 0.5], ["gaussian", 0.3, 0.5]]
    win, _ = studio.build_window(model)
    release = threading.Event()

    def held(value, _stages, **_kwargs):
        assert release.wait(10)
        return np.asarray(value) + 1

    monkeypatch.setattr(studio.api, "run_pipeline", held)
    gen = win._start_run_async()
    thread, worker = win._run_controller.threads[gen]
    _assert_thread_not_connected_to_worker(thread)
    seen = _watch_destruction(worker)
    release.set()
    _wait(lambda: not win._run_controller.running)
    _flush_deletes()
    _wait(lambda: bool(seen))
    assert seen == [threading.get_ident()], (
        "run worker was destroyed on a worker thread (ident %s, GUI %s)"
        % (seen, threading.get_ident()))
    assert np.all(model.displayed_result == np.asarray(model.image) + 2)
    _close(win)


def test_batch_worker_is_destroyed_on_the_gui_thread(tmp_path):
    import imgio
    _app()
    studio.ERROR_HOOK = lambda *_args: None
    root = tmp_path / "inputs"; root.mkdir()
    for index in range(2):
        imgio.save(str(root / ("part_%03d.png" % index)), np.full((4, 5), index, np.uint8))
    win, _model = studio.build_window()
    win._actions["batch_apply"].trigger(); _app().processEvents()
    fields = win._batch_dialog_fields
    fields["folder"].setText(str(root)); fields["output"].setText(str(tmp_path / "out"))
    fields["patterns"].setText("part_*.png")
    plan = win._batch_plan_from_dialog()
    assert len(plan.files) == 2
    gen = win._start_batch_async(plan)
    thread, worker = win._run_controller.threads[gen]
    _assert_thread_not_connected_to_worker(thread)
    seen = _watch_destruction(worker)
    _wait(lambda: not win._run_controller.running)
    _flush_deletes()
    _wait(lambda: bool(seen))
    assert seen == [threading.get_ident()], (
        "batch worker was destroyed on a worker thread (ident %s, GUI %s)"
        % (seen, threading.get_ident()))
    assert win._last_batch_result.done == 2
    _close(win)
