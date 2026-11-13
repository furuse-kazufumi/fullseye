"""The same feel in every panel — B1 [配色] (STUDIO_INTERACTION_RULES 2026-11-13, BRIEFS B1, ADDENDA A1-A3).

Counted here (each test names its D number / gate):
  D61  RAIL_ORDER has the integration branch's Project dock; install() does not raise.
  D104 the principal (code) has no x; its bar button, Window > Panels entry and palette entry never hide it.
  D105 the title band is name | status | (space) | float x | menu, the menu at the right end.
  D57 D97 every non-principal x / float / menu button is DENSITY["title_button"] (18 px), gaps 4.

Every window here runs under the offscreen platform with its own settings file (tmp_path), Fusion style.
"""
import time

import pytest

import studio_panels
import studio_theme


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _pump(app, sec=0.25):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def _app():
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setStyle("Fusion")
    return app


def _launch(monkeypatch, ini):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(ini))
    monkeypatch.delenv("FULLSEYE_STUDIO_PERSIST_LAYOUT", raising=False)
    app = _app()
    import studio
    studio_theme.set_current(studio_theme.DEFAULT_THEME, studio_theme.DEFAULT_DENSITY)
    win, _model = studio.build_window()
    win.resize(1280, 673)
    win.show()
    _pump(app)
    return app, win


def _close(app, win):
    win.quiesce()
    win.close_guard = lambda: True
    win.close()
    _pump(app, 0.15)


def _show_all(app, win):
    for key, dock in win._docks.items():
        if dock.isHidden():
            dock.show()
    _pump(app, 0.3)


def _menu_actions(menu):
    out = []
    for a in menu.actions():
        if a.menu() is not None:
            out += _menu_actions(a.menu())
        elif not a.isSeparator():
            out.append(a)
    return out


# --------------------------------------------------------------------------- #
# D61 — the Project dock of the integration branch has a place on the panel bar
# --------------------------------------------------------------------------- #
def test_rail_order_covers_every_dock_including_project(monkeypatch):
    assert studio_panels.RAIL_ORDER == ("program", "operators", "pipeline", "variables", "display",
                                        "compare", "ab", "project")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _app()
    from PySide6 import QtCore, QtWidgets
    win = QtWidgets.QMainWindow()
    win.setCentralWidget(QtWidgets.QLabel("image"))
    win._docks = {}
    for key in studio_panels.RAIL_ORDER:                      # the integration branch's set of docks
        dock = QtWidgets.QDockWidget(key.title(), win)
        dock.setObjectName("dock_" + key)
        dock.setWidget(QtWidgets.QPlainTextEdit())
        win.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        win._docks[key] = dock
    try:
        rail = studio_panels.install(win, lambda s: s)     # D61: no KeyError
        st = win._panels
        assert set(st["buttons"]) == set(studio_panels.RAIL_ORDER) and len(st["buttons"]) == 8
        assert not st["buttons"]["project"].icon().isNull()            # a drawn glyph, not an empty icon
        assert rail.findChild(QtWidgets.QToolButton, "rail_project") is st["buttons"]["project"]
        bar = st["titles"]["project"]
        bar.fill_menu()
        acts = _menu_actions(bar.b_menu.menu())
        assert st["float_actions"]["project"] in acts and bar.a_hide in acts
    finally:
        win.deleteLater()
        _pump(app, 0.05)
    # a dock without a place on the bar is still refused loudly
    win2 = QtWidgets.QMainWindow()
    win2._docks = {"console": QtWidgets.QDockWidget("Console", win2)}
    with pytest.raises(KeyError):
        studio_panels.install(win2, lambda s: s)
    win2.deleteLater()


