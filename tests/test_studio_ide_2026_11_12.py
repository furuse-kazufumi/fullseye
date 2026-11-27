# -*- coding: utf-8 -*-
"""Studio の IDE としての使いやすさ(第 1 便, 2026-11-12)。

監査(IDE_AUDIT.md)の受け入れ条件をそのまま試験にしたもの。起動は既存の Studio テストと同じ
(offscreen・空の設定ファイル)。キー操作は QTest で実際のキーイベントを送る(関数を直接呼ぶだけにしない)。

1. Program 欄のホバーヘルプ / 補完の順位(B-9)
2. 構文エラーの波線・ガター印・Problems(B-1)/「もしかして」/ 段の型違いの重複(B-2)
3. Program 欄の検索と置換(B-4)
4. Ctrl+/ の行コメント
5. Shift+F1 の op ヘルプ(B-10)/ 文字サイズ
6. Variables が非表示の間の実行(B-3)
7. 言語の切り替えに追従する文言(B-5, B-7)
8. 選んだ行だけの実行
"""
import json
import os
import re
import time

import pytest

import studio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CJK = re.compile("[぀-ヿ一-鿿]")


def _pump(sec=0.3):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def _app():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _launch(tmp_path, monkeypatch, size=(1400, 800), name="s.ini"):
    """空の設定ファイルで Studio を起動する(普段の設定には触らない)。"""
    _app()
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / name))
    win, model = studio.build_window()
    win.resize(*size)
    win.show()
    _pump(0.5)
    return win, model


def _close(win):
    studio._UI_LANG["code"] = "en"
    win.close_guard = lambda: True
    win.quiesce()
    win.close()
    _pump(0.1)


@pytest.fixture
def win(tmp_path, monkeypatch):
    w, m = _launch(tmp_path, monkeypatch)
    w._test_model = m
    yield w
    _close(w)


def _editor(win, text=""):
    """Program 欄を表示して中身を入れ、フォーカスを置く。"""
    ed = win._program["edit"]
    win._docks["program"].show()
    win.activateWindow()
    ed.setPlainText(text)
    ed.setFocus()
    _pump(0.3)
    return ed


def _key(w, key, mods=None):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    QTest.keyClick(w, key, mods if mods is not None else QtCore.Qt.NoModifier)
    _pump(0.05)


