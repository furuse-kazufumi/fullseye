# -*- coding: utf-8 -*-
"""studio_keymap / studio_keymap_qt: 利用者が決められるショートカットキー(登録簿・型・当たり・保存・設定の窓)。

前半は Qt なし(登録簿・正規化・当たりの判定・保存の形・読み込みの拒否・文の書き換え・対訳・文書の表)。
後半は offscreen の本物の窓(``studio.build_window``)に、配線の覚え書きどおりに取り付けて確かめる:
メニューの表示と実際のキーの一致、新しいキーで効き古いキーで効かない事(窓全体・Program 欄・矩形選択の部品)、
保存して次の起動で効く事、壊れた設定でも起動する事、言語の切り替え、設定の窓(探す・記録・当たり・戻す・型・
書き出しと読み込み)、別窓の QShortcut。設定は一時ファイル(利用者のレジストリには書かない)。
"""
import json
import os
import re
import time

import pytest

import studio_editops as eo
import studio_keymap as km

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------- #
# 登録簿
# --------------------------------------------------------------------------- #
def test_registry_counts_and_every_command_has_a_scope_and_default_keys():
    cmds = km.COMMANDS
    # 件数を先に確かめる(足した・消したら、ここが知らせる)
    assert len(cmds) == 124
    assert sum(not c.fixed for c in cmds) == 111 and sum(c.fixed for c in cmds) == 13
    assert sum(bool(c.keys) for c in cmds if not c.fixed) == 90
    assert sum(len(c.keys) for c in cmds if not c.fixed) == 94
    assert len({c.id for c in cmds}) == len(cmds)
    for c in cmds:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", c.id), c.id
        assert c.scope in km.SCOPES, c.id
        assert isinstance(c.keys, tuple), c.id
        assert all(km.normalize_sequence(k) == k for k in c.keys), c.id
        assert c.title and c.title.strip() == c.title, c.id
        if c.fixed:
            assert c.keys and not c.target, c.id                      # 組み込みはキーを持ち、取り付け先は無い
        else:
            assert c.target.split(":")[0] in {"action", "label", "attr", "work_mode", "editops", "shortcut", "own"}
        if c.target.startswith("action:"):
            assert c.target == "action:" + c.id                        # win._actions の鍵 = ID
        for m in c.mentions:
            assert m in km.BY_ID and m != c.id
        if c.ide:
            assert c.scope == "program_editor"
    used = {s for _t, scopes in km.PLACES.values() for s in scopes}
    assert used == set(km.SCOPES)                                      # どの範囲も、どこかの場所で効く


def test_the_editor_commands_are_the_box_selection_table_one_to_one():
    rows = [c for c in km.COMMANDS if c.target.startswith("editops:")]
    assert len(rows) == len(eo.KEYMAP) == 15
    for c, b in zip(rows, eo.KEYMAP):
        assert c.target == "editops:" + b.command and c.id == km.editops_id(b.command)
        assert c.keys == tuple(eo.normalize_key(k) for k in b.keys)
        assert c.title == b.title
    assert km.BY_ID["editops_box_cancel"].scope == "editor_box"
    assert km.BY_ID["editops_line_comment"].scope == "editor_no_comment"


@pytest.mark.parametrize("preset", sorted(km.PRESETS))
def test_presets_have_no_conflict_and_no_key_the_os_takes(preset):
    k = km.Keymap(preset)
    probs = k.problems()
    assert [p for p in probs if p.level == "error"] == []
    # 範囲が違うので当たりでない物は info として見えている(空で通る検査にしない)
    infos = {(p.code, p.command, p.key, p.other) for p in probs if p.level == "info"}
    assert ("shadow", "focus_search", "Ctrl+F", "program_find") in infos
    assert ("shadow", "leave_image_focus", "Esc", "editops_box_cancel") in infos
    assert ("shared", "editops_box_cancel", "Esc", "fixed_program_close_find") in infos
    assert len(k.entries()) >= 120
    for cid, keys in km.PRESETS[preset].items():
        assert cid in km.BY_ID and not km.BY_ID[cid].fixed
        assert all(km.normalize_sequence(x) == x for x in keys)
        assert [p for p in km.validate_keys(cid, keys) if p.level == "error"] == []


def test_the_two_presets_differ_where_the_ides_differ():
    vs, code = km.Keymap("visual_studio"), km.Keymap("vscode")
    assert vs.keys("editops_line_duplicate") == ("Ctrl+D",) and vs.keys("editops_multi_add_next") == ("Shift+Alt+.",)
    assert code.keys("editops_multi_add_next") == ("Ctrl+D",) and code.keys("editops_line_duplicate") == ("Shift+Alt+Down",)
    assert code.keys("editops_box_down") == ("Ctrl+Shift+Alt+Down", "Ctrl+Alt+Down")
    assert code.keys("palette") == ("Ctrl+Shift+P", "F1") and code.keys("find_panel") == ("Ctrl+P",)
    assert vs.keys("duplicate_stage") == code.keys("duplicate_stage") == ("Ctrl+D",)  # 段の一覧はどちらも段の複製
    differ = [c.id for c in km.COMMANDS if not c.fixed and vs.keys(c.id) != code.keys(c.id)]
    assert sorted(differ) == sorted(km.PRESETS["vscode"])


# --------------------------------------------------------------------------- #
# キーの書き方
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw, want", [
    ("shift+ctrl+k", "Ctrl+Shift+K"), ("Ctrl+K, Ctrl+S", "Ctrl+K, Ctrl+S"), ("ctrl+k ctrl+s", "Ctrl+K, Ctrl+S"),
    ("Ctrl++", "Ctrl++"), ("Ctrl + =", "Ctrl+="), ("Ctrl+,", "Ctrl+,"), ("Ctrl+,, Ctrl+S", "Ctrl+,, Ctrl+S"),
    ("Alt+Shift+.", "Shift+Alt+."), ("backtab", "Shift+Tab"), ("Strg+Umschalt+a", "Ctrl+Shift+A"),
    ("escape", "Esc"), ("delete", "Del"), ("pagedown", "PgDown"), ("f12", "F12"), ("Ctrl+Shift+\\", "Ctrl+Shift+\\"),
    ("Enter", "Enter"), ("Return", "Return"), ("+", "+"),
])
def test_normalize_sequence(raw, want):
    assert km.normalize_sequence(raw) == want


@pytest.mark.parametrize("raw, code", [
    ("", "bad_key"), ("Ctrl+", "bad_key"), ("Hyper+K", "bad_key"), ("Ctrl+Shift", "bad_key"), ("Ctrl+あ", "bad_key"),
    ("F36", "bad_key"), ("A, B, C", "too_many_strokes"), (None, "bad_key"),
])
def test_unreadable_keys_are_refused_with_a_reason(raw, code):
    with pytest.raises(km.KeyParseError) as ei:
        km.normalize_sequence(raw)
    assert ei.value.code == code


# --------------------------------------------------------------------------- #
# 当たりの判定(範囲を考える)
# --------------------------------------------------------------------------- #
def _codes(probs):
    return sorted((p.level, p.code, p.other) for p in probs)


def test_same_scope_is_a_conflict_and_nothing_changes():
    k = km.Keymap()
    probs = k.assign("export", ("Ctrl+O",))
    assert _codes(probs) == [("error", "ambiguous", "open_image")]
    assert k.keys("export") == ("Ctrl+E",) and k.keys("open_image") == ("Ctrl+O",) and k.overrides() == {}


