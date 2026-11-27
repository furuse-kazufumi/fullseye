"""The common gates of Studio 1.2.0 (STUDIO_INTERACTION_RULES 2026-11-13 5.1, BRIEFS B3 step 2; R2-S04).

Six groups, each counted on the real window (offscreen, Fusion, settings in tmp_path) or on the syntax tree, and
compared with the one-way ledger tests/data/studio_interaction_ledger.json (during 1.2.0 more than the ledger fails;
what was fixed is taken out with ``py -3.11 tools/studio_interaction_ledger.py --shrink``; the ledger is never
widened to let a gate pass). Every gate has a lower bound of what it examined, so an empty count fails.

  test_dialog_construction_sites_within_ledger         G09(a)   boxes / input windows made outside confirm_action
  test_confirm_kinds_default_and_escape_are_cancel     G09(b')  the 5 kinds built by the making function
  test_window_wide_key_meaning_overlaps_within_ledger  G13(b')(c) one key, two meanings / 7-language mnemonics
  test_untranslated_and_ampersand_within_ledger        G15(a')(b) untranslated text (6 languages) / eaten '&'
  test_toolbutton_checked_disabled_rules               G04(c')(d')
  test_principal_and_title_band                        G01(a)(f)(g)
"""
import json

import pytest

import studio_gatekit as kit


@pytest.fixture
def gate_window(tmp_path, monkeypatch):
    """The Studio window at 1280x673 under offscreen with the Fusion style and its own settings file."""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "gates.ini"))
    monkeypatch.delenv("FULLSEYE_STUDIO_PERSIST_LAYOUT", raising=False)
    app, win = kit.open_window(tmp_path / "gates.ini")
    assert app.style().objectName().lower() == "fusion"
    try:
        yield app, win
    finally:
        kit.close_window(app, win)


def test_the_ledger_is_well_formed_and_names_every_gate():
    """The ledger has one entry per gate of the kit, each count = its items, each item a D number and a place."""
    data = json.loads(kit.LEDGER.read_text(encoding="utf-8"))
    gates = data["gates"]
    assert sorted(gates) == sorted(kit.GATES)
    for gate, led in gates.items():
        assert led["count"] == len(led["items"]), gate
        keys = [kit.key_of(i) for i in led["items"]]
        assert len(keys) == len(set(keys)), gate                       # no item twice
        for i in led["items"]:
            assert i["d"].startswith("D") and i["where"] and i["text"], (gate, i)


def test_the_kit_walks_the_whole_window(gate_window):
    """The walker sees every kind of thing the gates count (each with a floor), and the dialogs list is the shown
    QDialogs of the application."""
    app, win = gate_window
    found = kit.walk(win)
    kit.at_least(len(found["views"]), 8, "item views")
    kit.at_least(len(found["line_edits"]), 3, "line edits")
    kit.at_least(len(found["plain_edits"]) + len(found["text_edits"]), 2, "text editors")
    kit.at_least(len(found["buttons"]), 40, "buttons")
    assert [d for d in found["dialogs"] if not d.isVisible()] == []     # only shown dialogs are walked


def test_dialog_construction_sites_within_ledger():
    """G09(a): QMessageBox( / QMessageBox.question|... / QDialogButtonBox / QInputDialog calls outside the making
    functions of confirm_action and ask_text <= the ledger (base 15 on f33a163ccd)."""
    items, examined = kit.count_g09a()
    assert len(kit.studio_sources()) >= 10
    kit.assert_within_ledger("G09(a)", items, examined)


def test_dialog_construction_gate_sees_a_planted_box(tmp_path):
    """The syntax-tree count is not blind: a box made in a new function, a static question and an input window are
    three new items; the same calls inside the making function are not counted."""
    src = tmp_path / "studio_planted.py"
    src.write_text(
        "from PySide6 import QtWidgets\n"
        "def planted(w):\n"
        "    QtWidgets.QMessageBox(w)\n"
        "    QtWidgets.QMessageBox.question(w, 't', 'x')\n"
        "    QtWidgets.QInputDialog.getText(w, 't', 'x')\n"
        "def _build_confirm_box(w):\n"
        "    return QtWidgets.QMessageBox(w)\n" + "x = 1\n" * 3, encoding="utf-8")
    items, examined = kit.count_g09a(tmp_path)
    assert [i["text"] for i in items] == ["QMessageBox #1", "QMessageBox.question #1", "QInputDialog.getText #1"]
    assert {i["where"] for i in items} == {"studio_planted.py::planted"}
    assert examined == 4


