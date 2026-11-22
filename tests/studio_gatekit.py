"""The gate kit of Studio 1.2.0 (STUDIO_INTERACTION_RULES 2026-11-13, 5.0 step 2 / 5.1): one place that

  * walks the window tree (every QAbstractItemView, QLineEdit, QPlainTextEdit, QTextEdit, QAbstractButton and every
    shown QDialog) -- the gates count what is on the window, not what a registry says is there (rule 8);
  * reads the property declarations of a widget (``"prose"``, ``"iconOnly"`` ...);
  * fixes the Qt style to Fusion (``fusion_app``) and keeps the settings in ``tmp_path`` (``gate_window``);
  * builds the confirmation boxes with the function that makes them (``build_confirm_box``) -- never only the hook;
  * states a lower bound for every count (``at_least``): a gate that counted nothing fails, it does not pass;
  * counts the six common gates (``count_*``) and compares them with the one-way ledger
    ``tests/data/studio_interaction_ledger.json`` (``compare``). The same functions are used by
    ``tools/studio_interaction_ledger.py`` (--check / --shrink / --report), so the test and the tool cannot disagree.

Every count returns ``(items, examined)``: ``items`` = the deviations found, each ``{"d": D number, "where": place,
"text": what}`` (``where`` + ``text`` is the identity of an item; no line numbers, so the ledger does not move when
code moves), ``examined`` = how many things were looked at (the lower bound is asserted on it).

The D numbers on the items are given from the kind of place (a table below), as a guide for the reader of the ledger;
the identity of an item does not depend on them.
"""
from __future__ import annotations

import ast
import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "tests" / "data" / "studio_interaction_ledger.json"

#: The gates of this kit, in report order: id -> (what is counted, the D numbers the gate belongs to).
GATES = {
    "G09(a)": ("confirmation boxes / input windows built directly (outside confirm_action / ask_text)",
               "D49 D50 D80 D88 D106 D107"),
    "G09(b')": ("confirmation kinds that the making function does not build with default = Esc = Cancel, "
                "no standard buttons and translated words", "D49 D50 D80 D106 D107"),
    "G13(b')": ("keys of the window bound to two commands of different meaning", "D11 D127 D94"),
    "G13(c)": ("menu-bar mnemonics used twice in one language (7 languages)", "D13"),
    "G15(a')": ("text shown untranslated in a non-English UI language (6 languages, matched against the source)",
                "D14 D15 D30 D35 D107 D108 D119"),
    "G15(b)": ("display texts whose '&' Qt eats as a mnemonic", "D14"),
    "G04(c')(d')": ("missing or non-distinct QSS rules QToolButton:checked / :disabled, QPushButton:disabled",
                    "D02 D03 D37"),
    "G01(a)(f)(g)": ("title bands: non-principal x not 18 px, principal hidden or with an x, rightmost not the menu",
                     "D57 D61 D97 D104 D105"),
}

#: Lower bounds of what each gate must have examined (5.1: a gate never passes on an empty count).
FLOORS = {"G09(a)": 2000, "G09(b')": 5, "G13(b')": 60, "G13(c)": 7 * 7, "G15(a')": 6 * 150, "G15(b)": 7 * 150,
          "G04(c')(d')": 6, "G01(a)(f)(g)": 7}

LANGS_NOT_EN = ("ja", "zh", "tw", "ko", "de", "hi")
#: Languages whose own script tells an English sentence apart (de cannot: only the match with the source counts).
OWN_SCRIPT = {"ja": r"[぀-ヿ㐀-鿿]", "zh": r"[㐀-鿿]", "tw": r"[㐀-鿿]",
              "ko": r"[가-힯ᄀ-ᇿ]", "hi": r"[ऀ-ॿ]"}


