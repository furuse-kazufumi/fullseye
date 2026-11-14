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
import re

import studio_layout
import studio_theme

#: Saved dock states are reused only from the same layout version ("3" = before the panel bar).
LAYOUT_VERSION = "4"
#: Panels shown next to the image on the first run. The rest come from the panel bar.
PRINCIPAL = ("program",)
#: The work mode that describes the first-run arrangement (studio_layout.MODES).
INITIAL_MODE = "code"
#: Order of the buttons on the panel bar (every key of ``win._docks`` must be here — a test counts).
#: "project" is the Project dock of the integration branch (integrate/studio-1-2-0): without it here,
#: install() raises KeyError as soon as the two branches are merged (D61). A key without a dock is skipped.
RAIL_ORDER = ("program", "operators", "pipeline", "variables", "display", "compare", "ab", "project")
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
S_WORK_MODE = "Work mode"
S_WORK_MODE_TIP = "choose which panels are shown; the name on the button is the mode in use"
S_MODE_CHANGED = "* = rearranged since this mode was chosen; choose the mode again to return to its arrangement"
S_STRIP = {"auto": "Tools and tabs: automatic (on the left when the panel is wide)",
           "top": "Tools and tabs: on top",
           "left": "Tools and tabs: on the left"}
STRINGS = (S_BAR, S_HINT, S_FLOAT, S_DOCK, S_HIDE, S_SHOW, S_LAYOUT, S_RESET, S_CODE_LEFT,
           S_CODE_BOTTOM, S_DOCK_ALL, S_MENU, S_MORE, S_REDUCE, S_REDUCE_TIP, S_OPENING, S_SAMPLE, S_SEARCHING, S_ST_SHOWN, S_ST_STAGES, S_ST_ERRORS, S_ST_VARS) + tuple(S_STRIP.values()) + (S_WORK_MODE, S_WORK_MODE_TIP, S_MODE_CHANGED)
# (the strings of the strip - S_OVERFLOW, S_SCROLL_BACK, S_SCROLL_ON - are added below, where they are defined)

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
        "spacing:4px; padding:2px 2px 2px 2px; }\n"
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
    elif name == "project":                    # a folder
        path([(2, 4), (6, 4), (7.5, 5.5), (14, 5.5), (14, 13), (2, 13), (2, 4)]); line(2, 7.5, 14, 7.5)
    elif name == "layout":                     # window split into three
        rect(2, 2.5, 12, 11); line(6.5, 2.5, 6.5, 13.5); line(6.5, 8.5, 14, 8.5)
    elif name == "float":                      # two overlapping windows
        rect(5.5, 2.5, 8, 7); rect(2.5, 6.5, 8, 7)
    elif name == "dock":                       # a window with its band at the bottom
        rect(2.5, 2.5, 11, 11); rect(2.5, 9.5, 11, 4, fill=True)
    elif name == "close":
        line(4, 4, 12, 12); line(12, 4, 4, 12)
    elif name == "menu":                       # three lines: a panel's menu button (D130: drawn)
        line(3, 4.5, 13, 4.5); line(3, 8, 13, 8); line(3, 11.5, 13, 11.5)
    elif name == "mark_run":                   # the state marks (D130): running = a filled triangle
        p.setBrush(col)
        p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(4.5 * s, 3 * s), QtCore.QPointF(13 * s, 8 * s),
                                       QtCore.QPointF(4.5 * s, 13 * s)]))
        p.setBrush(QtCore.Qt.NoBrush)
    elif name == "mark_done":                  # ended (done / stopped) = a filled square
        rect(4, 4, 8, 8, fill=True)
    elif name == "mark_fail":                  # failed = a cross
        pen.setWidthF(2.2 * s); p.setPen(pen)
        line(4, 4, 12, 12); line(12, 4, 4, 12)
    elif name == "image_focus":                # the image alone: four corners around a picture (D01)
        path([(2, 6), (2, 3), (5, 3)]); path([(11, 3), (14, 3), (14, 6)])
        path([(14, 10), (14, 13), (11, 13)]); path([(5, 13), (2, 13), (2, 10)])
        rect(5.5, 6, 5, 4, fill=True)
    elif name == "find_panel":                 # a panel and a magnifier (D01)
        rect(1.5, 2.5, 9, 8); line(1.5, 5, 10.5, 5)
        p.drawEllipse(QtCore.QPointF(10.5 * s, 10.5 * s), 2.6 * s, 2.6 * s); line(12.4, 12.4, 14.6, 14.6)
    elif name == "auto_update":                # a circle of arrows: the display follows every change (D01)
        import math   # noqa: PLC0415
        pts = [(8 + 5.2 * math.cos(math.radians(a)), 8 - 5.2 * math.sin(math.radians(a))) for a in range(40, 330, 10)]
        path(pts)
        hx, hy = pts[-1]
        path([(hx - 3.0, hy - 1.2), (hx, hy), (hx + 0.6, hy - 3.1)])
    elif name == "scroll_back_h":              # the scroll buttons of a strip (A2): chevrons
        path([(10, 3.5), (5.5, 8), (10, 12.5)])
    elif name == "scroll_on_h":
        path([(6, 3.5), (10.5, 8), (6, 12.5)])
    elif name == "scroll_back_v":
        path([(3.5, 10), (8, 5.5), (12.5, 10)])
    elif name == "scroll_on_v":
        path([(3.5, 6), (8, 10.5), (12.5, 6)])
    else:
        p.end()
        raise KeyError("no glyph named %r" % (name,))
    p.end()
    _GLYPH_CACHE[key] = pm
    return pm


def label_text(text):
    """A text for a menu entry / button label: '&' is shown, not taken as the key letter (D14, P15-3)."""
    return (text or "").replace("&", "&&")


def plain_text(text):
    """What a menu entry's text shows: the key-letter marks gone, '&&' read as '&' (for lists that show
    an action's name outside a menu: the palette)."""
    return (text or "").replace("&&", "\0").replace("&", "").replace("\0", "&")


def panel_order(win, keys):
    """``keys`` in the one order of the panel bar (RAIL_ORDER), only panels this window has (D21: the
    bar, Window > Panels, More > Panels and Find panel list the same set in the same order)."""
    have = set(getattr(win, "_docks", {}) or {})
    return [k for k in RAIL_ORDER if k in keys and k in have]


def tool_tip(name, effect, key=""):
    """The one shape of a hint (P04-5): "name — what happens (key)". The key comes from the action."""
    name = (name or "").replace("&", "").replace("\u2026", "").strip()
    effect = (effect or "").strip()
    text = "%s \u2014 %s" % (name, effect) if effect and effect != name else name
    return "%s (%s)" % (text, key) if key else text


def mode_switch(win, bar, actions):
    """D01: the four work modes as ONE button of the top band. Its menu holds the modes (an exclusive
    group: always one); its text is the mode in use and it is shown pressed (D02: "code" at start). The
    modes stay window actions, so Ctrl+1 .. Ctrl+4 keep working. Returns the button (``win._mode_switch``)."""
    from PySide6 import QtCore, QtWidgets   # noqa: PLC0415
    menu = QtWidgets.QMenu(win)
    for a in actions.values():
        menu.addAction(a)
        win.addAction(a)                     # the keys work although the actions left the bar
    b = QtWidgets.QToolButton(bar)
    b.setObjectName("work_mode_switch")
    b.setMenu(menu)
    b.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    b.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
    b.setCheckable(True)
    b.setFocusPolicy(QtCore.Qt.TabFocus)
    b.setCursor(QtCore.Qt.PointingHandCursor)

    def follow(*_a):
        on = [a for a in actions.values() if a.isChecked()]
        changed = (getattr(win, "_panels", None) or {}).get("mode_modified")
        b.setText(label_text(on[0].text() if on else "") + (" *" if changed else ""))   # D128: rearranged since
        b.setChecked(True)                   # pressed = the mode in use is named on it
    for a in actions.values():
        a.toggled.connect(follow)
        a.changed.connect(follow)
    bar.addWidget(b)
    win._mode_switch = b
    win._mode_switch_menu = menu
    b._fs_follow = follow                    # refresh() calls it: the language pass rewrites button texts
    follow()
    return b


def compose_top_tips(win, tr):
    """Hints of the top band's drawn buttons: "name — what happens (key)", in the language of the moment.
    The words come from the action's own status tip (the one the language switch translates)."""
    from PySide6 import QtGui   # noqa: PLC0415
    for act, _glyph_name in getattr(win, "_fs_glyph_actions", None) or []:
        try:
            base = act.statusTip() or act.toolTip()
            if not act.statusTip():
                act.setStatusTip(base)
            key = act.shortcut().toString(QtGui.QKeySequence.NativeText)
            act.setToolTip(tool_tip(act.text(), base, key))
        except RuntimeError:
            pass
    b = getattr(win, "_mode_switch", None)
    if b is not None:                            # the switch: what it is, then every mode with its own key
        b._fs_follow()                           # its text = the mode in use, in the language of the moment
        lines = [tool_tip(tr(S_WORK_MODE), tr(S_WORK_MODE_TIP))]
        for a in b.menu().actions():
            lines.append(tool_tip(a.text(), "", a.shortcut().toString(QtGui.QKeySequence.NativeText)))
        if (getattr(win, "_panels", None) or {}).get("mode_modified"):
            lines.append(tr(S_MODE_CHANGED))
        b.setToolTip("\n".join(lines))
        b.setAccessibleName(tr(S_WORK_MODE))


def mode_differs(win):
    """D128: whether the arrangement on screen is no longer the one the work mode in use asks for - a
    panel shown / hidden against the mode, a panel in a separate window, or a panel on another side
    than when the mode was chosen. (Sizes do not count; image focus is its own state.)"""
    st = getattr(win, "_panels", None)
    state = getattr(win, "_layout_state", None)
    if st is None or state is None or state.focus_image:
        return False
    mode = studio_layout.MODES.get(state.mode)
    if mode is None:
        return False
    base = st.get("mode_areas") or {}
    for key, dock in win._docks.items():
        want = key in mode.visible and key not in mode.collapsed
        if want == dock.isHidden():
            return True
        if dock.isHidden():
            continue
        if dock.isFloating() or (key in base and win.dockWidgetArea(dock) != base[key]):
            return True
    return False


def mode_watch(win):
    """Look again whether the arrangement is still the mode's, and let the switch say so (" *")."""
    st = getattr(win, "_panels", None)
    if st is None or getattr(win, "_applying_layout", False):
        return bool(st and st.get("mode_modified"))
    now = mode_differs(win)
    if now != bool(st.get("mode_modified")):
        st["mode_modified"] = now
        if getattr(win, "_mode_switch", None) is not None:
            compose_top_tips(win, st["tr"])      # the switch's text and hint follow
    return now


