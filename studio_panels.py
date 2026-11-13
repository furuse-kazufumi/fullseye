"""Fullseye Studio — the panel bar, dock <-> separate window, and the saved panel layout.

Stage 2 of the look / layout work (decision 2026-11-12, STUDIO_AS_PYTHON_IDE.md):

* The image and the code are the principals. Every other panel (Operators, Pipeline ·
  Parameters, Variables & Objects, Display · Analysis, Stage in -> out, A / B) is brought in
  and put away from a thin **panel bar** on the left edge: one icon button per panel.
  Click = show / hide (a panel hidden behind a tab is raised first), right-click = separate
  window / dock / hide.
* A panel can live in the main window (docked, tabbed) or in a **separate, modeless window**
  (Qt's own floating QDockWidget). Its title band carries the two buttons for that. Esc closes
  a separate window; a window that was saved outside every screen is brought back.
* The arrangement is saved on close and restored on the next start (``geometry`` /
  ``windowState`` / ``layout_version`` in the Studio settings); "Reset panel layout" returns
  to the first-run arrangement: image + code.

Not here (later stages): pinning / auto-hide, drop guides, several Program tabs.

Qt is imported inside the functions, so the table and geometry helpers work without a display.
"""
from __future__ import annotations

import os

import studio_layout
import studio_theme

#: Saved dock states are reused only from the same layout version ("3" = before the panel bar).
LAYOUT_VERSION = "4"
#: Panels shown next to the image on the first run. The rest come from the panel bar.
PRINCIPAL = ("program",)
#: The work mode that describes the first-run arrangement (studio_layout.MODES).
INITIAL_MODE = "code"
#: Order of the buttons on the panel bar (every key of ``win._docks`` must be here — a test counts).
RAIL_ORDER = ("program", "operators", "pipeline", "variables", "display", "compare", "ab")
#: objectName of the bar (also its key in QMainWindow.saveState()).
RAIL_NAME = "panel_rail"
WORK_LAYOUT_KEY = "studio/work_mode_layout"

# English base strings (keys of studio_assets/i18n.json "strings").
S_BAR = "Panel bar"
S_HINT = "Click: show or hide. Right-click: separate window or dock."
S_FLOAT = "Separate window"
S_DOCK = "Dock in the main window"
S_HIDE = "Hide"
S_SHOW = "Show"
S_LAYOUT = "Layout"
S_RESET = "Reset panel layout"
S_CODE_LEFT = "Code on the left (tall)"
S_CODE_BOTTOM = "Code at the bottom (wide)"
S_DOCK_ALL = "Dock all panels"
S_MENU = "Panel menu"
S_MORE = "More tools"
S_REDUCE = "Reduce motion"
S_REDUCE_TIP = ("Keep the icon still while something runs "
                "(until changed here, Windows' own animation setting is followed)")
S_OPENING = "Opening %s"
S_SAMPLE = "Loading sample: %s"
S_SEARCHING = "Searching: %s"
S_ST_SHOWN = "Shown: %d / %d"
S_ST_STAGES = "Stages: %d"
S_ST_ERRORS = "Errors: %d"
S_ST_VARS = "Variables: %d"
S_STRIP = {"auto": "Tools and tabs: automatic (on the left when the panel is wide)",
           "top": "Tools and tabs: on top",
           "left": "Tools and tabs: on the left"}
STRINGS = (S_BAR, S_HINT, S_FLOAT, S_DOCK, S_HIDE, S_SHOW, S_LAYOUT, S_RESET, S_CODE_LEFT,
           S_CODE_BOTTOM, S_DOCK_ALL, S_MENU, S_MORE, S_REDUCE, S_REDUCE_TIP, S_OPENING, S_SAMPLE, S_SEARCHING, S_ST_SHOWN, S_ST_STAGES, S_ST_ERRORS, S_ST_VARS) + tuple(S_STRIP.values())

_QWIDGETSIZE_MAX = 16777215


# --------------------------------------------------------------------------- #
# Qt-free parts
# --------------------------------------------------------------------------- #
def rail_colours(theme=None):
    """Colours of the panel bar for one scheme, all from the palette table: a slightly conspicuous
    band (role ``rail``), the hovered button (``rail_hi``), the ground and mark of a shown panel,
    and the two icon colours (panel shown / hidden)."""
    p = studio_theme.PALETTES[studio_theme.normalise_theme(theme or studio_theme.current_name())]
    return {"band": p["rail"], "hover": p["rail_hi"], "open": p["bg0"], "mark": p["accent"],
            "line": p["line"], "icon_off": p["text"], "icon_on": p["accent_hi"]}


def rail_width(level=None):
    """Width of the bar: one square icon button + 2 px on each side."""
    d = studio_theme.DENSITY[studio_theme.normalise_density(level or studio_theme.current_density())]
    return d["icon_btn"] + 4


def rail_qss(theme=None, level=None):
    """Style sheet of the bar itself (set on the QToolBar; the window sheet stays as it is)."""
    c = rail_colours(theme)
    return (
        "QToolBar#%(n)s { background:%(band)s; border:none; border-right:1px solid %(line)s; "
        "spacing:2px; padding:2px 2px 2px 2px; }\n"
        "QToolBar#%(n)s QToolButton { background:transparent; border:none; border-left:2px solid transparent; "
        "border-radius:0px; padding:0px; margin:0px; }\n"
        "QToolBar#%(n)s QToolButton:hover { background:%(hover)s; }\n"
        "QToolBar#%(n)s QToolButton:checked { background:%(open)s; border-left:2px solid %(mark)s; }\n"
        "QToolBar#%(n)s QToolButton::menu-indicator { image:none; width:0px; }\n"
        "QToolBar#%(n)s::separator { background:%(line)s; height:1px; margin:3px 4px; }\n"
    ) % dict(c, n=RAIL_NAME)


def title_qss(theme=None):
    """Style sheet of a panel's title band (name on the left, the two buttons on the right)."""
    p = studio_theme.PALETTES[studio_theme.normalise_theme(theme or studio_theme.current_name())]
    return (
        "QWidget#dock_title { background:%(chrome)s; border:none; border-left:3px solid %(accent)s; "
        "border-bottom:1px solid %(line)s; }\n"
        "QWidget#dock_title QLabel { background:transparent; color:%(muted)s; font-size:11px; border:none; }\n"
        "QWidget#dock_title QToolButton { background:transparent; border:none; border-radius:2px; padding:0px; "
        "color:%(muted)s; font-size:13px; }\n"
        "QWidget#dock_title QToolButton::menu-indicator { image:none; width:0px; }\n"
        "QWidget#dock_title QToolButton:hover { background:%(hover)s; }\n"
    ) % p


def initial_state():
    """The first-run work-mode state: image + code (``INITIAL_MODE``), nothing overridden."""
    return studio_layout.apply_mode(studio_layout.LayoutState(), INITIAL_MODE)


def clamp_to_screens(rect, screens, grab=48):
    """Where a separate window (x, y, w, h) should sit so that its title band can be grabbed.

    Unchanged when at least ``grab`` px of the top band lie inside one of ``screens``
    (each (x, y, w, h)); otherwise moved into the first screen (and shrunk to fit it)."""
    x, y, w, h = (int(v) for v in rect)
    screens = [tuple(int(v) for v in s) for s in screens]
    if not screens:
        return (x, y, w, h)
    for sx, sy, sw, sh in screens:
        over = min(x + w, sx + sw) - max(x, sx)
        if over >= min(grab, w) and sy <= y <= sy + sh - grab:
            return (x, y, w, h)
    sx, sy, sw, sh = screens[0]
    w, h = min(w, sw), min(h, sh)
    return (min(max(x, sx), sx + sw - w), min(max(y, sy), sy + sh - h), w, h)


def persist_enabled():
    """Whether the window arrangement is saved / restored in this process.

    Not under the offscreen platform (tests build hundreds of windows and must not hand a layout
    to each other), unless ``FULLSEYE_STUDIO_PERSIST_LAYOUT=1`` asks for it (the layout tests,
    with their own settings file)."""
    return (os.environ.get("QT_QPA_PLATFORM") != "offscreen"
            or os.environ.get("FULLSEYE_STUDIO_PERSIST_LAYOUT") == "1")


# --------------------------------------------------------------------------- #
# icons (drawn; no asset files)
# --------------------------------------------------------------------------- #
_GLYPH_CACHE = {}