# --------------------------------------------------------------------------- #
# Qt: the app, the window, waiting
# --------------------------------------------------------------------------- #
def pump(app, sec=0.25):
    """Let Qt run for ``sec`` seconds (deferred layout, single-shot timers)."""
    end = time.monotonic() + sec
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def fusion_app():
    """The QApplication of the process, its style fixed to Fusion (the gates must not depend on windows11 / fusion)."""
    from PySide6 import QtWidgets
    assert os.environ.get("QT_QPA_PLATFORM") == "offscreen", "the gates run offscreen only"
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setStyle("Fusion")
    return app


def open_window(settings_path, size=(1280, 673)):
    """Build the Studio window under offscreen with the settings in ``settings_path`` (never the user's)."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["FULLSEYE_STUDIO_SETTINGS"] = str(settings_path)
    os.environ.pop("FULLSEYE_STUDIO_PERSIST_LAYOUT", None)
    app = fusion_app()
    import studio
    import studio_theme
    studio_theme.set_current(studio_theme.DEFAULT_THEME, studio_theme.DEFAULT_DENSITY)
    win, model = studio.build_window()
    win._test_model = model
    win.resize(*size)
    win.show()
    pump(app, 0.3)
    return app, win


def close_window(app, win):
    """Close a window built by :func:`open_window` without asking anything."""
    try:
        win.quiesce()
    except Exception:                                                   # noqa: BLE001 - closing anyway
        pass
    win.close_guard = lambda: True
    win.close()
    pump(app, 0.15)


def show_all_docks(app, win):
    """Show every dock (a hidden panel has no title band on screen to measure)."""
    for dock in win._docks.values():
        if dock.isHidden():
            dock.show()
    pump(app, 0.3)


def walk(root):
    """Every item view, text field and button under ``root``, and every shown QDialog of the application.

    Returns ``{"views": [...], "line_edits": [...], "plain_edits": [...], "text_edits": [...], "buttons": [...],
    "dialogs": [...]}`` in the order Qt lists the children."""
    from PySide6 import QtWidgets
    out = {
        "views": root.findChildren(QtWidgets.QAbstractItemView),
        "line_edits": root.findChildren(QtWidgets.QLineEdit),
        "plain_edits": root.findChildren(QtWidgets.QPlainTextEdit),
        "text_edits": root.findChildren(QtWidgets.QTextEdit),
        "buttons": root.findChildren(QtWidgets.QAbstractButton),
        "dialogs": [w for w in QtWidgets.QApplication.topLevelWidgets()
                    if isinstance(w, QtWidgets.QDialog) and w.isVisible()],
    }
    return out


def declared(widget, name):
    """The property declaration ``name`` of ``widget`` (None when it is not declared)."""
    v = widget.property(name)
    return None if v is None else v


def menu_actions(menu):
    """Every entry of ``menu`` and its submenus (submenus are found as children: QAction.menu() lets go of them
    with PySide6 6.11.1)."""
    from PySide6 import QtWidgets
    subs = {m.menuAction(): m for m in menu.findChildren(QtWidgets.QMenu)}
    out = []
    for a in menu.actions():
        if a in subs:
            out.append(a)
            out += menu_actions(subs[a])
        elif not a.isSeparator():
            out.append(a)
    return out


def at_least(examined, floor, what):
    """The lower bound of a gate: fail loudly when fewer than ``floor`` things were counted."""
    assert examined >= floor, "%s: examined %d < floor %d (the gate counted too little to mean anything)" % (
        what, examined, floor)


# --------------------------------------------------------------------------- #
# the ledger (one way during 1.2.0: more than the ledger fails; fixed items are removed with --shrink)
# --------------------------------------------------------------------------- #
def load_ledger(path=LEDGER):
    """The ledger ``{gate id: {"count", "items": [{"d", "where", "text"}], ...}}`` (the ``gates`` object)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["gates"]


def key_of(item):
    """The identity of a ledger item (no line numbers)."""
    return (item["where"], item["text"])


def compare(gate, items, ledger=None):
    """``(new, fixed)``: items found now that the ledger does not have, and ledger items not found any more."""
    led = (ledger if ledger is not None else load_ledger())[gate]
    have = {key_of(i) for i in led["items"]}
    now = {key_of(i) for i in items}
    assert led["count"] == len(led["items"]), "%s: the ledger's count %d != its %d items" % (
        gate, led["count"], len(led["items"]))
    new = [i for i in items if key_of(i) not in have]
    fixed = [i for i in led["items"] if key_of(i) not in now]
    return new, fixed