def test_window_and_the_stage_list_overlap_so_qt_would_fire_neither():
    probs = km.Keymap().check("export", ("Ctrl+D",))
    errs = [p for p in probs if p.level == "error"]
    assert [(p.code, p.other, p.place) for p in errs] == [("ambiguous", "duplicate_stage", "stage_list")]
    # 同じキーはエディタでは行の複製(部品が先に取る)= 当たりではなく知らせるだけ
    assert ("info", "shadow", "editops_line_duplicate") in _codes(probs)


def test_a_part_that_takes_its_key_first_only_shadows_the_window_key():
    probs = km.Keymap().check("export", ("F3",))
    assert _codes(probs) == [("info", "shadow", "fixed_find_next"), ("info", "shadow", "program_find_next")]
    probs = km.Keymap().check("program_find_next", ("Ctrl+E",))           # 部品の側から見ると「先に取る」
    assert _codes(probs) == [("info", "shadows", "export")]


def test_disjoint_scopes_do_not_conflict():
    assert km.Keymap().check("duplicate_stage", ("Shift+Alt+Up",)) == []    # 段の一覧 と エディタ
    assert km.Keymap().check("python_editor_run", ("F6",)) == []           # 別窓 と 本体の窓全体


def test_two_parts_of_the_same_editor_conflict():
    probs = km.Keymap().check("program_find", ("Ctrl+Shift+K",))
    assert _codes(probs) == [("error", "same_widget", "editops_line_delete")]


def test_a_two_stroke_key_and_its_first_stroke_conflict():
    probs = km.Keymap().check("export", ("Ctrl+K",))
    assert _codes(probs) == [("error", "prefix", "keyboard_settings")]
    assert km.Keymap().check("export", ("Ctrl+K, Ctrl+E",)) == []           # 2 打目が違えば並べられる


def test_a_key_that_never_reaches_the_command_is_refused():
    probs = km.Keymap().check("python_editor_run", ("Ctrl+Space",))
    assert ("error", "unreachable", "fixed_complete") in _codes(probs)
    assert ("warning", "warn_ime", "") in _codes(probs)


def test_key_rules_by_scope():
    k = km.Keymap()
    assert _codes(k.check("editops_line_duplicate", ("Ctrl+K, Ctrl+D",))) == [("error", "chord_not_here", "")]
    assert _codes(k.check("export", ("E",))) == [("error", "plain_key", "")]
    assert _codes(k.check("export", ("Shift+E",))) == [("error", "plain_key", "")]
    assert ("error", "plain_key", "") in _codes(k.check("export", ("Tab",)))
    assert k.check("image_viewer_fit", ("G",)) == []                          # 文字を打たない窓では修飾なしでよい
    assert _codes(k.check("export", ("Alt+Tab",))) == [("error", "os_taken", "")]
    assert _codes(k.check("export", ("Meta+E",))) == [("error", "os_taken", "")]
    assert _codes(k.check("export", ("Ctrl+Alt+E",))) == [("warning", "warn_altgr", "")]
    assert _codes(k.check("export", ("F10",))) == [("warning", "warn_menu_key", "")]
    assert _codes(k.check("export", ("A", "B", "C", "D", "E"))).count(("error", "too_many_keys", "")) == 1
    assert _codes(k.check("fixed_complete", ("Ctrl+F12",))) == [("error", "fixed_command", "")]
    assert _codes(k.check("no_such_command", ("Ctrl+F12",))) == [("error", "unknown_command", "")]
    assert k.assign("export", ("Ctrl+Alt+E",)) and k.keys("export") == ("Ctrl+Alt+E",)   # 警告は当てて知らせる


def test_fixed_entries_from_the_window_take_part():
    menu = km.Entry("menu:File", "Alt+F", "window", None, True, "Menu bar: File")
    probs = km.Keymap().check("export", ("Alt+F",), extra=[menu])
    assert _codes(probs) == [("error", "ambiguous", "menu:File")]
    assert "Menu bar: File" in km.describe_problem(probs[0], titles={"menu:File": "Menu bar: File"})


# --------------------------------------------------------------------------- #
# 上書き・型・保存の形
# --------------------------------------------------------------------------- #
def test_only_the_overrides_are_kept_and_removing_keys_is_explicit():
    k = km.Keymap()
    assert k.to_data()["bindings"] == {}
    assert k.assign("export", ("Ctrl+Shift+F12",)) == []
    assert k.to_data() == {"format": km.FORMAT, "version": 1, "preset": "visual_studio",
                           "bindings": {"export": ["Ctrl+Shift+F12"]}}
    assert k.assign("export", ("Ctrl+E",)) == [] and k.to_data()["bindings"] == {}      # 既定と同じ = 上書きでない
    k.assign("export", ())
    assert k.keys("export") == () and k.to_data()["bindings"] == {"export": []}
    assert k.reset("export") and k.keys("export") == ("Ctrl+E",)
    k.assign("fit", ("Ctrl+Shift+F12",))
    k.assign("quit", ())
    assert k.reset_all() == 2 and k.overrides() == {}


def test_switching_the_preset_keeps_your_changes_but_drops_the_conflicting_ones():
    k = km.Keymap()
    assert [p.code for p in k.assign("export", ("F10",))] == ["warn_menu_key"]
    k.assign("fit", ("Ctrl+Shift+F12",))
    dropped = k.switch_preset("vscode")
    assert dropped == [("export", ("F10",))]                                  # VS Code 風では F10 = 1 段進む
    assert k.preset == "vscode" and k.overrides() == {"fit": ("Ctrl+Shift+F12",)}
    assert k.keys("dbg_step") == ("F10",) and k.keys("export") == ("Ctrl+E",)
    assert k.switch_preset("visual_studio") == [] and k.keys("fit") == ("Ctrl+Shift+F12",)
    with pytest.raises(ValueError):
        k.switch_preset("emacs")


def test_broken_settings_give_the_default_map_and_say_why():
    for text in ("{broken", "[1, 2]", json.dumps({"format": "other"}), json.dumps({"format": km.FORMAT, "version": 0})):
        k, probs = km.from_settings_text(text)
        assert k == km.Keymap() and probs and probs[0].code == "settings_broken", text
    k, probs = km.from_settings_text(json.dumps({"format": km.FORMAT, "version": 9}))
    assert k == km.Keymap() and [p.code for p in probs] == ["settings_newer"]          # 新しい版: 読まずに残す
    assert km.from_settings_text(None) == (km.Keymap(), [])
    assert km.from_settings_text(12)[1][0].code == "settings_broken"


def test_partly_broken_settings_keep_the_good_part():
    data = {"format": km.FORMAT, "version": 1, "preset": "visual_studio", "bindings": {
        "fit": ["Ctrl+Shift+F12"], "no_such": ["Ctrl+F12"], "quit": ["Ctrl+Hyper+Q"], "fixed_complete": ["Ctrl+F11"],
        "zoom_in": "Ctrl+F10", "export": ["Ctrl+O"], "zoom_out": ["Ctrl+Alt+Z"]}}
    k, probs = km.from_settings_text(json.dumps(data))
    assert k.overrides() == {"fit": ("Ctrl+Shift+F12",), "zoom_out": ("Ctrl+Alt+Z",)}
    codes = {(p.code, p.command) for p in probs}
    assert {("unknown_command", "no_such"), ("bad_key", "quit"), ("fixed_command", "fixed_complete"),
            ("bad_type", "zoom_in"), ("ambiguous", "export"), ("warn_altgr", "zoom_out")} <= codes