# --------------------------------------------------------------------------- #
# D104 — the principal (code) is never put away
# --------------------------------------------------------------------------- #
def test_principal_has_no_close_and_rail_never_hides_it(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        principals = [k for k in studio_panels.PRINCIPAL if k in win._docks]
        others = [k for k in win._docks if k not in studio_panels.PRINCIPAL]
        assert principals == ["program"] and len(others) >= 6
        for key in principals:
            bar = st["titles"][key]
            assert bar.b_close is None
            assert bar.findChild(QtWidgets.QToolButton, "dock_title_close") is None      # no x at all
            assert bar.findChild(QtWidgets.QToolButton, "dock_title_float") is not None  # the float stays
            bar.fill_menu()
            assert bar.a_hide not in [a for a in _menu_actions(bar.b_menu.menu()) if a.isVisible()]
            dock = win._docks[key]
            entries = {
                "bar button": st["buttons"][key].click,
                "Window > Panels": st["principal_actions"][key].trigger,
                "palette": win._actions["panel_show_" + key].trigger,
            }
            for name, press in entries.items():
                for _ in range(2):                                          # pressed twice in a row
                    press(); _pump(app, 0.1)
                    assert dock.isVisible() and not dock.isHidden(), (key, name)
            pa = st["principal_actions"][key]
            assert not pa.isCheckable()
            listed = _menu_actions(win._menu_panels)
            assert pa in listed and dock.toggleViewAction() not in listed       # not a check box
            assert dock.toggleViewAction() not in _menu_actions(win._more_menu_panels)
        for key in others:                                                   # the others keep their x
            assert st["titles"][key].b_close is not None, key
        st["buttons"]["variables"].click(); _pump(app, 0.15)               # and their bar button still hides
        assert win._docks["variables"].isVisible()
        st["buttons"]["variables"].click(); _pump(app, 0.15)
        assert win._docks["variables"].isHidden()
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# D105 — the menu button is at the right end of every title band
# --------------------------------------------------------------------------- #
def test_title_band_order_menu_is_rightmost(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        _show_all(app, win)
        counted = 0
        for key, bar in win._panels["titles"].items():
            lay = bar.layout()
            names = [lay.itemAt(i).widget().objectName() for i in range(lay.count())
                     if isinstance(lay.itemAt(i).widget(), QtWidgets.QToolButton)]
            want = (["dock_title_float", "dock_title_menu"] if key in studio_panels.PRINCIPAL
                    else ["dock_title_float", "dock_title_close", "dock_title_menu"])
            assert names == want, (key, names)
            last = [lay.itemAt(i).widget() for i in range(lay.count()) if lay.itemAt(i).widget() is not None][-1]
            assert last is bar.b_menu and last.text() == "≡", key
            win._docks[key].raise_(); _pump(app, 0.15)                          # a tab in front, to measure it
            if not win._docks[key].visibleRegion().isEmpty():
                xs = [b.x() for b in bar.buttons()]
                assert xs == sorted(xs) and xs[-1] == bar.b_menu.x(), (key, xs)    # left to right on screen too
                assert bar.label.x() < xs[0]
                counted += 1
        assert counted >= 3                                                  # measured on the screen, not only in the list
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# D57 D97 — the title band's buttons are 18 px, 4 px apart
# --------------------------------------------------------------------------- #
def test_non_principal_close_is_title_button_px(tmp_path, monkeypatch):
    for level in studio_theme.DENSITIES:
        assert studio_theme.DENSITY[level]["title_button"] == 18
    assert "spacing:4px" in studio_panels.rail_qss()
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        _show_all(app, win)
        side = studio_theme.density()["title_button"]
        seen = 0
        for key, bar in win._panels["titles"].items():
            assert bar.layout().spacing() == studio_theme.density()["click_gap"] == 4, key
            for b in bar.buttons():
                assert (b.width(), b.height()) == (side, side), (key, b.objectName(), b.size())
            if key not in studio_panels.PRINCIPAL and bar.b_close.isVisible():
                assert bar.b_close.width() == side and bar.b_close.height() == side
                seen += 1
        assert seen >= 3                                                     # x seen on real, shown title bands
    finally:
        _close(app, win)
