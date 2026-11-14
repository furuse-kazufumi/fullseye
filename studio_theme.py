"""Fullseye Studio — colour schemes, density and the style sheet built from them (no Qt).

One table per scheme, by ROLE (not by widget). Everything that used to be a hex literal in
``studio.py`` (``THEME``, ``NAVY_0`` … ``INK``, the per-widget style sheets, the painted
gutter / highlighter / image-ground colours) is looked up here, so switching the scheme
reaches every part.

Decision 2026-11-12 (STUDIO_AS_PYTHON_IDE.md, 見た目と配置の決定):

* ``instrument`` (計器盤) is the default dark scheme; ``panel`` (操作盤) is the light one.
* Red / amber / green are state colours only — never the colour of something you click.
  State is colour + shape + word (▶ running / ■ done / ▲ caution / ✕ error / ○ not connected).
* The ground around an image is a neutral grey (chroma 0) so the UI never tints the picture.
* Density: list row = text height + 4 px (compact, default) or + 8 px (standard);
  spacing unit 4 px; icon-only buttons are square 24 px (main actions 28 px);
  neighbouring clickable things are at least 4 px apart.

Pure Python on purpose: the contrast and table tests run without a display.
"""
from __future__ import annotations

#: Role -> what it colours (the vocabulary the rest of Studio uses).
ROLES = {
    "bg0": "window ground", "bg1": "panel ground", "bg2": "input-field ground",
    "chrome": "menu / tool bar / status bar ground", "editor": "code editor ground",
    "line": "frame lines", "hover": "row under the pointer", "text": "body text",
    "muted": "secondary text", "accent": "clickable / selected", "accent_hi": "clickable, hovered",
    "accent_ink": "text on the accent colour", "title": "panel titles", "brand": "product name",
    "readout": "instrument figures", "ok": "state: done / normal", "run": "state: running",
    "warn": "state: caution", "warn_bg": "ground of a caution notice", "err": "state: error",
    "off": "state: disabled / not connected", "surround": "ground around an image (neutral)",
    "gutter": "line-number gutter", "curline": "current code line", "execline": "line being executed",
    "annot": "marks drawn ON the image (ROI, cross-hair, swipe line): magenta = target, never a state",
    "rail": "panel bar band (the accent blended into the chrome: a little conspicuous)",
    "rail_hi": "panel bar, button under the pointer",
}
#: Syntax roles (Program editor / Python editor).
SYNTAX_ROLES = ("syn_kw", "syn_num", "syn_str", "syn_def", "syn_deco", "syn_cmt", "syn_op",
                "syn_bracket", "syn_opname", "syn_undef")
#: Grounds the highlighter sets behind characters (a QTextCharFormat background, under the glyph).
CODE_GROUND_ROLES = ("syn_suspect_bg",)

PALETTES = {
    # ① 計器盤 Instrument — dark slate; colour only for state.
    "instrument": {
        "bg0": "#1a1d22", "bg1": "#20242a", "bg2": "#272c33", "chrome": "#15181c", "editor": "#1d2126",
        "line": "#363c45", "hover": "#2c323a", "text": "#e4e7eb", "muted": "#9aa2ad",
        "accent": "#56b6e8", "accent_hi": "#7cc8f0", "accent_ink": "#0d1419", "title": "#cdd5df",
        "brand": "#f2f4f6", "readout": "#f2f4f6",
        "ok": "#4cc38a", "run": "#56b6e8", "warn": "#e8b04a", "warn_bg": "#4a3a17", "err": "#f0646a",
        "off": "#7d8590", "surround": "#2a2a2a",
        "gutter": "#16191d", "curline": "#242a31", "execline": "#1d3a2c", "annot": "#e040fb",
        "rail": "#264151", "rail_hi": "#34647e",
        "syn_kw": "#e8b04a", "syn_num": "#ff9db8", "syn_str": "#9fd28a", "syn_def": "#7cc8f0",
        "syn_deco": "#c6a4f0", "syn_cmt": "#8a95a4", "syn_op": "#6fd6c4",
        "syn_bracket": "#e4784e", "syn_opname": "#009cfc", "syn_undef": "#c08a78", "syn_suspect_bg": "#2c1804",
    },
    # ③ 操作盤 Machine Panel — light neutral grey (factory floor, projector, print).
    "panel": {
        "bg0": "#dfe2e6", "bg1": "#eceef1", "bg2": "#ffffff", "chrome": "#cfd4da", "editor": "#fbfbfc",
        "line": "#a9b0b9", "hover": "#e2e8f0", "text": "#15191e", "muted": "#4a525d",
        "accent": "#0a5bb5", "accent_hi": "#0d6fd8", "accent_ink": "#ffffff", "title": "#0a4a8f",
        "brand": "#15191e", "readout": "#0e1318",
        "ok": "#1a7a3c", "run": "#0a5bb5", "warn": "#8a5a00", "warn_bg": "#f6e3b8", "err": "#b3261e",
        "off": "#646c76", "surround": "#8c8c8c",
        "gutter": "#e6e9ed", "curline": "#eef3fa", "execline": "#d7f0de", "annot": "#e040fb",
        "rail": "#9cb5d0", "rail_hi": "#709ac8",
        "syn_kw": "#8a4b00", "syn_num": "#a3330e", "syn_str": "#25702c", "syn_def": "#0b57a4",
        "syn_deco": "#6b3fa0", "syn_cmt": "#5f6b78", "syn_op": "#00695c",
        "syn_bracket": "#5a3660", "syn_opname": "#8a2a42", "syn_undef": "#663624", "syn_suspect_bg": "#fcecd8",
    },
}
THEMES = ("instrument", "panel")
DEFAULT_THEME = "instrument"
THEME_LABELS = {"instrument": "Instrument (dark)", "panel": "Machine panel (light)"}

#: One table -> every density number. Rows never below 20 px, main buttons never below 28 px.
DENSITY = {
    "compact": {"row_pad": 4, "unit": 4, "row_gap": 3, "group_gap": 8, "inner": 6, "title_gap": 2,
                "title_band": 22, "tab_v": 2, "icon": 16, "icon_btn": 24, "main_icon": 20, "main_btn": 28,
                "click_gap": 4, "title_button": 18},
    "standard": {"row_pad": 8, "unit": 6, "row_gap": 6, "group_gap": 10, "inner": 8, "title_gap": 4,
                 "title_band": 28, "tab_v": 4, "icon": 18, "icon_btn": 28, "main_icon": 20, "main_btn": 30,
                 "click_gap": 4, "title_button": 18},
}
DENSITIES = ("compact", "standard")
DEFAULT_DENSITY = "compact"
DENSITY_LABELS = {"compact": "Compact", "standard": "Standard"}

