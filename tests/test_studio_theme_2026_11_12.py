"""Studio colour schemes and density (studio_theme.py; decision 2026-11-12).

Counts, not impressions: contrast of every role pair, no widget keeps an old colour after a
scheme switch, list rows = text + pad, clickable sizes and gaps, nothing clipped in 6 languages
at 1280x673, the setting survives a restart, a broken / all-hidden layout goes back to default.
"""
import os
import re

import pytest

import studio_theme


# --------------------------------------------------------------------------- #
# Qt-free: the tables
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("name", studio_theme.THEMES)
def test_every_role_pair_meets_its_contrast(name):
    bad = [r for r in studio_theme.contrast_report(name) if not r[4]]
    assert not bad, bad
    assert len(studio_theme.contrast_report(name)) == len(studio_theme.CONTRAST_PAIRS) >= 30


@pytest.mark.parametrize("name", studio_theme.THEMES)
def test_state_colours_are_not_the_click_colour_and_image_ground_is_neutral(name):
    p = studio_theme.PALETTES[name]
    assert p["accent"] not in {p["ok"], p["warn"], p["err"]}
    assert len({p["ok"], p["warn"], p["err"], p["off"]}) == 4
    assert studio_theme.chroma(p["surround"]) == 0
    assert set(p) >= set(studio_theme.ROLES) | set(studio_theme.SYNTAX_ROLES)


def test_bad_settings_fall_back_to_the_defaults():
    assert studio_theme.normalise_theme("banana") == studio_theme.DEFAULT_THEME
    assert studio_theme.normalise_density(None) == studio_theme.DEFAULT_DENSITY
    with pytest.raises(KeyError):
        studio_theme.PALETTES["instrument"]["no_such_role"]


def test_rows_are_text_plus_pad_and_never_below_20():
    assert studio_theme.row_height(16, "compact") == 20
    assert studio_theme.row_height(16, "standard") == 24
    assert studio_theme.row_height(10, "compact") == 20
    for lang in ("ja", "zh", "tw", "ko"):
        assert studio_theme.UI_FONTS[lang] != studio_theme.UI_FONTS["en"] or lang == "ja"
    assert "Microsoft YaHei UI" in studio_theme.font_stack("zh")
    assert "Microsoft JhengHei UI" in studio_theme.font_stack("tw")
    assert "Malgun Gothic" in studio_theme.font_stack("ko")


# --------------------------------------------------------------------------- #
# The live window (offscreen)
# --------------------------------------------------------------------------- #

@pytest.fixture()
def win(monkeypatch):
    if os.environ.get("FULLSEYE_TEST_REAL_WINDOW") != "1":       # =1: run on the real platform (local check)
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    import studio
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    studio._UI_LANG["code"] = "en"
    w, _model = studio.build_window()
    w.resize(1280, 673)
    w.show()
    app.processEvents()
    yield w
    studio_theme.set_current(studio_theme.DEFAULT_THEME, studio_theme.DEFAULT_DENSITY)
    studio._UI_LANG["code"] = "en"
    w.quiesce()
    w.close_guard = lambda: True
    w.close()
    app.processEvents()


_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


#: widgets that keep their own colours for now, each with its reason (2026-11-15, integration of the look branch
#: into integrate/studio-1-2-0): the Python mode's badge has its own contrast-tested table (studio_pymode.
#: BADGE_PALETTES) until B4 D37 puts the mode into the code's title band with the theme's pressed look.
OWN_COLOURS = {"program_mode_badge": "B4 D37 (1.2-A [統合])"}


def _all_sheet_hex(w):
    from PySide6 import QtWidgets
    found = []
    named = 0
    for x in [w] + w.findChildren(QtWidgets.QWidget):
        if x.objectName() in OWN_COLOURS:
            named += 1
            continue
        found += [h.lower() for h in _HEX.findall(x.styleSheet() or "")]
    assert named <= len(OWN_COLOURS)                                    # each exception is one widget
    return found


@pytest.mark.parametrize("target", ["panel", "instrument"])
def test_switching_the_scheme_reaches_every_widget(win, target):
    other = "instrument" if target == "panel" else "panel"
    win._apply_theme(theme=other, save=False)
    win._apply_theme(theme=target, save=False)
    allowed = {v.lower() for v in studio_theme.PALETTES[target].values()}
    left = [h for h in _all_sheet_hex(win) if h not in allowed]
    assert left == [], sorted(set(left))[:20]
    legacy = [h for h in _all_sheet_hex(win) if h in studio_theme.LEGACY_HEX
              and h not in allowed]
    assert legacy == []
    import studio

    def alive_in_win(obj):
        # the registries are process-wide (earlier test windows may be half-destroyed): judge only this window
        try:
            from PySide6 import QtWidgets
            parent = obj.document().parent() if hasattr(obj, "document") else obj
            while parent is not None and not isinstance(parent, QtWidgets.QWidget):
                parent = parent.parent()
            return parent is not None and (win is parent or win.isAncestorOf(parent))
        except RuntimeError:
            return False
    for hl in [h for h in list(studio._THEMED["highlighters"]) if alive_in_win(h)]:
        for f, role in hl._fmt_roles:
            assert f.foreground().color().name() == studio_theme.PALETTES[target][role]
    views = [v for v in list(studio._THEMED["surrounds"]) if alive_in_win(v)]
    assert views and all(v.backgroundBrush().color().name() == studio_theme.PALETTES[target]["surround"]
                         for v in views)