def assert_within_ledger(gate, items, examined, ledger=None):
    """The gate: the lower bound holds, nothing new (not in the ledger), and the count is not above the ledger's."""
    at_least(examined, FLOORS[gate], gate)
    led = (ledger if ledger is not None else load_ledger())[gate]
    new, _fixed = compare(gate, items, ledger)
    assert not new, "%s: %d new deviation(s) not in the ledger (fix them; the ledger is not widened):\n%s" % (
        gate, len(new), "\n".join("  %s | %s | %s" % (i["d"], i["where"], i["text"]) for i in new[:40]))
    assert len(items) <= led["count"], (gate, len(items), led["count"])


# --------------------------------------------------------------------------- #
# G09(a) - the syntax tree: boxes and input windows made directly
# --------------------------------------------------------------------------- #
#: The functions allowed to make a box / an input window (P09-2/9: confirm_action's maker and ask_text's).
BOX_MAKERS = ("_build_confirm_box", "ask_text", "_build_text_box")
_BOX_CTORS = ("QMessageBox", "QDialogButtonBox", "QInputDialog")
_BOX_STATIC = {"QMessageBox": ("question", "warning", "information", "critical", "about", "aboutQt"),
               "QInputDialog": ("getText", "getInt", "getDouble", "getItem", "getMultiLineText")}


def studio_sources(root=ROOT):
    """The Studio modules at the top of the tree (studio*.py), sorted."""
    return sorted(p for p in Path(root).glob("studio*.py") if p.is_file())


def _call_name(func):
    """``QMessageBox`` / ``QMessageBox.question`` ... for a call's function node, or None."""
    if isinstance(func, ast.Name) and func.id in _BOX_CTORS:
        return func.id
    if isinstance(func, ast.Attribute):
        if func.attr in _BOX_CTORS:
            return func.attr
        base = func.value
        base_name = base.attr if isinstance(base, ast.Attribute) else (base.id if isinstance(base, ast.Name) else "")
        if base_name in _BOX_STATIC and func.attr in _BOX_STATIC[base_name]:
            return base_name + "." + func.attr
    return None


def _d_for_box(fname, qual, call):
    if call.startswith("QInputDialog"):
        return "D107"
    if fname == "studio_params_qt.py":
        return "D88"
    low = qual.lower()
    if "trust" in low:
        return "D49"
    if fname == "studio_pymode.py" or "save" in low:
        return "D50"
    return "D106"