#: (foreground role, background role, required WCAG ratio). Body text 4.5, UI parts / state 3.0.
CONTRAST_PAIRS = (
    ("text", "bg0", 4.5), ("text", "bg1", 4.5), ("text", "bg2", 4.5), ("text", "chrome", 4.5),
    ("text", "editor", 4.5), ("muted", "bg0", 4.5), ("muted", "bg1", 4.5), ("muted", "chrome", 4.5),
    ("readout", "chrome", 4.5), ("title", "bg1", 4.5), ("brand", "chrome", 4.5),
    ("accent_ink", "accent", 4.5), ("accent", "bg0", 3.0), ("accent", "bg2", 3.0),
    ("ok", "chrome", 3.0), ("run", "chrome", 3.0), ("warn", "chrome", 3.0), ("err", "chrome", 3.0),
    ("off", "chrome", 3.0), ("text", "warn_bg", 4.5), ("err", "bg2", 3.0), ("warn", "bg2", 3.0),
    ("syn_kw", "editor", 4.5), ("syn_num", "editor", 4.5), ("syn_str", "editor", 4.5),
    ("syn_def", "editor", 4.5), ("syn_deco", "editor", 4.5), ("syn_cmt", "editor", 4.5),
    ("syn_op", "editor", 4.5),
    ("muted", "gutter", 4.5), ("text", "curline", 4.5),
    ("text", "rail", 4.5), ("text", "rail_hi", 4.5), ("accent_hi", "bg0", 3.0),
)

#: UI font stack per language (Windows-installed fonts only). zh / tw / ko get their own
#: regional glyph forms instead of falling back to Yu Gothic (Japanese forms).
UI_FONTS = {
    "ja": ('Segoe UI', 'Yu Gothic UI', 'Meiryo UI'),
    "zh": ('Segoe UI', 'Microsoft YaHei UI', 'Microsoft YaHei'),
    "tw": ('Segoe UI', 'Microsoft JhengHei UI', 'Microsoft JhengHei'),
    "ko": ('Segoe UI', 'Malgun Gothic'),
    "en": ('Segoe UI', 'Yu Gothic UI', 'Meiryo'),
    "de": ('Segoe UI', 'Yu Gothic UI', 'Meiryo'),
    "hi": ('Segoe UI', 'Nirmala UI', 'Noto Sans Devanagari'),
}
# The code typeface (CODE_FONTS / MONO_FONTS) is decided in one place, at the end of this file.

#: Hex values that used to be written straight into studio.py (the old Navy / Teal look) -> role.
#: Used once to re-point per-widget style sheets, and by the test that no widget keeps an old value.
LEGACY_HEX = {
    "#14161d": "bg0", "#1b1e28": "bg1", "#232734": "bg2", "#2c313f": "line", "#262b38": "line",
    "#12141b": "chrome", "#e2e5ec": "text", "#8b91a0": "muted", "#17b8a6": "accent", "#22d3bf": "accent_hi",
    "#f5a524": "warn", "#ffb841": "warn", "#0c1116": "accent_ink", "#5a3a00": "warn_bg", "#fff1cf": "text",
    "#c88a1c": "warn", "#c9a227": "warn", "#e5484d": "err", "#6b7280": "muted", "#1f2430": "curline",
    "#14342f": "execline", "#202020": "surround", "#232a36": "hover", "#5b6270": "off", "#191c25": "bg1",
    "#3d424e": "off", "#2a2f3b": "line", "#3a4152": "line",
    "#9ece6a": "syn_str", "#e0af68": "syn_kw", "#ff9e64": "syn_num", "#7dcfff": "syn_def",
    "#bb9af7": "syn_deco", "#565f89": "syn_cmt",
}

_STATE = {"theme": DEFAULT_THEME, "density": DEFAULT_DENSITY}


def normalise_theme(name):
    """Unknown / broken setting -> the default (fail-closed to a scheme that exists)."""
    return name if name in PALETTES else DEFAULT_THEME


def normalise_density(name):
    return name if name in DENSITY else DEFAULT_DENSITY


def set_current(theme=None, density=None):
    if theme is not None:
        _STATE["theme"] = normalise_theme(theme)
    if density is not None:
        _STATE["density"] = normalise_density(density)
    return dict(_STATE)


def current_name():
    return _STATE["theme"]


def current_density():
    return _STATE["density"]


def current():
    """The active scheme's role table (a copy: callers cannot edit the tables)."""
    return dict(PALETTES[_STATE["theme"]])


def colour(role):
    """One role of the active scheme (KeyError for an unknown role: no silent fallback)."""
    return PALETTES[_STATE["theme"]][role]


def density():
    return dict(DENSITY[_STATE["density"]])


def legacy_constants(p=None):
    """Values for the module constants studio.py keeps for other branches
    (``NAVY_0``, ``NAVY_1``, ``NAVY_2``, ``LINE``, ``TEXT``, ``MUTED``, ``TEAL``, ``TEAL_HI``, ``AMBER``, ``INK``)."""
    p = p or current()
    return {"NAVY_0": p["bg0"], "NAVY_1": p["bg1"], "NAVY_2": p["bg2"], "LINE": p["line"],
            "TEXT": p["text"], "MUTED": p["muted"], "TEAL": p["accent"], "TEAL_HI": p["accent_hi"],
            "AMBER": p["warn"], "INK": p["accent_ink"]}


# --------------------------------------------------------------------------- #
# WCAG 2.x contrast
# --------------------------------------------------------------------------- #

def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_):
    h = hex_.lstrip("#")
    if len(h) != 6:
        raise ValueError("expected #rrggbb, got %r" % hex_)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def chroma(hex_):
    h = hex_.lstrip("#")
    v = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return max(v) - min(v)


def contrast_report(name):
    """[(fg, bg, ratio, required, ok)] for every pair of one scheme."""
    p = PALETTES[name]
    return [(fg, bg, round(contrast(p[fg], p[bg]), 2), need, contrast(p[fg], p[bg]) >= need)
            for fg, bg, need in CONTRAST_PAIRS]


# --------------------------------------------------------------------------- #
# Style sheet
# --------------------------------------------------------------------------- #

