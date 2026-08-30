"""Autonomous UI-operation debug harness for Fullseye Studio.

Goal (user directive 2026-08-15): drive **real** input events — mouse
press/move/release/click, not just handler calls — through every button,
action, combo, variable list and (critically) every dock **drag**, so that
operation-level glitches and crashes are found in a sandbox *before* the user
ever touches the app.  Handler-only calls miss event-specific faults such as
the QMainWindow ``GroupedDragging`` code path, which only runs on a genuine
title-bar drag.

Why a subprocess + step log (not just a pytest):
  A hard C++/Qt segfault (the ``GroupedDragging`` suspicion) unwinds the whole
  interpreter — a Python ``try/except`` cannot catch it.  So each phase writes a
  ``{"step": name, "phase_start": true}`` line to a JSONL step log and flushes
  *before* doing anything risky.  If the process aborts, the parent reads the
  last ``phase_start`` with no matching ``phase_end`` and knows exactly which
  operation crashed, and ``faulthandler`` writes the native traceback to the
  crash log.  Python-level exceptions are caught in-process and recorded as
  ``ok=false`` findings so one bad button never stops the sweep.

Non-blocking discipline:
  Studio opens many modal dialogs (``QDialog.exec``: export/about/shortcuts/
  operator-reference/samples/palette, plus ``QFileDialog``/``QMessageBox``).
  A modal ``exec()`` would freeze the harness forever.  We therefore
    (1) stub ``studio.CONFIRM_HOOK`` / ``studio.ERROR_HOOK`` (module hooks the
        app already exposes for headless tests),
    (2) monkeypatch the ``QFileDialog`` / ``QMessageBox`` static entry points,
    (3) install a repeating **watchdog QTimer** that closes any
        ``QApplication.activeModalWidget()``.  A QTimer fires *inside* a nested
        ``exec()`` event loop, so it dismisses the custom ``QDialog.exec()``
        dialogs that cannot be patched statically.

Run:
  QT_QPA_PLATFORM=offscreen py -3.11 tools/studio_ui_harness.py \
      [--steplog PATH] [--shots DIR] [--report PATH]
Exit code: 0 if the sweep completed (findings may still be listed in the
report), non-zero only if the process itself died.
"""
from __future__ import annotations

import argparse
import faulthandler
import json
import os
import sys
import traceback
from typing import Any

