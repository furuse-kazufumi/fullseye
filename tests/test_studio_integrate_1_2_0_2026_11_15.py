"""The fixes made while merging the five Studio 1.2.0 branches into integrate/studio-1-2-0-2026-11-13 (2026-11-15).

Each test was seen failing on the code before its fix (the merged tree without the change).

  test_one_window_after_another_keeps_one_application_hand_filter
      studio_panels.install put one application-wide event filter (HandFollowsEnabled, D03) per window. Every
      window built in a process added another one, so every event of the application ran through N Python
      filters: the merged Studio test run slowed down test after test (260 s for one test) and the workers died
      with access violations inside that filter. One filter for the application.

Where the look branch's frame met the integration branch's Python mode (step 1), the existing tests of the two
branches are the regression tests (each failed on the merged tree before its fix; logs in the integration report):
  - Project dock registered as a panel (status, 3 menu entries, no-strip reason): test_every_strip_button_is_one_
    menu_entry_away, test_every_panel_declares_its_strip_and_the_ledger_counts_them_all.
  - the Python mode's row wraps (FlowRow): test_code_can_be_a_tall_column_or_a_wide_strip (image 196 px),
    test_the_code_strip_follows_the_same_rule, test_wide_panels_turn_their_strip_left_square_ones_keep_it_on_top.
  - the bar's hint follows the dock title: test_first_run_shows_image_and_code_and_a_bar_button_per_panel.
  - the scheme / density pass after the Python mode, popups on the scheme's roles:
    test_switching_the_scheme_reaches_every_widget, test_clickable_sizes_and_gaps.
  - completion rows after the code font: test_row_height_is_font_height_plus_4_everywhere (after a Studio window).
"""
import time

import pytest


def _pump(app, sec=0.2):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def _launch(monkeypatch, ini):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(ini))
    monkeypatch.delenv("FULLSEYE_STUDIO_PERSIST_LAYOUT", raising=False)
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setStyle("Fusion")
    import studio
    win, model = studio.build_window()
    win.resize(1280, 673)
    win.show()
    _pump(app, 0.3)
    return app, win, model


def _close(app, win):
    win.quiesce()
    win.close_guard = lambda: True
    win.close()
    _pump(app, 0.1)


_LANG_ROUNDS = r'''
import faulthandler, os, sys, time
faulthandler.enable()
from PySide6 import QtWidgets
app = QtWidgets.QApplication([]); app.setStyle("Fusion")
import studio
def pump(s):
    end = time.monotonic() + s
    while time.monotonic() < end:
        app.processEvents(); time.sleep(0.01)
w, _m = studio.build_window(); w.resize(1280, 673); w.show(); pump(0.3)
langs = ("en", "ja", "zh", "tw", "ko", "de", "hi")
for lang in langs + langs:
    w._apply_language(lang); pump(0.15)
w._apply_language("en")
print("LANGUAGE ROUNDS DONE", w._op_list.count(), flush=True)
w.close_guard = lambda: True; w.quiesce(); w.close()
'''


def test_switching_the_language_again_and_again_does_not_break_the_process(tmp_path):
    """After the first-run branch was merged (its language switch refills the 706 op rows), two rounds of the seven
    languages killed the process (access violation in op_list.clear()): the integration's Python mode rebuilt its
    variables panel into the dock on every switch, also in pipeline mode where the panel is not shown. Now it is
    rebuilt when the Python mode is entered. Run in a child process (a crash is an exit code, not a hung test)."""
    import os
    import subprocess
    import sys
    pytest.importorskip("PySide6")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", FULLSEYE_STUDIO_SETTINGS=str(tmp_path / "s.ini"),
               PYTHONUTF8="1", APPDATA=str(tmp_path), LOCALAPPDATA=str(tmp_path))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-c", _LANG_ROUNDS], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, cwd=root, timeout=600)
    assert r.returncode == 0 and "LANGUAGE ROUNDS DONE" in r.stdout, (r.returncode, r.stdout[-400:], r.stderr[-1500:])
    assert int(r.stdout.split("LANGUAGE ROUNDS DONE")[1].split()[0]) >= 100      # the op list was really refilled


