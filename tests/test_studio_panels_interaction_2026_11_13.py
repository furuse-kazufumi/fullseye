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
    win._test_model = _model                     # for the tests that add stages
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
    """Every entry of ``menu`` and of its submenus. The submenus are found as the menu's children, never
    through QAction.menu(): with PySide6 6.11.1 that call lets go of the submenu when the action's wrapper
    is collected, and the window's own reference to it (View > Colour scheme ...) is dead afterwards."""
    from PySide6 import QtWidgets
    subs = {m.menuAction(): m for m in menu.findChildren(QtWidgets.QMenu)}
    out = []
    for a in menu.actions():
        if a in subs:
            out += _menu_actions(subs[a])
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
        assert len(others) >= 6
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
            assert last is bar.b_menu and last.text() == "" and not last.icon().isNull(), key   # D130: drawn
            assert last.accessibleName().endswith(win._panels["tr"](studio_panels.S_MENU)), key
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


# --------------------------------------------------------------------------- #
# A1 A2 A3 — one strip for every panel's tools and every tab row
# --------------------------------------------------------------------------- #
_MAX = 16777215


def test_flow_plan_and_scroll_reach_without_qt():
    fp, sr = studio_panels.flow_plan, studio_panels.scroll_reach
    five = [24] * 5
    assert fp(five, 200, "scroll", 4) == {"lines": [[0, 1, 2, 3, 4]], "scroll": None}       # fits: one line
    assert fp(five, 100, "scroll", 4) == {"lines": [[0, 1, 2, 3, 4]], "scroll": 0}          # too long: it scrolls
    assert fp(five, 60, "wrap", 4) == {"lines": [[0, 1], [2, 3], [4]], "scroll": None}       # wraps: 3 rows
    assert fp([24] * 8, 60, "wrap", 4) == {"lines": [[0, 1], [2, 3], [4, 5, 6, 7]], "scroll": 2}   # cap 3: the last scrolls
    assert fp([24] * 8, 60, "wrap", 4, max_lines=2) == {"lines": [[0, 1], [2, 3, 4, 5, 6, 7]], "scroll": 1}
    assert fp([24, 80], 60, "wrap", 4)["scroll"] == 0                     # an item longer than the strip cannot wrap
    assert fp([24, 24, 24], 60, "wrap", [0, 4, 8])["lines"] == [[0, 1], [2]]              # a group gap is wider
    assert fp([24, 24, 24], 55, "wrap", [0, 8, 4])["lines"] == [[0], [1, 2]]
    assert fp([], 10) == {"lines": [], "scroll": None}
    assert fp([24] * 3, 0, "wrap") == {"lines": [[0, 1, 2]], "scroll": None}             # no length yet: as built
    assert sr(five, 4, 52, 0) == (0, 2, 3)                                # 2 shown; the last one is shown from 3 on
    assert sr(five, 4, 52, 9) == (3, 5, 3)                                # a start past the end is pulled back
    assert sr(five, 4, 10, 0) == (0, 1, 4)                                # less room than one item: still one shown
    assert sr([], 4, 50, 2) == (0, 0, 0)
    reach = set()
    first = 0
    while True:                                                           # stepping one at a time reaches every item
        f, e, last = sr(five, 4, 52, first)
        reach |= set(range(f, e))
        if f >= last:
            break
        first = f + 1
    assert reach == set(range(5))
    with pytest.raises(ValueError):
        fp([24, 24], 30, "wrap", [0, 4, 4])
    assert [studio_panels.normalise_overflow_mode(v) for v in ("WRAP", " scroll ", None, "fold")] == [
        "wrap", "scroll", "scroll", "scroll"]
    assert studio_panels.OVERFLOW_MODES == ("scroll", "wrap") and studio_panels.WRAP_MAX_LINES == 3
    assert studio_panels.scroll_arrow("compact") == 12 and studio_panels.scroll_arrow("standard") == 14
    assert not hasattr(studio_panels, "_find_strips")                     # nothing is guessed any more (A1)


def _strip_rows(win):
    return [r for r in studio_panels.panel_ledger(win) if r["strip"] is not None]


def _subwindow_of(widget):
    from PySide6 import QtWidgets
    w = widget
    while w is not None and not isinstance(w, QtWidgets.QMdiSubWindow):
        w = w.parentWidget()
    return w


def _shape_panel(app, win, row, w, h):
    """Give one panel the shape w x h: a dock floats and is resized, an image window is un-maximised."""
    shape = row["shape"]
    if row["kind"] in ("dock", "code"):
        if not shape.isFloating():
            studio_panels.toggle_float(win, row["key"], True)
        shape.resize(w, h)
    else:
        sub = _subwindow_of(shape)
        assert sub is not None, row["key"]
        if sub.isMaximized():
            sub.showNormal()
            _pump(app, 0.1)
        sub.resize(w + sub.width() - shape.width(), h + sub.height() - shape.height())
    _pump(app, 0.35)
    return shape.width(), shape.height()