def test_export_and_import_round_trip():
    k = km.Keymap("vscode")
    k.assign("fit", ("Ctrl+Shift+F12",))
    k.assign("quit", ())
    k.assign("keyboard_settings", ("Ctrl+K, Ctrl+K",))
    text = k.to_json()
    assert text.endswith("\n") and "\r" not in text
    got, probs = km.import_text(text)
    assert got == k and probs == []
    got2, _ = km.import_text(text.encode("utf-8"))
    assert got2 == k


def _doc(**over):
    d = {"format": km.FORMAT, "version": 1, "preset": "visual_studio", "bindings": {"fit": ["Ctrl+Shift+F12"]}}
    d.update(over)
    return json.dumps(d)


_REFUSED = [
    ("not json", "bad_json"),
    (b"\xff\xfe\x00", "bad_json"),
    ("[]", "bad_type"),
    (_doc(format="vscode-keybindings"), "bad_format"),
    (_doc(version=2), "bad_version"),
    (_doc(version=True), "bad_version"),
    (_doc(preset="emacs"), "unknown_preset"),
    (_doc(extra_field=1), "bad_type"),
    (_doc(bindings=[]), "bad_type"),
    (_doc(bindings={"no_such": ["Ctrl+F12"]}), "unknown_command"),
    (_doc(bindings={"fit": "Ctrl+F12"}), "bad_type"),
    (_doc(bindings={"fit": [12]}), "bad_type"),
    (_doc(bindings={"fit": ["Ctrl+Hyper+F"]}), "bad_key"),
    (_doc(bindings={"fit": ["Ctrl+O"]}), "ambiguous"),
    (_doc(bindings={"fit": ["Alt+Tab"]}), "os_taken"),
    (_doc(bindings={"fixed_complete": ["Ctrl+F12"]}), "fixed_command"),
    ("x" * (km.MAX_IMPORT_BYTES + 1), "too_big"),
    (_doc(bindings={"c%d" % i: [] for i in range(200)}), "too_big"),
]


@pytest.mark.parametrize("case", range(len(_REFUSED)), ids=[c for _d, c in _REFUSED])
def test_import_is_fail_closed(case):
    data, code = _REFUSED[case]
    got, probs = km.import_text(data)
    assert got is None
    assert code in [p.code for p in probs], probs


def test_import_with_only_warnings_is_applied_and_the_warnings_are_returned():
    got, probs = km.import_text(_doc(bindings={"fit": ["Ctrl+Alt+F"]}))
    assert got is not None and got.keys("fit") == ("Ctrl+Alt+F",)
    assert [p.code for p in probs] == ["warn_altgr"]


# --------------------------------------------------------------------------- #
# 文の中のキー
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text, pairs, lang, want", [
    ("Run all (F5 / Ctrl+R)", [(("F5", "Ctrl+R"), ("F8",))], "en", "Run all (F8)"),
    ("Run all (F5 / Ctrl+R)", [(("F5", "Ctrl+R"), ())], "en", "Run all"),
    ("Show the result. Also F5 or Ctrl+R from any panel", [(("F5", "Ctrl+R"), ("F8", "Ctrl+Shift+R"))], "en",
     "Show the result. Also F8 or Ctrl+Shift+R from any panel"),
    ("F5 continue, F6 step", [(("F5",), ("F6",)), (("F6",), ("F5",))], "en", "F6 continue, F5 step"),
    ("Gewählte Stufe nach vorn (Strg+Auf)", [(("Ctrl+Up",), ("Ctrl+Alt+Up",))], "de",
     "Gewählte Stufe nach vorn (Strg+Alt+Auf)"),
    ("Endergebnis anzeigen (Strg+Eingabe)", [(("Ctrl+Return",), ("Ctrl+Shift+Return",))], "de",
     "Endergebnis anzeigen (Strg+Umschalt+Eingabe)"),
    ("Help (Shift+F1); the list stays on F1", [(("F1",), ("F2",))], "en", "Help (Shift+F1); the list stays on F2"),
    ("Settings (Ctrl+K, Ctrl+S)", [(("Ctrl+K, Ctrl+S",), ("Ctrl+K, Ctrl+K",))], "en", "Settings (Ctrl+K, Ctrl+K)"),
    ("No key here", [(("F5",), ("F8",))], "en", "No key here"),
])
def test_retarget_text(text, pairs, lang, want):
    assert km.retarget_text(text, pairs, lang) == want


def test_text_pairs_follow_the_mentions():
    k = km.Keymap()
    k.assign("dbg_run", ("F8",))
    assert km.text_pairs(k, "run_all") == [(("Ctrl+Return",), ("Ctrl+Return",)), (("F5", "Ctrl+R"), ("F8",))]


# --------------------------------------------------------------------------- #
# 一覧と検索
# --------------------------------------------------------------------------- #
def test_rows_and_search():
    k = km.Keymap()
    rows = km.shortcut_rows(k)
    bound = [c for c in km.COMMANDS if c.keys]
    assert len(rows) == len(bound) == 103
    assert len(km.shortcut_rows(k, include_unbound=True)) == len(km.COMMANDS)
    assert [r[0] for r in km.search(rows, "ctrl+d")] == ["duplicate_stage", "editops_line_duplicate"]
    assert [r[0] for r in km.search(rows, "Ctrl+K")] == ["keyboard_settings"]               # 和音の 1 打目でも引ける
    assert {"duplicate_stage", "editops_line_duplicate"} <= {r[0] for r in km.search(rows, "duplicate")}
    assert {r[0] for r in km.search(rows, "stage list")} >= {"remove", "duplicate_stage", "step"}
    assert km.search(rows, "") == rows
    k.assign("fit", ("Ctrl+Shift+F12",))
    row = [r for r in km.shortcut_rows(k) if r[0] == "fit"][0]
    assert row[2] == "Ctrl+Shift+F12" and row[4] is True


# --------------------------------------------------------------------------- #
# 対訳
# --------------------------------------------------------------------------- #
def test_every_own_string_has_five_translations_and_nothing_else():
    table = km.load_table()
    assert km.missing() == []
    assert sorted(table) == sorted(km.ui_strings())
    assert len(table) == 122
    ph = re.compile(r"%\(\w+\)s|%[sd]")
    for en, row in table.items():
        for lang in km.LANGS[1:]:
            assert sorted(ph.findall(row[lang])) == sorted(ph.findall(en)), (en, lang)
            assert row[lang] != en or en in ("1:1 (Image Viewer)",), (en, lang)
    assert km.missing({})[:1] == [(km.ui_strings()[0], "ja")]


def test_every_command_title_has_a_japanese_text_through_the_tables():
    import studio                                                          # noqa: PLC0415  (Qt は使わない)
    tr = km.make_tr("ja", first=lambda s: studio.STRINGS_I18N.get(s, {}).get("ja", s))
    left = [c.id for c in km.COMMANDS if tr(c.title) == c.title]
    assert left == []
    assert tr(km.SCOPES["pipeline_list"].title) == "段の一覧"


@pytest.mark.parametrize("lang", km.LANGS)
def test_every_message_can_be_written_in_every_language(lang):
    tr = km.make_tr(lang)
    for code in km.MESSAGES:
        p = km.Problem("error", code, "export", "Ctrl+E", "open_image", "Ctrl+O", "main", "3")
        text = km.describe_problem(p, tr)
        assert text and "%(" not in text, (lang, code, text)