def mode_chosen(win, mode_id):
    """A work mode was chosen (the window has applied it). Chosen AGAIN while its arrangement was changed:
    back to the arrangement the mode had when it was chosen - the panels where they were then, what the
    user showed / hid against the mode forgotten (D128: "press it to return to that arrangement")."""
    import dataclasses   # noqa: PLC0415
    st = _state(win)
    if st.get("mode_applied") == mode_id and st.get("mode_modified"):
        state = win._layout_state
        overrides = {m: v for m, v in state.overrides.items() if m != mode_id}
        blob = st.get("mode_state") or getattr(win, "_default_state", None)
        win._applying_layout = True
        try:
            if blob is not None:
                win.restoreState(blob)
        finally:
            win._applying_layout = False
        win._layout_state = studio_layout.apply_mode(dataclasses.replace(state, overrides=overrides), mode_id)
        apply = getattr(win, "_apply_layout_state", None)
        if apply is not None:
            apply()
        try:
            if st.get("settings") is not None:
                st["settings"]().setValue(WORK_LAYOUT_KEY, studio_layout.to_json(win._layout_state))
        except Exception:                        # noqa: BLE001 - a broken store: the arrangement is still back
            pass
        after_restore(win)
    st["mode_applied"] = mode_id
    st["mode_state"] = win.saveState()
    st["mode_areas"] = {k: win.dockWidgetArea(d) for k, d in win._docks.items()}
    st["mode_modified"] = mode_differs(win)
    if getattr(win, "_mode_switch", None) is not None:
        compose_top_tips(win, st["tr"])          # the switch is told either way (its text was set before this)
    return st["mode_modified"]


def glyph_action(win, action, name):
    """Give a top-band action a drawn icon (re-tinted with the scheme by refresh)."""
    lst = getattr(win, "_fs_glyph_actions", None)
    if lst is None:
        lst = []
        win._fs_glyph_actions = lst
    lst.append((action, name))
    p = studio_theme.PALETTES[studio_theme.current_name()]
    action.setIcon(_icon(name, p["text"], p["accent"]))
    return action


def fix_hand(button):
    """D03: the pointing hand only on a button that can be pressed now."""
    from PySide6 import QtCore   # noqa: PLC0415
    try:
        if button.isEnabled():
            if button.property("fsHand"):
                button.setCursor(QtCore.Qt.PointingHandCursor)
                button.setProperty("fsHand", False)
        elif button.cursor().shape() == QtCore.Qt.PointingHandCursor:
            button.setProperty("fsHand", True)
            button.unsetCursor()
    except RuntimeError:                         # going away with its window
        pass


_LONE_AMP = re.compile(r"(?<!&)&(?=\s)")       # an '&' written as a word ("A & B"): never a key letter


def drop_repeated_titles(win):
    """D59: a group box whose title only repeats its panel's name loses the title (band + tab + frame
    said the same thing three times). D14: a title's lone '&' is shown. Called by refresh, after the
    language pass wrote the titles. Returns the number of groups without a title now."""
    from PySide6 import QtWidgets   # noqa: PLC0415

    def norm(text):
        return "".join(ch for ch in (text or "").casefold() if ch.isalnum())

    n = 0
    for dock in win._docks.values():
        name = norm(dock.windowTitle())
        for box in dock.findChildren(QtWidgets.QGroupBox):
            title = box.title()
            if title and _LONE_AMP.search(title):      # D14: "EXPORT & I/O" - a word, not a key letter
                box.setTitle(_LONE_AMP.sub("&&", title))
            if title and norm(title) == name:
                box.setProperty("fsTitleWas", title)
                box.setTitle("")
            bare = not box.title() and bool(box.property("fsTitleWas"))
            if bool(box.property("untitled")) != bare:
                box.setProperty("untitled", bare)      # the style sheet takes the title's room away
                box.style().unpolish(box); box.style().polish(box)
            n += 1 if bare else 0
    return n


def theme_mdi(win):
    """D17: the ground of the image area is the neutral surround (never Qt's grey), and the title band of
    an image window that is not maximised takes role colours through its palette (Qt's own is light blue):
    in front = the panel bar's band with the body text colour; behind = the panel ground, which the window's
    style sheet already gives it. Safe to call often; returns the windows reached."""
    from PySide6 import QtGui   # noqa: PLC0415
    mdi = getattr(win, "_mdi", None)
    if mdi is None:
        return 0
    name = studio_theme.current_name()
    p = studio_theme.PALETTES[name]
    if mdi.property("fsGround") != name:
        mdi.setBackground(QtGui.QBrush(QtGui.QColor(p["surround"])))
        mdi.setProperty("fsGround", name)
    n = 0
    for sub in mdi.subWindowList():
        n += 1
        if sub.property("fsTitleTheme") == name:
            continue
        pal = sub.palette()
        for group in (QtGui.QPalette.Active, QtGui.QPalette.Inactive, QtGui.QPalette.Disabled):
            pal.setColor(group, QtGui.QPalette.Highlight, QtGui.QColor(p["rail"]))
            pal.setColor(group, QtGui.QPalette.HighlightedText, QtGui.QColor(p["text"]))
        sub.setPalette(pal)
        sub.setProperty("fsTitleTheme", name)
    return n


def _icon(name, off, on=None):
    from PySide6 import QtGui   # noqa: PLC0415
    ic = QtGui.QIcon()
    ic.addPixmap(_glyph(name, off), QtGui.QIcon.Normal, QtGui.QIcon.Off)
    ic.addPixmap(_glyph(name, on or off), QtGui.QIcon.Normal, QtGui.QIcon.On)
    dim = studio_theme.PALETTES[studio_theme.current_name()]["off"]     # D03: disabled = the off colour
    ic.addPixmap(_glyph(name, dim), QtGui.QIcon.Disabled, QtGui.QIcon.Off)
    ic.addPixmap(_glyph(name, dim), QtGui.QIcon.Disabled, QtGui.QIcon.On)
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


def show_principal(win, key):
    """A principal (the code) is brought forward and given the keyboard; it is never hidden (P01-1)."""
    from PySide6 import QtWidgets   # noqa: PLC0415
    dock = win._docks[key]
    dock.show(); dock.raise_()
    if dock.isFloating():
        _keep_on_screen(win, dock)
        dock.activateWindow()
    root = dock.widget()
    editor = root.findChild(QtWidgets.QPlainTextEdit) if root is not None else None
    (editor or root or dock).setFocus()
    return True


def toggle_panel(win, key):
    """The panel-bar click: hidden -> shown and raised; behind a tab -> raised; in front -> hidden.
    A principal (``PRINCIPAL``) is only ever shown, raised and focused. Returns True when the
    panel is shown afterwards."""
    if key in PRINCIPAL:
        return show_principal(win, key)
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
        if want and win.isVisible() and not win.frameGeometry().intersects(dock.frameGeometry()):
            near = win.frameGeometry().topLeft()     # D60: by the main window, not where Qt left it
            dock.move(near.x() + 60, near.y() + 90)
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
    st = getattr(win, "_panels", None)
    if ok and st is not None:
        st["restore_again"] = state              # once more when shown and the strips have their side (relayout)
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
        root = getattr(root, "_fs_body", root)  # a panel whose strip stands on its left: the panel itself
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


# --------------------------------------------------------------------------- #
# one strip for every panel's tools and every tab row (A1 A2 A3, user 2026-11-13)
#
# Every panel DECLARES its tool strip: register_panel(win, key, strip=(row, body)) for a dock,
# declare_strip for the main image, adopt_image_strip for every other image window (also when it is
# detached). Nothing is guessed from the widget tree any more (the old _find_strips looked for "an
# icon row next to a list" and missed every strip that was not). A panel without a strip says why
# (STRIP_EXEMPT); panel_ledger(win) lists every panel and what it declared, and the gates count it.
#
# A strip is a FlowStrip. It turns with its panel: a row across the top while the panel is tall or near
# square, one column on the left when it is wide (strip_side: 2.2 / 1.6; automatic / on top / on the
# left - one setting for every panel, the image windows and the code). When it does not fit it either
#   SCROLLS: a scroll button at each end (across: back / on to the left / right, down: up / down; one
#            press = one item, held = repeat, the wheel too, the button at an end is disabled), or
#   WRAPS:   onto more rows (a row strip) or columns (a column strip), at most WRAP_MAX_LINES; past that
#            the last one scrolls, so every item stays reachable.
# One setting for every strip and every tab row: "When they do not fit: scroll / wrap" (default scroll:
# it takes no room and nothing moves). The tab row of a group of tabbed panels is the same part: a
# FlowStrip of FlowTabs laid over Qt's own QTabBar, which stays the model (current tab, the arrow keys,
# what QMainWindow raises). Qt has no multi-row tab bar, so the rows are drawn here and Qt's bar is only
# made as thick as the rows need. Wrapped rows stay where they are when a tab is chosen (the old
# Windows multi-row tab control moved the chosen row next to the page - the tab under the mouse jumped
# away; Visual Studio has no multi-row tool-window tabs): only the mark of the chosen tab moves.
# --------------------------------------------------------------------------- #
OVERFLOW_MODES = ("scroll", "wrap")
OVERFLOW_KEY = "panels/overflow_mode"
WRAP_MAX_LINES = 3
S_OVERFLOW = {"scroll": "When they do not fit: scroll", "wrap": "When they do not fit: wrap onto more rows"}
S_SCROLL_BACK = "Scroll back — show the ones before (or turn the mouse wheel)"
S_SCROLL_ON = "Scroll on — show the ones after (or turn the mouse wheel)"
#: panels that have no tool strip of their own, and why (panel_ledger lists them with the reason)
STRIP_EXEMPT = {
    "display": "its three buttons each belong to the choice box beside them (display mode, frame B, "
               "perception mode): a strip would part a button from the box it acts on",
    "compare": "no tool buttons: two image panes and a summary line",
}
_FAR = -30000                                   # where an item that is scrolled out of sight waits
STRINGS = STRINGS + tuple(S_OVERFLOW.values()) + (S_SCROLL_BACK, S_SCROLL_ON)


def normalise_overflow_mode(value):
    """An overflow mode from the settings: "scroll" (the default) or "wrap"."""
    value = str(value or "").strip().lower()
    return value if value in OVERFLOW_MODES else "scroll"