def _line_of(strip):
    """(x centres, y centres) of the strip's items, all of which must be in sight."""
    from PySide6 import QtCore
    items = [b for b in strip.items() if not b.isHidden()]
    assert items and set(items) <= set(strip.state["shown"]), strip.property("flowKey")
    cs = [b.mapTo(strip.window(), QtCore.QPoint(b.width() // 2, b.height() // 2)) for b in items]
    return [c.x() for c in cs], [c.y() for c in cs]


def _is_column(strip):
    xs, ys = _line_of(strip)
    return strip.orientation == "v" and max(xs) - min(xs) <= 1 and ys == sorted(ys) and len(set(ys)) == len(ys)


def _is_row(strip):
    xs, ys = _line_of(strip)
    return strip.orientation == "h" and max(ys) - min(ys) <= 1 and xs == sorted(xs) and len(set(xs)) == len(xs)


def test_every_panel_declares_its_strip_and_the_ledger_counts_them_all(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        sub = win._new_graphics_window(); _pump(app, 0.3)                  # a second image window
        assert sub is not None
        ledger = studio_panels.panel_ledger(win)
        kinds = [r["kind"] for r in ledger]
        assert len(ledger) >= len(win._docks) + 2 == 9                    # every dock + the main image + Graphics 2
        assert kinds.count("code") == 1 and kinds.count("image") >= 2
        assert len({r["key"] for r in ledger}) == len(ledger)
        strips = 0
        for r in ledger:
            if r["strip"] is None:                                         # no strip: only with its reason
                assert r["reason"] and r["key"] in studio_panels.STRIP_EXEMPT, r["key"]
                continue
            s = r["strip"]
            assert s.objectName() == "flow_strip" and s.property("flowKind") == "tools", r["key"]
            assert type(s).__name__ == "FlowStrip" and len(s.items()) >= 1, r["key"]
            assert all(isinstance(b, QtWidgets.QAbstractButton) for b in s.items()), r["key"]
            strips += 1
        assert strips >= 7                                                 # program operators pipeline variables ab + 2 images
        assert {r["key"] for r in ledger if r["strip"] is None} == set(studio_panels.STRIP_EXEMPT) & set(win._docks)
        assert sum(len(r["strip"].items()) for r in _strip_rows(win)) >= 32
        # every strip of the window is the same part; the tab rows too (counted by name and type)
        every = win.findChildren(QtWidgets.QWidget, "flow_strip")
        assert {type(s).__name__ for s in every} == {"FlowStrip"}
        assert set(studio_panels.all_strips(win)) <= set(every)
        assert not win.findChildren(QtWidgets.QToolButton, "strip_more")     # the old "..." is gone (A2)
    finally:
        _close(app, win)


def test_every_strip_button_is_one_menu_entry_away(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win._new_graphics_window(); _pump(app, 0.3)
        st = win._panels
        reach = st["strip_action_of"]
        menubar = set(_menu_actions(win.menuBar()))
        counted = 0
        for r in _strip_rows(win):
            for b in r["strip"].items():
                if r["kind"] == "image" and r["key"] != "graphics_1":
                    view = r["shape"]                                       # another image window: its own right-click
                    assert b.defaultAction() in view.actions.values(), r["key"]
                    counted += 1
                    continue
                act = reach.get(b)
                assert act is not None, (r["key"], b.toolTip())
                if r["kind"] == "image" or b in st.get("strip_menubar", ()):  # the main image, and a panel's
                    assert act in menubar, (r["key"], act.text())           # file buttons: the window's menus
                else:                                                       # a panel: its own menu button
                    bar = st["titles"][r["key"]]
                    bar.fill_menu()
                    assert act in _menu_actions(bar.b_menu.menu()), (r["key"], act.text())
                assert act.text().strip(), (r["key"], b.toolTip())
                counted += 1
        assert counted >= 32
        for key, bar in st["titles"].items():                              # still 3..8 of its own (user, 2026-11-13)
            own = [a for a in bar.actions if a is not None]
            assert studio_panels.MENU_OWN_MIN <= len(own) <= studio_panels.MENU_OWN_MAX, (key, len(own))
            assert len(own) == len(set(own)), key                           # one function, one entry
    finally:
        _close(app, win)


def test_wide_panels_turn_their_strip_left_square_ones_keep_it_on_top(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1600, 1000); _pump(app, 0.2)
        win._new_graphics_window(); _pump(app, 0.3)
        _show_all(app, win)
        rows = _strip_rows(win)
        assert len(rows) >= 7
        entries = {e["key"]: e for e in win._panels["strips"]}
        turned = 0
        for r in rows:
            s = r["strip"]
            w, h = _shape_panel(app, win, r, 1800, 330)
            assert w >= studio_panels.WIDE_ON * h, (r["key"], w, h)
            assert entries[r["key"]]["side"] == "left" and _is_column(s), (r["key"], w, h)
            w, h = _shape_panel(app, win, r, int(1.9 * 520), 520)          # between 1.6 and 2.2: stays
            assert studio_panels.WIDE_OFF < w / h < studio_panels.WIDE_ON, (r["key"], w, h)
            assert entries[r["key"]]["side"] == "left" and _is_column(s), r["key"]
            w, h = _shape_panel(app, win, r, 640, 640)
            assert w <= studio_panels.WIDE_OFF * h, (r["key"], w, h)
            assert entries[r["key"]]["side"] == "top" and _is_row(s), (r["key"], w, h)
            w, h = _shape_panel(app, win, r, int(1.9 * 520), 520)
            assert entries[r["key"]]["side"] == "top" and _is_row(s), r["key"]
            turned += 1
        assert turned == len(rows) >= 7
    finally:
        _close(app, win)


def test_one_setting_fixes_the_side_of_every_strip_and_tab_row(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        _show_all(app, win)
        rows = _strip_rows(win)
        assert len(rows) >= 6
        for mode, want in (("left", "v"), ("top", "h")):
            studio_panels.set_strip_mode(win, mode); _pump(app, 0.3)
            assert [r["strip"].orientation for r in rows] == [want] * len(rows), mode
        studio_panels.set_strip_mode(win, "auto"); _pump(app, 0.3)
        st = win._panels
        view = win._menus["view"]
        for a in list(st["strip_actions"].values()) + list(st["overflow_actions"].values()):
            assert a in view.actions() and a in win._actions.values(), a.text()   # View menu and the palette
            assert a in st["layout_button"].menu().actions(), a.text()             # and the bar's layout menu
    finally:
        _close(app, win)


def test_the_code_strip_follows_the_same_rule(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.3)
        entry = [e for e in win._panels["strips"] if e["key"] == "program"][0]
        dock = win._docks["program"]
        studio_panels.set_code_side(win, "bottom"); _pump(app, 0.4)       # under the image: wide
        assert dock.width() >= studio_panels.WIDE_ON * dock.height() and entry["side"] == "left"
        assert _is_column(entry["strip"])
        studio_panels.set_code_side(win, "left"); _pump(app, 0.4)         # the usual tall column: stays on top
        assert dock.height() > dock.width() and entry["side"] == "top" and _is_row(entry["strip"])
        assert len(entry["strip"].items()) >= 5
    finally:
        _close(app, win)


def _longest(strip):
    """The longest item along the strip."""
    return max((b.width() if strip.orientation == "h" else b.height()) for b in strip.items())


def _force_length(strip, length):
    if strip.orientation == "h":
        strip.setFixedWidth(length)
    else:
        strip.setFixedHeight(length)


def _free_length(strip):
    if strip.orientation == "h":
        strip.setMinimumWidth(0); strip.setMaximumWidth(_MAX)
    else:
        strip.setMinimumHeight(0); strip.setMaximumHeight(_MAX)


def _walk(app, strip):
    """Press the 'on' button to the end; every item seen in sight on the way (and never under a button)."""
    from PySide6 import QtCore
    assert strip.state["scrolling"] and strip.b_back.isVisible() and strip.b_on.isVisible()
    rewind = 0
    while strip.b_back.isEnabled() and rewind < 60:                          # back to the start first
        strip.b_back.click(); _pump(app, 0.01)
        rewind += 1
    assert not strip.b_back.isEnabled() and strip.b_on.isEnabled()          # at the start: back is disabled
    assert strip.b_on.autoRepeat() and strip.b_back.autoRepeat()           # held = repeat
    seen, steps = set(), 0
    while True:
        for b in strip.state["shown"]:
            g = QtCore.QRect(b.pos(), b.size())
            assert strip.rect().contains(g), strip.property("flowKey")
            if strip.state["scrolling"] and b in strip.state.get("scroll_items", strip.items()):
                assert not g.intersects(strip.b_back.geometry()) and not g.intersects(strip.b_on.geometry())
            seen.add(b)
        if not strip.b_on.isEnabled() or steps > 60:
            break
        strip.b_on.click(); _pump(app, 0.02)
        steps += 1
    assert not strip.b_on.isEnabled() and strip.b_back.isEnabled()          # at the end: on is disabled
    return seen


def test_short_strips_show_scroll_buttons_and_reach_every_tool(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtGui
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        _show_all(app, win)
        rows = [r for r in _strip_rows(win) if len(r["strip"].items()) >= 2]
        assert len(rows) >= 5
        reached = total = 0
        for mode in ("top", "left"):                                       # across and down
            studio_panels.set_strip_mode(win, mode); _pump(app, 0.3)
            for r in rows:
                s = r["strip"]
                if r["key"] in win._docks:
                    win._docks[r["key"]].raise_(); _pump(app, 0.15)
                least = s.minimumSizeHint()                               # two buttons long (never under the minimum)
                _force_length(s, max(2 * _longest(s), least.width() if s.orientation == "h" else least.height()))
                _pump(app, 0.15)
                seen = _walk(app, s)
                assert seen == set(s.items()), (mode, r["key"], len(seen), len(s.items()))
                reached += len(seen); total += len(s.items())
                if mode == "top":                                          # the wheel scrolls too
                    while s.b_back.isEnabled():
                        s.b_back.click(); _pump(app, 0.01)
                    ev = QtGui.QWheelEvent(QtCore.QPointF(5, 5), QtCore.QPointF(s.mapToGlobal(QtCore.QPoint(5, 5))),
                                           QtCore.QPoint(0, 0), QtCore.QPoint(0, -120), QtCore.Qt.NoButton,
                                           QtCore.Qt.NoModifier, QtCore.Qt.NoScrollPhase, False)
                    QtCore.QCoreApplication.sendEvent(s, ev); _pump(app, 0.02)
                    assert s.state["first"] == 1, r["key"]
                _free_length(s); _pump(app, 0.2)                           # room again: the buttons go
                assert not s.state["scrolling"] and s.b_back.isHidden() and s.b_on.isHidden(), (mode, r["key"])
        assert reached == total >= 2 * 25
    finally:
        studio_panels.set_strip_mode(win, "auto")
        _close(app, win)


def _tab_row(win, bar):
    rows = [r for r in win._panels["tab_rows"].values() if r.bar is bar]
    assert len(rows) == 1
    return rows[0]


def _tab_bars(win, n=None):
    from PySide6 import QtWidgets
    return [b for b in win.findChildren(QtWidgets.QTabBar)
            if b.parentWidget() is win and b.isVisible() and (n is None or b.count() == n)]


def _right_column_tabs(app, win, keys=("operators", "pipeline", "variables", "display")):
    from PySide6 import QtWidgets
    for k in keys:
        win._docks[k].show()
    _pump(app, 0.4)
    bars = [b for b in _tab_bars(win) if b.count() >= len(keys)
            and b.shape() in (QtWidgets.QTabBar.RoundedNorth, QtWidgets.QTabBar.TriangularNorth)]
    assert len(bars) == 1
    return bars[0]


def _bottom_tabs(app, win, keys=("variables", "compare", "ab")):
    from PySide6 import QtCore, QtWidgets
    for k, d in win._docks.items():                                       # only the group under the image
        if k not in keys and k not in studio_panels.PRINCIPAL:
            d.hide()
    studio_panels.set_code_side(win, "left")
    for k in keys:
        win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, win._docks[k])
        win._docks[k].show()
    for k in keys[1:]:
        win.tabifyDockWidget(win._docks[keys[0]], win._docks[k])
    win._docks[keys[0]].raise_()
    _pump(app, 0.5)
    bars = [b for b in _tab_bars(win, len(keys)) if b.shape() in (QtWidgets.QTabBar.RoundedWest,
                                                                  QtWidgets.QTabBar.TriangularWest)]
    assert len(bars) == 1
    return bars[0]


def test_tab_rows_are_the_same_strip_scroll_when_short_and_reach_every_tab(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtGui
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.2)
        for make, vertical in ((_right_column_tabs, False), (_bottom_tabs, True)):
            bar = make(app, win)
            row = _tab_row(win, bar)
            s = row.strip
            assert s.objectName() == "flow_strip" and s.property("flowKind") == "tabs"
            assert s.parentWidget() is bar and s.geometry() == bar.rect()       # laid over Qt's own bar
            assert bar.usesScrollButtons() and bar.elideMode() == QtCore.Qt.ElideNone and not bar.tabsClosable()
            assert [t.label for t in row.tabs] == [bar.tabText(i) for i in range(bar.count())]
            assert all(t.vertical == vertical for t in row.tabs) and s.orientation == ("v" if vertical else "h")
            hints = [(t.sizeHint().height() if vertical else t.sizeHint().width()) for t in row.tabs]
            along, total = max(hints), sum(hints)
            full = bar.height() if vertical else bar.width()
            if total <= full:                                                  # room enough: every tab, no buttons
                assert set(s.state["shown"]) == set(row.tabs)
                assert not s.state["scrolling"] and s.b_on.isHidden()
            else:                                                              # already too many: it scrolls
                assert s.state["scrolling"] and s.b_on.isVisible()
            if vertical:
                bar.setFixedHeight(int(1.5 * along))
            else:
                bar.setFixedWidth(int(1.5 * along))
            _pump(app, 0.3)                                                    # 1.5 tabs long
            assert s.geometry() == bar.rect()
            seen = _walk(app, s)
            assert seen == set(row.tabs) and len(seen) == bar.count() >= 3, (
                vertical, sorted(t.label for t in seen), [(t.label, t.geometry().getRect()) for t in row.tabs],
                s.geometry().getRect(), s.state["first"], s.state["last_first"])
            # the scroll buttons of a tab row are those of a tool strip (same look, same size)
            assert (s.b_on.height() if vertical else s.b_on.width()) == studio_panels.scroll_arrow()
            while s.b_back.isEnabled():                                        # a chosen tab out of sight comes into sight:
                s.b_back.click(); _pump(app, 0.01)                             # from the start, the last tab ...
            last = bar.count() - 1 if bar.currentIndex() != bar.count() - 1 else bar.count() - 2
            assert row.tabs[last] not in s.state["shown"]
            bar.setCurrentIndex(last); _pump(app, 0.1)
            assert row.tabs[last] in s.state["shown"] and row.tabs[last].isChecked()
            while s.b_on.isEnabled():                                          # ... from the end, the first one
                s.b_on.click(); _pump(app, 0.01)
            assert row.tabs[0] not in s.state["shown"] and bar.currentIndex() != 0
            bar.setCurrentIndex(0); _pump(app, 0.1)
            assert row.tabs[0] in s.state["shown"] and row.tabs[0].isChecked()
            key = row.key_at(bar.count() - 1)                                  # a tab's right-click = that panel's menu
            ev = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, QtCore.QPoint(3, 3),
                                         row.tabs[-1].mapToGlobal(QtCore.QPoint(3, 3)))
            QtCore.QCoreApplication.sendEvent(row.tabs[-1], ev); _pump(app, 0.05)
            menu = win._panels["open_menu"]
            assert menu is win._panels["titles"][key].b_menu.menu()
            assert win._panels["float_actions"][key] in menu.actions()
            menu.close()
            bar.setMinimumSize(0, 0); bar.setMaximumSize(_MAX, _MAX); _pump(app, 0.3)
            assert s.state["scrolling"] == (total > full)                      # room again: as before
    finally:
        _close(app, win)


def test_vertical_tabs_never_cut_a_name_in_any_language(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.2)
        bar = _bottom_tabs(app, win)
        counted = 0
        for lang in ("ja", "de", "en", "zh", "ko", "tw"):
            win._apply_language(lang); _pump(app, 0.4)
            row = _tab_row(win, bar)
            row.place(); _pump(app, 0.1)
            assert [t.label for t in row.tabs] == [bar.tabText(i) for i in range(bar.count())], lang
            assert len(row.tabs) >= 3
            for t in row.tabs:
                need = t.fontMetrics().horizontalAdvance(t.label) + 2
                assert t.vertical and t.height() >= need, (lang, t.label, t.height(), need)   # the whole name
                counted += 1
        assert counted >= 18
        win._apply_language("en"); _pump(app, 0.2)
        row = _tab_row(win, bar)
        assert any("&" in t.label for t in row.tabs)                          # Variables & Objects keeps its '&'
    finally:
        win._apply_language("en")
        _close(app, win)


def test_wrap_mode_reaches_every_tool_and_tab_and_one_switch_reaches_every_panel(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.2)
        _show_all(app, win)
        bar = _right_column_tabs(app, win)
        bar.setCurrentIndex(2); _pump(app, 0.1)
        current = bar.currentIndex()
        checked = {k: b.isChecked() for k, b in win._panels["buttons"].items()}
        n = studio_panels.set_overflow_mode(win, "wrap"); _pump(app, 0.3)  # one switch ...
        every = studio_panels.all_strips(win)
        assert n == len(every) >= len(_strip_rows(win)) + 1                # ... reaches every strip and tab row
        assert len(every) >= 7                                             # 5 panels + the main image + the tab row
        assert all(s.mode == "wrap" for s in every)
        assert win._panels["overflow_actions"]["wrap"].isChecked()
        assert bar.currentIndex() == current                               # the chosen tab and the pressed state stay
        assert {k: b.isChecked() for k, b in win._panels["buttons"].items()} == checked
        gap = studio_theme.density()["click_gap"]
        for mode in ("top", "left"):
            studio_panels.set_strip_mode(win, mode); _pump(app, 0.3)
            for r in _strip_rows(win):
                s = r["strip"]
                k = len(s.items())
                if k < 3:
                    continue
                _force_length(s, 2 * _longest(s) + gap + 2); _pump(app, 0.15)   # two per row: ceil(k / 2) rows
                need = -(-k // 2)
                if need <= studio_panels.WRAP_MAX_LINES:
                    assert s.state["lines"] == need and not s.state["scrolling"], (mode, r["key"], s.state["lines"])
                    assert set(s.state["shown"]) == set(s.items()), (mode, r["key"])
                else:                                                      # past 3 rows: the last one scrolls
                    assert s.state["lines"] == studio_panels.WRAP_MAX_LINES and s.state["scrolling"]
                    assert _walk(app, s) | set(s.state["shown"]) == set(s.items()), (mode, r["key"])
                assert s.state["lines"] <= studio_panels.WRAP_MAX_LINES
                least = s.minimumSizeHint()                               # the shortest a layout gives it
                _force_length(s, least.width() if s.orientation == "h" else least.height()); _pump(app, 0.15)
                assert 2 <= s.state["lines"] <= studio_panels.WRAP_MAX_LINES, (mode, r["key"])
                seen = set(s.state["shown"])
                if s.state["scrolling"]:
                    seen |= _walk(app, s)
                assert seen == set(s.items()), (mode, r["key"])
                _free_length(s); _pump(app, 0.15)
        studio_panels.set_strip_mode(win, "auto"); _pump(app, 0.3)
        row = _tab_row(win, bar)                                            # tabs wrap onto rows too
        along = max(t.sizeHint().width() for t in row.tabs)
        bar.setFixedWidth(int(2.2 * along)); _pump(app, 0.4)
        s = row.strip
        assert 2 <= s.state["lines"] <= studio_panels.WRAP_MAX_LINES and not s.state["scrolling"]
        assert set(s.state["shown"]) == set(row.tabs)
        assert abs(bar.height() - s.state["lines"] * row.t1) <= 2, (bar.height(), s.state["lines"], row.t1)
        assert bar.currentIndex() == current and row.tabs[current].isChecked()
        bar.setMinimumSize(0, 0); bar.setMaximumSize(_MAX, _MAX)
        assert studio_panels.set_overflow_mode(win, "scroll") == len(studio_panels.all_strips(win))
        _pump(app, 0.3)
        assert bar.currentIndex() == current
        assert abs(bar.height() - row.t1) <= 2                             # back to one row
    finally:
        _close(app, win)


def test_the_overflow_setting_is_saved_and_back_after_a_restart(tmp_path, monkeypatch):
    from PySide6 import QtCore
    ini = tmp_path / "s.ini"
    app, win = _launch(monkeypatch, ini)
    st = win._panels
    assert st["overflow_mode"] == "scroll" and st["overflow_actions"]["scroll"].isChecked()   # the default
    st["overflow_actions"]["wrap"].trigger(); _pump(app, 0.2)
    assert st["overflow_mode"] == "wrap"
    _close(app, win)
    s = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
    assert s.value("panels/overflow_mode") == "wrap"
    del s
    app, win = _launch(monkeypatch, ini)
    try:
        assert win._panels["overflow_mode"] == "wrap" and win._panels["overflow_actions"]["wrap"].isChecked()
        assert all(s.mode == "wrap" for s in studio_panels.all_strips(win))
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# D01 D02 D03 — the top band
# --------------------------------------------------------------------------- #
def _qss_rules(qss):
    """{selector: {property: value}} from a style sheet (enough for the theme's flat rules)."""
    import re
    out = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", qss):
        props = {}
        for part in body.split(";"):
            if ":" in part:
                k, v = part.split(":", 1)
                props[k.strip()] = v.strip()
        for s in sel.split(","):
            out.setdefault(s.strip(), {}).update(props)
    return out


def test_qss_has_checked_and_disabled_rules_for_toolbutton(tmp_path, monkeypatch):
    for theme in studio_theme.THEMES:
        p = studio_theme.PALETTES[theme]
        rules = _qss_rules(studio_theme.build_qss(theme))
        base, on, off = rules["QToolButton"], rules["QToolButton:checked"], rules["QToolButton:disabled"]
        assert on["background"] != base["background"] and p["accent"] in on["border"]       # pressed: its own look
        assert off["color"] == p["off"] != base["color"]                                   # disabled: the off colour
        assert off["background"] != base["background"]
        assert rules["QPushButton:disabled"]["color"] == p["off"]
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    from PySide6 import QtCore
    try:
        sw = win._mode_switch                                               # D02: "code" pressed at start
        assert win._work_mode_actions["code"].isChecked() and sw.isChecked()
        assert sw.text() == win._work_mode_actions["code"].text()
        hand = [b for b in win.findChildren(type(sw)) if b.property("iconOnly")]
        assert len(hand) >= 20
        b = win._panel_buttons["program"]["run"]                             # D03: no pointing hand when disabled
        assert b.cursor().shape() == QtCore.Qt.PointingHandCursor
        b.setEnabled(False); _pump(app, 0.05)
        assert b.cursor().shape() != QtCore.Qt.PointingHandCursor
        b.setEnabled(True); _pump(app, 0.05)
        assert b.cursor().shape() == QtCore.Qt.PointingHandCursor
        disabled = [x for x in hand if not x.isEnabled()]
        assert disabled and all(x.cursor().shape() != QtCore.Qt.PointingHandCursor for x in disabled)
    finally:
        _close(app, win)


def test_top_band_text_buttons_only_run_and_examples(tmp_path, monkeypatch):
    import re
    from PySide6 import QtCore, QtGui, QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        bars = [win.findChild(QtWidgets.QToolBar, n) for n in ("main_tools", "work_modes")]
        assert all(b is not None for b in bars)
        buttons = [w for b in bars for w in b.findChildren(QtWidgets.QToolButton)
                   if w.isVisible() and w.objectName() != "qt_toolbar_ext_button"]
        assert len(buttons) >= 8
        texty = [w for w in buttons if w.icon().isNull() or w.toolButtonStyle() == QtCore.Qt.ToolButtonTextOnly]
        allowed = {"Run", "Examples", "実行", "例を開く"}
        assert [w.objectName() for w in texty if w.text() not in allowed] == ["work_mode_switch"], \
            [(w.objectName(), w.text()) for w in texty]
        sw = win._mode_switch                                               # one switch for the four modes
        modes = list(win._work_mode_actions.values())
        assert len(modes) == 4
        assert sw.menu().actions() == modes
        assert sw.popupMode() == QtWidgets.QToolButton.InstantPopup
        group = {a.actionGroup() for a in modes}
        assert len(group) == 1 and next(iter(group)).isExclusive()
        assert not any(a in bars[1].actions() for a in modes)              # not four buttons any more
        for a in modes:                                                     # the keys still work from the window
            assert a in win.actions() and a.shortcut().toString()
        modes[1].trigger(); _pump(app, 0.2)
        assert sw.text() == modes[1].text() and sw.isChecked()
        modes[3].trigger(); _pump(app, 0.2)
        assert sw.text() == modes[3].text()
        drawn = win._fs_glyph_actions                                       # Auto-update, Image focus, Find panel
        assert sorted(n for _a, n in drawn) == ["auto_update", "find_panel", "image_focus"]
        for act, _n in drawn:
            assert not act.icon().isNull()
            tip = act.toolTip()
            assert re.match(r"^[^—]+ — .+$", tip), tip                # name — what happens (key)
            key = act.shortcut().toString(QtGui.QKeySequence.NativeText)
            assert (tip.endswith("(%s)" % key) if key else not tip.endswith(")")), tip
        def switch_tip():
            """The switch's hint: what it is (no key typed by hand), then every mode with ITS key."""
            lines = sw.toolTip().split("\n")
            assert re.match(r"^[^—]+ — .+$", lines[0]) and "Ctrl" not in lines[0], lines
            assert lines[1:] == ["%s (%s)" % (a.text(), a.shortcut().toString(QtGui.QKeySequence.NativeText))
                                 for a in modes], lines
            assert len(lines) == 5
            return lines
        switch_tip()
        modes[1].trigger(); _pump(app, 0.2)                                 # not the mode the window started with
        win._apply_language("ja"); _pump(app, 0.3)                          # hints follow the language
        try:
            for a, _n in drawn:                                             # the name AND what happens
                name, _dash, effect = a.toolTip().partition(" — ")
                assert re.search(r"[぀-ヿ一-鿿]", name) and re.search(r"[぀-ヿ]", effect), a.toolTip()
                assert "—" not in effect, a.toolTip()                  # composed once, not on top of itself
            assert modes[1].isChecked() and sw.text() == modes[1].text()    # still the mode in use, in Japanese
            assert re.search(r"[぀-ヿ一-鿿]", sw.text()) and sw.isChecked()
            lines = switch_tip()
            assert len(lines) == 5
            assert all(re.search(r"[぀-ヿ一-鿿]", line) for line in lines)
            win._apply_theme(save=False); _pump(app, 0.2)                   # composing again changes nothing
            assert all(a.toolTip().count("—") == 1 for a, _n in drawn)
        finally:
            win._apply_language("en"); _pump(app, 0.2)
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# 1.2-B of the panel frame, part 1 — the title band and the menus: D14 D59 D98 D100 D111
# --------------------------------------------------------------------------- #
def _shown_tab_bars(win):
    """The tab rows of tabbed panels that are on screen (Qt parks an unused one outside the window)."""
    from PySide6 import QtWidgets
    return [b for b in win.findChildren(QtWidgets.QTabBar)
            if b.parentWidget() is win and b.isVisible() and win.rect().intersects(b.geometry())]


def test_ampersand_is_shown_in_menus_tabs_bands_and_group_titles(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    assert studio_panels.label_text("A & B") == "A && B" and studio_panels.label_text(None) == ""
    assert studio_panels.plain_text("Separate window: Variables && Objects") == "Separate window: Variables & Objects"
    assert studio_panels.plain_text("&File") == "File" and studio_panels.plain_text("A && &B") == "A & B"
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        amp = [k for k, d in win._docks.items() if "&" in d.windowTitle()]
        assert amp == ["variables"]                                         # Variables & Objects (en)
        for k in amp:
            title = win._docks[k].windowTitle()
            assert win._docks[k].toggleViewAction().text() == title.replace("&", "&&")
            assert st["float_actions"][k].text().endswith(title.replace("&", "&&"))
            assert st["titles"][k].key_menu.text().startswith(title.replace("&", "&&"))
            assert "&" in st["titles"][k].label.text()                      # the band's label shows it
        shown = [a.text() for a in _menu_actions(win._menu_panels)]
        assert len(shown) >= 14
        assert not [t for t in shown if t.startswith("Float: ")], shown   # D100: the old five are gone
        assert len([t for t in shown if t.startswith("Separate window: ")]) == len(win._docks) == 7   # one word
        assert all("& " not in t.replace("&&", "") for t in shown), shown  # no lone '&' left to be eaten
        groups = [g.title() for d in win._docks.values() for g in d.findChildren(QtWidgets.QGroupBox)]
        lone = [t for t in groups if "& " in t.replace("&&", "")]
        assert len(groups) >= 6 and not lone, lone                          # EXPORT & I/O, DISPLAY & PERCEPTION
        assert sum("&&" in t for t in groups) >= 2
        win._apply_language("ja"); win._apply_language("en"); _pump(app, 0.3)   # the language pass writes them again
        groups = [g.title() for d in win._docks.values() for g in d.findChildren(QtWidgets.QGroupBox)]
        assert sum("&&" in t for t in groups) >= 2 and not [t for t in groups if "& " in t.replace("&&", "")]
        got = {}

        def look():                                                         # the palette is modal: read it, close it
            got["labels"] = list(win._palette["labels"])
            for d in win.findChildren(QtWidgets.QDialog):
                if d.isVisible():
                    d.reject()
        from PySide6 import QtCore
        QtCore.QTimer.singleShot(300, look)
        win._actions["palette"].trigger()                                   # returns when look() closed it
        hit = [r for r in got["labels"] if "Variables" in r and "Objects" in r]
        assert hit and all("Variables & Objects" in r for r in hit), hit    # what the menu shows, not "&&"
        assert len(got["labels"]) >= 100
    finally:
        _close(app, win)


def test_tabbed_panel_band_drops_the_name_the_tab_carries_it(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        for k in ("operators", "pipeline", "variables"):
            win._docks[k].show()
        _pump(app, 0.4)
        st = win._panels
        tabbed = [k for k in ("operators", "pipeline", "variables") if win.tabifiedDockWidgets(win._docks[k])]
        assert len(tabbed) == 3
        for k in tabbed:
            assert st["titles"][k].label.isHidden(), k                      # D59: the tab says the name
        assert not st["titles"]["program"].label.isHidden()                 # alone: the band names it
        studio_panels.toggle_float(win, "variables", True); _pump(app, 0.3)
        assert not st["titles"]["variables"].label.isHidden()               # a separate window has no tab
        win._docks["variables"].hide(); win._docks["pipeline"].hide(); _pump(app, 0.4)
        assert _shown_tab_bars(win) == []
        assert not st["titles"]["operators"].label.isHidden()               # no tab row any more: the band names it again
        # a group title that only repeats the panel's name is gone (band + tab + frame said it three times)
        ops = {g.property("fsTitleWas"): g for g in win._docks["operators"].findChildren(QtWidgets.QGroupBox)
               if g.property("fsTitleWas")}
        assert list(ops) == ["OPERATORS"] and ops["OPERATORS"].title() == "" and ops["OPERATORS"].property("untitled")
        titles = [g.title() for d in win._docks.values() for g in d.findChildren(QtWidgets.QGroupBox)]
        names = {"".join(c for c in d.windowTitle().casefold() if c.isalnum()) for d in win._docks.values()}
        assert len(titles) >= 6 and not [t for t in titles if "".join(c for c in t.casefold() if c.isalnum()) in names]
        assert sum(1 for t in titles if t) >= 5                             # the others keep theirs
        win._apply_language("ja"); _pump(app, 0.4)                          # ja: the group says something else
        try:
            assert ops["OPERATORS"].title() and ops["OPERATORS"].title() != win._docks["operators"].windowTitle()
            assert not ops["OPERATORS"].property("untitled")
        finally:
            win._apply_language("en"); _pump(app, 0.3)
        assert ops["OPERATORS"].title() == ""
    finally:
        _close(app, win)


def test_panel_menu_holds_only_this_panels_things_under_short_names(tmp_path, monkeypatch):
    import re
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        common = set(st["strip_actions"].values()) | set(st["overflow_actions"].values()) | {
            a for _t, a in st["layout_actions"]}
        assert len(common) >= 7
        for key, bar in st["titles"].items():
            bar.fill_menu()
            acts = _menu_actions(bar.b_menu.menu())
            assert not (set(acts) & common), key                            # D98: the window-wide ones are elsewhere
            assert acts[-2:] == [st["float_actions"][key], bar.a_hide], key
        every = list(st["strip_actions"].values()) + list(st["overflow_actions"].values())
        view = _menu_actions(win._menus["view"])
        assert all(a in view for a in every)
        layout = win._layouts_menu                                          # Window > Layout: the settings for all
        assert all(a in layout.actions() for a in every)
        win._rebuild_layouts_menu()                                         # studio.py refills that menu ...
        assert not any(a in layout.actions() for a in every)
        layout.aboutToShow.emit()                                           # ... and they are back when it opens
        assert all(a in layout.actions() for a in every)
        assert len([a for a in layout.actions() if a in every]) == len(every)   # once each
        # entries made from buttons carry the function's own short name, not the button's whole hint
        named = 0
        for (panel, name), text in studio_panels.BUTTON_NAMES.items():
            button = win._panel_buttons[panel][name]
            act = st["button_actions"].get(button)
            if act is None:                                                 # the window has a QAction of its own for it
                assert st["strip_action_of"][button].text().strip(), (panel, name)
                continue
            assert act.text() == text.replace("&", "&&"), (panel, name, act.text())
            assert act.text() != button.toolTip().split("\n")[0] and len(act.text()) <= 40
            assert button.toolTip() and act.toolTip() == button.toolTip()   # the whole hint stays the entry's hint
            bar = st["titles"][panel]
            bar.fill_menu()
            assert act in _menu_actions(bar.b_menu.menu()), (panel, name)
            named += 1
        assert named >= 9
        made = [a for a in st["button_of"] if a.text()]
        assert len(made) >= 12 and all(len(a.text()) <= 40 and len(a.text().split()) >= 2 for a in made), [
            a.text() for a in made]                                         # no bare "Apply" / "Sync", no sentence
        win._apply_language("ja"); _pump(app, 0.4)
        try:
            for (panel, name), _text in studio_panels.BUTTON_NAMES.items():
                act = st["button_actions"].get(win._panel_buttons[panel][name])
                if act is not None:
                    assert re.search(r"[぀-ヿ一-鿿]", act.text()), (panel, name, act.text())
        finally:
            win._apply_language("en"); _pump(app, 0.3)
    finally:
        _close(app, win)


def test_bar_right_click_names_the_panel_and_never_hides_the_code(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        seen = 0
        for key in ("variables", "program"):
            st["panel_menu"](key, st["buttons"][key], st["buttons"][key].rect().center())
            menu = st["open_menu"]
            texts = [a.text() for a in menu.actions()]
            name = win._docks[key].windowTitle().replace("&", "&&")
            assert len(texts) == 2 and all(t.endswith(": " + name) for t in texts), texts   # D111
            if key == "program":
                assert texts[0].startswith("Show")                         # D104: never "Hide" on the code
                menu.actions()[0].trigger(); _pump(app, 0.1)
                assert win._docks["program"].isVisible()
            else:
                assert texts[0].startswith("Show") and win._docks[key].isHidden()
                menu.actions()[0].trigger(); _pump(app, 0.2)                # it does what it says
                assert win._docks[key].isVisible()
                st["panel_menu"](key, st["buttons"][key], st["buttons"][key].rect().center())
                assert st["open_menu"].actions()[0].text() == "Hide: " + name
                st["open_menu"].close()
            menu.close()
            seen += 1
        assert seen == 2
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# 1.2-B of the panel frame, part 2 — every list of panels is the same list: D20 D21 D60
# --------------------------------------------------------------------------- #
def _panel_keys_in(win, menu):
    entry = {}
    for k, d in win._docks.items():
        entry[win._panels["principal_actions"][k] if k in studio_panels.PRINCIPAL else d.toggleViewAction()] = k
    return [entry[a] for a in menu.actions() if a in entry]


def test_panel_lists_same_set_and_order(tmp_path, monkeypatch):
    import json
    import os
    from PySide6 import QtCore, QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        want = [k for k in studio_panels.RAIL_ORDER if k in win._docks]
        assert len(want) == len(win._docks) == 7
        assert studio_panels.panel_order(win, ["ab", "result", "program", "nope"]) == ["program", "ab"]
        rail = sorted(win._panels["buttons"], key=lambda k: win._panels["buttons"][k].y())
        assert rail == want
        assert _panel_keys_in(win, win._menu_panels) == want                # Window > Panels
        assert _panel_keys_in(win, win._more_menu_panels) == want           # More > Panels
        floats = [a for a in win._menu_panels.actions() if a in win._panels["float_actions"].values()]
        assert floats == [win._panels["float_actions"][k] for k in want]
        dlg = win._find_panel_dialog(); _pump(app, 0.2)                    # Find panel (D20: one window)
        try:
            found = dlg.findChild(QtWidgets.QListWidget)
            query = dlg.findChild(QtWidgets.QLineEdit)
            keys = [found.item(i).data(QtCore.Qt.UserRole) for i in range(found.count())]
            assert keys == want and "result" not in keys                    # the same set, the same order
            assert [found.item(i).text() for i in range(found.count())] == [win._docks[k].windowTitle() for k in want]
            assert found.currentRow() == 0                                 # the first one is chosen
            assert win._find_panel_dialog() is dlg                         # asked again: the same window
            assert len([d for d in win.findChildren(QtWidgets.QDialog) if d.isVisible()]) == 1
            query.setText("zzzz-no-such-panel"); _pump(app, 0.1)
            assert found.count() == 1 and found.item(0).data(QtCore.Qt.UserRole) is None
            assert found.item(0).text() == "No panel by that name" and not found.item(0).flags()
            query.returnPressed.emit(); _pump(app, 0.1)                    # Enter on "nothing": nothing happens
            assert dlg.isVisible()
            win._docks["variables"].hide(); _pump(app, 0.1)
            assert win._docks["variables"].isHidden()
            query.setText(win._docks["variables"].windowTitle()[:6]); _pump(app, 0.1)
            assert found.count() == 1 and found.item(0).data(QtCore.Qt.UserRole) == "variables"
            query.returnPressed.emit(); _pump(app, 0.3)                    # Enter in the box opens the first one
            assert win._docks["variables"].isVisible() and not dlg.isVisible()
        finally:
            dlg.close()
        # the hint of "Pin as A" names the panel; no hint sends the reader down a menu path that is not there
        tips = [a.toolTip() for a in win._actions.values()]
        assert len(tips) >= 40 and not [t for t in tips if "Window > Panels" in t]
        assert "A / B panel" in win._actions["pin_a"].toolTip()
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studio_assets", "i18n.json")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        row = data["tooltips"][win._tt_en[win._actions["pin_a"]]]
        assert len(row) == 6 and not [v for v in row.values() if "Window >" in v]
    finally:
        _close(app, win)


def test_float_near_the_window_and_float_all_only_what_is_shown(tmp_path, monkeypatch):
    from PySide6 import QtGui
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        hidden = [k for k, d in win._docks.items() if d.isHidden()]
        assert len(hidden) >= 5
        win._float_all_panels(True); _pump(app, 0.3)                       # D60
        assert [k for k in hidden if not win._docks[k].isHidden() or win._docks[k].isFloating()] == []
        shown = [k for k, d in win._docks.items() if not d.isHidden()]
        assert len(shown) >= 1
        assert [k for k in shown if not win._docks[k].isFloating()] == []
        screens = [s.availableGeometry() for s in QtGui.QGuiApplication.screens()]
        assert len(screens) >= 1
        off = [k for k in shown if not any(s.intersects(win._docks[k].frameGeometry()) for s in screens)]
        assert off == []                                                    # on a screen, by the window
        win._float_all_panels(False); _pump(app, 0.3)
        assert [k for k, d in win._docks.items() if d.isFloating()] == []
        # a panel that was never shown: made separate, it lands by the main window (not where Qt left it)
        key = hidden[-1]
        studio_panels.toggle_float(win, key, True); _pump(app, 0.3)
        g = win._docks[key].frameGeometry()
        assert win._docks[key].isFloating() and any(s.intersects(g) for s in screens), (key, g)
        studio_panels.toggle_float(win, key, False); _pump(app, 0.2)
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# the "Stages: N" read-out counts stages, not the hint row of an empty pipeline
# --------------------------------------------------------------------------- #
def test_stage_count_of_an_empty_pipeline_is_zero_also_after_a_language_switch(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        item = [it for it in win._panels["titles"]["pipeline"].status if it["id"] == "stages"]
        assert len(item) == 1
        read = item[0]["text"]
        assert win._stage_list.count() == 1 and not win._stage_list.item(0).flags()   # the hint row, not a stage
        assert read() == "Stages: 0"
        win._apply_language("ja"); win._apply_language("en"); _pump(app, 0.3)        # the read-out is asked again
        assert read() == "Stages: 0" and item[0]["now"] == "Stages: 0"
        win._docks["pipeline"].show(); _pump(app, 0.5)                              # and while the panel is shown
        assert item[0]["now"] == "Stages: 0"
        for op in ("median", "otsu"):
            win._test_model.add_stage(op, 0.5, 0.5)
        win._refresh_stage_list(); _pump(app, 0.5)
        assert win._stage_list.count() == 2 and read() == "Stages: 2"
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# a second image window: its old strip widget is gone at once (left to deleteLater it crashed the next run)
# --------------------------------------------------------------------------- #
def test_new_image_window_leaves_no_old_strip_behind_and_a_run_in_the_same_call_is_safe(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        sub = win._new_graphics_window()                                    # no event loop turn after this
        left = [w for w in QtWidgets.QApplication.allWidgets() if w.objectName() == "view_tools"]
        assert left == [], left                                             # the strip the window was built with
        view = sub.widget()
        assert view._tools.objectName() == "flow_strip" and len(view._tools.items()) == 5
        assert [b.parentWidget() is view._tools for b in view._tools.items()] == [True] * 5
        prog = win._program                                                 # ... and a program applied in the same call
        prog["edit"].setPlainText("gaussian 0.4 0.5\nsobel_mag 0.5 0.5\notsu")
        prog["apply"]()
        assert [s[0] for s in win._test_model.stages] == ["gaussian", "sobel_mag", "otsu"]
        sub3 = win._new_graphics_window()
        win._do_run_all(); _pump(app, 0.5)
        assert sub3.widget()._tools.objectName() == "flow_strip"
        assert [w for w in QtWidgets.QApplication.allWidgets() if w.objectName() == "view_tools"] == []
        assert len([r for r in studio_panels.panel_ledger(win) if r["kind"] == "image"]) == 3
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# D58 — Esc in a separate panel window: first the text of its search box, then the window
# D134 — tabs: right-click = that panel's menu, never closable, vertical ones turned, one panel = no tab row
# --------------------------------------------------------------------------- #
def test_floating_panel_esc_clears_search_first(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtWidgets
    from PySide6.QtTest import QTest
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        dock = win._docks["operators"]
        studio_panels.toggle_float(win, "operators", True); _pump(app, 0.3)
        assert dock.isFloating() and dock.isVisible()
        boxes = [b for b in dock.findChildren(QtWidgets.QLineEdit) if b.isVisible() and not b.isReadOnly()
                 and not isinstance(b.parentWidget(), (QtWidgets.QAbstractSpinBox, QtWidgets.QComboBox))]
        assert len(boxes) >= 1
        box = boxes[0]
        box.setFocus(); box.setText("gauss"); _pump(app, 0.4)               # the search of Operators, with text
        assert dock.focusWidget() is box
        QTest.keyClick(box, QtCore.Qt.Key_Escape); _pump(app, 0.2)          # through the real key path
        assert box.text() == "" and dock.isVisible() and dock.isFloating()  # 1st Esc: the text only
        assert not win._layout_state.focus_image                            # the window's own Esc did not fire
        QTest.keyClick(box, QtCore.Qt.Key_Escape); _pump(app, 0.2)
        assert dock.isHidden()                                              # 2nd Esc: the window
        dock.show(); _pump(app, 0.2)                                        # an empty box: one Esc is enough
        assert dock.isFloating() and box.text() == ""
        QTest.keyClick(box, QtCore.Qt.Key_Escape); _pump(app, 0.2)
        assert dock.isHidden()
        studio_panels.toggle_float(win, "operators", False); _pump(app, 0.3)   # docked: Esc is not the panel's
        box.setFocus(); box.setText("otsu"); _pump(app, 0.4)
        QTest.keyClick(box, QtCore.Qt.Key_Escape); _pump(app, 0.2)
        assert dock.isVisible() and box.text() == "otsu"
    finally:
        _close(app, win)


def test_tabs_context_menu_is_panel_menu_and_not_closable(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtGui, QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.2)
        checked = turned = 0
        for make in (_right_column_tabs, _bottom_tabs):
            bar = make(app, win)
            row = _tab_row(win, bar)
            assert not bar.tabsClosable() and len(row.tabs) >= 3
            assert not bar.findChildren(QtWidgets.QAbstractButton, "qt_tabbar_closebutton")   # no x on a tab
            for i, tab in enumerate(row.tabs):
                if tab.vertical:                                            # turned 90 degrees: taller than wide
                    assert tab.sizeHint().height() > tab.sizeHint().width(), tab.label
                    turned += 1
                key = row.key_at(i)
                ev = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, QtCore.QPoint(2, 2),
                                             tab.mapToGlobal(QtCore.QPoint(2, 2)))
                QtCore.QCoreApplication.sendEvent(tab, ev); _pump(app, 0.03)
                menu = win._panels["open_menu"]
                assert key is not None and menu is win._panels["titles"][key].b_menu.menu(), key
                assert win._panels["float_actions"][key] in menu.actions(), key
                menu.close()
                checked += 1
        assert checked >= 6 and turned >= 3
        keys = ("variables", "compare", "ab")                               # one panel left: no tab row at all
        for k in keys[1:]:
            win._docks[k].hide()
        _pump(app, 0.4)
        assert win._docks["variables"].isVisible()
        assert _shown_tab_bars(win) == []
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# D99 — the corner says how a job really ended; D130 — the shapes of states and of the title band are drawn
# --------------------------------------------------------------------------- #
def _wait_for(app, predicate, sec=8.0):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return bool(predicate())


def _px(widget, x, y):
    return widget.grab().toImage().pixelColor(x, y).name()


def test_brand_end_states_done_stopped_failed(tmp_path, monkeypatch):
    import threading
    import numpy as np
    from PySide6 import QtWidgets
    assert [studio_panels.end_state(v) for v in (True, False, "done", "stopped", "failed", "nonsense", None, 1)] == [
        "done", "failed", "done", "stopped", "failed", "done", "failed", "done"]
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
    app = _app()
    studio_theme.set_current(studio_theme.DEFAULT_THEME, studio_theme.DEFAULT_DENSITY)
    p = studio_theme.PALETTES[studio_theme.current_name()]
    # 1. the part alone: a mark and a word for each end, the cross in the error colour, no amber ground
    host = QtWidgets.QWidget(); host.resize(400, 60)
    b = studio_panels.make_brand_status(host, "Fullseye Studio")
    b.show_after_ms = 0
    host.show(); _pump(app, 0.05)
    seen = {}
    for how, word, mark in (("done", "Done", "mark_done"), ("stopped", "Stopped", "mark_done"),
                            ("failed", "Failed", "mark_fail")):
        tok = b.begin("job"); _pump(app, 0.03)
        b.end(tok, how); _pump(app, 0.05)
        assert b.current() == (how, word), how
        img = b.grab().toImage()
        assert (b.shown_mark, b.shown_text) == (mark, word), how           # a drawn mark + the word, no character
        seen[how] = {img.pixelColor(x, y).name() for x in range(img.width()) for y in range(img.height())}
        b.flash_timer.stop(); b._flash_over()
    assert p["warn_bg"] not in seen["failed"] and p["warn"] not in seen["failed"]   # never amber (D99)
    assert p["err"] in seen["failed"] and p["err"] not in seen["done"] and p["err"] not in seen["stopped"]
    tok = b.begin("quick"); b.end(tok, "stopped"); _pump(app, 0.05)        # a stop is always said, however short
    b2 = studio_panels.make_brand_status(host, "Fullseye Studio")           # (the default 300 ms rule)
    tok = b2.begin("quick"); b2.end(tok, "stopped"); _pump(app, 0.05)
    assert b2.current() == ("stopped", "Stopped")
    tok = b2.begin("quick"); b2.end(tok, "done"); _pump(app, 0.05)
    b2.flash_timer.stop(); b2._flash_over()
    assert b2.current()[0] == "idle"                                        # a short success is not flashed
    # follow_progress: the outcome is asked when the bar hides; no answer / a broken one = done
    bar = QtWidgets.QProgressBar(host); bar.hide()
    lab = QtWidgets.QLabel("Run in progress 2/3 stages: otsu", host)
    box = {"how": "stopped"}
    keep = studio_panels.follow_progress(b, bar, lab, outcome=lambda: box["how"])
    for how, word in (("stopped", "Stopped"), ("failed", "Failed"), ("done", "Done")):
        box["how"] = how
        bar.show(); _pump(app, 0.05)
        assert b.current()[0] == "busy"
        bar.hide(); _pump(app, 0.05)
        assert b.current() == (how, word), how                              # the word of the end, not "in progress"
        b.flash_timer.stop(); b._flash_over()
    box["how"] = None
    bar.show(); _pump(app, 0.05); bar.hide(); _pump(app, 0.05)
    assert b.current()[0] == "failed"                                       # None is falsy: not a success
    b.flash_timer.stop(); b._flash_over()
    del keep
    host.close()
    # 2. the real window: stop a run, let one fail, let one finish
    import studio
    monkeypatch.setattr(studio, "ERROR_HOOK", lambda *_a: None)
    model = studio.PipelineModel(studio.demo_image(32))
    model.stages = [["gaussian", 0.2 + i * 0.1, 0.5] for i in range(3)]
    win, _m = studio.build_window(model)
    win.resize(1280, 673); win.show(); _pump(app, 0.3)
    try:
        brand = win._brand
        brand.show_after_ms = 0
        gate = {"entered": threading.Event(), "release": threading.Event(), "mode": "slow", "calls": 0}

        def run_pipeline(value, stages, **_kw):
            gate["calls"] += 1
            if gate["mode"] == "slow" and gate["calls"] == 1:
                gate["entered"].set()
                assert gate["release"].wait(8)
            if gate["mode"] == "fail":
                raise ValueError("boom")
            return np.asarray(value)

        monkeypatch.setattr(studio.api, "run_pipeline", run_pipeline)
        win._start_run_async()
        assert _wait_for(app, gate["entered"].is_set)
        assert brand.current()[0] == "busy"
        win._run_ui["stop"].click(); gate["release"].set()
        assert _wait_for(app, lambda: not win._run_controller.running)
        _pump(app, 0.1)
        assert brand.current() == ("stopped", "Stopped"), brand.current()   # not a square that says "done"
        brand.grab()
        assert (brand.shown_mark, brand.shown_text) == ("mark_done", "Stopped")
        brand.flash_timer.stop(); brand._flash_over()
        gate.update(mode="fail", calls=0)
        win._start_run_async()
        assert _wait_for(app, lambda: not win._run_controller.running)
        _pump(app, 0.1)
        assert brand.current() == ("failed", "Failed"), brand.current()
        brand.grab()
        assert brand.shown_mark == "mark_fail"
        brand.flash_timer.stop(); brand._flash_over()
        gate.update(mode="ok", calls=0)
        win._start_run_async()
        assert _wait_for(app, lambda: not win._run_controller.running)
        _pump(app, 0.1)
        assert brand.current() == ("done", "Done"), brand.current()
        brand.flash_timer.stop(); brand._flash_over()
        win._apply_language("ja"); _pump(app, 0.3)                          # the word follows the language
        try:
            gate.update(mode="slow", calls=0)
            gate["entered"].clear(); gate["release"].clear()
            win._start_run_async()
            assert _wait_for(app, gate["entered"].is_set)
            win._run_ui["stop"].click(); gate["release"].set()
            assert _wait_for(app, lambda: not win._run_controller.running)
            _pump(app, 0.1)
            assert brand.current() == ("stopped", "止めました"), brand.current()
        finally:
            win._apply_language("en"); _pump(app, 0.2)
    finally:
        _close(app, win)


def _lend_windows_fonts():
    """The offscreen platform starts without the Windows fonts: lend it the UI and symbol faces (application
    fonts, nothing is installed). Returns the families now known, or skips where the files are not there."""
    import os
    from PySide6 import QtGui
    folder = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    files = ("segoeui.ttf", "seguisym.ttf", "YuGothR.ttc", "YuGothM.ttc", "meiryo.ttc", "msyh.ttc", "msjh.ttc",
             "malgun.ttf", "Nirmala.ttc")
    have = [f for f in files if os.path.isfile(os.path.join(folder, f))]
    if "segoeui.ttf" not in have or "seguisym.ttf" not in have:
        pytest.skip("the Windows UI faces (segoeui.ttf / seguisym.ttf) are not on this machine: the glyph "
                    "coverage of the UI font stack cannot be measured here")
    for f in have:
        QtGui.QFontDatabase.addApplicationFont(os.path.join(folder, f))
    return set(QtGui.QFontDatabase.families())


def _symbols(text):
    """The characters of ``text`` that are shapes, arrows or signs (not letters of any script, not CJK
    punctuation): the ones a UI face may lack."""
    out = set()
    for ch in text or "":
        o = ord(ch)
        if 0x2190 <= o <= 0x2BFF or 0x2000 <= o <= 0x206F and ch in "\u2022\u2026":
            out.add(ch)
    return out


def test_state_glyphs_have_a_font_or_are_drawn(tmp_path, monkeypatch):
    from PySide6 import QtGui, QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        # 1. buttons and state marks are pictures: no character to be missing
        band_buttons = [(key, b) for key, bar in st["titles"].items() for b in bar.buttons()]
        assert len(band_buttons) == 7 * 3 - 1                               # float, x, menu; the code has no x
        for key, b in band_buttons:
            assert b.text() == "" and not b.icon().isNull(), (key, b.objectName(), b.text())
        for name in ("menu", "mark_run", "mark_done", "mark_fail", "close", "float", "dock"):
            img = studio_panels._glyph(name, "#ffffff", 16).toImage()
            inked = sum(1 for x in range(img.width()) for y in range(img.height()) if img.pixelColor(x, y).alpha() > 60)
            assert inked >= 40, (name, inked)                               # something is drawn
        shapes = {n: studio_panels._glyph(n, "#ffffff", 16).toImage() for n in ("mark_run", "mark_done", "mark_fail")}
        assert shapes["mark_run"] != shapes["mark_done"] != shapes["mark_fail"] != shapes["mark_run"]
        assert set(studio_panels.BRAND_MARKS) == {"busy", "done", "stopped", "failed"}
        marks = [it for bar in st["titles"].values() for it in bar.status if it["mark"] is not None]
        assert len(marks) >= 1                                              # the error count of Pipeline
        for it in marks:
            assert not it["mark"].pixmap().isNull() and not _symbols(it["text"]() or "")
        win._state.setdefault("errors", []).append("x"); _pump(app, 0.4)    # an error: mark and words appear together
        win._docks["pipeline"].show(); _pump(app, 0.5)
        err = [it for it in st["titles"]["pipeline"].status if it["id"] == "errors"][0]
        assert err["now"] == "Errors: 1" and err["label"].isVisible() == err["mark"].isVisible()
        win._state["errors"].clear(); _pump(app, 0.4)
        # 2. symbols that stay inside sentences: some face of the UI stack has each of them
        known = _lend_windows_fonts()
        checked = 0
        for lang in ("en", "ja"):
            win._apply_language(lang); _pump(app, 0.4)
            for d in win._docks.values():
                d.show()
            _pump(app, 0.4)
            used = {}
            for w in win.findChildren(QtWidgets.QWidget):
                texts = [w.toolTip()]
                if isinstance(w, (QtWidgets.QLabel, QtWidgets.QAbstractButton)):
                    texts.append(w.text())
                for t in texts:
                    for ch in _symbols(t):
                        used.setdefault(ch, t[:40])
            for a in win.findChildren(QtGui.QAction):
                for ch in _symbols(a.text()) | _symbols(a.toolTip()):
                    used.setdefault(ch, a.text()[:40])
            for text in studio_panels.STRINGS:
                for ch in _symbols(win._panels["tr"](text)):
                    used.setdefault(ch, text[:40])
            assert len(used) >= 5, used
            fams = [f for f in studio_theme.ui_families(lang) if f in known]
            assert "Segoe UI" in fams and "Segoe UI Symbol" in fams
            raws = [QtGui.QRawFont.fromFont(QtGui.QFont(f)) for f in fams]  # each face by itself, no system fallback
            assert len(raws) >= 2
            assert [r.familyName() for r in raws] == fams
            missing = {ch: where for ch, where in used.items() if not any(r.supportsCharacter(ord(ch)) for r in raws)}
            assert not missing, (lang, {"U+%04X" % ord(c): w for c, w in missing.items()})
            checked += len(used)
        assert checked >= 10
        for lang in studio_theme.UI_FONTS:                                  # the symbol face is in every stack
            assert studio_theme.ui_families(lang)[-1] == "Segoe UI Symbol"
            assert '"Segoe UI Symbol"' in studio_theme.font_stack(lang)
    finally:
        win._apply_language("en")
        _close(app, win)


# --------------------------------------------------------------------------- #
# the look, 1.2-B: D17 (image area), D120 (trees / tables / headers), D121 (prose), D122 (titles not amber)
# --------------------------------------------------------------------------- #
def test_prose_labels_not_monospace(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        code = set(studio_theme.CODE_FONTS)
        ui = studio_theme.UI_FONTS["en"][0]
        hints = [lab for lab in win.findChildren(QtWidgets.QLabel) if lab.property("hint")]
        figures = [lab for lab in hints if lab.property("figures")]
        prose = [lab for lab in win.findChildren(QtWidgets.QLabel) if lab.property("prose")]
        assert len(hints) >= 9
        assert len(figures) == 4                                            # pixel read-out, image info, 2 signatures
        assert win._img_info in figures
        assert {"select an operator to see its signature", "select a stage to tune its knobs"} <= {
            lab.text() for lab in figures}
        assert len(prose) >= 5
        assert {id(x) for x in prose} == {id(x) for x in hints} - {id(x) for x in figures}
        for lab in prose:                                                   # a sentence: the UI face, never fixed pitch
            lab.ensurePolished()
            fams = lab.font().families()
            assert fams[0] == ui and not (set(fams) & code), (lab.text()[:30], fams)
        for lab in figures:                                                 # figures and signatures: the code face
            lab.ensurePolished()
            assert lab.font().families()[0] == studio_theme.CODE_FONTS[0], lab.text()[:30]
        texts = {lab.text() for lab in prose}
        assert "ready" in texts and any(t.startswith("current: ") for t in texts)
        # a window built later: its sentences are prose too (the same sweep that gives code its face)
        dlg = QtWidgets.QDialog(win)
        late = QtWidgets.QLabel("loading the demo clip", dlg); late.setProperty("hint", True)
        fig = QtWidgets.QLabel("12 x 34", dlg); fig.setProperty("hint", True); fig.setProperty("figures", True)
        dlg.show(); _pump(app, 0.3)
        try:
            late.ensurePolished(); fig.ensurePolished()
            assert late.property("prose") and late.font().families()[0] == ui
            assert not fig.property("prose") and fig.font().families()[0] == studio_theme.CODE_FONTS[0]
            assert studio_theme.mark_prose(dlg) == [late]
        finally:
            dlg.close()
    finally:
        _close(app, win)


def test_group_title_and_brand_not_warn_colour(tmp_path, monkeypatch):
    from PySide6 import QtGui, QtWidgets
    for theme in studio_theme.THEMES:
        p = studio_theme.PALETTES[theme]
        rules = _qss_rules(studio_theme.build_qss(theme))
        assert rules["QGroupBox::title"]["color"] == p["title"] != p["warn"]
        assert p["brand"] != p["warn"] and p["title"] != p["warn"]
        assert p["warn"] not in rules["QDockWidget::title"].values()
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        p = studio_theme.PALETTES[studio_theme.current_name()]
        for d in win._docks.values():
            d.show()
        _pump(app, 0.4)
        groups = [g for d in win._docks.values() for g in d.findChildren(QtWidgets.QGroupBox) if g.title() and g.isVisible()]
        assert len(groups) >= 3
        amber = QtGui.QColor(p["warn"])
        painted = 0
        for g in groups:                                                    # the painted title: no amber pixel
            img = g.grab(g.rect().adjusted(0, 0, 0, -(g.height() - 16))).toImage()
            near = sum(1 for x in range(img.width()) for y in range(img.height())
                       if abs(img.pixelColor(x, y).red() - amber.red()) < 24
                       and abs(img.pixelColor(x, y).green() - amber.green()) < 24
                       and abs(img.pixelColor(x, y).blue() - amber.blue()) < 24)
            assert near == 0, (g.title(), near)
            painted += 1
        assert painted >= 3
        img = win._brand.grab().toImage()                                   # the product name, idle
        cols = {img.pixelColor(x, y).name() for x in range(40, img.width()) for y in range(img.height())}
        assert p["brand"] in cols and p["warn"] not in cols
    finally:
        _close(app, win)


def test_trees_tables_and_headers_select_in_the_accent(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtGui, QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        p = studio_theme.PALETTES[studio_theme.current_name()]
        rules = _qss_rules(studio_theme.build_qss(studio_theme.current_name()))
        for sel in ("QTreeView::item:selected", "QTableView::item:selected"):
            assert rules[sel]["background"] == p["accent"] and rules[sel]["color"] == p["accent_ink"], sel
        assert rules["QHeaderView::section"]["background"] == p["chrome"]
        dlg = QtWidgets.QDialog(win); dlg.resize(520, 300)                  # a window made later, under the same sheet
        lay = QtWidgets.QHBoxLayout(dlg)
        model = QtGui.QStandardItemModel(3, 2, dlg)
        model.setHorizontalHeaderLabels(["name", "value"])
        for r in range(3):
            for c in range(2):
                model.setItem(r, c, QtGui.QStandardItem("item %d %d" % (r, c)))
        tree = QtWidgets.QTreeView(); tree.setModel(model); tree.setRootIsDecorated(False)
        table = QtWidgets.QTableView(); table.setModel(model)
        widget = QtWidgets.QTreeWidget(); widget.setHeaderLabels(["a", "b"])
        for r in range(3):
            QtWidgets.QTreeWidgetItem(widget, ["row %d" % r, "x"])
        for v in (tree, table, widget):
            lay.addWidget(v)
        dlg.show(); _pump(app, 0.3)
        try:
            tree.setCurrentIndex(model.index(1, 0)); table.setCurrentIndex(model.index(1, 1))
            widget.setCurrentItem(widget.topLevelItem(1)); _pump(app, 0.2)
            seen = 0
            accent, qt_blue = QtGui.QColor(p["accent"]), QtGui.QColor("#308cc6")

            def near(c, ref, tol=14):                                       # the style lays a faint sheen over a selected row
                return max(abs(c.red() - ref.red()), abs(c.green() - ref.green()), abs(c.blue() - ref.blue())) <= tol

            assert not near(accent, qt_blue, 30)                            # the two can be told apart at all
            for view, index in ((tree, model.index(1, 0)), (table, model.index(1, 1)),
                                (widget, widget.indexFromItem(widget.topLevelItem(1)))):
                r = view.visualRect(index)
                assert r.height() >= 20, (type(view).__name__, r.height())  # a row is never under 20 px
                img = view.viewport().grab().toImage()
                got = img.pixelColor(r.right() - 6, r.center().y())
                assert near(got, accent) and not near(got, qt_blue), (type(view).__name__, got.name())
                other = view.visualRect(index.sibling(0, index.column()))
                assert not near(img.pixelColor(other.right() - 6, other.center().y()), accent)
                head = view.header() if hasattr(view, "header") else view.horizontalHeader()
                himg = head.grab().toImage()
                assert himg.pixelColor(head.width() // 4, 3).name() == p["chrome"], type(view).__name__
                seen += 1
            assert seen == 3
        finally:
            dlg.close()
    finally:
        _close(app, win)


def test_image_area_ground_and_title_take_role_colours(tmp_path, monkeypatch):
    from PySide6 import QtGui
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        p = studio_theme.PALETTES[studio_theme.current_name()]
        mdi = win._mdi
        assert mdi.background().color().name() == p["surround"]             # not Qt's grey
        sub2 = win._new_graphics_window(); _pump(app, 0.4)
        subs = mdi.subWindowList()
        assert len(subs) == 2
        assert sub2 in subs
        assert studio_panels.theme_mdi(win) == 2
        for sub in subs:
            pal = sub.palette()
            assert pal.color(QtGui.QPalette.Active, QtGui.QPalette.Highlight).name() == p["rail"], sub.windowTitle()
            assert pal.color(QtGui.QPalette.Active, QtGui.QPalette.HighlightedText).name() == p["text"]
            assert pal.color(QtGui.QPalette.Inactive, QtGui.QPalette.Window).name() == p["bg1"]   # behind: the sheet's
        for sub in subs:
            sub.showNormal()
        subs[0].setGeometry(10, 10, 360, 240); subs[1].setGeometry(420, 30, 360, 240); _pump(app, 0.4)
        mdi.setActiveSubWindow(subs[1]); _pump(app, 0.3)
        img = mdi.grab().toImage()
        assert img.pixelColor(400, 200).name() == p["surround"]             # the ground between the two windows
        blue = QtGui.QColor("#308cc6")                                      # Fusion's own active title
        for sub in subs:                                                    # no light-blue title band
            g = sub.geometry()
            band = [img.pixelColor(x, g.top() + 10) for x in range(g.left() + 40, g.right() - 80, 7)]
            assert len(band) >= 20
            assert not [c for c in band if abs(c.red() - blue.red()) < 40 and abs(c.green() - blue.green()) < 40
                        and abs(c.blue() - blue.blue()) < 40], sub.windowTitle()
            assert not [c for c in band if c.blue() > 180 and c.blue() - c.red() > 60], sub.windowTitle()
        win._apply_theme(theme="panel", save=False); _pump(app, 0.4)        # the other scheme: both follow
        try:
            q = studio_theme.PALETTES["panel"]
            assert mdi.background().color().name() == q["surround"]
            assert subs[0].palette().color(QtGui.QPalette.Active, QtGui.QPalette.Highlight).name() == q["rail"]
        finally:
            win._apply_theme(theme=studio_theme.DEFAULT_THEME, save=False); _pump(app, 0.3)
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# D128 — the work-mode switch: " *" once the arrangement is no longer the mode's; chosen again, it returns
# --------------------------------------------------------------------------- #
def test_work_mode_marked_modified_after_rearrange(tmp_path, monkeypatch):
    from PySide6 import QtCore
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        sw = win._mode_switch
        modes = win._work_mode_actions
        st = win._panels
        assert len(modes) == 4
        assert sw.text() == modes["code"].text() and not studio_panels.mode_differs(win)   # first run: as the mode asks
        modes["build"].trigger(); _pump(app, 0.3)
        name = modes["build"].text()
        assert sw.text() == name and sw.isChecked() and not st["mode_modified"]
        ops = win._docks["operators"]
        area = win.dockWidgetArea(ops)
        assert ops.isVisible() and area == QtCore.Qt.RightDockWidgetArea
        # 1. a panel moved to another side: the mode stays pressed, its name carries the mark (G01(h))
        win.addDockWidget(QtCore.Qt.LeftDockWidgetArea, ops); _pump(app, 0.3)
        assert sw.text() == name + " *" and sw.isChecked() and modes["build"].isChecked()
        assert studio_panels.S_MODE_CHANGED in sw.toolTip()
        assert [a.text() for a in sw.menu().actions()] == [a.text() for a in modes.values()]   # the entries are not marked
        modes["build"].trigger(); _pump(app, 0.3)                           # chosen again: back to its arrangement
        assert sw.text() == name and win.dockWidgetArea(ops) == area and ops.isVisible()
        assert studio_panels.S_MODE_CHANGED not in sw.toolTip()
        # 2. a panel put away against the mode
        ops.hide(); _pump(app, 0.3)
        assert sw.text() == name + " *" and modes["build"].isChecked()
        modes["build"].trigger(); _pump(app, 0.3)
        assert sw.text() == name and ops.isVisible()
        assert "build" not in win._layout_state.overrides                   # what was hidden against it is forgotten
        # 3. a panel brought in that the mode does not show, and a panel made a separate window
        win._docks["variables"].show(); _pump(app, 0.3)
        assert sw.text() == name + " *"
        modes["build"].trigger(); _pump(app, 0.3)
        assert sw.text() == name and win._docks["variables"].isHidden()
        studio_panels.toggle_float(win, "pipeline", True); _pump(app, 0.3)
        assert sw.text() == name + " *"
        win._apply_language("ja"); _pump(app, 0.4)                          # the mark survives the language pass
        try:
            assert sw.text() == modes["build"].text() + " *" and sw.text() != name + " *"
        finally:
            win._apply_language("en"); _pump(app, 0.3)
        modes["build"].trigger(); _pump(app, 0.3)
        assert sw.text() == name and not win._docks["pipeline"].isFloating()
        # 4. another mode: its own arrangement, no mark; resizing a panel is not a rearrangement
        ops.hide(); _pump(app, 0.3)
        assert sw.text() == name + " *"
        modes["code"].trigger(); _pump(app, 0.3)
        assert sw.text() == modes["code"].text() and not st["mode_modified"]
        win.resizeDocks([win._docks["program"]], [200], QtCore.Qt.Vertical); _pump(app, 0.3)
        assert sw.text() == modes["code"].text()
        modes["build"].trigger(); _pump(app, 0.3)                           # what the user hid in "build" is remembered:
        assert ops.isHidden() and sw.text() == name + " *"                  # so the mark is there, honestly
        modes["build"].trigger(); _pump(app, 0.3)
        assert ops.isVisible() and sw.text() == name
        win._toggle_focus_image(True); _pump(app, 0.3)                      # image focus is its own state, not a mark
        assert not studio_panels.mode_differs(win)
        win._toggle_focus_image(False); _pump(app, 0.3)
        assert sw.text() == name
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# D24 — the tool strip of every image window: 24 px buttons, zoom in / zoom out / fit / 1:1, then save
# --------------------------------------------------------------------------- #
def test_image_strips_are_icon_button_size_and_in_one_order(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        side = studio_theme.density()["icon_btn"]
        assert side == 24 and studio_panels.IMAGE_ZOOM_ORDER == ("zoom_in", "zoom_out", "fit", "actual_size")
        win._new_graphics_window(); _pump(app, 0.3)
        win._new_graphics_window(); _pump(app, 0.3)
        rows = [r for r in studio_panels.panel_ledger(win) if r["kind"] == "image"]
        assert len(rows) == 3                                               # the main image and two more
        want = (("open_image", "demo"), ("zoom_in", "zoom_out", "fit", "actual_size"), ("save_result", "save"))
        counted, ends = 0, {}
        for r in rows:
            strip = r["strip"]
            names = (win._panel_buttons["graphics_1"] if r["key"] == "graphics_1" else r["shape"].tool_buttons)
            by_button = {b: n for n, b in names.items()}
            items = strip.items()
            assert len(items) >= 5
            small = [(by_button.get(b), b.width(), b.height()) for b in items if b.height() != side or b.width() < side]
            assert small == [], (r["key"], small)                          # 24 px, never smaller
            order = [by_button[b] for b in items if by_button.get(b) in studio_panels.IMAGE_ZOOM_ORDER]
            assert order == list(studio_panels.IMAGE_ZOOM_ORDER), (r["key"], order)
            zoom = [g for g in strip.groups if by_button.get(g[0]) == "zoom_in"]
            assert len(zoom) == 1 and len(zoom[0]) == 4, r["key"]           # one group, in that order
            # P04-6: [open / make] | [view] | [save] in EVERY image window, the main one too (the user-eye
            # check: Graphics 1 had save in its first group, so two windows side by side had it at opposite ends)
            kinds = []
            for g in strip.groups:
                names_g = [by_button.get(b) for b in g]
                kind = [i for i, grp in enumerate(want) if names_g[0] in grp]
                assert len(kind) == 1 and all(n in want[kind[0]] for n in names_g), (r["key"], names_g)
                kinds.append(kind[0])
            assert kinds == sorted(set(kinds)) and kinds[-2:] == [1, 2], (r["key"], kinds)
            ends[r["key"]] = kinds
            counted += len(items)
        assert counted >= 17
        assert ends["graphics_1"] == [0, 1, 2] and len(ends) == 3           # the main one opens, views, saves
        assert {tuple(k[-2:]) for k in ends.values()} == {(1, 2)}           # save at the same end everywhere
        assert studio_panels.IMAGE_GROUPS == want                           # one table for every window
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# D03 (the picture, not only the sheet) — a disabled icon button draws its icon in the "off" colour
# --------------------------------------------------------------------------- #
def _opaque_colours(pm):
    from PySide6 import QtGui
    im = pm.toImage().convertToFormat(QtGui.QImage.Format_ARGB32)
    out = set()
    for y in range(im.height()):
        for x in range(im.width()):
            c = im.pixelColor(x, y)
            if c.alpha() == 255:
                out.add(c.name())
    return out


def test_disabled_icon_buttons_draw_the_icon_in_the_off_colour(tmp_path, monkeypatch):
    from PySide6 import QtGui, QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win._docks["pipeline"].show(); _pump(app, 0.3)
        off = studio_theme.PALETTES[studio_theme.current_name()]["off"].lower()
        hand = [b for b in win.findChildren(QtWidgets.QAbstractButton)
                if b.property("iconOnly") and not b.icon().isNull()]
        hand += [b for bar in win._panels["titles"].values() for b in bar.buttons()]
        assert len(hand) >= 30
        counted, wrong = 0, []
        for b in hand:
            ic = b.icon()
            side = max(16, b.iconSize().width())
            normal = _opaque_colours(ic.pixmap(side, side, QtGui.QIcon.Normal, QtGui.QIcon.Off))
            dimmed = _opaque_colours(ic.pixmap(side, side, QtGui.QIcon.Disabled, QtGui.QIcon.Off))
            if not normal:
                continue                                                    # nothing opaque to compare
            if dimmed != {off} or normal == {off}:
                wrong.append((b.objectName() or b.toolTip().split("\n")[0][:30], sorted(normal)[:2], sorted(dimmed)[:2]))
            counted += 1
        assert counted >= 30
        assert wrong == [], wrong[:8]
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# D104 (a separate window too) — the code made a separate window is not put away by Esc or by its close
# --------------------------------------------------------------------------- #
def test_principal_in_a_separate_window_survives_esc_and_close(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtTest import QTest
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        principals = [k for k in studio_panels.PRINCIPAL if k in win._docks]
        assert principals == ["program"]
        checked = 0
        for key in principals:
            dock = win._docks[key]
            editor = dock.widget().findChild(QtWidgets.QPlainTextEdit)
            assert editor is not None
            assert not (dock.features() & QtWidgets.QDockWidget.DockWidgetClosable), key   # Qt refuses its close
            # 1. made a separate window through its own menu (the last entry of the band's menu)
            bar = st["titles"][key]
            bar.fill_menu()
            st["float_actions"][key].trigger(); _pump(app, 0.4)
            assert dock.isFloating() and dock.isVisible(), key
            ways = {
                "Esc in the editor": lambda: QTest.keyClick(editor, QtCore.Qt.Key_Escape),
                "Esc on the window": lambda: QtCore.QCoreApplication.sendEvent(
                    dock, QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape, QtCore.Qt.NoModifier)),
                "its close (Alt+F4)": dock.close,
            }
            for name, press in ways.items():
                editor.setFocus(); _pump(app, 0.1)
                press(); _pump(app, 0.3)
                assert dock.isVisible() and not dock.isHidden() and dock.isFloating(), (key, name)
                assert st["buttons"][key].isChecked(), (key, name)          # the bar still says it is shown
                checked += 1
            assert not win._layout_state.focus_image                        # the window's own Esc did not fire either
            studio_panels.toggle_float(win, key, False); _pump(app, 0.3)
            for name, press in ways.items():                                # docked: the same, nothing is put away
                editor.setFocus(); _pump(app, 0.05)
                if name != "Esc in the editor":
                    press(); _pump(app, 0.2)
                assert dock.isVisible(), (key, name)
        assert checked >= 3
        # the others are still put away by Esc in a separate window (D58), so the rule is about principals only
        ops = win._docks["operators"]
        studio_panels.toggle_float(win, "operators", True); _pump(app, 0.3)
        QtCore.QCoreApplication.sendEvent(
            ops, QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape, QtCore.Qt.NoModifier)); _pump(app, 0.2)
        assert ops.isHidden()
        assert ops.features() & QtWidgets.QDockWidget.DockWidgetClosable
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# A2 A3 — Qt's own tab bar never shows through the rows that are drawn over it (the user-eye check:
# a ghost "A/B 比較" right of a short wrapped row, Qt's scroll boxes, letters behind a disabled arrow)
# --------------------------------------------------------------------------- #
_LOUD = ("QTabBar::tab { color:#ff00ff; background:#00ff00; border:1px solid #00ff00; } "
         "QTabBar QToolButton { background:#00ff00; color:#ff00ff; border:1px solid #00ff00; }")


def _loud_pixels(img, rect=None):
    """Pixels of Qt's own bar painted in the loud colours (green ground / magenta letters)."""
    from PySide6 import QtCore
    r = rect if rect is not None else QtCore.QRect(0, 0, img.width(), img.height())
    n = 0
    for y in range(max(0, r.top()), min(img.height(), r.bottom() + 1)):
        for x in range(max(0, r.left()), min(img.width(), r.right() + 1)):
            c = img.pixelColor(x, y)
            if (c.green() > 150 and c.red() < 110 and c.blue() < 110) or (
                    c.red() > 150 and c.blue() > 150 and c.green() < 110):
                n += 1
    return n


def test_qt_tab_bar_never_shows_through_the_drawn_rows(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.2)
        looked = 0
        for make, vertical in ((_right_column_tabs, False), (_bottom_tabs, True)):
            bar = make(app, win)
            row = _tab_row(win, bar)
            s = row.strip
            along = max((t.sizeHint().height() if vertical else t.sizeHint().width()) for t in row.tabs)
            # 1. scrolled: at the start the "back" button is disabled; nothing of Qt's tabs behind it
            studio_panels.set_overflow_mode(win, "scroll"); _pump(app, 0.2)
            (bar.setFixedHeight if vertical else bar.setFixedWidth)(int(1.5 * along)); _pump(app, 0.4)
            assert s.state["scrolling"] and s.b_back.isVisible() and not s.b_back.isEnabled()
            bar.setStyleSheet(row.qss + " " + _LOUD); app.processEvents()
            img = bar.grab().toImage()
            assert _loud_pixels(img, s.b_back.geometry()) == 0, ("behind the disabled back button", vertical)
            assert _loud_pixels(img) == 0, ("scrolled row", vertical)
            looked += 1
            bar.setStyleSheet(row.qss); bar.setMinimumSize(0, 0); bar.setMaximumSize(_MAX, _MAX); _pump(app, 0.3)
            # 2. wrapped onto rows: right of (under) the last tab of a short row is the ground, not a ghost tab
            if not vertical:
                studio_panels.set_overflow_mode(win, "wrap"); _pump(app, 0.2)
                bar.setFixedWidth(int(2.2 * along)); _pump(app, 0.4)
                assert 2 <= s.state["lines"] <= studio_panels.WRAP_MAX_LINES and not s.state["scrolling"]
                ends = {}
                for t in row.tabs:                                          # the right end of every row
                    ends[t.y()] = max(ends.get(t.y(), 0), t.x() + t.width())
                assert len(ends) >= 2 and min(ends.values()) < s.width() - 4    # a row that is shorter than the strip
                bar.setStyleSheet(row.qss + " " + _LOUD); app.processEvents()
                img = bar.grab().toImage()
                from PySide6 import QtCore
                for y, end in ends.items():
                    gap = QtCore.QRect(end + 1, y, s.width() - end - 1, row.t1)
                    assert _loud_pixels(img, gap) == 0, ("right of a short row", y, end)
                assert _loud_pixels(img) == 0
                ground = studio_theme.PALETTES[studio_theme.current_name()]["bg0"]
                y, end = min(ends.items(), key=lambda kv: kv[1])
                assert img.pixelColor(end + 3, y + row.t1 // 2).name() == ground   # the window's ground there
                looked += 1
                bar.setStyleSheet(row.qss); bar.setMinimumSize(0, 0); bar.setMaximumSize(_MAX, _MAX)
                studio_panels.set_overflow_mode(win, "scroll"); _pump(app, 0.3)
        assert looked >= 3
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# A1 (automatic side) — choosing a tab never moves the tab row under the mouse (the user-eye check: with the
# tall Pipeline in front the row was on top; a click on "Variables" let the group shrink, its ratio passed
# 2.2 and the whole row jumped to the left, away from the pointer)
# --------------------------------------------------------------------------- #
def test_choosing_a_tab_keeps_the_side_and_place_of_its_row(tmp_path, monkeypatch):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.2)
        keys = ["pipeline", "variables", "ab", "compare", "display", "operators"]
        studio_panels.set_code_side(win, "left"); _pump(app, 0.2)
        win._docks["pipeline"].widget().setMinimumHeight(560)               # a panel taller than the others
        for k in keys:
            win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, win._docks[k]); win._docks[k].show()
        for k in keys[1:]:
            win.tabifyDockWidget(win._docks[keys[0]], win._docks[k])
        win._docks["pipeline"].raise_(); _pump(app, 0.6)
        rows = [r for r in win._panels["tab_rows"].values() if r.bar.isVisible() and len(r.tabs) == len(keys)]
        assert len(rows) == 1
        row = rows[0]
        start = (row.vertical(), row.bar.pos().toTuple())
        assert win._docks["pipeline"].width() / win._docks["pipeline"].height() < studio_panels.WIDE_ON
        sizes, clicks = set(), 0
        for i in [1, 0, 2, 1, 3, 4, 5, 0]:                                   # every tab, as a user clicks them
            t = row.tabs[i]
            if t not in row.strip.state["shown"]:
                row.strip.ensure_visible(t); _pump(app, 0.1)
            QTest.mouseClick(t, QtCore.Qt.LeftButton); _pump(app, 0.5)
            assert row.bar.currentIndex() == i
            front = win._docks[row.key_at(i)]
            sizes.add((front.width(), front.height()))
            assert (row.vertical(), row.bar.pos().toTuple()) == start, (i, t.label, front.size().toTuple())
            clicks += 1
        assert clicks == 8 and len(sizes) >= 2                               # the group did change its size
        assert any(w / h >= studio_panels.WIDE_ON for w, h in sizes)          # ... past the threshold: still no jump
        # a size the user gives (the window) is decided again: the rule itself still works
        win._docks["variables"].raise_(); _pump(app, 0.3)
        win.resize(1700, 720); _pump(app, 0.6)
        front = win._docks["variables"]
        assert front.width() / front.height() >= studio_panels.WIDE_ON
        assert row.vertical(), (front.size().toTuple(),)
        win.resize(1280, 720); _pump(app, 0.4)
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# A2 — an image window bigger than the image area it sits in (the code widened / heightened to the most):
# its strip scrolls within the part that is SEEN, with both scroll buttons whole (the user-eye check: the
# strip judged "it fits" by the window's own width, so 1:1 was cut at the area's edge, or ▼ was out of sight)
# --------------------------------------------------------------------------- #
def _inside_area(win, w):
    """``w`` lies wholly inside the image area (the MDI viewport, which clips the image windows)."""
    from PySide6 import QtCore
    vp = win._mdi.viewport()
    return vp.rect().contains(QtCore.QRect(w.mapTo(vp, QtCore.QPoint(0, 0)), w.size()))


def test_image_strips_scroll_within_the_seen_part_of_a_squeezed_image_window(tmp_path, monkeypatch):
    from PySide6 import QtCore
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1024, 700); _pump(app, 0.2)
        win._new_graphics_window(); _pump(app, 0.4)                         # a second one: its strip is laid over it
        cases, reached = 0, 0
        for side, orient in (("left", QtCore.Qt.Horizontal), ("bottom", QtCore.Qt.Vertical)):
            studio_panels.set_code_side(win, side); _pump(app, 0.3)
            win.resizeDocks([win._docks["program"]], [2000], orient); _pump(app, 0.8)
            vp = win._mdi.viewport()
            subs = win._mdi.subWindowList()
            assert len(subs) == 2
            for sub in subs:
                win._mdi.setActiveSubWindow(sub); _pump(app, 0.5)
                rows = [r for r in studio_panels.panel_ledger(win) if r["kind"] == "image"
                        and _subwindow_of(r["shape"]) is sub]
                assert len(rows) == 1, sub.windowTitle()
                s = rows[0]["strip"]
                cut = sub.width() > vp.width() if side == "left" else sub.height() > vp.height()
                assert cut, (side, sub.size().toTuple(), vp.size().toTuple())   # the case is really made
                where = (side, rows[0]["key"], s.state["scrolling"], vp.size().toTuple())
                seen = set()
                for _step in range(40):
                    for b in s.state["shown"]:
                        assert _inside_area(win, b), where + (b.toolTip()[:30],)
                        seen.add(b)
                    if not s.state["scrolling"]:
                        break
                    for arrow in (s.b_back, s.b_on):                        # ▲▼ / ◀▶ whole and in sight
                        assert arrow.isVisible() and _inside_area(win, arrow), where
                    if not s.b_on.isEnabled():
                        break
                    s.b_on.click(); _pump(app, 0.02)
                assert seen == set(s.items()) and len(seen) >= 5, where + (len(seen), len(s.items()))
                reached += len(seen)
                cases += 1
        assert cases == 4 and reached >= 20
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# A1 — no drawn tool button of a panel is left out of every strip (the user-eye check: the three buttons of
# "Export & I/O" stayed a row at the bottom right when "Tools and tabs: left" turned everything else)
# --------------------------------------------------------------------------- #
def _drawn(b):
    """A button that shows only a picture (what a strip holds)."""
    from PySide6 import QtCore, QtWidgets
    if b.icon().isNull() or (b.text() or "").replace("&", "").strip():
        return isinstance(b, QtWidgets.QToolButton) and not b.icon().isNull() and \
            b.toolButtonStyle() == QtCore.Qt.ToolButtonIconOnly
    return True


def test_every_drawn_button_of_a_panel_is_in_a_strip_or_says_why_not(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1600, 1000); _pump(app, 0.2)
        win._new_graphics_window(); _pump(app, 0.3)
        _show_all(app, win)
        counted = 0
        for mode in ("top", "left"):
            studio_panels.set_strip_mode(win, mode); _pump(app, 0.3)
            held = set()
            for s in studio_panels.all_strips(win):
                held |= set(s.items()) | {s.b_back, s.b_on}
            in_strips = loose = 0
            for key, dock in win._docks.items():
                dock.raise_(); _pump(app, 0.05)
                band = set(win._panels["titles"][key].buttons())
                for b in dock.findChildren(QtWidgets.QAbstractButton):
                    if b.objectName().startswith("qt_") or b in band or not b.isVisible() or not _drawn(b):
                        continue
                    if b in held:
                        in_strips += 1
                    else:                                                   # only with its reason
                        why = studio_panels.STRIP_EXEMPT.get(key) or b.property("fsLoose")
                        assert why, (mode, key, b.toolTip()[:50])
                        loose += 1
            assert in_strips >= 20 and loose <= 4, (mode, in_strips, loose)   # code 6 + ops 3 + pipe 9 + vars 2
            counted += in_strips + loose
            # the pipeline's file buttons are the third group of its strip: [edit] | [run] | [save / export]
            pipe = [r for r in studio_panels.panel_ledger(win) if r["key"] == "pipeline"][0]["strip"]
            names = {b: n for n, b in win._panel_buttons["pipeline"].items()}
            assert [[names.get(b) for b in g] for g in pipe.groups] == [
                ["remove", "move_up", "move_down"], ["reset", "step", "run_all"],
                ["open_pipeline", "save_pipeline", "export"]], mode
            assert win._panel_strips["pipeline"][2].parentWidget().isHidden()   # the emptied "Export & I/O" box
        assert counted >= 44                                                # (20 in strips + 4 with a reason) x 2
    finally:
        studio_panels.set_strip_mode(win, "auto")
        _close(app, win)


# --------------------------------------------------------------------------- #
# A1 — "Tools and tabs: on top" means on top: every panel's strip stands right under its title band, above
# everything else of the panel (Visual Studio's tool windows; the user-eye check: Operators and A/B had their
# strip at the very bottom, Pipeline under its list, Variables between its list and its details)
# --------------------------------------------------------------------------- #
def test_on_top_every_strip_stands_above_the_rest_of_its_panel(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1600, 1000); _pump(app, 0.2)
        _show_all(app, win)
        checked = 0
        for mode in ("top", "auto"):
            studio_panels.set_strip_mode(win, mode); _pump(app, 0.3)
            for r in _strip_rows(win):
                s = r["strip"]
                if r["kind"] == "image":
                    if s.overlay:
                        continue                                            # laid over its image's corner
                    view = r["shape"].findChild(QtWidgets.QGraphicsView)
                    top = r["shape"]
                    assert s.orientation == "h" or mode == "auto", r["key"]
                    if s.orientation == "h":
                        assert s.mapTo(top, QtCore.QPoint(0, s.height())).y() <= view.mapTo(top, QtCore.QPoint(0, 0)).y()
                        checked += 1
                    continue
                dock = r["shape"]
                dock.raise_(); _pump(app, 0.1)
                if s.orientation != "h":
                    assert mode == "auto", r["key"]                         # "on top" is never a column
                    continue
                root = dock.widget()
                bottom = s.mapTo(root, QtCore.QPoint(0, s.height())).y()
                others = [w for w in root.findChildren(QtWidgets.QWidget)
                          if w.isVisible() and w is not s and not s.isAncestorOf(w) and not w.isAncestorOf(s)
                          and w.width() > 0 and w.height() > 0]
                assert len(others) >= 3, r["key"]
                above = [(w.objectName() or type(w).__name__, w.mapTo(root, QtCore.QPoint(0, 0)).y())
                         for w in others if w.mapTo(root, QtCore.QPoint(0, 0)).y() < bottom]
                assert above == [], (mode, r["key"], bottom, above[:4])
                checked += 1
        assert checked >= 2 * 5 + 1                                         # code ops pipeline vars A/B (x2) + the image
    finally:
        studio_panels.set_strip_mode(win, "auto")
        _close(app, win)


def test_a_tab_group_the_program_builds_takes_the_side_of_its_settled_front(tmp_path, monkeypatch):
    """The hold of the tab sides is the user's (a click / a key in the row), not Qt's: while a group is being
    built (tabified, a panel raised by the program) the side follows the front it settles on - a passing wide
    front must not leave a tall right-hand column with its tabs on the left."""
    from PySide6 import QtCore
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.2)
        studio_panels.set_code_side(win, "left"); _pump(app, 0.3)
        keys = ("operators", "pipeline", "variables", "ab", "display", "compare")
        for k in keys:
            win.addDockWidget(QtCore.Qt.RightDockWidgetArea, win._docks[k]); win._docks[k].show()
        _pump(app, 0.3)
        for k in keys[1:]:
            win.tabifyDockWidget(win._docks[keys[0]], win._docks[k])
        win._docks["pipeline"].raise_(); _pump(app, 0.6)
        rows = [r for r in win._panels["tab_rows"].values() if r.bar.isVisible() and len(r.tabs) == len(keys)]
        assert len(rows) == 1
        front = win._docks["pipeline"]
        assert front.width() / front.height() <= studio_panels.WIDE_OFF, front.size().toTuple()   # tall / square
        assert not rows[0].vertical(), front.size().toTuple()                  # so its tabs are on top
        assert not win._panels.get("tab_hold")                                  # nobody chose a tab yet
    finally:
        _close(app, win)