# --------------------------------------------------------------------------- #
# 文書の表(2 つの型の全部のキー)
# --------------------------------------------------------------------------- #
def _doc_rows():
    path = os.path.join(ROOT, "docs", "STUDIO_KEYBOARD.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    rows = {}
    for line in text.splitlines():
        m = re.match(r"\| `([a-z0-9_]+)` \|(.*)\|\s*$", line)
        if m:
            rows[m.group(1)] = [c.strip() for c in m.group(2).split("|")]
    return text, rows


def _cell_keys(cell):
    return tuple(x.strip().strip("`") for x in cell.split(" / ")) if cell != "—" else ()


def test_the_document_lists_every_key_of_both_presets():
    text, rows = _doc_rows()
    assert len(rows) == len(km.COMMANDS)
    for c in km.COMMANDS:
        cells = rows[c.id]
        if c.fixed:
            assert _cell_keys(cells[-1]) == c.keys, c.id
        else:
            assert _cell_keys(cells[-2]) == km.preset_keys("visual_studio", c.id), c.id
            assert _cell_keys(cells[-1]) == km.preset_keys("vscode", c.id), c.id
    for name in ("keymap/user", "Ctrl+K, Ctrl+S", km.FORMAT, "STUDIO_EDITOR_KEYS.md"):
        assert name in text


# --------------------------------------------------------------------------- #
# 本物の窓(offscreen)
# --------------------------------------------------------------------------- #
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    pytest.importorskip("PySide6")
    from PySide6 import QtCore, QtGui, QtWidgets  # noqa: PLC0415
    from PySide6.QtTest import QTest  # noqa: PLC0415
    return QtCore, QtGui, QtWidgets, QTest


@pytest.fixture(scope="module")
def app():
    _QtCore, _QtGui, QtWidgets, _T = _qt()
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _pump(sec=0.05):
    from PySide6 import QtWidgets  # noqa: PLC0415
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.005)


@pytest.fixture(scope="module")
def studio_mod(app, tmp_path_factory):
    old = os.environ.get("FULLSEYE_STUDIO_SETTINGS")
    os.environ["FULLSEYE_STUDIO_SETTINGS"] = str(tmp_path_factory.mktemp("keymap") / "studio.ini")
    import studio  # noqa: PLC0415
    yield studio
    if old is None:
        os.environ.pop("FULLSEYE_STUDIO_SETTINGS", None)
    else:
        os.environ["FULLSEYE_STUDIO_SETTINGS"] = old


def _build(studio_mod, flash=None):
    """本物の窓を作り、配線の覚え書き(WIRING.txt)どおりに矩形選択とキーの割り当てを取り付ける。"""
    import studio_editops_qt as eq  # noqa: PLC0415
    import studio_keymap_qt as kq  # noqa: PLC0415
    w, _model = studio_mod.build_window()
    w.resize(1400, 860)
    w.show()
    w.activateWindow()
    _pump(0.3)
    # ---- ここからが配線の差分(studio.py の build_window の最後、studio_pymode.install の後) ----
    ops = eq.install(w._program["edit"], settings=studio_mod._settings,
                     tr=eo.make_tr(lambda: studio_mod._UI_LANG.get("code", "en"), first=studio_mod.tr))
    ops.populate_menu(w._menus["edit"])
    w._actions.update(ops.command_actions(w))
    studio_mod.PALETTE_WORDS.update(eo.PALETTE_WORDS)
    ctl = kq.install(w, settings=studio_mod._settings, tr=studio_mod.tr,
                     lang=lambda: studio_mod._UI_LANG.get("code", "en"), flash=flash,
                     palette_words=studio_mod.PALETTE_WORDS)
    # ---- ここまで ----
    w._editops = ops
    return w, ctl


def _close(w):
    w.close_guard = lambda: True
    w.quiesce()
    w.close()
    _pump(0.1)


@pytest.fixture(scope="module")
def win(app, studio_mod):
    import studio_editops_qt as eq  # noqa: PLC0415
    w, _ctl = _build(studio_mod)
    yield w
    for k in list(eo.PALETTE_WORDS) + ["keyboard_settings"]:
        studio_mod.PALETTE_WORDS.pop(k, None)
    studio_mod._UI_LANG["code"] = "en"
    _close(w)
    eq.apply_bindings(None)


@pytest.fixture
def ctl(win, studio_mod):
    c = win._keymap
    yield c
    if c.dialog is not None:
        c.dialog.close()
    if studio_mod._UI_LANG.get("code") != "en":
        win._apply_language("en")
    c.keymap = km.Keymap()
    c._commit()
    _pump(0.05)


def _keys_of(obj):
    import studio_keymap_qt as kq  # noqa: PLC0415
    from PySide6 import QtGui  # noqa: PLC0415
    seqs = obj.keys() if isinstance(obj, QtGui.QShortcut) else obj.shortcuts()
    return tuple(kq._seq_text(s) for s in seqs)


def test_install_finds_every_command_of_the_real_window(win, ctl):
    import studio_editops_qt as eq  # noqa: PLC0415
    import studio_keymap_qt as kq  # noqa: PLC0415
    rep = ctl.apply()
    assert rep["missing"] == [] and rep["applied"] >= 85
    assert len(win._actions) >= 100
    assert [k for k in win._actions if k not in km.BY_ID] == []          # 本体に足した action は登録簿にも載せる
    st = kq._state(win)
    for cid, en in (("image_focus", "Image focus"), ("leave_image_focus", "Leave image focus"),
                    ("code_to_editor", "Pipeline as code → editor"), ("work_mode_build", "Build pipeline")):
        a = win._actions[cid]
        assert a is st.targets[cid][0] and a.text() == en and a.objectName() == "keymap:" + cid
    assert win._actions["system_settings"] is win._act_system_settings
    code_to_editor = win._actions["code_to_editor"]                       # 右クリックのメニューにしか無かった
    assert any(eq._host_window(w) is win for w in code_to_editor.associatedObjects())
    tools = [a.objectName() for a in win._menus["tools"].actions()]
    assert "keymap:keyboard_settings" in tools
    assert tools.index("keymap:keyboard_settings") > tools.index("keymap:system_settings")


def test_the_menu_key_and_the_real_key_are_the_same_for_every_command(win, ctl):
    import studio_keymap_qt as kq  # noqa: PLC0415
    from PySide6 import QtGui  # noqa: PLC0415
    st = kq._state(win)

    def check():
        n = 0
        for c in km.COMMANDS:
            for obj in st.targets.get(c.id, ()):
                if isinstance(obj, QtGui.QAction):
                    assert _keys_of(obj) == ctl.keymap.keys(c.id), c.id
                    n += 1
        return n

    assert check() >= 85
    for cid, keys in (("export", ("Ctrl+Alt+Shift+E",)), ("dbg_run", ("F8", "Ctrl+Shift+F8")), ("quit", ()),
                      ("duplicate_stage", ("Ctrl+Shift+F9",)), ("program_find", ("Ctrl+F7",)),
                      ("image_focus", ("Ctrl+F11",))):
        assert [p for p in ctl.assign(cid, keys) if p.level == "error"] == [], cid
    assert check() >= 85
    assert _keys_of(win._actions["dbg_run"]) == ("F8", "Ctrl+Shift+F8")
    from PySide6 import QtCore  # noqa: PLC0415
    assert win._actions["duplicate_stage"].shortcutContext() == QtCore.Qt.WidgetWithChildrenShortcut
    file_menu = win._menus["file"]
    assert win._actions["export"] in file_menu.actions()                  # メニューの項目そのものの QAction


def _activate(win):
    win.activateWindow()
    win.raise_()
    _pump(0.1)


