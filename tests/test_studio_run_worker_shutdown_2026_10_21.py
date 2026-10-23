"""Regression coverage for overlapping Studio workers and Qt shutdown."""
import os
import subprocess
import sys
import textwrap

import pytest


def test_overlapping_workers_close_cleanly_in_fresh_process():
    pytest.importorskip("PySide6")
    code = textwrap.dedent(
        r"""
        import faulthandler
        import os
        import sys
        import threading
        import time

        # If the child stalls, dump every thread's stack before the parent's
        # timeout kills it (a kill leaves stdout/stderr empty and says nothing).
        faulthandler.dump_traceback_later(
            float(os.environ.get("FULLSEYE_STUDIO_SHUTDOWN_DUMP_AFTER", "100")),
            exit=True)

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        import numpy as np
        from PySide6 import QtCore, QtWidgets
        import studio

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

        def wait(predicate, timeout=5.0):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                app.processEvents()
                if predicate():
                    return
                time.sleep(0.002)
            raise AssertionError("condition timed out")

        total = int(os.environ.get("FULLSEYE_STUDIO_SHUTDOWN_REPEATS", "30"))
        original = studio.api.run_pipeline
        try:
            for iteration in range(total):
                print(f"iteration {iteration} start {time.monotonic():.3f}",
                      file=sys.stderr, flush=True)
                model = studio.PipelineModel(studio.demo_image(16))
                model.stages = [["gaussian", 0.2, 0.5]]
                win, _ = studio.build_window(model)
                entered = threading.Event()
                release = threading.Event()
                lock = threading.Lock()
                ordinal = {"n": 0}

                def ordered(value, _stages, **_kwargs):
                    with lock:
                        ordinal["n"] += 1
                        n = ordinal["n"]
                    if n == 1:
                        entered.set()
                        if not release.wait(5):
                            raise AssertionError("old generation was not released")
                    return np.full_like(value, n)

                studio.api.run_pipeline = ordered
                g1 = win._start_run_async()
                wait(entered.is_set)
                g2 = win._start_run_async()
                wait(lambda: model.displayed_generation == g2)
                release.set()
                wait(lambda: not win._run_controller.running)
                assert (g1, g2) == (1, 2)
                assert model.displayed_generation == g2
                assert not win._run_controller.threads
                assert not win._run_controller.finish_bridges
                win.close_guard = None
                win.close()
                win.deleteLater()
                QtCore.QCoreApplication.sendPostedEvents(
                    None, QtCore.QEvent.DeferredDelete)
                app.processEvents()
            print(f"codex_last: {total}/{total} passed", flush=True)
        finally:
            studio.api.run_pipeline = original
            app.quit()
        """
    )
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env["FULLSEYE_STUDIO_SHUTDOWN_REPEATS"] = "30"
    # The child dumps all thread stacks at 100 s and exits; the parent waits
    # longer so that dump (not an empty kill) is what a stall reports.  60 s
    # was hit once on a loaded CI runner with no output at all (2026-10-23).
    env["FULLSEYE_STUDIO_SHUTDOWN_DUMP_AFTER"] = "100"
    try:
        result = subprocess.run(
            [sys.executable, "-X", "faulthandler", "-c", code],
            cwd=os.path.dirname(os.path.dirname(__file__)), env=env,
            capture_output=True, text=True, timeout=150,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        err = exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        pytest.fail("Studio worker child did not finish in 150 s\n"
                    + out + err[-8000:])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "codex_last: 30/30 passed" in result.stdout
    assert "Fatal Python error" not in result.stderr
