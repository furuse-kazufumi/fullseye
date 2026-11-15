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