def test_a_new_window_key_fires_and_the_old_one_does_not(win, ctl):
    _QtCore, _QtGui, QtWidgets, QTest = _qt()
    from PySide6 import QtCore  # noqa: PLC0415
    K = QtCore.Qt
    hits = []
    a = win._actions["zoom_in"]

    def spy(*_a):
        hits.append(1)
    a.triggered.connect(spy)
    try:
        _activate(win)
        win._stage_list.setFocus()
        _pump(0.05)
        assert QtWidgets.QApplication.activeWindow() is win
        QTest.keyClick(win._stage_list, K.Key_Equal, K.ControlModifier)
        assert hits == [1]
        assert ctl.assign("zoom_in", ("Ctrl+F11",)) == []
        QTest.keyClick(win._stage_list, K.Key_Equal, K.ControlModifier)
        assert hits == [1]                                                # 古いキーでは効かない
        QTest.keyClick(win._stage_list, K.Key_F11, K.ControlModifier)
        assert hits == [1, 1]                                             # 新しいキーで効く
    finally:
        a.triggered.disconnect(spy)                                       # 本体の配線(ズーム)は残す


def _program(win, text):
    ed = win._program["edit"]
    win._docks["program"].show()
    win.activateWindow()
    ed.setPlainText(text)
    ed.setFocus()
    _pump(0.2)
    return ed


def test_the_program_editor_follows_a_changed_key(win, ctl):
    _QtCore, _QtGui, _QtWidgets, QTest = _qt()
    from PySide6 import QtCore  # noqa: PLC0415
    K = QtCore.Qt
    bar = win._program["find"]["bar"]
    hits = []

    def spy(*_a):
        hits.append(1)
    win._actions["focus_search"].triggered.connect(spy)
    try:
        _activate(win)
        ed = _program(win, "blur (0.5, 0.5)\notsu (0.5, 0.5)")
        QTest.keyClick(ed, K.Key_F, K.ControlModifier)
        assert bar.isVisible() and hits == []                             # 既定: 欄の検索が窓の Ctrl+F より先
        bar.close_bar()
        assert ctl.assign("program_find", ("Ctrl+F7",)) == []
        ed.setFocus()
        _pump(0.05)
        QTest.keyClick(ed, K.Key_F7, K.ControlModifier)
        assert bar.isVisible()                                            # 新しいキーで欄の検索
        bar.close_bar()
        ed.setFocus()
        _pump(0.05)
        QTest.keyClick(ed, K.Key_F, K.ControlModifier)
        assert not bar.isVisible() and hits == [1]                        # 古いキーは欄に通さず、窓の Ctrl+F が撃たれる
        assert _keys_of(win._actions["program_find"]) == ("Ctrl+F7",)     # メニューの表示も新しいキー
    finally:
        win._actions["focus_search"].triggered.disconnect(spy)
        bar.close_bar()


def test_box_selection_editor_keys_follow_the_registry(win, ctl):
    _QtCore, _QtGui, _QtWidgets, QTest = _qt()
    from PySide6 import QtCore  # noqa: PLC0415
    import studio_editops_qt as eq  # noqa: PLC0415
    from PySide6 import QtWidgets  # noqa: PLC0415
    K = QtCore.Qt
    ops = win._editops
    _activate(win)
    ed = _program(win, "a\nb")
    QTest.keyClick(ed, K.Key_D, K.ControlModifier)
    assert ed.toPlainText() == "a\na\nb"                                  # 既定: Ctrl+D = 行の複製
    ed.undo()
    assert ctl.assign("editops_line_duplicate", ("Ctrl+F9",)) == []
    assert ops.keys_for("line.duplicate") == ("Ctrl+F9",)
    ed.setFocus()
    cur = ed.textCursor()
    cur.setPosition(0)
    ed.setTextCursor(cur)
    QTest.keyClick(ed, K.Key_D, K.ControlModifier)
    assert "a\na" not in ed.toPlainText()                                # 古いキーでは複製しない(X11 の Ctrl+D は 1 字消す)
    ed.setPlainText("a\nb")
    ed.setFocus()
    QTest.keyClick(ed, K.Key_F9, K.ControlModifier)
    assert ed.toPlainText() == "a\na\nb"                                  # 新しいキーで複製
    ed.undo()
    labels = [a.text() for m in ops.build_context_menu().findChildren(QtWidgets.QMenu) for a in m.actions()
              if a.objectName() == "editops:line.duplicate"]
    assert labels and all(t.endswith("\tCtrl+F9") for t in labels)
    assert "Ctrl+F9" in ops.howto_text()
    assert eq.check_conflicts(win, ed)["studio"] == []


def test_the_vscode_preset_in_the_editor(win, ctl):
    _QtCore, _QtGui, _QtWidgets, QTest = _qt()
    from PySide6 import QtCore  # noqa: PLC0415
    K = QtCore.Qt
    assert ctl.switch_preset("vscode") == []
    _activate(win)
    ed = _program(win, "abc = abc + 1")
    cur = ed.textCursor()
    cur.setPosition(1)
    ed.setTextCursor(cur)
    QTest.keyClick(ed, K.Key_D, K.ControlModifier)                        # VS Code 風: Ctrl+D = 語を選ぶ → 次の一致
    assert ed.textCursor().selectedText() == "abc" and ed.toPlainText() == "abc = abc + 1"
    QTest.keyClick(ed, K.Key_D, K.ControlModifier)
    assert win._editops.selected_texts() == ["abc", "abc"]
    QTest.keyClick(ed, K.Key_Escape)
    QTest.keyClick(ed, K.Key_Down, K.ShiftModifier | K.AltModifier)       # 行の複製 = Shift+Alt+Down
    assert ed.toPlainText() == "abc = abc + 1\nabc = abc + 1"
    assert _keys_of(win._actions["palette"]) == ("Ctrl+Shift+P", "F1")


def test_a_change_is_saved_and_used_by_the_next_start(win, ctl, studio_mod):
    assert ctl.assign("fit", ("Ctrl+Shift+F12",)) == []
    s = studio_mod._settings()
    saved = json.loads(s.value(km.SETTINGS_KEY))
    assert saved["bindings"] == {"fit": ["Ctrl+Shift+F12"]}
    with open(os.environ["FULLSEYE_STUDIO_SETTINGS"], encoding="utf-8") as fh:
        assert "keymap" in fh.read()
    w2, ctl2 = _build(studio_mod)
    try:
        assert ctl2.keymap.keys("fit") == ("Ctrl+Shift+F12",) and ctl2.load_problems == []
        assert _keys_of(w2._actions["fit"]) == ("Ctrl+Shift+F12",)
    finally:
        _close(w2)
    ctl.apply()


def test_broken_settings_do_not_stop_the_start(win, ctl, studio_mod):
    s = studio_mod._settings()
    s.setValue(km.SETTINGS_KEY, "{this is not json")
    s.sync()
    said = []
    w3, ctl3 = _build(studio_mod, flash=said.append)
    try:
        assert ctl3.keymap == km.Keymap()
        assert [p.code for p in ctl3.load_problems] == ["settings_broken"]
        assert said == [km.MSG_LOAD_BROKEN]
        assert _keys_of(w3._actions["fit"]) == ("Ctrl+0",)
        assert studio_mod._settings().value(km.SETTINGS_KEY) == "{this is not json"   # 起動では書き直さない
        data = {"format": km.FORMAT, "version": 1, "preset": "visual_studio",
                "bindings": {"fit": ["Ctrl+Shift+F12"], "no_such": ["Ctrl+F12"], "export": ["Ctrl+O"]}}
        s = studio_mod._settings()
        s.setValue(km.SETTINGS_KEY, json.dumps(data))
        s.sync()
        probs = ctl3.load()
        ctl3.apply()
        assert ctl3.keymap.overrides() == {"fit": ("Ctrl+Shift+F12",)}
        assert {p.code for p in probs} == {"unknown_command", "ambiguous"}
        assert _keys_of(w3._actions["fit"]) == ("Ctrl+Shift+F12",)
        assert _keys_of(w3._actions["export"]) == ("Ctrl+E",)
    finally:
        _close(w3)
    ctl.apply()