# --- import the Studio module from the project root ------------------------- #
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class StepLog:
    """Append-only JSONL step log; flushed after every write so a segfault
    leaves the last-attempted step on disk (crash attribution)."""

    def __init__(self, path: str):
        self.path = path
        self._fh = open(path, "w", encoding="utf-8")
        self.findings: list[dict[str, Any]] = []
        self.n_ok = 0
        self.n_fail = 0

    def _emit(self, rec: dict[str, Any]) -> None:
        self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def start(self, step: str, **extra: Any) -> None:
        self._emit({"step": step, "phase_start": True, **extra})

    def end(self, step: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.n_ok += 1
        else:
            self.n_fail += 1
            self.findings.append({"step": step, "detail": detail})
        self._emit({"step": step, "phase_end": True, "ok": ok, "detail": detail})

    def note(self, msg: str) -> None:
        self._emit({"note": msg})

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass


def _run_step(log: StepLog, name: str, fn, **extra) -> Any:
    """Run one operation; catch Python-level errors as findings.  A hard
    segfault escapes this and is attributed via the on-disk ``phase_start``."""
    log._cur_phase = name          # so the slot-exception hook can attribute async faults
    log.start(name, **extra)
    try:
        out = fn()
        log.end(name, True)
        return out
    except Exception as e:  # noqa: BLE001 - harness records every failure
        tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        log.end(name, False, detail="%s: %s\n%s" % (type(e).__name__, e, tb))
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steplog", default=os.path.join(_ROOT, "studio_ui_steps.jsonl"))
    ap.add_argument("--shots", default=os.path.join(_ROOT, "out", "ui_harness_shots"))
    ap.add_argument("--report", default=os.path.join(_ROOT, "studio_ui_report.json"))
    ap.add_argument("--crashlog", default=os.path.join(_ROOT, "studio_ui_crash.log"))
    args = ap.parse_args()

    # Native crash capture (segfault → traceback on disk, attributable to step).
    try:
        faulthandler.enable(open(args.crashlog, "w", encoding="utf-8"))
    except Exception:
        pass

    os.makedirs(args.shots, exist_ok=True)
    log = StepLog(args.steplog)

    from PySide6 import QtWidgets, QtGui, QtCore
    from PySide6.QtTest import QTest
    import studio

    # Capture exceptions raised inside Qt slots (queued signals fired during a
    # pump()): PySide6 routes these through sys.excepthook, so record the full
    # traceback + the phase that was active — otherwise they only print one line
    # and are lost (they never reach a synchronous try/except in a phase body).
    log._cur_phase = "<pre>"

    def _slot_hook(t, v, tb):
        rec = {"slot_exception": "%s: %s" % (t.__name__, v),
               "during_phase": getattr(log, "_cur_phase", "<pre>"),
               "traceback": "".join(traceback.format_exception(t, v, tb))}
        log._emit(rec)
        log.n_fail += 1
        log.findings.append({"step": "slot:" + _cur_phase["name"],
                             "detail": rec["slot_exception"] + "\n" + rec["traceback"]})
        sys.__excepthook__(t, v, tb)
    sys.excepthook = _slot_hook

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    # ---- modal-safety: nothing may block the sweep ------------------------- #
    studio.CONFIRM_HOOK = lambda parent, title, text: False   # veto quit/clear (safe)
    studio.ERROR_HOOK = lambda *a, **k: None                  # no error modal
    _tmp_png = os.path.join(args.shots, "_probe.png")
    QtGui.QGuiApplication.primaryScreen()  # ensure screen exists offscreen

    def _patch_static(cls, name, value):
        try:
            setattr(cls, name, staticmethod(lambda *a, **k: value))
        except Exception:
            pass

    # Provide a real writable path for "save" dialogs so the save code runs;
    # return "cancel" ("") for "open" so we exercise the cancel branch without
    # needing a real image file (open-with-file is covered by pytest already).
    _patch_static(QtWidgets.QFileDialog, "getOpenFileName", ("", ""))
    _patch_static(QtWidgets.QFileDialog, "getSaveFileName",
                  (os.path.join(args.shots, "_saved.png"), ""))
    _patch_static(QtWidgets.QMessageBox, "information", QtWidgets.QMessageBox.Ok)
    _patch_static(QtWidgets.QMessageBox, "warning", QtWidgets.QMessageBox.Ok)
    _patch_static(QtWidgets.QMessageBox, "critical", QtWidgets.QMessageBox.Ok)
    _patch_static(QtWidgets.QMessageBox, "question", QtWidgets.QMessageBox.Discard)

    # Watchdog: close any modal dialog that slips through (custom QDialog.exec()).
    modal_closes = {"n": 0}

    def _kill_modal():
        # Close BOTH a modal dialog (QDialog.exec) and a popup (QMenu.exec is a
        # *popup*, not a modal widget — activeModalWidget() returns None for it,
        # so a context menu would block the sweep forever without this).
        closed = False
        for getter in (app.activeModalWidget, app.activePopupWidget):
            w = getter()
            if w is not None:
                try:
                    w.close()
                except Exception:
                    pass
                closed = True
        if closed:
            modal_closes["n"] += 1
    wd = QtCore.QTimer()
    wd.setInterval(30)
    wd.timeout.connect(_kill_modal)
    wd.start()

    def pump(ms: int = 40) -> None:
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, ms)

    try:
        import shiboken6
    except Exception:
        shiboken6 = None

    def probe_primary(tag: str) -> None:
        """Record whether the resident primary graphics window (and its image
        view) is still alive + still in the MDI — pinpoints which op destroys it."""
        gp = win.findChild(QtWidgets.QWidget, "graphics_primary")
        alive = gp is not None and (shiboken6 is None or shiboken6.isValid(gp))
        in_mdi = False
        if alive:
            try:
                in_mdi = any(s.widget() is gp for s in win._mdi.subWindowList())
            except Exception:
                in_mdi = False
        log._emit({"probe": tag, "primary_alive": bool(alive),
                   "primary_in_mdi": bool(in_mdi),
                   "n_gfx": len(getattr(win, "_graphics_windows", []))})

    def shot(tag: str) -> None:
        probe_primary(tag)
        try:
            pm = win.grab()
            pm.save(os.path.join(args.shots, "shot_%s.png" % tag))
        except Exception:
            pass

    # ---- P0: build + show -------------------------------------------------- #
    build = _run_step(log, "P0_build", lambda: studio.build_window())
    if build is None:
        log.note("build_window failed — aborting")
        log.close()
        return 2
    win, model = build
    _run_step(log, "P0_show", lambda: (win.show(), pump(120)))
    shot("00_initial")

    # ---- helper: faithful mouse-drag (buttons held during moves) ----------- #
    def drag(widget, start, path, hold_move=True):
        """Press at ``start`` (local QPoint), MouseMove through ``path`` with the
        left button *held* (QTest.mouseMove drops button state, so we post real
        QMouseEvents), then release.  This drives the QMainWindow dock drag /
        GroupedDragging state machine the way a human title-bar drag does."""
        def _post(etype, local, buttons):
            gp = widget.mapToGlobal(local)
            ev = QtGui.QMouseEvent(etype, QtCore.QPointF(local), QtCore.QPointF(gp),
                                   QtCore.Qt.LeftButton, buttons, QtCore.Qt.NoModifier)
            QtWidgets.QApplication.sendEvent(widget, ev)
        _post(QtCore.QEvent.MouseButtonPress, start, QtCore.Qt.LeftButton)
        pump(20)
        for p in path:
            _post(QtCore.QEvent.MouseMove, p, QtCore.Qt.LeftButton if hold_move else QtCore.Qt.NoButton)
            pump(20)
        _post(QtCore.QEvent.MouseButtonRelease, path[-1] if path else start, QtCore.Qt.NoButton)
        pump(40)

    # ---- P1: click every QPushButton with REAL mouse events ---------------- #
    def p1():
        btns = win.findChildren(QtWidgets.QPushButton)
        for b in btns:
            name = b.objectName() or b.text() or "button"
            log.start("P1_click", widget=name)
            try:
                QTest.mouseClick(b, QtCore.Qt.LeftButton)
                pump(20)
                _kill_modal()
                log.end("P1_click", True)
            except Exception as e:  # noqa: BLE001
                log.end("P1_click", False, detail="%s: %s" % (type(e).__name__, e))
        return len(btns)
    _run_step(log, "P1_buttons", p1)
    shot("01_after_buttons")

    # ---- P2: trigger every QAction (watchdog dismisses any modal) ---------- #
    def _primary_in_mdi():
        gp = win.findChild(QtWidgets.QWidget, "graphics_primary")
        if gp is None:
            return None
        try:
            return any(s.widget() is gp for s in win._mdi.subWindowList())
        except Exception:
            return None

    def p2():
        import shiboken6
        acts = [a for a in win.findChildren(QtGui.QAction) if a.isEnabled()]
        prev_in = _primary_in_mdi()
        for a in acts:
            # an earlier trigger may have DESTROYED the dialog owning this action
            # (Feature inspection is WA_DeleteOnClose since 2026-08-30 — reopening
            # deletes the previous dialog and its child QActions): skip dead ones
            if not shiboken6.isValid(a):
                continue
            name = a.objectName() or a.text() or "action"
            if not name:
                continue
            log.start("P2_action", widget=name)
            try:
                a.trigger()
                pump(30)
                _kill_modal()
                now_in = _primary_in_mdi()
                if prev_in and now_in is False:
                    log._emit({"note": "PRIMARY LEFT MDI", "action": name})
                prev_in = now_in
                log.end("P2_action", True)
            except Exception as e:  # noqa: BLE001
                log.end("P2_action", False, detail="%s: %s" % (type(e).__name__, e))
        return len(acts)
    _run_step(log, "P2_actions", p2)
    shot("02_after_actions")

    # ---- P3: exercise combos (samples, display mode) ----------------------- #
    def p3():
        for cb in win.findChildren(QtWidgets.QComboBox):
            for i in range(cb.count()):
                cb.setCurrentIndex(i)
                pump(10)
        return True
    _run_step(log, "P3_combos", p3)
    shot("03_after_combos")

    # ---- P4: type a program + apply/run ------------------------------------ #
    def p4():
        prog = win._program
        prog["edit"].setPlainText("gaussian (2, 0)\nthreshold (128, 255)\n")
        prog["apply"]()
        pump(30)
        prog["run"]()
        pump(30)
        return True
    _run_step(log, "P4_program", p4)
    shot("04_after_program")

    # ---- P5: variable list select + double-click display ------------------- #
    def p5():
        vs = win._variables
        vs["refresh"]()
        pump(20)
        lst = vs["list"]
        for r in range(lst.count()):
            lst.setCurrentRow(r)
            pump(10)
            it = lst.currentItem()
            if it is not None:
                lst.itemDoubleClicked.emit(it)   # → display_variable(True) = new gfx window
                pump(20)
        return lst.count()
    _run_step(log, "P5_variables", p5)
    shot("05_after_variables")

    # ---- P6: graphics windows: open / tile / cascade / detach / reattach --- #
    def p6():
        win._new_graphics_window()
        win._new_graphics_window()
        pump(20)
        win._mdi.tileSubWindows(); pump(20)
        win._mdi.cascadeSubWindows(); pump(20)
        # detach the active graphics sub-window to a top-level, then reattach
        try:
            win._detach_graphics(); pump(30)
            win._reattach_graphics(); pump(30)
        except Exception:
            raise
        return len(win._graphics_windows)
    _run_step(log, "P6_graphics", p6)
    shot("06_after_graphics")

    # ---- P7: DOCK DRAG — the GroupedDragging crash suspect ----------------- #
    # Drag every dock by its title strip to each edge target + onto a sibling
    # dock, with the button held through the move (drives group-window creation).
    def p7_one(dock_key, target):
        d = win._docks[dock_key]
        d.show(); d.raise_(); pump(20)
        w = d.width(); h = d.height()
        start = QtCore.QPoint(max(20, w // 2), 10)          # title strip (~top)
        # walk toward target in the main window's coordinate space, mapped local
        tx, ty = target
        path = []
        for k in range(1, 9):
            px = int(start.x() + (tx - start.x()) * k / 8)
            py = int(start.y() + (ty - start.y()) * k / 8)
            path.append(QtCore.QPoint(px, py))
        drag(d, start, path)

    def p7():
        # targets are local-to-dock offsets that push the drag well past the
        # title, toward window edges (re-dock) and far corners (float / group).
        targets = [(-200, 200), (600, 200), (300, 600), (300, -120), (900, 500)]
        for key in ("operators", "program", "variables", "display", "pipeline"):
            for t in targets:
                log.start("P7_dockdrag", widget=key, target=list(t))
                try:
                    p7_one(key, t)
                    log.end("P7_dockdrag", True)
                except Exception as e:  # noqa: BLE001
                    log.end("P7_dockdrag", False, detail="%s: %s" % (type(e).__name__, e))
        return True
    _run_step(log, "P7_dockdrag_all", p7)
    shot("07_after_dockdrag")

    # ---- P8: layout presets + builtin layouts + float panels --------------- #
    def p8():
        win._save_layout_preset("harness_preset"); pump(20)
        win._apply_layout_preset("harness_preset"); pump(20)
        for nm in list(win._builtin_layouts.keys()):
            win._apply_builtin_layout(nm); pump(20)
        win._delete_layout_preset("harness_preset"); pump(10)
        # per-panel float + float-all + reset
        for key in list(win._docks.keys()):
            try:
                win._float_panel(key); pump(15)
            except Exception:
                raise
        win._float_all_panels(); pump(20)
        win._reset_layout(); pump(20)
        return True
    _run_step(log, "P8_layout", p8)
    shot("08_after_layout")

    # ---- P9: right-click context menus (watchdog closes the QMenu.exec) ---- #
    # win._ctx values are the actions_fn callbacks, not widgets; the real list
    # widgets carry the CustomContextMenu policy, so emit the signal on those.
    def p9():
        widgets = {"operators": win._op_list,
                   "pipeline": win._stage_list,
                   "variables": win._variables["list"]}
        for key, wdg in widgets.items():
            log.start("P9_context", widget=key)
            try:
                if wdg.count() > 0:
                    wdg.setCurrentRow(0)
                pump(10)
                wdg.customContextMenuRequested.emit(QtCore.QPoint(5, 5))
                pump(30)
                _kill_modal()
                log.end("P9_context", True)
            except Exception as e:  # noqa: BLE001
                log.end("P9_context", False, detail="%s: %s" % (type(e).__name__, e))
        return True
    _run_step(log, "P9_context_all", p9)
    shot("09_after_context")

    wd.stop()
    shot("10_final")

    report = {
        "ok": True,
        "steps_ok": log.n_ok,
        "steps_fail": log.n_fail,
        "modal_closes": modal_closes["n"],
        "graphics_windows": len(getattr(win, "_graphics_windows", [])),
        "findings": log.findings,
        "steplog": args.steplog,
        "shots": args.shots,
        "crashlog": args.crashlog,
    }
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    log.note("sweep complete: ok=%d fail=%d modal_closes=%d"
             % (log.n_ok, log.n_fail, modal_closes["n"]))
    log.close()
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