def test_confirm_kinds_default_and_escape_are_cancel(gate_window):
    """G09(b'): run / unsaved / changed / trust / text built by the making function: default = Esc = Cancel,
    no standard buttons, words in the i18n table. A kind without the function is one ledger item (B4: D106)."""
    import studio
    items, examined = kit.count_g09b(studio)
    assert examined == len(kit.CONFIRM_KINDS) == 5
    kit.assert_within_ledger("G09(b')", items, examined)


def test_window_wide_key_meaning_overlaps_within_ledger(gate_window):
    """G13(b'): keys bound to two meanings over the whole window <= the ledger (base 5); G13(c): menu-bar
    mnemonics used twice, in each of the 7 languages <= the ledger (goal 0, 5.4)."""
    app, win = gate_window
    items, examined = kit.count_g13b(win)
    kit.assert_within_ledger("G13(b')", items, examined)
    import studio
    langs = tuple(studio.LANGUAGES)
    assert sorted(langs) == sorted(("en",) + kit.LANGS_NOT_EN)
    items, examined = kit.count_g13c(app, win, ("en",) + kit.LANGS_NOT_EN)
    kit.assert_within_ledger("G13(c)", items, examined)


def test_untranslated_and_ampersand_within_ledger(gate_window):
    """G15(a'): text shown in a non-English language that equals an English source of the i18n table (or is three
    English words in a language with its own script) <= the ledger; G15(b): '&' eaten as a mnemonic <= the ledger."""
    app, win = gate_window
    (un, un_n), (amp, amp_n) = kit.count_g15(app, win)
    kit.assert_within_ledger("G15(a')", un, un_n)
    kit.assert_within_ledger("G15(b)", amp, amp_n)


def test_untranslated_rule_matches_the_source_not_the_script():
    """The judgement is the match with the source text: German that equals the English source counts, German that
    differs does not; three English words count in ja, a name with '_' does not, a row equal in both languages is
    not counted."""
    src = {"Open image": {"ja": "画像を開く", "de": "Bild öffnen"}, "OK": {"de": "OK"}}
    assert kit._untranslated("de", "menu", "Open image", src)
    assert not kit._untranslated("de", "menu", "Bild öffnen", src)
    assert not kit._untranslated("de", "button", "OK", src)
    assert kit._untranslated("ja", "button", "Run the whole thing", src)
    assert not kit._untranslated("ja", "button", "gauss_filter on image", src)
    assert not kit._untranslated("ja", "label", "Run the whole thing", src)      # prose: only the match counts


def test_toolbutton_checked_disabled_rules():
    """G04(c')(d'): every theme's QSS has QToolButton:checked and :disabled and QPushButton:disabled, distinct from
    the normal rule (structure, not pixels)."""
    import studio_theme
    items, examined = kit.count_g04(studio_theme)
    kit.assert_within_ledger("G04(c')(d')", items, examined)


def test_principal_and_title_band(gate_window):
    """G01(a)(f)(g): a non-principal x is DENSITY["title_button"] px and shown, the principal has no x and its bar
    button never hides it, the rightmost widget of every title band is the menu."""
    app, win = gate_window
    items, examined = kit.count_g01(app, win)
    kit.assert_within_ledger("G01(a)(f)(g)", items, examined)


def test_ledger_compare_finds_new_and_fixed():
    """compare(): an item not in the ledger is new, a ledger item not found is fixed (what --shrink removes)."""
    ledger = {"G": {"count": 2, "items": [{"d": "D1", "where": "a", "text": "x"},
                                          {"d": "D2", "where": "b", "text": "y"}]}}
    new, fixed = kit.compare("G", [{"d": "D1", "where": "a", "text": "x"}, {"d": "D3", "where": "c", "text": "z"}],
                             ledger)
    assert [i["where"] for i in new] == ["c"] and [i["where"] for i in fixed] == ["b"]
    with pytest.raises(AssertionError):
        kit.at_least(3, 4, "floor")