#: Faces asked for the symbols a sentence may hold (arrows, a cross, a triangle) when the language's
#: own UI faces lack them (D130: Segoe UI has no U+2715; without a fallback it is a hollow box).
SYMBOL_FONTS = ("Segoe UI Symbol",)


def ui_families(lang):
    """The UI font families of one language, in the order they are asked: its own, then the symbol face."""
    return tuple(UI_FONTS.get(lang, UI_FONTS["en"])) + SYMBOL_FONTS


def font_stack(lang):
    return ",".join('"%s"' % f for f in ui_families(lang)) + ",system-ui,sans-serif"


def mono_stack():
    return ",".join('"%s"' % f for f in MONO_FONTS) + ",monospace"


def row_height(text_px, level=None):
    """List / tree / table row height: text height + the density's pad, never below 20 px."""
    d = DENSITY[normalise_density(level or _STATE["density"])]
    return max(20, int(text_px) + d["row_pad"])


def build_qss(theme=None, lang="en", level=None, text_px=16):
    """The whole window style sheet for one scheme / language / density.

    ``text_px`` is the measured UI font height (QFontMetrics.height()); rows are text + pad.
    Latin languages get small caps with letter spacing on dock titles; CJK titles do not
    (small caps do nothing there), they use the accent tick instead."""
    p = PALETTES[normalise_theme(theme or _STATE["theme"])]
    d = DENSITY[normalise_density(level or _STATE["density"])]
    row = row_height(text_px, level)
    u = d["unit"]
    latin = lang in ("en", "de")
    caps = "text-transform:uppercase; letter-spacing:1px;" if latin else ""
    gcaps = "letter-spacing:1px;" if latin else ""
    tpad = max(0, (d["title_band"] - int(text_px)) // 2)
    half = max(2, d["row_pad"] // 2)
    r = 3
    return f"""
QWidget {{ background:{p['bg0']}; color:{p['text']}; font-size:12px; font-family:{font_stack(lang)}; }}
QMainWindow, QDialog {{ background:{p['bg0']}; }}
QLabel {{ color:{p['text']}; background:transparent; }}
QLabel[muted="true"] {{ color:{p['muted']}; }}
QLabel[hint="true"] {{ color:{p['muted']}; font-family:{mono_stack()}; }}

QMenuBar {{ background:{p['chrome']}; color:{p['text']}; border-bottom:1px solid {p['line']}; padding:1px 4px; }}
QMenuBar::item {{ background:transparent; padding:3px 9px; border-radius:{r}px; }}
QMenuBar::item:selected {{ background:{p['bg2']}; color:{p['accent']}; }}
QMenu {{ background:{p['bg1']}; border:1px solid {p['line']}; border-radius:{r}px; padding:3px; }}
QMenu::item {{ padding:{half}px 24px {half}px 12px; border-radius:{r}px; }}
QMenu::item:selected {{ background:{p['accent']}; color:{p['accent_ink']}; }}
QMenu::separator {{ height:1px; background:{p['line']}; margin:4px 6px; }}

QToolBar {{ background:{p['chrome']}; border:none; border-bottom:1px solid {p['line']}; spacing:{d['click_gap']}px; padding:1px {u}px; }}
QToolButton {{ background:{p['bg2']}; border:1px solid {p['line']}; border-radius:{r}px; padding:2px 8px; color:{p['text']}; }}
QToolButton[iconOnly="true"] {{ padding:{max(2, (d['icon_btn'] - d['icon']) // 2 - 1)}px; }}
QToolButton:hover {{ border-color:{p['accent']}; color:{p['accent_hi']}; }}
QToolButton:pressed {{ background:{p['accent']}; color:{p['accent_ink']}; }}
QToolButton:checked {{ background:{p['bg1']}; border:1px solid {p['accent']}; color:{p['accent']}; }}
QToolButton[accent="true"] {{ background:{p['accent']}; color:{p['accent_ink']}; border:none; font-weight:700; }}
QToolButton[accent="true"]:hover {{ background:{p['accent_hi']}; }}
QToolButton:focus {{ border:1px solid {p['accent_hi']}; }}
QToolButton:disabled {{ background:{p['bg1']}; border:1px solid {p['line']}; color:{p['off']}; }}
QToolButton[accent="true"]:disabled {{ background:{p['bg2']}; color:{p['off']}; }}

QDockWidget {{ titlebar-close-icon:none; titlebar-normal-icon:none; font-size:11px; color:{p['muted']}; }}
QDockWidget::title {{ background:{p['chrome']}; padding:{tpad}px 8px {tpad}px 10px; border:none;
    border-left:3px solid {p['accent']}; border-bottom:1px solid {p['line']}; {caps} text-align:left; }}
QDockWidget::title:hover {{ background:{p['bg2']}; }}
QDockWidget::close-button, QDockWidget::float-button {{ background:transparent; border:none; padding:0; icon-size:12px; }}
QMdiArea {{ background:{p['bg0']}; }}
QMdiSubWindow {{ background:{p['bg1']}; }}
QMdiSubWindow > QWidget {{ border:1px solid {p['line']}; }}

QGroupBox {{ background:{p['bg1']}; border:1px solid {p['line']}; border-radius:{r}px;
    margin-top:{d['inner'] + 8}px; padding:0px; }}
QGroupBox::title {{ subcontrol-origin:margin; subcontrol-position:top left; left:8px; top:0px;
    padding:0px 6px; color:{p['title']}; font-size:11px; font-weight:700; {gcaps} }}
QGroupBox[untitled="true"] {{ margin-top:0px; }}

QLineEdit,QComboBox,QPlainTextEdit,QTextEdit,QTextBrowser,QListWidget,QTreeWidget,QTableWidget,QSpinBox {{
    background:{p['bg2']}; border:1px solid {p['line']}; border-radius:{r}px; padding:0px {u + 2}px;
    selection-background-color:{p['accent']}; selection-color:{p['accent_ink']}; }}
QPlainTextEdit {{ background:{p['editor']}; }}
QComboBox, QLineEdit, QSpinBox {{ min-height:{row - 2}px; }}
QLineEdit:focus,QComboBox:focus,QPlainTextEdit:focus,QListWidget:focus,QSpinBox:focus,QTreeWidget:focus {{
    border:1px solid {p['accent_hi']}; }}
QListWidget::item, QListView::item {{ height:{row}px; padding:0px {u}px; border-radius:{r}px; }}
QTreeWidget::item, QTreeView::item {{ height:{row}px; }}
QComboBox QAbstractItemView::item {{ height:{row}px; }}
QListWidget::item:hover {{ background:{p['hover']}; }}
QListWidget::item:selected {{ background:{p['accent']}; color:{p['accent_ink']}; }}
QComboBox::drop-down {{ border:none; width:18px; }}
QComboBox QAbstractItemView {{ background:{p['bg1']}; border:1px solid {p['line']}; border-radius:{r}px;
    selection-background-color:{p['accent']}; selection-color:{p['accent_ink']}; outline:none; }}

QPushButton {{ background:{p['bg2']}; border:1px solid {p['line']}; border-radius:{r}px; padding:3px 10px; color:{p['text']}; }}
QPushButton[iconOnly="true"] {{ padding:{max(2, (d['icon_btn'] - d['icon']) // 2 - 1)}px; }}
QPushButton:hover {{ background:{p['hover']}; border-color:{p['accent']}; }}
QPushButton:pressed {{ background:{p['accent']}; color:{p['accent_ink']}; }}
QPushButton:disabled {{ color:{p['off']}; border-color:{p['line']}; background:{p['bg1']}; }}
QPushButton[accent="true"] {{ background:{p['accent']}; color:{p['accent_ink']}; border:none; font-weight:700; }}
QPushButton[accent="true"]:hover {{ background:{p['accent_hi']}; }}
QPushButton:focus {{ border:1px solid {p['accent_hi']}; }}
QCheckBox, QRadioButton {{ background:transparent; padding:{half}px 0px; margin:0px; }}
QRadioButton::indicator {{ width:12px; height:12px; border:1px solid {p['muted']}; border-radius:7px; background:{p['bg2']}; }}
QRadioButton::indicator:checked {{ border:1px solid {p['accent']}; background:qradialgradient(cx:0.5, cy:0.5, radius:0.5,
    fx:0.5, fy:0.5, stop:0 {p['accent']}, stop:0.42 {p['accent']}, stop:0.55 {p['bg2']}, stop:1 {p['bg2']}); }}
QRadioButton::indicator:disabled {{ border-color:{p['off']}; }}
QTabBar::tab {{ background:{p['bg1']}; color:{p['muted']}; padding:{d['tab_v']}px {u * 2}px; border:1px solid {p['line']};
    border-bottom:none; border-top-left-radius:{r}px; border-top-right-radius:{r}px; }}
QTabBar::tab:selected {{ background:{p['bg2']}; color:{p['text']}; border-top:2px solid {p['accent']}; }}
QTabBar::tab:left {{ padding:{u * 2}px {d['tab_v']}px; border:1px solid {p['line']}; border-right:none;
    border-top-left-radius:{r}px; border-bottom-left-radius:{r}px; border-top-right-radius:0px; }}
QTabBar::tab:left:selected {{ border-top:1px solid {p['line']}; border-left:2px solid {p['accent']}; }}

QSlider::groove:horizontal {{ height:6px; background:{p['line']}; border-radius:3px; }}
QSlider::handle:horizontal {{ width:16px; background:{p['accent']}; border-radius:8px; margin:-6px 0; }}
QSlider::handle:horizontal:hover {{ background:{p['accent_hi']}; }}
QSlider::sub-page:horizontal {{ background:{p['accent']}; border-radius:3px; }}
/* Qt QSS orders the sub-control BEFORE the pseudo-state (state-first silently never matches). */
QSlider::handle:horizontal:disabled {{ background:{p['off']}; }}
QSlider::sub-page:horizontal:disabled {{ background:{p['line']}; }}
QSlider::groove:horizontal:disabled {{ background:{p['bg2']}; }}
QSlider::handle:horizontal:focus {{ border:2px solid {p['accent_hi']}; }}

QScrollBar:vertical {{ background:transparent; width:12px; margin:2px; }}
QScrollBar::handle:vertical {{ background:{p['line']}; border-radius:{r}px; min-height:28px; }}
QScrollBar::handle:vertical:hover {{ background:{p['off']}; }}
QScrollBar:horizontal {{ background:transparent; height:12px; margin:2px; }}
QScrollBar::handle:horizontal {{ background:{p['line']}; border-radius:{r}px; min-width:28px; }}
QScrollBar::add-line,QScrollBar::sub-line {{ height:0; width:0; }}
QSplitter::handle {{ background:{p['line']}; }}
QSplitter::handle:horizontal {{ width:2px; }}
QStatusBar {{ background:{p['chrome']}; color:{p['muted']}; border-top:1px solid {p['line']}; }}
QStatusBar QLabel {{ color:{p['muted']}; }}
QStatusBar::item {{ border:none; }}
QProgressBar {{ background:{p['bg2']}; border:1px solid {p['line']}; border-radius:2px; }}
QProgressBar::chunk {{ background:{p['run']}; }}
QToolTip {{ background:{p['bg1']}; color:{p['text']}; border:1px solid {p['accent']}; border-radius:{r}px; padding:6px 8px; }}
"""


def fill(template, theme=None):
    """A per-widget style sheet written with {role} placeholders -> concrete colours."""
    p = PALETTES[normalise_theme(theme or _STATE["theme"])]
    return template.format(**p, mono=mono_stack(), chrome_rgba=rgba("chrome", 180, theme))


def rgba(role, alpha, theme=None):
    h = PALETTES[normalise_theme(theme or _STATE["theme"])][role].lstrip("#")
    return "rgba(%d,%d,%d,%d)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(alpha))


# --------------------------------------------------------------------------- #
# The code typeface (one place; added 2026-11-13)
#
# Program text, Python, output, tracebacks, values, completion lists, the code inside help
# pages: all fixed pitch, all from here. The rule (user, 2026-11-13): a face with which coding
# mistakes are hard to make. The first installed family of CODE_FONTS is used, alone.
#
# Measured on Windows 11 (DirectWrite, 10 pt; advance of one character; glyph pairs drawn at the
# same size and compared — the table and the images are in the stage-2 report):
#
#   family          half   kana  kanji  full / half   zero            1 l I        ligatures
#   BIZ UDGothic    6.50  13.00  13.00     2.00       narrower than O  all differ   none
#   MS Gothic       6.50  13.00  13.00     2.00       as wide as O     1 ~ l        none
#   Consolas        7.14  10.59  13.00     1.48       slashed          all differ   none
#   Cascadia Mono   7.61  10.59  13.00     1.39       dotted           all differ   none (Mono)
#   Consolas / Cascadia Mono + a Japanese family for the full-width glyphs: 1.82 / 1.71
#
# No family that ships with Windows has both a marked zero and full-width = 2 x half-width.
# A pair whose full-width is not exactly twice the half-width is NOT allowed (columns and Python
# indentation next to Japanese text drift), so the Japanese dual-width families come first and
# no second family is mixed in. BIZ UDGothic before MS Gothic: every confusable pair draws
# differently in it (MS Gothic's 1 and l nearly coincide). Where neither is installed (Windows
# without the Japanese fonts, Linux) the Latin faces with a marked zero follow. Cascadia Code is
# not listed: its ligatures turn != and -> into other shapes. What no typeface can make safe
# (a full-width space, an invisible or look-alike character) is marked by mark_code().
# --------------------------------------------------------------------------- #
CODE_FONTS = ("BIZ UDGothic", "MS Gothic", "Consolas", "Cascadia Mono",
              "Noto Sans Mono CJK JP", "DejaVu Sans Mono", "Liberation Mono")
MONO_FONTS = CODE_FONTS                 # the name the style sheet and older callers use
CODE_PT_DEFAULT = 10
CODE_PT_RANGE = (6, 32)
#: marks the part of a widget style sheet written by apply_code_font (so it is replaced, not piled up)
_CF_OPEN, _CF_CLOSE = "/*code-font*/", "/*end-code-font*/"
_CODE = {"pt": CODE_PT_DEFAULT, "prefer": "", "family": {}}

#: characters that read as something else or as nothing: kind -> what it is (suspicious_chars)
SUSPICIOUS_KINDS = {
    "wide_space": "full-width space (U+3000) — looks like indentation, is a syntax error",
    "wide_ascii": "full-width form of an ASCII character (U+FF01..U+FF5E), e.g. a full-width bracket or colon",
    "invisible": "zero-width or direction-control character (U+200B..U+200F, U+202A..U+202E, U+2060..U+2069, U+FEFF)",
    "lookalike": ("a character drawn like an ASCII one: Cyrillic / Greek letters, the minus sign U+2212, the dashes "
                  "U+2010..U+2015, typographic quotes U+2018 / U+2019 / U+201C / U+201D and primes U+2032 / U+2033"),
    "trailing": "space or tab at the end of a line",
    "tab": "tab character",
}
_LOOKALIKE = frozenset("\u0430\u0435\u043e\u0440\u0441\u0445\u0443\u0456\u0458\u0410\u0412\u0415\u041a\u041c\u041d\u041e\u0420"
                       "\u0421\u0422\u0425\u03bf\u03bd\u0391\u0392\u0395\u0396\u0397\u0399\u039a\u039c\u039d\u039f\u03a1\u03a4\u03a5\u03a7"
                       "\u2212\u2010\u2011\u2012\u2013"        # minus sign and the short dashes: drawn like "-"
                       "\u2014\u2015"                          # em dash, bar: 1 px from "-" in BIZ UDGothic (2026-11-13)
                       "\u2018\u2019\u201c\u201d\u2032\u2033")   # typographic quotes / primes: ' and " are curly in BIZ UDGothic
_INVISIBLE = frozenset([0xFEFF] + list(range(0x200B, 0x2010)) + list(range(0x202A, 0x202F))
                       + list(range(0x2060, 0x206A)))


def suspicious_chars(line):
    """(index, kind) of every character of one line that a reader takes for something else or does
    not see at all (kinds: SUSPICIOUS_KINDS). Trailing white space is reported per character."""
    out = []
    stripped = len(line.rstrip(" \t"))
    for i, ch in enumerate(line):
        code = ord(ch)
        if code == 0x3000:
            out.append((i, "wide_space"))
        elif 0xFF01 <= code <= 0xFF5E:
            out.append((i, "wide_ascii"))
        elif code in _INVISIBLE:
            out.append((i, "invisible"))
        elif ch in _LOOKALIKE:
            out.append((i, "lookalike"))
        elif ch == "\t":
            out.append((i, "trailing" if i >= stripped else "tab"))
        elif ch == " " and i >= stripped:
            out.append((i, "trailing"))
    return out


def normalise_code_pt(value):
    """A code font size from the settings: an int inside CODE_PT_RANGE (bad value -> the default)."""
    try:
        pt = int(value)
    except (TypeError, ValueError):
        return CODE_PT_DEFAULT
    return max(CODE_PT_RANGE[0], min(pt, CODE_PT_RANGE[1]))


def set_code_pt(value):
    """Remember the code font size (points) for every code surface built from now on."""
    _CODE["pt"] = normalise_code_pt(value)
    return _CODE["pt"]


def code_pt():
    return _CODE["pt"]


def pick_code_family(available, candidates=None):
    """The first of ``candidates`` (default CODE_FONTS) that is in ``available``; None when none is."""
    names = {str(a).casefold(): str(a) for a in available}
    for fam in (CODE_FONTS if candidates is None else candidates):
        hit = names.get(fam.casefold())
        if hit is not None:
            return hit
    return None


def set_code_family(name):
    """The user's own choice of code family (settings key ``ui/mono_font_family``); "" = the table.
    It is used when it is installed and fixed pitch, otherwise the table decides as usual."""
    _CODE["prefer"] = str(name or "").strip()
    _CODE["family"].clear()
    return _CODE["prefer"]


def code_families():
    """The family every code surface uses on this machine, as a one-item list (needs a QGuiApplication).

    The user's choice when usable, else the first installed CODE_FONTS member, else the system's
    fixed font, else any installed fixed-pitch family. Never a second family for the full-width
    glyphs: a pair whose full-width is not exactly twice the half-width is not allowed. Cached."""
    from PySide6 import QtGui   # noqa: PLC0415
    key = (tuple(CODE_FONTS), _CODE["prefer"])
    hit = _CODE["family"].get(key)
    if hit is not None:
        return list(hit)
    families = list(QtGui.QFontDatabase.families())
    fam = None
    if _CODE["prefer"]:
        fam = pick_code_family(families, (_CODE["prefer"],))
        if fam is not None and not QtGui.QFontDatabase.isFixedPitch(fam):
            fam = None
    if fam is None:
        fam = pick_code_family(families)
    if fam is None:
        fam = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont).family()
        if not QtGui.QFontInfo(QtGui.QFont(fam)).fixedPitch():
            fixed = [f for f in families if QtGui.QFontDatabase.isFixedPitch(f)]
            fam = fixed[0] if fixed else fam
    _CODE["family"][key] = (fam,)
    return [fam]


def code_font_choices():
    """Installed fixed-pitch members of CODE_FONTS / CODE_CJK_FONTS, in table order (the settings list)."""
    from PySide6 import QtGui   # noqa: PLC0415
    families = list(QtGui.QFontDatabase.families())
    out = []
    for cand in MONO_FONTS:
        hit = pick_code_family(families, (cand,))
        if hit is not None and QtGui.QFontDatabase.isFixedPitch(hit) and hit not in out:
            out.append(hit)
    return out


def code_family():
    """The half-width family of the code font (the one QFontInfo reports)."""
    return code_families()[0]


def code_font(pt=None):
    """The QFont for code: code_families(), fixed pitch, ``pt`` points (default: the remembered size)."""
    from PySide6 import QtGui   # noqa: PLC0415
    f = QtGui.QFont()
    f.setFamilies(code_families())
    f.setStyleHint(QtGui.QFont.Monospace)
    f.setFixedPitch(True)
    f.setPointSize(code_pt() if pt is None else normalise_code_pt(pt))
    if hasattr(f, "setFeature"):                 # Qt 6.7+: != and -> stay two characters in every family
        for tag in ("liga", "clig", "calt", "dlig"):
            try:
                f.setFeature(QtGui.QFont.Tag(tag), 0)
            except (TypeError, ValueError, AttributeError):
                break
    return f


def mark_code(editor, trailing=True):
    """Draw marks over the characters a typeface cannot make safe, in one QPlainTextEdit:
    a full-width space (a box), full-width ASCII forms and look-alike letters (underlined in the
    caution colour), invisible / direction-control characters (a red bar where they sit), and,
    when ``trailing`` is on, white space at the end of a line and tabs (faint). Only the visible
    blocks are scanned at each paint. Returns the filter (``.trailing`` switches the faint marks;
    ``.count`` is the number of marks of the last paint). Calling twice returns the first one."""
    from PySide6 import QtCore, QtGui, QtWidgets   # noqa: PLC0415
    old = getattr(editor, "_fs_code_marks", None)
    if old is not None:
        old.trailing = bool(trailing)
        return old

    class Marks(QtCore.QObject):
        def __init__(self):
            super().__init__(editor)
            self.trailing, self.count, self.busy = bool(trailing), 0, False
            self.kinds = {}

        def eventFilter(self, obj, ev):
            if ev.type() != QtCore.QEvent.Paint or self.busy or obj is not editor.viewport():
                return False
            self.busy = True
            try:
                QtWidgets.QApplication.sendEvent(obj, ev)       # the editor paints itself first
                self.paint(obj)
            finally:
                self.busy = False
            return True

        def paint(self, viewport):
            p = PALETTES[_STATE["theme"]]
            painter = QtGui.QPainter(viewport)
            fm = QtGui.QFontMetricsF(editor.font())
            block = editor.firstVisibleBlock()
            bottom = viewport.height()
            count, kinds = 0, {}
            while block.isValid():
                top = editor.blockBoundingGeometry(block).translated(editor.contentOffset()).top()
                if top > bottom:
                    break
                found = suspicious_chars(block.text()) if block.isVisible() else []
                for idx, kind in found:
                    if kind in ("trailing", "tab") and not self.trailing:
                        continue
                    cur = QtGui.QTextCursor(block)
                    cur.setPosition(block.position() + idx)
                    r0 = editor.cursorRect(cur)
                    cur.setPosition(block.position() + idx + 1)
                    r1 = editor.cursorRect(cur)
                    w = r1.left() - r0.left() if r1.top() == r0.top() and r1.left() > r0.left() else 0
                    box = QtCore.QRectF(r0.left(), r0.top(), max(w, 2), r0.height())
                    if kind in ("wide_space", "wide_ascii", "lookalike"):
                        # the caution colour as a translucent ground (the glyph stays readable) + a shape:
                        # a frame for the space that is not a space, an underline for the others
                        ground = QtGui.QColor(p["warn"]); ground.setAlpha(70)
                        painter.fillRect(box, ground)
                        if kind == "wide_space":
                            painter.setPen(QtGui.QPen(QtGui.QColor(p["warn"]), 1))
                            painter.drawRect(box.adjusted(1.5, 2.5, -1.5, -2.5))
                        else:
                            painter.fillRect(QtCore.QRectF(box.left(), box.bottom() - 2, box.width(), 2),
                                             QtGui.QColor(p["warn"]))
                    elif kind == "invisible":
                        painter.fillRect(QtCore.QRectF(box.left() - 1, box.top() + 1, 2, box.height() - 2), QtGui.QColor(p["err"]))
                    else:                                    # trailing space / tab: faint
                        col = QtGui.QColor(p["off"]); col.setAlpha(110)
                        if kind == "tab" or block.text()[idx] == "\t":
                            y = box.center().y()
                            painter.setPen(QtGui.QPen(col, 1))
                            painter.drawLine(QtCore.QPointF(box.left() + 2, y), QtCore.QPointF(box.right() - 2, y))
                        else:
                            painter.fillRect(QtCore.QRectF(box.center().x() - 1, box.center().y() - 1, 2, 2), col)
                    count += 1
                    kinds[kind] = kinds.get(kind, 0) + 1
                block = block.next()
            painter.end()
            self.count, self.kinds = count, kinds
            del fm

    marks = Marks()
    editor.viewport().installEventFilter(marks)
    editor._fs_code_marks = marks
    editor.viewport().update()
    return marks


def code_css(pt=None):
    """``font-family`` / ``font-size`` declarations of the code font (for a widget style sheet or HTML)."""
    return "font-family:%s; font-size:%dpt;" % (",".join('"%s"' % f for f in code_families()),
                                                 code_pt() if pt is None else normalise_code_pt(pt))


def apply_code_font(widget, pt=None):
    """Give one widget the code font (the short call for any part that shows or takes code).

    The window style sheet names the UI font for every QWidget, which outranks ``setFont``; so the
    font is also written into the widget's own style sheet, in a marked part that the next call
    replaces. The widget's other style rules are kept. Tab stops follow the new advance."""
    from PySide6 import QtGui   # noqa: PLC0415
    font = code_font(pt)
    sheet = widget.styleSheet() or ""
    a = sheet.find(_CF_OPEN)
    b = sheet.find(_CF_CLOSE)
    if a >= 0 and b > a:
        sheet = sheet[:a] + sheet[b + len(_CF_CLOSE):]
    css = code_css(pt)
    part = ("* { %s }" % css) if "{" in sheet else css
    want = sheet + _CF_OPEN + part + _CF_CLOSE
    if want != (widget.styleSheet() or ""):
        widget.setStyleSheet(want)
    widget.setFont(font)
    if hasattr(widget, "setTabStopDistance"):
        widget.setTabStopDistance(4 * QtGui.QFontMetricsF(font).horizontalAdvance(" "))
    return font


def _browser_code(browser):
    """Code inside a help page (<code>, <pre>, font-family:monospace) -> the code family. Returns the
    number of fragments re-pointed. The page's own sizes are kept."""
    from PySide6 import QtGui   # noqa: PLC0415
    fams = code_families()
    fam = fams[0]
    doc = browser.document()
    generic = ("monospace", "courier", "courier new", "consolas", "cascadia mono")
    spans = []
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            fr = it.fragment()
            if fr.isValid():
                cf = fr.charFormat()
                names = [str(n).strip("'\" ").casefold() for n in (cf.fontFamilies() or [])]
                if (cf.fontFixedPitch() or any(n in generic for n in names)) and names[:1] != [fam.casefold()]:
                    spans.append((fr.position(), fr.length()))
            it += 1
        block = block.next()
    if not spans:
        return 0
    fmt = QtGui.QTextCharFormat()
    fmt.setFontFamilies(fams); fmt.setFontFixedPitch(True)
    was = doc.isUndoRedoEnabled()
    doc.setUndoRedoEnabled(False)
    blocked = browser.blockSignals(True)
    try:
        cur = QtGui.QTextCursor(doc)
        for pos, length in spans:
            cur.setPosition(pos); cur.setPosition(pos + length, QtGui.QTextCursor.KeepAnchor)
            cur.mergeCharFormat(fmt)
    finally:
        browser.blockSignals(blocked)
        doc.setUndoRedoEnabled(was)
    return len(spans)


def code_surfaces(root):
    """Every widget under ``root`` that shows or takes code, as (kind, widget):

    ``editor`` (an editable QPlainTextEdit: the Program box, a Python editor tab), ``readout`` (a
    read-only one: output, traceback, inspector, value of a variable, exported code), ``mono_text``
    (a QTextEdit whose own sheet asks for a fixed-pitch font), ``op_list`` (the operator names and
    signatures; ``root._op_list`` or a list with the ``codeFont`` property) and ``completion`` (the
    pop-up list of a QCompleter). Help pages are handled apart (the code fragments inside them)."""
    from PySide6 import QtWidgets   # noqa: PLC0415
    out, seen = [], set()

    def add(kind, w):
        if w is not None and id(w) not in seen:
            seen.add(id(w)); out.append((kind, w))

    widgets = [root] + root.findChildren(QtWidgets.QWidget)
    for w in widgets:
        if isinstance(w, QtWidgets.QPlainTextEdit):
            add("readout" if w.isReadOnly() else "editor", w)
        elif isinstance(w, QtWidgets.QTextEdit) and not isinstance(w, QtWidgets.QTextBrowser):
            if "monospace" in (w.styleSheet() or "") or _CF_OPEN in (w.styleSheet() or ""):
                add("mono_text", w)
        elif w.property("codeFont"):
            add("op_list", w)
    add("op_list", getattr(root, "_op_list", None))
    for c in root.findChildren(QtWidgets.QCompleter):
        add("completion", c.popup())
    return out


def apply_code_fonts(root, pt=None):
    """Code font on every code surface under ``root`` and on the code inside its help pages.
    Returns (surfaces, help fragments)."""
    from PySide6 import QtWidgets   # noqa: PLC0415
    n = 0
    for _kind, w in code_surfaces(root):
        apply_code_font(w, pt)
        n += 1
    frags = 0
    for b in ([root] if isinstance(root, QtWidgets.QTextBrowser) else []) + root.findChildren(QtWidgets.QTextBrowser):
        frags += _browser_code(b)
        if not b.property("fsCodeWatch"):                # a page loaded later gets the same treatment
            b.setProperty("fsCodeWatch", True)
            b.textChanged.connect(lambda _b=b: _browser_code(_b))
    return n, frags


def refresh_code_fonts(pt=None):
    """The size setting changed (or is being applied at start): remember it and re-apply the code
    font in every top-level window that exists. Returns the number of surfaces reached."""
    from PySide6 import QtWidgets   # noqa: PLC0415
    if pt is not None:
        set_code_pt(pt)
    n = 0
    for top in QtWidgets.QApplication.topLevelWidgets():
        try:
            n += apply_code_fonts(top)[0]
        except RuntimeError:                     # a window that is being destroyed
            pass
    return n


def watch_code_fonts(app):
    """Windows and editors built later (dialogs, a new editor tab) get the code font when they are
    first shown: one application event filter, installed once. Returns the filter."""
    from PySide6 import QtCore, QtWidgets   # noqa: PLC0415
    old = getattr(app, "_fs_code_font_watch", None)
    if old is not None:
        return old

    class Watch(QtCore.QObject):
        def eventFilter(self, obj, ev):
            if ev.type() == QtCore.QEvent.Show and isinstance(obj, QtWidgets.QWidget):
                if obj.isWindow() and not isinstance(obj, QtWidgets.QMenu):
                    QtCore.QTimer.singleShot(0, lambda o=obj: self.sweep(o))
                elif isinstance(obj, QtWidgets.QPlainTextEdit) and _CF_OPEN not in (obj.styleSheet() or ""):
                    QtCore.QTimer.singleShot(0, lambda o=obj: self.one(o))
            return False

        @staticmethod
        def sweep(obj):
            try:
                apply_code_fonts(obj)
            except RuntimeError:                 # the window was destroyed before the timer fired
                pass

        @staticmethod
        def one(obj):
            try:
                apply_code_font(obj)
            except RuntimeError:
                pass

    watch = Watch(app)
    app.installEventFilter(watch)
    app._fs_code_font_watch = watch
    return watch


# --------------------------------------------------------------------------- #
# Code colours tell things apart, not only the typeface (user, 2026-11-13)
#
# A 0 typed for an O is a number where a name was meant: when numbers and names have different
# colours it shows at once. So neighbouring roles must be distinguishable by measurement, in both
# schemes, also for protan / deutan vision, and never by red against green alone: each role also
# has a cue that is not a colour (CODE_STYLE).
# --------------------------------------------------------------------------- #
#: role -> cue besides the colour (what a highlighter sets on the character format)
CODE_STYLE = {
    "text": {}, "syn_kw": {"bold": True}, "syn_num": {}, "syn_str": {}, "syn_def": {"bold": True},
    "syn_deco": {"italic": True}, "syn_cmt": {"italic": True}, "syn_op": {},
    "syn_bracket": {}, "syn_opname": {}, "syn_undef": {"underline": "wave"},
}
#: The colour table of code (user, 2026-11-13): what a reader tells apart -> role. A name is body text;
#: a suspicious character keeps its own colour and gets the ground (and mark_code's frame / underline).
CODE_ROLE_TABLE = (
    ("number", "\u6570", "syn_num"),
    ("name", "\u540d\u524d", "text"),
    ("keyword", "\u30ad\u30fc\u30ef\u30fc\u30c9", "syn_kw"),
    ("string", "\u6587\u5b57\u5217", "syn_str"),
    ("comment", "\u30b3\u30e1\u30f3\u30c8", "syn_cmt"),
    ("operator", "\u6f14\u7b97\u5b50", "syn_op"),
    ("bracket", "\u62ec\u5f27", "syn_bracket"),
    ("op name", "op \u306e\u540d\u524d", "syn_opname"),
    ("undefined name", "\u672a\u5b9a\u7fa9", "syn_undef"),
    ("suspicious-character ground", "\u602a\u3057\u3044\u6587\u5b57\u306e\u4e0b\u5730", "syn_suspect_bg"),
    ("def / class name", "\u5b9a\u7fa9\u306e\u540d\u524d", "syn_def"),
    ("decorator", "\u30c7\u30b3\u30ec\u30fc\u30bf", "syn_deco"),
)
#: grounds code is read on: every code colour keeps 4.5 : 1 on each (WCAG AA, both schemes)
CODE_GROUNDS = ("editor", "curline", "syn_suspect_bg")
#: a ground that marks something must stand apart from the grounds around it (CIE76)
GROUND_PAIRS = (("syn_suspect_bg", "editor"), ("syn_suspect_bg", "curline"), ("syn_suspect_bg", "execline"))
GROUND_MIN = 12.0
#: pairs of roles that sit next to each other in code and must not be mistaken for each other
DISTINCT_PAIRS = (
    ("syn_num", "text"), ("syn_kw", "text"), ("syn_str", "text"), ("syn_op", "text"), ("syn_cmt", "text"),
    ("syn_str", "syn_cmt"), ("syn_num", "syn_str"), ("syn_kw", "syn_def"), ("syn_num", "syn_kw"), ("syn_op", "syn_num"),
    ("syn_opname", "text"), ("syn_opname", "syn_def"), ("syn_opname", "syn_kw"), ("syn_opname", "syn_num"),
    ("syn_opname", "syn_op"), ("syn_bracket", "text"), ("syn_bracket", "syn_op"), ("syn_bracket", "syn_num"),
    ("syn_bracket", "syn_str"), ("syn_bracket", "syn_kw"), ("syn_undef", "text"), ("syn_undef", "syn_opname"),
    ("syn_undef", "syn_num"),
)
#: smallest colour difference (CIE76, Lab) for a pair: seen normally / with protan or deutan vision
DISTINCT_MIN, DISTINCT_MIN_CVD = 18.0, 10.0


def lab(hex_):
    """sRGB "#rrggbb" -> CIE L*a*b* (D65)."""
    h = hex_.lstrip("#")
    r, g, b = (_lin(int(h[i:i + 2], 16)) for i in (0, 2, 4))
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t):
        return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0
    fx, fy, fz = f(x), f(y), f(z)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def delta_e(a, b):
    """Colour difference of two "#rrggbb" (CIE76: distance in Lab; about 2 is just noticeable)."""
    la, lb = lab(a), lab(b)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def simulate_cvd(hex_, kind):
    """How "#rrggbb" looks with ``kind`` = "protan" or "deutan" vision (Vienot et al. 1999, linear RGB)."""
    m = {"protan": ((0.11238, 0.88762, 0.0), (0.11238, 0.88762, 0.0), (0.00401, -0.00401, 1.0)),
         "deutan": ((0.29275, 0.70725, 0.0), (0.29275, 0.70725, 0.0), (-0.02234, 0.02234, 1.0))}[kind]
    h = hex_.lstrip("#")
    rgb = [_lin(int(h[i:i + 2], 16)) for i in (0, 2, 4)]
    out = []
    for row in m:
        v = max(0.0, min(1.0, sum(c * x for c, x in zip(row, rgb))))
        v = 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1.0 / 2.4) - 0.055
        out.append(int(round(max(0.0, min(1.0, v)) * 255)))
    return "#%02x%02x%02x" % tuple(out)