def scroll_arrow(level=None):
    """Length of one scroll button along its strip: half a tool button (12 px compact, 14 standard). The
    same for tool strips and tab rows; across the strip it is as thick as the row it scrolls."""
    d = studio_theme.DENSITY[studio_theme.normalise_density(level or studio_theme.current_density())]
    return max(10, d["icon_btn"] // 2)


def _leads(n, gaps):
    lead = list(gaps) if isinstance(gaps, (list, tuple)) else [gaps] * n
    if len(lead) != n:
        raise ValueError("one gap per item (%d) or one number, not %d" % (n, len(lead)))
    return [max(0, int(g)) for g in lead]


def _span(ext, lead, idx):
    return sum(ext[i] for i in idx) + sum(lead[i] for i in idx[1:])


def flow_plan(extents, length, mode="scroll", gaps=4, max_lines=WRAP_MAX_LINES):
    """Qt-free: how a row of items fits into ``length`` px along the strip.

    ``extents``: each item's length along the strip. ``gaps``: one number, or one per item = the gap
    BEFORE that item when it is not the first of its row (a new group has a wider one). Returns
    {"lines": [[index, ...], ...], "scroll": index of the line that scrolls, or None}.
    Everything on one line when it fits (or when the strip has no length yet). "scroll": that one line
    scrolls. "wrap": greedy rows of at most ``length``; more than ``max_lines`` rows -> the last row
    takes all the rest and scrolls. An item longer than the strip cannot wrap: it scrolls."""
    n = len(extents)
    ext = [max(0, int(e)) for e in extents]
    lead = _leads(n, gaps)
    every = list(range(n))
    if n == 0:
        return {"lines": [], "scroll": None}
    if length <= 0 or _span(ext, lead, every) <= length:
        return {"lines": [every], "scroll": None}
    if normalise_overflow_mode(mode) == "scroll" or max_lines <= 1 or max(ext) > length:
        return {"lines": [every], "scroll": 0}
    lines, cur = [], []
    for i in every:
        if cur and _span(ext, lead, cur + [i]) > length:
            lines.append(cur)
            cur = []
        cur.append(i)
    lines.append(cur)
    if len(lines) <= max_lines:
        return {"lines": lines, "scroll": None}
    head = lines[:max_lines - 1]
    return {"lines": head + [[i for line in lines[max_lines - 1:] for i in line]], "scroll": max_lines - 1}


def scroll_reach(extents, gaps, room, first=0):
    """Qt-free: one scrolling line of items in ``room`` px (the length between its two scroll buttons).

    Returns (first, end, last_first): items first .. end-1 are wholly shown (always at least one), and
    ``last_first`` is the smallest start at which the LAST item is shown - the end of the scroll."""
    n = len(extents)
    if n == 0:
        return 0, 0, 0
    ext = [max(0, int(e)) for e in extents]
    lead = _leads(n, gaps)
    last_first, used = n - 1, ext[n - 1]
    while last_first > 0 and used + lead[last_first] + ext[last_first - 1] <= room:
        used += lead[last_first] + ext[last_first - 1]
        last_first -= 1
    first = max(0, min(int(first), last_first))
    end, used = first + 1, ext[first]
    while end < n and used + lead[end] + ext[end] <= room:
        used += lead[end] + ext[end]
        end += 1
    return first, end, last_first


_FLOW = {}


def flow_classes():
    """FlowStrip / FlowTab / TabRow (made once; Qt is imported here, not when the module loads)."""
    if _FLOW:
        return _FLOW
    from PySide6 import QtCore, QtGui, QtWidgets   # noqa: PLC0415

    class FlowStrip(QtWidgets.QWidget):
        """One row (or column) of tools or tabs that scrolls or wraps when it does not fit.

        ``kind`` "tools": a panel's own buttons, moved in by ``set_groups``; "tabs": the FlowTabs of a
        TabRow. objectName "flow_strip" and the property "flowKind" are what the gates count. An item
        the application hides is left out; an item scrolled out of sight waits outside the strip (it is
        not hidden, so the application's own show / hide stays the application's)."""

        def __init__(self, kind="tools", key="", parent=None):
            super().__init__(parent)
            self.setObjectName("flow_strip")
            self.setProperty("flowKind", kind)
            self.setProperty("flowKey", key)
            self.kind, self.key = kind, key
            self.orientation = "h"
            self.mode = "scroll"
            self.groups = []
            self.first = 0
            self.thickness = None                    # one row's thickness; None = the thickest item
            self.overlay = False                     # drawn over an image: a ground of its own
            self.sizes_itself = kind == "tools"      # a tab row's size is its tab bar's
            self.state = {"lines": 1, "scrolling": False, "first": 0, "last_first": 0, "shown": []}
            self._seps, self._busy, self._queued = [], False, False
            self.tr = lambda s: s
            self.b_back = self._arrow("flow_back", -1)
            self.b_on = self._arrow("flow_on", 1)
            self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
            self.restyle()

        def _arrow(self, name, step):
            b = QtWidgets.QToolButton(self)
            b.setObjectName(name)
            b.setAutoRaise(True)
            b.setFocusPolicy(QtCore.Qt.NoFocus)
            b.setAutoRepeat(True); b.setAutoRepeatDelay(350); b.setAutoRepeatInterval(90)
            b.setProperty("keepSize", True)
            b.clicked.connect(lambda _c=False, s=step: self.scroll_by(s))
            b.hide()
            return b

        # ---- what it holds -------------------------------------------------- #
        def set_groups(self, groups):
            """The items in groups (a wider gap and a thin line between two groups), moved into the strip."""
            for w in self.items():
                w.removeEventFilter(self)
            self.groups = [list(g) for g in groups if g]
            for w in self.items():
                hidden = w.isHidden() and w.testAttribute(QtCore.Qt.WA_WState_ExplicitShowHide)
                w.setParent(self)
                w.setVisible(not hidden)
                w.installEventFilter(self)
            self.first = 0
            self.updateGeometry()
            self.relayout()

        def items(self):
            return [w for g in self.groups for w in g]

        def set_orientation(self, orientation):
            orientation = "v" if orientation == "v" else "h"
            if orientation == self.orientation:
                return
            self.orientation = orientation
            self.first = 0
            if self.sizes_itself:
                self.setMinimumSize(0, 0)
                self.setMaximumSize(_QWIDGETSIZE_MAX, _QWIDGETSIZE_MAX)
            pol = QtWidgets.QSizePolicy
            self.setSizePolicy(pol.Preferred, pol.Fixed) if orientation == "h" else self.setSizePolicy(pol.Fixed, pol.Preferred)
            self._set_arrow_icons()
            self.updateGeometry()
            self.relayout()

        def set_mode(self, mode):
            mode = normalise_overflow_mode(mode)
            if mode != self.mode:
                self.mode = mode
                self.first = 0
                self.updateGeometry()
                self.relayout()

        # ---- sizes ---------------------------------------------------------- #
        def _gaps(self):
            d = studio_theme.density()
            return (0, 0) if self.kind == "tabs" else (d["click_gap"], d["group_gap"])

        def _laid(self):
            """[(widget, along, across, lead, new_group)] for the items the application shows."""
            gap, ggap = self._gaps()
            out = []
            for g in self.groups:
                start = True
                for w in g:
                    if w.isHidden():
                        continue
                    s = w.sizeHint().expandedTo(w.minimumSize()).boundedTo(w.maximumSize())
                    along, across = (s.width(), s.height()) if self.orientation == "h" else (s.height(), s.width())
                    newg = start and bool(out)
                    out.append((w, along, across, ggap if newg else gap, newg))
                    start = False
            return out

        def _row(self, laid):
            if self.thickness:
                return int(self.thickness)
            return max([a for _w, _l, a, _g, _n in laid] or [studio_theme.density()["icon_btn"]])

        def _line_gap(self):
            return self._gaps()[0]

        def sizeHint(self):
            laid = self._laid()
            ext = [x[1] for x in laid]
            along = _span(ext, [x[3] for x in laid], list(range(len(laid)))) if laid else 0
            k = max(1, self.state["lines"])
            across = k * self._row(laid) + (k - 1) * self._line_gap()
            return QtCore.QSize(along, across) if self.orientation == "h" else QtCore.QSize(across, along)

        def minimumSizeHint(self):
            laid = self._laid()
            along = (2 * scroll_arrow() + max(x[1] for x in laid)) if laid else 0
            k = max(1, self.state["lines"])
            across = k * self._row(laid) + (k - 1) * self._line_gap()
            return QtCore.QSize(along, across) if self.orientation == "h" else QtCore.QSize(across, along)

        # ---- placing -------------------------------------------------------- #
        def relayout(self):
            if self._busy:
                return
            self._busy = True
            try:
                self._place()
            finally:
                self._busy = False

        def _queue(self):
            if not self._queued:
                self._queued = True
                QtCore.QTimer.singleShot(0, self._run_queued)

        def _run_queued(self):
            self._queued = False
            try:
                self.relayout()
            except RuntimeError:                     # the strip went with its panel
                pass

        def _place(self):
            laid = self._laid()
            h = self.orientation == "h"
            length = self.width() if h else self.height()
            arrow = scroll_arrow()
            t = self._row(laid)
            lg = self._line_gap()
            plan = flow_plan([x[1] for x in laid], length, self.mode, [x[3] for x in laid], WRAP_MAX_LINES)
            lines = plan["lines"] or [[]]
            k = len(lines)
            across_total = k * t + (k - 1) * lg
            if self.sizes_itself:                    # the row / column is exactly as thick as its lines
                if h and (self.minimumHeight() != across_total or self.maximumHeight() != across_total):
                    self.setFixedHeight(across_total)
                elif not h and (self.minimumWidth() != across_total or self.maximumWidth() != across_total):
                    self.setFixedWidth(across_total)
            pos, self._seps, shown = {}, [], []
            first = last_first = 0
            sl = plan["scroll"]
            for li, line in enumerate(lines):
                c0 = li * (t + lg)
                if li == sl:
                    sub = [laid[i] for i in line]
                    first, end, last_first = scroll_reach([x[1] for x in sub], [0] + [x[3] for x in sub[1:]],
                                                          max(0, length - 2 * arrow), self.first)
                    self.first = first
                    vis, m = line[first:end], arrow
                else:
                    vis, m = line, 0
                for j, i in enumerate(vis):
                    w, along, across, lead, newg = laid[i]
                    if j:
                        if newg:
                            self._seps.append((m + lead // 2, c0, t))
                        m += lead
                    pos[i] = (m, c0, along, across)
                    m += along
                    shown.append(w)
            for i, (w, along, across, _lead, _newg) in enumerate(laid):
                if i not in pos:
                    w.move(_FAR, _FAR)               # out of sight; still reachable from the panel's menu
                    continue
                a, c0, along, across = pos[i]
                if self.kind == "tabs" or w.minimumSize() != w.maximumSize():
                    across = t                       # a tab and a button with text fill the row
                c = c0 + max(0, (t - across) // 2)
                w.setGeometry(a, c, along, across) if h else w.setGeometry(c, a, across, along)
            if sl is not None:
                c0 = sl * (t + lg)
                for b, a in ((self.b_back, 0), (self.b_on, max(0, length - arrow))):
                    b.setGeometry(a, c0, arrow, t) if h else b.setGeometry(c0, a, t, arrow)
                    b.show(); b.raise_()
                self.b_back.setEnabled(first > 0)
                self.b_on.setEnabled(first < last_first)
            else:
                self.b_back.hide(); self.b_on.hide()
                self.first = 0
            if self.state["lines"] != k:
                self.updateGeometry()
            self.state = {"lines": k, "scrolling": sl is not None, "first": first, "last_first": last_first,
                          "shown": shown, "plan": plan}
            self.update()

        # ---- moving --------------------------------------------------------- #
        def scroll_by(self, step):
            if not self.state["scrolling"]:
                return
            self.first = max(0, min(self.first + int(step), self.state["last_first"]))
            self.relayout()

        def ensure_visible(self, w):
            """Bring ``w`` into sight when it is scrolled away (a chosen tab, a tool that got the focus)."""
            if not self.state["scrolling"] or w in self.state["shown"] or w not in self.items():
                return
            for _ in range(len(self.items()) + 1):
                before = self.first
                order = [x[0] for x in self._laid()]
                shown = self.state["shown"]
                if w in shown:
                    break
                ahead = order.index(w) > max(order.index(s) for s in shown) if shown else True
                self.first = max(0, self.first + (1 if ahead else -1))
                self.relayout()
                if self.first == before:
                    break

        # ---- Qt events ------------------------------------------------------ #
        def eventFilter(self, obj, ev):
            t = ev.type()
            if t in (QtCore.QEvent.Show, QtCore.QEvent.Hide) and not self._busy:
                self.updateGeometry()
                self._queue()
            elif t == QtCore.QEvent.Resize and not self._busy:
                self._queue()
            elif t == QtCore.QEvent.FocusIn:
                self.ensure_visible(obj)
            return False

        def resizeEvent(self, ev):
            super().resizeEvent(ev)
            self.relayout()

        def wheelEvent(self, ev):
            if not self.state["scrolling"]:
                ev.ignore()
                return
            d = ev.angleDelta()
            v = d.y() or d.x()
            if v:
                self.scroll_by(-1 if v > 0 else 1)
            ev.accept()

        def restyle(self, tr=None):
            if tr is not None:
                self.tr = tr
            p = studio_theme.PALETTES[studio_theme.current_name()]
            self.setStyleSheet(
                "QToolButton#flow_back, QToolButton#flow_on { background:%(chrome)s; border:1px solid %(line)s; "
                "border-radius:2px; padding:0px; margin:0px; }\n"
                "QToolButton#flow_back:hover, QToolButton#flow_on:hover { border-color:%(accent)s; }\n"
                "QToolButton#flow_back:disabled, QToolButton#flow_on:disabled { background:transparent; "
                "border-color:transparent; }\n" % p)
            self.b_back.setToolTip(self.tr(S_SCROLL_BACK)); self.b_back.setAccessibleName(self.tr(S_SCROLL_BACK))
            self.b_on.setToolTip(self.tr(S_SCROLL_ON)); self.b_on.setAccessibleName(self.tr(S_SCROLL_ON))
            self._set_arrow_icons()
            self.updateGeometry()
            self.relayout()

        def _set_arrow_icons(self):
            p = studio_theme.PALETTES[studio_theme.current_name()]
            side = max(8, scroll_arrow() - 2)
            for b, name in ((self.b_back, "scroll_back"), (self.b_on, "scroll_on")):
                g = name + ("_v" if self.orientation == "v" else "_h")
                ic = QtGui.QIcon()
                ic.addPixmap(_glyph(g, p["text"]), QtGui.QIcon.Normal)
                ic.addPixmap(_glyph(g, p["off"]), QtGui.QIcon.Disabled)
                b.setIcon(ic)
                b.setIconSize(QtCore.QSize(side, side))

        def paintEvent(self, _ev):
            if not self._seps and not self.overlay:
                return
            p = studio_theme.PALETTES[studio_theme.current_name()]
            painter = QtGui.QPainter(self)
            if self.overlay:                         # over an image: a ground of its own
                ground = QtGui.QColor(p["chrome"]); ground.setAlpha(220)
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                painter.setPen(QtCore.Qt.NoPen); painter.setBrush(ground)
                painter.drawRoundedRect(QtCore.QRectF(self.rect()), 5, 5)
            painter.setPen(QtGui.QPen(QtGui.QColor(p["line"]), 1))
            for a, c0, t in self._seps:              # a thin line between two groups
                if self.orientation == "h":
                    painter.drawLine(a, c0 + 3, a, c0 + t - 4)
                else:
                    painter.drawLine(c0 + 3, a, c0 + t - 4, a)
            painter.end()

    class FlowTab(QtWidgets.QAbstractButton):
        """One tab of a TabRow, drawn by the strip: the text is never cut and never loses an '&' (it is
        not a mnemonic here), a vertical tab is turned 90 degrees and read from the bottom up (the
        user's choice). Its text is kept apart from QAbstractButton.setText (which would make '&' a key)."""

        def __init__(self, row, index, text, parent=None):
            super().__init__(parent)
            self.setObjectName("flow_tab")
            self.row, self.index, self.label = row, index, str(text)
            self.vertical = False
            self.setCheckable(True)
            self.setFocusPolicy(QtCore.Qt.NoFocus)
            self.setAccessibleName(self.label)
            self.setToolTip(self.label)
            self.setAttribute(QtCore.Qt.WA_Hover, True)
            self._press = None

        def sizeHint(self):
            fm = self.fontMetrics()
            d = studio_theme.density()
            along = fm.horizontalAdvance(self.label) + 4 * d["unit"] + 2
            across = fm.height() + 2 * d["tab_v"] + 2
            return QtCore.QSize(across, along) if self.vertical else QtCore.QSize(along, across)

        def minimumSizeHint(self):
            return self.sizeHint()

        def paintEvent(self, _ev):
            p = studio_theme.PALETTES[studio_theme.current_name()]
            painter = QtGui.QPainter(self)
            r = self.rect()
            on = self.isChecked()
            painter.fillRect(r, QtGui.QColor(p["bg2"] if on else (p["hover"] if self.underMouse() else p["bg1"])))
            painter.setPen(QtGui.QColor(p["line"]))
            painter.drawRect(r.adjusted(0, 0, -1, -1))
            if on:                                   # the chosen tab: the accent edge, as Qt's tab had
                edge = QtCore.QRect(0, 0, 2, r.height()) if self.vertical else QtCore.QRect(0, 0, r.width(), 2)
                painter.fillRect(edge, QtGui.QColor(p["accent"]))
                if self.row is not None and self.row.has_focus():
                    pen = QtGui.QPen(QtGui.QColor(p["accent_hi"]), 1, QtCore.Qt.DotLine)
                    painter.setPen(pen)
                    painter.drawRect(r.adjusted(3, 3, -4, -4))
            painter.setPen(QtGui.QColor(p["text"] if on else p["muted"]))
            painter.setFont(self.font())
            if self.vertical:
                painter.translate(0, r.height())
                painter.rotate(-90)
                box = QtCore.QRect(0, 0, r.height(), r.width())
            else:
                box = QtCore.QRect(r)
            painter.drawText(box, QtCore.Qt.AlignCenter, self.label)     # no mnemonic flag: '&' is drawn
            painter.end()

        def mousePressEvent(self, ev):
            if ev.button() == QtCore.Qt.LeftButton:
                self._press = ev.position().toPoint()
            super().mousePressEvent(ev)

        def mouseMoveEvent(self, ev):
            if self._press is not None and ev.buttons() & QtCore.Qt.LeftButton:
                here = ev.position().toPoint()
                if (here - self._press).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                    strip = self.parentWidget()
                    at = self.mapTo(strip, here)
                    margin = 2 * max(8, (self.height() if not self.vertical else self.width()))
                    if not strip.rect().adjusted(-margin, -margin, margin, margin).contains(at):
                        self._press = None
                        self.setDown(False)
                        if self.row is not None:          # pulled out of the row: a separate window (P18-4)
                            self.row.drag_out(self.index, ev.globalPosition().toPoint())
                        return
            super().mouseMoveEvent(ev)

        def mouseReleaseEvent(self, ev):
            self._press = None
            super().mouseReleaseEvent(ev)

        def contextMenuEvent(self, ev):
            if self.row is not None:                     # a tab's right-click = that panel's menu (P18-3)
                self.row.menu_for(self.index, ev.globalPos())
            ev.accept()

    class TabRow(QtCore.QObject):
        """The tab row of one group of tabbed panels: a FlowStrip of FlowTabs over Qt's QTabBar."""

        def __init__(self, win, bar):
            super().__init__(bar)
            self.win, self.bar = win, bar
            self.strip = FlowStrip("tabs", "tabs", bar)
            self.tabs, self.sig, self.qss = [], None, ""
            self.t1, self.off = None, None
            self.strip.show()
            bar.installEventFilter(self)
            bar.currentChanged.connect(self.follow_current)
            bar.setProperty("fsTabRow", True)

        def vertical(self):
            return self.bar.shape() in (QtWidgets.QTabBar.RoundedWest, QtWidgets.QTabBar.RoundedEast,
                                        QtWidgets.QTabBar.TriangularWest, QtWidgets.QTabBar.TriangularEast)

        def has_focus(self):
            return self.bar.hasFocus()

        def signature(self):
            b = self.bar
            return (b.count(), tuple(b.tabText(i) for i in range(b.count())), b.shape())

        def _set_qss(self, qss):
            if qss != self.qss:
                self.qss = qss
                self.bar.setStyleSheet(qss)

        def _measure(self):
            """One row's thickness = Qt's bar as it is without the extra rows."""
            self._set_qss("")
            s = self.bar.sizeHint()
            self.t1 = max(1, s.width() if self.vertical() else s.height())
            self.off = None

        def rebuild(self):
            for t in self.tabs:
                t.setParent(None)
                t.deleteLater()
            v = self.vertical()
            self.tabs = []
            for i in range(self.bar.count()):
                tab = FlowTab(self, i, self.bar.tabText(i))
                tab.vertical = v
                tab.setFont(self.bar.font())
                tab.clicked.connect(lambda _c=False, k=i: self.select(k))
                self.tabs.append(tab)
            self.strip.set_groups([self.tabs])
            self._measure()
            self.follow_current(self.bar.currentIndex())

        def place(self):
            st = _state(self.win)
            sig = self.signature()
            if sig != self.sig:
                self.sig = sig
                self.rebuild()
            if self.t1 is None:
                self._measure()
            self.strip.tr = st["tr"]
            self.strip.set_orientation("v" if self.vertical() else "h")
            self.strip.set_mode(st.get("overflow_mode", "scroll"))
            self.strip.thickness = self.t1
            self.strip.setGeometry(self.bar.rect())
            self.strip.raise_()
            self.strip.relayout()
            self._rows(self.strip.state["lines"])

        def _rows(self, k):
            """Make Qt's bar as thick as ``k`` rows (it is only the room; the rows are the strip's)."""
            if k <= 1:
                self._set_qss("")
                return
            side = "width" if self.vertical() else "height"
            if self.off is None:                     # what the style adds to a tab's min-height / min-width
                probe = 4 * self.t1
                self._set_qss("QTabBar::tab { min-%s: %dpx; }" % (side, probe))
                s = self.bar.sizeHint()
                self.off = (s.width() if self.vertical() else s.height()) - probe
            self._set_qss("QTabBar::tab { min-%s: %dpx; }" % (side, max(1, k * self.t1 - self.off)))

        def follow_current(self, index):
            for t in self.tabs:
                t.setChecked(t.index == index)
            if 0 <= index < len(self.tabs):
                self.strip.ensure_visible(self.tabs[index])

        def select(self, index):
            self.bar.setCurrentIndex(index)          # Qt raises the panel of that tab
            self.follow_current(self.bar.currentIndex())

        def key_at(self, index):
            """The panel key of tab ``index`` (Qt keeps the dock's address as the tab's data)."""
            data = self.bar.tabData(index)
            try:
                import shiboken6   # noqa: PLC0415
                for key, dock in self.win._docks.items():
                    if shiboken6.getCppPointer(dock)[0] == data:
                        return key
            except Exception:                        # noqa: BLE001 - fall back on the name
                pass
            text = self.bar.tabText(index)
            for key, dock in self.win._docks.items():
                if dock.windowTitle() == text:
                    return key
            return None

        def menu_for(self, index, gpos):
            key = self.key_at(index)
            bar = _state(self.win)["titles"].get(key) if key else None
            if bar is None:
                return None
            bar.fill_menu()
            menu = bar.b_menu.menu()
            _state(self.win)["open_menu"] = menu
            menu.popup(gpos)
            return menu

        def drag_out(self, index, gpos):
            key = self.key_at(index)
            if key is None:
                return None
            toggle_float(self.win, key, True)
            dock = self.win._docks[key]
            dock.move(gpos - QtCore.QPoint(40, 10))
            _keep_on_screen(self.win, dock)
            sync(self.win)
            return dock

        def eventFilter(self, obj, ev):
            t = ev.type()
            if t in (QtCore.QEvent.Resize, QtCore.QEvent.Show, QtCore.QEvent.FontChange):
                QtCore.QTimer.singleShot(0, self._safe_place)
            elif t in (QtCore.QEvent.FocusIn, QtCore.QEvent.FocusOut):
                for tab in self.tabs:
                    tab.update()
            return False

        def _safe_place(self):
            try:
                self.place()
            except RuntimeError:                     # the bar went with the window
                pass

    _FLOW.update(FlowStrip=FlowStrip, FlowTab=FlowTab, TabRow=TabRow)
    return _FLOW


def _holding(start, target):
    """(layout, index) of the item that holds ``target`` (a widget or a layout) under ``start``."""
    stack = [start] if start is not None else []
    while stack:
        lay = stack.pop()
        for i in range(lay.count()):
            it = lay.itemAt(i)
            if it.widget() is target or it.layout() is target:
                return lay, i
            if it.layout() is not None:
                stack.append(it.layout())
    return None, -1


def declare_strip(win, key, row, body=None, shape=None, root=None):
    """Panel ``key`` declares its tool strip (the ONE door; register_panel(strip=...) calls it).

    ``row``: the row layout that holds the panel's tool buttons. Every button in it (in order) goes into
    the strip; a separator line or a gap of 6 px or more between two of them starts a new group; the
    rest of the row (a box, a label) stays where it is. ``body``: the widget the strip stands to the
    left of when the panel is wide (None: the whole panel). ``shape``: the widget whose width and height
    decide the side (None: the dock). ``root``: the panel's top widget when ``body`` is None and the
    panel is not a dock. Returns the FlowStrip (calling again for the same key returns the first one)."""
    from PySide6 import QtCore, QtWidgets   # noqa: PLC0415
    st = _state(win)
    decl = st.setdefault("strip_decl", {})
    if decl.get(key, {}).get("strip") is not None:
        return decl[key]["strip"]
    FlowStrip = flow_classes()["FlowStrip"]
    dock = win._docks.get(key) if hasattr(win, "_docks") else None
    shape = shape if shape is not None else dock
    if shape is None:
        raise ValueError("strip of %r: no dock of that name, so a shape widget is needed" % (key,))
    # 1. the buttons, in groups; separators between them leave the row
    groups, cur, drop, first_at = [], [], [], None
    items = [row.itemAt(i) for i in range(row.count())]
    for i, it in enumerate(items):
        w = it.widget()
        if isinstance(w, QtWidgets.QAbstractButton):
            cur.append(w)
            first_at = i if first_at is None else first_at
        elif cur and any(isinstance(x.widget(), QtWidgets.QAbstractButton) for x in items[i + 1:]):
            line = isinstance(w, QtWidgets.QFrame) and w.frameShape() == QtWidgets.QFrame.VLine
            gap = it.spacerItem() is not None
            if line or gap:
                drop.append(i)
                if line or it.sizeHint().width() >= 6 or it.spacerItem().expandingDirections():
                    if cur:
                        groups.append(cur)
                    cur = []
            else:                                    # another kind of widget between buttons: a new group
                groups.append(cur)
                cur = []
    if cur:
        groups.append(cur)
    buttons = [b for g in groups for b in g]
    if not buttons:
        raise ValueError("strip of %r: the row holds no buttons" % (key,))
    for i in sorted(drop + [row.indexOf(b) for b in buttons], reverse=True):
        it = row.takeAt(i)
        w = it.widget() if it is not None else None
        if w is not None and not isinstance(w, QtWidgets.QAbstractButton):
            w.hide()
            w.setParent(None)
    strip = FlowStrip("tools", key)
    strip.set_groups(groups)
    row.insertWidget(first_at - sum(1 for i in drop if i < first_at), strip)
    slot = row.indexOf(strip)
    # 2. the row's home: a widget of its own, so that it can step aside when the strip is on the left
    parent = row.parent()
    if not isinstance(parent, QtWidgets.QBoxLayout):
        raise TypeError("strip of %r: its row must sit in a box layout, not %r" % (key, type(parent).__name__))
    at = next(i for i in range(parent.count()) if parent.itemAt(i).layout() is row)
    stretch = parent.stretch(at)
    m = row.contentsMargins()
    parent.takeAt(at)
    row.setParent(None)
    home = QtWidgets.QWidget()
    home.setObjectName("strip_home")
    home.setLayout(row)
    row.setContentsMargins(m)
    home.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
    parent.insertWidget(at, home, stretch)
    # 3. the left column: the body (or the whole panel) gets a column on its left for the strip
    host = QtWidgets.QWidget()
    host.setObjectName("strip_host")
    hl = QtWidgets.QHBoxLayout(host)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(studio_theme.density()["click_gap"])
    left = QtWidgets.QVBoxLayout()
    left.setContentsMargins(0, 0, 0, 0)
    hl.addLayout(left)
    if body is None:
        top = root if root is not None else (dock.widget() if dock is not None else None)
        if top is None:
            raise ValueError("strip of %r: no panel widget to stand beside" % (key,))
        if dock is not None and dock.widget() is top:
            dock.setWidget(host)
        hl.addWidget(top, 1)
        top.show()
        body = top
        host._fs_body = top                      # tighten() works on the panel, not on the strip's host
    else:
        lay, i = _holding(body.parentWidget().layout() if body.parentWidget() is not None else None, body)
        if not isinstance(lay, QtWidgets.QBoxLayout):
            raise TypeError("strip of %r: its body must sit in a box layout" % (key,))
        stretch = lay.stretch(i)
        hidden = body.isHidden() and body.testAttribute(QtCore.Qt.WA_WState_ExplicitShowHide)
        lay.takeAt(i)
        host.setSizePolicy(body.sizePolicy())
        hl.addWidget(body, 1)
        lay.insertWidget(i, host, stretch)
        body.setVisible(not hidden)
    entry = {"key": key, "kind": "dock" if dock is not None else "image", "strip": strip, "row": row,
             "slot": slot, "home": home, "host": host, "left": left, "body": body, "shape": shape, "side": "top"}
    st["strips"].append(entry)
    decl[key] = {"strip": strip, "reason": None, "entry": entry}
    strip.restyle(st["tr"])
    if shape is not dock and st.get("follow") is not None:
        shape.installEventFilter(st["follow"])
    return strip


#: D24: the zoom tools of every image window, in this order (then a group gap, then save)
IMAGE_ZOOM_ORDER = ("zoom_in", "zoom_out", "fit", "actual_size")


def adopt_image_strip(win, view, key=None):
    """An image window's own tool strip (the small one over its top-left corner) becomes a FlowStrip that
    turns and scrolls like every other. Safe to call twice; returns the strip or None (no strip)."""
    from PySide6 import QtCore   # noqa: PLC0415
    st = getattr(win, "_panels", None)
    old = getattr(view, "_tools", None)
    if st is None or old is None:
        return None
    if old.objectName() == "flow_strip":
        return old
    buttons = getattr(view, "tool_buttons", None) or {}
    order = [b for b in (old.layout().itemAt(i).widget() for i in range(old.layout().count())) if b is not None]
    order = [b for b in order if b in buttons.values()]
    if not order:
        return None
    save = [b for b in order if buttons.get("save") is b]
    look = [b for b in order if b not in save]
    rank = {buttons.get(name): i for i, name in enumerate(IMAGE_ZOOM_ORDER)}
    look.sort(key=lambda b: rank.get(b, len(rank)))   # D24: the main image's order, in every image window
    st["image_seq"] = st.get("image_seq", 1) + 1
    key = key or "graphics_%d" % st["image_seq"]
    FlowStrip = flow_classes()["FlowStrip"]
    strip = FlowStrip("tools", key, view)
    strip.overlay = True
    strip.set_groups([look, save])
    old.hide()
    old.setParent(None)
    old.deleteLater()
    # ... and it goes NOW, not when the event loop turns again: left alive without its buttons, a display
    # run in the same call (open a window, then apply / run) ended in an access violation
    QtCore.QCoreApplication.sendPostedEvents(old, int(QtCore.QEvent.DeferredDelete))
    view._tools = strip
    strip.move(6, 6)
    strip.show()
    strip.raise_()
    entry = {"key": key, "kind": "overlay", "strip": strip, "shape": view, "side": "top"}
    st["strips"].append(entry)
    st.setdefault("strip_decl", {})[key] = {"strip": strip, "reason": None, "entry": entry}
    strip.restyle(st["tr"])
    if st.get("follow") is not None:
        view.installEventFilter(st["follow"])
    _place_overlay(entry)
    return strip


def _place_overlay(entry):
    strip, view = entry["strip"], entry["shape"]
    room = (view.width() if entry["side"] == "top" else view.height()) - 12
    hint = strip.sizeHint()
    if entry["side"] == "top":
        strip.resize(max(1, min(hint.width(), room)), strip.height())
    else:
        strip.resize(strip.width(), max(1, min(hint.height(), room)))
    strip.move(6, 6)
    strip.raise_()


def _turn(entry, side):
    """One strip to the left of its body as a column, or back into its row on top."""
    strip = entry["strip"]
    if entry["kind"] == "overlay":
        entry["side"] = side
        strip.set_orientation("v" if side == "left" else "h")
        _place_overlay(entry)
        return
    row, left, home = entry["row"], entry["left"], entry["home"]
    if side == "left":
        if row.indexOf(strip) >= 0:
            row.removeWidget(strip)
            left.addWidget(strip, 1)
        strip.set_orientation("v")
        rest = [row.itemAt(i).widget() for i in range(row.count())]
        home.setVisible(any(w is not None and not w.isHidden() for w in rest))
    else:
        if row.indexOf(strip) < 0:
            left.removeWidget(strip)
            row.insertWidget(min(entry["slot"], row.count()), strip)
        strip.set_orientation("h")
        home.show()
    strip.show()
    entry["side"] = side


def _alive(w):
    try:
        w.objectName()
        return True
    except RuntimeError:
        return False


def panel_ledger(win):
    """Every panel on screen and what it declared: [{"key", "kind", "strip", "reason", "shape"}].

    ``kind``: "code" (the principal dock), "dock", or "image" (the main image and every other image
    window, also a detached one). A floating panel is its dock. A strip of None comes with its reason."""
    st = _state(win)
    decl = st.get("strip_decl") or {}
    out = []
    for key, dock in win._docks.items():
        d = decl.get(key) or {}
        out.append({"key": key, "kind": "code" if key in PRINCIPAL else "dock", "strip": d.get("strip"),
                    "reason": d.get("reason"), "shape": dock})
    for entry in st["strips"]:
        if entry["kind"] in ("image", "overlay") and _alive(entry["shape"]):
            out.append({"key": entry["key"], "kind": "image", "strip": entry["strip"], "reason": None,
                        "shape": entry["shape"]})
    return out


def relayout(win):
    """Every declared strip takes the side its panel's shape asks for (or the user's fixed side) and the
    overflow mode; every tab row of tabbed panels likewise. Safe at any time; nothing before ``install``."""
    from PySide6 import QtCore, QtWidgets   # noqa: PLC0415
    st = getattr(win, "_panels", None)
    if st is None:
        return {}
    mode, overflow = st["strip_mode"], st.get("overflow_mode", "scroll")
    theme_mdi(win)                               # an image window made since: its title in role colours (D17)
    for view in win.findChildren(QtWidgets.QGraphicsView):          # image windows made since (or detached)
        tools = getattr(view, "_tools", None)
        if tools is not None and _alive(tools) and tools.objectName() != "flow_strip":
            adopt_image_strip(win, view)
    keep = []
    for entry in st["strips"]:
        shape = entry["shape"]
        if not _alive(shape) or not _alive(entry["strip"]):
            continue                                 # an image window that was closed
        keep.append(entry)
        entry["strip"].set_mode(overflow)
        if shape.isHidden() or shape.width() <= 0:
            continue
        side = strip_side(shape.width(), shape.height(), entry["side"], mode)
        if side != entry["side"]:
            _turn(entry, side)
        elif entry["kind"] == "overlay":
            _place_overlay(entry)
    st["strips"] = keep
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
    rows = st.setdefault("tab_rows", {})
    TabRow = flow_classes()["TabRow"]
    for bar in win.findChildren(QtWidgets.QTabBar):
        if bar.parentWidget() is win:                    # the tab bars of tabbed panels
            bar.setElideMode(QtCore.Qt.ElideNone)        # a name is never cut
            bar.setUsesScrollButtons(True)               # Qt's own scrolling, under the row that is drawn
            bar.setTabsClosable(False)                   # a tab is never closed (P18-3)
            if st.get("tab_keys") is not None and not bar.property("fsTabKeys"):
                bar.setProperty("fsTabKeys", True)
                bar.installEventFilter(st["tab_keys"])
            row = rows.get(id(bar))
            if row is None or row.bar is not bar:
                row = rows[id(bar)] = TabRow(win, bar)
            row.place()
    st["tab_sides"] = areas
    for bar in st["titles"].values():               # tabbed or not: the band's name follows (D59)
        bar.follow()
    again = st.pop("restore_again", None) if win.isVisible() else None
    if again is not None:                        # the sizes as saved, now that every strip has its side
        win._applying_layout = True
        try:
            win.restoreState(again)
        finally:
            win._applying_layout = False
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


def set_overflow_mode(win, mode, settings=None):
    """"scroll" or "wrap" for every tool strip and every tab row at once (saved when ``settings`` is
    given). Returns how many strips and tab rows now use it."""
    st = _state(win)
    st["overflow_mode"] = normalise_overflow_mode(mode)
    if settings is not None:
        settings.setValue(OVERFLOW_KEY, st["overflow_mode"])
    for m, action in (st.get("overflow_actions") or {}).items():
        action.setChecked(m == st["overflow_mode"])
    relayout(win)
    return sum(1 for s in all_strips(win) if s.mode == st["overflow_mode"])


def all_strips(win):
    """Every FlowStrip of the window: the declared tool strips and the tab rows."""
    st = _state(win)
    out = [e["strip"] for e in st["strips"] if _alive(e["strip"])]
    out += [r.strip for r in (st.get("tab_rows") or {}).values() if _alive(r.bar)]
    return out


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
#: how a job can end (D99). The corner shows a mark and a word for each: a square + "Done", a square +
#: "Stopped", a cross in the error colour + "Failed".
BRAND_END = ("done", "stopped", "failed")
BRAND_MARKS = {"busy": "mark_run", "done": "mark_done", "stopped": "mark_done", "failed": "mark_fail"}
S_DONE, S_STOPPED, S_FAILED = "Done", "Stopped", "Failed"
STRINGS = STRINGS + (S_DONE, S_STOPPED, S_FAILED)


def end_state(ok):
    """How a job ended, from what its caller says: True / "done", "stopped", False / "failed"."""
    if isinstance(ok, str) and ok in BRAND_END:
        return ok
    return "done" if ok else "failed"


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
            self.shown_text, self.shown_mark = name, None    # what the last paint wrote / which mark it drew

        # ---- the door (any thread) ---------------------------------------- #
        def begin(self, text, total=None):
            token = next(self.tokens)
            self._call.emit("begin", (token, str(text), total, _time.monotonic()))
            return token

        def update_job(self, token, done=None, text=None):
            self._call.emit("update", (token, done, text))

        def end(self, token, ok=True, text=None):
            """``ok``: True / False, or how it ended - "done", "stopped", "failed" (BRAND_END)."""
            self._call.emit("end", (token, end_state(ok), text))

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
                token, how, text = args
                job = self.jobs.pop(token, None)
                if job is None:
                    return
                shown = (now - job["t0"]) * 1000.0 >= self.show_after_ms
                if not self.jobs and (shown or how != "done"):   # a stop and a failure are always said, however short
                    word = {"done": S_DONE, "stopped": S_STOPPED, "failed": S_FAILED}[how]
                    self.flash = (text or self.tr(word), how)
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
            """What the frame shows now: ("idle", name) / ("busy", text, fraction or None, others) /
            ("done" | "stopped" | "failed", text)."""
            now = _time.monotonic()
            live = [(t, j) for t, j in self.jobs.items() if (now - j["t0"]) * 1000.0 >= self.show_after_ms]
            if live:
                token, job = max(live)                           # the newest job speaks; the others are counted
                frac = None
                if job["total"]:
                    frac = max(0.0, min(1.0, float(job["done"]) / float(job["total"])))
                return ("busy", job["text"], frac, len(live) - 1)
            if self.flash is not None:
                return (self.flash[1], self.flash[0])
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
            elif cur[0] == "failed":                             # the error colour as a line, never an amber ground (D99)
                painter.fillRect(QtCore.QRect(0, r.height() - 2, r.width(), 2), QtGui.QColor(p["err"]))
            pm = self.icon_frame(self.frame if cur[0] == "busy" else 0)
            if pm is not None:                                   # the icon stays; while busy it is the flip book
                painter.drawPixmap(QtCore.QRect(6, (r.height() - 22) // 2, 22, 22), pm)
                x = 34
            self.shown_mark = None
            if cur[0] == "idle":
                painter.setFont(self.name_font); painter.setPen(QtGui.QColor(p["brand"]))
                text = cur[1]
            else:                                                # shape + word, not colour alone; the shape is
                painter.setFont(self.job_font); painter.setPen(QtGui.QColor(p["text"]))   # drawn, not a character (D130)
                self.shown_mark = BRAND_MARKS[cur[0]]
                painter.drawPixmap(QtCore.QRect(x, (r.height() - 12) // 2, 12, 12),
                                   _glyph(self.shown_mark, p["err"] if cur[0] == "failed" else p["text"], 12))
                x += 16
                text = cur[1]
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


def follow_progress(brand, bar, label=None, outcome=None):
    """Let the brand corner follow an existing QProgressBar (shown = a job begins, value = how far,
    hidden = it ended) and, when given, the label that says what is running. ``outcome``: a callable
    asked when the bar hides - "done", "stopped" or "failed" (D99: the corner says how the job really
    ended; without one, or when it fails, the job counts as done). Returns the filter (keep a reference)."""
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
                try:
                    how = end_state(outcome()) if outcome is not None else "done"
                except Exception:                    # noqa: BLE001 - no answer: as before
                    how = "done"
                brand.end(token, how)                # the word of the outcome ("Stopped"), not the last progress text
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
    _copy_button(button, act, st.get("tr"))
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


def _copy_button(button, act, tr=None):
    text = (button.text() or "").replace("&", "").strip()
    tip = (button.toolTip() or "").strip()
    own = button.property("fsName")              # D98: the function's own short name (BUTTON_NAMES)
    if own:
        text = (tr or (lambda s: s))(str(own))
    elif not text or text in ("\u2026", "+", "\u2212", "-"):         # an icon / a sign: the tool tip names it
        text = short_name(tip) or button.accessibleName() or text
    act.setText(label_text(text))
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
    tr = _state(win).get("tr")
    for act, button in list((_state(win).get("button_of") or {}).items()):
        try:
            _copy_button(button, act, tr)
            n += 1
        except RuntimeError:                     # the button was destroyed with its panel
            pass
    return n


#: D98: the name of the menu entry made from a panel button that has no QAction (P15-4: one name per
#: function - not the button's whole hint, not one bare word). {(panel, button name in win._panel_buttons): name}
BUTTON_NAMES = {
    ("program", "run"): "Run the code",
    ("program", "continue"): "Continue to the next breakpoint",
    ("program", "step"): "Step one line",
    ("program", "reset"): "Clear the run marks",
    ("program", "apply"): "Apply the code to the pipeline",
    ("program", "sync"): "Regenerate the code from the pipeline",
    ("variables", "display_new"): "Display in a new window",
    ("variables", "display_here"): "Display in the current window",
    ("variables", "watch_remove"): "Remove the watch row",
    ("operators", "insert"): "Insert into the pipeline",
    ("operators", "run_once"): "Run once (pipeline unchanged)",
    ("operators", "help"): "Operator help",
}
STRINGS = STRINGS + tuple(BUTTON_NAMES.values())

#: How many of its own functions a panel's menu offers (user, 2026-11-13: "3 to 8")
MENU_OWN_MIN, MENU_OWN_MAX = 3, 8


def register_panel(win, key, status=None, actions=None, strip=None, no_strip=None, strip_equiv=None):
    """What one panel shows in its title band, offers in its menu button and uses as its tool strip —
    the ONE place a panel (also one added later: console, parameters, call stack) says so.

    ``strip``: (row, body) = the panel's tool strip (declare_strip, once per panel). ``no_strip``: why
    the panel has none (panel_ledger keeps the reason; a panel with neither fails the gate). Every
    button of the strip is also an entry of the menu (A2: a tool scrolled out of sight is one menu entry
    away): ``strip_equiv[button]`` (the window's QAction for the same function), else the button's
    default action, else button_action(win, button); the ones ``actions`` lacks are added at the end.

    ``status``: a list of ``{"id": str, "text": callable -> str, "tip": str, "priority": int}``. Each
    is a small read-out to the right of the name; ``text()`` is asked four times a second while the
    panel is shown ("" hides the item). When the band is too narrow, items with the LOWEST priority
    go first (whole items, never cut text); what was dropped is listed at the top of the menu.
    ``actions``: QActions (the same objects the panel's buttons / the main menu use, so name, key
    and enabled state cannot disagree); ``None`` in the list is a separator. Calling again replaces."""
    from PySide6 import QtWidgets   # noqa: PLC0415
    st = _state(win)
    if key not in win._docks:
        raise KeyError("no panel named %r" % (key,))
    actions = list(actions or [])
    if strip is not None:
        row, body = strip
        fs = declare_strip(win, key, row, body)
        own, extra = [a for a in actions if a is not None], []
        reach = st.setdefault("strip_action_of", {})
        made = st.get("button_actions") or {}
        for b in fs.items():                     # the entry the panel already lists for this button comes first
            act = ((made.get(b) if made.get(b) in own else None)
                   or (b.defaultAction() if isinstance(b, QtWidgets.QToolButton) else None)
                   or (strip_equiv or {}).get(b)
                   or button_action(win, b))
            reach[b] = act
            if act not in own and act not in extra:
                extra.append(act)
        if extra:
            actions += ([None] if own else []) + extra
    elif no_strip:
        st.setdefault("strip_decl", {})[key] = {"strip": None, "reason": str(no_strip), "entry": None}
    bar = st["titles"][key]
    bar.set_registration(list(status or []), actions)
    return bar


def _default_registrations(win):
    """The panels that exist today. Values are read from the live widgets; a missing one is skipped."""
    from PySide6 import QtCore   # noqa: PLC0415
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
        if sl is None:
            return ""
        rows = [sl.item(i) for i in range(sl.count())]       # the hint row of an empty pipeline is not a stage
        return tr(S_ST_STAGES) % sum(1 for it in rows if it is not None and it.flags() != QtCore.Qt.NoItemFlags)

    def errors():
        state = getattr(win, "_state", None) or {}
        n = len(state.get("errors") or []) + len(state.get("structured_errors") or [])
        return (tr(S_ST_ERRORS) % n) if n else ""              # its cross is drawn (the item's glyph, D130)

    def variables():
        lst = (getattr(win, "_variables", None) or {}).get("list")
        return tr(S_ST_VARS) % lst.count() if lst is not None else ""

    strips = getattr(win, "_panel_strips", None) or {}         # {key: (row, body)} - studio.py declares them
    own_buttons = getattr(win, "_panel_buttons", None) or {}
    for (panel, name), text in BUTTON_NAMES.items():           # D98: the short name of each button's menu entry
        b = (own_buttons.get(panel) or {}).get(name)
        if b is not None:
            b.setProperty("fsName", text)

    def equiv(key):
        """A strip button whose function the window already has as a QAction (same name in win._actions)."""
        return {b: acts[n] for n, b in (own_buttons.get(key) or {}).items() if n in acts and b is not None}

    def register_panel(win_, key, *args, **kwargs):            # a panel this window does not have: skipped
        if key not in win_._docks:
            return
        if key in strips:
            kwargs.update(strip=strips[key], strip_equiv=equiv(key))
        else:
            kwargs.update(no_strip=STRIP_EXEMPT.get(key))
        globals()["register_panel"](win_, key, *args, **kwargs)

    register_panel(win, "program", [],
                   btn("program", "run", "continue", "step", "reset") + [None]
                   + btn("program", "apply", "sync") + [None] + pick("export", "verify_exported"))
    register_panel(win, "operators", [{"id": "shown", "text": shown_ops, "priority": 1}],
                   pick("focus_search", "op_reference", "samples"))
    register_panel(win, "pipeline", [{"id": "errors", "text": errors, "priority": 2, "glyph": ("mark_fail", "err")},
                                     {"id": "stages", "text": stages, "priority": 1}],
                   pick("run_all", "step", "reset") + [None]
                   + pick("remove", "move_up", "move_down", "duplicate_stage", "bypass"))
    register_panel(win, "variables", [{"id": "count", "text": variables, "priority": 1}],
                   btn("variables", "display_new", "display_here") + pick("viewer_3d", "feature_inspection")
                   + [None] + btn("variables", "watch_remove"))
    register_panel(win, "display", [], pick("fit", "actual_size", "zoom_in", "zoom_out", "surface_3d"))
    register_panel(win, "compare", [], pick("step", "reset") + [None] + pick("pin_a"))
    register_panel(win, "ab", [], pick("pin_a") + [None] + btn("ab", "restore", "adopt", "keep"))
    # the main image window: its strip of open / demo / save | zoom (it has no menu button; the same
    # QActions are in the File and View menus and on the image's right-click)
    if "graphics_1" in strips:
        row, body = strips["graphics_1"]
        sub = getattr(win, "_primary_gsub", None)
        shape = sub.widget() if sub is not None and sub.widget() is not None else body.parentWidget()
        fs = declare_strip(win, "graphics_1", row, body, shape=shape)
        reach = _state(win).setdefault("strip_action_of", {})
        same = equiv("graphics_1")
        for b in fs.items():
            reach[b] = same.get(b) or button_action(win, b)


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
        action.setText("%s: %s" % (tr(S_FLOAT), label_text(win._docks[key].windowTitle())))
    for key, action in (st.get("principal_actions") or {}).items():
        action.setText(label_text(win._docks[key].windowTitle()))
    for key, dock in win._docks.items():        # Qt names the show / hide entry after the title: keep its '&'
        dock.toggleViewAction().setText(label_text(dock.windowTitle()))
    drop_repeated_titles(win)
    for bar in st["titles"].values():
        bar.restyle()
    for mode, action in st["strip_actions"].items():
        action.setText(tr(S_STRIP[mode]))
    sync_button_actions(win)                     # menu entries made from buttons: the language of the moment
    rm = getattr(win, "_reduce_motion_action", None)
    if rm is not None:
        rm.setText(tr(S_REDUCE)); rm.setToolTip(tr(S_REDUCE_TIP)); rm.setStatusTip(tr(S_REDUCE_TIP))
    for mode, action in (st.get("overflow_actions") or {}).items():
        action.setText(tr(S_OVERFLOW[mode]))
    p = studio_theme.PALETTES[studio_theme.current_name()]
    for act, name in getattr(win, "_fs_glyph_actions", None) or []:
        try:
            act.setIcon(_icon(name, p["text"], p["accent"]))
        except RuntimeError:
            pass
    compose_top_tips(win, tr)
    for entry in st["strips"]:                  # every tool strip: its scroll buttons' look and words
        if _alive(entry["strip"]):
            entry["strip"].restyle(tr)
    for row in (st.get("tab_rows") or {}).values():
        if _alive(row.bar):
            row.sig, row.t1 = None, None        # rebuilt in the new font / language at the next place()
            row.strip.restyle(tr)
    tighten(win)
    relayout(win)
    sync(win)
    from PySide6 import QtWidgets   # noqa: PLC0415
    for b in win.findChildren(QtWidgets.QAbstractButton):    # D03: buttons disabled before the filter came
        if not b.isEnabled():
            fix_hand(b)


def install(win, tr, settings=None):
    """Build the panel bar, the title bands and the menu entries, and put the window into the
    first-run arrangement (image + code). Call once, after every dock exists and before the
    default state is captured."""
    from PySide6 import QtCore, QtGui, QtWidgets   # noqa: PLC0415
    missing = set(win._docks) - set(RAIL_ORDER)
    if missing:
        raise KeyError("panels without a place on the panel bar: %s" % sorted(missing))

    class TitleBar(QtWidgets.QWidget):
        """Name, then the panel's status items, then space; on the right separate window / dock,
        hide, and the menu button at the right end (name | status | float x | menu, D105). A
        principal has no hide button (D104). Mouse presses on the name, the status items and the
        space are left to QDockWidget (labels do not take them), so dragging and double-click keep
        working."""

        def __init__(self, key, dock):
            super().__init__(dock)
            self.key, self.dock = key, dock
            self.setObjectName("dock_title")
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            lay = QtWidgets.QHBoxLayout(self)
            lay.setContentsMargins(10, 0, 2, 1); lay.setSpacing(studio_theme.density()["click_gap"])
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
            self.b_menu.setCursor(QtCore.Qt.PointingHandCursor)      # its three lines are drawn in restyle (D130)
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
            self.b_close = None                                  # a principal is never put away (D104)
            if key not in PRINCIPAL:
                self.b_close = QtWidgets.QToolButton(); self.b_close.setObjectName("dock_title_close")
            for b in self.buttons():
                if b is not self.b_menu:
                    b.setAutoRaise(True); b.setFocusPolicy(QtCore.Qt.NoFocus)
                    b.setCursor(QtCore.Qt.PointingHandCursor); b.setProperty("keepSize", True)
            lay.addWidget(self.label); lay.addLayout(self.status_box); lay.addStretch(1)
            for b in self.buttons():                            # float, hide, then the menu at the right end
                lay.addWidget(b)
            self.b_float.clicked.connect(lambda _c=False: toggle_float(win, key))
            if self.b_close is not None:
                self.b_close.clicked.connect(lambda _c=False: dock.hide())
            dock.windowTitleChanged.connect(lambda _t: self.restyle())
            dock.topLevelChanged.connect(lambda _f: sync(win))

        def buttons(self):
            """The band's buttons from left to right: separate window, hide (not on a principal), menu."""
            return [b for b in (self.b_float, self.b_close, self.b_menu) if b is not None]

        def sizeHint(self):                      # QDockWidget asks the hint (not the fixed size) for the band
            return QtCore.QSize(super().sizeHint().width(), studio_theme.density()["title_band"] - 2)

        def minimumSizeHint(self):
            return QtCore.QSize(40, studio_theme.density()["title_band"] - 2)

        def set_registration(self, status, actions):
            for item in self.status:
                item["label"].deleteLater()
                if item["mark"] is not None:
                    item["mark"].deleteLater()
            self.status, self.actions = [], actions
            for spec in status:
                mark = None
                if spec.get("glyph"):                # a drawn mark before the words: (glyph name, colour role)
                    mark = QtWidgets.QLabel(); mark.setObjectName("dock_title_mark_" + str(spec["id"]))
                    mark.setFixedSize(12, 12); mark.setScaledContents(True)
                    self.status_box.addWidget(mark)
                lab = QtWidgets.QLabel(""); lab.setObjectName("dock_title_status_" + str(spec["id"]))
                lab.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
                self.status_box.addWidget(lab)
                self.status.append({"id": str(spec["id"]), "text": spec["text"], "tip": spec.get("tip", ""),
                                    "priority": int(spec.get("priority", 0)), "label": lab, "now": "",
                                    "mark": mark, "glyph": spec.get("glyph")})
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
            gap = self.layout().spacing()
            fixed = (0 if self.label.isHidden() else self.label.sizeHint().width()) + 10 + 2 + 1
            for b in self.buttons():
                fixed += b.width() + gap
            room = self.width() - fixed - 8
            keep, self.dropped = [], []
            for item in sorted(self.status, key=lambda it: -it["priority"]):
                need = item["label"].fontMetrics().horizontalAdvance(item["now"]) + 10 + (
                    16 if item["mark"] is not None else 0)
                if item["now"] and need <= room:
                    room -= need
                    keep.append(item["id"])
                elif item["now"]:
                    self.dropped.append(item)
            for item in self.status:
                item["label"].setVisible(item["id"] in keep)
                if item["mark"] is not None:
                    item["mark"].setVisible(item["id"] in keep)
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
            # D98: only what is this panel's. The settings for every panel (tools and tabs, when they do not
            # fit, reset the layout) are in View, in Window > Layout, in the bar's layout menu and the palette
            menu.addAction(st["float_actions"][self.key])
            menu.addAction(self.a_hide)

        def restyle(self):
            st = win._panels
            _tr = st["tr"]
            d = studio_theme.density()
            p = studio_theme.PALETTES[studio_theme.current_name()]
            self.setStyleSheet(title_qss())
            self.setFixedHeight(d["title_band"] - 2)        # 11 px name + 18 px buttons: 2 px under the table's band
            side = d["title_button"]                         # one number for every title band (P04-1, D97)
            self.layout().setSpacing(d["click_gap"])
            text = self.dock.windowTitle()
            self.label.setText(text.upper() if st["lang"] in ("en", "de") else text)
            for b in self.buttons():
                b.setFixedSize(side, side); b.setIconSize(QtCore.QSize(12, 12))
            self.b_menu.setIcon(_icon("menu", p["muted"]))
            name = "%s \u2014 %s (Alt+M)" % (text, _tr(S_MENU))
            self.b_menu.setToolTip(name); self.b_menu.setAccessibleName("%s \u2014 %s" % (text, _tr(S_MENU)))
            self.key_menu.setText(label_text("%s \u2014 %s" % (text, _tr(S_MENU))))
            self.label.setAccessibleName(text)
            for item in self.status:
                item["now"] = None                   # texts are in the language of the moment: ask again
                if item["mark"] is not None:
                    name, role = item["glyph"]
                    item["mark"].setPixmap(_glyph(name, p[role], 12))
            self.update_status()
            if self.b_close is not None:
                self.b_close.setIcon(_icon("close", p["muted"]))
                self.b_close.setToolTip(_tr(S_HIDE)); self.b_close.setAccessibleName(_tr(S_HIDE))
            self.a_hide.setText(_tr(S_HIDE))
            self.a_hide.setVisible(self.key not in PRINCIPAL)
            self.follow()

        def follow(self):
            st = win._panels
            p = studio_theme.PALETTES[studio_theme.current_name()]
            floating = self.dock.isFloating()
            # D59: behind / beside a tab that is SHOWN the tab names the panel, the band does not. (Qt also
            # lists the hidden panels of the group: with those alone there is no tab row, so the band names it.)
            tabbed = (not floating and not self.dock.isHidden() and any(
                not d.isHidden() and not d.isFloating() for d in win.tabifiedDockWidgets(self.dock)))
            if self.label.isHidden() != tabbed:
                self.label.setVisible(not tabbed)
                self.fit()
            self.b_float.setIcon(_icon("dock" if floating else "float", p["muted"]))
            tip = st["tr"](S_DOCK if floating else S_FLOAT)
            self.b_float.setToolTip(tip); self.b_float.setAccessibleName(tip)

    class EscCloses(QtCore.QObject):
        """Esc in a separate panel window closes it (a docked panel is left alone). When the keyboard is in
        a box that holds text (the search of Operators, a watch expression), the first Esc clears the box
        and the next one closes the window (D58, the Esc ladder's step 3).

        The main window has an Esc shortcut of its own (leave image focus) that would take the key
        first, so the ShortcutOverride is claimed here; the key press that follows closes the window.
        A child that uses Esc itself (an open completer, a line being edited) never lets it get here."""

        def eventFilter(self, obj, ev):
            if (ev.type() in (QtCore.QEvent.KeyPress, QtCore.QEvent.ShortcutOverride)
                    and ev.key() == QtCore.Qt.Key_Escape and ev.modifiers() == QtCore.Qt.NoModifier
                    and isinstance(obj, QtWidgets.QDockWidget) and obj.isFloating()):
                if ev.type() == QtCore.QEvent.KeyPress:
                    fw = obj.focusWidget()
                    if (isinstance(fw, QtWidgets.QLineEdit) and fw.text() and not fw.isReadOnly()
                            and fw.isVisible() and obj.isAncestorOf(fw)):
                        fw.clear()                   # D58: a box with text in it - the first Esc only clears it
                    else:
                        obj.hide()
                ev.accept()
                return True
            return False

    class HandFollowsEnabled(QtCore.QObject):
        """D03: a disabled button does not show the pointing hand (it cannot be pressed); enabled again,
        it gets the hand back. Only buttons that were given the hand are touched."""

        def eventFilter(self, obj, ev):
            if ev.type() == QtCore.QEvent.EnabledChange and isinstance(obj, QtWidgets.QAbstractButton):
                fix_hand(obj)
            return False

    hand = HandFollowsEnabled(win)
    app = QtWidgets.QApplication.instance()
    if app is not None:
        app.installEventFilter(hand)

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
          "tr": tr, "lang": "en", "esc": esc, "menus": [], "overflow_mode": "scroll", "overflow_actions": {},
          "tab_rows": {}, "strip_decl": {}}
    win._panels = st

    def panel_menu(key, button, pos):
        """Right-click on a bar button: show / hide, separate window / dock (modeless popup)."""
        _tr = win._panels["tr"]
        dock = win._docks[key]
        menu = QtWidgets.QMenu(button)
        name = label_text(dock.windowTitle())
        if key in PRINCIPAL:                         # D104: a principal is only brought forward
            a_vis = menu.addAction("%s: %s" % (_tr(S_SHOW), name))
        else:
            a_vis = menu.addAction("%s: %s" % (_tr(S_SHOW if dock.isHidden() else S_HIDE), name))
        a_float = menu.addAction("%s: %s" % (_tr(S_DOCK if dock.isFloating() else S_FLOAT), name))

        def flip():
            if key in PRINCIPAL:
                show_principal(win, key)
            else:
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
    st["hand_filter"] = hand

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
    try:
        st["overflow_mode"] = normalise_overflow_mode(settings().value(OVERFLOW_KEY) if settings is not None else "scroll")
    except Exception:                            # noqa: BLE001 - a broken store must not stop the window
        st["overflow_mode"] = "scroll"
    lmenu.addSeparator()
    group = QtGui.QActionGroup(win); group.setExclusive(True); st["strip_group"] = group
    for mode in STRIP_MODES:
        a = QtGui.QAction(tr(S_STRIP[mode]), win)
        a.setObjectName("strip_" + mode)
        a.setCheckable(True); a.setChecked(mode == st["strip_mode"]); group.addAction(a)
        a.triggered.connect(lambda _c=False, m=mode: set_strip_mode(
            win, m, st["settings"]() if st["settings"] is not None else None))
        lmenu.addAction(a)
        st["strip_actions"][mode] = a
    # when tools or tabs do not fit: scroll / wrap - one setting for every strip and tab row (A3)
    lmenu.addSeparator()
    ogroup = QtGui.QActionGroup(win); ogroup.setExclusive(True); st["overflow_group"] = ogroup
    for mode in OVERFLOW_MODES:
        a = QtGui.QAction(tr(S_OVERFLOW[mode]), win)
        a.setObjectName("overflow_" + mode)
        a.setCheckable(True); a.setChecked(mode == st["overflow_mode"]); ogroup.addAction(a)
        a.triggered.connect(lambda _c=False, m=mode: set_overflow_mode(
            win, m, st["settings"]() if st["settings"] is not None else None))
        lmenu.addAction(a)
        st["overflow_actions"][mode] = a
    view_menu = (getattr(win, "_menus", None) or {}).get("view")
    if view_menu is not None:                    # the same entries in the View menu (and so in the palette)
        view_menu.addSeparator()
        for a in list(st["strip_actions"].values()) + [None] + list(st["overflow_actions"].values()):
            view_menu.addSeparator() if a is None else view_menu.addAction(a)
    layouts = getattr(win, "_layouts_menu", None)
    if layouts is not None:                      # D98: the settings for every panel live in Window > Layout

        def settle(menu=layouts):
            if st["strip_actions"]["auto"] in menu.actions():
                return
            for a in [None] + list(st["strip_actions"].values()) + [None] + list(st["overflow_actions"].values()):
                menu.addSeparator() if a is None else menu.addAction(a)
        layouts.aboutToShow.connect(settle)
        settle()
        st["settle_layout_menu"] = settle

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
    watch = QtCore.QTimer(win); watch.setSingleShot(True); watch.setInterval(0)      # D128: once per turn
    watch.timeout.connect(lambda: mode_watch(win))
    st["mode_watch"] = watch
    for mode_id, action in (getattr(win, "_work_mode_actions", None) or {}).items():
        action.triggered.connect(lambda _c=False, m=mode_id: mode_chosen(win, m))
    for dock in win._docks.values():
        dock.visibilityChanged.connect(lambda _v: watch.start())
        dock.dockLocationChanged.connect(lambda _a: watch.start())
        dock.topLevelChanged.connect(lambda _f: watch.start())
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

    # a principal's entry in Window > Panels / More > Panels / the palette brings it forward and gives it
    # the keyboard; it is not a check box (D104: shown is not a choice)
    st["principal_actions"] = {}
    for key in PRINCIPAL:
        dock = win._docks.get(key)
        if dock is None:
            continue
        pa = QtGui.QAction(dock.windowTitle(), win)
        pa.setObjectName("panel_show_" + key)
        pa.triggered.connect(lambda _c=False, k=key: (show_principal(win, k), sync(win)))
        st["principal_actions"][key] = pa
        for m in (getattr(win, "_menu_panels", None), getattr(win, "_more_menu_panels", None)):
            if m is None:
                continue
            tva = dock.toggleViewAction()
            if tva in m.actions():
                m.insertAction(tva, pa); m.removeAction(tva)
            elif pa not in m.actions():
                m.insertAction(m.actions()[0] if m.actions() else None, pa)

    def order_entries(m):
        """D21: the panel entries of ``m`` (show / hide, or a principal's bring-forward) in RAIL_ORDER,
        where the first of them was."""
        entry = {k: (st["principal_actions"].get(k) if k in PRINCIPAL else d.toggleViewAction())
                 for k, d in win._docks.items()}
        acts = m.actions()
        mine = [a for a in acts if a in entry.values()]
        if not mine:
            return 0
        after = acts[acts.index(mine[-1]) + 1:]
        anchor = after[0] if after else None
        for a in mine:
            m.removeAction(a)
        n = 0
        for k in panel_order(win, list(entry)):
            if entry[k] is not None:
                m.insertAction(anchor, entry[k])
                n += 1
        return n

    # menus + command palette: every panel has a show / hide entry and a separate-window entry
    menu = getattr(win, "_menu_panels", None)
    if menu is not None:
        listed = set(menu.actions())
        for key in RAIL_ORDER:
            tva = win._docks[key].toggleViewAction() if key in win._docks else None
            if key in PRINCIPAL:
                continue
            if tva is not None and tva not in listed:
                before = next((a for a in menu.actions() if a.isSeparator()), None)
                menu.insertAction(before, tva)
        order_entries(menu)
        menu.addSeparator()
        for key in panel_order(win, list(st["float_actions"])):
            menu.addAction(st["float_actions"][key])
    more = getattr(win, "_more_menu_panels", None)
    if more is not None:
        listed = set(more.actions())
        for key in RAIL_ORDER:                       # every panel, also those studio.py did not list there
            if key in win._docks and key not in PRINCIPAL and win._docks[key].toggleViewAction() not in listed:
                more.addAction(win._docks[key].toggleViewAction())
        order_entries(more)
    actions = getattr(win, "_actions", None)
    if isinstance(actions, dict):
        for key, fa in st["float_actions"].items():
            actions["panel_float_" + key] = fa
        for key, pa in st["principal_actions"].items():
            actions["panel_show_" + key] = pa
        for mode, a in st["strip_actions"].items():
            actions["strip_" + mode] = a
        for mode, a in st["overflow_actions"].items():
            actions["overflow_" + mode] = a
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
