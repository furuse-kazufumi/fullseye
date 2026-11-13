"""Code is shown and typed in a fixed-pitch face, decided in one place (studio_theme.py; 2026-11-13).

Counted here: every code surface of the window (and of the Python editor built later) resolves to
a fixed-pitch family (QFontInfo, not the name that was asked for), the size setting reaches all of
them, a machine with none of the listed families still gets a fixed-pitch face, the code inside a
help page follows, and what the full-width companion buys (kana as wide as kanji; 2 x with a
dual-width family).

Offscreen, own settings file; nothing outside tmp_path is written.
"""
import os
import time

import pytest

import studio_theme


# --------------------------------------------------------------------------- #
# Qt-free: the table
# --------------------------------------------------------------------------- #
def test_the_table_and_the_pick():
    # dual-width Japanese faces first (full-width = 2 x half-width), then Latin faces with a marked zero
    assert studio_theme.CODE_FONTS[:4] == ("BIZ UDGothic", "MS Gothic", "Consolas", "Cascadia Mono")
    assert "Cascadia Code" not in studio_theme.CODE_FONTS                             # ligatures: != would change shape
    assert studio_theme.MONO_FONTS == studio_theme.CODE_FONTS
    assert len(studio_theme.MONO_FONTS) == len(set(studio_theme.MONO_FONTS)) == 7
    pick = studio_theme.pick_code_family
    assert pick(["Arial", "Cascadia Mono", "MS Gothic"]) == "MS Gothic"            # table order, not list order
    assert pick(["arial", "consolas"]) == "consolas"                                # case does not matter
    assert pick(["Arial", "Times New Roman"]) is None                               # none of them: the caller falls back
    assert pick([]) is None
    assert pick(["MS Gothic", "Consolas"], ("Consolas", "MS Gothic")) == "Consolas"  # an explicit candidate list
    stack = studio_theme.mono_stack()
    assert stack.endswith(",monospace") and stack.startswith('"BIZ UDGothic","MS Gothic"')
    assert stack in studio_theme.build_qss()                                         # the one stack the window sheet uses


@pytest.mark.parametrize("value,want", [(10, 10), ("14", 14), (3, 6), (99, 32), (None, 10), ("big", 10), (12.7, 12)])
def test_the_size_setting_is_clamped(value, want):
    assert studio_theme.CODE_PT_RANGE == (6, 32) and studio_theme.CODE_PT_DEFAULT == 10
    assert studio_theme.normalise_code_pt(value) == want


# --------------------------------------------------------------------------- #
# with Qt (offscreen)
# --------------------------------------------------------------------------- #
_WIN_FONTS = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
_FONT_FILES = [os.path.join(_WIN_FONTS, n) for n in ("consola.ttf", "CascadiaMono.ttf", "BIZ-UDGothicR.ttc",
                                                     "msgothic.ttc", "arial.ttf")] + [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]


def _pump(app, sec=0.25):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