def _glyph(name, colour, px=16):
    """A line glyph on a 16 x 16 grid, drawn at 2x. ``name``: a panel key or float / dock / close / layout."""
    from PySide6 import QtCore, QtGui   # noqa: PLC0415
    key = (name, colour, px)
    hit = _GLYPH_CACHE.get(key)
    if hit is not None:
        return hit
    r = 2
    pm = QtGui.QPixmap(px * r, px * r)
    pm.setDevicePixelRatio(r)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    s = px / 16.0
    col = QtGui.QColor(colour)
    pen = QtGui.QPen(col); pen.setWidthF(1.4 * s)
    pen.setCapStyle(QtCore.Qt.RoundCap); pen.setJoinStyle(QtCore.Qt.RoundJoin)
    p.setPen(pen); p.setBrush(QtCore.Qt.NoBrush)

    def line(x1, y1, x2, y2):
        p.drawLine(QtCore.QPointF(x1 * s, y1 * s), QtCore.QPointF(x2 * s, y2 * s))

    def rect(x, y, w, h, fill=False):
        if fill:
            p.fillRect(QtCore.QRectF(x * s, y * s, w * s, h * s), col)
        else:
            p.drawRect(QtCore.QRectF(x * s, y * s, w * s, h * s))

    def dot(x, y, rad=1.7):
        p.setBrush(col); p.drawEllipse(QtCore.QPointF(x * s, y * s), rad * s, rad * s); p.setBrush(QtCore.Qt.NoBrush)

    def path(pts):
        p.drawPolyline(QtGui.QPolygonF([QtCore.QPointF(a * s, b * s) for a, b in pts]))

    if name == "program":                      # </>
        path([(5.5, 4.5), (2, 8), (5.5, 11.5)]); path([(10.5, 4.5), (14, 8), (10.5, 11.5)]); line(9, 3, 7, 13)
    elif name == "operators":                  # a list with a plus
        line(2, 4, 8.5, 4); line(2, 8, 8.5, 8); line(2, 12, 8.5, 12); line(12, 5.5, 12, 10.5); line(9.5, 8, 14.5, 8)
    elif name == "pipeline":                   # three sliders
        for y, x in ((4, 5), (8, 11), (12, 7)):
            line(2, y, 14, y); dot(x, y)
    elif name == "variables":                  # a small table
        rect(2, 3, 12, 10); line(2, 6.5, 14, 6.5); line(2, 9.8, 14, 9.8); line(7, 3, 7, 13)
    elif name == "display":                    # histogram
        line(2, 13.5, 14, 13.5)
        for x, h in ((3, 4), (6, 9), (9, 6), (12, 3)):
            rect(x - 0.9, 13 - h, 1.8, h, fill=True)
    elif name == "compare":                    # in -> out
        rect(1.5, 4.5, 4.5, 7); rect(10, 4.5, 4.5, 7); path([(7.2, 6.3), (8.8, 8), (7.2, 9.7)])
    elif name == "ab":                         # split view, left half filled
        rect(2, 3, 12, 10); rect(2, 3, 6, 10, fill=True)
    elif name == "layout":                     # window split into three
        rect(2, 2.5, 12, 11); line(6.5, 2.5, 6.5, 13.5); line(6.5, 8.5, 14, 8.5)
    elif name == "float":                      # two overlapping windows
        rect(5.5, 2.5, 8, 7); rect(2.5, 6.5, 8, 7)
    elif name == "dock":                       # a window with its band at the bottom
        rect(2.5, 2.5, 11, 11); rect(2.5, 9.5, 11, 4, fill=True)
    elif name == "close":
        line(4, 4, 12, 12); line(12, 4, 4, 12)
    else:
        p.end()
        raise KeyError("no glyph named %r" % (name,))
    p.end()
    _GLYPH_CACHE[key] = pm
    return pm


def _icon(name, off, on=None):
    from PySide6 import QtGui   # noqa: PLC0415
    ic = QtGui.QIcon()
    ic.addPixmap(_glyph(name, off), QtGui.QIcon.Normal, QtGui.QIcon.Off)
    ic.addPixmap(_glyph(name, on or off), QtGui.QIcon.Normal, QtGui.QIcon.On)
    return ic


# --------------------------------------------------------------------------- #
# the Qt side
# --------------------------------------------------------------------------- #
def _state(win):
    return win._panels


def _behind_a_tab(win, dock):
    """Docked, not hidden, but another tab of the same group is in front."""
    if dock.isHidden() or dock.isFloating() or not win.tabifiedDockWidgets(dock):
        return False
    return dock.visibleRegion().isEmpty()


def toggle_panel(win, key):
    """The panel-bar click: hidden -> shown and raised; behind a tab -> raised; in front -> hidden.
    Returns True when the panel is shown afterwards."""
    dock = win._docks[key]
    if dock.isHidden():
        dock.show(); dock.raise_()
        if dock.isFloating():
            _keep_on_screen(win, dock)
        return True
    if win.isVisible() and _behind_a_tab(win, dock):
        dock.raise_()
        return True
    dock.hide()
    return False


def toggle_float(win, key, floating=None):
    """Dock <-> separate (modeless) window for one panel; the panel is shown either way.
    Returns True when it is a separate window afterwards."""
    dock = win._docks[key]
    want = (not dock.isFloating()) if floating is None else bool(floating)
    dock.show()
    if want != dock.isFloating():
        dock.setFloating(want)
    if want:
        _keep_on_screen(win, dock)
        dock.raise_(); dock.activateWindow()
    else:
        dock.raise_()
    return dock.isFloating()


def _keep_on_screen(win, dock):
    from PySide6 import QtGui   # noqa: PLC0415
    screens = [(g.x(), g.y(), g.width(), g.height())
               for g in (s.availableGeometry() for s in QtGui.QGuiApplication.screens())]
    g = dock.frameGeometry()
    new = clamp_to_screens((g.x(), g.y(), g.width(), g.height()), screens)
    if new != (g.x(), g.y(), g.width(), g.height()):
        dock.move(new[0], new[1]); dock.resize(new[2], new[3])
        return True
    return False


def set_code_side(win, side):
    """Put the Program (code) panel on the left as a tall column, or at the bottom as a wide strip."""
    from PySide6 import QtCore   # noqa: PLC0415
    if side not in ("left", "bottom"):
        raise ValueError("side must be 'left' or 'bottom', not %r" % (side,))
    dock = win._docks["program"]
    dock.setFloating(False)
    win.addDockWidget(QtCore.Qt.LeftDockWidgetArea if side == "left" else QtCore.Qt.BottomDockWidgetArea, dock)
    dock.show()
    if side == "left":
        win.resizeDocks([dock], [max(360, int(win.width() * 0.46))], QtCore.Qt.Horizontal)
    else:
        win.resizeDocks([dock], [max(160, int(win.height() * 0.36))], QtCore.Qt.Vertical)
    return side


def _sync_modes(win):
    for mode_id, action in (getattr(win, "_work_mode_actions", None) or {}).items():
        action.setChecked(mode_id == win._layout_state.mode)


def sync(win):
    """Bar buttons, title-band buttons and the float menu follow the real state of every panel."""
    st = _state(win)
    for key, dock in win._docks.items():
        b = st["buttons"].get(key)
        if b is not None:
            b.setChecked(not dock.isHidden())
        a = st["float_actions"].get(key)
        if a is not None:
            a.setChecked(dock.isFloating())
        bar = st["titles"].get(key)
        if bar is not None:
            bar.follow()


def save_layout(win, settings):
    """Window geometry + the whole dock / tool-bar arrangement -> the Studio settings."""
    settings.setValue("geometry", win.saveGeometry())
    settings.setValue("windowState", win.saveState())
    settings.setValue("layout_version", LAYOUT_VERSION)


def restore_layout(win, settings, usable=None):
    """Apply the saved arrangement. True when the saved dock state is in use afterwards.

    Anything that cannot be used leaves the first-run arrangement in place: another layout
    version, a value that is not a byte array, a blob ``restoreState`` refuses, or a well-formed
    blob that hides every main panel (``usable(win)`` False)."""
    from PySide6 import QtCore   # noqa: PLC0415
    geo = settings.value("geometry")
    state = settings.value("windowState") if str(settings.value("layout_version")) == LAYOUT_VERSION else None
    if isinstance(geo, (QtCore.QByteArray, bytes)) and len(geo):
        win.restoreGeometry(geo)
    ok = False
    if isinstance(state, (QtCore.QByteArray, bytes)) and len(state):
        ok = bool(win.restoreState(state))
        if ok and usable is not None and not usable(win):
            ok = False
        if not ok:
            win.restoreState(win._default_state)
    after_restore(win)
    return ok


def after_restore(win):
    """The bar is always there, and no separate window is left outside every screen."""
    st = _state(win)
    st["rail"].show()
    relayout(win)
    for dock in win._docks.values():
        if dock.isFloating() and not dock.isHidden():
            _keep_on_screen(win, dock)
    sync(win)


def reset_layout(win, settings=None):
    """Back to the first-run arrangement: image + code, every other panel docked and hidden."""
    win._applying_layout = True
    try:
        if getattr(win, "_default_state", None) is not None:
            win.restoreState(win._default_state)
        for key, dock in win._docks.items():
            if key not in PRINCIPAL:
                dock.setFloating(False); dock.hide()
            else:
                dock.show()
    finally:
        win._applying_layout = False
    win._layout_state = initial_state()
    _sync_modes(win)
    if settings is not None:
        settings.setValue(WORK_LAYOUT_KEY, studio_layout.to_json(win._layout_state))
    first = getattr(win, "apply_first_layout", None)
    if first is not None and win.isVisible():
        first()
    after_restore(win)


def tighten(win):
    """A column in which nothing may grow spreads its spare height as gaps between the rows.
    Give that height to the column's text box (fixed height -> minimum height), or, when there is
    none, push the rows to the top. Returns the number of columns changed (each only once)."""
    from PySide6 import QtWidgets   # noqa: PLC0415
    grow = (QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Ignored)

    def grows(item):
        w = item.widget()
        if w is not None:
            if w.isHidden() or w.maximumHeight() <= w.minimumHeight():
                return False
            if w.sizePolicy().verticalPolicy() in grow:
                return True
            inner = w.layout()                   # a group box grows when something inside it does
            return (inner is not None and not isinstance(w, QtWidgets.QAbstractScrollArea)
                    and any(grows(inner.itemAt(i)) for i in range(inner.count())))
        if item.spacerItem() is not None:
            return _spacer_grows(item)
        lay = item.layout()
        return lay is not None and any(grows(lay.itemAt(i)) for i in range(lay.count()))

    changed = 0
    for dock in win._docks.values():
        root = dock.widget()
        if root is None:
            continue
        for box in root.findChildren(QtWidgets.QGroupBox)[::-1] + [root]:    # inner columns first
            lay = box.layout()
            if not isinstance(lay, QtWidgets.QVBoxLayout) or box.property("fsTight"):
                continue
            box.setProperty("fsTight", True)
            items = [lay.itemAt(i) for i in range(lay.count())]
            if not items or any(grows(it) for it in items):
                continue
            texts = [it.widget() for it in items
                     if isinstance(it.widget(), (QtWidgets.QPlainTextEdit, QtWidgets.QTextEdit, QtWidgets.QAbstractItemView))
                     and it.widget().minimumHeight() == it.widget().maximumHeight()]
            if texts:
                texts[-1].setMaximumHeight(_QWIDGETSIZE_MAX)
            elif box is root:
                lay.addStretch(1)
            else:                                # a group of fixed rows keeps its own height
                pol = box.sizePolicy()
                pol.setVerticalPolicy(QtWidgets.QSizePolicy.Maximum)
                box.setSizePolicy(pol)
            changed += 1
    bar = win.statusBar()                        # one text line + 8 px, whatever sits in it
    bar.setMaximumHeight(bar.fontMetrics().height() + 8)
    return changed