def test_enter_in_the_search_on_an_op_that_cannot_be_a_stage_says_why_and_raises_nothing(tmp_path, monkeypatch):
    """(a) "difference" + Enter in the op search: the first insertable-looking row (check_difference) went to add_op,
    which called model.add_stage after push_undo and raised KeyError inside the slot (integration + look branches,
    also master). Since the first-run branch's rules are merged, Enter refuses with the reason; nothing raises, no
    stage and no undo step are added."""
    import sys
    import traceback
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    app, win, model = _launch(monkeypatch, tmp_path / "s.ini")
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda t, v, tb: raised.append("".join(traceback.format_exception(t, v, tb))))
    try:
        for word in ("difference", "check_difference"):
            undo_before = len(win._undo_stack)
            win._search.setText(word)
            _pump(app, 0.8)
            assert win._op_list.count() >= 2, word                          # the search really listed rows
            QTest.keyClick(win._search, QtCore.Qt.Key_Return)
            _pump(app, 0.5)
            assert raised == [], raised[-1][-600:]
            assert model.stages == [] and len(win._undo_stack) == undo_before, word
            assert win.statusBar().currentMessage().strip(), word           # it says why (not silent)
    finally:
        _close(app, win)


def test_first_steps_never_cut_a_step_in_the_middle(tmp_path, monkeypatch):
    """(b) The first-steps band stays one line (design D126), and when it is narrower than its three steps a step
    ends with "…" instead of a glyph cut beside the next step (the look branch saw "File ▸ Sa| 2. Open Operators"
    in en and ja with one panel shown on the right). The whole step is the tooltip."""
    app, win, _model = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720)
        checked = cut_seen = 0
        for lang in ("en", "ja"):
            win._apply_language(lang)
            _pump(app, 0.3)
            for width in (1280, 900, 760):
                win.resize(width, 720)
                win._panels["buttons"]["operators"].click() if not win._docks["operators"].isVisible() else None
                _pump(app, 0.4)
                labs = [lab for lab in win._first_steps_labels if lab.isVisible()]
                assert len(labs) == 3, (lang, width)
                for lab in labs:
                    assert hasattr(lab, "drawn_text"), "a plain QLabel cuts the sentence where the room ends"
                    shown = lab.drawn_text()
                    room = lab.contentsRect().width()
                    assert lab.fontMetrics().horizontalAdvance(shown) <= room, (lang, width, shown, room)
                    assert shown == lab.text() or shown.endswith("…"), (lang, width, shown)
                    assert lab.toolTip() == lab.text()
                    cut_seen += shown != lab.text()
                    checked += 1
                rects = [lab.geometry() for lab in labs]
                assert not any(rects[i].intersects(rects[j]) for i in range(3) for j in range(i + 1, 3))
                assert win._first_steps.height() <= 40                       # still one line (D126)
        assert checked == 2 * 3 * 3 and cut_seen >= 1                      # a narrow band was really measured
    finally:
        win._apply_language("en")
        _close(app, win)


def test_a_second_image_window_speaks_the_ui_language(tmp_path, monkeypatch):
    """(c) D30: the tools of a second image window (Fit / 1:1 / zoom / Save, their tooltips and its right-click
    entries) were English in a Japanese UI ("Zoom this window in"), and did not follow a language switch."""
    import re
    cjk = re.compile(r"[぀-ヿ㐀-鿿]")
    app, win, _model = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win._apply_language("ja")
        _pump(app, 0.3)
        sub = win._new_graphics_window()
        _pump(app, 0.3)
        gv = sub.widget()
        acts = [gv.actions[k] for k in ("fit", "actual_size", "zoom_in", "zoom_out", "save", "copy")]
        assert len(acts) == 6
        for a in acts:
            assert cjk.search(a.text()) and cjk.search(a.toolTip()), (a.text(), a.toolTip())
        win._apply_language("en")
        _pump(app, 0.3)
        assert gv.actions["zoom_in"].toolTip() == "Zoom this window in"           # and back
        win._apply_language("ja")
        _pump(app, 0.3)
        assert cjk.search(gv.actions["zoom_in"].toolTip())
    finally:
        win._apply_language("en")
        _close(app, win)


