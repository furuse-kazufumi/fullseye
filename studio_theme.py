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
}
#: Syntax roles (Program editor / Python editor).
SYNTAX_ROLES = ("syn_kw", "syn_num", "syn_str", "syn_def", "syn_deco", "syn_cmt")

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
        "syn_kw": "#e8b04a", "syn_num": "#f2a37a", "syn_str": "#9fd28a", "syn_def": "#7cc8f0",
        "syn_deco": "#c6a4f0", "syn_cmt": "#8a95a4",
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
        "syn_kw": "#8a4b00", "syn_num": "#a3330e", "syn_str": "#25702c", "syn_def": "#0b57a4",
        "syn_deco": "#6b3fa0", "syn_cmt": "#5f6b78",
    },
}
THEMES = ("instrument", "panel")
DEFAULT_THEME = "instrument"
THEME_LABELS = {"instrument": "Instrument (dark)", "panel": "Machine panel (light)"}

#: One table -> every density number. Rows never below 20 px, main buttons never below 28 px.
DENSITY = {
    "compact": {"row_pad": 4, "unit": 4, "row_gap": 3, "group_gap": 8, "inner": 6, "title_gap": 2,
                "title_band": 22, "tab_v": 2, "icon": 16, "icon_btn": 24, "main_icon": 20, "main_btn": 28,
                "click_gap": 4},
    "standard": {"row_pad": 8, "unit": 6, "row_gap": 6, "group_gap": 10, "inner": 8, "title_gap": 4,
                 "title_band": 28, "tab_v": 4, "icon": 18, "icon_btn": 28, "main_icon": 20, "main_btn": 30,
                 "click_gap": 4},
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
    ("muted", "gutter", 4.5), ("text", "curline", 4.5),
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
MONO_FONTS = ("Cascadia Mono", "Consolas")

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

def font_stack(lang):
    fams = UI_FONTS.get(lang, UI_FONTS["en"])
    return ",".join('"%s"' % f for f in fams) + ",system-ui,sans-serif"


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

QDockWidget {{ titlebar-close-icon:none; titlebar-normal-icon:none; font-size:11px; color:{p['muted']}; }}
QDockWidget::title {{ background:{p['chrome']}; padding:{tpad}px 8px {tpad}px 10px; border:none;
    border-left:3px solid {p['accent']}; border-bottom:1px solid {p['line']}; {caps} text-align:left; }}
QDockWidget::title:hover {{ background:{p['bg2']}; }}
QDockWidget::close-button, QDockWidget::float-button {{ background:transparent; border:none; padding:0; icon-size:12px; }}
QMdiArea {{ background:{p['bg0']}; }}
QMdiSubWindow {{ background:{p['bg1']}; }}
QMdiSubWindow > QWidget {{ border:1px solid {p['line']}; }}

QGroupBox {{ background:{p['bg1']}; border:1px solid {p['line']}; border-radius:{r}px;
    margin-top:{d['inner'] + 8}px; padding:{d['inner']}px; }}
QGroupBox::title {{ subcontrol-origin:margin; subcontrol-position:top left; left:8px; top:0px;
    padding:0px 6px; color:{p['title']}; font-size:11px; font-weight:700; {gcaps} }}

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
QTabBar::tab {{ background:{p['bg1']}; color:{p['muted']}; padding:{d['tab_v']}px {u * 2}px; border:1px solid {p['line']};
    border-bottom:none; border-top-left-radius:{r}px; border-top-right-radius:{r}px; }}
QTabBar::tab:selected {{ background:{p['bg2']}; color:{p['text']}; border-top:2px solid {p['accent']}; }}

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
