"""Studio panel bar, dock <-> separate window, saved panel layout (studio_panels.py; stage 2, 2026-11-13).

The image and the code are the principals; every other panel comes from the panel bar.
Counted here: one bar button per panel (all of them), show / hide / raise, separate window and
back, the arrangement survives a restart, "Reset panel layout" returns to image + code, a broken
settings file still starts, a window saved outside every screen comes back.

Every window here runs under the offscreen platform with its own settings file (tmp_path).
"""
import json
import os
import time

import pytest

import studio_layout
import studio_panels
import studio_theme

#: the docks of this branch (RAIL_ORDER also names the integration branch's Project dock, D61)
DOCKS = tuple(k for k in studio_panels.RAIL_ORDER if k != "project")
OTHERS = tuple(k for k in DOCKS if k not in studio_panels.PRINCIPAL)


# --------------------------------------------------------------------------- #
# Qt-free
# --------------------------------------------------------------------------- #
def test_the_bar_has_a_place_for_every_panel_of_the_layout_table():
    panels = set(studio_layout.PANELS) - {"result"}             # the image is the central widget, not a panel
    assert len(panels) == 7
    assert set(DOCKS) == panels and set(studio_panels.RAIL_ORDER) - panels == {"project"}
    assert len(studio_panels.RAIL_ORDER) == len(set(studio_panels.RAIL_ORDER))
    assert studio_panels.PRINCIPAL == ("program",) and len(OTHERS) == 6


def test_first_run_state_is_image_plus_code():
    state = studio_panels.initial_state()
    shown = {k for k, f in state.panels.items() if f["visible"] and not f["collapsed"]}
    assert state.mode == studio_panels.INITIAL_MODE == "code"
    assert shown == {"program", "result"}
    assert state.overrides == {}


@pytest.mark.parametrize("theme", studio_theme.THEMES)
def test_bar_colours_stand_out_a_little_and_icons_are_readable(theme):
    c = studio_panels.rail_colours(theme)
    p = studio_theme.PALETTES[theme]
    assert c["band"] == p["rail"] and c["hover"] == p["rail_hi"]         # palette roles (no colour of its own)
    assert c["band"] not in (p["chrome"], p["bg0"], p["bg1"])           # a slightly conspicuous band
    assert studio_theme.contrast(c["band"], p["chrome"]) >= 1.3
    assert studio_theme.contrast(c["icon_off"], c["band"]) >= 4.5       # icon of a hidden panel on the band
    assert studio_theme.contrast(c["icon_off"], c["hover"]) >= 4.5
    assert studio_theme.contrast(c["icon_on"], c["open"]) >= 3.0        # icon of a shown panel on its ground
    assert c["mark"] == p["accent"]                                      # never a state colour
    qss = studio_panels.rail_qss(theme)
    assert c["band"] in qss and "QToolBar#panel_rail" in qss
    assert qss.count("{") == qss.count("}") == 6


def test_bar_is_one_icon_button_wide():
    assert studio_panels.rail_width("compact") == studio_theme.DENSITY["compact"]["icon_btn"] + 4 == 28
    assert studio_panels.rail_width("standard") == studio_theme.DENSITY["standard"]["icon_btn"] + 4 == 32


def test_a_window_outside_every_screen_is_brought_back():
    screens = [(0, 0, 1920, 1040), (1920, 0, 1280, 984)]
    clamp = studio_panels.clamp_to_screens
    assert clamp((100, 100, 400, 300), screens) == (100, 100, 400, 300)           # inside: untouched
    assert clamp((2000, 50, 400, 300), screens) == (2000, 50, 400, 300)           # on the second screen: untouched
    assert clamp((1900, 100, 400, 300), screens) == (1900, 100, 400, 300)         # straddles two screens: untouched
    assert clamp((-5000, -5000, 400, 300), screens) == (0, 0, 400, 300)           # nowhere: into the first screen
    assert clamp((5000, 200, 400, 300), screens) == (1520, 200, 400, 300)
    assert clamp((100, 1030, 400, 300), screens) == (100, 740, 400, 300)          # title band below the screen
    assert clamp((100, -200, 400, 300), screens) == (100, 0, 400, 300)            # title band above the screen
    assert clamp((0, 0, 4000, 3000), [(0, 0, 800, 600)]) == (0, 0, 4000, 3000)    # title reachable: size is the user's
    assert clamp((-9000, 0, 4000, 3000), [(0, 0, 800, 600)]) == (0, 0, 800, 600)  # brought back and made to fit
    assert clamp((7, 8, 9, 10), []) == (7, 8, 9, 10)                              # no screen known: leave it


def test_layout_is_not_saved_under_offscreen_unless_asked(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.delenv("FULLSEYE_STUDIO_PERSIST_LAYOUT", raising=False)
    assert studio_panels.persist_enabled() is False
    monkeypatch.setenv("FULLSEYE_STUDIO_PERSIST_LAYOUT", "1")
    assert studio_panels.persist_enabled() is True
    monkeypatch.delenv("FULLSEYE_STUDIO_PERSIST_LAYOUT")
    monkeypatch.setenv("QT_QPA_PLATFORM", "windows")
    assert studio_panels.persist_enabled() is True


def test_every_bar_string_is_translated_into_every_language():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studio_assets", "i18n.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    langs = set(data["languages"]) - {"en"}
    assert len(langs) == 6 and len(studio_panels.STRINGS) == 43
    for text in studio_panels.STRINGS:
        row = data["strings"].get(text)
        assert row is not None, "no i18n row for %r" % text
        assert set(row) == langs and all(row[c].strip() for c in langs), text
        assert text not in data["pending_translation"]


# --------------------------------------------------------------------------- #
# the real window (offscreen, own settings file)
# --------------------------------------------------------------------------- #
def _pump(app, sec=0.25):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def _launch(monkeypatch, ini, persist=False):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(ini))
    if persist:
        monkeypatch.setenv("FULLSEYE_STUDIO_PERSIST_LAYOUT", "1")
    else:
        monkeypatch.delenv("FULLSEYE_STUDIO_PERSIST_LAYOUT", raising=False)
    from PySide6 import QtWidgets
    import studio

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    studio_theme.set_current(studio_theme.DEFAULT_THEME, studio_theme.DEFAULT_DENSITY)
    win, _model = studio.build_window()
    win.show()
    _pump(app)
    return app, win


def _close(app, win):
    win.quiesce()
    win.close_guard = lambda: True
    win.close()
    _pump(app, 0.15)


def _shown(win):
    return {k: not d.isHidden() for k, d in win._docks.items()}


FIRST_RUN = {k: (k in studio_panels.PRINCIPAL) for k in DOCKS}


