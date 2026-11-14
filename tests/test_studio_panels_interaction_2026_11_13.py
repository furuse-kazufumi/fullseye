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
                if r["kind"] == "image":                                    # the main image: the window's menus
                    assert act in menubar, (r["key"], act.text())
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