def _spacer_grows(item):
    from PySide6 import QtCore   # noqa: PLC0415
    return bool(item.spacerItem().expandingDirections() & QtCore.Qt.Vertical)


# --------------------------------------------------------------------------- #
# wide panels: tools and tabs go to the left edge (2026-11-13)
#
# A panel docked under the image is wide and low; a row of icon buttons or a tab bar across its
# top (or bottom) costs height it does not have. When a panel is WIDE, its icon row stands on the
# left as one column and the tabs of its tab group stand on the left as vertical tabs (Qt's own
# rotated text, read bottom to top — the user's choice, 2026-11-13). When it is tall or near
# square, everything is where it was. The user can fix the side: automatic / on top / on the left.
# --------------------------------------------------------------------------- #
#: width / height at which a panel counts as wide, and the lower value at which it stops (hysteresis:
#: between the two the side stays as it is, so dragging a splitter around the threshold does not flip it)
WIDE_ON, WIDE_OFF = 2.2, 1.6
STRIP_MODES = ("auto", "top", "left")
STRIP_MODE_KEY = "panels/strip_mode"


def normalise_strip_mode(value):
    """A strip mode from the settings: one of STRIP_MODES (anything else -> "auto")."""
    value = str(value or "").strip().lower()
    return value if value in STRIP_MODES else "auto"


def strip_side(width, height, current="top", mode="auto"):
    """Where a panel's icon row / tabs go: "left" (one column) or "top" (one row, as built).

    ``mode`` "top" / "left" is the user's fixed choice. Automatic: "left" from width / height >=
    WIDE_ON, back to "top" at <= WIDE_OFF, unchanged in between; a panel without a size keeps ``current``."""
    mode = normalise_strip_mode(mode)
    if mode != "auto":
        return mode
    current = current if current in ("top", "left") else "top"
    if width <= 0 or height <= 0:
        return current
    ratio = float(width) / float(height)
    if ratio >= WIDE_ON:
        return "left"
    if ratio <= WIDE_OFF:
        return "top"
    return current


def _find_strips(win):
    """Icon rows that sit directly under (or above) a list in a panel, re-housed so they can turn.

    Rule: in a vertical column, a list / tree / table followed (or preceded) by a row whose widgets
    are all icon-only tool buttons, at least two of them. The two items are moved into one box
    layout whose direction is switched later; nothing else in the column moves."""
    from PySide6 import QtWidgets   # noqa: PLC0415

    def icon_row(item):
        lay = item.layout() if item is not None else None
        if not isinstance(lay, QtWidgets.QHBoxLayout):
            return None
        ws = [lay.itemAt(i).widget() for i in range(lay.count()) if lay.itemAt(i).widget() is not None]
        if len(ws) >= 2 and all(isinstance(w, QtWidgets.QToolButton) and not w.text() for w in ws):
            return ws
        return None

    out = []
    for key, dock in win._docks.items():
        if key in PRINCIPAL or dock.widget() is None:      # the code panel belongs to the Program work
            continue
        root = dock.widget()
        for box in [root] + root.findChildren(QtWidgets.QGroupBox):
            col = box.layout()
            if not isinstance(col, QtWidgets.QVBoxLayout):
                continue
            i = 0
            while i < col.count() - 1:
                a, b = col.itemAt(i), col.itemAt(i + 1)
                view = a.widget() if isinstance(a.widget(), QtWidgets.QAbstractItemView) else None
                buttons = icon_row(b)
                below = True
                if view is None or buttons is None:
                    view = b.widget() if isinstance(b.widget(), QtWidgets.QAbstractItemView) else None
                    buttons = icon_row(a)
                    below = False
                if view is None or buttons is None:
                    i += 1
                    continue
                stretch = col.stretch(i if below else i + 1)
                row = (b if below else a).layout()
                col.takeAt(i + 1); col.takeAt(i)
                row.setParent(None)
                pair = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.BottomToTop if below else QtWidgets.QBoxLayout.TopToBottom)
                pair.setContentsMargins(0, 0, 0, 0); pair.setSpacing(col.spacing())
                pair.addLayout(row); pair.addWidget(view, 1)
                col.insertLayout(i, pair, max(1, stretch))
                more = QtWidgets.QToolButton(); more.setText("…"); more.setObjectName("strip_more")
                more.setProperty("keepSize", True); more.setPopupMode(QtWidgets.QToolButton.InstantPopup)
                more.setMenu(QtWidgets.QMenu(more)); more.hide()
                row.addWidget(more)

                def fill(menu=more.menu(), tools=buttons):
                    # built when it opens: the tools' enabled state and tool tips are those of that moment
                    menu.clear()
                    for b in tools:
                        if b.isHidden():
                            act = menu.addAction(b.icon(), (b.toolTip() or b.accessibleName() or "").split("\n")[0])
                            act.setEnabled(b.isEnabled())
                            act.triggered.connect(lambda _c=False, btn=b: btn.click())
                more.menu().aboutToShow.connect(fill)
                out.append({"key": key, "dock": dock, "pair": pair, "row": row, "view": view, "buttons": buttons,
                            "below": below, "more": more, "side": "top", "shown": len(buttons)})
                i += 1
    return out