def test_switching_the_language_keeps_the_keys_and_rewrites_the_texts(win, ctl, studio_mod):
    ja_default = studio_mod.STRINGS_I18N["Run all (F5 / Ctrl+R)"]["ja"]
    assert "F5" in ja_default                                              # 訳にも既定のキーが書いてある
    assert ctl.assign("dbg_run", ("F8",)) == []
    a = win._actions["dbg_run"]
    assert a.text() == "Run all (F8)"
    win._lang_actions["ja"].trigger()
    _pump(0.05)
    assert _keys_of(a) == ("F8",) and "F8" in a.text() and "F5" not in a.text()
    assert a.text() == km.retarget_text(ja_default, [(("F5", "Ctrl+R"), ("F8",))], "ja")
    assert win._actions["keyboard_settings"].text() == km.load_table()[km.ACT_SETTINGS]["ja"]
    assert "F8" in win._actions["run_all"].toolTip() and "Ctrl+R" not in win._actions["run_all"].toolTip()
    win._lang_actions["en"].trigger()
    _pump(0.05)
    assert a.text() == "Run all (F8)"
    ctl.reset("dbg_run")
    assert a.text() == "Run all (F5 / Ctrl+R)" and _keys_of(a) == ("F5", "Ctrl+R")


def test_the_f1_table_and_the_palette_show_the_changed_key(win, ctl, studio_mod):
    assert ctl.assign("quit", ("Ctrl+Shift+F4",)) == []
    rows = studio_mod.shortcut_table([(a.text(), a.shortcut().toString()) for a in win._actions.values()])
    assert ("Quit", "Ctrl+Shift+F4") in rows
    assert ("Image focus", "F11") in rows and ("Leave image focus", "Esc") in rows   # ID の無かった物も載る
    # パレットの行の文は show_palette と同じ式で作る(窓は exec で止まるので開かない)
    labels = ["▸ " + a.text().replace("…", "").strip() for a in win._actions.values() if a.isEnabled()]
    assert "▸ Customize keyboard shortcuts" in labels
    assert ctl.assign("dbg_run", ("F8",)) == []
    labels = ["▸ " + a.text().replace("…", "").strip() for a in win._actions.values() if a.isEnabled()]
    assert "▸ Run all (F8)" in labels
    full = {r[0]: r for r in ctl.rows()}
    assert full["quit"][2] == "Ctrl+Shift+F4" and full["quit"][4] is True
    assert full["fixed_mdi_close"][2] == "Ctrl+F4 / Ctrl+W" and full["fixed_mdi_close"][5] is True
    assert full["menu:File"][2] == "Alt+F"
    assert "keyboard_settings" in studio_mod.PALETTE_WORDS


def test_window_mnemonics_take_part_in_the_check(win, ctl):
    probs = ctl.check("export", ("Alt+F",))
    assert [(p.level, p.code, p.other) for p in probs] == [("error", "ambiguous", "menu:File")]
    assert "Menu bar: File" in ctl.describe(probs[0])


# ---- 設定の窓 ------------------------------------------------------------- #
def _press(w, key, mods=None):
    _QtCore, _QtGui, _QtWidgets, QTest = _qt()
    from PySide6 import QtCore  # noqa: PLC0415
    QTest.keyClick(w, key, mods if mods is not None else QtCore.Qt.NoModifier)
    _pump(0.02)


def test_dialog_search_record_conflict_and_assign(win, ctl):
    from PySide6 import QtCore  # noqa: PLC0415
    K = QtCore.Qt
    dlg = ctl.open_dialog()
    _pump(0.2)
    assert not dlg.isModal() and dlg.isVisible()
    assert dlg.table.rowCount() == len(km.COMMANDS) + 7                     # + メニューバーのニーモニック 7 つ
    dlg.search.setText("ctrl+d")
    assert dlg.visible_ids() == ["duplicate_stage", "editops_line_duplicate"]
    dlg.search.setText("")
    assert len(dlg.visible_ids()) == dlg.table.rowCount()
    assert dlg.select("zoom_in")
    from PySide6 import QtGui  # noqa: PLC0415
    probe = QtGui.QKeyEvent(QtCore.QEvent.ShortcutOverride, K.Key_O, K.ControlModifier)
    QtCore.QCoreApplication.sendEvent(dlg.recorder, probe)
    assert probe.isAccepted()                                             # 記録の間は窓のキーを撃たせない
    _press(dlg.recorder, K.Key_O, K.ControlModifier)
    assert dlg.recorder.text() == "Ctrl+O"
    assert "Open image" in dlg.status.text() and "Main window" in dlg.status.text()
    assert not dlg.b_assign.isEnabled() and not dlg.b_add.isEnabled()     # 当たり: 割り当てられない
    assert ctl.keymap.keys("open_image") == ("Ctrl+O",)                   # 相手は勝手に外さない
    dlg.b_clear.click()
    _press(dlg.recorder, K.Key_F11, K.ControlModifier)
    assert dlg.recorder.text() == "Ctrl+F11" and dlg.b_assign.isEnabled()
    dlg.b_assign.click()
    _pump(0.05)
    assert ctl.keymap.keys("zoom_in") == ("Ctrl+F11",) and _keys_of(win._actions["zoom_in"]) == ("Ctrl+F11",)
    r = dlg.visible_ids().index("zoom_in")
    assert dlg.table.item(r, 1).text() == "Ctrl+F11" and dlg.table.item(r, 3).text() == "●"
    _press(dlg.recorder, K.Key_Equal, K.ControlModifier)
    dlg.b_add.click()
    assert ctl.keymap.keys("zoom_in") == ("Ctrl+F11", "Ctrl+=")
    dlg.b_reset.click()
    assert ctl.keymap.keys("zoom_in") == ("Ctrl+=",) and not ctl.keymap.is_changed("zoom_in")
    dlg.b_remove.click()
    assert ctl.keymap.keys("zoom_in") == () and _keys_of(win._actions["zoom_in"]) == ()
    h = dlg.table.verticalHeader().defaultSectionSize()
    assert h == dlg.table.fontMetrics().height() + 4


def test_dialog_in_japanese_and_fixed_rows(win, ctl):
    dlg = ctl.open_dialog()
    win._lang_actions["ja"].trigger()
    _pump(0.1)
    table = km.load_table()
    assert dlg.windowTitle() == table[km.DLG_TITLE]["ja"]
    assert dlg.table.horizontalHeaderItem(1).text() == "キー"
    dlg.search.setText("複製")
    assert {"duplicate_stage", "editops_line_duplicate"} <= set(dlg.visible_ids())
    dlg.search.setText("")
    assert dlg.select("fixed_mdi_close")
    assert not dlg.recorder.isEnabled() and not dlg.b_assign.isEnabled()
    assert dlg.hint.text() == table[km.MSG_FIXED]["ja"]
    assert dlg.select("program_find")
    assert dlg.selected.text().endswith("Program 欄")
    win._lang_actions["en"].trigger()
    _pump(0.05)
    assert dlg.windowTitle() == km.DLG_TITLE