def count_g09a(root=ROOT):
    """Calls that make a QMessageBox / QDialogButtonBox / QInputDialog outside :data:`BOX_MAKERS`."""
    items = []
    examined = 0
    for path in studio_sources(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        seen = {}

        def visit(node, qual):
            nonlocal examined
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    visit(child, qual + [child.name])
                    continue
                if isinstance(child, ast.Call):
                    examined += 1
                    name = _call_name(child.func)
                    if name and not any(q in BOX_MAKERS for q in qual):
                        q = ".".join(qual) or "<module>"
                        k = seen.get((q, name), 0)
                        seen[(q, name)] = k + 1
                        items.append({"d": _d_for_box(path.name, q, name),
                                      "where": "%s::%s" % (path.name, q),
                                      "text": "%s #%d" % (name, k + 1)})
                visit(child, qual)
        visit(tree, [])
    return items, examined


# --------------------------------------------------------------------------- #
# G09(b') - the making function builds every kind for real
# --------------------------------------------------------------------------- #
CONFIRM_KINDS = (("run", "D106"), ("unsaved", "D50"), ("changed", "D106"), ("trust", "D49"), ("text", "D107"))


def build_confirm_box(studio, kind, parent=None):
    """The real box of ``kind`` made by the function that makes it (``studio._build_confirm_box`` for run /
    unsaved / changed / trust, ``studio._build_text_box`` for the text input). None while that function is absent
    (B4 brings it: D106 / D107)."""
    if kind == "text":
        maker = getattr(studio, "_build_text_box", None)
        return None if maker is None else maker(parent, "Gate", "Name", "")
    maker = getattr(studio, "_build_confirm_box", None)
    return None if maker is None else maker(parent, "Gate", "Something is lost.", "Do it", kind=kind)


def _i18n_sources(root=ROOT):
    data = json.loads((Path(root) / "studio_assets" / "i18n.json").read_text(encoding="utf-8"))
    src = {}
    for table in ("strings", "tooltips", "pending_translation"):
        for k, v in (data.get(table) or {}).items():
            if isinstance(v, dict):
                src.setdefault(k, {}).update({lk: lv for lk, lv in v.items() if isinstance(lv, str)})
    return src


def count_g09b(studio, root=ROOT):
    """Kinds whose box is not built for real with default = Esc = Cancel (RejectRole), no standard buttons and
    words that are in the i18n table. Every kind without a making function is one item."""
    from PySide6 import QtWidgets
    src = _i18n_sources(root)
    items = []
    examined = 0
    for kind, d in CONFIRM_KINDS:
        examined += 1
        box = build_confirm_box(studio, kind)
        if box is None:
            items.append({"d": d, "where": "studio.confirm_action kind=%s" % kind, "text": "no making function"})
            continue
        try:
            problems = []
            if isinstance(box, QtWidgets.QMessageBox):
                if box.standardButtons() != QtWidgets.QMessageBox.NoButton:
                    problems.append("standard buttons")
                dflt, esc = box.defaultButton(), box.escapeButton()
                if dflt is None or box.buttonRole(dflt) != QtWidgets.QMessageBox.RejectRole:
                    problems.append("default is not Cancel")
                if esc is None or esc is not dflt:
                    problems.append("Esc is not the default (Cancel)")
                for b in box.buttons():
                    word = b.text().replace("&", "")
                    if word not in src:
                        problems.append("word not in i18n: %s" % word)
            for p in problems:
                items.append({"d": d, "where": "studio.confirm_action kind=%s" % kind, "text": p})
        finally:
            box.deleteLater()
    return items, examined


# --------------------------------------------------------------------------- #
# G13(b') / G13(c) - the meaning of a key over the window; the mnemonics of the menu bar
# --------------------------------------------------------------------------- #
def _plain(text):
    t = (text or "").replace("&&", "\0").replace("&", "").replace("\0", "&")
    t = t.replace("…", "").replace("...", "")
    t = re.sub(r"\s*\((?:Ctrl|Shift|Alt|F\d)[^)]*\)\s*$", "", t)
    return t.strip().lower()


def _family_of(action):
    """The meaning of an action: the key registry's family when the action has one (``keymap:<id>`` / a known id),
    else its plain text."""
    try:
        import studio_keymap as km
    except ImportError:
        km = None
    if km is not None:
        cid = None
        name = action.objectName() or ""
        if name.startswith("keymap:"):
            cid = name.split(":", 1)[1]
        fam = None
        for attr in ("family", "family_of", "command_family"):
            fn = getattr(km, attr, None)
            if fn is not None and cid:
                try:
                    fam = fn(cid)
                except Exception:                                       # noqa: BLE001 - unknown id
                    fam = None
                break
        if fam:
            return "family:" + str(fam)
    return "text:" + _plain(action.text() or action.toolTip())


def _scope_of(binding_context, widgets):
    """``None`` = the whole window (Window / Application shortcut); else the widgets it is bound to (a Widget /
    WidgetWithChildren shortcut fires only with the focus there)."""
    from PySide6 import QtCore, QtWidgets
    if binding_context in (QtCore.Qt.WindowShortcut, QtCore.Qt.ApplicationShortcut):
        return None
    return [w for w in widgets if isinstance(w, QtWidgets.QWidget) and not isinstance(w, QtWidgets.QMenu)]


def _meet(scope_a, scope_b):
    """Two bindings can fire for the same key press: one of them is window-wide, or their widgets are the same /
    one inside the other (a panel's own key in another panel never meets it)."""
    if scope_a is None or scope_b is None:
        return True
    return any(a is b or a.isAncestorOf(b) or b.isAncestorOf(a) for a in scope_a for b in scope_b)


def window_bindings(win):
    """``{key text: [(meaning, scope, where)]}`` for every QAction and QShortcut under the window with a key."""
    from PySide6 import QtGui
    out = {}
    for a in win.findChildren(QtGui.QAction):
        scope = _scope_of(a.shortcutContext(), a.associatedObjects())
        for seq in a.shortcuts():
            k = seq.toString(QtGui.QKeySequence.PortableText)
            if k:
                out.setdefault(k, []).append((_family_of(a), scope, a.objectName() or _plain(a.text())))
    for sc in win.findChildren(QtGui.QShortcut):
        scope = _scope_of(sc.context(), [sc.parent()])
        for seq in sc.keys():
            k = seq.toString(QtGui.QKeySequence.PortableText)
            if k:
                who = sc.objectName() or (sc.parent().objectName() if sc.parent() is not None else "")
                meaning = "shortcut:" + (sc.objectName() or sc.whatsThis() or type(sc.parent()).__name__)
                out.setdefault(k, []).append((meaning, scope, who))
    return out


def _d_for_key(key):
    if key in ("F1", "Shift+F1", "Ctrl+F1"):
        return "D127"
    if key in ("Ctrl+H", "Ctrl+Alt+H"):
        return "D11"
    if key in ("Ctrl+D", "Ctrl+/"):
        return "D94"
    return "D11"


def count_g13b(win):
    """Keys of the window bound to two commands of different meaning that can fire for the same key press (one
    item per key; the meanings that meet are listed)."""
    b = window_bindings(win)
    items = []
    for key in sorted(b):
        rows = b[key]
        met = set()
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                if rows[i][0] != rows[j][0] and _meet(rows[i][1], rows[j][1]):
                    met.update((rows[i][0], rows[j][0]))
        if met:
            items.append({"d": _d_for_key(key), "where": "key %s" % key, "text": " | ".join(sorted(met))})
    return items, len(b)


def mnemonic_of(text):
    """The mnemonic letter of a menu title (the character after a single '&'), lower case, or ''."""
    t = (text or "").replace("&&", "")
    m = re.search(r"&(.)", t)
    return m.group(1).lower() if m else ""


def count_g13c(app, win, languages):
    """Menu-bar mnemonics used twice in one language. ``examined`` = top menus looked at over the languages."""
    items = []
    examined = 0
    try:
        for lang in languages:
            win._apply_language(lang)
            pump(app, 0.2)
            seen = {}
            for a in win.menuBar().actions():
                if a.isSeparator() or not a.isVisible():
                    continue
                examined += 1
                ch = mnemonic_of(a.text())
                if ch:
                    seen.setdefault(ch, []).append(a.text())
            for ch, titles in sorted(seen.items()):
                if len(titles) > 1:
                    items.append({"d": "D13", "where": "menu bar %s Alt+%s" % (lang, ch.upper()),
                                  "text": " | ".join(titles)})
    finally:
        win._apply_language("en")
        pump(app, 0.2)
    return items, examined


# --------------------------------------------------------------------------- #
# G15(a') / G15(b) - untranslated text, eaten '&'
# --------------------------------------------------------------------------- #
def shown_texts(win):
    """``[(kind, text)]`` of the window's chrome: menus (every entry, every level), dock titles, tab texts,
    group titles, button texts and tool tips (toolbars by their actions, so a narrow screen does not change the
    count), labels, the window title. Item views' rows (op names, files) are not chrome and are not read."""
    from PySide6 import QtWidgets
    out = []
    out.append(("window title", win.windowTitle()))
    for top in win.menuBar().actions():
        if top.menu() is None and not top.isVisible():
            continue
        out.append(("menu", top.text()))
    for m in win.menuBar().findChildren(QtWidgets.QMenu):
        for a in menu_actions(m):
            if a.isVisible():
                out.append(("menu", a.text()))
    for d in win.findChildren(QtWidgets.QDockWidget):
        out.append(("dock title", d.windowTitle()))
    for bar in win.findChildren(QtWidgets.QTabBar):
        for i in range(bar.count()):
            out.append(("tab", bar.tabText(i)))
    for g in win.findChildren(QtWidgets.QGroupBox):
        out.append(("group title", g.title()))
    for tb in win.findChildren(QtWidgets.QToolBar):
        for a in tb.actions():
            if a.isVisible() and not a.isSeparator():
                out.append(("button", a.text()))
                out.append(("tooltip", a.toolTip()))
    for b in win.findChildren(QtWidgets.QAbstractButton):
        if isinstance(b.parentWidget(), QtWidgets.QToolBar) or not b.isVisibleTo(win):
            continue
        if b.objectName().startswith("qt_"):
            continue
        out.append(("button", b.text()))
        out.append(("tooltip", b.toolTip()))
    for lab in win.findChildren(QtWidgets.QLabel):
        if lab.isVisibleTo(win) and lab.textFormat() != 1:                # 1 = Qt.RichText
            out.append(("label", lab.text()))
    return [(k, t) for k, t in out if t and t.strip()]


_WORD = re.compile(r"[A-Za-z]{2,}")


def _untranslated(lang, kind, text, src):
    plain = text.replace("&&", "\0").replace("&", "").replace("\0", "&").strip()
    if plain in src:
        row = src[plain]
        if row.get(lang) is not None and row.get(lang) == plain:
            return False                                                 # the table says: the same in this language
        return True
    if kind in ("label", "tooltip"):
        return False                                                     # prose / op docs: only the match counts
    script = OWN_SCRIPT.get(lang)
    if script is None or re.search(script, plain):
        return False
    if re.search(r"[_/\\]|\.py\b|^\W*$", plain):
        return False                                                     # names, paths, symbols
    return len(_WORD.findall(plain)) >= 3


def _d_for_text(kind):
    return {"tooltip": "D30", "menu": "D108", "window title": "D119", "dock title": "D35",
            "tab": "D35", "group title": "D35", "button": "D15", "label": "D15"}.get(kind, "D15")


def count_g15(app, win, languages=LANGS_NOT_EN, root=ROOT):
    """``((untranslated items, examined), (eaten '&' items, examined))`` over ``languages`` (+ en for '&')."""
    src = _i18n_sources(root)
    un, un_n = [], 0
    amp, amp_n = [], 0
    seen_un, seen_amp = set(), set()
    try:
        for lang in ("en",) + tuple(languages):
            win._apply_language(lang)
            pump(app, 0.3)
            for kind, text in shown_texts(win):
                if kind in ("menu", "button", "tab", "group title"):
                    amp_n += 1
                    rest = text.replace("&&", "")
                    if ("& " in rest or rest.endswith("&")) and (lang, kind, text) not in seen_amp:
                        seen_amp.add((lang, kind, text))
                        amp.append({"d": "D14", "where": "%s %s" % (lang, kind), "text": text})
                if lang == "en":
                    continue
                un_n += 1
                if _untranslated(lang, kind, text, src) and (lang, kind, text) not in seen_un:
                    seen_un.add((lang, kind, text))
                    un.append({"d": _d_for_text(kind), "where": "%s %s" % (lang, kind), "text": text})
    finally:
        win._apply_language("en")
        pump(app, 0.2)
    return (un, un_n), (amp, amp_n)


# --------------------------------------------------------------------------- #
# G04(c')(d') - the style sheet has the pressed and the disabled rules
# --------------------------------------------------------------------------- #
def qss_rules(qss):
    """``{selector: {property: value}}`` of a flat style sheet."""
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


def count_g04(studio_theme):
    """Per theme: QToolButton:checked with its own ground and the accent in the frame, QToolButton:disabled and
    QPushButton:disabled in the off colour with a ground / frame unlike the normal one."""
    items = []
    examined = 0
    for theme in studio_theme.THEMES:
        p = studio_theme.PALETTES[theme]
        rules = qss_rules(studio_theme.build_qss(theme))
        base = rules.get("QToolButton", {})
        checks = (
            ("QToolButton:checked", lambda r: r.get("background") not in (None, base.get("background"))
             and p["accent"] in r.get("border", ""), "D02 D37"),
            ("QToolButton:disabled", lambda r: r.get("color") == p["off"] != base.get("color")
             and r.get("background") != base.get("background") and r.get("border") != base.get("border"), "D03"),
            ("QPushButton:disabled", lambda r: r.get("color") == p["off"], "D03"),
        )
        for sel, ok, d in checks:
            examined += 1
            rule = rules.get(sel)
            if rule is None:
                items.append({"d": d, "where": "theme %s" % theme, "text": "%s missing" % sel})
            elif not ok(rule):
                items.append({"d": d, "where": "theme %s" % theme, "text": "%s not distinct" % sel})
    return items, examined


# --------------------------------------------------------------------------- #
# G01(a)(f)(g) - the title bands of the panels
# --------------------------------------------------------------------------- #
def count_g01(app, win):
    """Every dock: its title band's rightmost widget is the menu (g); a non-principal x is shown at
    DENSITY["title_button"] (a); the principal has no x and two presses of its bar button keep it shown (f)."""
    import studio_panels
    import studio_theme
    from PySide6 import QtWidgets
    show_all_docks(app, win)
    side = studio_theme.density()["title_button"]
    st = win._panels
    items = []
    examined = 0
    for key, dock in win._docks.items():
        examined += 1
        bar = st["titles"].get(key)
        if bar is None:
            items.append({"d": "D61", "where": "dock %s" % key, "text": "no title band"})
            continue
        lay = bar.layout()
        widgets = [lay.itemAt(i).widget() for i in range(lay.count()) if lay.itemAt(i).widget() is not None]
        if not widgets or widgets[-1].objectName() != "dock_title_menu":
            items.append({"d": "D105", "where": "dock %s" % key, "text": "rightmost is not the menu"})
        close = bar.findChild(QtWidgets.QToolButton, "dock_title_close")
        if key in studio_panels.PRINCIPAL:
            if close is not None and close.isVisibleTo(bar):
                items.append({"d": "D104", "where": "dock %s" % key, "text": "principal has an x"})
            for _ in range(2):
                st["buttons"][key].click()
                pump(app, 0.1)
                if not dock.isVisible():
                    items.append({"d": "D104", "where": "dock %s" % key, "text": "bar button hides the principal"})
                    dock.show()
                    break
        else:
            if close is None or not close.isVisibleTo(bar):
                items.append({"d": "D57", "where": "dock %s" % key, "text": "no x shown"})
            elif (close.width(), close.height()) != (side, side):
                items.append({"d": "D97", "where": "dock %s" % key,
                              "text": "x is %dx%d, not %d" % (close.width(), close.height(), side)})
    return items, examined


# --------------------------------------------------------------------------- #
# everything at once (the tool)
# --------------------------------------------------------------------------- #
def count_everything(settings_path, root=ROOT):
    """``{gate: (items, examined)}`` for the eight gates, on one window built under offscreen."""
    import studio
    import studio_theme
    out = {"G09(a)": count_g09a(root)}
    app, win = open_window(settings_path)
    try:
        out["G09(b')"] = count_g09b(studio, root)
        out["G13(b')"] = count_g13b(win)
        langs = ("en",) + LANGS_NOT_EN
        out["G13(c)"] = count_g13c(app, win, langs)
        (un, amp) = count_g15(app, win)
        out["G15(a')"] = un
        out["G15(b)"] = amp
        out["G04(c')(d')"] = count_g04(studio_theme)
        out["G01(a)(f)(g)"] = count_g01(app, win)
    finally:
        close_window(app, win)
    return out