def distinct_report(name):
    """One row per DISTINCT_PAIRS entry: (role a, role b, dE, dE protan, dE deutan, cue differs, ok).
    ok = far enough apart normally AND (far enough with protan and deutan vision OR a non-colour cue differs)."""
    p = PALETTES[normalise_theme(name)]
    rows = []
    for a, b in DISTINCT_PAIRS:
        d0 = delta_e(p[a], p[b])
        dp = delta_e(simulate_cvd(p[a], "protan"), simulate_cvd(p[b], "protan"))
        dd = delta_e(simulate_cvd(p[a], "deutan"), simulate_cvd(p[b], "deutan"))
        cue = CODE_STYLE.get(a, {}) != CODE_STYLE.get(b, {})
        ok = d0 >= DISTINCT_MIN and (min(dp, dd) >= DISTINCT_MIN_CVD or cue)
        rows.append((a, b, round(d0, 1), round(dp, 1), round(dd, 1), cue, ok))
    return rows


def code_colour_table(name):
    """The code colour table of one scheme: one row per CODE_ROLE_TABLE entry,
    (meaning, meaning_ja, role, hex, lowest contrast on CODE_GROUNDS (None for a ground), cue)."""
    p = PALETTES[normalise_theme(name)]
    rows = []
    for en, ja, role in CODE_ROLE_TABLE:
        low = None if role in CODE_GROUND_ROLES else round(min(contrast(p[role], p[g]) for g in CODE_GROUNDS), 2)
        cue = ", ".join("%s=%s" % kv for kv in sorted(CODE_STYLE.get(role, {}).items())) or "-"
        rows.append((en, ja, role, p[role], low, cue))
    return rows


def ground_report(name):
    """(ground a, ground b, dE, ok) per GROUND_PAIRS: a marking ground stands apart from its neighbours."""
    p = PALETTES[normalise_theme(name)]
    return [(a, b, round(delta_e(p[a], p[b]), 1), delta_e(p[a], p[b]) >= GROUND_MIN) for a, b in GROUND_PAIRS]