def test_dialog_reset_all_and_preset_need_a_confirmation(win, ctl):
    dlg = ctl.open_dialog()
    ctl.assign("export", ("F10",))
    ctl.assign("fit", ("Ctrl+Shift+F12",))
    asked = []
    dlg.confirm = lambda title, text: asked.append((title, text)) or False
    assert dlg.do_reset_all() is False and len(ctl.keymap.overrides()) == 2   # 断った: 何も変えない
    assert "2" in asked[-1][1]
    assert dlg.switch_preset("vscode") is False and ctl.keymap.preset == "visual_studio"
    assert "F10" in asked[-1][1]                                         # 外れる上書きを先に知らせる
    dlg.confirm = lambda title, text: True
    assert dlg.switch_preset("vscode") is True
    assert ctl.keymap.preset == "vscode" and ctl.keymap.overrides() == {"fit": ("Ctrl+Shift+F12",)}
    assert dlg.preset.currentData() == "vscode"
    assert dlg.do_reset_all() is True and ctl.keymap.overrides() == {}
    assert ctl.keymap.preset == "vscode"


def test_dialog_export_import_and_a_refused_import(win, ctl, tmp_path):
    dlg = ctl.open_dialog()
    ctl.assign("fit", ("Ctrl+Shift+F12",))
    ctl.assign("keyboard_settings", ("Ctrl+K, Ctrl+K",))
    path = str(tmp_path / "keys.json")
    dlg.ask_save = lambda: path
    assert dlg.do_export() is True
    with open(path, "rb") as fh:
        raw = fh.read()
    assert b"\r" not in raw and json.loads(raw)["bindings"]["fit"] == ["Ctrl+Shift+F12"]
    ctl.reset_all()
    dlg.ask_open = lambda: path
    assert dlg.do_import() is True
    assert ctl.keymap.overrides() == {"fit": ("Ctrl+Shift+F12",), "keyboard_settings": ("Ctrl+K, Ctrl+K",)}
    assert _keys_of(win._actions["fit"]) == ("Ctrl+Shift+F12",)
    bad = str(tmp_path / "bad.json")
    with open(bad, "w", encoding="utf-8") as fh:
        json.dump({"format": km.FORMAT, "version": 1, "bindings": {"fit": ["Ctrl+Alt+F"], "no_such": ["F12"]}}, fh)
    said = []
    dlg.inform = lambda title, text: said.append(text)
    dlg.ask_open = lambda: bad
    assert dlg.do_import() is False
    assert said and "no_such" in said[0]
    assert ctl.keymap.overrides()["fit"] == ("Ctrl+Shift+F12",)          # 断った時は何も当てない


def test_the_recorder_ignores_the_ime_and_records_two_strokes(win, ctl):
    from PySide6 import QtCore, QtGui  # noqa: PLC0415
    K = QtCore.Qt
    dlg = ctl.open_dialog()
    assert dlg.select("keyboard_settings")
    rec = dlg.recorder
    assert rec.allow_chords and not rec.testAttribute(K.WA_InputMethodEnabled)
    rec.setFocus()
    ev = QtGui.QInputMethodEvent()
    ev.setCommitString("あ")
    QtCore.QCoreApplication.sendEvent(rec, ev)
    assert rec.text() == ""
    _press(rec, K.Key_K, K.ControlModifier)
    _press(rec, K.Key_S, K.ControlModifier)
    assert rec.sequence() == "Ctrl+K, Ctrl+S"
    _press(rec, K.Key_E, K.ControlModifier)
    assert rec.sequence() == "Ctrl+E"                                     # 3 打目で始めから
    from PySide6 import QtWidgets  # noqa: PLC0415
    before = QtWidgets.QApplication.focusWidget()
    _press(rec, K.Key_Tab)
    assert rec.sequence() == "Ctrl+E, Tab"                                # Tab も記録する
    assert QtWidgets.QApplication.focusWidget() is before                 # フォーカスは動かない
    assert dlg.select("editops_line_duplicate")
    assert not rec.allow_chords
    _press(rec, K.Key_K, K.ControlModifier)
    _press(rec, K.Key_G, K.ControlModifier)
    assert rec.sequence() == "Ctrl+G"                                     # エディタは 1 打ずつ
    _press(rec, K.Key_Greater, K.ShiftModifier | K.AltModifier)
    assert rec.sequence() == "Shift+Alt+."                                # Shift で変わる記号は元のキーで


def test_separate_window_shortcuts_follow_the_keymap(win, ctl):
    from PySide6 import QtGui  # noqa: PLC0415
    import studio_editops_qt as eq  # noqa: PLC0415
    assert ctl.assign("image_viewer_fit", ("G",)) == []
    win._show_image_viewer(None)
    _pump(0.2)
    dlg = win._viewer_dlg
    try:
        found = {s.objectName(): _keys_of(s) for s in dlg.findChildren(QtGui.QShortcut)}
        assert found == {"keymap:image_viewer_fit": ("G",), "keymap:image_viewer_actual_size": ("1",),
                         "keymap:image_viewer_next": ("Right",), "keymap:image_viewer_previous": ("Left",)}
        assert ctl.assign("image_viewer_fit", ("H",)) == []
        fit = [s for s in dlg.findChildren(QtGui.QShortcut) if s.objectName() == "keymap:image_viewer_fit"][0]
        assert _keys_of(fit) == ("H",)
        existing = eq.collect_shortcuts(win, win._program["edit"])
        viewer = [r for r in existing if r[1] == "QShortcut@QDialog"]
        assert len(viewer) == 4 and not any(cov for _k, _o, cov in viewer)   # 別窓のキーは本体の欄に効かない
    finally:
        dlg.close()
    win._act_pyedit.trigger()
    _pump(0.3)
    pdlg = win._pyedit_dlg
    try:
        names = {s.objectName(): _keys_of(s) for s in pdlg.findChildren(QtGui.QShortcut)}
        assert names == {"keymap:python_editor_run": ("F5",), "keymap:python_editor_save": ("Ctrl+S",),
                         "keymap:python_editor_ledger_op": ("Ctrl+Shift+L",)}
        assert ctl.assign("python_editor_run", ("Ctrl+F5",)) == []         # 別窓なので本体の Ctrl+F5 と当たらない
        run = [s for s in pdlg.findChildren(QtGui.QShortcut) if s.objectName() == "keymap:python_editor_run"][0]
        assert _keys_of(run) == ("Ctrl+F5",)
    finally:
        pdlg.close()


# --------------------------------------------------------------------------- #
# 2026-11-13 独立レビュー 1 回目の直し(C1: 設定の読み込みを壊れにくく)
# --------------------------------------------------------------------------- #
_DEEP = "[" * 50000 + "]" * 50000


@pytest.mark.parametrize("text", [
    json.dumps({"format": km.FORMAT, "version": 1, "preset": [], "bindings": {}}),
    json.dumps({"format": km.FORMAT, "version": 1, "preset": {}, "bindings": {}}),
    json.dumps({"format": km.FORMAT, "version": 1, "preset": 3, "bindings": {"fit": ["Ctrl+Shift+F12"]}}),
    json.dumps({"format": km.FORMAT, "version": [1], "bindings": {}}),
    json.dumps({"format": [km.FORMAT], "version": 1}),
    _DEEP,
    '{"format": "%s", "version": 1, "bindings": {"fit": %s}}' % (km.FORMAT, _DEEP),
], ids=["preset_list", "preset_dict", "preset_int", "version_list", "format_list", "deep", "deep_inside"])
def test_settings_of_a_wrong_shape_never_raise_and_give_a_map(text):
    k, probs = km.from_settings_text(text)
    assert isinstance(k, km.Keymap) and probs
    assert all(p.level in ("error", "warning") for p in probs)
    assert probs[0].code in ("settings_broken", "unknown_preset"), probs