def test_the_parameter_window_opens_from_studio_wired_as_its_report_says(tmp_path, monkeypatch):
    """D87 ([束] REPORT 8.5): Window ▸ Parameters… opens the parameter window with lang=, the look branch's FlowStrip,
    the side rule and the overflow mode; the checks the report asks for after the merge: 1280x280 puts the strip on
    the left and its scroll buttons reach all 10 tools; ja tooltips of the scroll buttons are not the English
    source; set_overflow_mode(win, "wrap") reaches the window's strip; a language switch reaches the window."""
    import studio_panels
    from PySide6 import QtWidgets
    app, win, _model = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        act = win._actions["params_window"]
        menus = [m for m in win.menuBar().findChildren(QtWidgets.QMenu) if act in m.actions()]
        assert menus, "Parameters… is in no menu"
        win._apply_language("ja")
        _pump(app, 0.3)
        act.trigger()
        _pump(app, 0.5)
        pw = win._params_window
        assert pw.isVisible()
        strip = pw.panel.strip_widget()
        assert strip.objectName() == "flow_strip" and type(strip).__name__ == "FlowStrip"
        import re
        assert re.search(r"[぀-ヿ㐀-鿿]", strip.b_back.toolTip()), strip.b_back.toolTip()  # ja
        pw.resize(1280, 280)
        _pump(app, 0.6)
        assert pw.panel.strip_side_shown() == "left"
        reached = set()
        for _ in range(30):
            reached |= {b for b in strip.state["shown"]}
            if not strip.b_on.isEnabled():
                break
            strip.b_on.click()
            _pump(app, 0.05)
        assert len(set(strip.items())) == 10 and set(strip.items()) <= reached
        studio_panels.set_overflow_mode(win, "wrap")
        _pump(app, 0.2)
        assert pw.panel.strip_widget().mode == "wrap"
        win._apply_language("en")
        _pump(app, 0.3)
        assert getattr(pw.panel.tr_, "lang", None) == "en"                # the window followed the switch
        pw.close()
    finally:
        win._apply_language("en")
        _close(app, win)


def test_scroll_buttons_are_16_px_along_their_strip():
    """(d) The scroll buttons of tool strips and tab rows: 16 px along the strip at the default density (12 px was
    half a tool button: hard to hit, main's decision 2026-11-15); the number comes from studio_theme.DENSITY."""
    import studio_panels
    import studio_theme
    assert studio_theme.DENSITY["compact"]["scroll_button"] == 16
    assert studio_panels.scroll_arrow("compact") == 16
    assert studio_panels.scroll_arrow("standard") == studio_theme.DENSITY["standard"]["scroll_button"] >= 16


def test_a_closed_window_stops_reading_its_panels_status(tmp_path, monkeypatch):
    """The title bands' read-outs are asked four times a second (studio_panels' status tick). A closed window kept
    asking forever: in one test process every closed window went on reading its op list and stage list (the
    merged run's workers died inside op_list.clear() of later windows). Closed = the tick stops."""
    app, win, _model = _launch(monkeypatch, tmp_path / "s.ini")
    tick = win._panels["status_tick"]
    assert tick.isActive()
    asked = []
    bar = win._panels["titles"]["operators"]
    monkeypatch.setattr(bar, "update_status", lambda *a: asked.append(1))
    win._docks["operators"].show()
    _pump(app, 0.6)
    assert asked                                                       # shown: it is read
    _close(app, win)
    asked.clear()
    _pump(app, 0.6)
    assert not tick.isActive() and asked == []                         # closed: never again


def test_one_window_after_another_keeps_one_application_hand_filter(tmp_path, monkeypatch):
    """Three windows in one process: one EnabledChange of one button reaches fix_hand once, not once per window."""
    import studio_panels
    from PySide6 import QtWidgets
    wins = []
    try:
        for i in range(3):
            app, win, _model = _launch(monkeypatch, tmp_path / ("s%d.ini" % i))
            wins.append(win)
        calls = []
        real = studio_panels.fix_hand
        monkeypatch.setattr(studio_panels, "fix_hand", lambda b: (calls.append(b), real(b))[1])
        probe = QtWidgets.QToolButton(wins[-1])
        probe.show()
        _pump(app, 0.05)
        calls.clear()
        probe.setEnabled(False)
        _pump(app, 0.05)
        assert [c for c in calls if c is probe] == [probe], len(calls)
        probe.setEnabled(True)
        _pump(app, 0.05)
        assert len([c for c in calls if c is probe]) == 2
    finally:
        for w in wins:
            _close(QtWidgets.QApplication.instance(), w)