def _turn_strip(entry, side):
    """One icon row to the left (a column) or back where it was built (a row). In a column that is
    too short for every button, the last ones go into the "…" menu."""
    from PySide6 import QtWidgets   # noqa: PLC0415
    d = studio_theme.density()
    row, pair, more = entry["row"], entry["pair"], entry["more"]
    buttons = entry["buttons"]
    if side == "left":
        pair.setDirection(QtWidgets.QBoxLayout.LeftToRight)
        row.setDirection(QtWidgets.QBoxLayout.TopToBottom)
        row.setSpacing(2)
        step = max(b.height() for b in buttons) + 2
        room = entry["view"].height() if entry["view"].height() > 0 else step * len(buttons)
        fit = len(buttons) if step * len(buttons) <= room else max(1, room // step - 1)
    else:
        pair.setDirection(QtWidgets.QBoxLayout.BottomToTop if entry["below"] else QtWidgets.QBoxLayout.TopToBottom)
        row.setDirection(QtWidgets.QBoxLayout.LeftToRight)
        row.setSpacing(d["click_gap"])
        fit = len(buttons)
    for n, b in enumerate(buttons):
        b.setVisible(n < fit)
    more.setFixedSize(d["icon_btn"], d["icon_btn"])
    more.setVisible(fit < len(buttons))
    entry["side"], entry["shown"] = side, fit


def relayout(win):
    """Every panel's icon row and every dock area's tab bar take the side their panel's shape asks
    for (or the user's fixed side). Safe to call at any time; does nothing before ``install``."""
    from PySide6 import QtCore, QtWidgets   # noqa: PLC0415
    st = getattr(win, "_panels", None)
    if st is None:
        return {}
    mode = st["strip_mode"]
    for entry in st["strips"]:
        dock = entry["dock"]
        if dock.isHidden() or dock.width() <= 0:
            continue
        side = strip_side(dock.width(), dock.height(), entry["side"], mode)
        if side != entry["side"] or side == "left":
            _turn_strip(entry, side)
    areas = {}
    for area in (QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.RightDockWidgetArea,
                 QtCore.Qt.TopDockWidgetArea, QtCore.Qt.BottomDockWidgetArea):
        docks = [d for d in win._docks.values()
                 if not d.isHidden() and not d.isFloating() and win.dockWidgetArea(d) == area
                 and win.tabifiedDockWidgets(d)]
        if not docks:
            continue
        front = max(docks, key=lambda d: d.width() * d.height() if not d.visibleRegion().isEmpty() else 0)
        now = "left" if win.tabPosition(area) == QtWidgets.QTabWidget.West else "top"
        side = strip_side(front.width(), front.height(), now, mode)
        if side != now:
            win.setTabPosition(area, QtWidgets.QTabWidget.West if side == "left" else QtWidgets.QTabWidget.North)
        areas[area] = side
    for bar in win.findChildren(QtWidgets.QTabBar):
        if bar.parentWidget() is win:                    # the tab bars of tabbed panels
            bar.setElideMode(QtCore.Qt.ElideNone)        # a name is never cut; too many tabs -> Qt's scroll arrows
            bar.setUsesScrollButtons(True)
            if st.get("tab_keys") is not None and not bar.property("fsTabKeys"):
                bar.setProperty("fsTabKeys", True)
                bar.installEventFilter(st["tab_keys"])
    st["tab_sides"] = areas
    return areas


def set_strip_mode(win, mode, settings=None):
    """The user's choice for tools and tabs: "auto", "top" or "left" (saved when ``settings`` is given)."""
    st = _state(win)
    st["strip_mode"] = normalise_strip_mode(mode)
    if settings is not None:
        settings.setValue(STRIP_MODE_KEY, st["strip_mode"])
    for m, action in st["strip_actions"].items():
        action.setChecked(m == st["strip_mode"])
    relayout(win)
    return st["strip_mode"]


# --------------------------------------------------------------------------- #
# the brand corner doubles as the progress read-out (user, 2026-11-13)
#
# Idle: icon + "Fullseye Studio", as before. While something runs: the same frame, its ground a
# band that grows from the left (known total) or moving stripes (unknown), its text what is being
# done. Then a short "done" / failure text, and the name again. The frame never changes size.
# One door: begin(text, total=None) -> token / update(token, done=None, text=None) /
# end(token, ok=True, text=None); safe from any thread. Division of labour with the status bar at
# the bottom: here = what is running and how far; there = results and the longer sentences.
# --------------------------------------------------------------------------- #
BRAND_SHOW_AFTER_MS = 300        # shorter jobs never show (no flicker)
BRAND_DONE_MS = 800              # how long "done" / the failure text stays
BRAND_STALE_MS = 120000          # a job nobody updated or ended for this long is dropped (and logged)


# --------------------------------------------------------------------------- #
# the icon in motion while something runs: a flip book (user, 2026-11-13)
#
# The Fullseye icon is a reticle: a cream centre, an orange ring, a teal ring, navy outlines and a
# navy cross. Three motions that belong to that shape were drawn from the icon itself and compared
# (stage-2 report: brand_motion_compare.png and the numbers beside it):
#   "turn"    the cross turns a quarter of a circle per cycle; the rings are round, so only the cross
#             moves (aiming / scanning);
#   "breathe" the cream centre widens and narrows (a pupil, an aperture stopping down);
#   "sweep"   a light sector runs round the teal ring (a radar, a scan line).
# Default "turn": its frame 0 is the icon pixel for pixel (no jump when a job begins), the moving part
# is the thin cross, so the corner stays calm next to the text, and at 22 px it plainly moves.
# Frames are made once per icon / size / motion and kept; the timer runs at BRAND_FRAMES per
# BRAND_CYCLE_MS only while a job is shown and the window can be seen; "reduce motion" (the Studio
# setting, else Windows' own "show animations" switch) keeps frame 0 and the band does not move.
# --------------------------------------------------------------------------- #
#: colours measured on studio_assets/fullseye_256.png; "light" is the sweep's lit teal
ICON_COLOURS = {"navy": "#0d2039", "teal": "#14b8a6", "orange": "#f5a524", "cream": "#fff3d6", "light": "#a8f2e4"}
#: radii on the same icon, as fractions of the outer radius: cream / navy / orange / navy / teal / rim
ICON_RADII = (0.20, 0.34, 0.56, 0.68, 0.92, 1.0)
BRAND_MOTIONS = ("turn", "breathe", "sweep")
BRAND_MOTION = "turn"
BRAND_FRAMES = 10                # frames per cycle
BRAND_CYCLE_MS = 1000            # one cycle; the flip-book timer ticks every BRAND_CYCLE_MS / BRAND_FRAMES
REDUCE_MOTION_KEY = "ui/reduce_motion"      # "1" / "0"; unset = follow the system
_FRAME_CACHE = {}


def _icon_image(source, side):
    """``source`` (a QIcon, QPixmap, QImage or a file path) as a ``side`` x ``side`` ARGB image."""
    from PySide6 import QtCore, QtGui   # noqa: PLC0415
    if isinstance(source, str):
        img = QtGui.QImage(source)
    elif isinstance(source, QtGui.QIcon):
        img = source.pixmap(QtCore.QSize(side, side)).toImage()
    elif isinstance(source, QtGui.QPixmap):
        img = source.toImage()
    else:
        img = QtGui.QImage(source)
    if img.isNull():
        raise ValueError("no icon image to animate")
    img = img.convertToFormat(QtGui.QImage.Format_ARGB32)
    if img.width() != side or img.height() != side:
        img = img.scaled(side, side, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
    img.setDevicePixelRatio(1.0)
    return img


def icon_frames(source, px=22, motion=BRAND_MOTION, n=BRAND_FRAMES, dpr=2):
    """The flip book: ``n`` QPixmaps of ``px`` logical pixels (drawn at ``dpr``) made from the icon.

    Frame k shows phase k / n of one cycle. "turn" and "breathe" leave frame 0 equal to the icon;
    "sweep" lights a sector from the first frame on. Kept per (icon, px, motion, n, dpr)."""
    from PySide6 import QtCore, QtGui   # noqa: PLC0415
    import math   # noqa: PLC0415
    if motion not in BRAND_MOTIONS:
        raise ValueError("motion must be one of %s, not %r" % (BRAND_MOTIONS, motion))
    n, dpr = max(1, int(n)), max(1, int(round(float(dpr))))
    side = int(px) * dpr
    ident = source if isinstance(source, str) else source.cacheKey()
    key = (ident, int(px), motion, n, dpr)
    hit = _FRAME_CACHE.get(key)
    if hit is not None:
        return hit
    base = _icon_image(source, side)
    c = side / 2.0
    R = side / 2.0
    col = {name: QtGui.QColor(v) for name, v in ICON_COLOURS.items()}
    frames = []
    for k in range(n):
        t = k / float(n)
        out = QtGui.QImage(base) if k == 0 or motion == "sweep" else QtGui.QImage(side, side, QtGui.QImage.Format_ARGB32)
        if motion == "turn" and k:
            out.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(out)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            p.translate(c, c); p.rotate(90.0 * t); p.translate(-c, -c)     # the cross is four-fold: 90 degrees = a cycle
            p.drawImage(0, 0, base)
            p.end()
        elif motion == "breathe" and k:
            out = QtGui.QImage(base)
            pupil = ICON_RADII[0] + 0.10 * (0.5 - 0.5 * math.cos(2.0 * math.pi * t))
            p = QtGui.QPainter(out)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(col["navy"]); p.drawEllipse(QtCore.QPointF(c, c), (pupil + 0.14) * R, (pupil + 0.14) * R)
            p.setBrush(col["cream"]); p.drawEllipse(QtCore.QPointF(c, c), pupil * R, pupil * R)
            p.end()
        elif motion == "sweep":
            # teal pixels inside the teal ring get lighter in a sector that trails the head (clockwise from the top)
            head = 360.0 * t
            teal, light = col["teal"], col["light"]
            for y in range(side):
                for x in range(side):
                    dx, dy = x + 0.5 - c, y + 0.5 - c
                    r = (dx * dx + dy * dy) ** 0.5 / R
                    if not ICON_RADII[3] < r < ICON_RADII[4]:
                        continue
                    px_ = out.pixelColor(x, y)
                    if abs(px_.red() - teal.red()) + abs(px_.green() - teal.green()) + abs(px_.blue() - teal.blue()) > 90:
                        continue                                     # the navy cross and outlines stay
                    ang = math.degrees(math.atan2(dx, -dy)) % 360.0  # 0 at the top, clockwise
                    behind = (head - ang) % 360.0
                    w = max(0.0, 1.0 - behind / 80.0) * 0.9
                    if w > 0:
                        px_.setRed(int(px_.red() + (light.red() - px_.red()) * w))
                        px_.setGreen(int(px_.green() + (light.green() - px_.green()) * w))
                        px_.setBlue(int(px_.blue() + (light.blue() - px_.blue()) * w))
                        out.setPixelColor(x, y, px_)
        pm = QtGui.QPixmap.fromImage(out)
        pm.setDevicePixelRatio(dpr)
        frames.append(pm)
    _FRAME_CACHE[key] = frames
    return frames


def system_reduces_motion():
    """True when the operating system asks for fewer animations (Windows: "Show animations in
    Windows" off, read with SystemParametersInfo SPI_GETCLIENTAREAANIMATION; read only). False
    elsewhere or when it cannot be read."""
    if os.name != "nt":
        return False
    try:
        import ctypes   # noqa: PLC0415
        value = ctypes.c_int(1)
        ok = ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(value), 0)
        return bool(ok) and not value.value
    except Exception:                            # noqa: BLE001 - no answer = animations allowed
        return False


def reduce_motion(settings=None):
    """The Studio's own "reduce motion" setting when it is set ("1" / "0"), else the system's."""
    try:
        value = settings.value(REDUCE_MOTION_KEY) if settings is not None else None
    except Exception:                            # noqa: BLE001 - a broken store: follow the system
        value = None
    word = str(value).strip().lower() if value is not None else ""
    if word in ("1", "true", "on", "yes"):
        return True
    if word in ("0", "false", "off", "no"):
        return False
    return system_reduces_motion()


def make_brand_status(parent, name="Fullseye Studio", icon=None, log=None, tr=None, reduce=None):
    """Build the brand / progress widget (a QWidget with ``begin`` / ``update_job`` / ``end``;
    ``update`` is QWidget's own repaint, so the middle call is ``update_job``).

    ``icon``: a QIcon (drawn sharp at the screen's pixel ratio), a QPixmap, or None. While a job is
    shown the icon is a flip book (``icon_frames``). ``reduce``: a callable that says whether motion
    is to be reduced (asked when a job begins; None = never)."""
    from PySide6 import QtCore, QtGui, QtWidgets   # noqa: PLC0415
    import itertools   # noqa: PLC0415
    import time as _time   # noqa: PLC0415

    class BrandStatus(QtWidgets.QWidget):
        _call = QtCore.Signal(str, object)           # (what, args): hops to the GUI thread when needed

        def __init__(self):
            super().__init__(parent)
            self.setObjectName("brand_status")
            self.name, self.icon, self.log, self.tr = name, icon, log, tr or (lambda s: s)
            self.reduce = reduce
            self.jobs = {}                           # token -> {"text", "total", "done", "t0", "seen"}
            self.tokens = itertools.count(1)
            self.flash = None                        # (text, ok) shown for BRAND_DONE_MS after the last job
            self.phase = 0
            self.frame = 0                           # flip-book frame while busy (0 = the icon as it is)
            self.frames_advanced = 0                 # how many times the flip book turned a page (tests, report)
            self.motion = BRAND_MOTION
            self.reduced_motion = False
            self.show_after_ms, self.done_ms, self.stale_ms = BRAND_SHOW_AFTER_MS, BRAND_DONE_MS, BRAND_STALE_MS
            self._call.connect(self._on_call)
            self.tick = QtCore.QTimer(self); self.tick.setInterval(BRAND_CYCLE_MS // BRAND_FRAMES)
            self.tick.timeout.connect(self._on_tick)
            self.flash_timer = QtCore.QTimer(self); self.flash_timer.setSingleShot(True)
            self.flash_timer.timeout.connect(self._flash_over)
            f = self.font(); f.setPixelSize(15); f.setWeight(QtGui.QFont.ExtraBold)
            self.name_font = f
            g = self.font(); g.setPixelSize(12)
            self.job_font = g
            w = QtGui.QFontMetrics(f).horizontalAdvance(name) + (30 if icon is not None else 0) + 20
            self.setFixedSize(max(w, 210), 24)       # the frame is the same idle and busy
            self.setAccessibleName(name)

        # ---- the door (any thread) ---------------------------------------- #
        def begin(self, text, total=None):
            token = next(self.tokens)
            self._call.emit("begin", (token, str(text), total, _time.monotonic()))
            return token

        def update_job(self, token, done=None, text=None):
            self._call.emit("update", (token, done, text))

        def end(self, token, ok=True, text=None):
            self._call.emit("end", (token, bool(ok), text))

        # ---- GUI thread ----------------------------------------------------- #
        def _on_call(self, what, args):
            now = _time.monotonic()
            if what == "begin":
                token, text, total, t0 = args
                self.jobs[token] = {"text": text, "total": total, "done": 0, "t0": t0, "seen": now}
                self.flash = None
                try:
                    self.reduced_motion = bool(self.reduce()) if self.reduce is not None else False
                except Exception:                    # noqa: BLE001 - no answer = motion allowed
                    self.reduced_motion = False
                self.tick.start()
            elif what == "update":
                token, done, text = args
                job = self.jobs.get(token)
                if job is None:
                    return
                if done is not None:
                    job["done"] = done
                if text is not None:
                    job["text"] = str(text)
                job["seen"] = now
            elif what == "end":
                token, ok, text = args
                job = self.jobs.pop(token, None)
                if job is None:
                    return
                shown = (now - job["t0"]) * 1000.0 >= self.show_after_ms
                if not self.jobs and (shown or not ok):          # a failure is always said, however short
                    self.flash = (text or (self.tr("Done") if ok else self.tr("Failed")), ok)
                    self.flash_timer.start(self.done_ms)
                if not self.jobs:
                    self.frame = 0
            self._sync()

        def can_be_seen(self):
            """The corner is on a screen: shown, its window not minimised and exposed."""
            if not self.isVisible():
                return False
            top = self.window()
            if top.isMinimized():
                return False
            handle = top.windowHandle()
            return handle is None or handle.isExposed()

        def _on_tick(self):
            now = _time.monotonic()
            for token, job in list(self.jobs.items()):
                if (now - job["seen"]) * 1000.0 > self.stale_ms:     # the safety valve: end() never came
                    self.jobs.pop(token, None)
                    if self.log is not None:
                        self.log("progress job was never ended: %r" % (job["text"],), "dropped after %d ms" % self.stale_ms)
            seen = self.can_be_seen()
            busy = self.current()[0] == "busy"
            if seen and busy and not self.reduced_motion:            # nothing moves where nobody can see it
                self.phase = (self.phase + 3) % 24
                self.frame = (self.frame + 1) % BRAND_FRAMES
                self.frames_advanced += 1
            # hidden: one look a second (the stale-job valve still works), no painting
            self.tick.setInterval(BRAND_CYCLE_MS // BRAND_FRAMES if seen else 1000)
            if not self.jobs:
                self.tick.stop()
                self.frame = 0
            if seen:
                self._sync()

        def _flash_over(self):
            self.flash = None
            self._sync()

        def current(self):
            """What the frame shows now: ("idle", name) / ("busy", text, fraction or None, others) / ("done" | "failed", text)."""
            now = _time.monotonic()
            live = [(t, j) for t, j in self.jobs.items() if (now - j["t0"]) * 1000.0 >= self.show_after_ms]
            if live:
                token, job = max(live)                           # the newest job speaks; the others are counted
                frac = None
                if job["total"]:
                    frac = max(0.0, min(1.0, float(job["done"]) / float(job["total"])))
                return ("busy", job["text"], frac, len(live) - 1)
            if self.flash is not None:
                return ("done" if self.flash[1] else "failed", self.flash[0])
            return ("idle", self.name)

        def _sync(self):
            cur = self.current()
            if cur[0] == "busy":
                text = cur[1] + (" (+%d)" % cur[3] if cur[3] else "")
                pct = "" if cur[2] is None else " %d%%" % int(round(cur[2] * 100))
                self.setToolTip(text); self.setAccessibleDescription(text + pct)
            elif cur[0] == "idle":
                self.setToolTip(""); self.setAccessibleDescription("")
            else:
                self.setToolTip(cur[1]); self.setAccessibleDescription(cur[1])
            self.update()

        def icon_frame(self, k=0):
            """Frame ``k`` of the flip book at this screen's pixel ratio (None without an icon)."""
            if self.icon is None:
                return None
            dpr = max(1, int(round(self.devicePixelRatioF() + 0.49)))
            return icon_frames(self.icon, 22, self.motion, BRAND_FRAMES, dpr)[k % BRAND_FRAMES]

        def paintEvent(self, _ev):
            p = studio_theme.PALETTES[studio_theme.current_name()]
            cur = self.current()
            painter = QtGui.QPainter(self)
            r = self.rect()
            x = 6
            if cur[0] == "busy":
                band = QtGui.QColor(p["rail_hi"])                # the text colour reads on it and on the chrome (4.5 +)
                if cur[2] is not None:
                    painter.fillRect(QtCore.QRect(0, 0, int(round(r.width() * cur[2])), r.height()), band)
                else:                                            # unknown length: stripes that move
                    painter.setClipRect(r)
                    for sx in range(-24 + self.phase, r.width() + 24, 24):
                        painter.fillRect(QtCore.QRect(sx, 0, 12, r.height()), band)
                    painter.setClipping(False)
                painter.fillRect(QtCore.QRect(0, r.height() - 2, r.width(), 2), QtGui.QColor(p["line"]))
            elif cur[0] == "failed":
                painter.fillRect(r, QtGui.QColor(p["warn_bg"]))
            pm = self.icon_frame(self.frame if cur[0] == "busy" else 0)
            if pm is not None:                                   # the icon stays; while busy it is the flip book
                painter.drawPixmap(QtCore.QRect(6, (r.height() - 22) // 2, 22, 22), pm)
                x = 34
            if cur[0] == "idle":
                painter.setFont(self.name_font); painter.setPen(QtGui.QColor(p["brand"]))
                text = cur[1]
            else:
                painter.setFont(self.job_font); painter.setPen(QtGui.QColor(p["text"]))
                mark = {"busy": "▶ ", "done": "■ ", "failed": "▲ "}[cur[0]]     # shape + word, not colour alone
                text = mark + cur[1]
            fm = painter.fontMetrics()
            more = " (+%d)" % cur[3] if cur[0] == "busy" and cur[3] else ""     # the count of other jobs is never cut
            text = fm.elidedText(text, QtCore.Qt.ElideRight, r.width() - x - 6 - fm.horizontalAdvance(more)) + more
            self.shown_text = text
            painter.drawText(QtCore.QRect(x, 0, r.width() - x - 6, r.height()), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text)
            painter.end()

    return BrandStatus()


def brand_wrap(brand, fn, text_of, ok=None):
    """``fn`` run as one job of the brand corner: begin before, end after. The job counts as done when
    ``fn`` returns anything but False (or when ``ok(result, *args, **kwargs)`` says so); an exception
    ends it as failed and is raised again. Work on the GUI thread cannot be painted while it runs: the
    corner then says the outcome afterwards — when it took BRAND_SHOW_AFTER_MS or more, or failed."""
    import functools   # noqa: PLC0415

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            text = str(text_of(*args, **kwargs) or "")
        except Exception:                            # noqa: BLE001 - a label must never stop the work
            text = ""
        token = brand.begin(text)
        try:
            result = fn(*args, **kwargs)
        except BaseException:
            brand.end(token, False, ("%s — %s" % (text, brand.tr("Failed"))) if text else None)
            raise
        try:
            good = (result is not False) if ok is None else bool(ok(result, *args, **kwargs))
        except Exception:                            # noqa: BLE001
            good = True
        brand.end(token, good, ("%s — %s" % (text, brand.tr("Done" if good else "Failed"))) if text else None)
        return result
    wrapper.brand_job = True
    return wrapper


def reduce_motion_action(win, menu, settings, tr):
    """The "Reduce motion" switch (checkable, in ``menu``). Checked at start = what is in effect now
    (the Studio setting, else the system's); a change is saved (``REDUCE_MOTION_KEY``) and reaches the
    brand corner at once. Returns the action (also ``win._reduce_motion_action``)."""
    from PySide6 import QtGui   # noqa: PLC0415
    act = QtGui.QAction(tr(S_REDUCE), win)
    act.setObjectName("reduce_motion")
    act.setCheckable(True)
    try:
        act.setChecked(reduce_motion(settings()))
    except Exception:                            # noqa: BLE001 - a broken store: motion allowed
        act.setChecked(False)
    act.setToolTip(tr(S_REDUCE_TIP)); act.setStatusTip(tr(S_REDUCE_TIP))

    def flip(on):
        try:
            settings().setValue(REDUCE_MOTION_KEY, "1" if on else "0")
        except Exception:                        # noqa: BLE001 - the switch still works for this session
            pass
        brand = getattr(win, "_brand", None)
        if brand is not None:
            brand.reduced_motion = bool(on)
            if on:
                brand.frame = 0
            brand.update()
    act.toggled.connect(flip)
    menu.addAction(act)
    win._reduce_motion_action = act
    return act


def follow_progress(brand, bar, label=None):
    """Let the brand corner follow an existing QProgressBar (shown = a job begins, value = how far,
    hidden = it ended) and, when given, the label that says what is running. The code that drives
    the bar is not touched. Returns the filter (keep a reference)."""
    from PySide6 import QtCore   # noqa: PLC0415

    class Follow(QtCore.QObject):
        def __init__(self):
            super().__init__(bar)
            self.token = None

        def text(self):
            return label.text() if label is not None else ""

        def eventFilter(self, obj, ev):
            if ev.type() == QtCore.QEvent.Show and self.token is None:
                self.token = brand.begin(self.text(), bar.maximum() or None)
            elif ev.type() == QtCore.QEvent.Hide and self.token is not None:
                token, self.token = self.token, None
                brand.end(token, True, self.text() or None)
            return False

        def moved(self, _value=None):
            if self.token is not None:
                job = brand.jobs.get(self.token)
                if job is not None:
                    job["total"] = bar.maximum() or None
                brand.update_job(self.token, done=bar.value(), text=self.text() or None)

    f = Follow()
    bar.installEventFilter(f)
    bar.valueChanged.connect(f.moved)
    return f


def button_action(win, button):
    """The ONE QAction of a panel's own button that has none (a tool or push button made with a
    ``clicked`` handler). Triggering it presses the real button, so the function, its checks and its
    undo step are the button's. Its name (the button's text, else the first line of its tool tip),
    tool tip, icon and enabled state are copied from the button whenever a menu shows it
    (``sync_button_actions``), so they cannot disagree. Asked again for the same button it returns
    the same action: one function, one QAction."""
    from PySide6 import QtGui   # noqa: PLC0415
    st = _state(win)
    cache = st.setdefault("button_actions", {})
    act = cache.get(button)
    if act is None:
        act = QtGui.QAction(win)
        act.setObjectName("panel_button_action")
        act.triggered.connect(lambda _c=False, b=button: b.click() if b.isEnabled() else None)
        cache[button] = act
        st.setdefault("button_of", {})[act] = button
    _copy_button(button, act)
    return act


#: where a long tool tip is cut to make a menu entry (the whole tip stays the entry's tool tip)
_NAME_CUTS = (" \u2014 ", ": ", "; ", " (", " \u2192 ", " \u2190 ", "\uff08", "\uff1a", "\u3002", "(")


def short_name(tip, limit=32):
    """A menu entry's name from a button's tool tip: its first line, cut before the first explanation
    (" \u2014 ", ": ", "; ", " (", an arrow, the Japanese full stop ...) when longer than ``limit``."""
    import unicodedata   # noqa: PLC0415
    line = (tip or "").strip().split("\n")[0].strip()
    if sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in line) <= limit:   # columns, not characters
        return line
    cuts = [line.find(c) for c in _NAME_CUTS if line.find(c) >= 2]
    return line[:min(cuts)].strip() if cuts else line


def _copy_button(button, act):
    text = (button.text() or "").replace("&", "").strip()
    tip = (button.toolTip() or "").strip()
    if not text or text in ("\u2026", "+", "\u2212", "-"):           # an icon / a sign: the tool tip names it
        text = short_name(tip) or button.accessibleName() or text
    act.setText(text)
    act.setToolTip(tip or text)
    act.setStatusTip(tip.split("\n")[0] if tip else text)
    if button.property("accent"):              # drawn for the accent ground: no icon in a menu (it would vanish)
        from PySide6 import QtGui   # noqa: PLC0415
        act.setIcon(QtGui.QIcon())
    else:
        act.setIcon(button.icon())
    act.setEnabled(button.isEnabled())


def sync_button_actions(win):
    """Copy name / tip / icon / enabled state from every button into its action (a menu is about to
    show them; the language or the state may have changed). Returns the number of actions synced."""
    n = 0
    for act, button in list((_state(win).get("button_of") or {}).items()):
        try:
            _copy_button(button, act)
            n += 1
        except RuntimeError:                     # the button was destroyed with its panel
            pass
    return n


#: How many of its own functions a panel's menu offers (user, 2026-11-13: "3 to 8")
MENU_OWN_MIN, MENU_OWN_MAX = 3, 8


def register_panel(win, key, status=None, actions=None):
    """What one panel shows in its title band and offers in its menu button — the ONE place a panel
    (also one added later: console, parameters, call stack) says so.

    ``status``: a list of ``{"id": str, "text": callable -> str, "tip": str, "priority": int}``. Each
    is a small read-out to the right of the name; ``text()`` is asked four times a second while the
    panel is shown ("" hides the item). When the band is too narrow, items with the LOWEST priority
    go first (whole items, never cut text); what was dropped is listed at the top of the menu.
    ``actions``: QActions (the same objects the panel's buttons / the main menu use, so name, key
    and enabled state cannot disagree); ``None`` in the list is a separator. Calling again replaces."""
    st = _state(win)
    if key not in win._docks:
        raise KeyError("no panel named %r" % (key,))
    bar = st["titles"][key]
    bar.set_registration(list(status or []), list(actions or []))
    return bar


def _default_registrations(win):
    """The panels that exist today. Values are read from the live widgets; a missing one is skipped."""
    tr = lambda s: _state(win)["tr"](s)   # noqa: E731 - the language can change after registration
    acts = getattr(win, "_actions", None) or {}

    def pick(*names):
        return [acts[n] for n in names if n in acts]

    def btn(key, *names):
        """The panel's own buttons that have no QAction (``win._panel_buttons``, set by studio.py)."""
        own = (getattr(win, "_panel_buttons", None) or {}).get(key) or {}
        return [button_action(win, own[n]) for n in names if own.get(n) is not None]

    def shown_ops():
        ol = getattr(win, "_op_list", None)
        if ol is None or ol.count() == 0:
            return ""
        return tr(S_ST_SHOWN) % (sum(1 for i in range(ol.count()) if not ol.item(i).isHidden()), ol.count())

    def stages():
        sl = getattr(win, "_stage_list", None)
        return tr(S_ST_STAGES) % sl.count() if sl is not None else ""

    def errors():
        state = getattr(win, "_state", None) or {}
        n = len(state.get("errors") or []) + len(state.get("structured_errors") or [])
        return ("\u2715 " + tr(S_ST_ERRORS) % n) if n else ""

    def variables():
        lst = (getattr(win, "_variables", None) or {}).get("list")
        return tr(S_ST_VARS) % lst.count() if lst is not None else ""

    register_panel(win, "program", [],
                   btn("program", "run", "continue", "step", "reset") + [None]
                   + btn("program", "apply", "sync") + [None] + pick("export", "verify_exported"))
    register_panel(win, "operators", [{"id": "shown", "text": shown_ops, "priority": 1}],
                   pick("focus_search", "op_reference", "samples"))
    register_panel(win, "pipeline", [{"id": "errors", "text": errors, "priority": 2},
                                     {"id": "stages", "text": stages, "priority": 1}],
                   pick("run_all", "step", "reset") + [None]
                   + pick("remove", "move_up", "move_down", "duplicate_stage", "bypass"))
    register_panel(win, "variables", [{"id": "count", "text": variables, "priority": 1}],
                   btn("variables", "display_new", "display_here") + pick("viewer_3d", "feature_inspection")
                   + [None] + btn("variables", "watch_remove"))
    register_panel(win, "display", [], pick("fit", "actual_size", "zoom_in", "zoom_out", "surface_3d"))
    register_panel(win, "compare", [], pick("step", "reset") + [None] + pick("pin_a"))
    register_panel(win, "ab", [], pick("pin_a") + [None] + btn("ab", "restore", "adopt", "keep"))


def refresh(win, tr, lang="en"):
    """Scheme, density and language reached the bar and the title bands (called after every
    theme / language change). Does nothing before ``install``."""
    from PySide6 import QtCore   # noqa: PLC0415
    st = getattr(win, "_panels", None)
    if st is None:
        return
    st["tr"], st["lang"] = tr, lang
    if getattr(win, "_brand", None) is not None:
        win._brand.tr = tr
    c = rail_colours()
    d = studio_theme.density()
    rail = st["rail"]
    rail.setStyleSheet(rail_qss())
    rail.setWindowTitle(tr(S_BAR))
    rail.setIconSize(QtCore.QSize(d["icon"], d["icon"]))
    for key, b in st["buttons"].items():
        b.setIcon(_icon(key, c["icon_off"], c["icon_on"]))
        b.setFixedSize(d["icon_btn"], d["icon_btn"])
        b.setIconSize(QtCore.QSize(d["icon"], d["icon"]))
        name = win._docks[key].windowTitle()
        b.setToolTip(name + "\n" + tr(S_HINT)); b.setAccessibleName(name)
    lb = st["layout_button"]
    lb.setIcon(_icon("layout", c["icon_off"]))
    lb.setFixedSize(d["icon_btn"], d["icon_btn"]); lb.setIconSize(QtCore.QSize(d["icon"], d["icon"]))
    lb.setToolTip(tr(S_LAYOUT)); lb.setAccessibleName(tr(S_LAYOUT))
    for text, action in st["layout_actions"]:
        if action not in st.get("shared_actions", ()):      # the Window menu's own are named by studio.py
            action.setText(tr(text))
    for key, action in st["float_actions"].items():
        action.setText("%s: %s" % (tr(S_FLOAT), win._docks[key].windowTitle()))
    for bar in st["titles"].values():
        bar.restyle()
    for mode, action in st["strip_actions"].items():
        action.setText(tr(S_STRIP[mode]))
    sync_button_actions(win)                     # menu entries made from buttons: the language of the moment
    rm = getattr(win, "_reduce_motion_action", None)
    if rm is not None:
        rm.setText(tr(S_REDUCE)); rm.setToolTip(tr(S_REDUCE_TIP)); rm.setStatusTip(tr(S_REDUCE_TIP))
    for entry in st["strips"]:                  # the "..." of a turned icon row: what it holds
        entry["more"].setToolTip(tr(S_MORE)); entry["more"].setAccessibleName(tr(S_MORE))
    tighten(win)
    relayout(win)
    sync(win)


def install(win, tr, settings=None):
    """Build the panel bar, the title bands and the menu entries, and put the window into the
    first-run arrangement (image + code). Call once, after every dock exists and before the
    default state is captured."""
    from PySide6 import QtCore, QtGui, QtWidgets   # noqa: PLC0415
    missing = set(win._docks) - set(RAIL_ORDER)
    if missing:
        raise KeyError("panels without a place on the panel bar: %s" % sorted(missing))

    class TitleBar(QtWidgets.QWidget):
        """Name, then the panel's status items, then space; on the right the menu button, separate
        window / dock, hide. Mouse presses on the name, the status items and the space are left to
        QDockWidget (labels do not take them), so dragging and double-click keep working."""

        def __init__(self, key, dock):
            super().__init__(dock)
            self.key, self.dock = key, dock
            self.setObjectName("dock_title")
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            lay = QtWidgets.QHBoxLayout(self)
            lay.setContentsMargins(10, 0, 2, 1); lay.setSpacing(2)
            self.label = QtWidgets.QLabel(dock.windowTitle())
            self.label.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
            self.label.setMinimumWidth(20)
            self.status, self.actions, self.dropped = [], [], []
            self.a_hide = QtGui.QAction("Hide", self)            # one per panel (named in restyle)
            self.a_hide.triggered.connect(lambda _c=False: self.dock.hide())
            self.status_box = QtWidgets.QHBoxLayout(); self.status_box.setContentsMargins(8, 0, 0, 0)
            self.status_box.setSpacing(10)
            self.b_menu = QtWidgets.QToolButton(); self.b_menu.setObjectName("dock_title_menu")
            self.b_menu.setAutoRaise(True); self.b_menu.setProperty("keepSize", True)
            self.b_menu.setText("\u2261"); self.b_menu.setCursor(QtCore.Qt.PointingHandCursor)
            self.b_menu.setFocusPolicy(QtCore.Qt.TabFocus)
            self.b_menu.setPopupMode(QtWidgets.QToolButton.InstantPopup)
            self.b_menu.setMenu(QtWidgets.QMenu(self.b_menu))
            self.b_menu.menu().aboutToShow.connect(self.fill_menu)
            # Alt+M inside this panel opens its menu: a QAction of the panel (named in restyle), so the key
            # is listed with every other key binding of the window
            self.key_menu = QtGui.QAction("Panel menu", dock)
            self.key_menu.setShortcut(QtGui.QKeySequence("Alt+M"))
            self.key_menu.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
            self.key_menu.triggered.connect(lambda _c=False: self.b_menu.showMenu())
            dock.addAction(self.key_menu)
            self.b_float = QtWidgets.QToolButton(); self.b_float.setObjectName("dock_title_float")
            self.b_close = QtWidgets.QToolButton(); self.b_close.setObjectName("dock_title_close")
            for b in (self.b_float, self.b_close):
                b.setAutoRaise(True); b.setFocusPolicy(QtCore.Qt.NoFocus)
                b.setCursor(QtCore.Qt.PointingHandCursor); b.setProperty("keepSize", True)
            lay.addWidget(self.label); lay.addLayout(self.status_box); lay.addStretch(1)
            lay.addWidget(self.b_menu); lay.addWidget(self.b_float); lay.addWidget(self.b_close)
            self.b_float.clicked.connect(lambda _c=False: toggle_float(win, key))
            self.b_close.clicked.connect(lambda _c=False: dock.hide())
            dock.windowTitleChanged.connect(lambda _t: self.restyle())
            dock.topLevelChanged.connect(lambda _f: sync(win))

        def sizeHint(self):                      # QDockWidget asks the hint (not the fixed size) for the band
            return QtCore.QSize(super().sizeHint().width(), studio_theme.density()["title_band"] - 2)

        def minimumSizeHint(self):
            return QtCore.QSize(40, studio_theme.density()["title_band"] - 2)

        def set_registration(self, status, actions):
            for item in self.status:
                item["label"].deleteLater()
            self.status, self.actions = [], actions
            for spec in status:
                lab = QtWidgets.QLabel(""); lab.setObjectName("dock_title_status_" + str(spec["id"]))
                lab.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
                self.status_box.addWidget(lab)
                self.status.append({"id": str(spec["id"]), "text": spec["text"], "tip": spec.get("tip", ""),
                                    "priority": int(spec.get("priority", 0)), "label": lab, "now": ""})
            self.update_status()

        def update_status(self):
            """Ask every item for its text (cheap); lay the band out again only when one changed."""
            changed = False
            for item in self.status:
                try:
                    text = str(item["text"]() or "")
                except Exception:                    # noqa: BLE001 - a read-out must never break the window
                    text = ""
                if text != item["now"]:
                    item["now"] = text
                    item["label"].setText(text)
                    item["label"].setToolTip(item["tip"] or text)
                    changed = True
            if changed or not self.status:
                self.fit()
            return changed

        def fit(self):
            """Too narrow for everything: whole status items go, lowest priority first. The name and
            the buttons stay to the last."""
            fixed = self.label.sizeHint().width() + 10 + 2 + 1
            for b in (self.b_menu, self.b_float, self.b_close):
                fixed += b.width() + 2
            room = self.width() - fixed - 8
            keep, self.dropped = [], []
            for item in sorted(self.status, key=lambda it: -it["priority"]):
                need = item["label"].fontMetrics().horizontalAdvance(item["now"]) + 10
                if item["now"] and need <= room:
                    room -= need
                    keep.append(item["id"])
                elif item["now"]:
                    self.dropped.append(item)
            for item in self.status:
                item["label"].setVisible(item["id"] in keep)
            names = [self.dock.windowTitle()] + [it["now"] for it in self.dropped]
            self.label.setToolTip("\n".join(names) if self.dropped else "")

        def resizeEvent(self, ev):
            super().resizeEvent(ev)
            self.fit()

        def fill_menu(self):
            """Built when it opens: status items that did not fit, the panel's own actions (the shared
            QAction objects), then what every panel has."""
            st = win._panels
            _tr = st["tr"]
            menu = self.b_menu.menu()
            menu.clear()
            sync_button_actions(win)                 # buttons' names / enabled state of this moment
            for item in self.dropped:
                menu.addAction(item["now"]).setEnabled(False)
            if self.dropped:
                menu.addSeparator()
            for act in self.actions:
                if act is None:
                    menu.addSeparator()
                else:
                    menu.addAction(act)
            if self.actions:
                menu.addSeparator()
            for mode in STRIP_MODES:
                menu.addAction(st["strip_actions"][mode])
            menu.addSeparator()
            menu.addAction(st["float_actions"][self.key])
            menu.addAction(self.a_hide)
            menu.addAction(st["layout_actions"][0][1])           # Reset panel layout

        def restyle(self):
            st = win._panels
            _tr = st["tr"]
            d = studio_theme.density()
            p = studio_theme.PALETTES[studio_theme.current_name()]
            self.setStyleSheet(title_qss())
            self.setFixedHeight(d["title_band"] - 2)        # 11 px name + 16 px buttons: 2 px under the table's band
            side = max(14, d["title_band"] - 6)
            text = self.dock.windowTitle()
            self.label.setText(text.upper() if st["lang"] in ("en", "de") else text)
            for b in (self.b_menu, self.b_float, self.b_close):
                b.setFixedSize(side, side); b.setIconSize(QtCore.QSize(12, 12))
            name = "%s \u2014 %s (Alt+M)" % (text, _tr(S_MENU))
            self.b_menu.setToolTip(name); self.b_menu.setAccessibleName("%s \u2014 %s" % (text, _tr(S_MENU)))
            self.key_menu.setText("%s \u2014 %s" % (text, _tr(S_MENU)))
            self.label.setAccessibleName(text)
            for item in self.status:
                item["now"] = None                   # texts are in the language of the moment: ask again
            self.update_status()
            self.b_close.setIcon(_icon("close", p["muted"]))
            self.b_close.setToolTip(_tr(S_HIDE)); self.b_close.setAccessibleName(_tr(S_HIDE))
            self.a_hide.setText(_tr(S_HIDE))
            self.follow()

        def follow(self):
            st = win._panels
            p = studio_theme.PALETTES[studio_theme.current_name()]
            floating = self.dock.isFloating()
            self.b_float.setIcon(_icon("dock" if floating else "float", p["muted"]))
            tip = st["tr"](S_DOCK if floating else S_FLOAT)
            self.b_float.setToolTip(tip); self.b_float.setAccessibleName(tip)

    class EscCloses(QtCore.QObject):
        """Esc in a separate panel window closes it (a docked panel is left alone).

        The main window has an Esc shortcut of its own (leave image focus) that would take the key
        first, so the ShortcutOverride is claimed here; the key press that follows closes the window.
        A child that uses Esc itself (an open completer, a line being edited) never lets it get here."""

        def eventFilter(self, obj, ev):
            if (ev.type() in (QtCore.QEvent.KeyPress, QtCore.QEvent.ShortcutOverride)
                    and ev.key() == QtCore.Qt.Key_Escape and ev.modifiers() == QtCore.Qt.NoModifier
                    and isinstance(obj, QtWidgets.QDockWidget) and obj.isFloating()):
                if ev.type() == QtCore.QEvent.KeyPress:
                    obj.hide()
                ev.accept()
                return True
            return False

    rail = QtWidgets.QToolBar(tr(S_BAR), win)
    rail.setObjectName(RAIL_NAME)
    rail.setMovable(False); rail.setFloatable(False)
    rail.setOrientation(QtCore.Qt.Vertical)
    rail.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
    rail.toggleViewAction().setVisible(False)            # the bar is the way back to every panel: it stays
    win.addToolBar(QtCore.Qt.LeftToolBarArea, rail)

    esc = EscCloses(win)
    st = {"rail": rail, "buttons": {}, "titles": {}, "float_actions": {}, "layout_actions": [],
          "strips": [], "strip_actions": {}, "strip_mode": "auto", "tab_sides": {}, "settings": settings,
          "tr": tr, "lang": "en", "esc": esc, "menus": []}
    win._panels = st

    def panel_menu(key, button, pos):
        """Right-click on a bar button: show / hide, separate window / dock (modeless popup)."""
        _tr = win._panels["tr"]
        dock = win._docks[key]
        menu = QtWidgets.QMenu(button)
        a_vis = menu.addAction(_tr(S_SHOW if dock.isHidden() else S_HIDE))
        a_float = menu.addAction(_tr(S_DOCK if dock.isFloating() else S_FLOAT))

        def flip():
            dock.setVisible(dock.isHidden())
            if not dock.isHidden():
                dock.raise_()
            sync(win)
        a_vis.triggered.connect(lambda _c=False: flip())
        a_float.triggered.connect(lambda _c=False: (toggle_float(win, key), sync(win)))
        win._panels["open_menu"] = menu                      # retained (shiboken) and reachable by a test
        menu.popup(button.mapToGlobal(pos))
        return menu
    st["panel_menu"] = panel_menu

    for key in RAIL_ORDER:
        dock = win._docks.get(key)
        if dock is None:
            continue
        b = QtWidgets.QToolButton()
        b.setObjectName("rail_" + key)
        b.setCheckable(True); b.setProperty("keepSize", True); b.setProperty("railKey", key)
        b.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.setFocusPolicy(QtCore.Qt.TabFocus)
        b.clicked.connect(lambda _c=False, k=key: (toggle_panel(win, k), sync(win)))
        b.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        b.customContextMenuRequested.connect(lambda pos, k=key, btn=b: panel_menu(k, btn, pos))
        rail.addWidget(b)
        st["buttons"][key] = b
        if key == PRINCIPAL[-1]:
            rail.addSeparator()
        bar = TitleBar(key, dock)
        dock.setTitleBarWidget(bar)
        st["titles"][key] = bar
        dock.installEventFilter(esc)
        dock.visibilityChanged.connect(lambda _v: sync(win))
        fa = QtGui.QAction("%s: %s" % (tr(S_FLOAT), dock.windowTitle()), win)
        fa.setCheckable(True)
        fa.triggered.connect(lambda checked=False, k=key: toggle_float(win, k, checked))
        st["float_actions"][key] = fa

    # layout button: reset / code side / dock all (bottom of the bar)
    grow = QtWidgets.QWidget(); grow.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
    grow.setStyleSheet("background:transparent;")
    rail.addWidget(grow)
    lmenu = QtWidgets.QMenu(win); st["menus"].append(lmenu)
    # one function, one QAction: where the window already has the action (Window menu), that one is used
    known = getattr(win, "_actions", None) or {}
    shared = {S_RESET: known.get("reset_layout"), S_DOCK_ALL: known.get("dock_all")}
    st["shared_actions"] = [a for a in shared.values() if a is not None]
    for text, fn in ((S_RESET, lambda: win._reset_layout()),
                     (S_CODE_LEFT, lambda: set_code_side(win, "left")),
                     (S_CODE_BOTTOM, lambda: set_code_side(win, "bottom")),
                     (S_DOCK_ALL, lambda: [toggle_float(win, k, False) for k, d in win._docks.items() if d.isFloating()])):
        a = shared.get(text)
        if a is None:
            a = QtGui.QAction(tr(text), win)
            a.triggered.connect(lambda _c=False, f=fn: f())
        lmenu.addAction(a)
        st["layout_actions"].append((text, a))
    lb = QtWidgets.QToolButton(); lb.setObjectName("rail_layout")
    lb.setProperty("keepSize", True)
    lb.setMenu(lmenu); lb.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    lb.setCursor(QtCore.Qt.PointingHandCursor)
    rail.addWidget(lb)
    st["layout_button"] = lb

    # wide panels: icon rows and tabs on the left (automatic / on top / on the left)
    try:
        st["strip_mode"] = normalise_strip_mode(settings().value(STRIP_MODE_KEY) if settings is not None else "auto")
    except Exception:                            # noqa: BLE001 - a broken store must not stop the window
        st["strip_mode"] = "auto"
    st["strips"] = _find_strips(win)
    lmenu.addSeparator()
    group = QtGui.QActionGroup(win); group.setExclusive(True); st["strip_group"] = group
    for mode in STRIP_MODES:
        a = QtGui.QAction(tr(S_STRIP[mode]), win)
        a.setCheckable(True); a.setChecked(mode == st["strip_mode"]); group.addAction(a)
        a.triggered.connect(lambda _c=False, m=mode: set_strip_mode(
            win, m, st["settings"]() if st["settings"] is not None else None))
        lmenu.addAction(a)
        st["strip_actions"][mode] = a

    class Follow(QtCore.QObject):
        """A panel or the window changed size / place: look again, once per event-loop turn."""

        def __init__(self, parent):
            super().__init__(parent)
            self.pending = False

        def eventFilter(self, obj, ev):
            if ev.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Show) and not self.pending:
                self.pending = True
                QtCore.QTimer.singleShot(0, self.run)
            return False

        def run(self):
            self.pending = False
            try:
                relayout(win)
            except RuntimeError:                 # the window is being destroyed
                pass

    class TabKeys(QtCore.QObject):
        """Up / Down walk the tabs of a vertical tab bar (Qt's QTabBar only listens to Left / Right,
        whatever its direction; those keep working)."""

        def eventFilter(self, obj, ev):
            if ev.type() != QtCore.QEvent.KeyPress or not isinstance(obj, QtWidgets.QTabBar):
                return False
            if ev.key() not in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
                return False
            if obj.shape() not in (QtWidgets.QTabBar.RoundedWest, QtWidgets.QTabBar.TriangularWest,
                                   QtWidgets.QTabBar.RoundedEast, QtWidgets.QTabBar.TriangularEast):
                return False
            step = 1 if ev.key() == QtCore.Qt.Key_Down else -1
            i = obj.currentIndex() + step
            while 0 <= i < obj.count() and not obj.isTabEnabled(i):
                i += step
            if 0 <= i < obj.count():
                obj.setCurrentIndex(i)
            return True

    st["tab_keys"] = TabKeys(win)
    follow = Follow(win); st["follow"] = follow
    _default_registrations(win)
    tick = QtCore.QTimer(win); tick.setInterval(250)             # status read-outs: 4 times a second
    tick.timeout.connect(lambda: [bar.update_status() for k, bar in st["titles"].items()
                                  if not win._docks[k].isHidden()])
    tick.start(); st["status_tick"] = tick
    win.installEventFilter(follow)
    for dock in win._docks.values():
        dock.installEventFilter(follow)
        dock.dockLocationChanged.connect(lambda _a: follow.run())
        dock.topLevelChanged.connect(lambda _f: follow.run())

    # menus + command palette: every panel has a show / hide entry and a separate-window entry
    menu = getattr(win, "_menu_panels", None)
    if menu is not None:
        listed = set(menu.actions())
        for key in RAIL_ORDER:
            tva = win._docks[key].toggleViewAction() if key in win._docks else None
            if tva is not None and tva not in listed:
                before = next((a for a in menu.actions() if a.isSeparator()), None)
                menu.insertAction(before, tva)
        menu.addSeparator()
        for fa in st["float_actions"].values():
            menu.addAction(fa)
    actions = getattr(win, "_actions", None)
    if isinstance(actions, dict):
        for key, fa in st["float_actions"].items():
            actions["panel_float_" + key] = fa
        for text, a in st["layout_actions"]:
            if text in (S_CODE_LEFT, S_CODE_BOTTOM):
                actions["layout_" + ("code_left" if text == S_CODE_LEFT else "code_bottom")] = a

    # first-run arrangement: image + code
    for key, dock in win._docks.items():
        if key not in PRINCIPAL:
            dock.hide()
    win._layout_state = initial_state()
    _sync_modes(win)
    refresh(win, tr)
    return rail