@pytest.mark.parametrize("data, code", [
    (json.dumps({"format": km.FORMAT, "version": 1, "preset": [], "bindings": {}}), "unknown_preset"),
    (json.dumps({"format": km.FORMAT, "version": 1, "preset": {}, "bindings": {}}), "unknown_preset"),
    ("[" * 100000 + "]" * 100000, "bad_json"),
    ("[" * 120000, "bad_json"),
    ('{"format": "%s", "version": 1, "bindings": {"fit": ["Ctrl+F12"], "fit": ["Ctrl+F11"]}}' % km.FORMAT,
     "bad_type"),
    ('{"format": "%s", "format": "%s", "version": 1}' % (km.FORMAT, km.FORMAT), "bad_type"),
], ids=["preset_list", "preset_dict", "deep_200kb", "open_120kb", "same_id_twice", "same_field_twice"])
def test_import_refuses_wrong_shapes_without_raising(data, code):
    assert len(data.encode("utf-8")) <= km.MAX_IMPORT_BYTES
    got, probs = km.import_text(data)
    assert got is None
    assert code in [p.code for p in probs], probs


def test_a_dropped_override_always_says_why_and_a_round_trip_never_loses_silently():
    # 部品(エディタ)の側のキーを変えて、Qt の表の側(Python エディタの Run = F5)を届かなくする
    k = km.Keymap()
    k._set("editops_line_duplicate", ("F5",))                    # 検査を通さずに作った表(古い版が保存した物など)
    got, probs = km.import_text(k.to_json())
    assert got is None                                           # 「成功」と言って上書きを落とさない
    assert "editops_line_duplicate" in [p.command for p in probs if p.level == "error"], probs
    k2, probs2 = km.from_settings_text(k.to_json())
    assert k2.overrides() == {}
    assert [p.command for p in probs2 if p.level == "error"] == ["editops_line_duplicate"], probs2


def test_dropped_counts_only_the_overrides_that_were_not_used():
    data = {"format": km.FORMAT, "version": 1, "preset": "visual_studio", "bindings": {
        "fit": ["Ctrl+Shift+F12"], "no_such": ["Ctrl+F12"], "export": ["Ctrl+O"], "zoom_out": ["Ctrl+Alt+Z"]}}
    _k, probs = km.from_settings_text(json.dumps(data))
    assert km.dropped_commands(probs) == ["export", "no_such"]   # 警告だけの zoom_out は当てている = 数えない
    assert km.dropped_commands([km.Problem("warning", "settings_newer", detail="2")]) == []


def test_messages_from_a_file_cannot_fake_lines_or_turn_the_text_around():
    fake = "x\n\n\u202e\nImported 5 changed shortcuts. All good." + "y" * 80
    p = km.Problem("error", "unknown_command", fake, "Ctrl+\u202eQ", detail="\x1b[2J")
    text = km.describe_problem(p)
    assert "\n" not in text and "\u202e" not in text and "\x1b" not in text
    assert "\\u000a" in text and "\\u202e" in text
    assert len(text) < 120
    got, probs = km.import_text(json.dumps({"format": km.FORMAT, "version": 1, "bindings": {fake: ["F12"]}}))
    assert got is None and probs
    lines = [km.describe_problem(q) for q in probs]
    assert lines and not any("\n" in s or "\u202e" in s for s in lines)


def _set_saved(studio_mod, value):
    s = studio_mod._settings()
    if value is None:
        s.remove(km.SETTINGS_KEY)
    else:
        s.setValue(km.SETTINGS_KEY, value)
    s.remove(km.SETTINGS_KEY + ".backup")
    s.sync()


@pytest.mark.parametrize("value, message", [
    (json.dumps({"format": km.FORMAT, "version": 1, "preset": [], "bindings": {}}), km.MSG_LOAD_PART),
    ("[" * 50000 + "]" * 50000, km.MSG_LOAD_BROKEN),
], ids=["preset_list", "deep"])
def test_broken_settings_of_any_shape_do_not_stop_the_start(win, ctl, studio_mod, value, message):
    _set_saved(studio_mod, value)
    said = []
    w4, ctl4 = _build(studio_mod, flash=said.append)
    try:
        assert ctl4.keymap == km.Keymap()
        assert said == [message]
        assert _keys_of(w4._actions["fit"]) == ("Ctrl+0",)
        assert studio_mod._settings().value(km.SETTINGS_KEY) == value       # 起動では書き直さない
    finally:
        _close(w4)
        _set_saved(studio_mod, None)
    ctl.apply()


def test_a_newer_setting_is_kept_and_backed_up_before_a_change(win, ctl, studio_mod):
    newer = json.dumps({"format": km.FORMAT, "version": 2, "preset": "vscode", "bindings": {"undo": ["Ctrl+Alt+Z"]},
                        "macros": {"x": 1}})
    _set_saved(studio_mod, newer)
    said = []
    w5, ctl5 = _build(studio_mod, flash=said.append)
    try:
        assert ctl5.keymap == km.Keymap() and len(said) == 1 and "newer" in said[0]
        assert studio_mod._settings().value(km.SETTINGS_KEY) == newer
        assert ctl5.assign("fit", ("Ctrl+Shift+F12",)) == []                 # 利用者が変えた時にだけ書く
        s = studio_mod._settings()
        assert s.value(km.SETTINGS_KEY + ".backup") == newer                # 元の文字列は残す
        assert json.loads(s.value(km.SETTINGS_KEY))["bindings"] == {"fit": ["Ctrl+Shift+F12"]}
    finally:
        _close(w5)
        _set_saved(studio_mod, None)
    ctl.apply()


def test_warnings_only_settings_are_used_quietly_and_not_rewritten(win, ctl, studio_mod):
    saved = json.dumps({"format": km.FORMAT, "version": 1, "preset": "visual_studio", "bindings": {"fit": ["Ctrl+Alt+F"]}})
    _set_saved(studio_mod, saved)
    said = []
    w6, ctl6 = _build(studio_mod, flash=said.append)
    try:
        assert ctl6.keymap.keys("fit") == ("Ctrl+Alt+F",) and said == []
        assert _keys_of(w6._actions["fit"]) == ("Ctrl+Alt+F",)
        assert studio_mod._settings().value(km.SETTINGS_KEY) == saved
    finally:
        _close(w6)
        _set_saved(studio_mod, None)
    ctl.apply()


def test_the_start_message_counts_the_dropped_overrides_and_the_dialog_lists_them(win, ctl, studio_mod):
    data = {"format": km.FORMAT, "version": 1, "preset": "visual_studio",
            "bindings": {"fit": ["Ctrl+Shift+F12"], "no_such": ["Ctrl+F12"], "export": ["Ctrl+O"]}}
    _set_saved(studio_mod, json.dumps(data))
    said = []
    w7, ctl7 = _build(studio_mod, flash=said.append)
    try:
        assert len(said) == 1 and " 2 " in said[0]                          # 捨てた上書きは 2 つ
        dlg = ctl7.open_dialog()
        _pump(0.1)
        note = dlg.load_note
        assert not note.isHidden()
        assert "no_such" in note.text() and "Open image" in note.text()
        ctl7.reset_all()                                                     # 変えたら知らせは消える
        assert note.isHidden()
        dlg.close()
    finally:
        _close(w7)
        _set_saved(studio_mod, None)
    ctl.apply()