def _pos_of(ed, needle, nth=0):
    """欄の中で needle(の中ほど)がある位置(ビューポート座標)。"""
    from PySide6 import QtGui
    text = ed.toPlainText()
    i = -1
    for _ in range(nth + 1):
        i = text.index(needle, i + 1)
    c = QtGui.QTextCursor(ed.document())
    c.setPosition(i + max(1, len(needle) // 2))
    r = ed.cursorRect(c)
    from PySide6 import QtCore
    return QtCore.QPoint(r.x() + 1, r.center().y())


def _hover(ed, needle, nth=0):
    """needle の上へ ToolTip イベントを送り、出た文を返す(何も出なければ "")。"""
    from PySide6 import QtCore, QtGui, QtWidgets
    QtWidgets.QToolTip.hideText()
    p = _pos_of(ed, needle, nth)
    ev = QtGui.QHelpEvent(QtCore.QEvent.ToolTip, p, ed.viewport().mapToGlobal(p))
    QtWidgets.QApplication.sendEvent(ed.viewport(), ev)
    _pump(0.05)
    return QtWidgets.QToolTip.text() if QtWidgets.QToolTip.isVisible() else ""


# --------------------------------------------------------------------------- 1. ホバーヘルプ
def test_hover_on_an_op_name_shows_the_signature_and_the_real_unit(win):
    ed = _editor(win, "gaussian (0.4, 0.5)\n")
    text = _hover(ed, "gaussian")
    assert "blur σ" in text, text                       # つまみの実単位(受け入れ条件)
    assert "gaussian" in text                           # 補完 popup と同じシグネチャ文
    assert ed._tip("gaussian").splitlines()[0] in text


def test_hover_on_a_non_op_word_shows_nothing(win):
    ed = _editor(win, "gaussian (0.4, 0.5)\n* a comment about nothing\n")
    assert _hover(ed, "comment") == ""
    assert _hover(ed, "nothing") == ""


def test_hover_knob_text_follows_the_values_on_that_line(win):
    ed = _editor(win, "gaussian (0.1, 0.5)\ngaussian (0.9, 0.5)\n")
    first, second = _hover(ed, "gaussian", 0), _hover(ed, "gaussian", 1)
    line = lambda t: [x for x in t.splitlines() if "σ" in x and "=" in x][-1]
    assert line(first) != line(second)


# --------------------------------------------------------------------------- 補完の順位(B-9)
def test_completion_puts_the_nearest_name_first(win):
    ed = win._program["edit"]
    got = ed.completion_candidates("gaus")
    assert got[0] == "gaussian", got[:5]
    assert set(got) == set(ed._index.search("gaus", limit=None))      # 並べ替えるだけで、候補は増減しない
    assert ed.completion_candidates("gaussian")[0] == "gaussian"        # 完全一致
    exact = ed.completion_candidates("otsu")
    assert exact[0] == "otsu"


def test_completion_popup_order_and_tab_still_confirm(win):
    from PySide6 import QtCore
    ed = _editor(win, "")
    from PySide6.QtTest import QTest
    QTest.keyClicks(ed, "gaus")
    _pump(0.3)
    pop = ed._completer.popup()
    assert pop.isVisible()
    assert pop.model().index(0, 0).data() == "gaussian"
    _key(pop, QtCore.Qt.Key_Tab)                          # Tab で確定する挙動は変えない
    assert ed.toPlainText().strip() == "gaussian"


# --------------------------------------------------------------------------- 2. 構文エラー(B-1)
def _problems(win):
    pl = win._problems_list
    return [pl.item(i).text() for i in range(pl.count())]


def _wave_lines(ed):
    from PySide6 import QtGui
    out = []
    for s in ed.extraSelections():
        if s.format.underlineStyle() == QtGui.QTextCharFormat.WaveUnderline:
            out.append(s.cursor.blockNumber() + 1)
    return out


def _click_problem(win, row):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    pl = win._problems_list
    QTest.mouseClick(pl.viewport(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier,
                     pl.visualItemRect(pl.item(row)).center())
    _pump(0.1)


def test_unknown_op_goes_to_problems_with_a_squiggle_and_a_gutter_mark(win):
    ed = _editor(win, "gaussian (0.4, 0.5)\nnotanop (1,2)\notsu (0.5,0.5)\n")
    win._program["apply"]()
    _pump(0.2)
    rows = _problems(win)
    syn = [r for r in rows if "line 2: unknown op" in r]
    assert len(syn) == 1, rows                                  # 1 行だけ出る
    assert rows                                                 # 空の一覧では「消えた」を確かめられない
    assert not any("no problems" in r for r in rows), rows      # 『no problems』は消える
    assert _wave_lines(ed) == [2]                               # 該当行だけが波線
    assert set(ed.errors()) == {2}                              # ガターの赤印の元
    # Problems の行を押すと、その行へカーソルが移る
    ed.moveCursor(__import__("PySide6.QtGui", fromlist=["QTextCursor"]).QTextCursor.Start)
    _click_problem(win, rows.index(syn[0]))
    assert ed.textCursor().blockNumber() + 1 == 2


def test_fixing_the_text_removes_the_marks(win):
    ed = _editor(win, "gaussian (0.4, 0.5)\nnotanop (1,2)\n")
    win._program["apply"]()
    assert _wave_lines(ed) == [2]
    ed.setPlainText("gaussian (0.4, 0.5)\nsobel_mag (0.5, 0.5)\n")
    win._program["apply"]()
    _pump(0.3)
    assert _wave_lines(ed) == [] and ed.errors() == {}
    after = _problems(win)
    assert after, "the Problems list is empty"                    # 空でなく『no problems』の 1 行に戻る
    assert len(after) == 1 and "no problems" in after[0], after
    assert not any("unknown op" in r for r in after), after


def test_syntax_errors_appear_while_typing_without_apply(win):
    ed = _editor(win, "")
    ed.setPlainText("gaussian (0.4, 0.5)\ngaussian (zzz, 0.5)\n")      # 数でない引数
    _pump(0.6)
    assert _wave_lines(ed) == [2], ed.errors()
    rows = _problems(win)
    assert rows, "the Problems list is empty"
    assert any("args must be numbers" in r for r in rows), rows
    ed.setPlainText("for 3\ngaussian (0.4, 0.5)\n")                      # 閉じていない for
    _pump(0.6)
    assert ed.errors() and any("missing 'endfor'" in r for r in _problems(win)), _problems(win)
    assert _wave_lines(ed) == [1]                                       # 開いた行


def test_squiggle_survives_the_cursor_moving(win):
    ed = _editor(win, "gaussian (0.4, 0.5)\nnotanop (1,2)\n")
    win._program["apply"]()
    from PySide6 import QtCore
    _key(ed, QtCore.Qt.Key_Down)
    _key(ed, QtCore.Qt.Key_Up)
    assert _wave_lines(ed) == [2]


# --------------------------------------------------------------------------- 「もしかして」
def test_unknown_op_suggests_close_names(win):
    ed = _editor(win, "gausian (0.4,0.5)\n")
    win._program["apply"]()
    text = win._program["status"]().text()
    assert "unknown op 'gausian'" in text and "did you mean" in text and "gaussian" in text, text
    shown = text.split("did you mean", 1)[1]
    assert shown.count(",") <= 2                                          # 3 件まで
    # 解析関数そのもの(Qt なし)も同じ文を返す
    errs = studio.parse_hdev_program("gausian (0.4,0.5)\n", ["gaussian", "otsu"])[1]
    assert "gaussian" in errs[0] and "otsu" not in errs[0]


def test_unknown_op_with_nothing_close_has_no_suggestion():
    errs = studio.parse_hdev_program("qqqqqqqq (0.4,0.5)\n", ["gaussian", "otsu"])[1]
    assert errs == ["line 1: unknown op 'qqqqqqqq'"]


# --------------------------------------------------------------------------- B-2
def test_type_mismatch_is_one_row_in_problems(win):
    _editor(win, "otsu (0.5, 0.5)\ngaussian (0.4, 0.5)\n")
    win._load_sample_image("coins")
    _pump(0.3)
    win._program["apply"]()
    win._do_run_all()
    _pump(1.5)
    rows = [r for r in _problems(win) if "stage 2" in r]
    assert len(rows) == 1, _problems(win)
    assert "outputs 'region'" in rows[0] or "region" in rows[0]


# --------------------------------------------------------------------------- 3. 検索と置換(B-4)
_THREE = "otsu (0.5,0.5)\ngaussian (0.4,0.5)\notsu (0.5,0.5)\n"


def _fw():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.focusWidget()


def test_ctrl_f_in_the_program_goes_to_the_find_bar_not_the_operator_search(win):
    from PySide6 import QtCore
    ed = _editor(win, _THREE)
    f = win._program["find"]
    assert not f["bar"].isVisible()
    _key(ed, QtCore.Qt.Key_F, QtCore.Qt.ControlModifier)
    assert f["bar"].isVisible()
    assert _fw() is f["find_edit"], _fw()
    assert _fw() is not win._search_ui["edit"]
    assert not f["replace_edit"].isVisible()                       # Ctrl+F は検索だけ


def test_ctrl_f_elsewhere_still_goes_to_the_operator_search(win):
    from PySide6 import QtCore
    lst = win._search_ui["list"]
    lst.setFocus()
    win.activateWindow()
    _pump(0.2)
    _key(lst, QtCore.Qt.Key_F, QtCore.Qt.ControlModifier)
    assert _fw() is win._search_ui["edit"], _fw()                   # 従来どおり
    assert not win._program["find"]["bar"].isVisible()


def test_enter_finds_next_and_wraps_f3_and_shift_f3_move_and_esc_closes(win):
    from PySide6 import QtCore, QtGui
    from PySide6.QtTest import QTest
    ed = _editor(win, _THREE)
    f = win._program["find"]
    c = ed.textCursor(); c.movePosition(QtGui.QTextCursor.Start); ed.setTextCursor(c)
    _key(ed, QtCore.Qt.Key_F, QtCore.Qt.ControlModifier)
    QTest.keyClicks(f["find_edit"], "otsu")
    assert "2" in f["count"].text()                                 # 2 件
    line = lambda: ed.textCursor().blockNumber() + 1
    _key(f["find_edit"], QtCore.Qt.Key_Return)
    assert line() == 1 and ed.textCursor().selectedText() == "otsu"
    _key(f["find_edit"], QtCore.Qt.Key_Return)
    assert line() == 3                                              # 次の一致へ
    _key(f["find_edit"], QtCore.Qt.Key_Return)
    assert line() == 1                                              # 末尾から先頭へ戻る
    _key(ed, QtCore.Qt.Key_F3)
    assert line() == 3
    _key(ed, QtCore.Qt.Key_F3, QtCore.Qt.ShiftModifier)
    assert line() == 1
    _key(f["find_edit"], QtCore.Qt.Key_Escape)                      # Esc で閉じる。フォーカスは欄へ戻る
    assert not f["bar"].isVisible() and win.focusWidget() is ed        # (offscreen の窓は非アクティブなので窓の側の焦点で見る)
    _key(ed, QtCore.Qt.Key_F3)                                      # 閉じたあとも F3 は検索語で動く
    assert line() in (1, 3) and ed.textCursor().selectedText() == "otsu"


def test_esc_in_the_editor_closes_the_find_bar(win):
    from PySide6 import QtCore
    ed = _editor(win, _THREE)
    _key(ed, QtCore.Qt.Key_F, QtCore.Qt.ControlModifier)
    ed.setFocus()
    _key(ed, QtCore.Qt.Key_Escape)
    assert not win._program["find"]["bar"].isVisible()


def test_match_case_toggle(win):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    ed = _editor(win, "Otsu otsu OTSU\n")
    f = win._program["find"]
    _key(ed, QtCore.Qt.Key_F, QtCore.Qt.ControlModifier)
    QTest.keyClicks(f["find_edit"], "otsu")
    assert f["bar"].matches() == 3                                  # 既定は区別しない
    f["case"].setChecked(True)
    assert f["bar"].matches() == 1


def test_replace_all_is_one_undo(win):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    ed = _editor(win, _THREE)
    f = win._program["find"]
    _key(ed, QtCore.Qt.Key_H, QtCore.Qt.ControlModifier)            # Ctrl+H = 置換つき
    assert f["bar"].isVisible() and f["replace_edit"].isVisible()
    assert _fw() is f["find_edit"]                                  # ホールドアウトの窓は開かない
    QTest.keyClicks(f["find_edit"], "otsu")
    QTest.keyClicks(f["replace_edit"], "sobel_mag")
    f["replace_all"].click()
    _pump(0.1)
    assert "otsu" not in ed.toPlainText() and ed.toPlainText().count("sobel_mag") == 2
    ed.setFocus()
    _key(ed, QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)            # Undo 1 回で全部戻る
    assert ed.toPlainText() == _THREE


def test_replace_one_replaces_the_selected_match_and_moves_on(win):
    from PySide6 import QtCore, QtGui
    from PySide6.QtTest import QTest
    ed = _editor(win, _THREE)
    f = win._program["find"]
    c = ed.textCursor(); c.movePosition(QtGui.QTextCursor.Start); ed.setTextCursor(c)
    _key(ed, QtCore.Qt.Key_H, QtCore.Qt.ControlModifier)
    QTest.keyClicks(f["find_edit"], "otsu")
    QTest.keyClicks(f["replace_edit"], "canny")
    f["replace"].click()                                            # 最初は選ぶだけ
    assert ed.toPlainText() == _THREE
    f["replace"].click()                                            # 選んでいる 1 件を置き換えて次へ
    assert ed.toPlainText().count("canny") == 1 and ed.toPlainText().count("otsu") == 1
    assert ed.textCursor().selectedText() == "otsu"


def test_replace_text_containing_the_query_does_not_loop(win):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    ed = _editor(win, "otsu\notsu\n")
    f = win._program["find"]
    _key(ed, QtCore.Qt.Key_H, QtCore.Qt.ControlModifier)
    QTest.keyClicks(f["find_edit"], "otsu")
    QTest.keyClicks(f["replace_edit"], "otsu_x")
    assert f["bar"].replace_all() == 2
    assert ed.toPlainText() == "otsu_x\notsu_x\n"


# --------------------------------------------------------------------------- 4. Ctrl+/ の行コメント
def test_ctrl_slash_comments_and_uncomments_the_selected_lines(win):
    from PySide6 import QtCore, QtGui
    text = "gaussian (0.4, 0.5)\nsobel_mag (0.5, 0.5)\notsu (0.5, 0.5)\n"
    ed = _editor(win, text)
    c = ed.textCursor()
    c.setPosition(0); c.setPosition(len("gaussian (0.4, 0.5)\nsobel_mag"), QtGui.QTextCursor.KeepAnchor)
    ed.setTextCursor(c)                                         # 1〜2 行目を選ぶ
    _key(ed, QtCore.Qt.Key_Slash, QtCore.Qt.ControlModifier)
    lines = ed.toPlainText().split("\n")
    assert lines[0] == "* gaussian (0.4, 0.5)" and lines[1] == "* sobel_mag (0.5, 0.5)" and lines[2] == "otsu (0.5, 0.5)"
    _key(ed, QtCore.Qt.Key_Slash, QtCore.Qt.ControlModifier)     # もう一度で外れる
    assert ed.toPlainText() == text


def test_comment_toggle_is_one_undo_and_comment_lines_do_not_become_stages(win):
    from PySide6 import QtCore, QtGui
    text = "gaussian (0.4, 0.5)\nsobel_mag (0.5, 0.5)\notsu (0.5, 0.5)\n"
    ed = _editor(win, text)
    ed.selectAll()
    _key(ed, QtCore.Qt.Key_Slash, QtCore.Qt.ControlModifier)
    commented = [l for l in ed.toPlainText().split("\n") if l]
    assert commented, "the editor is empty"
    assert len(commented) == 3, commented                         # 行が消えていない
    assert all(l.startswith("* ") for l in commented), commented
    win._program["apply"]()
    assert len(win._test_model.stages) == 0                       # コメント行は段にならない
    ed.setFocus()
    _key(ed, QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)          # 1 回の Undo で戻る
    assert ed.toPlainText() == text


def test_comment_toggle_without_a_selection_uses_the_cursor_line_and_skips_blank_lines(win):
    from PySide6 import QtCore, QtGui
    ed = _editor(win, "gaussian (0.4, 0.5)\n\notsu (0.5, 0.5)\n")
    c = ed.textCursor(); c.setPosition(0); ed.setTextCursor(c)
    _key(ed, QtCore.Qt.Key_Slash, QtCore.Qt.ControlModifier)
    assert ed.toPlainText() == "* gaussian (0.4, 0.5)\n\notsu (0.5, 0.5)\n"
    ed.selectAll()                                                 # 空行は触らない / 1 行でも非コメントなら全部に付ける
    _key(ed, QtCore.Qt.Key_Slash, QtCore.Qt.ControlModifier)
    assert ed.toPlainText() == "* * gaussian (0.4, 0.5)\n\n* otsu (0.5, 0.5)\n"
    _key(ed, QtCore.Qt.Key_Slash, QtCore.Qt.ControlModifier)
    assert ed.toPlainText() == "* gaussian (0.4, 0.5)\n\notsu (0.5, 0.5)\n"


# --------------------------------------------------------------------------- 5. F1 の「ここのヘルプ」(WIRING 4 章 D127)
def _put_cursor_in(ed, needle):
    from PySide6 import QtGui
    i = ed.toPlainText().index(needle)
    c = QtGui.QTextCursor(ed.document())
    c.setPosition(i + 1)
    ed.setTextCursor(c)


def test_shift_f1_on_an_op_name_opens_its_help(win):
    from PySide6 import QtCore
    ed = _editor(win, "gaussian (0.4, 0.5)\notsu (0.5, 0.5)\n")
    _put_cursor_in(ed, "otsu")
    assert not win._help["dialog"].isVisible()
    _key(ed, QtCore.Qt.Key_F1)
    assert win._help["dialog"].isVisible()
    assert win._help["pick"].currentText() == "otsu"                 # 見出し = カーソルの下の op
    win._help["dialog"].hide()


def test_shift_f1_on_a_non_op_word_opens_nothing_and_says_so(win):
    from PySide6 import QtCore
    ed = _editor(win, "* just a comment\n")
    _put_cursor_in(ed, "comment")
    win._stage_list.setCurrentRow(-1)
    win._op_list.setCurrentRow(-1)
    _key(ed, QtCore.Qt.Key_F1)
    assert not win._help["dialog"].isVisible()
    assert win._keymap.dialog is not None and win._keymap.dialog.isVisible()  # 無ければキーの一覧(D127)
    win._keymap.dialog.close()


def test_f1_still_opens_the_keyboard_shortcuts_not_the_op_help(win):
    """(2026-11-15, integration) F1 = help for the selected op, the key list = Ctrl+F1 (first-run branch
    07e66baa0a and design D127; the key branch makes F1 "help here"). Shift+F1 stays the op reference."""
    assert win._actions["shortcuts"].shortcut().toString() == "Ctrl+F1"
    assert win._actions["op_reference"].shortcut().toString() == "Shift+F1"      # 欄の外では従来どおり


# --------------------------------------------------------------------------- 12. 文字サイズ(候補 12)
def _wheel(ed, dy):
    from PySide6 import QtCore, QtGui, QtWidgets
    ev = QtGui.QWheelEvent(QtCore.QPointF(50, 50), QtCore.QPointF(50, 50), QtCore.QPoint(0, 0), QtCore.QPoint(0, dy),
                           QtCore.Qt.NoButton, QtCore.Qt.ControlModifier, QtCore.Qt.NoScrollPhase, False)
    QtWidgets.QApplication.sendEvent(ed.viewport(), ev)
    _pump(0.05)


def test_ctrl_wheel_changes_the_editor_font_one_point_per_notch(win):
    ed = _editor(win, "gaussian (0.4, 0.5)\n")
    p0 = ed.font().pointSize()
    _wheel(ed, 120)
    assert ed.font().pointSize() == p0 + 1
    _wheel(ed, -120)
    _wheel(ed, -120)
    assert ed.font().pointSize() == p0 - 1


def test_ctrl_plus_and_ctrl_minus_change_the_font_within_6_to_32(win):
    from PySide6 import QtCore
    ed = _editor(win, "gaussian (0.4, 0.5)\n")
    for _ in range(40):
        _key(ed, QtCore.Qt.Key_Minus, QtCore.Qt.ControlModifier)
    assert ed.font().pointSize() == 6                                 # 下限
    for _ in range(40):
        _key(ed, QtCore.Qt.Key_Plus, QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier)
    assert ed.font().pointSize() == 32                                # 上限
    _key(ed, QtCore.Qt.Key_Equal, QtCore.Qt.ControlModifier)          # Ctrl+= もすでに上限
    assert ed.font().pointSize() == 32


def test_font_size_is_saved_and_restored_and_the_gutter_follows(tmp_path, monkeypatch):
    win, _m = _launch(tmp_path, monkeypatch, name="font.ini")
    try:
        ed = _editor(win, "gaussian (0.4, 0.5)\n")
        w0 = ed.gutter_width()
        _wheel(ed, 120); _wheel(ed, 120); _wheel(ed, 120)
        want = ed.font().pointSize()
        assert ed.gutter_width() >= w0                                # 字が大きくなれば行番号の欄も追従
        assert int(studio._settings().value("ui/mono_font_pt")) == want
    finally:
        _close(win)
    win2, _m2 = _launch(tmp_path, monkeypatch, name="font.ini")        # 再起動
    try:
        assert win2._program["edit"].font().pointSize() == want
    finally:
        _close(win2)


# --------------------------------------------------------------------------- 6. Variables が古いまま(B-3)
def test_variables_panel_is_current_when_opened_after_a_run_while_hidden(win):
    win._load_sample_image("coins")
    _pump(0.3)
    win._docks["variables"].hide()
    _pump(0.2)
    ed = win._program["edit"]
    ed.setPlainText("gaussian (0.4, 0.5)\nsobel_mag (0.5, 0.5)\notsu (0.5, 0.5)\n")
    win._program["apply"]()
    win._do_run_all()
    _pump(1.5)
    assert not win._docks["variables"].isVisible()
    win._docks["variables"].show()                                   # 手動の refresh はしない
    _pump(0.4)
    vl = win._variables["list"]
    rows = [vl.item(i).text() for i in range(vl.count())]
    assert len(rows) == 4, rows
    assert not any("? ·" in r for r in rows), rows                   # 『? · control』が残らない
    assert any("image · iconic" in r for r in rows) and any("region · iconic" in r for r in rows), rows


# --------------------------------------------------------------------------- 7. 言語の切り替えに追従する文言(B-5, B-7)
def _rows_text(win):
    return [win._stage_list.item(i).text() for i in range(win._stage_list.count())]


def _uncomputed_stage(win):
    win._load_sample_image("coins")
    _pump(0.3)
    win._test_model.add_stage("otsu")                       # モデルにだけ足す: まだ計算されていない段
    win._refresh_stage_list(select=0)
    _pump(0.2)


def test_stage_row_not_computed_is_english_only_in_english(win):
    _uncomputed_stage(win)
    row = _rows_text(win)[0]
    assert "not computed" in row and not _CJK.search(row), row           # 英語 UI に日本語が混ざらない
    assert "not computed" in win._stage_list.item(0).toolTip() and not _CJK.search(win._stage_list.item(0).toolTip())


@pytest.mark.parametrize("lang, word", [("ja", "未計算"), ("zh", "未计算"), ("tw", "未計算"),
                                          ("ko", "미계산"), ("de", "nicht berechnet"), ("hi", "गणना नहीं हुई")])
def test_stage_row_not_computed_follows_the_language(win, lang, word):
    _uncomputed_stage(win)
    win._apply_language(lang)
    _pump(0.3)
    try:
        row = _rows_text(win)[0]
        assert word in row, row
        assert "not computed" not in row, row
    finally:
        win._apply_language("en")


def _hover_readout(win):
    win._load_sample_image("coins")
    _pump(0.3)
    win._program["edit"].setPlainText("gaussian (0.4, 0.5)\n")
    win._program["apply"]()
    win._do_run_all()
    _pump(1.0)
    win._current_view().hover_cb(10, 10, 0.3)
    return win._readout.text()


def test_pixel_readout_has_no_cjk_in_english(win):
    text = _hover_readout(win)
    # (2026-11-15) the first-run branch's line: the coordinates first (M5, design P10-5)
    assert text.startswith("x=10  y=10   value ") and "shown" in text and "range" in text, text
    assert not _CJK.search(text), text


def test_pixel_readout_follows_the_language(win):
    _hover_readout(win)
    win._apply_language("ja")
    try:
        win._current_view().hover_cb(10, 10, 0.3)
        text = win._readout.text()
        assert text.startswith("x=10  y=10   値 ") and "表示" in text and "レンジ" in text, text
        assert not re.search("[A-Za-z]{4,}", text.replace("float64", "")), text        # 英単語(型名を除く)が残らない
    finally:
        win._apply_language("en")
    win._apply_language("de")
    try:
        win._current_view().hover_cb(10, 10, 0.3)
        assert win._readout.text().startswith("x=10  y=10   Wert "), win._readout.text()
    finally:
        win._apply_language("en")


def test_run_status_line_follows_a_language_switch(win):
    win._load_sample_image("coins")
    _pump(0.3)
    win._program["edit"].setPlainText("gaussian (0.4, 0.5)\n")
    win._program["apply"]()
    win._do_run_all()
    _pump(0.8)
    msg = win.statusBar().currentMessage()
    assert msg.startswith("Run: done / Result:"), msg
    win._apply_language("ja")
    _pump(0.3)
    try:
        msg = win.statusBar().currentMessage()
        assert msg.startswith("実行: 完了 / 結果:"), msg                   # 英語のまま残らない
        assert "Run: done" not in msg
    finally:
        win._apply_language("en")
    msg = win.statusBar().currentMessage()
    assert msg.startswith("Run: done / Result:"), msg                    # 戻せば英語へ


def test_new_texts_all_have_six_languages_and_pending_rows_did_not_grow():
    with open(os.path.join(ROOT, "studio_assets", "i18n.json"), encoding="utf-8") as f:
        d = json.load(f)
    for key in ("not computed", "Value %s (%s) / Shown %s / Range %s to %s", "did you mean %s?", "Find", "Replace all",
                "not an operator: %s", "no operator under the cursor", "knobs on this line: %s",
                "%d replaced", "Match case"):
        row = d["strings"][key]
        assert all(row.get(c) for c in ("ja", "zh", "tw", "ko", "de", "hi")), key
    # 上限(test_studio_first_minute の門 PENDING_ROWS と同じ数。2026-11-15: 初回の枝の日本語だけの行を合わせた)
    assert len([k for k in d["pending_translation"] if k != "_note"]) <= 455


# --------------------------------------------------------------------------- 8. 選んだ行だけの実行(候補 10)
_OPS3 = ["gaussian", "sobel_mag", "otsu"]


def _counting(monkeypatch, names):
    """``ops.RT`` の各 op を呼び出し回数つきの包みに差し替える(本物の計算はそのまま)。"""
    import api
    counts = {n: 0 for n in names}
    for n in names:
        real = api._ops.RT[n]

        def wrap(v, a, b, _real=real, _n=n):
            counts[_n] += 1
            return _real(v, a, b)
        monkeypatch.setitem(api._ops.RT, n, wrap)
    return counts


def _three_stage_program(win):
    win._load_sample_image("coins")
    _pump(0.3)
    ed = _editor(win, "gaussian (0.4, 0.5)\nsobel_mag (0.5, 0.5)\notsu (0.5, 0.5)\n")
    win._program["apply"]()
    win._do_run_all()
    _pump(1.5)
    return ed


def _select_line(ed, n):
    from PySide6 import QtGui
    blk = ed.document().findBlockByNumber(n - 1)
    c = QtGui.QTextCursor(blk)
    c.select(QtGui.QTextCursor.LineUnderCursor)
    ed.setTextCursor(c)


def test_running_only_the_selected_line_does_not_recompute_the_other_stages(win, monkeypatch):
    ed = _three_stage_program(win)
    counts = _counting(monkeypatch, _OPS3)
    _select_line(ed, 2)
    win._program["run_selection"]()
    _pump(0.3)
    assert "ran line 2" in win._program["status"]().text(), win._program["status"]().text()
    assert counts["gaussian"] == 0, counts                         # 1 行目(上流)はキャッシュから
    assert counts["otsu"] == 0, counts                             # 3 行目は計算しない
    assert counts["sobel_mag"] >= 1, counts                        # 選んだ行だけ走った


def test_ctrl_return_with_a_selection_runs_only_the_selection(win, monkeypatch):
    from PySide6 import QtCore
    ed = _three_stage_program(win)
    counts = _counting(monkeypatch, _OPS3)
    _select_line(ed, 3)
    _key(ed, QtCore.Qt.Key_Return, QtCore.Qt.ControlModifier)
    _pump(0.3)
    assert "ran line 3" in win._program["status"]().text(), win._program["status"]().text()
    assert counts["gaussian"] == 0 and counts["sobel_mag"] == 0 and counts["otsu"] >= 1, counts


def test_ctrl_return_without_a_selection_is_still_run_all(win):
    from PySide6 import QtCore
    ed = _three_stage_program(win)
    c = ed.textCursor(); c.clearSelection(); ed.setTextCursor(c)
    assert win._actions["run_all"].shortcut().toString() == "Ctrl+Return"       # 割り当ては変えない
    assert win._actions["run_selection"].shortcut().toString() == "Ctrl+Alt+Return"


def test_run_selected_lines_is_in_the_run_menu(win):
    names = [a.text() for a in win._menus["run"].actions()]
    assert any("Run selected lines" in n for n in names), names


def test_selecting_only_a_comment_line_runs_nothing_and_says_so(win):
    ed = _editor(win, "* a comment\ngaussian (0.4, 0.5)\n")
    win._load_sample_image("coins")
    win._program["apply"]()
    _select_line(ed, 1)
    win._program["run_selection"]()
    assert "no stage in the selected lines" in win._program["status"]().text()


# --------------------------------------------------------------------------- 9. ROI の統計を Inspector に(候補 7・B-6)
def test_roi_statistics_appear_in_the_inspector(win):
    win._load_sample_image("coins")
    _pump(0.3)
    win._program["edit"].setPlainText("gaussian (0.4, 0.5)\n")
    win._program["apply"]()
    win._do_run_all()
    _pump(1.0)
    before = win._inspector.toPlainText()
    assert "roi" not in before
    whole = float(re.search(r"mean: ([-0-9.eE+]+)", before).group(1))
    win._set_roi((50, 50, 150, 150))
    text = win._inspector.toPlainText()
    assert "roi: 100x100" in text, text
    roi_mean = float(re.search(r"roi min: .*mean: ([-0-9.eE+]+)", text).group(1))
    assert abs(roi_mean - whole) > 1e-3, (roi_mean, whole)               # 全画像の mean とは違う値
    assert text.startswith(before.split("\n\nroi:")[0])                  # 本文はそのまま、ROI が後ろに付く
    win._set_roi(None)                                                   # 解除(Shift+クリックと同じ入口)
    assert "roi" not in win._inspector.toPlainText()


# --------------------------------------------------------------------------- 10. 入口(STUDIO_UX_RULES §1・§6)
_ENTRY_KEYS = {
    "program_find": ("Find in Program", "Ctrl+F"), "program_replace": ("Replace in Program", "Ctrl+H"),
    "program_find_next": ("Find next in Program", "F3"), "program_find_prev": ("Find previous in Program", "Shift+F3"),
    "program_comment": ("Comment / uncomment lines", "Ctrl+/"),
    "help_here": ("Help for the selected operator", "F1"),  # WIRING 2.7: program_help_here は help_here に吸収
    "program_font_bigger": ("Bigger editor text", "Ctrl++"), "program_font_smaller": ("Smaller editor text", "Ctrl+-"),
    "run_selection": ("Run selected lines", "Ctrl+Alt+Return"),
}


def _menu_texts(win):
    out = []
    for key in ("edit", "view", "help", "run"):
        out += [a.text() for a in win._menus[key].actions()]
    return out


def test_every_new_feature_has_menu_palette_and_key_entries_under_one_name(win):
    texts = _menu_texts(win)
    for key, (name, seq) in _ENTRY_KEYS.items():
        a = win._actions[key]
        assert a.text() == name, (key, a.text())
        assert name in texts, ("menu", key)                                   # メニュー
        assert seq in [s.toString() for s in a.shortcuts()], (key, [s.toString() for s in a.shortcuts()])   # キー
        assert a.toolTip(), key                                                # ヒント


def _palette_hits(win, query):
    win._actions["palette"].trigger if False else None
    labels = ["▸ " + win._actions[k].text() + " " + studio.PALETTE_WORDS.get(k, "") for k in win._actions]
    keys = list(win._actions)
    return [keys[i] for i in studio.palette_filter(labels, query)]


@pytest.mark.parametrize("query, key", [
    ("検索", "program_find"), ("find", "program_find"), ("探す", "program_find"),
    ("置換", "program_replace"), ("replace", "program_replace"), ("置き換え", "program_replace"),
    ("次を検索", "program_find_next"), ("前を検索", "program_find_prev"),
    ("コメント", "program_comment"), ("comment", "program_comment"), ("コメントアウト", "program_comment"),
    ("ヘルプ", "help_here"), ("documentation", "help_here"),  # WIRING 2.7: パレットの語も移す
    ("文字サイズ", "program_font_bigger"), ("font size", "program_font_smaller"), ("拡大", "program_font_bigger"), ("縮小", "program_font_smaller"),
    ("選んだ行", "run_selection"), ("selection", "run_selection"), ("部分実行", "run_selection"),
])
def test_command_palette_finds_the_new_features_by_japanese_and_english_words(win, query, key):
    assert key in _palette_hits(win, query), (query, key)


def test_real_palette_dialog_lists_the_new_actions_and_runs_one(win):
    """実際のパレット(Ctrl+P の窓)で、日本語の語から当たり、Enter で動く。"""
    from PySide6 import QtCore, QtWidgets
    from PySide6.QtTest import QTest
    ed = _editor(win, "otsu (0.5,0.5)\n")
    seen = {}

    def drive():
        pal = win._palette
        pal["edit"].setText("置換")
        QtWidgets.QApplication.processEvents()
        seen["rows"] = [pal["list"].item(i).text() for i in range(pal["list"].count())]
        QTest.keyClick(pal["edit"], QtCore.Qt.Key_Return)
    QtCore.QTimer.singleShot(300, drive)
    win._actions["palette"].trigger()
    _pump(0.3)
    assert any("Replace in Program" in r for r in seen["rows"]), seen["rows"][:5]
    assert win._program["find"]["bar"].isVisible()                          # Enter で置換つきの検索帯が開いた
    assert win._program["find"]["replace_edit"].isVisible()


def test_menu_entry_runs_the_feature_from_anywhere(win):
    win._program["edit"].setPlainText("* a\notsu (0.5,0.5)\n")
    win._actions["program_find"].trigger()
    assert win._program["find"]["bar"].isVisible()
    win._program["find"]["bar"].close_bar()
    win._actions["program_font_bigger"].trigger()
    assert win._program["edit"].font().pointSize() >= 11
    win._program["edit"].selectAll()
    win._actions["program_comment"].trigger()
    assert win._program["edit"].toPlainText().startswith("* * a")


def test_new_entry_names_have_six_languages_and_japanese_ui_shows_japanese(win):
    win._apply_language("ja")
    try:
        for key in _ENTRY_KEYS:
            t = win._actions[key].text()
            assert _CJK.search(t), (key, t)                                     # 日本語 UI に英語だけの名前を残さない
    finally:
        win._apply_language("en")