@pytest.fixture()
def qapp(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtGui, QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # The offscreen platform has an EMPTY font database on Windows (0 families: every font test would
    # skip and prove nothing). Lend it the system's font files for the length of one test, read-only.
    lent = []
    if not QtGui.QFontDatabase.families():
        for path in _FONT_FILES:
            if os.path.isfile(path):
                lent.append(QtGui.QFontDatabase.addApplicationFont(path))
    if not any(QtGui.QFontDatabase.isFixedPitch(f) for f in QtGui.QFontDatabase.families()):
        for i in lent:
            QtGui.QFontDatabase.removeApplicationFont(i)
        pytest.skip("this machine has no fixed-pitch family at all")
    studio_theme.set_code_family("")
    studio_theme.set_code_pt(studio_theme.CODE_PT_DEFAULT)
    yield app
    for i in lent:
        QtGui.QFontDatabase.removeApplicationFont(i)
    studio_theme.set_code_family("")
    studio_theme.set_code_pt(studio_theme.CODE_PT_DEFAULT)


def _resolved(widget_or_font):
    from PySide6 import QtGui
    font = widget_or_font if isinstance(widget_or_font, QtGui.QFont) else widget_or_font.font()
    info = QtGui.QFontInfo(font)
    return info.family(), bool(info.fixedPitch()), int(round(info.pointSizeF()))


def test_the_code_font_is_fixed_pitch(qapp):
    fams = studio_theme.code_families()
    assert len(fams) == 1 and fams[0] == studio_theme.code_family()                  # one family: never a mixed pair
    family, fixed, pt = _resolved(studio_theme.code_font())
    assert fixed and family == fams[0] and pt == 10
    assert _resolved(studio_theme.code_font(18))[2] == 18
    assert _resolved(studio_theme.code_font(500))[2] == 32                           # clamped, never absurd
    css = studio_theme.code_css(12)
    assert css.startswith('font-family:"%s"' % fams[0]) and css.endswith("font-size:12pt;")


def test_a_machine_with_none_of_the_listed_families_still_gets_fixed_pitch(qapp, monkeypatch):
    monkeypatch.setattr(studio_theme, "CODE_FONTS", ("No Such Face 1", "No Such Face 2"))
    from PySide6 import QtGui
    assert studio_theme.pick_code_family(QtGui.QFontDatabase.families()) is None      # really none of them
    fams = studio_theme.code_families()
    assert fams and fams[0] not in ("No Such Face 1", "No Such Face 2") and len(fams) == 1
    family, fixed, _pt = _resolved(studio_theme.code_font())
    assert fixed, "fell back to %r, which is not fixed pitch" % family


def test_the_users_own_family_is_used_only_when_it_is_installed_and_fixed_pitch(qapp):
    from PySide6 import QtGui
    table = studio_theme.code_family()
    studio_theme.set_code_family("No Such Face 9")
    assert studio_theme.code_family() == table
    proportional = [f for f in QtGui.QFontDatabase.families() if not QtGui.QFontDatabase.isFixedPitch(f)
                    and QtGui.QFontDatabase.isSmoothlyScalable(f)]
    if proportional:
        studio_theme.set_code_family(proportional[0])
        assert studio_theme.code_family() == table                                    # a proportional face is refused
    others = [f for f in studio_theme.code_font_choices() if f != table]
    if not others:
        pytest.skip("only one of the listed families is installed here")
    studio_theme.set_code_family(others[-1])
    assert studio_theme.code_family() == others[-1]
    assert _resolved(studio_theme.code_font())[:2] == (others[-1], True)
    studio_theme.set_code_family("")
    assert studio_theme.code_family() == table


#: pairs a reader mixes up; every one must DRAW differently in the chosen face (same size, same box)
CONFUSABLE = (("0", "O"), ("0", "o"), ("O", "o"), ("1", "l"), ("1", "I"), ("l", "I"), ("l", "|"), ("I", "|"), ("1", "|"),
              (";", ":"), (",", "."), ("'", "`"), ("'", "\u00b4"), ("`", "\u00b4"), ('"', "''"),
              ("-", "_"), ("-", "\u30fc"), ("-", "\u2212"), ("-", "\u2014"), ("\u30fc", "\u2014"),
              ("(", "["), ("(", "{"), ("[", "{"), ("rn", "m"), ("B", "8"), ("S", "5"), ("Z", "2"),
              ("(", "\uff08"), (")", "\uff09"), (",", "\uff0c"), (":", "\uff1a"), ("=", "\uff1d"), ('"', "\uff02"),
              (" ", "\u3000"), ("A", "\uff21"), ("0", "\uff10"))


def _drawn(font, text, w=96, h=40):
    from PySide6 import QtCore, QtGui
    img = QtGui.QImage(w, h, QtGui.QImage.Format_Grayscale8)
    img.fill(0)
    p = QtGui.QPainter(img)
    p.setFont(font); p.setPen(QtGui.QColor(255, 255, 255))
    p.drawText(QtCore.QPointF(4, 26), text)          # on a baseline (a rect + alignment dropped the hyphen offscreen)
    p.end()
    return [[img.pixelColor(x, y).red() > 40 for x in range(w)] for y in range(h)]    # thin strokes are grey at 10 pt


def test_every_confusable_pair_draws_differently_in_the_chosen_face(qapp):
    from PySide6 import QtGui
    assert len(CONFUSABLE) == 36 and all(a != b for a, b in CONFUSABLE)
    # 12 pt: the offscreen platform's FreeType draws NO ink for BIZ UDGothic's hyphen at exactly 10 pt (the
    # Windows platform draws it at 9..12 pt — measured; the 10 pt comparison on the real platform is in the report)
    font = studio_theme.code_font(12)
    fm = QtGui.QFontMetricsF(font)
    same, inked = [], 0
    for a, b in CONFUSABLE:
        ga, gb = _drawn(font, a), _drawn(font, b)
        diff = sum(1 for ra, rb in zip(ga, gb) for x, y in zip(ra, rb) if x != y)
        inked += any(any(r) for r in ga) and any(any(r) for r in gb)
        if diff == 0 and fm.horizontalAdvance(a) == fm.horizontalAdvance(b):
            same.append((a, b))
    assert inked >= 30, inked                    # the comparison is of real glyphs (thin dashes may leave no ink offscreen)
    # What the face cannot separate must be caught by the marks instead (found: the minus sign U+2212 is drawn
    # exactly like the hyphen in BIZ UDGothic). Nothing may be both identical AND unmarked.
    unmarked = [(a, b) for a, b in same if not studio_theme.suspicious_chars(a) and not studio_theme.suspicious_chars(b)]
    assert unmarked == [], "drawn identically at 12 pt in %s and not marked: %r" % (studio_theme.code_family(), unmarked)
    assert len(same) <= 2, same
    assert studio_theme.suspicious_chars("a \u2212 b") == [(2, "lookalike")]


def test_full_width_is_two_half_width_cells_and_ligatures_are_off(qapp):
    from PySide6 import QtGui
    if studio_theme.code_family() not in ("BIZ UDGothic", "MS Gothic", "Noto Sans Mono CJK JP"):
        pytest.skip("no Japanese dual-width family installed: the chosen face is %s" % studio_theme.code_family())
    for pt in (9, 10, 11, 12, 14):
        font = studio_theme.code_font(pt)
        fm = QtGui.QFontMetricsF(font)
        half = fm.horizontalAdvance("a" * 40) / 40.0
        for ch in ("\u3042", "\u6f22", "\uff21", "\u3000", "\uff08", "\u30fc"):   # kana, kanji, full-width A / space / ( / long mark
            full = fm.horizontalAdvance(ch * 40) / 40.0
            assert abs(full - 2 * half) <= 1.0, (pt, ch, full, half)
        assert fm.horizontalAdvance("\uff76") == pytest.approx(half, abs=1.0)        # half-width kana: one cell
        assert fm.horizontalAdvance("i" * 40) == pytest.approx(fm.horizontalAdvance("W" * 40), abs=0.5)
        # Python indentation: four spaces are four cells, whatever follows
        assert fm.horizontalAdvance("    x") == pytest.approx(5 * half, abs=0.5)
        for pair in ("!=", "->", "==", "<=", ">=", "=>", "//", "**", "::"):          # no ligature: a pair is two cells
            assert fm.horizontalAdvance(pair) == pytest.approx(
                fm.horizontalAdvance(pair[0]) + fm.horizontalAdvance(pair[1]), abs=0.5), (pt, pair)


def test_suspicious_characters_are_found_by_kind():
    find = studio_theme.suspicious_chars
    assert find("x = 1") == [] and find("") == []
    assert find("x\u3000= 1") == [(1, "wide_space")]
    assert find("f\uff08a\uff09\uff1a") == [(1, "wide_ascii"), (3, "wide_ascii"), (4, "wide_ascii")]
    assert find("a\u200bb\u202ec\ufeff") == [(1, "invisible"), (3, "invisible"), (5, "invisible")]
    assert find("p\u0430ss") == [(1, "lookalike")]                                   # Cyrillic a inside "pass"
    # pasted from a document: typographic quotes, the em dash (1 px from "-" in BIZ UDGothic), primes
    assert find("print(\u2018a\u2019)") == [(6, "lookalike"), (8, "lookalike")]
    assert find("s = \u201cab\u201d") == [(4, "lookalike"), (7, "lookalike")]
    assert find("x \u2014 y \u2015 z") == [(2, "lookalike"), (6, "lookalike")]
    assert find("t = 3\u2032 + 4\u2033") == [(5, "lookalike"), (10, "lookalike")]
    assert find("print('a', \"b\")  # ascii quotes - and _") == []                 # the ASCII ones are not
    assert find("x = 1  \t") == [(5, "trailing"), (6, "trailing"), (7, "trailing")]
    assert find("\tif x:") == [(0, "tab")]
    assert find("# \u65e5\u672c\u8a9e\u306e\u30b3\u30e1\u30f3\u30c8 abc") == []   # ordinary Japanese is not suspicious
    assert set(k for _i, k in find("\u3000\uff21\u200b\u0430\t ")) <= set(studio_theme.SUSPICIOUS_KINDS)
    assert len(studio_theme.SUSPICIOUS_KINDS) == 6


def test_marks_are_painted_over_a_full_width_space_and_its_kin(qapp):
    from PySide6 import QtGui, QtWidgets
    studio_theme.set_current(studio_theme.DEFAULT_THEME, studio_theme.DEFAULT_DENSITY)
    lines = ["x = 1", "y\u3000= 2", "f\uff08a\uff09", "p\u0430ss\u200b", "z = 3   "]

    def shot(marked, trailing=True):
        ed = QtWidgets.QPlainTextEdit()
        ed.setStyleSheet("QPlainTextEdit { background:#1d2126; color:#e4e7eb; border:none; }")
        studio_theme.apply_code_font(ed, 12)
        ed.setPlainText("\n".join(lines))
        ed.resize(360, 160)
        marks = studio_theme.mark_code(ed, trailing=trailing) if marked else None
        ed.show()
        for _ in range(20):
            qapp.processEvents()
        img = ed.viewport().grab().toImage().convertToFormat(QtGui.QImage.Format_RGB32)
        second = ed.document().firstBlock().next()                 # where the first line ends, measured
        line2 = ed.blockBoundingGeometry(second).translated(ed.contentOffset()).top()
        out = (img, marks.count if marks else 0, dict(marks.kinds) if marks else {}, int(line2))
        ed.close(); ed.deleteLater()
        return out

    plain, n0, _k0, line2 = shot(False)
    marked, n1, kinds, _l2 = shot(True)
    assert n0 == 0 and n1 == 1 + 2 + 2 + 3                                           # every mark of the text, counted
    assert kinds == {"wide_space": 1, "wide_ascii": 2, "lookalike": 1, "invisible": 1, "trailing": 3}
    changed = sum(1 for y in range(plain.height()) for x in range(plain.width()) if plain.pixel(x, y) != marked.pixel(x, y))
    assert changed > 60                                                              # the marks are really on the picture
    warn = QtGui.QColor(studio_theme.PALETTES[studio_theme.DEFAULT_THEME]["warn"])
    near = sum(1 for y in range(marked.height()) for x in range(marked.width())
               if abs(marked.pixelColor(x, y).red() - warn.red()) < 12 and abs(marked.pixelColor(x, y).green() - warn.green()) < 12
               and abs(marked.pixelColor(x, y).blue() - warn.blue()) < 12)
    assert near > 20                                                                 # in the caution colour (frame + underlines)
    _img, n2, kinds2, _l3 = shot(True, trailing=False)
    assert n2 == n1 - 3 and "trailing" not in kinds2                                 # the faint marks can be switched off
    # a clean line gets no mark (its rows are measured: at 12 pt the second line starts above 20 px)
    assert 10 <= line2 <= 40, line2
    first_line = sum(1 for y in range(0, line2) for x in range(plain.width()) if plain.pixel(x, y) != marked.pixel(x, y))
    second_line = sum(1 for y in range(line2, 2 * line2) for x in range(plain.width()) if plain.pixel(x, y) != marked.pixel(x, y))
    assert first_line == 0 and second_line > 0, (first_line, second_line, line2)


@pytest.mark.parametrize("name", studio_theme.THEMES)
def test_code_roles_can_be_told_apart_also_with_protan_and_deutan_vision(name):
    rows = studio_theme.distinct_report(name)
    assert len(rows) == len(studio_theme.DISTINCT_PAIRS) == 23
    bad = [r for r in rows if not r[6]]
    assert not bad, bad
    for a, b, d0, dp, dd, cue, _ok in rows:
        assert d0 >= studio_theme.DISTINCT_MIN, (a, b, d0)
        assert min(dp, dd) >= studio_theme.DISTINCT_MIN_CVD or cue, (a, b, dp, dd)   # never by red against green alone
    p = studio_theme.PALETTES[name]
    for role in studio_theme.SYNTAX_ROLES + ("text",):
        assert studio_theme.contrast(p[role], p["editor"]) >= 4.5, role               # WCAG AA on the editor ground
        assert role in studio_theme.CODE_STYLE
    assert "syn_op" in studio_theme.SYNTAX_ROLES and len(studio_theme.SYNTAX_ROLES) == 10
    # the measure itself: black / white are 100 apart, a colour is 0 from itself, red and green collapse for a deutan eye
    assert studio_theme.delta_e("#000000", "#ffffff") == pytest.approx(100.0, abs=0.1)
    assert studio_theme.delta_e(p["syn_num"], p["syn_num"]) == 0
    assert studio_theme.delta_e(studio_theme.simulate_cvd("#d04040", "deutan"), studio_theme.simulate_cvd("#6a8a2a", "deutan")) < \
        studio_theme.delta_e("#d04040", "#6a8a2a") / 2


@pytest.mark.parametrize("name", studio_theme.THEMES)
def test_the_code_colour_table_has_every_role_the_user_listed_and_passes_its_gates(name):
    """User, 2026-11-13: numbers, names, keywords, strings, comments, operators, brackets, op names,
    undefined names and the ground of a suspicious character, in a table; 4.5 : 1 and told apart, both schemes."""
    table = studio_theme.code_colour_table(name)
    listed = ("number", "name", "keyword", "string", "comment", "operator", "bracket", "op name",
              "undefined name", "suspicious-character ground")
    assert len(table) == 12 and [r[0] for r in table][:10] == list(listed)
    p = studio_theme.PALETTES[name]
    roles = [r[2] for r in table]
    assert len(set(roles)) == len(roles)                                           # one role per meaning
    assert set(roles) - {"text"} == set(studio_theme.SYNTAX_ROLES) | set(studio_theme.CODE_GROUND_ROLES)
    fg = [r for r in table if r[2] not in studio_theme.CODE_GROUND_ROLES]
    assert len(fg) == 11
    for en, _ja, role, hex_, low, _cue in fg:
        assert hex_ == p[role] and low >= 4.5, (name, en, role, low)                   # on the editor, the current line, the ground
    # colour is never the only cue where a reader must stop: an undefined name is also underlined (wave)
    assert studio_theme.CODE_STYLE["syn_undef"] == {"underline": "wave"}
    rows = studio_theme.ground_report(name)
    assert len(rows) == 3 and all(r[3] for r in rows), rows                       # the ground stands apart
    # the state hues (ok / warn / err) are not reused for op names or brackets
    for role in ("syn_opname", "syn_bracket"):
        assert all(studio_theme.delta_e(p[role], p[s]) >= studio_theme.DISTINCT_MIN for s in ("ok", "warn", "err")), role


def test_apply_keeps_the_widgets_own_rules_and_does_not_pile_up(qapp):
    from PySide6 import QtWidgets
    plain = QtWidgets.QPlainTextEdit()
    lst = QtWidgets.QListWidget()
    lst.setStyleSheet("QListWidget::item { height: 20px; }")
    for w in (plain, lst):
        for pt in (10, 14, 12):
            studio_theme.apply_code_font(w, pt)
        sheet = w.styleSheet()
        assert sheet.count("/*code-font*/") == sheet.count("/*end-code-font*/") == 1
        assert "font-size:12pt" in sheet and "font-size:14pt" not in sheet and "font-size:10pt" not in sheet
        w.ensurePolished()
        assert _resolved(w) == (studio_theme.code_family(), True, 12)
    assert lst.styleSheet().startswith("QListWidget::item { height: 20px; }")
    assert plain.tabStopDistance() > 0
    for w in (plain, lst):
        w.deleteLater()


def test_code_inside_a_help_page_follows_also_after_a_new_page_is_loaded(qapp):
    from PySide6 import QtGui, QtWidgets
    host = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(host)
    br = QtWidgets.QTextBrowser(); lay.addWidget(br)
    page = ("<h2>op</h2><p>prose here</p><p style='font-family:monospace;font-size:11px'>op(a, b) -&gt; image</p>"
            "<p>call <code>fullseye.run(\"x\")</code> or</p><pre>import fullseye\nfullseye.run()</pre>")
    br.setHtml(page)

    def census():
        code, prose = [], []
        block = br.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fr = it.fragment()
                if fr.isValid() and fr.text().strip():
                    fam = QtGui.QFontInfo(fr.charFormat().font()).family()
                    (code if fr.charFormat().fontFixedPitch() or "fullseye" in fr.text() or "op(a" in fr.text()
                     else prose).append((fr.text()[:14], fam, QtGui.QFontInfo(fr.charFormat().font()).fixedPitch()))
                it += 1
            block = block.next()
        return code, prose

    code, prose = census()
    assert len(code) >= 3 and len(prose) >= 3
    n, frags = studio_theme.apply_code_fonts(host)
    assert n == 0 and frags >= 3
    code, prose_after = census()
    assert len(code) >= 3 and all(fam == studio_theme.code_family() and fixed for _t, fam, fixed in code), code
    assert prose_after == prose                                                       # prose keeps its own face
    assert studio_theme.apply_code_fonts(host)[1] == 0                                # nothing left to do
    br.setHtml(page.replace("op(a, b)", "op2(a, b, c)"))                              # a new page later
    _pump(qapp, 0.05)
    code, _prose = census()
    assert len(code) >= 3 and all(fam == studio_theme.code_family() and fixed for _t, fam, fixed in code), code
    host.deleteLater()


# --------------------------------------------------------------------------- #
# the real window
# --------------------------------------------------------------------------- #
@pytest.fixture()
def win(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
    monkeypatch.delenv("FULLSEYE_STUDIO_PERSIST_LAYOUT", raising=False)
    import studio
    studio_theme.set_current(studio_theme.DEFAULT_THEME, studio_theme.DEFAULT_DENSITY)
    w, _model = studio.build_window()
    w.show()
    _pump(qapp, 0.4)
    yield w
    for top in list(qapp.topLevelWidgets()):
        if top is not w and top.isVisible() and top.parent() is w:
            top.close()
    w.quiesce()
    w.close_guard = lambda: True
    w.close()
    _pump(qapp, 0.15)


def _kinds(surfaces):
    out = {}
    for kind, _w in surfaces:
        out[kind] = out.get(kind, 0) + 1
    return out


def test_every_code_surface_of_the_window_is_fixed_pitch(win, qapp):
    from PySide6 import QtWidgets
    surfaces = studio_theme.code_surfaces(win)
    kinds = _kinds(surfaces)
    # the Program box; inspector + value of a variable; the op list; completion lists of the Program box and the op search
    assert kinds.get("editor", 0) >= 1 and kinds.get("readout", 0) >= 2, kinds
    assert kinds.get("op_list", 0) == 1 and kinds.get("completion", 0) >= 2, kinds
    assert len(surfaces) >= 6
    family = studio_theme.code_family()
    for kind, w in surfaces:
        w.ensurePolished()
        assert _resolved(w) == (family, True, 10), (kind, type(w).__name__, _resolved(w))
    # nothing that holds code was left out: every QPlainTextEdit of the window is in the list
    listed = {id(w) for _k, w in surfaces}
    plains = win.findChildren(QtWidgets.QPlainTextEdit)
    assert len(plains) >= 3 and all(id(p) in listed for p in plains)
    assert win._op_list.count() > 50 and id(win._op_list) in listed
    # the hint labels (status read-outs) take the same stack from the window sheet
    hints = [lab for lab in win.findChildren(QtWidgets.QLabel) if lab.property("hint")]
    assert len(hints) >= 3
    for lab in hints:
        lab.ensurePolished()
        assert _resolved(lab)[:2] == (family, True), lab.text()


def test_surfaces_built_later_get_it_when_first_shown(win, qapp):
    from PySide6 import QtWidgets
    assert getattr(win, "_pyedit", None) is None                 # the Python editor does not exist yet
    win._act_pyedit.trigger()
    _pump(qapp, 0.5)
    dlg = win._pyedit["dlg"]
    surfaces = studio_theme.code_surfaces(dlg)
    kinds = _kinds(surfaces)
    assert kinds.get("editor", 0) >= 1 and kinds.get("readout", 0) >= 1 and kinds.get("completion", 0) >= 1, kinds
    assert len(surfaces) >= 3
    family = studio_theme.code_family()
    for kind, w in surfaces:
        w.ensurePolished()
        assert _resolved(w) == (family, True, 10), (kind, type(w).__name__, _resolved(w))
    before = win._pyedit["tabs"].count()
    win._pyedit["new"]()                                         # a second tab, built after the dialog was shown
    _pump(qapp, 0.4)
    assert win._pyedit["tabs"].count() == before + 1
    editors = [w for w in dlg.findChildren(QtWidgets.QPlainTextEdit) if not w.isReadOnly()]
    assert len(editors) >= 2
    for ed in editors:
        ed.ensurePolished()
        assert _resolved(ed) == (family, True, 10)
    dlg.close()


def test_the_size_setting_reaches_every_surface(win, qapp):
    from PySide6 import QtCore
    win._act_pyedit.trigger()
    _pump(qapp, 0.5)
    everything = studio_theme.code_surfaces(win) + studio_theme.code_surfaces(win._pyedit["dlg"])
    assert len(everything) >= 9
    assert {_resolved(w)[2] for _k, w in everything} == {10}
    assert win._apply_mono_font(15) == 15
    _pump(qapp, 0.2)
    for kind, w in everything:
        w.ensurePolished()
        assert _resolved(w) == (studio_theme.code_family(), True, 15), (kind, type(w).__name__, _resolved(w))
    assert studio_theme.code_pt() == 15
    s = QtCore.QSettings(os.environ["FULLSEYE_STUDIO_SETTINGS"], QtCore.QSettings.IniFormat)
    assert int(s.value("ui/mono_font_pt")) == 15                 # saved for the next start
    assert win._apply_mono_font(400) == 32                       # clamped
    win._apply_mono_font(10)
    _pump(qapp, 0.1)
    assert {_resolved(w)[2] for _k, w in everything} == {10}
    # scheme / density / language changes do not undo it (the density pass rewrites the op list's sheet)
    win._apply_theme(theme="panel", level="standard", save=False)
    win._apply_language("ja")
    _pump(qapp, 0.2)
    try:
        for kind, w in everything:
            w.ensurePolished()
            assert _resolved(w) == (studio_theme.code_family(), True, 10), (kind, type(w).__name__, _resolved(w))
    finally:
        win._apply_language("en")
        win._apply_theme(theme=studio_theme.DEFAULT_THEME, level=studio_theme.DEFAULT_DENSITY, save=False)
        win._pyedit["dlg"].close()


def test_choosing_another_family_reaches_every_surface(win, qapp):
    others = [f for f in studio_theme.code_font_choices() if f != studio_theme.code_family()]
    if not others:
        pytest.skip("only one of the listed families is installed here")
    assert len(studio_theme.code_font_choices()) >= 2
    surfaces = studio_theme.code_surfaces(win)
    assert len(surfaces) >= 6
    studio_theme.set_code_family(others[-1])
    win._apply_mono_font(11)
    _pump(qapp, 0.2)
    for kind, w in surfaces:
        w.ensurePolished()
        assert _resolved(w) == (others[-1], True, 11), (kind, type(w).__name__, _resolved(w))