@pytest.mark.parametrize("level,pad", [("compact", 4), ("standard", 8)])
def test_list_rows_are_text_plus_pad(win, level, pad):
    from PySide6 import QtWidgets
    win._apply_theme(level=level, save=False)
    QtWidgets.QApplication.processEvents()
    ol = win._op_list
    assert ol.count() > 0
    h = ol.visualItemRect(ol.item(0)).height()
    text = ol.fontMetrics().height()
    assert h == text + pad, (h, text)                  # the op list: text + pad (its own rule since 1.1.1)
    sl = win._stage_list
    assert "height:%dpx" % max(text + pad, 36 + 4) in sl.styleSheet() or \
        "height:%dpx" % (36 + 4) in sl.styleSheet()


def test_clickable_sizes_and_gaps(win):
    from PySide6 import QtWidgets
    d = studio_theme.density()
    icon_only = [b for b in win.findChildren(QtWidgets.QToolButton) if b.property("iconOnly")]
    assert len(icon_only) >= 15
    for b in icon_only:
        assert min(b.width(), b.height()) >= 24, (b.toolTip(), b.size())
        if b.property("accent") and not b.property("keepSize"):
            assert b.height() >= 28
    for lay in win.findChildren(QtWidgets.QBoxLayout):
        ws = [lay.itemAt(i).widget() for i in range(lay.count())]
        if sum(isinstance(x, QtWidgets.QAbstractButton) for x in ws) >= 2 \
                and not isinstance(lay.parentWidget(), QtWidgets.QToolBar) \
                and lay.parentWidget().objectName() != "view_tools":
            assert lay.spacing() >= d["click_gap"], (lay.parentWidget(), lay.spacing())


@pytest.mark.parametrize("lang", ["en", "ja", "zh", "tw", "ko", "de"])
def test_nothing_clipped_at_1280x673(win, lang):
    """Every visible text button shows its whole text, no tool bar hides actions behind the
    overflow arrow, and the menu bar fits — in each of the six languages."""
    from PySide6 import QtWidgets
    win._apply_language(lang)
    win.resize(1280, 673)
    QtWidgets.QApplication.processEvents()
    real = QtWidgets.QApplication.platformName() != "offscreen"
    for b in win.findChildren(QtWidgets.QPushButton):
        if b.isVisible() and not b.visibleRegion().isEmpty() and b.text().strip():
            need = b.fontMetrics().horizontalAdvance(b.text().replace("&", "")) + 8
            assert b.width() >= need, (lang, b.text(), b.width(), need)
    if not real:
        # The offscreen platform has no system fonts: its fallback glyphs are about twice as wide
        # (work_modes sizeHint 1184 px offscreen vs 569 px on Windows, measured 2026-11-12, and the
        # same before this change), so bar widths are only judged on a real platform:
        #   FULLSEYE_TEST_REAL_WINDOW=1 py -3.11 -m pytest tests/test_studio_theme_2026_11_12.py
        return
    for tb in win.findChildren(QtWidgets.QToolBar):
        if not tb.isVisible():
            continue
        # an action pushed behind the overflow arrow has a widget that the tool bar hid
        hidden = [a.text() or a.toolTip() for a in tb.actions()
                  if a.isVisible() and not a.isSeparator() and tb.widgetForAction(a) is not None
                  and not tb.widgetForAction(a).isVisible()]
        assert hidden == [], (lang, tb.objectName(), hidden, tb.width(), tb.sizeHint().width())
    mb = win.menuBar()
    assert mb.sizeHint().width() <= win.width(), (lang, mb.sizeHint().width())


def test_scheme_and_density_survive_a_restart(win, monkeypatch, tmp_path):
    import studio
    from PySide6 import QtWidgets
    win._apply_theme(theme="panel", level="standard")          # saves
    s = studio._settings()
    assert s.value("ui/theme") == "panel" and s.value("ui/density") == "standard"
    studio_theme.set_current("instrument", "compact")
    w2, _m = studio.build_window()
    try:
        assert studio_theme.current_name() == "panel"
        assert studio_theme.current_density() == "standard"
        assert w2._theme_actions["panel"].isChecked() and w2._density_actions["standard"].isChecked()
    finally:
        w2.quiesce(); w2.close_guard = lambda: True; w2.close()
        QtWidgets.QApplication.processEvents()
    s.setValue("ui/theme", "banana")                             # broken value -> the default
    w3, _m = studio.build_window()
    try:
        assert studio_theme.current_name() == studio_theme.DEFAULT_THEME
    finally:
        w3.quiesce(); w3.close_guard = lambda: True; w3.close()


def test_entries_menu_palette_and_settings(win):
    acts = win._actions
    for k in ("theme_instrument", "theme_panel", "density_compact", "density_standard"):
        assert k in acts                                  # the command palette lists win._actions
    titles = [m.title() for m in win._theme_menus]
    assert titles == ["Colour scheme", "Density"]


def test_broken_or_all_hidden_layout_goes_back_to_default(win):
    import studio
    from PySide6 import QtWidgets
    assert studio.dock_layout_usable(win)
    assert win.restoreState(b"not a layout") is False             # Qt refuses it, layout unchanged
    assert studio.dock_layout_usable(win)
    for d in win._docks.values():
        d.hide()
    hidden = win.saveState()
    assert not studio.dock_layout_usable(win)
    assert win.restoreState(win._default_state)
    QtWidgets.QApplication.processEvents()
    assert studio.dock_layout_usable(win)
    assert win.restoreState(hidden) and not studio.dock_layout_usable(win)   # what the startup guard catches