def test_first_run_shows_image_and_code_and_a_bar_button_per_panel(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        assert len(win._docks) == 7 and set(win._docks) == set(DOCKS)
        assert _shown(win) == FIRST_RUN
        assert win.centralWidget().isVisible() and win._docks["program"].isVisible()
        assert not any(d.isFloating() for d in win._docks.values())
        st = win._panels
        rail = st["rail"]
        assert rail.isVisible() and win.toolBarArea(rail) == QtCore.Qt.LeftToolBarArea
        assert rail.width() == studio_panels.rail_width() == 28
        assert rail.orientation() == QtCore.Qt.Vertical and not rail.isMovable()
        assert set(st["buttons"]) == set(win._docks)                       # button <-> panel: all of them
        d = studio_theme.density()
        names = set()
        for key, b in st["buttons"].items():
            assert b.isVisible() and b.parentWidget() is rail, key
            assert (b.width(), b.height()) == (d["icon_btn"], d["icon_btn"]) == (24, 24), key
            assert not b.icon().isNull() and b.iconSize().width() == d["icon"] == 16, key
            title = win._docks[key].windowTitle()
            assert title and b.toolTip().startswith(title + "\n") and b.accessibleName() == title, key
            assert b.isChecked() == (key in studio_panels.PRINCIPAL), key
            names.add(title)
        assert len(names) == 7                                             # seven different names
        ys = [st["buttons"][k].y() for k in DOCKS]
        assert ys == sorted(ys) and len(set(ys)) == 7                      # one column, in table order
        gaps = [b - a - 24 for a, b in zip(ys[1:], ys[2:])]                # between neighbouring buttons (after the code button)
        assert gaps and all(0 <= g <= 4 for g in gaps), gaps
        assert st["layout_button"].isVisible() and st["layout_button"].toolTip() == "Layout"
        assert [t for t, _a in st["layout_actions"]] == [studio_panels.S_RESET, studio_panels.S_CODE_LEFT,
                                                        studio_panels.S_CODE_BOTTOM, studio_panels.S_DOCK_ALL]
        # the work-mode buttons agree with what is on screen
        checked = [k for k, a in win._work_mode_actions.items() if a.isChecked()]
        assert checked == ["code"] and win._layout_state.mode == "code"
        # title band of every panel: its name + the two buttons
        assert set(st["titles"]) == set(win._docks)
        for key, bar in st["titles"].items():
            assert win._docks[key].titleBarWidget() is bar
            assert bar.label.text() == win._docks[key].windowTitle().upper()          # English UI: caps
            assert bar.b_float.toolTip() == "Separate window"
            assert (bar.b_close is None) if key in studio_panels.PRINCIPAL else (bar.b_close.toolTip() == "Hide")
        assert isinstance(win.centralWidget(), QtWidgets.QMdiArea)
    finally:
        _close(app, win)


def test_each_bar_button_shows_and_hides_its_own_panel(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        buttons = win._panels["buttons"]
        assert len(buttons) == 7
        for key in OTHERS:
            before = _shown(win)
            buttons[key].click(); _pump(app, 0.1)
            assert _shown(win) == dict(before, **{key: True}), key        # this panel and no other
            assert win._docks[key].isVisible() and buttons[key].isChecked(), key
            buttons[key].click(); _pump(app, 0.1)
            assert _shown(win) == before and not buttons[key].isChecked(), key
        buttons["program"].click(); _pump(app, 0.1)                        # the code panel is a principal (D104):
        assert _shown(win) == FIRST_RUN and buttons["program"].isChecked()  # its button brings it forward, never hides it
        buttons["program"].click(); _pump(app, 0.1)
        assert _shown(win) == FIRST_RUN and buttons["program"].isChecked()
        # the title band's close button and the bar stay in step
        buttons["variables"].click(); _pump(app, 0.1)
        win._panels["titles"]["variables"].b_close.click(); _pump(app, 0.1)
        assert win._docks["variables"].isHidden() and not buttons["variables"].isChecked()
    finally:
        _close(app, win)


def test_a_panel_behind_a_tab_is_raised_not_hidden(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        buttons = win._panels["buttons"]
        buttons["operators"].click(); _pump(app, 0.1)
        buttons["pipeline"].click(); _pump(app, 0.1)
        assert win._docks["pipeline"] in win.tabifiedDockWidgets(win._docks["operators"])
        win._docks["operators"].raise_(); _pump(app, 0.2)
        assert win._docks["pipeline"].visibleRegion().isEmpty()            # really behind the Operators tab
        buttons["pipeline"].click(); _pump(app, 0.2)
        assert not win._docks["pipeline"].isHidden() and not win._docks["operators"].isHidden()
        assert not win._docks["pipeline"].visibleRegion().isEmpty()        # now in front
        assert buttons["pipeline"].isChecked() and buttons["operators"].isChecked()
        buttons["pipeline"].click(); _pump(app, 0.2)                       # in front -> the click hides it
        assert win._docks["pipeline"].isHidden() and not win._docks["operators"].isHidden()
    finally:
        _close(app, win)


def test_every_panel_becomes_a_separate_window_and_docks_back(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtGui, QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        assert len(st["float_actions"]) == 7
        for key in DOCKS:
            dock, bar = win._docks[key], st["titles"][key]
            area = win.dockWidgetArea(dock)
            assert studio_panels.toggle_float(win, key) is True; _pump(app, 0.1)
            assert dock.isFloating() and dock.isWindow() and dock.isVisible(), key
            assert not dock.isModal() and dock.windowModality() == QtCore.Qt.NonModal, key
            assert st["float_actions"][key].isChecked() and st["buttons"][key].isChecked(), key
            assert bar.b_float.toolTip() == "Dock in the main window", key
            bar.b_float.click(); _pump(app, 0.1)                           # the title band's button docks it back
            assert not dock.isFloating() and not dock.isHidden(), key
            assert win.dockWidgetArea(dock) == area, key                   # back where it was
            assert not st["float_actions"][key].isChecked() and bar.b_float.toolTip() == "Separate window", key
            if key not in studio_panels.PRINCIPAL:
                dock.hide()
        _pump(app, 0.1)
        assert _shown(win) == FIRST_RUN
        # menu entry (Window > Panels, also the command palette's action)
        st["float_actions"]["display"].trigger(); _pump(app, 0.1)
        assert win._docks["display"].isFloating() and win._docks["display"].isVisible()
        # Esc closes a separate window; the next click on the bar brings it back, still separate
        ev = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape, QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(win._docks["display"], ev); _pump(app, 0.1)
        assert win._docks["display"].isHidden() and not st["buttons"]["display"].isChecked()
        st["buttons"]["display"].click(); _pump(app, 0.1)
        assert win._docks["display"].isVisible() and win._docks["display"].isFloating()
        # Esc in a DOCKED panel does not close it
        win._docks["operators"].show(); _pump(app, 0.1)
        QtWidgets.QApplication.sendEvent(win._docks["operators"], ev); _pump(app, 0.1)
        assert not win._docks["operators"].isHidden()
        # right-click menu of a bar button: two entries, the second one floats / docks
        menu = st["panel_menu"]("operators", st["buttons"]["operators"], QtCore.QPoint(3, 3))
        texts = [a.text() for a in menu.actions()]
        assert texts == ["Hide: Operators", "Separate window: Operators"]          # D111: which panel
        menu.actions()[1].trigger(); _pump(app, 0.1); menu.close()
        assert win._docks["operators"].isFloating()
        menu = st["panel_menu"]("operators", st["buttons"]["operators"], QtCore.QPoint(3, 3))
        assert [a.text() for a in menu.actions()] == ["Hide: Operators", "Dock in the main window: Operators"]
        menu.actions()[0].trigger(); _pump(app, 0.1); menu.close()
        assert win._docks["operators"].isHidden()
        # "Dock all panels" from the layout button
        dict(st["layout_actions"])[studio_panels.S_DOCK_ALL].trigger(); _pump(app, 0.1)
        assert not any(d.isFloating() for d in win._docks.values())
    finally:
        _close(app, win)


def test_the_arrangement_survives_a_restart(tmp_path, monkeypatch):
    from PySide6 import QtCore
    ini = tmp_path / "s.ini"
    app, win = _launch(monkeypatch, ini, persist=True)
    win._panels["buttons"]["operators"].click()
    studio_panels.toggle_float(win, "variables")
    win._docks["variables"].setGeometry(180, 140, 360, 300)
    studio_panels.set_code_side(win, "left")
    _pump(app, 0.2)
    assert win.dockWidgetArea(win._docks["program"]) == QtCore.Qt.LeftDockWidgetArea
    want = _shown(win)
    assert want == dict(FIRST_RUN, operators=True, variables=True)
    geo = win._docks["variables"].geometry()
    _close(app, win)

    s = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
    assert str(s.value("layout_version")) == studio_panels.LAYOUT_VERSION == "4"
    assert len(s.value("windowState")) > 100
    del s

    app, win = _launch(monkeypatch, ini, persist=True)
    try:
        assert _shown(win) == want
        assert win._docks["variables"].isFloating() and win._docks["variables"].isVisible()
        assert win._docks["variables"].geometry() == geo
        assert not win._docks["operators"].isFloating()
        assert win.dockWidgetArea(win._docks["program"]) == QtCore.Qt.LeftDockWidgetArea
        st = win._panels
        assert {k: b.isChecked() for k, b in st["buttons"].items()} == want
        assert st["float_actions"]["variables"].isChecked()
        assert st["titles"]["variables"].b_float.toolTip() == "Dock in the main window"
        assert st["rail"].isVisible()
    finally:
        _close(app, win)


def test_reset_returns_to_image_plus_code_and_stays_after_a_restart(tmp_path, monkeypatch):
    from PySide6 import QtCore
    ini = tmp_path / "s.ini"
    app, win = _launch(monkeypatch, ini, persist=True)
    for key in ("operators", "pipeline", "display"):
        win._panels["buttons"][key].click()
    studio_panels.toggle_float(win, "ab")
    studio_panels.set_code_side(win, "left")
    win._set_work_mode("inspect")
    _pump(app, 0.2)
    assert _shown(win) != FIRST_RUN and any(d.isFloating() for d in win._docks.values())
    dict(win._panels["layout_actions"])[studio_panels.S_RESET].trigger()      # the bar's "Reset panel layout"
    _pump(app, 0.2)
    assert _shown(win) == FIRST_RUN
    assert not any(d.isFloating() for d in win._docks.values())
    assert win.dockWidgetArea(win._docks["program"]) == QtCore.Qt.BottomDockWidgetArea
    assert win._layout_state.mode == "code" and win._layout_state.overrides == {}
    assert [k for k, a in win._work_mode_actions.items() if a.isChecked()] == ["code"]
    assert {k: b.isChecked() for k, b in win._panels["buttons"].items()} == FIRST_RUN
    _close(app, win)
    app, win = _launch(monkeypatch, ini, persist=True)
    try:
        assert _shown(win) == FIRST_RUN
        assert win.dockWidgetArea(win._docks["program"]) == QtCore.Qt.BottomDockWidgetArea
    finally:
        _close(app, win)


def _good_state(tmp_path, monkeypatch):
    """A real saved arrangement that differs from the first run (Operators shown)."""
    from PySide6 import QtCore
    ini = tmp_path / "good.ini"
    app, win = _launch(monkeypatch, ini, persist=True)
    win._panels["buttons"]["operators"].click(); _pump(app, 0.1)
    _close(app, win)
    s = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
    state = s.value("windowState")
    assert isinstance(state, QtCore.QByteArray) and len(state) > 100
    return QtCore.QByteArray(state)


BROKEN = ("state_is_text", "state_is_noise", "state_is_cut", "geometry_is_text", "old_version", "no_version",
          "work_layout_not_json", "work_layout_unknown_panel", "theme_unknown", "every_panel_hidden")


@pytest.mark.parametrize("case", BROKEN)
def test_a_broken_settings_file_still_starts_with_image_plus_code(case, tmp_path, monkeypatch):
    from PySide6 import QtCore
    good = _good_state(tmp_path, monkeypatch)
    ini = tmp_path / "broken.ini"
    s = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
    s.setValue("layout_version", studio_panels.LAYOUT_VERSION)
    s.setValue("windowState", good)
    if case == "state_is_text":
        s.setValue("windowState", "not a byte array")
    elif case == "state_is_noise":
        s.setValue("windowState", QtCore.QByteArray(bytes(range(256)) * 4))
    elif case == "state_is_cut":
        s.setValue("windowState", good.left(len(good) // 3))
    elif case == "geometry_is_text":
        s.setValue("geometry", "12,34"); s.setValue("windowState", "x")
    elif case == "old_version":
        s.setValue("layout_version", "3")
    elif case == "no_version":
        s.remove("layout_version")
    elif case == "work_layout_not_json":
        s.setValue("studio/work_mode_layout", "{not json"); s.setValue("windowState", "x")
    elif case == "work_layout_unknown_panel":
        s.setValue("studio/work_mode_layout", '{"mode": "code", "panels": {"nope": {"visible": true}}}')
        s.setValue("windowState", "x")
    elif case == "theme_unknown":
        s.setValue("ui/theme", "banana"); s.setValue("ui/density", "tiny"); s.setValue("windowState", "x")
    elif case == "every_panel_hidden":
        app, win = _launch(monkeypatch, tmp_path / "hide.ini", persist=True)
        win._docks["program"].hide(); _pump(app, 0.1)
        assert _shown(win) == {k: False for k in win._docks}
        hidden = QtCore.QByteArray(win.saveState())
        _close(app, win)
        s.setValue("windowState", hidden)
    s.sync()
    del s
    app, win = _launch(monkeypatch, ini, persist=True)
    try:
        assert _shown(win) == FIRST_RUN, case                              # none of them lets Operators through
        assert win._panels["rail"].isVisible() and len(win._panels["buttons"]) == 7
        assert win.centralWidget().isVisible()
        assert studio_theme.current_name() in studio_theme.THEMES
    finally:
        _close(app, win)


def test_the_good_state_used_by_the_broken_cases_really_restores(tmp_path, monkeypatch):
    """The control of the test above: the same blob, unbroken, does bring Operators back."""
    from PySide6 import QtCore
    good = _good_state(tmp_path, monkeypatch)
    ini = tmp_path / "ok.ini"
    s = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
    s.setValue("layout_version", studio_panels.LAYOUT_VERSION); s.setValue("windowState", good); s.sync()
    del s
    app, win = _launch(monkeypatch, ini, persist=True)
    try:
        assert _shown(win) == dict(FIRST_RUN, operators=True)
    finally:
        _close(app, win)


def test_a_separate_window_saved_outside_every_screen_comes_back(tmp_path, monkeypatch):
    from PySide6 import QtGui
    ini = tmp_path / "s.ini"
    app, win = _launch(monkeypatch, ini, persist=True)
    studio_panels.toggle_float(win, "variables")
    win._docks["variables"].setGeometry(-6000, -6000, 360, 300)
    _pump(app, 0.2)
    assert win._docks["variables"].geometry().x() == -6000
    _close(app, win)
    app, win = _launch(monkeypatch, ini, persist=True)
    try:
        dock = win._docks["variables"]
        assert dock.isFloating() and dock.isVisible()
        screens = [s.availableGeometry() for s in QtGui.QGuiApplication.screens()]
        assert screens and any(g.intersects(dock.frameGeometry()) for g in screens)
        assert any(g.contains(dock.frameGeometry().topLeft()) for g in screens)
    finally:
        _close(app, win)


def test_scheme_density_and_language_reach_the_bar_and_the_title_bands(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        rail = st["rail"]
        for theme in studio_theme.THEMES:
            win._apply_theme(theme=theme, save=False); _pump(app, 0.05)
            assert studio_panels.rail_colours(theme)["band"] in rail.styleSheet(), theme
            assert studio_theme.PALETTES[theme]["chrome"] in st["titles"]["program"].styleSheet(), theme
        assert studio_panels.rail_colours("instrument")["band"] != studio_panels.rail_colours("panel")["band"]
        win._apply_theme(level="standard", save=False); _pump(app, 0.05)
        assert rail.width() == 32 and st["buttons"]["operators"].width() == 28
        win._apply_theme(theme="instrument", level="compact", save=False); _pump(app, 0.05)
        assert rail.width() == 28 and st["buttons"]["operators"].width() == 24
        win._apply_language("ja"); _pump(app, 0.05)
        title = win._docks["operators"].windowTitle()
        assert title != "Operators"
        assert st["buttons"]["operators"].toolTip() == title + "\nクリック: 出す / しまう。右クリック: 別ウィンドウ / 本体に戻す。"
        assert st["titles"]["operators"].label.text() == title
        assert st["titles"]["operators"].b_float.toolTip() == "別ウィンドウにする"
        assert st["layout_button"].toolTip() == "レイアウト"
        assert st["float_actions"]["operators"].text() == "別ウィンドウにする: " + title
        assert [a.text() for _t, a in st["layout_actions"]] == ["パネル配置を元に戻す", "コードを左に(縦長)",
                                                              "コードを下に(横長)", "すべてのパネルを戻す"]
        win._apply_language("en"); _pump(app, 0.05)
        assert st["titles"]["operators"].label.text() == "OPERATORS"
        assert st["buttons"]["operators"].toolTip().startswith("Operators\nClick: show or hide.")
    finally:
        win._apply_language("en")
        _close(app, win)


def test_menu_and_palette_reach_every_panel(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        listed = win._menu_panels.actions()
        for key, dock in win._docks.items():
            entry = (win._panels["principal_actions"][key] if key in studio_panels.PRINCIPAL
                     else dock.toggleViewAction())                              # a principal: "bring forward" (D104)
            assert entry in listed, "Window > Panels has no show / hide entry for %s" % key
            assert win._panels["float_actions"][key] in listed, key
            assert win._actions["panel_float_" + key] is win._panels["float_actions"][key]
        assert sum(1 for a in listed if a in [d.toggleViewAction() for d in win._docks.values()]) == 6
        assert win._actions["layout_code_left"].text() == "Code on the left (tall)"
        assert win._actions["layout_code_bottom"].text() == "Code at the bottom (wide)"
    finally:
        _close(app, win)


def test_code_can_be_a_tall_column_or_a_wide_strip(tmp_path, monkeypatch):
    from PySide6 import QtCore
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.2)
        code, image = win._docks["program"], win.centralWidget()
        wide = (code.width(), code.height())
        assert wide[0] > wide[1] * 2
        win._actions["layout_code_left"].trigger(); _pump(app, 0.3)
        assert win.dockWidgetArea(code) == QtCore.Qt.LeftDockWidgetArea
        assert code.height() > wide[1] * 2 and code.width() >= 360          # tall, and wide enough to write in
        assert image.width() >= 400 and image.height() > 400                # the image keeps real room
        win._actions["layout_code_bottom"].trigger(); _pump(app, 0.3)
        assert win.dockWidgetArea(code) == QtCore.Qt.BottomDockWidgetArea and code.width() > code.height() * 2
        with pytest.raises(ValueError):
            studio_panels.set_code_side(win, "top")
    finally:
        _close(app, win)


def test_density_leftovers_group_rows_and_spare_height(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        d = studio_theme.density()
        groups = [g for dock in win._docks.values() for g in dock.widget().findChildren(QtWidgets.QGroupBox)]
        assert len(groups) >= 7
        nested = 0
        for g in groups:
            m = g.layout().contentsMargins()
            assert (m.left(), m.top(), m.right(), m.bottom()) == (d["inner"], d["title_gap"], d["inner"], d["inner"])
            for lay in g.findChildren(QtWidgets.QLayout):
                if lay.parentWidget() is g and lay is not g.layout():      # a row nested in the group's column
                    mm = lay.contentsMargins()
                    assert (mm.left(), mm.top(), mm.right(), mm.bottom()) == (0, 0, 0, 0), g.title()
                    nested += 1
        assert nested >= 8                                                 # the rows that used to carry 2 + 6 px each
        assert "padding:0px; }" in studio_theme.build_qss().split("QGroupBox {")[1].split("\n")[1]
        # Display · Analysis: the inspector takes the spare height instead of gaps between fixed rows
        boxes = win._docks["display"].widget().findChildren(QtWidgets.QPlainTextEdit)
        released = [b for b in boxes if b.minimumHeight() == 150 and b.maximumHeight() > 10000]
        assert len(released) == 1
        # a second pass changes nothing more
        assert studio_panels.tighten(win) == 0
        assert win.statusBar().maximumHeight() == win.statusBar().fontMetrics().height() + 8
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# wide panels: icon rows and tabs on the left (2026-11-13)
# --------------------------------------------------------------------------- #
def test_side_rule_has_hysteresis_and_the_fixed_modes_win():
    side = studio_panels.strip_side
    assert (studio_panels.WIDE_ON, studio_panels.WIDE_OFF) == (2.2, 1.6)
    assert side(220, 100, "top") == "left" and side(219, 100, "top") == "top"       # on at 2.2
    assert side(161, 100, "left") == "left" and side(160, 100, "left") == "top"     # off at 1.6
    assert side(190, 100, "top") == "top" and side(190, 100, "left") == "left"      # in between: stays
    # dragging back and forth around either threshold's inside does not flip it
    for start in ("top", "left"):
        cur, flips = start, 0
        for w in [170, 215, 165, 210, 175, 200, 162, 218] * 5:
            new = side(w, 100, cur)
            flips += new != cur
            cur = new
        assert flips == 0, start
    # a full sweep up and down flips exactly once each way
    cur, seen = "top", []
    for w in list(range(100, 300, 5)) + list(range(300, 100, -5)):
        new = side(w, 100, cur)
        if new != cur:
            seen.append((w, new))
        cur = new
    assert seen == [(220, "left"), (160, "top")]
    assert side(100, 300, "top", "left") == "left" and side(900, 100, "left", "top") == "top"   # fixed by the user
    assert side(0, 0, "left") == "left" and side(500, 0, "top") == "top"            # no size yet: unchanged
    assert [studio_panels.normalise_strip_mode(v) for v in ("LEFT", " top ", None, "sideways", "auto")] == [
        "left", "top", "auto", "auto", "auto"]
    assert studio_panels.STRIP_MODES == ("auto", "top", "left") and set(studio_panels.S_STRIP) == set(studio_panels.STRIP_MODES)


_FONTS = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
_UI_FONT_FILES = [os.path.join(_FONTS, n) for n in ("segoeui.ttf", "YuGothR.ttc", "msyh.ttc", "msjh.ttc", "malgun.ttf")] + [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def _lend_fonts():
    """The offscreen platform has an empty font database on Windows (text widths are then those of a
    placeholder box). Lend it the UI font files for one test; returns the ids to give back."""
    from PySide6 import QtGui
    if QtGui.QFontDatabase.families():
        return []
    return [QtGui.QFontDatabase.addApplicationFont(p) for p in _UI_FONT_FILES if os.path.isfile(p)]


def _to_bottom(win, app, keys, code_left=True):
    from PySide6 import QtCore
    if code_left:
        studio_panels.set_code_side(win, "left")
    for k in keys:
        win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, win._docks[k])
        win._docks[k].show()
    for k in keys[1:]:
        win.tabifyDockWidget(win._docks[keys[0]], win._docks[k])
    win._docks[keys[0]].raise_()
    _pump(app, 0.4)


def test_icon_rows_turn_with_the_shape_of_their_panel(tmp_path, monkeypatch):
    """Every panel declares its strip (A1, 2026-11-13); the gate over all panels and the scroll / wrap of a
    strip that does not fit (A2 A3, which replaced the "..." menu) are in test_studio_panels_interaction_2026_11_13."""
    from PySide6 import QtCore
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.2)
        strips = {e["key"]: e for e in win._panels["strips"]}
        assert {k: len(e["strip"].items()) for k, e in strips.items() if k in win._docks} == {
            "program": 6, "operators": 3, "pipeline": 6, "variables": 2, "ab": 3}
        entry = strips["variables"]
        s = entry["strip"]
        dock = win._docks["variables"]
        dock.show(); _pump(app, 0.4)                                        # in the right column: tall
        assert dock.height() > dock.width() and entry["side"] == "top" and s.orientation == "h"
        assert len({b.mapTo(dock, QtCore.QPoint(0, 0)).y() for b in s.items()}) == 1      # one row
        _to_bottom(win, app, ["variables"])                                 # under the image: wide
        assert dock.width() >= 2.2 * dock.height(), (dock.width(), dock.height())
        assert entry["side"] == "left" and s.orientation == "v"
        xs = {b.mapTo(dock, QtCore.QPoint(0, 0)).x() for b in s.items()}
        assert len(xs) == 1 and min(xs) < entry["body"].mapTo(dock, QtCore.QPoint(0, 0)).x()   # one column, on the left
        assert not entry["home"].isVisible()                                # the row it left gives its height back
        studio_panels.set_strip_mode(win, "top"); _pump(app, 0.3)           # the user fixes it on top
        assert entry["side"] == "top" and s.orientation == "h" and entry["home"].isVisible()
        studio_panels.set_strip_mode(win, "auto"); _pump(app, 0.3)
        assert entry["side"] == "left"
        win.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock); _pump(app, 0.4)   # moved back: tall again
        assert dock.height() > dock.width() and entry["side"] == "top"
        studio_panels.set_strip_mode(win, "left"); _pump(app, 0.3)          # fixed on the left although tall
        assert entry["side"] == "left" and s.orientation == "v"
        studio_panels.toggle_float(win, "variables"); dock.resize(900, 260); _pump(app, 0.4)
        studio_panels.set_strip_mode(win, "auto"); _pump(app, 0.3)
        assert entry["side"] == "left"                                      # a separate window follows its own shape
        dock.resize(300, 500); _pump(app, 0.4)
        assert entry["side"] == "top"
    finally:
        _close(app, win)


def test_tabs_of_a_wide_tab_group_stand_on_the_left_and_every_tab_is_reachable(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtGui, QtTest, QtWidgets
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _qapp = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    lent = _lend_fonts()
    if not QtGui.QFontDatabase.families():
        pytest.skip("no font at all on this machine: text widths cannot be measured")
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        win.resize(1280, 720); _pump(app, 0.2)
        keys = ["variables", "compare", "ab"]
        _to_bottom(win, app, keys)
        assert win.tabPosition(QtCore.Qt.BottomDockWidgetArea) == QtWidgets.QTabWidget.West
        assert win.tabPosition(QtCore.Qt.RightDockWidgetArea) == QtWidgets.QTabWidget.North      # other areas untouched
        bars = [b for b in win.findChildren(QtWidgets.QTabBar) if b.parentWidget() is win and b.isVisible() and b.count() == 3]
        assert len(bars) == 1
        bar = bars[0]
        assert bar.shape() == QtWidgets.QTabBar.RoundedWest and bar.elideMode() == QtCore.Qt.ElideNone
        d = studio_theme.density()
        fm = bar.fontMetrics()
        assert bar.width() == fm.height() + 2 * d["tab_v"] + 2                # text height + the table's pad + frame
        assert bar.width() <= 24
        titles = {win._docks[k].windowTitle(): k for k in keys}
        assert len(titles) == 3
        for lang in ("en", "ja", "zh", "tw", "ko", "de"):                     # no name is cut in any language
            win._apply_language(lang); _pump(app, 0.3)
            texts = [bar.tabText(i) for i in range(bar.count())]
            assert sorted(texts) == sorted(win._docks[k].windowTitle() for k in keys), lang
            for i in range(bar.count()):
                r = bar.tabRect(i)
                assert r.height() >= fm.horizontalAdvance(bar.tabText(i)) + 2, (lang, bar.tabText(i), r.height())
                assert bar.rect().contains(r), (lang, bar.tabText(i))
        win._apply_language("en"); _pump(app, 0.3)
        titles = {win._docks[k].windowTitle(): k for k in keys}
        front = []
        for i in range(bar.count()):                                          # every tab brings its own panel forward
            bar.setCurrentIndex(i); _pump(app, 0.15)
            key = titles[bar.tabText(i)]
            assert not win._docks[key].visibleRegion().isEmpty(), key
            front.append(key)
        assert sorted(front) == sorted(keys)
        bar.setCurrentIndex(0); bar.setFocus(); _pump(app, 0.1)               # keyboard: the arrow keys walk the tabs
        QtTest.QTest.keyClick(bar, QtCore.Qt.Key_Down); _pump(app, 0.1)
        assert bar.currentIndex() == 1
        QtTest.QTest.keyClick(bar, QtCore.Qt.Key_Down); _pump(app, 0.1)
        assert bar.currentIndex() == 2
        QtTest.QTest.keyClick(bar, QtCore.Qt.Key_Up); _pump(app, 0.1)
        assert bar.currentIndex() == 1
        QtTest.QTest.keyClick(bar, QtCore.Qt.Key_Down); QtTest.QTest.keyClick(bar, QtCore.Qt.Key_Down); _pump(app, 0.1)
        assert bar.currentIndex() == 2                                        # stops at the last tab
        QtTest.QTest.keyClick(bar, QtCore.Qt.Key_Left); _pump(app, 0.1)       # Qt's own keys still work
        assert bar.currentIndex() == 1
        assert not win._docks[titles[bar.tabText(1)]].visibleRegion().isEmpty()   # the key really changed the panel
        studio_panels.set_strip_mode(win, "top"); _pump(app, 0.3)             # fixed on top: a horizontal bar again
        assert win.tabPosition(QtCore.Qt.BottomDockWidgetArea) == QtWidgets.QTabWidget.North
        studio_panels.set_strip_mode(win, "auto"); _pump(app, 0.3)
        assert win.tabPosition(QtCore.Qt.BottomDockWidgetArea) == QtWidgets.QTabWidget.West
        assert "QTabBar::tab:left" in studio_theme.build_qss()
    finally:
        win._apply_language("en")
        _close(app, win)
        for i in lent:
            QtGui.QFontDatabase.removeApplicationFont(i)


def test_the_fixed_side_is_saved_and_is_back_after_a_restart(tmp_path, monkeypatch):
    from PySide6 import QtCore
    ini = tmp_path / "s.ini"
    app, win = _launch(monkeypatch, ini)
    st = win._panels
    assert st["strip_mode"] == "auto" and [m for m, a in st["strip_actions"].items() if a.isChecked()] == ["auto"]
    assert len(st["strip_actions"]) == 3
    st["strip_actions"]["left"].trigger(); _pump(app, 0.2)                    # the entry in the bar's layout menu
    assert st["strip_mode"] == "left"
    _close(app, win)
    s = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
    assert s.value("panels/strip_mode") == "left"
    del s
    app, win = _launch(monkeypatch, ini)
    try:
        st = win._panels
        assert st["strip_mode"] == "left"
        assert [m for m, a in st["strip_actions"].items() if a.isChecked()] == ["left"]
        win._docks["variables"].show(); _pump(app, 0.4)
        entry = [e for e in st["strips"] if e["key"] == "variables"][0]
        assert entry["side"] == "left"                                        # tall panel, yet on the left: the saved choice
        s = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
        s.setValue("panels/strip_mode", "diagonal"); s.sync()
        del s
    finally:
        _close(app, win)
    app, win = _launch(monkeypatch, ini)
    try:
        assert win._panels["strip_mode"] == "auto"                            # a value it does not know -> automatic
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# title band: name -> status -> menu button (2026-11-13)
# --------------------------------------------------------------------------- #
def test_every_panel_has_a_title_band_with_a_menu_button_one_line_high(tmp_path, monkeypatch):
    from PySide6 import QtCore
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        bars = win._panels["titles"]
        assert len(bars) == len(win._docks) == 7
        d = studio_theme.density()
        for key, bar in bars.items():
            win._docks[key].show()
        _pump(app, 0.3)
        for key, bar in bars.items():
            title = win._docks[key].windowTitle()
            assert bar.height() == d["title_band"] - 2 <= bar.fontMetrics().height() + 2 * d["row_pad"], key   # one line
            assert bar.b_menu.objectName() == "dock_title_menu" and bar.b_menu.menu() is not None, key
            assert bar.b_menu.accessibleName() == title + " — Panel menu", key
            assert bar.b_menu.toolTip().endswith("(Alt+M)") and bar.label.accessibleName() == title, key
            assert bar.b_menu.focusPolicy() == QtCore.Qt.TabFocus, key                 # reachable with Tab
            assert bar.key_menu.shortcut().toString() == "Alt+M", key
            assert bar.key_menu.shortcutContext() == QtCore.Qt.WidgetWithChildrenShortcut, key  # only inside this panel
            assert bar.key_menu in win._docks[key].actions(), key
            assert bar.key_menu.text() == (title + " \u2014 Panel menu").replace("&", "&&"), key   # D14: '&' is shown
            # order on the band: name, [status], separate window, hide, menu at the right end (D105)
            xs = [bar.label.x()] + [b.x() for b in bar.buttons()]
            assert xs == sorted(xs) and len(set(xs)) == len(xs) and xs[-1] == bar.b_menu.x(), key
            left = -1 if bar.label.isHidden() else bar.label.x()       # D59: tabbed = the tab carries the name
            for item in bar.status:
                if not item["label"].isHidden():
                    assert left < item["label"].x() < bar.buttons()[0].x(), (key, item["id"])
    finally:
        _close(app, win)


def test_the_menu_holds_what_the_panel_registered_then_the_common_entries(tmp_path, monkeypatch):
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        want = {"operators": ["focus_search", "op_reference", "samples"],
                "pipeline": ["run_all", "step", "reset", None, "remove", "move_up", "move_down", "duplicate_stage", "bypass"],
                "display": ["fit", "actual_size", "zoom_in", "zoom_out", "surface_3d"],
                "compare": ["step", "reset", None, "pin_a"]}            # (program / variables / A / B: buttons too, below)
        total = 0
        for key, names in want.items():
            assert all(n is None or n in win._actions for n in names), key          # the actions exist in this build
            bar = st["titles"][key]
            assert bar.actions[:len(names)] == [None if n is None else win._actions[n] for n in names], key
            bar.fill_menu()
            acts = bar.b_menu.menu().actions()
            own = [a for a in acts if a in [win._actions[n] for n in names if n]]
            assert own == [win._actions[n] for n in names if n], key                  # the SAME QAction objects, in order
            tail = acts[-3:]                                                          # what every panel has: its own two
            assert tail[0].isSeparator() and tail[1] is st["float_actions"][key], key
            assert tail[2].text() == "Hide" and tail[2] is bar.a_hide, key
            everywhere = list(st["strip_actions"].values()) + [st["layout_actions"][0][1]]   # D98: not in a panel's menu
            assert not [a for a in acts if a in everywhere], key
            total += len(own)
        assert total == 3 + 8 + 5 + 3
        ops = st["titles"]["operators"].actions                                   # the strip's buttons follow (A2)
        assert ops[3:] == [None] + [studio_panels.button_action(win, b) for b in win._panel_buttons["operators"].values()]
        # a key in the menu is the action's own (shown at the right by Qt): Run all has one
        assert win._actions["run_all"].shortcut().toString() != ""
        # the menu's Hide really hides
        bar = st["titles"]["operators"]
        win._docks["operators"].show(); _pump(app, 0.1)
        bar.fill_menu()
        [a for a in bar.b_menu.menu().actions() if a.text() == "Hide"][0].trigger(); _pump(app, 0.1)
        assert win._docks["operators"].isHidden()
        with pytest.raises(KeyError):
            studio_panels.register_panel(win, "no_such_panel")
    finally:
        _close(app, win)


def test_every_panel_menu_offers_three_to_eight_of_its_own_and_one_qaction_per_function(tmp_path, monkeypatch):
    """User, 2026-11-13: the menu button holds 3..8 of the panel's frequent functions + the common entries,
    and the same function is the same QAction wherever it appears (menu bar, bar's layout menu, panel menus)."""
    from PySide6 import QtGui
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        own = {k: [a for a in bar.actions if a is not None] for k, bar in st["titles"].items()}
        assert sorted(own) == sorted(DOCKS) and len(own) == 7
        for key, acts in own.items():
            assert studio_panels.MENU_OWN_MIN <= len(acts) <= studio_panels.MENU_OWN_MAX, (key, [a.text() for a in acts])
            assert len(set(acts)) == len(acts), key                                  # no entry twice in one menu
            assert all(a.text().strip() for a in acts), key                         # every entry has a name
        # the panel buttons that had no QAction: one action each, the button's name / state, pressing the button
        pb = win._panel_buttons
        assert sorted(pb) == ["ab", "graphics_1", "operators", "pipeline", "program", "variables"]
        assert sum(len(v) for v in pb.values()) == 6 + 3 + 3 + 3 + 6 + 7
        backed = st["button_of"]                    # pipeline / graphics_1 use the window's own QActions (same names)
        assert len(backed) == 4 + 2 + 3 + 3 + 3 and set(backed.values()) <= {b for v in pb.values() for b in v.values()}
        for act, button in backed.items():
            assert studio_panels.button_action(win, button) is act                     # asked again: the same object
            assert act.toolTip() == button.toolTip().strip() and act.text()
        restore = pb["ab"]["restore"]
        act = studio_panels.button_action(win, restore)
        assert act.text() == restore.text()                                          # a push button keeps its own words
        clicks = []
        restore.clicked.connect(lambda _c=False: clicks.append(1))
        restore.setEnabled(True); act.trigger(); _pump(app, 0.05)
        assert clicks == [1]                                                         # the entry presses the real button
        restore.setEnabled(False)
        st["titles"]["ab"].fill_menu()                                             # the menu takes the state of the moment
        assert not act.isEnabled()
        act.trigger(); _pump(app, 0.05)
        assert clicks == [1]                                                         # a disabled button is not pressed
        name = studio_panels.button_action(win, pb["program"]["apply"]).text()
        assert name == "Apply the code to the pipeline"                              # D98: the function's own short name
        assert len(studio_panels.button_action(win, pb["program"]["continue"]).text()) <= 32
        # one function, one QAction: the bar's layout menu uses the Window menu's own actions
        layout = dict(st["layout_actions"])
        assert layout[studio_panels.S_RESET] is win._actions["reset_layout"]
        assert layout[studio_panels.S_DOCK_ALL] is win._actions["dock_all"]
        texts = [a.text() for a in win.findChildren(QtGui.QAction)]
        assert texts.count("Reset panel layout") == 1 and texts.count("Dock all panels") == 1, \
            (texts.count("Reset panel layout"), texts.count("Dock all panels"))
        bar = st["titles"]["variables"]
        def kept(b):            # the menu's entries without the read-outs that did not fit (made per opening)
            return [a for a in b.b_menu.menu().actions() if not a.isSeparator()][len(b.dropped):]
        bar.fill_menu(); first = kept(bar)
        bar.fill_menu(); second = kept(bar)
        assert len(second) >= 5 + 2 and first == second and bar.a_hide in second       # Hide is made once, not per opening
        # "Reset panel layout" from a panel menu really resets (image + code)
        win._docks["pipeline"].show(); _pump(app, 0.1)
        layout[studio_panels.S_RESET].trigger(); _pump(app, 0.3)
        assert [k for k, d in win._docks.items() if not d.isHidden()] == ["program"]
        win._apply_language("ja"); _pump(app, 0.3)                                   # names follow the language
        st["titles"]["ab"].fill_menu()
        assert act.text() == restore.text() and act.text() != "Restore A", act.text()
        names = [a.text() for bar in st["titles"].values() for a in bar.actions if a is not None]
        assert len(names) >= 7 * studio_panels.MENU_OWN_MIN
        english = [n for n in names if all(ord(ch) < 128 for ch in n)]
        assert english == [], english                                                 # no English left in the Japanese menus
        assert studio_panels.button_action(win, pb["program"]["apply"]).text() == "コードを処理手順に適用"
    finally:
        win._apply_language("en")
        _close(app, win)


def test_status_items_follow_the_panel(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        st = win._panels
        for key in ("operators", "pipeline", "variables"):
            studio_panels.toggle_float(win, key); win._docks[key].resize(640, 420)
        _pump(app, 0.6)
        ops = st["titles"]["operators"].status[0]
        total = win._op_list.count()
        assert total > 50 and ops["now"].startswith("Shown: ") and ops["now"].endswith("/ %d" % total)
        assert not ops["label"].isHidden() and ops["label"].text() == ops["now"]
        before = ops["now"]
        search = [e for e in win._docks["operators"].findChildren(QtWidgets.QLineEdit) if e.placeholderText()][0]
        search.setText("otsu"); _pump(app, 0.7)                                # no call from the test: the 4 Hz tick
        shown = sum(1 for i in range(win._op_list.count()) if not win._op_list.item(i).isHidden())
        assert 0 < shown < total or win._op_list.count() < total
        assert ops["now"] != before and ops["label"].text() == ops["now"]
        stages = [i for i in st["titles"]["pipeline"].status if i["id"] == "stages"][0]
        n = win._stage_list.count()
        assert stages["now"] == "Stages: %d" % n
        win._stage_list.addItem("extra row"); _pump(app, 0.6)       # the read-out counts the list's own rows
        assert stages["now"] == "Stages: %d" % (n + 1) and stages["label"].text() == stages["now"]
        err = [i for i in st["titles"]["pipeline"].status if i["id"] == "errors"][0]
        assert err["now"] == "" and err["label"].isHidden()                  # nothing wrong: the item is not there at all
        win._state["errors"] = ["boom"]; _pump(app, 0.6)
        assert err["now"] == "✕ Errors: 1" and not err["label"].isHidden()
        win._state["errors"] = []; _pump(app, 0.6)
        assert err["now"] == "" and err["label"].isHidden()
        win._apply_language("ja"); _pump(app, 0.6)
        assert stages["now"] == "段 %d" % win._stage_list.count()     # (the language change rebuilt the list)
    finally:
        win._apply_language("en")
        _close(app, win)


def test_a_narrow_band_drops_whole_items_lowest_priority_first_and_keeps_name_and_menu(tmp_path, monkeypatch):
    from PySide6 import QtGui, QtWidgets
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _qapp = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    lent = _lend_fonts()
    if not QtGui.QFontDatabase.families():
        pytest.skip("no font at all on this machine: text widths cannot be measured")
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        texts = {"hi": "errors 3 of 12 in the last run", "mid": "lines 1 204 of output kept", "lo": "stopped at line 88 of measure.py"}
        bar = studio_panels.register_panel(win, "compare", status=[
            {"id": "lo", "text": lambda: texts["lo"], "priority": 1},
            {"id": "hi", "text": lambda: texts["hi"], "priority": 3},
            {"id": "mid", "text": lambda: texts["mid"], "priority": 2}], actions=[])
        assert [i["id"] for i in bar.status] == ["lo", "hi", "mid"] and len(bar.status) == 3
        dock = win._docks["compare"]
        studio_panels.toggle_float(win, "compare")
        seen = []
        for width in (1100, 900, 760, 680, 600, 540, 480, 420, 380, 340, 300, 260, 220, 190, 160):
            dock.resize(width, 300); _pump(app, 0.15)
            vis = tuple(i["id"] for i in bar.status if not i["label"].isHidden())
            seen.append(vis)
            assert not bar.label.isHidden() and not bar.b_menu.isHidden()            # name and menu: to the last
            assert bar.b_menu.x() + bar.b_menu.width() <= bar.width() and bar.label.x() >= 0
            for i in bar.status:                                                    # never a cut item: whole or gone
                if not i["label"].isHidden():
                    assert i["label"].width() >= i["label"].fontMetrics().horizontalAdvance(i["now"]), (width, i["id"])
                    assert i["label"].x() + i["label"].width() <= bar.buttons()[0].x(), (width, i["id"])
            assert sorted(i["id"] for i in bar.dropped) == sorted(set(texts) - set(vis))
        assert set(seen[0]) == {"lo", "hi", "mid"} and seen[-1] == ()
        order = []
        for vis in seen:                                                            # the order they disappear in
            for gone in ("lo", "mid", "hi"):
                if gone not in vis and gone not in order:
                    order.append(gone)
        assert order == ["lo", "mid", "hi"]
        sizes = [len(v) for v in seen]
        assert sizes == sorted(sizes, reverse=True) and len(set(sizes)) == 4          # 3, 2, 1 and 0 were all seen
        # what was dropped is still to be had: the name's tool tip and the top of the menu
        assert bar.label.toolTip().split("\n")[1:] and set(bar.label.toolTip().split("\n")[1:]) == set(texts.values())
        bar.fill_menu()
        head = bar.b_menu.menu().actions()[:3]
        assert {a.text() for a in head} == set(texts.values()) and not any(a.isEnabled() for a in head)
        dock.resize(1100, 300); _pump(app, 0.15)
        assert bar.label.toolTip() == "" and not bar.dropped
        texts["hi"] = ""; bar.update_status()                                        # an empty text takes no room
        assert [i["id"] for i in bar.status if not i["label"].isHidden()] == ["lo", "mid"]
        bar2 = studio_panels.register_panel(win, "compare", status=[], actions=[])   # registering again replaces
        assert bar2 is bar and bar.status == []
    finally:
        _close(app, win)
        for i in lent:
            QtGui.QFontDatabase.removeApplicationFont(i)


def test_double_click_and_drag_on_the_name_still_belong_to_the_dock(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtTest
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        dock = win._docks["operators"]
        dock.show(); _pump(app, 0.3)
        bar = win._panels["titles"]["operators"]
        on_name = bar.label.geometry().center()
        on_space = QtCore.QPoint((bar.label.geometry().right() + bar.buttons()[0].x()) // 2, bar.height() // 2)
        assert bar.childAt(on_space) is None or bar.childAt(on_space) in [i["label"] for i in bar.status]
        assert not dock.isFloating()
        QtTest.QTest.mouseDClick(bar, QtCore.Qt.LeftButton, pos=on_name); _pump(app, 0.3)
        assert dock.isFloating()                                    # Qt's own double-click: separate window
        QtTest.QTest.mouseDClick(bar, QtCore.Qt.LeftButton, pos=on_name); _pump(app, 0.3)
        assert not dock.isFloating()                                # ... and back
        QtTest.QTest.mouseDClick(bar, QtCore.Qt.LeftButton, pos=on_space); _pump(app, 0.3)
        assert dock.isFloating()                                    # the empty part of the band too
        QtTest.QTest.mouseDClick(bar, QtCore.Qt.LeftButton, pos=on_space); _pump(app, 0.3)
        assert not dock.isFloating()
        # drag: press on the name and move away -> the dock leaves the window (Qt's own drag)
        QtTest.QTest.mousePress(bar, QtCore.Qt.LeftButton, pos=on_name)
        for step in range(1, 9):
            QtTest.QTest.mouseMove(bar, on_name + QtCore.QPoint(-30 * step, -25 * step)); _pump(app, 0.03)
        dragged = dock.isFloating()
        QtTest.QTest.mouseRelease(bar, QtCore.Qt.LeftButton, pos=on_name + QtCore.QPoint(-240, -200)); _pump(app, 0.3)
        assert dragged
        # a click on the menu button is the button's, not a drag
        assert bar.childAt(bar.b_menu.geometry().center()) is bar.b_menu
    finally:
        _close(app, win)


# --------------------------------------------------------------------------- #
# the brand corner as the progress read-out (2026-11-13)
# --------------------------------------------------------------------------- #
def _brand(monkeypatch, log=None):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    host = QtWidgets.QWidget()
    b = studio_panels.make_brand_status(host, "Fullseye Studio", None, log)
    host.resize(400, 60); host.show()
    _pump(app, 0.05)
    return app, host, b


def test_brand_begin_update_end_changes_text_and_band_but_never_the_frame(monkeypatch):
    app, host, b = _brand(monkeypatch)
    size = (b.width(), b.height())
    assert b.current() == ("idle", "Fullseye Studio") and b.accessibleName() == "Fullseye Studio"
    b.show_after_ms, b.done_ms = 0, 120
    tok = b.begin("Running 1/7 median", total=7); _pump(app, 0.05)
    assert b.current() == ("busy", "Running 1/7 median", 0.0, 0)
    b.update_job(tok, done=3, text="Running 3/7 otsu"); _pump(app, 0.05)
    state = b.current()
    assert state[:2] == ("busy", "Running 3/7 otsu") and state[2] == pytest.approx(3 / 7.0)
    assert b.toolTip() == "Running 3/7 otsu" and b.accessibleDescription() == "Running 3/7 otsu 43%"
    b.grab()
    assert b.shown_text == "▶ Running 3/7 otsu"                        # a shape and words, not colour alone
    assert (b.width(), b.height()) == size
    b.update_job(tok, done=99); _pump(app, 0.05)
    assert b.current()[2] == 1.0                                            # never beyond the frame
    tok2 = b.begin("Indexing the search"); _pump(app, 0.05)                 # unknown length: no fraction
    assert b.current() == ("busy", "Indexing the search", None, 1)          # the newest speaks, the other is counted
    b.grab()
    assert b.shown_text.endswith("(+1)")
    b.end(tok2); _pump(app, 0.05)
    assert b.current()[:2] == ("busy", "Running 3/7 otsu")                  # back to the one still running
    b.end(tok); _pump(app, 0.03)
    assert b.current() == ("done", "Done") and (b.width(), b.height()) == size
    _pump(app, 0.25)
    assert b.current() == ("idle", "Fullseye Studio") and b.toolTip() == ""
    b.update_job(tok, done=1); b.end(tok); _pump(app, 0.05)                 # a token that is over: ignored
    assert b.current() == ("idle", "Fullseye Studio")
    # a text longer than the frame is cut at its end and whole in the tool tip
    long = "Loading a very long file name that cannot fit into the frame at all.png"
    tok = b.begin(long); _pump(app, 0.05); b.grab()
    assert b.shown_text.endswith("…") and b.toolTip() == long and (b.width(), b.height()) == size
    b.end(tok); host.close()


def test_brand_short_jobs_do_not_flicker_but_a_failure_is_always_said(monkeypatch):
    app, host, b = _brand(monkeypatch)
    assert b.show_after_ms == studio_panels.BRAND_SHOW_AFTER_MS == 300
    seen = set()
    tok = b.begin("quick", total=2)
    for _ in range(10):
        _pump(app, 0.01); seen.add(b.current()[0])
    b.end(tok); _pump(app, 0.05); seen.add(b.current()[0])
    assert seen == {"idle"}                                                 # 0.1 s job: nothing was ever shown
    tok = b.begin("slow"); _pump(app, 0.45)
    assert b.current()[:2] == ("busy", "slow")                              # after 0.3 s it is there
    b.end(tok); _pump(app, 0.05)
    b.flash_timer.stop(); b._flash_over()
    tok = b.begin("save"); b.end(tok, ok=False, text="Could not save: disk full"); _pump(app, 0.05)
    assert b.current() == ("failed", "Could not save: disk full")           # short, but a failure
    b.grab()
    assert b.shown_text.startswith("▲ ")
    host.close()


def test_brand_is_safe_from_another_thread_and_drops_a_job_nobody_ended(monkeypatch):
    import threading
    logged = []
    app, host, b = _brand(monkeypatch, log=lambda what, why: logged.append((what, why)))
    b.show_after_ms = 0
    got = {}

    def work():
        tok = b.begin("from a thread", total=4)
        b.update_job(tok, done=2)
        got["tok"] = tok
    th = threading.Thread(target=work); th.start(); th.join()
    assert b.jobs == {}                                                     # nothing touched the widget from the thread
    _pump(app, 0.1)
    assert b.current()[:3] == ("busy", "from a thread", 0.5)
    th = threading.Thread(target=lambda: b.end(got["tok"])); th.start(); th.join(); _pump(app, 0.1)
    assert b.current()[0] == "done"
    b.flash_timer.stop(); b._flash_over()
    b.stale_ms = 150
    b.begin("never ended"); _pump(app, 0.6)
    assert b.current() == ("idle", "Fullseye Studio") and b.jobs == {}
    assert len(logged) == 1 and "never ended" in logged[0][0]
    host.close()


def test_brand_follows_the_run_progress_bar_in_the_real_window(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        b = win._brand
        tb = [t for t in win.findChildren(QtWidgets.QToolBar) if t.objectName() == "main_tools"][0]
        assert b.parentWidget() is tb and b.isVisible() and b.current() == ("idle", "Fullseye Studio")
        size = (b.width(), b.height())
        b.show_after_ms = 0
        bars = [p for p in win.findChildren(QtWidgets.QProgressBar) if p.width() == 90 or p.maximumWidth() == 90]
        assert len(bars) == 1
        bar = bars[0]
        bar.setRange(0, 5); bar.setValue(0); bar.show(); _pump(app, 0.1)
        assert b.current()[0] == "busy" and b.current()[2] == 0.0
        bar.setValue(2); _pump(app, 0.1)
        assert b.current()[2] == pytest.approx(0.4) and (b.width(), b.height()) == size
        bar.hide(); _pump(app, 0.1)
        assert b.current()[0] == "done"
        for lang in ("ja", "zh", "tw", "ko", "de", "en"):                   # the frame holds in every language
            win._apply_language(lang); _pump(app, 0.1)
            assert (b.width(), b.height()) == size and b.isVisible(), lang
    finally:
        win._apply_language("en")
        _close(app, win)


# --------------------------------------------------------------------------- #
# the icon as a flip book while something runs (requirement 8, 2026-11-13)
# --------------------------------------------------------------------------- #
_ICO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studio_assets", "fullseye.ico")


def _img_of(pm):
    from PySide6 import QtGui
    return pm.toImage().convertToFormat(QtGui.QImage.Format_ARGB32)


def _changed(a, b):
    assert (a.width(), a.height()) == (b.width(), b.height()) and a.width() > 0
    return sum(1 for y in range(a.height()) for x in range(a.width()) if a.pixel(x, y) != b.pixel(x, y))


def test_flip_book_frames_are_the_icon_in_motion(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtCore, QtGui, QtWidgets
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    icon = QtGui.QIcon(_ICO)
    assert not icon.isNull()
    n = studio_panels.BRAND_FRAMES
    assert 8 <= n <= 12 and 800 <= studio_panels.BRAND_CYCLE_MS <= 1200            # 8..12 frames, about a second
    assert studio_panels.BRAND_MOTION in studio_panels.BRAND_MOTIONS and len(studio_panels.BRAND_MOTIONS) == 3
    base = icon.pixmap(QtCore.QSize(44, 44)).toImage().convertToFormat(QtGui.QImage.Format_ARGB32)
    for motion in studio_panels.BRAND_MOTIONS:
        frames = studio_panels.icon_frames(icon, 22, motion, n, 2)
        assert len(frames) == n and studio_panels.icon_frames(icon, 22, motion, n, 2) is frames     # made once
        imgs = [_img_of(f) for f in frames]
        assert len(imgs) == n                                                        # counted before all()
        assert len(frames) == n
        assert all(f.devicePixelRatio() == 2 and (im.width(), im.height()) == (44, 44) for f, im in zip(frames, imgs))
        steps = [_changed(imgs[k], imgs[(k + 1) % n]) for k in range(n)]
        assert min(steps) > 0, (motion, steps)                                       # every page differs from the next
        if motion != "sweep":
            assert _changed(imgs[0], base) == 0, motion                             # frame 0 IS the icon: no jump at the start
    turn = [_img_of(f) for f in studio_panels.icon_frames(icon, 22, "turn", n, 2)]
    moved = _changed(turn[0], turn[n // 2])                                           # 45 degrees: the cross has moved
    assert moved > 0.08 * 44 * 44, moved
    with pytest.raises(ValueError):
        studio_panels.icon_frames(icon, 22, "spin", n, 2)


def _brand_with_icon(monkeypatch, reduce=None):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtGui, QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    host = QtWidgets.QWidget()
    b = studio_panels.make_brand_status(host, "Fullseye Studio", QtGui.QIcon(_ICO), None, None, reduce=reduce)
    host.resize(400, 60); host.show()
    _pump(app, 0.05)
    return app, host, b


def _icon_part(b):
    from PySide6 import QtCore, QtGui
    return b.grab(QtCore.QRect(6, 1, 22, 22)).toImage().convertToFormat(QtGui.QImage.Format_ARGB32)


def test_the_flip_book_turns_only_while_a_job_is_shown_and_the_window_is_seen(monkeypatch):
    app, host, b = _brand_with_icon(monkeypatch)
    try:
        idle = _icon_part(b)
        b.show_after_ms = 0
        tok = b.begin("Running 2 / 5", total=5)
        _pump(app, 0.65)
        assert b.current()[0] == "busy" and b.frames_advanced >= 3, b.frames_advanced     # ~10 pages a second
        assert b.tick.interval() == studio_panels.BRAND_CYCLE_MS // studio_panels.BRAND_FRAMES
        pages = set()
        for _ in range(6):
            _pump(app, 0.11)
            pages.add(b.frame)
        assert len(pages) >= 3, pages
        b.frame = studio_panels.BRAND_FRAMES // 2
        assert _changed(_icon_part(b), idle) > 0                                     # the painted icon moves
        b.grab()
        assert b.shown_text.startswith("▶ Running 2 / 5")                       # the words stay beside it
        host.hide(); _pump(app, 0.05)
        before = b.frames_advanced
        _pump(app, 0.5)
        assert b.frames_advanced == before and b.tick.interval() == 1000            # nobody can see it: no page turns
        assert not b.can_be_seen()
        host.show(); _pump(app, 1.3)
        assert b.frames_advanced > before and b.can_be_seen()                     # back on screen: it moves again
        b.end(tok); _pump(app, 0.05)
        assert b.frame == 0
        b.flash_timer.stop(); b._flash_over()
        assert _changed(_icon_part(b), idle) == 0                                    # idle: the icon as it is
        _pump(app, 0.25)
        assert not b.tick.isActive()                                                 # no job: no timer at all
    finally:
        host.close()


def test_reduce_motion_keeps_the_first_page(monkeypatch):
    from PySide6 import QtGui
    app, host, b = _brand_with_icon(monkeypatch, reduce=lambda: True)
    try:
        b.show_after_ms = 0
        tok = b.begin("Indexing the search")                                       # unknown length: stripes
        _pump(app, 0.25)
        first = b.grab().toImage().convertToFormat(QtGui.QImage.Format_ARGB32)
        _pump(app, 0.45)
        later = b.grab().toImage().convertToFormat(QtGui.QImage.Format_ARGB32)
        assert b.reduced_motion and b.current()[0] == "busy"
        assert b.frames_advanced == 0 and b.frame == 0 and b.phase == 0             # neither the icon nor the stripes move
        assert _changed(first, later) == 0                                           # the whole corner is still
        b.end(tok)
        b.reduce = lambda: (_ for _ in ()).throw(RuntimeError("no settings"))      # a broken answer: motion allowed
        tok = b.begin("x"); _pump(app, 0.35)
        assert not b.reduced_motion and b.frames_advanced >= 1
        b.end(tok)
    finally:
        host.close()


def test_the_reduce_motion_setting_and_the_system_switch(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6 import QtCore
    s = QtCore.QSettings(str(tmp_path / "rm.ini"), QtCore.QSettings.IniFormat)
    system = studio_panels.system_reduces_motion()
    assert system in (True, False)
    assert studio_panels.reduce_motion(s) is system                                 # unset: the system decides
    assert studio_panels.reduce_motion(None) is system
    for value, want in (("1", True), ("true", True), ("0", False), ("off", False), ("maybe", system)):
        s.setValue(studio_panels.REDUCE_MOTION_KEY, value)
        assert studio_panels.reduce_motion(s) is want, value


def test_brand_wrap_reports_done_failed_and_raises_again(monkeypatch):
    app, host, b = _brand_with_icon(monkeypatch)
    try:
        b.show_after_ms = 0
        calls = []
        ok = studio_panels.brand_wrap(b, lambda p: (calls.append(p), True)[1], lambda p: "Opening %s" % p)
        assert ok("a.png") is True and calls == ["a.png"] and ok.brand_job
        _pump(app, 0.05)
        assert b.current() == ("done", "Opening a.png — Done")
        bad = studio_panels.brand_wrap(b, lambda p: False, lambda p: "Opening %s" % p)
        assert bad("b.png") is False
        _pump(app, 0.05)
        assert b.current() == ("failed", "Opening b.png — Failed")
        b.show_after_ms = 300                                                        # a short failure is still said
        b.flash_timer.stop(); b._flash_over()

        def boom(_p):
            raise OSError("disk")
        with pytest.raises(OSError):
            studio_panels.brand_wrap(b, boom, lambda p: "Saving %s" % p)("c.png")
        _pump(app, 0.05)
        assert b.current() == ("failed", "Saving c.png — Failed") and b.jobs == {}
        label_breaks = studio_panels.brand_wrap(b, lambda: 7, lambda: 1 / 0)          # a broken label never stops the work
        assert label_breaks() == 7
        judged = studio_panels.brand_wrap(b, lambda n: None, lambda n: n, ok=lambda r, n: n == "yes")
        b.flash_timer.stop(); b._flash_over()
        judged("no"); _pump(app, 0.05)
        assert b.current()[0] == "failed"
    finally:
        host.close()


def test_loading_a_sample_and_searching_are_jobs_of_the_corner_in_the_real_window(tmp_path, monkeypatch):
    import studio
    monkeypatch.setattr(studio, "ERROR_HOOK", lambda *a: None)                     # no modal in tests
    app, win = _launch(monkeypatch, tmp_path / "s.ini")
    try:
        b = win._brand
        assert isinstance(b.icon, __import__("PySide6.QtGui", fromlist=["QIcon"]).QIcon)   # drawn sharp at the screen's ratio
        assert win._load_image_path.brand_job and win._load_sample_image.brand_job
        assert win._search_ui["search_now"].brand_job
        b.show_after_ms = 0
        win._load_sample_image("coins"); _pump(app, 0.1)
        assert b.current() == ("done", "Loading sample: coins — Done"), b.current()
        b.flash_timer.stop(); b._flash_over()
        win._search_ui["search_now"]("blur"); _pump(app, 0.1)
        assert b.current() == ("done", "Searching: blur — Done"), b.current()
        b.flash_timer.stop(); b._flash_over()
        win._load_sample_image("no_such_sample_xyz"); _pump(app, 0.2)
        assert b.current()[0] == "failed" and "no_such_sample_xyz" in b.current()[1], b.current()
        act = win._actions["reduce_motion"]
        assert act.isCheckable() and act in win.findChildren(__import__("PySide6.QtGui", fromlist=["QAction"]).QAction)
        act.setChecked(True); _pump(app, 0.05)
        assert b.reduced_motion
        from PySide6 import QtCore
        assert QtCore.QSettings(str(tmp_path / "s.ini"), QtCore.QSettings.IniFormat).value(studio_panels.REDUCE_MOTION_KEY) == "1"
        act.setChecked(False)
        win._apply_language("ja"); _pump(app, 0.3)
        assert act.text() == "動きを減らす"
    finally:
        win._apply_language("en")
        _close(app, win)
